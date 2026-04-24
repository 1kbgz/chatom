"""Tests for interactive component publishing and interaction handling."""

import asyncio
from typing import List

import pytest

from chatom import Interaction, InteractionRegistry, InteractionType, Message
from chatom.format import (
    ButtonStyle,
    ComponentContainer,
    Format,
    FormattedMessage,
    SelectOption,
    attach_components_for_backend,
)


def _run(coro):
    """Run a coroutine, creating an event loop if needed."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Phase 2.1: components on Message + attach_components_for_backend
# ---------------------------------------------------------------------------


class TestMessageComponents:
    def test_default_components_is_none(self):
        m = Message(content="hi")
        assert m.components is None

    def test_attach_component_container(self):
        m = Message(content="hi")
        cc = ComponentContainer()
        cc.add_button("Yes", "go")
        m.components = cc
        assert m.components is cc
        assert len(m.components.rows) == 1

    def test_round_trip_through_formatted(self):
        fm = FormattedMessage()
        fm.add_text("click below")
        fm.components = ComponentContainer()
        fm.components.add_button("Go", "btn1")
        msg = Message.from_formatted(fm, backend="slack")
        assert msg.components is not None
        assert msg.components.rows[0].components[0].action_id == "btn1"

        fm2 = msg.to_formatted()
        assert fm2.components is msg.components

    def test_none_components_round_trip(self):
        fm = FormattedMessage()
        fm.add_text("plain")
        msg = Message.from_formatted(fm, backend="slack")
        assert msg.components is None


class TestAttachComponentsForBackend:
    def _container(self) -> ComponentContainer:
        c = ComponentContainer()
        c.add_button("Yes", "yes_btn", style=ButtonStyle.PRIMARY)
        c.add_button("No", "no_btn", style=ButtonStyle.DANGER)
        return c

    def test_slack_produces_blocks(self):
        kw: dict = {}
        attach_components_for_backend(kw, self._container(), Format.SLACK_MARKDOWN)
        assert "blocks" in kw
        # single action row with two buttons
        assert kw["blocks"][0]["type"] == "actions"
        assert len(kw["blocks"][0]["elements"]) == 2

    def test_slack_appends_to_existing_blocks(self):
        kw: dict = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}]}
        attach_components_for_backend(kw, self._container(), Format.SLACK_MARKDOWN)
        assert len(kw["blocks"]) == 2  # original section + our action row

    def test_discord_produces_components(self):
        kw: dict = {}
        attach_components_for_backend(kw, self._container(), Format.DISCORD_MARKDOWN)
        assert "components" in kw
        assert kw["components"][0]["type"] == 1  # action row

    def test_symphony_inlines_into_content(self):
        kw: dict = {"content": "please pick"}
        attach_components_for_backend(kw, self._container(), Format.SYMPHONY_MESSAGEML)
        assert "components" not in kw
        assert "blocks" not in kw
        assert "<button" in kw["content"]
        assert kw["content"].startswith("please pick")

    def test_empty_container_is_noop(self):
        kw: dict = {}
        attach_components_for_backend(kw, ComponentContainer(), Format.SLACK_MARKDOWN)
        assert kw == {}

    def test_generic_format_uses_components(self):
        kw: dict = {}
        attach_components_for_backend(kw, self._container(), Format.MARKDOWN)
        assert "components" in kw

    def test_select_menu(self):
        c = ComponentContainer()
        c.add_select(
            "picker",
            [SelectOption(label="A", value="a"), SelectOption(label="B", value="b")],
        )
        kw: dict = {}
        attach_components_for_backend(kw, c, Format.SLACK_MARKDOWN)
        assert kw["blocks"][0]["elements"][0]["type"] == "static_select"


# ---------------------------------------------------------------------------
# Phase 2.2: Interaction model + InteractionRegistry
# ---------------------------------------------------------------------------


class TestInteractionModel:
    def test_defaults(self):
        i = Interaction(id="x")
        assert i.type == InteractionType.OTHER
        assert i.values == []
        assert i.value == ""
        assert i.channel_id == ""
        assert i.user_id == ""

    def test_button_interaction(self):
        i = Interaction(
            id="evt1",
            type=InteractionType.BUTTON,
            action_id="confirm",
            values=["ok"],
            message_id="msg1",
            backend="slack",
        )
        assert i.type == InteractionType.BUTTON
        assert i.value == "ok"
        assert i.action_id == "confirm"

    def test_select_interaction(self):
        i = Interaction(
            id="evt2",
            type=InteractionType.SELECT,
            action_id="picker",
            values=["opt_a", "opt_b"],
        )
        assert i.values == ["opt_a", "opt_b"]
        assert i.value == "opt_a"


class TestInteractionRegistry:
    def test_register_and_dispatch(self):
        r = InteractionRegistry()
        seen: List[str] = []

        def handle(ev: Interaction) -> str:
            seen.append(ev.value)
            return ev.value

        r.register("go", handle)
        results = _run(r.dispatch(Interaction(id="e1", action_id="go", values=["1"])))
        assert seen == ["1"]
        assert results == ["1"]

    def test_decorator_registration(self):
        r = InteractionRegistry()

        @r.on("click")
        def handle(ev):
            return "clicked"

        results = _run(r.dispatch(Interaction(id="e", action_id="click")))
        assert results == ["clicked"]

    def test_async_handler(self):
        r = InteractionRegistry()

        async def handle(ev):
            await asyncio.sleep(0)
            return ev.action_id

        r.register("async_btn", handle)
        results = _run(r.dispatch(Interaction(id="e", action_id="async_btn")))
        assert results == ["async_btn"]

    def test_multiple_handlers_run_in_order(self):
        r = InteractionRegistry()
        order: List[int] = []
        r.register("x", lambda e: order.append(1))
        r.register("x", lambda e: order.append(2))
        r.register("x", lambda e: order.append(3))
        _run(r.dispatch(Interaction(id="e", action_id="x")))
        assert order == [1, 2, 3]

    def test_handler_exception_is_isolated(self):
        r = InteractionRegistry()
        results: List[str] = []

        def bad(ev):
            raise RuntimeError("boom")

        def good(ev):
            results.append("ran")
            return "ok"

        r.register("a", bad)
        r.register("a", good)
        out = _run(r.dispatch(Interaction(id="e", action_id="a")))
        assert results == ["ran"]
        # only the successful handler contributes a result
        assert out == ["ok"]

    def test_default_handler_for_unmatched(self):
        r = InteractionRegistry()
        seen: List[str] = []

        r.register_default(lambda e: seen.append(f"default:{e.action_id}"))
        r.register("known", lambda e: seen.append("known"))

        _run(r.dispatch(Interaction(id="e1", action_id="known")))
        _run(r.dispatch(Interaction(id="e2", action_id="surprise")))

        assert seen == ["known", "default:surprise"]

    def test_specific_overrides_default(self):
        r = InteractionRegistry()
        calls: List[str] = []
        r.register_default(lambda e: calls.append("default"))
        r.register("hit", lambda e: calls.append("specific"))
        _run(r.dispatch(Interaction(id="e", action_id="hit")))
        assert calls == ["specific"]

    def test_unregister(self):
        r = InteractionRegistry()

        def h(ev):
            return 1

        r.register("a", h)
        assert r.unregister("a", h) is True
        assert r.unregister("a", h) is False
        assert r.action_ids == []

    def test_clear_all(self):
        r = InteractionRegistry()
        r.register("a", lambda e: None)
        r.register("b", lambda e: None)
        r.clear()
        assert r.action_ids == []

    def test_clear_one(self):
        r = InteractionRegistry()
        r.register("a", lambda e: None)
        r.register("b", lambda e: None)
        r.clear("a")
        assert r.action_ids == ["b"]

    def test_handlers_for(self):
        r = InteractionRegistry()

        def h1(ev):
            return 1

        def h2(ev):
            return 2

        r.register("x", h1)
        r.register("x", h2)
        assert r.handlers_for("x") == [h1, h2]
        # unmatched with no default -> empty list
        assert r.handlers_for("missing") == []


# ---------------------------------------------------------------------------
# Backend.stream_interactions default behavior
# ---------------------------------------------------------------------------


class TestStreamInteractionsDefault:
    """The default ``BackendBase.stream_interactions`` raises NotImplementedError."""

    def test_raises_not_implemented(self):
        from chatom.backend import BackendBase

        class Stub(BackendBase):
            name = "stub"

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def send_message(self, channel, content, **kwargs):
                pass

            async def fetch_user(self, *args, **kwargs):
                return None

            async def fetch_channel(self, *args, **kwargs):
                return None

            async def fetch_messages(self, *args, **kwargs):
                return []

        async def run():
            stub = Stub()
            gen = stub.stream_interactions()
            with pytest.raises(NotImplementedError):
                async for _ in gen:
                    pass

        _run(run())
