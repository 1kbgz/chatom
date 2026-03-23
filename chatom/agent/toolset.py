from __future__ import annotations

from typing import Any, Optional, cast

from pydantic import BaseModel as PydanticBaseModel, Field, TypeAdapter
from pydantic_ai._run_context import RunContext
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets.abstract import AbstractToolset, ToolsetTool

from chatom.backend import BackendBase
from chatom.base import Channel, User
from chatom.base.capabilities import Capability


class ChannelRef(PydanticBaseModel):
    """Partial channel reference.  Provide at least ``id`` or ``name``."""

    id: Optional[str] = Field(default=None, description="Channel ID.")
    name: Optional[str] = Field(default=None, description="Channel name.")

    def to_channel(self) -> Channel:
        """Construct a chatom :class:`Channel` for backend resolution."""
        return Channel(id=self.id or "", name=self.name or "")


class UserRef(PydanticBaseModel):
    """Partial user reference.  Provide at least one identifier."""

    id: Optional[str] = Field(default=None, description="User ID.")
    name: Optional[str] = Field(default=None, description="User display name.")
    email: Optional[str] = Field(default=None, description="User email address.")
    handle: Optional[str] = Field(default=None, description="User handle / username.")

    def to_user(self) -> User:
        """Construct a chatom :class:`User` for backend resolution."""
        return User(
            id=self.id or "",
            name=self.name or "",
            email=self.email or "",
            handle=self.handle or "",
        )


class ReadChannelHistoryParams(PydanticBaseModel):
    """Parameters for reading message history from a channel."""

    channel: ChannelRef = Field(description="Channel to read messages from. Provide at least channel ID or name.")
    limit: int = Field(default=50, description="Maximum number of messages to fetch (1-200).", ge=1, le=200)


class SearchMessagesParams(PydanticBaseModel):
    """Parameters for searching messages."""

    query: str = Field(description="Search query string.")
    channel: Optional[ChannelRef] = Field(default=None, description="Optional channel to limit search to.")
    limit: int = Field(default=20, description="Maximum number of results (1-100).", ge=1, le=100)


class LookupUserParams(PydanticBaseModel):
    """Parameters for looking up a user.  Provide at least one identifier."""

    user: UserRef = Field(description="User to look up. Provide at least one of: id, name, email, handle.")


class LookupChannelParams(PydanticBaseModel):
    """Parameters for looking up a channel.  Provide at least one identifier."""

    channel: ChannelRef = Field(description="Channel to look up. Provide at least id or name.")


class GetChannelMembersParams(PydanticBaseModel):
    """Parameters for getting channel members."""

    channel: ChannelRef = Field(description="Channel to get members for.")


class SendMessageParams(PydanticBaseModel):
    """Parameters for sending a message."""

    channel: ChannelRef = Field(description="Channel to send the message to.")
    content: str = Field(description="Message content to send.")


class EditMessageParams(PydanticBaseModel):
    """Parameters for editing a message."""

    message_id: str = Field(description="ID of the message to edit.")
    content: str = Field(description="New message content.")
    channel: ChannelRef = Field(description="Channel containing the message.")


class AddReactionParams(PydanticBaseModel):
    """Parameters for adding a reaction."""

    message_id: str = Field(description="ID of the message to react to.")
    emoji: str = Field(description="Emoji name or unicode character to add.")
    channel: ChannelRef = Field(description="Channel containing the message.")


_TOOL_DESCRIPTORS: list[dict[str, Any]] = [
    {
        "name": "read_channel_history",
        "description": (
            "Read recent message history from a chat channel. "
            "Returns messages ordered oldest-to-newest. "
            "Each message includes the author, content, timestamp, and ID."
        ),
        "params_model": ReadChannelHistoryParams,
        "capability": None,  # always available
        "write": False,
    },
    {
        "name": "search_messages",
        "description": (
            "Search for messages matching a text query across channels. Returns matching messages with their channel, author, and content."
        ),
        "params_model": SearchMessagesParams,
        "capability": Capability.MESSAGE_SEARCH,
        "write": False,
    },
    {
        "name": "lookup_user",
        "description": (
            "Look up a chat user by their ID, name, email, or handle. "
            "Returns the user's profile including display name, email, and avatar. "
            "At least one identifier must be provided."
        ),
        "params_model": LookupUserParams,
        "capability": None,
        "write": False,
    },
    {
        "name": "lookup_channel",
        "description": (
            "Look up a chat channel by its ID or name. "
            "Returns the channel's metadata including name, topic, and type. "
            "At least one identifier must be provided."
        ),
        "params_model": LookupChannelParams,
        "capability": None,
        "write": False,
    },
    {
        "name": "get_channel_members",
        "description": ("Get the list of users who are members of a channel. Returns user profiles for all channel members."),
        "params_model": GetChannelMembersParams,
        "capability": None,
        "write": False,
    },
    {
        "name": "send_message",
        "description": ("Send a new message to a chat channel. The content should be plain text; formatting is handled automatically."),
        "params_model": SendMessageParams,
        "capability": None,
        "write": True,
    },
    {
        "name": "edit_message",
        "description": "Edit an existing message's content.",
        "params_model": EditMessageParams,
        "capability": Capability.EDITING,
        "write": True,
    },
    {
        "name": "add_reaction",
        "description": ("Add an emoji reaction to a message. Use this to acknowledge messages (e.g. '👀' for seen, '✅' for done)."),
        "params_model": AddReactionParams,
        "capability": Capability.EMOJI_REACTIONS,
        "write": True,
    },
]


