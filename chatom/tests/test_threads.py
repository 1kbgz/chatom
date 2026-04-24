"""Tests for Phase 5: thread abstraction polish.

Covers:
- BackendBase._extract_thread_id / _extract_reply_to_id helpers.
- Standardized ``thread=`` / ``reply_to=`` kwargs on each backend's
  ``send_message`` (via the Mock backends).
- ``Message.reply()`` convenience helper.
- ``_send_messages_thread`` forwarding ``msg.thread`` and ``msg.reply_to``
  as kwargs to ``send_message``.
"""

import asyncio

import pytest
from pydantic import SecretStr

from chatom.backend import BackendBase
from chatom.base import Channel, Message
from chatom.base.thread import Thread


class TestExtractHelpers:
    def test_extract_thread_id_none(self):
        assert BackendBase._extract_thread_id(None) is None

    def test_extract_thread_id_empty_string(self):
        assert BackendBase._extract_thread_id("") is None

    def test_extract_thread_id_string(self):
        assert BackendBase._extract_thread_id("T1") == "T1"

    def test_extract_thread_id_from_thread(self):
        assert BackendBase._extract_thread_id(Thread(id="T2")) == "T2"

    def test_extract_thread_id_from_message_with_thread(self):
        msg = Message(id="M1", thread=Thread(id="T3"))
        assert BackendBase._extract_thread_id(msg) == "T3"

    def test_extract_thread_id_from_message_without_thread(self):
        # Root-of-thread idiom: the message itself seeds the thread.
        msg = Message(id="M2")
        assert BackendBase._extract_thread_id(msg) == "M2"

    def test_extract_reply_to_id_none(self):
        assert BackendBase._extract_reply_to_id(None) is None

    def test_extract_reply_to_id_string(self):
        assert BackendBase._extract_reply_to_id("M1") == "M1"

    def test_extract_reply_to_id_message(self):
        assert BackendBase._extract_reply_to_id(Message(id="M5")) == "M5"


@pytest.fixture
def slack_backend():
    from chatom.slack import MockSlackBackend, SlackConfig

    cfg = SlackConfig(bot_token=SecretStr("xoxb-t"), app_token=SecretStr("xapp-t"))
    return MockSlackBackend(config=cfg)


@pytest.fixture
def discord_backend():
    from chatom.discord import DiscordConfig, MockDiscordBackend

    cfg = DiscordConfig(bot_token=SecretStr("discord-token"))
    return MockDiscordBackend(config=cfg)


@pytest.fixture
def telegram_backend():
    from chatom.telegram import MockTelegramBackend

    return MockTelegramBackend()


@pytest.fixture
def symphony_backend():
    from chatom.symphony import MockSymphonyBackend, SymphonyConfig

    cfg = SymphonyConfig()
    return MockSymphonyBackend(config=cfg)


class TestSlackThreadKwargs:
    @pytest.mark.asyncio
    async def test_thread_message_translated_to_thread_ts(self, slack_backend):
        await slack_backend.connect()
        parent = Message(id="1234.5678")
        msg = await slack_backend.send_message("C1", "hi", thread=parent)
        assert msg.thread is not None
        assert msg.thread.id == "1234.5678"

    @pytest.mark.asyncio
    async def test_thread_string_id(self, slack_backend):
        await slack_backend.connect()
        msg = await slack_backend.send_message("C1", "hi", thread="abc.def")
        assert msg.thread.id == "abc.def"

    @pytest.mark.asyncio
    async def test_reply_to_uses_thread_ts(self, slack_backend):
        # Slack has no standalone reply primitive; reply_to collapses to thread_ts.
        await slack_backend.connect()
        parent = Message(id="9.9")
        msg = await slack_backend.send_message("C1", "ack", reply_to=parent)
        assert msg.thread is not None
        assert msg.thread.id == "9.9"

    @pytest.mark.asyncio
    async def test_thread_id_legacy_still_works(self, slack_backend):
        await slack_backend.connect()
        msg = await slack_backend.send_message("C1", "hi", thread_id="legacy.123")
        assert msg.thread.id == "legacy.123"


class TestDiscordThreadKwargs:
    @pytest.mark.asyncio
    async def test_thread_routes_to_thread_channel(self, discord_backend):
        await discord_backend.connect()
        msg = await discord_backend.send_message("CHAN1", "hi", thread="THREAD42")
        # Discord threads ARE channels, so the message should be sent there.
        assert msg.channel_id == "THREAD42"
        assert msg.thread is not None
        assert msg.thread.id == "THREAD42"

    @pytest.mark.asyncio
    async def test_reply_to_tracked(self, discord_backend):
        await discord_backend.connect()
        parent = Message(id="888")
        msg = await discord_backend.send_message("CHAN1", "ack", reply_to=parent)
        assert msg.metadata.get("reply_to_id") == "888"


