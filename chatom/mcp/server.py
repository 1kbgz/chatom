"""Build a FastMCP server from chatom backends.

Each backend's operations become MCP tools.  When multiple backends are
served, tool names are prefixed with the backend name
(e.g. ``slack__read_channel_history``).
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from chatom.backend import BackendBase
from chatom.base import Channel, User
from chatom.base.capabilities import Capability

__all__ = ("build_mcp_server",)


class ChannelRef(BaseModel):
    """Partial channel reference.  Provide at least ``id`` or ``name``."""

    id: Optional[str] = Field(default=None, description="Channel ID.")
    name: Optional[str] = Field(default=None, description="Channel name.")

    def to_channel(self) -> Channel:
        return Channel(id=self.id or "", name=self.name or "")


class UserRef(BaseModel):
    """Partial user reference.  Provide at least one identifier."""

    id: Optional[str] = Field(default=None, description="User ID.")
    name: Optional[str] = Field(default=None, description="User display name.")
    email: Optional[str] = Field(default=None, description="User email address.")
    handle: Optional[str] = Field(default=None, description="User handle / username.")

    def to_user(self) -> User:
        return User(
            id=self.id or "",
            name=self.name or "",
            email=self.email or "",
            handle=self.handle or "",
        )


def _serialize(obj: Any) -> Any:
    """Convert backend return values to JSON-safe structures."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_none=True)
    return str(obj)


def _register_backend_tools(
    mcp: FastMCP,
    backend: BackendBase,
    *,
    prefix: str = "",
    read_only: bool = False,
) -> None:
    """Register MCP tools for a single backend."""

    caps = backend.capabilities

    def _name(base: str) -> str:
        return f"{prefix}__{base}" if prefix else base

    def _has(cap: Capability) -> bool:
        return caps.supports(cap) if caps else True

    @mcp.tool(name=_name("read_channel_history"))
    async def read_channel_history(
        channel: ChannelRef = Field(description="Channel to read messages from."),
        limit: int = Field(default=50, description="Maximum messages (1-200).", ge=1, le=200),
    ) -> list[dict[str, Any]]:
        """Read recent message history from a chat channel."""
        msgs = await backend.fetch_messages(channel=channel.to_channel(), limit=limit)
        return _serialize(msgs)

    if _has(Capability.MESSAGE_SEARCH):

        @mcp.tool(name=_name("search_messages"))
        async def search_messages(
            query: str = Field(description="Search query string."),
            channel: Optional[ChannelRef] = Field(default=None, description="Optional channel to limit search to."),
            limit: int = Field(default=20, description="Maximum results (1-100).", ge=1, le=100),
        ) -> list[dict[str, Any]]:
            """Search for messages matching a text query."""
            ch = channel.to_channel() if channel else None
            msgs = await backend.search_messages(query=query, channel=ch, limit=limit)
            return _serialize(msgs)

    @mcp.tool(name=_name("lookup_user"))
    async def lookup_user(
        user: UserRef = Field(description="User to look up. Provide at least one identifier."),
    ) -> Optional[dict[str, Any]]:
        """Look up a chat user by ID, name, email, or handle."""
        u = user.to_user()
        result = await backend.lookup_user(
            id=u.id or None,
            name=u.name or None,
            email=u.email or None,
            handle=u.handle or None,
        )
        return _serialize(result)

    @mcp.tool(name=_name("lookup_channel"))
    async def lookup_channel(
        channel: ChannelRef = Field(description="Channel to look up."),
    ) -> Optional[dict[str, Any]]:
        """Look up a channel by ID or name."""
        ch = channel.to_channel()
        result = await backend.lookup_channel(id=ch.id or None, name=ch.name or None)
        return _serialize(result)

    @mcp.tool(name=_name("get_channel_members"))
    async def get_channel_members(
        channel: ChannelRef = Field(description="Channel to get members for."),
    ) -> list[dict[str, Any]]:
        """Get the list of members in a channel."""
        members = await backend.fetch_channel_members(channel.to_channel())
        return _serialize(members)

    if not read_only:

        @mcp.tool(name=_name("send_message"))
        async def send_message(
            channel: ChannelRef = Field(description="Channel to send the message to."),
            content: str = Field(description="Message content to send."),
        ) -> dict[str, Any]:
            """Send a message to a channel."""
            result = await backend.send_message(channel=channel.to_channel(), content=content)
            return _serialize(result)

        if _has(Capability.EDITING):

            @mcp.tool(name=_name("edit_message"))
            async def edit_message(
                message_id: str = Field(description="ID of the message to edit."),
                content: str = Field(description="New message content."),
                channel: ChannelRef = Field(description="Channel containing the message."),
            ) -> dict[str, Any]:
                """Edit an existing message."""
                result = await backend.edit_message(
                    message=message_id,
                    content=content,
                    channel=channel.to_channel(),
                )
                return _serialize(result)

        if _has(Capability.EMOJI_REACTIONS):

            @mcp.tool(name=_name("add_reaction"))
            async def add_reaction(
                message_id: str = Field(description="ID of the message to react to."),
                emoji: str = Field(description="Emoji name or unicode character."),
                channel: ChannelRef = Field(description="Channel containing the message."),
            ) -> dict[str, str]:
                """Add an emoji reaction to a message."""
                await backend.add_reaction(
                    message=message_id,
                    emoji=emoji,
                    channel=channel.to_channel(),
                )
                return {"ok": "true"}


def build_mcp_server(
    backends: dict[str, BackendBase],
    *,
    name: str = "chatom",
    read_only: bool = False,
) -> FastMCP:
    """Build a FastMCP server from one or more chatom backends.

    Args:
        backends: Map of backend name to instance (e.g. ``{"slack": slack_backend}``).
        name: Server name shown to MCP clients.
        read_only: If True, omit write tools (send, edit, react).

    Returns:
        A configured :class:`FastMCP` server ready to run.
    """
    mcp = FastMCP(name)
    single = len(backends) == 1
    for bname, backend in backends.items():
        prefix = "" if single else bname
        _register_backend_tools(mcp, backend, prefix=prefix, read_only=read_only)
    return mcp
