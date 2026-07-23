"""Tests for the chatom-mcp server."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from fastmcp import Client

from chatom.base import Channel, Image, Message, User
from chatom.base.capabilities import (
    SLACK_CAPABILITIES,
    BackendCapabilities,
    Capability,
)
from chatom.mcp import build_mcp_server


class _MockBackend:
    """Bare-bones BackendBase stand-in for MCP server tests."""

    name = "mock"
    display_name = "Mock"

    def __init__(
        self,
        capabilities: BackendCapabilities | None = None,
        users: dict[str, User] | None = None,
        channels: dict[str, Channel] | None = None,
        messages: dict[str, list[Message]] | None = None,
    ) -> None:
        self.capabilities = capabilities or SLACK_CAPABILITIES
        self._users = users or {}
        self._channels = channels or {}
        self._messages = messages or {}
        self.sent: list[dict[str, Any]] = []
        self.reactions: list[dict[str, Any]] = []
        self.uploaded: list[dict[str, Any]] = []
        self.removed_reactions: list[dict[str, Any]] = []
        self.deleted: list[dict[str, Any]] = []
        self.presence_set: list[dict[str, Any]] = []

    async def fetch_messages(
        self,
        channel: str | Channel,
        limit: int = 100,
        before: str | None = None,
        after: str | None = None,
    ) -> list[Message]:
        ch_id = channel if isinstance(channel, str) else channel.id
        return self._messages.get(ch_id, [])[:limit]

    async def search_messages(
        self,
        query: str,
        channel: str | Channel | None = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> list[Message]:
        results: list[Message] = []
        for ch_msgs in self._messages.values():
            for m in ch_msgs:
                if query.lower() in (m.content or "").lower():
                    results.append(m)
        return results[:limit]

    async def lookup_user(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
        email: str | None = None,
        handle: str | None = None,
    ) -> User | None:
        if id:
            return self._users.get(id)
        for u in self._users.values():
            if name and u.name == name:
                return u
        return None

    async def lookup_channel(
        self,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> Channel | None:
        if id:
            return self._channels.get(id)
        for c in self._channels.values():
            if name and c.name == name:
                return c
        return None

    async def fetch_channel_members(
        self,
        identifier: str | Channel | None = None,
        *,
        id: str | None = None,
        name: str | None = None,
    ) -> list[User]:
        return list(self._users.values())

    async def send_message(
        self,
        channel: str | Channel,
        content: str,
        **kwargs: Any,
    ) -> Message:
        ch_id = channel if isinstance(channel, str) else channel.id
        self.sent.append({"channel": ch_id, "content": content})
        return Message(id="sent_1", content=content, channel=Channel(id=ch_id))

    async def edit_message(
        self,
        message: str | Message,
        content: str,
        channel: str | Channel | None = None,
        **kwargs: Any,
    ) -> Message:
        msg_id = message if isinstance(message, str) else message.id
        return Message(id=msg_id, content=content)

    async def add_reaction(
        self,
        message: str | Message,
        emoji: str,
        channel: str | Channel | None = None,
    ) -> None:
        msg_id = message if isinstance(message, str) else message.id
        ch_id = channel if isinstance(channel, str) else (channel.id if channel else "")
        self.reactions.append({"message_id": msg_id, "emoji": emoji, "channel": ch_id})

    async def upload_file(
        self,
        channel: str | Channel,
        data: bytes,
        filename: str = "file",
        content_type: str = "",
        title: str = "",
        content: str = "",
        **kwargs: Any,
    ) -> Message:
        ch_id = channel if isinstance(channel, str) else channel.id
        self.uploaded.append({"channel": ch_id, "data": data, "filename": filename, "content_type": content_type})
        return Message(id="uploaded_1", content=content, channel=Channel(id=ch_id))

    async def download_attachment(self, attachment: Any, *, message: Message | None = None) -> bytes:
        if attachment.data is not None:
            return attachment.data
        return f"bytes:{getattr(attachment, 'id', '')}".encode()

    async def get_bot_info(self) -> User | None:
        return User(id="BOT1", name="Test Bot", handle="testbot")

    async def get_presence(self, user: str | User) -> Any:
        uid = user if isinstance(user, str) else user.id
        return {"user_id": uid, "status": "available"}

    async def remove_reaction(
        self,
        message: str | Message,
        emoji: str,
        channel: str | Channel | None = None,
    ) -> None:
        msg_id = message if isinstance(message, str) else message.id
        ch_id = channel if isinstance(channel, str) else (channel.id if channel else "")
        self.removed_reactions.append({"message_id": msg_id, "emoji": emoji, "channel": ch_id})

    async def delete_message(
        self,
        message: str | Message,
        channel: str | Channel | None = None,
    ) -> None:
        msg_id = message if isinstance(message, str) else message.id
        ch_id = channel if isinstance(channel, str) else (channel.id if channel else "")
        self.deleted.append({"message_id": msg_id, "channel": ch_id})

    async def set_presence(self, status: str, status_text: str | None = None, **kwargs: Any) -> None:
        self.presence_set.append({"status": status, "status_text": status_text})


@pytest.fixture
def alice() -> User:
    return User(id="U1", name="Alice", display_name="Alice A")


@pytest.fixture
def general() -> Channel:
    return Channel(id="C1", name="general", topic="General discussion")


@pytest.fixture
def sample_messages(alice: User, general: Channel) -> list[Message]:
    return [
        Message(
            id="m1",
            content="Hello world",
            author=alice,
            channel=general,
            timestamp=datetime(2026, 3, 23, 10, 0),  # noqa: DTZ001
        ),
        Message(
            id="m2",
            content="How is everyone?",
            author=alice,
            channel=general,
            timestamp=datetime(2026, 3, 23, 10, 5),  # noqa: DTZ001
        ),
    ]


@pytest.fixture
def mock_backend(alice: User, general: Channel, sample_messages: list[Message]) -> _MockBackend:
    return _MockBackend(
        users={"U1": alice},
        channels={"C1": general},
        messages={"C1": sample_messages},
    )


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
            assert "remove_reaction" not in tool_names
            assert "delete_message" not in tool_names
            assert "set_presence" not in tool_names
            assert "upload_file" not in tool_names
            assert "read_channel_history" in tool_names
            # Read-side tools remain available in read-only mode.
            assert "list_recent_attachments" in tool_names
            assert "download_attachment" in tool_names
            assert "get_bot_info" in tool_names
            assert "get_presence" in tool_names

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
            # get_bot_info has no capability requirement — always available.
            assert "get_bot_info" in tool_names
            # No PRESENCE/DELETING/EMOJI capability → those tools are gated off.
            assert "get_presence" not in tool_names
            assert "set_presence" not in tool_names
            assert "delete_message" not in tool_names
            assert "remove_reaction" not in tool_names
            # No FILES/IMAGES capability → attachment tools are gated off.
            assert "list_recent_attachments" not in tool_names
            assert "download_attachment" not in tool_names
            assert "upload_file" not in tool_names

    @pytest.mark.asyncio
    async def test_attachment_tools_present_with_files(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "list_recent_attachments" in tool_names
            assert "download_attachment" in tool_names
            assert "upload_file" in tool_names

    @pytest.mark.asyncio
    async def test_new_tools_present_with_slack_caps(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "get_bot_info" in tool_names
            assert "get_presence" in tool_names
            assert "remove_reaction" in tool_names
            assert "delete_message" in tool_names
            assert "set_presence" in tool_names

    @pytest.mark.asyncio
    async def test_disabled_tools_denylist(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend}, disabled_tools={"delete_message", "set_presence"})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "delete_message" not in tool_names
            assert "set_presence" not in tool_names
            # Other tools remain.
            assert "remove_reaction" in tool_names
            assert "send_message" in tool_names

    @pytest.mark.asyncio
    async def test_enabled_tools_allowlist(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend}, enabled_tools={"read_channel_history", "get_bot_info"})
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert tool_names == {"read_channel_history", "get_bot_info"}

    @pytest.mark.asyncio
    async def test_disabled_wins_over_enabled(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server(
            {"mock": mock_backend},
            enabled_tools={"read_channel_history", "delete_message"},
            disabled_tools={"delete_message"},
        )
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert "read_channel_history" in tool_names
            assert "delete_message" not in tool_names


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
    async def test_get_bot_info(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            result = await client.call_tool("get_bot_info", {})
            data = result.data if hasattr(result, "data") and result.data is not None else result
            assert data["id"] == "BOT1"
            assert data["handle"] == "testbot"

    @pytest.mark.asyncio
    async def test_remove_reaction(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            _ = await client.call_tool(
                "remove_reaction",
                {"message_id": "m1", "emoji": "thumbsup", "channel": {"id": "C1"}},
            )
            assert mock_backend.removed_reactions[0]["emoji"] == "thumbsup"

    @pytest.mark.asyncio
    async def test_delete_message(self, mock_backend: _MockBackend) -> None:
        # delete_message must be explicitly enabled (off in the shipped config).
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            _ = await client.call_tool(
                "delete_message",
                {"message_id": "m1", "channel": {"id": "C1"}},
            )
            assert mock_backend.deleted[0]["message_id"] == "m1"

    @pytest.mark.asyncio
    async def test_set_presence(self, mock_backend: _MockBackend) -> None:
        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            _ = await client.call_tool("set_presence", {"status": "away", "status_text": "brb"})
            assert mock_backend.presence_set[0] == {"status": "away", "status_text": "brb"}

    @pytest.mark.asyncio
    async def test_upload_file(self, mock_backend: _MockBackend) -> None:
        import base64

        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            payload = base64.b64encode(b"PNGDATA").decode("ascii")
            _ = await client.call_tool(
                "upload_file",
                {"channel": {"id": "C1"}, "filename": "out.png", "data_base64": payload},
            )
            assert mock_backend.uploaded[0]["data"] == b"PNGDATA"
            assert mock_backend.uploaded[0]["filename"] == "out.png"
            assert mock_backend.uploaded[0]["content_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_list_and_download_attachment(self, mock_backend: _MockBackend) -> None:
        import base64

        mock_backend._messages["C1"][0].attachments = [Image(id="att1", filename="pic.png", content_type="image/png")]

        mcp = build_mcp_server({"mock": mock_backend})
        async with Client(mcp) as client:
            listed = await client.call_tool("list_recent_attachments", {"channel": {"id": "C1"}})
            items = listed.structured_content["result"]
            assert any(a["attachment_id"] == "att1" for a in items)

            got = await client.call_tool(
                "download_attachment",
                {"attachment_id": "att1", "channel": {"id": "C1"}},
            )
            got_data = got.data if hasattr(got, "data") and got.data is not None else got
            assert base64.b64decode(got_data["data_base64"]) == b"bytes:att1"

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