def _serialize_result(obj: Any) -> Any:
    """Convert backend return values to JSON-safe dicts."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return [_serialize_result(item) for item in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_none=True)
    return str(obj)


class BackendToolset(AbstractToolset[Any]):
    """Expose a chatom :class:`BackendBase` as a pydantic-ai toolset.

    Tools are derived dynamically from the backend's declared
    :class:`~chatom.base.capabilities.BackendCapabilities`.  Write tools
    (``send_message``, ``edit_message``, ``add_reaction``) are omitted
    when *read_only* is ``True``.

    Example::

        from chatom.agent import BackendToolset
        from pydantic_ai import Agent

        toolset = BackendToolset(backend=slack_backend)
        agent = Agent("anthropic:claude-sonnet-4-6", toolsets=[toolset])
        result = await agent.run("Summarize the last 20 messages in #general")
    """

    def __init__(
        self,
        backend: BackendBase,
        *,
        read_only: bool = False,
        max_retries: int = 1,
    ) -> None:
        self._backend = backend
        self._read_only = read_only
        self._max_retries = max_retries

    @property
    def id(self) -> str | None:
        return f"chatom-{self._backend.name}" if self._backend.name else "chatom"

    async def get_tools(self, ctx: RunContext[Any]) -> dict[str, ToolsetTool[Any]]:
        tools: dict[str, ToolsetTool[Any]] = {}
        for desc in _TOOL_DESCRIPTORS:
            if not self._should_include(desc):
                continue
            params_model = desc["params_model"]
            adapter = TypeAdapter(params_model)
            tool_def = ToolDefinition(
                name=desc["name"],
                description=desc["description"],
                parameters_json_schema=adapter.json_schema(),
            )
            tools[desc["name"]] = ToolsetTool(
                toolset=self,
                tool_def=tool_def,
                max_retries=self._max_retries,
                args_validator=cast(Any, adapter.validator),
            )
        return tools

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, Any],
        ctx: RunContext[Any],
        tool: ToolsetTool[Any],
    ) -> Any:
        handler = getattr(self, f"_call_{name}", None)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        result = await handler(tool_args)
        return _serialize_result(result)

    def _should_include(self, desc: dict[str, Any]) -> bool:
        """Decide whether a tool descriptor should be exposed."""
        if desc["write"] and self._read_only:
            return False
        cap = desc.get("capability")
        if cap is not None and self._backend.capabilities:
            if not self._backend.capabilities.supports(cap):
                return False
        return True

    @staticmethod
    def _channel(args: dict[str, Any], key: str = "channel") -> Channel:
        """Extract a ChannelRef from args and convert to a chatom Channel."""
        ref = args[key]
        if isinstance(ref, ChannelRef):
            return ref.to_channel()
        # Already validated by Pydantic — dict input
        return ChannelRef.model_validate(ref).to_channel()

    @staticmethod
    def _user(args: dict[str, Any], key: str = "user") -> User:
        """Extract a UserRef from args and convert to a chatom User."""
        ref = args[key]
        if isinstance(ref, UserRef):
            return ref.to_user()
        return UserRef.model_validate(ref).to_user()

    async def _call_read_channel_history(self, args: dict[str, Any]) -> Any:
        return await self._backend.fetch_messages(
            channel=self._channel(args),
            limit=args.get("limit", 50),
        )

    async def _call_search_messages(self, args: dict[str, Any]) -> Any:
        ch = self._channel(args) if args.get("channel") else None
        return await self._backend.search_messages(
            query=args["query"],
            channel=ch,
            limit=args.get("limit", 20),
        )

    async def _call_lookup_user(self, args: dict[str, Any]) -> Any:
        user = self._user(args)
        return await self._backend.lookup_user(
            id=user.id or None,
            name=user.name or None,
            email=user.email or None,
            handle=user.handle or None,
        )

    async def _call_lookup_channel(self, args: dict[str, Any]) -> Any:
        ch = self._channel(args)
        return await self._backend.lookup_channel(
            id=ch.id or None,
            name=ch.name or None,
        )

    async def _call_get_channel_members(self, args: dict[str, Any]) -> Any:
        return await self._backend.fetch_channel_members(self._channel(args))

    async def _call_send_message(self, args: dict[str, Any]) -> Any:
        return await self._backend.send_message(
            channel=self._channel(args),
            content=args["content"],
        )

    async def _call_edit_message(self, args: dict[str, Any]) -> Any:
        return await self._backend.edit_message(
            message=args["message_id"],
            content=args["content"],
            channel=self._channel(args),
        )

    async def _call_add_reaction(self, args: dict[str, Any]) -> Any:
        await self._backend.add_reaction(
            message=args["message_id"],
            emoji=args["emoji"],
            channel=self._channel(args),
        )
        return {"ok": True}