class TestTelegramThreadKwargs:
    @pytest.mark.asyncio
    async def test_thread_translated(self, telegram_backend):
        msg = await telegram_backend.send_message("12345", "hi", thread="777")
        assert msg.thread is not None
        assert msg.thread.id == "777"

    @pytest.mark.asyncio
    async def test_reply_to_tracked(self, telegram_backend):
        parent = Message(id="42")
        msg = await telegram_backend.send_message("12345", "ack", reply_to=parent)
        assert msg.metadata.get("reply_to_message_id") == "42"


class TestSymphonyThreadKwargs:
    @pytest.mark.asyncio
    async def test_thread_silently_dropped(self, symphony_backend):
        # Symphony has no thread concept; should accept and ignore rather than raise.
        await symphony_backend.connect()
        parent = Message(id="M1")
        msg = await symphony_backend.send_message("S1", "hi", thread=parent, reply_to=parent)
        assert msg is not None


class TestMessageReply:
    @pytest.mark.asyncio
    async def test_reply_in_thread_default(self, slack_backend):
        await slack_backend.connect()
        incoming = Message(id="1.0", channel=Channel(id="C1"))
        reply = await incoming.reply("thanks", backend=slack_backend)
        # Slack's thread_ts is set from the incoming message id (no existing thread)
        assert reply.thread is not None
        assert reply.thread.id == "1.0"

    @pytest.mark.asyncio
    async def test_reply_preserves_existing_thread(self, slack_backend):
        await slack_backend.connect()
        incoming = Message(id="2.0", channel=Channel(id="C1"), thread=Thread(id="root.ts"))
        reply = await incoming.reply("thanks", backend=slack_backend)
        assert reply.thread.id == "root.ts"

    @pytest.mark.asyncio
    async def test_reply_without_thread(self, telegram_backend):
        incoming = Message(id="99", channel=Channel(id="12345"))
        reply = await incoming.reply("ack", backend=telegram_backend, in_thread=False)
        # in_thread=False uses reply_to path
        assert reply.metadata.get("reply_to_message_id") == "99"
        assert reply.thread is None

    @pytest.mark.asyncio
    async def test_reply_without_channel_raises(self, slack_backend):
        await slack_backend.connect()
        orphan = Message(id="orphan")
        with pytest.raises(ValueError, match="no channel"):
            await orphan.reply("x", backend=slack_backend)


class _CapturingBackend(BackendBase):
    """Captures send_message kwargs for assertion. Uses class-level state
    so we don't have to plumb config through the CSP writer, which spawns
    a new backend instance in its own thread."""

    name = "capturing"
    display_name = "Capturing"

    # class-level capture list so the test sees what the writer thread sent
    captured: list = []

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def fetch_user(self, identifier=None, **kwargs):
        return None

    async def fetch_channel(self, identifier=None, **kwargs):
        return Channel(id=kwargs.get("id") or (identifier or ""))

    async def fetch_messages(self, channel, **kwargs):
        return []

    async def send_message(self, channel, content, **kwargs):
        type(self).captured.append({"channel": channel, "content": content, **kwargs})
        return Message(id="sent", content=content, channel=Channel(id=str(channel)))


def test_send_messages_thread_forwards_thread_and_reply_to():
    """``_send_messages_thread`` must forward ``msg.thread`` and
    ``msg.reply_to`` as kwargs to ``send_message``."""
    pytest.importorskip("csp")
    from queue import Queue

    from chatom.csp.nodes import _send_messages_thread

    _CapturingBackend.captured = []
    backend = _CapturingBackend()

    parent = Message(id="parent-id")
    thread_msg = Message(
        id="m1",
        content="in thread",
        channel=Channel(id="C1"),
        thread=Thread(id="T-root"),
    )
    reply_msg = Message(
        id="m2",
        content="replying",
        channel=Channel(id="C1"),
        reply_to=parent,
    )

    q: Queue = Queue()
    q.put(thread_msg)
    q.put(reply_msg)
    q.put(None)

    # Run the writer thread function synchronously (it drives its own loop).
    _send_messages_thread(q, backend)

    captured = _CapturingBackend.captured
    assert len(captured) == 2
    assert captured[0]["content"] == "in thread"
    assert isinstance(captured[0]["thread"], Thread)
    assert captured[0]["thread"].id == "T-root"

    assert captured[1]["content"] == "replying"
    # reply_to forwarded as the Message object
    assert isinstance(captured[1]["reply_to"], Message)
    assert captured[1]["reply_to"].id == "parent-id"


# Make sure asyncio-based tests don't leak loops
@pytest.fixture(autouse=True)
def _close_loops():
    yield
    # Drain any pending tasks in the default loop policy
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if not loop.is_closed():
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for t in pending:
                t.cancel()
    except Exception:
        pass
