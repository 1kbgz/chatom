"""Tests for the chatom-mcp server."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pytest
from fastmcp import Client

from chatom.base import Channel, Message, User
from chatom.base.capabilities import (
    SLACK_CAPABILITIES,
    BackendCapabilities,
    Capability,
)
from chatom.mcp import build_mcp_server

# ---------------------------------------------------------------------------
# Minimal mock backend (same pattern as chatom/tests/test_agent.py)
# ---------------------------------------------------------------------------


class _MockBackend:
    """Bare-bones BackendBase stand-in for MCP server tests."""

    name = "mock"
    display_name = "Mock"

    def __init__(
        self,
        capabilities: Optional[BackendCapabilities] = None,
        users: Optional[Dict[str, User]] = None,
        channels: Optional[Dict[str, Channel]] = None,
        messages: Optional[Dict[str, List[Message]]] = None,
    ) -> None:
        self.capabilities = capabilities or SLACK_CAPABILITIES
        self._users = users or {}
        self._channels = channels or {}
        self._messages = messages or {}
        self.sent: list[dict[str, Any]] = []
        self.reactions: list[dict[str, Any]] = []

    async def fetch_messages(
        self,
        channel: Union[str, Channel],
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        ch_id = channel if isinstance(channel, str) else channel.id
        return self._messages.get(ch_id, [])[:limit]

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

    async def lookup_user(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        if id:
            return self._users.get(id)
        for u in self._users.values():
            if name and u.name == name:
                return u
        return None

    async def lookup_channel(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        if id:
            return self._channels.get(id)
        for c in self._channels.values():
            if name and c.name == name:
                return c
        return None

    async def fetch_channel_members(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[User]:
        return list(self._users.values())

    async def send_message(
        self,
        channel: Union[str, Channel],
        content: str,
        **kwargs: Any,
    ) -> Message:
        ch_id = channel if isinstance(channel, str) else channel.id
        self.sent.append({"channel": ch_id, "content": content})
        return Message(id="sent_1", content=content, channel=Channel(id=ch_id))

    async def edit_message(
        self,
        message: Union[str, Message],
        content: str,
        channel: Optional[Union[str, Channel]] = None,
        **kwargs: Any,
    ) -> Message:
        msg_id = message if isinstance(message, str) else message.id
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
            timestamp=datetime(2026, 3, 23, 10, 0),
        ),
        Message(
            id="m2",
            content="How is everyone?",
            author=alice,
            channel=general,
            timestamp=datetime(2026, 3, 23, 10, 5),
        ),
    ]


@pytest.fixture
def mock_backend(alice: User, general: Channel, sample_messages: List[Message]) -> _MockBackend:
    return _MockBackend(
        users={"U1": alice},
        channels={"C1": general},
        messages={"C1": sample_messages},
    )


# ---------------------------------------------------------------------------
# Server builder tests
# ---------------------------------------------------------------------------


class TestBuildMcpServer:
    """Tests for build_mcp_server via the Client (avoids accessing internals)."""

    @pytest.mark.asyncio
    async def test_single_backend_no_prefix(self, mock_backend: _MockBackend) -> None:

        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "read_channel_history" in tool_names
            assert "mock__read_channel_history" not in tool_names

    @pytest.mark.asyncio
    async def test_multi_backend_prefixed(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"slack": mock_backend, "discord": mock_backend})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "slack__read_channel_history" in tool_names
            assert "discord__read_channel_history" in tool_names
            assert "read_channel_history" not in tool_names

    @pytest.mark.asyncio
    async def test_read_only_omits_write_tools(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend}, read_only=True)
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "send_message" not in tool_names
            assert "edit_message" not in tool_names
            assert "add_reaction" not in tool_names
            assert "read_channel_history" in tool_names

    @pytest.mark.asyncio
    async def test_capability_gating(self) -> None:
        caps = BackendCapabilities(capabilities=frozenset({Capability.PLAINTEXT}))
        backend = _MockBackend(capabilities=caps)
        mcp = build_mcp_server({"test": backend})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "search_messages" not in tool_names
            assert "edit_message" not in tool_names
            assert "add_reaction" not in tool_names
            assert "read_channel_history" in tool_names


# ---------------------------------------------------------------------------
# MCP Client integration tests
# ---------------------------------------------------------------------------


class TestMcpClientIntegration:
    """Test tools via FastMCP Client (in-process, no subprocess)."""

    @pytest.mark.asyncio
    async def test_list_tools(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert "read_channel_history" in names
            assert "lookup_user" in names
            assert "send_message" in names

    @pytest.mark.asyncio
    async def test_read_channel_history(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            result = await client.call_tool(
                "read_channel_history",
                {"channel": {"id": "C1"}, "limit": 10},
            )
            # Result is a list of message dicts
            data = result.data if hasattr(result, "data") and result.data is not None else result
            assert isinstance(data, list)
            assert len(data) == 2

    @pytest.mark.asyncio
    async def test_lookup_user(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            result = await client.call_tool(
                "lookup_user",
                {"user": {"id": "U1"}},
            )
            data = result.data if hasattr(result, "data") and result.data is not None else result
            assert data["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_send_message(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            _ = await client.call_tool(
                "send_message",
                {"channel": {"id": "C1"}, "content": "Hello from MCP"},
            )
            assert mock_backend.sent[0]["content"] == "Hello from MCP"

    @pytest.mark.asyncio
    async def test_add_reaction(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            _ = await client.call_tool(
                "add_reaction",
                {"message_id": "m1", "emoji": "thumbsup", "channel": {"id": "C1"}},
            )
            assert mock_backend.reactions[0]["emoji"] == "thumbsup"

    @pytest.mark.asyncio
    async def test_search_messages(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            result = await client.call_tool(
                "search_messages",
                {"query": "hello"},
            )
            data = result.data if hasattr(result, "data") and result.data is not None else result
            assert isinstance(data, list)
            assert len(data) == 1  # Only "Hello world" matches

    @pytest.mark.asyncio
    async def test_prefixed_tools_multi_backend(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"slack": mock_backend, "discord": mock_backend})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {t.name for t in tools}
            assert "slack__read_channel_history" in names
            assert "discord__read_channel_history" in names

            # Call a prefixed tool
            result = await client.call_tool(
                "slack__lookup_user",
                {"user": {"id": "U1"}},
            )
            data = result.data if hasattr(result, "data") and result.data is not None else result
            assert data["name"] == "Alice"
