"""Tests for chatom bridge: IdentityMapper and MessageBridge."""

import asyncio
import re
from typing import List, Optional

import pytest

from chatom.base import Channel, Message, User
from chatom.base.attachment import Attachment
from chatom.base.embed import Embed
from chatom.bridge import IdentityMapper, MessageBridge
from chatom.bridge.identity import LinkedIdentity

# Mention patterns, one per backend used in these tests. Real backend
# classes declare these themselves as ``mention_pattern`` ClassVars.
_MENTION_PATTERNS = {
    "slack": re.compile(r"<@(U[A-Z0-9]+)>"),
    "discord": re.compile(r"<@!?(\d+)>"),
    "symphony": re.compile(r'<mention\s+uid="(\d+)"\s*/>'),
}


def _platform_id(backend: str, n: int) -> str:
    """Generate a platform-conformant user ID that matches mention regex patterns."""
    if backend == "slack":
        return f"U{n:09d}"  # U prefix + digits
    elif backend in ("discord", "symphony"):
        return str(100000 + n)  # numeric
    return f"USR{n}"


class FakeBackend:
    """Minimal backend stub for testing."""

    def __init__(self, name: str = "fake", users: Optional[dict] = None):
        self.name = name
        self._users = users or {}  # id -> User  OR  email -> User
        self.sent: List[dict] = []
        self.mention_pattern = _MENTION_PATTERNS.get(name)

    async def fetch_user(
        self,
        identifier=None,
        *,
        id=None,
        name=None,
        email=None,
        handle=None,
    ) -> Optional[User]:
        uid = identifier or id
        if uid and uid in self._users:
            return self._users[uid]
        if email:
            for u in self._users.values():
                if u.email == email:
                    return u
        return None

    async def send_message(self, channel, content, **kwargs) -> Message:
        self.sent.append({"channel": channel, "content": content, **kwargs})
        return Message(id="sent_1", content=content, backend=self.name)


