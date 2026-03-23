"""Tests for the chatom.agent subpackage."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pytest

from chatom.backend import BackendBase
from chatom.base import Channel, Message, User
from chatom.base.capabilities import (
    SLACK_CAPABILITIES,
    BackendCapabilities,
    Capability,
)


class _MockBackend(BackendBase):
    """Minimal BackendBase subclass for toolset tests.

    Implements the abstract methods plus the additional methods that
    BackendToolset dispatches to, without pulling in any platform SDK.
    """

    name = "mock"
    display_name = "Mock"

    # Internal storage — set after construction via _configure()
    _users: Dict[str, User] = {}
    _channels: Dict[str, Channel] = {}
    _messages: Dict[str, List[Message]] = {}
    sent: list = []
    edited: list = []
    reactions: list = []

    def _configure(
        self,
        *,
        capabilities: Optional[BackendCapabilities] = None,
        users: Optional[Dict[str, User]] = None,
        channels: Optional[Dict[str, Channel]] = None,
        messages: Optional[Dict[str, List[Message]]] = None,
    ) -> "_MockBackend":
        """Populate the mock with test data. Returns self for chaining."""
        if capabilities is not None:
            self.capabilities = capabilities
        self._users = users or {}
        self._channels = channels or {}
        self._messages = messages or {}
        self.sent = []
        self.edited = []
        self.reactions = []
        return self

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def fetch_user(
        self,
        identifier: Optional[Union[str, User]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        uid = id or (identifier if isinstance(identifier, str) else (identifier.id if identifier else None))
        if uid:
            return self._users.get(uid)
        for u in self._users.values():
            if name and u.name == name:
                return u
        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        cid = id or (identifier if isinstance(identifier, str) else (identifier.id if identifier else None))
        if cid:
            return self._channels.get(cid)
        for c in self._channels.values():
            if name and c.name == name:
                return c
        return None

    async def fetch_messages(
        self,
        channel: Union[str, Channel],
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        ch_id = channel if isinstance(channel, str) else channel.id
        msgs = self._messages.get(ch_id, [])
        if not msgs and isinstance(channel, Channel) and channel.name:
            for c in self._channels.values():
                if c.name == channel.name:
                    msgs = self._messages.get(c.id, [])
                    break
        return msgs[:limit]

    async def send_message(
        self,
        channel: Union[str, Channel],
        content: str,
        **kwargs: Any,
    ) -> Message:
        ch_id = channel if isinstance(channel, str) else channel.id
        self.sent.append({"channel": ch_id, "content": content})
        return Message(id="sent_1", content=content, channel=Channel(id=ch_id))

    async def search_messages(
        self,
        query: str,
        channel: Optional[Union[str, Channel]] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Message]:
        results: list[Message] = []
        for ch_msgs in self._messages.values():
            for m in ch_msgs:
                if query.lower() in (m.content or "").lower():
                    results.append(m)
        return results[:limit]

    async def fetch_channel_members(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[User]:
        return list(self._users.values())

    async def edit_message(
        self,
        message: Union[str, Message],
        content: str,
        channel: Optional[Union[str, Channel]] = None,
        **kwargs: Any,
    ) -> Message:
        msg_id = message if isinstance(message, str) else message.id
        ch_id = channel if isinstance(channel, str) else (channel.id if channel else "")
        self.edited.append({"message_id": msg_id, "content": content, "channel": ch_id})
        return Message(id=msg_id, content=content)

    async def add_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        msg_id = message if isinstance(message, str) else message.id
        ch_id = channel if isinstance(channel, str) else (channel.id if channel else "")
        self.reactions.append({"message_id": msg_id, "emoji": emoji, "channel": ch_id})


@pytest.fixture
def alice() -> User:
    return User(id="U1", name="Alice", display_name="Alice A")


@pytest.fixture
def general() -> Channel:
    return Channel(id="C1", name="general", topic="General discussion")


@pytest.fixture
def sample_messages(alice: User, general: Channel) -> List[Message]:
    return [
        Message(
            id="m1",
            content="Hello world",
            author=alice,
            channel=general,
            created_at=datetime(2026, 3, 23, 10, 0),
        ),
        Message(
            id="m2",
            content="How is everyone?",
            author=alice,
            channel=general,
            created_at=datetime(2026, 3, 23, 10, 5),
        ),
    ]


@pytest.fixture
def mock_backend(alice: User, general: Channel, sample_messages: List[Message]) -> _MockBackend:
    return _MockBackend(capabilities=SLACK_CAPABILITIES)._configure(
        users={"U1": alice},
        channels={"C1": general},
        messages={"C1": sample_messages},
    )


@pytest.fixture
def readonly_backend(mock_backend: _MockBackend) -> _MockBackend:
    """Same data, but used with read_only=True."""
    return mock_backend


class TestBackendToolset:
    """Tests for BackendToolset."""

    @pytest.mark.asyncio
    async def test_get_tools_returns_all_tools(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.retries = {}
        tools = await toolset.get_tools(ctx)

        expected_names = {
            "read_channel_history",
            "search_messages",
            "lookup_user",
            "lookup_channel",
            "get_channel_members",
            "send_message",
            "edit_message",
            "add_reaction",
        }
        assert set(tools.keys()) == expected_names

    @pytest.mark.asyncio
    async def test_read_only_omits_write_tools(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend, read_only=True)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.retries = {}
        tools = await toolset.get_tools(ctx)

        write_tools = {"send_message", "edit_message", "add_reaction"}
        assert write_tools.isdisjoint(set(tools.keys()))
        assert "read_channel_history" in tools
        assert "lookup_user" in tools

    @pytest.mark.asyncio
    async def test_capability_gating(self) -> None:
        """Backend without MESSAGE_SEARCH should not expose search_messages."""
        from chatom.agent.toolset import BackendToolset

        caps = BackendCapabilities(
            capabilities=frozenset({Capability.PLAINTEXT}),
        )
        backend = _MockBackend(capabilities=caps)
        toolset = BackendToolset(backend, read_only=True)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.retries = {}
        tools = await toolset.get_tools(ctx)

        assert "search_messages" not in tools
        assert "edit_message" not in tools
        assert "add_reaction" not in tools
        assert "read_channel_history" in tools
        assert "lookup_user" in tools

    @pytest.mark.asyncio
    async def test_id_property(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        assert toolset.id == "chatom-mock"

    @pytest.mark.asyncio
    async def test_call_read_channel_history(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        tool = MagicMock()
        result = await toolset.call_tool(
            "read_channel_history",
            {"channel": {"id": "C1"}, "limit": 10},
            ctx,
            tool,
        )
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_call_lookup_user(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        tool = MagicMock()
        result = await toolset.call_tool(
            "lookup_user",
            {"user": {"id": "U1"}},
            ctx,
            tool,
        )
        assert result["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_call_lookup_user_not_found(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        tool = MagicMock()
        result = await toolset.call_tool(
            "lookup_user",
            {"user": {"id": "U999"}},
            ctx,
            tool,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_call_send_message(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        tool = MagicMock()
        result = await toolset.call_tool(
            "send_message",
            {"channel": {"id": "C1"}, "content": "Hello from agent"},
            ctx,
            tool,
        )
        assert result["content"] == "Hello from agent"
        assert mock_backend.sent[0]["content"] == "Hello from agent"

    @pytest.mark.asyncio
    async def test_call_add_reaction(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        tool = MagicMock()
        result = await toolset.call_tool(
            "add_reaction",
            {"message_id": "m1", "emoji": "thumbsup", "channel": {"id": "C1"}},
            ctx,
            tool,
        )
        assert result == {"ok": True}
        assert mock_backend.reactions[0]["emoji"] == "thumbsup"

    @pytest.mark.asyncio
    async def test_call_unknown_tool_raises(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        tool = MagicMock()
        with pytest.raises(ValueError, match="Unknown tool"):
            await toolset.call_tool("nonexistent", {}, ctx, tool)

    @pytest.mark.asyncio
    async def test_tool_definitions_have_json_schemas(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.toolset import BackendToolset

        toolset = BackendToolset(mock_backend)
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx.retries = {}
        tools = await toolset.get_tools(ctx)
        for name, tool in tools.items():
            schema = tool.tool_def.parameters_json_schema
            assert "properties" in schema, f"{name} schema missing 'properties'"
            assert tool.tool_def.description, f"{name} missing description"


class TestChannelContext:
    """Tests for ChannelContext and build_channel_context."""

    @pytest.mark.asyncio
    async def test_build_channel_context(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.context import build_channel_context

        ctx = await build_channel_context(mock_backend, "C1", limit=10)
        assert ctx.channel_id == "C1"
        assert ctx.channel_name == "general"
        assert len(ctx.messages) == 2
        assert "Alice A" in ctx.participants

    @pytest.mark.asyncio
    async def test_build_channel_context_by_name(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.context import build_channel_context

        ctx = await build_channel_context(mock_backend, "general", limit=10)
        assert ctx.channel_name == "general"

    @pytest.mark.asyncio
    async def test_format_for_llm(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.context import build_channel_context

        ctx = await build_channel_context(mock_backend, "C1")
        text = ctx.format_for_llm()
        assert "#general" in text
        assert "Alice" in text
        assert "Hello world" in text
        assert "How is everyone?" in text
        assert "2026-03-23 10:00" in text

    @pytest.mark.asyncio
    async def test_token_budget_truncation(self, mock_backend: _MockBackend) -> None:
        from chatom.agent.context import build_channel_context

        ctx = await build_channel_context(
            mock_backend,
            "C1",
            token_budget=10,
        )
        assert len(ctx.messages) < 2

    @pytest.mark.asyncio
    async def test_empty_channel(self) -> None:
        from chatom.agent.context import build_channel_context

        backend = _MockBackend(capabilities=SLACK_CAPABILITIES)._configure(
            channels={"C2": Channel(id="C2", name="empty")},
        )
        ctx = await build_channel_context(backend, "C2")
        assert ctx.channel_name == "empty"
        assert len(ctx.messages) == 0
        assert len(ctx.participants) == 0
