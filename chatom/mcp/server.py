"""Build a FastMCP server from chatom backends.

Each backend's operations become MCP tools.  When multiple backends are
served, tool names are prefixed with the backend name
(e.g. ``slack__read_channel_history``).
"""

from __future__ import annotations

from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from chatom.agent.toolset import resolve_history_bounds
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
    enabled_tools: Optional[set[str]] = None,
    disabled_tools: Optional[set[str]] = None,
) -> None:
    """Register MCP tools for a single backend.

    Whether a tool is exposed is decided by, in order:

    1. ``read_only`` — write tools are omitted when True.
    2. The backend's declared capabilities (e.g. ``editing`` for
       ``edit_message``).
    3. ``enabled_tools`` — an optional allow-list. When given, only the
       listed (unprefixed) tool names are registered.
    4. ``disabled_tools`` — a deny-list that always wins, even over the
       allow-list and capabilities.
    """

    caps = backend.capabilities
    disabled = disabled_tools or set()

    def _name(base: str) -> str:
        return f"{prefix}__{base}" if prefix else base

    def _has(cap: Capability) -> bool:
        return caps.supports(cap) if caps else True

    def _enabled(base: str) -> bool:
        if base in disabled:
            return False
        if enabled_tools is not None and base not in enabled_tools:
            return False
        return True

    def _tool(base: str, *, cap: Optional[Capability] = None, write: bool = False, available: bool = True):
        """Register the decorated function as an MCP tool when all gates pass.

        The gates are evaluated up-front so disabled tools are never
        registered with the server (and therefore never advertised).
        """

        def decorator(fn: Any) -> Any:
            if write and read_only:
                return fn
            if not available:
                return fn
            if cap is not None and not _has(cap):
                return fn
            if not _enabled(base):
                return fn
            mcp.tool(name=_name(base))(fn)
            return fn

        return decorator

    _attachments_ok = _has(Capability.FILES) or _has(Capability.IMAGES)

    @_tool("read_channel_history")
    async def read_channel_history(
        channel: ChannelRef = Field(description="Channel to read messages from."),
        limit: int = Field(default=50, description="Maximum messages, newest first (1-200).", ge=1, le=200),
        last_minutes: Optional[int] = Field(default=None, description="Only messages from the last N minutes (e.g. 30).", ge=1),
        after: Optional[str] = Field(default=None, description="Only messages at/after this ISO-8601 UTC timestamp."),
        before: Optional[str] = Field(default=None, description="Only messages at/before this ISO-8601 UTC timestamp."),
    ) -> list[dict[str, Any]]:
        """Read message history from a chat channel, newest-first."""
        after_dt, before_dt = resolve_history_bounds(after, before, last_minutes)
        msgs = await backend.fetch_messages(channel=channel.to_channel(), limit=limit, after=after_dt, before=before_dt)
        return _serialize(msgs)

    @_tool("search_messages", cap=Capability.MESSAGE_SEARCH)
    async def search_messages(
        query: str = Field(description="Search query string."),
        channel: Optional[ChannelRef] = Field(default=None, description="Optional channel to limit search to."),
        limit: int = Field(default=20, description="Maximum results (1-100).", ge=1, le=100),
    ) -> list[dict[str, Any]]:
        """Search for messages matching a text query."""
        ch = channel.to_channel() if channel else None
        msgs = await backend.search_messages(query=query, channel=ch, limit=limit)
        return _serialize(msgs)

    @_tool("lookup_user")
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

    @_tool("lookup_channel")
    async def lookup_channel(
        channel: ChannelRef = Field(description="Channel to look up."),
    ) -> Optional[dict[str, Any]]:
        """Look up a channel by ID or name."""
        ch = channel.to_channel()
        result = await backend.lookup_channel(id=ch.id or None, name=ch.name or None)
        return _serialize(result)

    @_tool("get_channel_members")
    async def get_channel_members(
        channel: ChannelRef = Field(description="Channel to get members for."),
    ) -> list[dict[str, Any]]:
        """Get the list of members in a channel."""
        members = await backend.fetch_channel_members(channel.to_channel())
        return _serialize(members)

    @_tool("get_bot_info")
    async def get_bot_info() -> Optional[dict[str, Any]]:
        """Get the bot's own user profile (id, name, handle).

        Useful for self-identification — e.g. checking whether a message
        was authored by, or mentions, the bot.
        """
        return _serialize(await backend.get_bot_info())

    @_tool("get_presence", cap=Capability.PRESENCE)
    async def get_presence(
        user: UserRef = Field(description="User to look up presence for. Provide at least one identifier."),
    ) -> Optional[dict[str, Any]]:
        """Get a user's presence/status (online, away, etc.)."""
        u = user.to_user()
        return _serialize(await backend.get_presence(u.id or u))

    @_tool("list_recent_attachments", available=_attachments_ok)
    async def list_recent_attachments(
        channel: ChannelRef = Field(description="Channel to scan for attachments."),
        limit: int = Field(default=20, description="Number of recent messages to scan (1-100).", ge=1, le=100),
    ) -> list[dict[str, Any]]:
        """List files, images, and documents on recent messages in a channel.

        Returns each attachment's id, filename, content_type, size and the
        message_id it belongs to. Use this before downloading.
        """
        messages = await backend.fetch_messages(channel=channel.to_channel(), limit=limit)
        result: list[dict[str, Any]] = []
        for msg in messages or []:
            msg_id = getattr(msg, "id", "") or ""
            for att in getattr(msg, "attachments", None) or []:
                result.append(
                    {
                        "attachment_id": getattr(att, "id", "") or "",
                        "filename": getattr(att, "filename", "") or "",
                        "content_type": getattr(att, "content_type", "") or "",
                        "size": getattr(att, "size", None),
                        "message_id": msg_id,
                    }
                )
        return result

    @_tool("download_attachment", available=_attachments_ok)
    async def download_attachment(
        attachment_id: str = Field(description="ID of the attachment (from list_recent_attachments)."),
        channel: ChannelRef = Field(description="Channel the attachment was posted in."),
        message_id: Optional[str] = Field(default=None, description="Message ID the attachment belongs to (required by some backends)."),
        max_bytes: int = Field(default=5_000_000, description="Maximum bytes to return (1-20MB).", ge=1, le=20_000_000),
    ) -> dict[str, Any]:
        """Download an attachment's content, returned base64-encoded."""
        import base64

        messages = await backend.fetch_messages(channel=channel.to_channel(), limit=100)
        found_att = None
        found_msg = None
        for msg in messages or []:
            if message_id and (getattr(msg, "id", "") or "") != message_id:
                continue
            for att in getattr(msg, "attachments", None) or []:
                if (getattr(att, "id", "") or "") == attachment_id:
                    found_att = att
                    found_msg = msg
                    break
            if found_att is not None:
                break

        if found_att is None:
            return {"error": "not_found", "message": f"No attachment '{attachment_id}' found in recent history."}

        data = await backend.download_attachment(found_att, message=found_msg)
        if len(data) > max_bytes:
            return {"error": "too_large", "message": f"Attachment is {len(data)} bytes (limit {max_bytes}).", "size": len(data)}

        return {
            "filename": getattr(found_att, "filename", "") or "",
            "content_type": getattr(found_att, "content_type", "") or "",
            "size": len(data),
            "data_base64": base64.b64encode(data).decode("ascii"),
        }

    @_tool("send_message", write=True)
    async def send_message(
        channel: ChannelRef = Field(description="Channel to send the message to."),
        content: str = Field(description="Message content to send."),
    ) -> dict[str, Any]:
        """Send a message to a channel."""
        result = await backend.send_message(channel=channel.to_channel(), content=content)
        return _serialize(result)

    @_tool("edit_message", cap=Capability.EDITING, write=True)
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

    @_tool("add_reaction", cap=Capability.EMOJI_REACTIONS, write=True)
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

    @_tool("remove_reaction", cap=Capability.EMOJI_REACTIONS, write=True)
    async def remove_reaction(
        message_id: str = Field(description="ID of the message to remove a reaction from."),
        emoji: str = Field(description="Emoji name or unicode character to remove."),
        channel: ChannelRef = Field(description="Channel containing the message."),
    ) -> dict[str, str]:
        """Remove an emoji reaction previously added to a message."""
        await backend.remove_reaction(
            message=message_id,
            emoji=emoji,
            channel=channel.to_channel(),
        )
        return {"ok": "true"}

    @_tool("delete_message", cap=Capability.DELETING, write=True)
    async def delete_message(
        message_id: str = Field(description="ID of the message to delete."),
        channel: ChannelRef = Field(description="Channel containing the message."),
    ) -> dict[str, str]:
        """Delete a message. Irreversible — disabled by default."""
        await backend.delete_message(message=message_id, channel=channel.to_channel())
        return {"ok": "true"}

    @_tool("set_presence", cap=Capability.PRESENCE, write=True)
    async def set_presence(
        status: str = Field(description="Presence status (e.g. 'available', 'away', 'busy')."),
        status_text: str = Field(default="", description="Optional custom status text."),
    ) -> dict[str, str]:
        """Set the bot's own presence/status."""
        await backend.set_presence(status, status_text or None)
        return {"ok": "true"}

    @_tool("upload_file", write=True, available=_attachments_ok)
    async def upload_file(
        channel: ChannelRef = Field(description="Channel to upload the file to."),
        filename: str = Field(description="Name of the file including extension (e.g. 'chart.png')."),
        data_base64: str = Field(description="The file content, base64-encoded."),
        content_type: str = Field(default="", description="MIME type. Inferred from filename if omitted."),
        content: str = Field(default="", description="Optional accompanying message text."),
    ) -> dict[str, Any]:
        """Upload a file, image, or document to a channel."""
        import base64
        import binascii

        try:
            data = base64.b64decode(data_base64, validate=True)
        except (binascii.Error, ValueError) as e:
            return {"error": "invalid_data", "message": f"data_base64 is not valid base64: {e}"}

        ct = content_type
        if not ct:
            import mimetypes

            ct = mimetypes.guess_type(filename)[0] or ""

        sent = await backend.upload_file(
            channel=channel.to_channel(),
            data=data,
            filename=filename,
            content_type=ct,
            content=content,
        )
        return {"ok": True, "message_id": getattr(sent, "id", "") or ""}


def build_mcp_server(
    backends: dict[str, BackendBase],
    *,
    name: str = "chatom",
    read_only: bool = False,
    enabled_tools: Optional[set[str]] = None,
    disabled_tools: Optional[set[str]] = None,
) -> FastMCP:
    """Build a FastMCP server from one or more chatom backends.

    Args:
        backends: Map of backend name to instance (e.g. ``{"slack": slack_backend}``).
        name: Server name shown to MCP clients.
        read_only: If True, omit write tools (send, edit, react, etc.).
        enabled_tools: Optional allow-list of (unprefixed) tool names. When
            given, only these tools are registered, subject to capability and
            ``read_only`` gating. ``None`` means "all tools".
        disabled_tools: Optional deny-list of (unprefixed) tool names that are
            never registered, even if otherwise available. Useful for omitting
            destructive tools such as ``delete_message``.

    Returns:
        A configured :class:`FastMCP` server ready to run.
    """
    mcp = FastMCP(name)
    single = len(backends) == 1
    for bname, backend in backends.items():
        prefix = "" if single else bname
        _register_backend_tools(
            mcp,
            backend,
            prefix=prefix,
            read_only=read_only,
            enabled_tools=enabled_tools,
            disabled_tools=disabled_tools,
        )
    return mcp