def _run(coro):
    """Run a coroutine in the current event loop or create one."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class TestLinkedIdentity:
    """Tests for LinkedIdentity data model."""

    def test_add_and_query(self):
        li = LinkedIdentity()
        li.add("slack", "U1", User(id="U1", name="Alice", email="alice@co.com"))
        assert li.has_backend("slack")
        assert not li.has_backend("discord")
        assert li.get_ref("slack") == "U1"
        assert li.get_ref("discord") is None
        assert li.email == "alice@co.com"

    def test_add_multiple(self):
        li = LinkedIdentity()
        li.add("slack", "U1", User(id="U1", email="a@co.com"))
        li.add("symphony", "S1", User(id="S1", email="a@co.com"))
        assert li.has_backend("slack")
        assert li.has_backend("symphony")
        assert li.get_ref("symphony") == "S1"

    def test_get_user(self):
        u = User(id="U1", name="Alice")
        li = LinkedIdentity()
        li.add("slack", "U1", u)
        assert li.get_user("slack") is u
        assert li.get_user("discord") is None


class TestIdentityMapperRegistration:
    """Tests for backend registration."""

    def test_register_and_list(self):
        mapper = IdentityMapper()
        b1 = FakeBackend("slack")
        b2 = FakeBackend("symphony")
        mapper.register_backend("slack", b1)
        mapper.register_backend("symphony", b2)
        assert sorted(mapper.backends) == ["slack", "symphony"]

    def test_empty_mapper(self):
        mapper = IdentityMapper()
        assert mapper.backends == []
        assert mapper.identities == []


class TestIdentityMapperLink:
    """Tests for manual linking."""

    def test_link_two_users(self):
        mapper = IdentityMapper()
        u1 = User(id="U1", name="Alice", email="alice@co.com")
        u2 = User(id="S1", name="Alice S", email="alice@co.com")
        identity = mapper.link(u1, u2, backends=["slack", "symphony"])
        assert identity.has_backend("slack")
        assert identity.has_backend("symphony")
        assert identity.email == "alice@co.com"
        assert len(mapper.identities) == 1

    def test_link_requires_two_users(self):
        mapper = IdentityMapper()
        u1 = User(id="U1")
        with pytest.raises(ValueError):
            mapper.link(u1, backends=["slack"])

    def test_link_merges_into_existing(self):
        mapper = IdentityMapper()
        u1 = User(id="U1", email="alice@co.com")
        u2 = User(id="S1", email="alice@co.com")
        u3 = User(id="D1", email="alice@co.com")
        mapper.link(u1, u2, backends=["slack", "symphony"])
        # Link a third user to an existing group via email match
        mapper.link(u1, u3, backends=["slack", "discord"])
        assert len(mapper.identities) == 1
        identity = mapper.identities[0]
        assert identity.has_backend("discord")
        assert identity.get_ref("discord") == "D1"

    def test_link_backends_mismatch_raises(self):
        mapper = IdentityMapper()
        u1 = User(id="U1")
        u2 = User(id="U2")
        with pytest.raises(ValueError):
            mapper.link(u1, u2, backends=["slack"])  # only 1 backend for 2 users

    def test_resolve_id_sync(self):
        mapper = IdentityMapper()
        u1 = User(id="U1", email="a@co.com")
        u2 = User(id="S1", email="a@co.com")
        mapper.link(u1, u2, backends=["slack", "symphony"])
        assert mapper.resolve_id(u1, source="slack", target="symphony") == "S1"
        assert mapper.resolve_id(u2, source="symphony", target="slack") == "U1"
        assert mapper.resolve_id(u1, source="slack", target="discord") is None

    def test_get_identity(self):
        mapper = IdentityMapper()
        u1 = User(id="U1", email="a@co.com")
        u2 = User(id="S1", email="a@co.com")
        mapper.link(u1, u2, backends=["slack", "symphony"])
        identity = mapper.get_identity(u1, backend="slack")
        assert identity is not None
        assert identity.get_ref("symphony") == "S1"

    def test_get_identity_by_string_id(self):
        mapper = IdentityMapper()
        u1 = User(id="U1", email="a@co.com")
        u2 = User(id="S1", email="a@co.com")
        mapper.link(u1, u2, backends=["slack", "symphony"])
        identity = mapper.get_identity("U1", backend="slack")
        assert identity is not None

    def test_clear(self):
        mapper = IdentityMapper()
        u1 = User(id="U1", email="a@co.com")
        u2 = User(id="S1", email="a@co.com")
        mapper.link(u1, u2, backends=["slack", "symphony"])
        mapper.clear()
        assert mapper.identities == []
        assert mapper.resolve_id(u1, source="slack", target="symphony") is None


class TestIdentityMapperLinkByEmail:
    """Tests for auto-discovery via email."""

    def test_link_by_email_found_on_both(self):
        alice_slack = User(id="U1", name="Alice", email="alice@co.com")
        alice_sym = User(id="S1", name="Alice S", email="alice@co.com")
        slack = FakeBackend("slack", {"U1": alice_slack})
        symphony = FakeBackend("symphony", {"S1": alice_sym})

        mapper = IdentityMapper()
        mapper.register_backend("slack", slack)
        mapper.register_backend("symphony", symphony)

        identity = _run(mapper.link_by_email("alice@co.com"))
        assert identity is not None
        assert identity.get_ref("slack") == "U1"
        assert identity.get_ref("symphony") == "S1"

    def test_link_by_email_found_on_one(self):
        alice = User(id="U1", name="Alice", email="alice@co.com")
        slack = FakeBackend("slack", {"U1": alice})
        symphony = FakeBackend("symphony", {})

        mapper = IdentityMapper()
        mapper.register_backend("slack", slack)
        mapper.register_backend("symphony", symphony)

        identity = _run(mapper.link_by_email("alice@co.com"))
        assert identity is None  # not found on 2+ backends

    def test_link_by_email_not_found(self):
        mapper = IdentityMapper()
        mapper.register_backend("slack", FakeBackend("slack", {}))
        mapper.register_backend("symphony", FakeBackend("symphony", {}))
        identity = _run(mapper.link_by_email("nobody@co.com"))
        assert identity is None

    def test_link_by_email_idempotent(self):
        alice_slack = User(id="U1", email="alice@co.com")
        alice_sym = User(id="S1", email="alice@co.com")
        mapper = IdentityMapper()
        mapper.register_backend("slack", FakeBackend("slack", {"U1": alice_slack}))
        mapper.register_backend("symphony", FakeBackend("symphony", {"S1": alice_sym}))

        id1 = _run(mapper.link_by_email("alice@co.com"))
        id2 = _run(mapper.link_by_email("alice@co.com"))
        assert id1 is id2
        assert len(mapper.identities) == 1

    def test_link_all_by_email(self):
        mapper = IdentityMapper()
        mapper.register_backend(
            "slack",
            FakeBackend(
                "slack",
                {
                    "U1": User(id="U1", email="a@co.com"),
                    "U2": User(id="U2", email="b@co.com"),
                },
            ),
        )
        mapper.register_backend(
            "sym",
            FakeBackend(
                "sym",
                {
                    "S1": User(id="S1", email="a@co.com"),
                },
            ),
        )
        results = _run(mapper.link_all_by_email(["a@co.com", "b@co.com"]))
        # Only a@co.com is on both
        assert len(results) == 1
        assert results[0].get_ref("slack") == "U1"


class TestIdentityMapperResolve:
    """Tests for async resolution."""

    def test_resolve_from_cache(self):
        alice_slack = User(id="U1", name="Alice", email="alice@co.com")
        alice_sym = User(id="S1", name="Alice S", email="alice@co.com")

        mapper = IdentityMapper()
        mapper.register_backend("slack", FakeBackend("slack", {"U1": alice_slack}))
        mapper.register_backend("symphony", FakeBackend("symphony", {"S1": alice_sym}))
        mapper.link(alice_slack, alice_sym, backends=["slack", "symphony"])

        result = _run(mapper.resolve(alice_slack, source="slack", target="symphony"))
        assert result is not None
        assert result.id == "S1"

    def test_resolve_discovers_by_email(self):
        alice_slack = User(id="U1", name="Alice", email="alice@co.com")
        alice_sym = User(id="S1", name="Alice S", email="alice@co.com")

        mapper = IdentityMapper()
        mapper.register_backend("slack", FakeBackend("slack", {"U1": alice_slack}))
        mapper.register_backend("symphony", FakeBackend("symphony", {"S1": alice_sym}))
        # NOT pre-linked

        result = _run(mapper.resolve(alice_slack, source="slack", target="symphony"))
        assert result is not None
        assert result.id == "S1"

    def test_resolve_not_found(self):
        mapper = IdentityMapper()
        mapper.register_backend("slack", FakeBackend("slack", {}))
        mapper.register_backend("symphony", FakeBackend("symphony", {}))

        u = User(id="U999", name="Nobody")
        result = _run(mapper.resolve(u, source="slack", target="symphony"))
        assert result is None

    def test_resolve_by_string_id(self):
        alice_slack = User(id="U1", name="Alice", email="alice@co.com")
        alice_sym = User(id="S1", name="Alice S", email="alice@co.com")

        mapper = IdentityMapper()
        mapper.register_backend("slack", FakeBackend("slack", {"U1": alice_slack}))
        mapper.register_backend("symphony", FakeBackend("symphony", {"S1": alice_sym}))
        mapper.link(alice_slack, alice_sym, backends=["slack", "symphony"])

        result = _run(mapper.resolve("U1", source="slack", target="symphony"))
        assert result is not None
        assert result.id == "S1"


class TestMessageBridge:
    """Tests for message forwarding."""

    def _make_backends(self):
        alice_slack = User(id="U1", name="Alice", email="alice@co.com")
        alice_sym = User(id="S1", name="Alice Symphony", email="alice@co.com")
        bob_slack = User(id="U2", name="Bob", email="bob@co.com")
        bob_sym = User(id="S2", name="Bob Symphony", email="bob@co.com")

        slack = FakeBackend(
            "slack",
            {
                "U1": alice_slack,
                "U2": bob_slack,
            },
        )
        symphony = FakeBackend(
            "symphony",
            {
                "S1": alice_sym,
                "S2": bob_sym,
            },
        )

        mapper = IdentityMapper()
        mapper.register_backend("slack", slack)
        mapper.register_backend("symphony", symphony)
        mapper.link(alice_slack, alice_sym, backends=["slack", "symphony"])
        mapper.link(bob_slack, bob_sym, backends=["slack", "symphony"])

        return slack, symphony, mapper

    def test_forward_simple_text(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
        )

        msg = Message(
            id="msg1",
            content="Hello world",
            author=User(id="U1", name="Alice"),
            channel=Channel(id="C1"),
            backend="slack",
        )

        result = _run(bridge.forward(msg))
        assert result is not None
        assert len(symphony.sent) == 1
        assert "Hello world" in symphony.sent[0]["content"]

    def test_forward_with_attribution(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=True,
        )

        msg = Message(
            id="msg1",
            content="Test message",
            author=User(id="U1", name="Alice"),
            channel=Channel(id="C1"),
            backend="slack",
        )

        _run(bridge.forward(msg))
        sent_content = symphony.sent[0]["content"]
        assert "Alice" in sent_content
        assert "slack" in sent_content

    def test_forward_without_attribution(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msg = Message(
            id="msg1",
            content="Test message",
            author=User(id="U1", name="Alice"),
            channel=Channel(id="C1"),
            backend="slack",
        )

        _run(bridge.forward(msg))
        assert "via slack" not in symphony.sent[0]["content"]

    def test_forward_translates_slack_mentions(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msg = Message(
            id="msg1",
            content="Hello <@U2>, check this out",
            author=User(id="U1", name="Alice"),
            channel=Channel(id="C1"),
            backend="slack",
        )

        _run(bridge.forward(msg))
        sent = symphony.sent[0]["content"]
        # The mention should be translated to Symphony format
        assert '<mention uid="S2"/>' in sent
        assert "<@U2>" not in sent

    def test_forward_unresolved_mention_becomes_text(self):
        slack, symphony, mapper = self._make_backends()
        # Add a user that's on Slack but NOT linked to Symphony
        slack._users["U99"] = User(id="U99", name="Charlie")

        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msg = Message(
            id="msg1",
            content="Hey <@U99>!",
            channel=Channel(id="C1"),
            backend="slack",
        )

        _run(bridge.forward(msg))
        sent = symphony.sent[0]["content"]
        # Should fall back to @DisplayName text
        assert "@Charlie" in sent

    def test_forward_explicit_channel(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
        )

        msg = Message(
            id="msg1",
            content="Hi",
            channel=Channel(id="C1"),
            backend="slack",
        )

        _run(bridge.forward(msg, to_channel="explicit_stream"))
        assert symphony.sent[0]["channel"] == "explicit_stream"

    def test_forward_no_channel_returns_none(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
        )

        msg = Message(id="msg1", content="Hi", backend="slack")
        result = _run(bridge.forward(msg))
        assert result is None
        assert len(symphony.sent) == 0

    def test_forward_with_attachments(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msg = Message(
            id="msg1",
            content="See attached",
            channel=Channel(id="C1"),
            backend="slack",
            attachments=[
                Attachment(filename="report.pdf", url="https://example.com/report.pdf"),
            ],
        )

        _run(bridge.forward(msg))
        assert "attachments" in symphony.sent[0]
        assert len(symphony.sent[0]["attachments"]) == 1
        assert symphony.sent[0]["attachments"][0].filename == "report.pdf"

    def test_forward_with_embeds(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msg = Message(
            id="msg1",
            content="Status",
            channel=Channel(id="C1"),
            backend="slack",
            embeds=[Embed(title="Bot Status", description="All good")],
        )

        _run(bridge.forward(msg))
        assert "embeds" in symphony.sent[0]
        assert symphony.sent[0]["embeds"][0].title == "Bot Status"

    def test_forward_without_attachments(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msg = Message(
            id="msg1",
            content="Text only",
            channel=Channel(id="C1"),
            backend="slack",
            attachments=[Attachment(filename="skip.txt")],
        )

        _run(bridge.forward(msg, include_attachments=False))
        assert "attachments" not in symphony.sent[0]

    def test_forward_many(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msgs = [Message(id=f"msg{i}", content=f"Message {i}", channel=Channel(id="C1"), backend="slack") for i in range(3)]

        results = _run(bridge.forward_many(msgs))
        assert len(results) == 3
        assert len(symphony.sent) == 3

    def test_forward_no_mapper_preserves_mentions_as_text(self):
        slack = FakeBackend("slack", {})
        discord = FakeBackend("discord", {})

        bridge = MessageBridge(
            source=slack,
            dest=discord,
            source_name="slack",
            dest_name="discord",
            channels={"C1": "D1"},
            attribution=False,
        )

        msg = Message(
            id="msg1",
            content="Hey <@U123> check this",
            channel=Channel(id="C1"),
            backend="slack",
        )

        _run(bridge.forward(msg))
        # Without a mapper, mentions pass through as plain text
        assert "<@U123>" in discord.sent[0]["content"]

    def test_custom_attribution_format(self):
        slack, symphony, mapper = self._make_backends()
        bridge = MessageBridge(
            source=slack,
            dest=symphony,
            source_name="Slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=True,
            attribution_format="[{source}] {name}: ",
        )

        msg = Message(
            id="msg1",
            content="Hello",
            author=User(id="U1", name="Alice"),
            channel=Channel(id="C1"),
            backend="slack",
        )

        _run(bridge.forward(msg))
        assert "[Slack] Alice: " in symphony.sent[0]["content"]


class TestMessageBridgeMentionPatterns:
    """Tests for mention translation across backends."""

    def _make_bridge(self, source_name, dest_name):
        # Use platform-conformant IDs so mention regexes match
        src_id = _platform_id(source_name, 1)
        dst_id = _platform_id(dest_name, 1)
        u1_src = User(id=src_id, name="Alice", email="alice@co.com")
        u1_dst = User(id=dst_id, name="Alice Dest", email="alice@co.com")

        src = FakeBackend(source_name, {src_id: u1_src})
        dst = FakeBackend(dest_name, {dst_id: u1_dst})

        mapper = IdentityMapper()
        mapper.register_backend(source_name, src)
        mapper.register_backend(dest_name, dst)
        mapper.link(u1_src, u1_dst, backends=[source_name, dest_name])

        bridge = MessageBridge(
            source=src,
            dest=dst,
            source_name=source_name,
            dest_name=dest_name,
            identity_mapper=mapper,
            channels={"C1": "D1"},
            attribution=False,
        )
        return bridge, src, dst

    def test_slack_to_discord_mention(self):
        bridge, _, dst = self._make_bridge("slack", "discord")
        src_id = _platform_id("slack", 1)
        dst_id = _platform_id("discord", 1)
        msg = Message(id="m1", content=f"Hi <@{src_id}>!", channel=Channel(id="C1"), backend="slack")
        _run(bridge.forward(msg))
        assert f"<@{dst_id}>" in dst.sent[0]["content"]

    def test_slack_to_symphony_mention(self):
        bridge, _, dst = self._make_bridge("slack", "symphony")
        src_id = _platform_id("slack", 1)
        dst_id = _platform_id("symphony", 1)
        msg = Message(id="m1", content=f"Hi <@{src_id}>!", channel=Channel(id="C1"), backend="slack")
        _run(bridge.forward(msg))
        assert f'<mention uid="{dst_id}"/>' in dst.sent[0]["content"]

    def test_discord_to_slack_mention(self):
        bridge, _, dst = self._make_bridge("discord", "slack")
        # Discord mentions use numeric IDs
        u1_src = User(id="123456", name="Alice", email="alice@co.com")
        u1_dst = User(id="UDST1", name="Alice Slack", email="alice@co.com")
        bridge.source._users = {"123456": u1_src}
        bridge.dest._users = {"UDST1": u1_dst}
        bridge.mapper.clear()
        bridge.mapper.link(u1_src, u1_dst, backends=["discord", "slack"])

        msg = Message(id="m1", content="Hey <@123456> look", channel=Channel(id="C1"), backend="discord")
        _run(bridge.forward(msg))
        assert "<@UDST1>" in dst.sent[0]["content"]

    def test_multiple_mentions_in_one_message(self):
        u1 = User(id="U1", name="Alice", email="a@co.com")
        u2 = User(id="U2", name="Bob", email="b@co.com")
        s1 = User(id="S1", name="Alice S", email="a@co.com")
        s2 = User(id="S2", name="Bob S", email="b@co.com")

        slack = FakeBackend("slack", {"U1": u1, "U2": u2})
        sym = FakeBackend("symphony", {"S1": s1, "S2": s2})

        mapper = IdentityMapper()
        mapper.register_backend("slack", slack)
        mapper.register_backend("symphony", sym)
        mapper.link(u1, s1, backends=["slack", "symphony"])
        mapper.link(u2, s2, backends=["slack", "symphony"])

        bridge = MessageBridge(
            source=slack,
            dest=sym,
            source_name="slack",
            dest_name="symphony",
            identity_mapper=mapper,
            channels={"C1": "stream_1"},
            attribution=False,
        )

        msg = Message(
            id="m1",
            content="<@U1> and <@U2> please review",
            channel=Channel(id="C1"),
            backend="slack",
        )
        _run(bridge.forward(msg))
        sent = sym.sent[0]["content"]
        assert '<mention uid="S1"/>' in sent
        assert '<mention uid="S2"/>' in sent
        assert "please review" in sent

    def test_text_with_no_mentions(self):
        bridge, _, dst = self._make_bridge("slack", "symphony")
        msg = Message(id="m1", content="Just plain text", channel=Channel(id="C1"), backend="slack")
        _run(bridge.forward(msg))
        assert "Just plain text" in dst.sent[0]["content"]
