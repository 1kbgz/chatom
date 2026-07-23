from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from pydantic import BaseModel as PydanticBaseModel, Field, TypeAdapter
from pydantic_ai._run_context import RunContext
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets.abstract import AbstractToolset, ToolsetTool

from chatom.backend import BackendBase
from chatom.base import Channel, ChannelType, User
from chatom.base.capabilities import Capability

logger = logging.getLogger(__name__)


def resolve_history_bounds(
    after: Any = None,
    before: Any = None,
    last_minutes: Any = None,
) -> tuple[datetime | None, datetime | None]:
    """Resolve history-range args to an ``(after, before)`` datetime pair.

    ``after``/``before`` may be ISO-8601 strings (``Z`` accepted); ``last_minutes``
    is a convenience lower bound of *now* minus N minutes. Either result may be
    None. Shared by the agent toolset and the MCP server so both surfaces expose
    identical range semantics.
    """

    def _parse(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        dt = datetime.fromisoformat(str(value).strip())
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

    after_dt = _parse(after)
    before_dt = _parse(before)
    if last_minutes:
        window_start = datetime.now(UTC) - timedelta(minutes=int(last_minutes))
        after_dt = window_start if after_dt is None else max(after_dt, window_start)
    return after_dt, before_dt


class AccessDeniedError(Exception):
    """Raised when a tool call is denied by the access policy."""


class ToolBudgetExceededError(Exception):
    """Raised when a tool call exceeds the per-run or per-tool call budget."""


@dataclass
class AccessPolicy:
    """Configures what the agent is allowed to access on behalf of a user.

    All checks are enforced *before* calling the backend — the agent cannot
    bypass these regardless of prompt injection.

    Attributes:
        requesting_user: The user who invoked the command. Required for
            membership checks.
        invoking_channel_id: The channel where the command was issued. Used
            when ``restrict_to_invoking_channel`` is True.
        restrict_to_invoking_channel: If True, the agent can only access
            messages from the channel where the command was invoked.
            Prevents cross-channel data exfiltration.
        require_membership: If True, verify the requesting user is a member
            of any channel the agent tries to read. This is the primary
            guardrail against reading rooms the user isn't in.
        block_dm_reads: If True, prevent the agent from reading DM/group
            channels. DMs often contain sensitive 1:1 conversations.
        allowed_channel_ids: If set, only these channel IDs can be accessed.
            Acts as an explicit whitelist. Takes precedence over membership
            checks (i.e. if set, only these are allowed regardless of
            membership).
        blocked_channel_ids: Channels that are never accessible, regardless
            of other settings. Useful for compliance/HR channels.
        history_visible_since: If set, messages older than this timestamp
            are filtered out. Use this to enforce "no pre-join history"
            policies — set to the user's join date.
        max_messages_per_request: Hard cap on messages returned per tool
            call, preventing bulk data extraction.
    """

    requesting_user: User | None = None
    invoking_channel_id: str | None = None
    restrict_to_invoking_channel: bool = False
    require_membership: bool = False
    block_dm_reads: bool = False
    allowed_channel_ids: set[str] | None = None
    blocked_channel_ids: set[str] = field(default_factory=set)
    history_visible_since: datetime | None = None
    max_messages_per_request: int = 200


class ChannelRef(PydanticBaseModel):
    """Partial channel reference.  Provide at least ``id`` or ``name``."""

    id: str | None = Field(default=None, description="Channel ID.")
    name: str | None = Field(default=None, description="Channel name.")

    def to_channel(self) -> Channel:
        """Construct a chatom :class:`Channel` for backend resolution."""
        return Channel(id=self.id or "", name=self.name or "")


class UserRef(PydanticBaseModel):
    """Partial user reference.  Provide at least one identifier."""

    id: str | None = Field(default=None, description="User ID.")
    name: str | None = Field(default=None, description="User display name.")
    email: str | None = Field(default=None, description="User email address.")
    handle: str | None = Field(default=None, description="User handle / username.")

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
    limit: int = Field(default=50, description="Maximum number of messages to return, newest first (1-200).", ge=1, le=200)
    last_minutes: int | None = Field(
        default=None,
        description="Only messages from the last N minutes (e.g. 30 for the last half hour). Use this for recency without needing the current time.",
        ge=1,
    )
    after: str | None = Field(
        default=None,
        description="Only messages at or after this ISO-8601 UTC timestamp (e.g. '2026-07-17T18:51:00Z'). Lower bound of a range.",
    )
    before: str | None = Field(
        default=None,
        description="Only messages at or before this ISO-8601 UTC timestamp. Upper bound of a range.",
    )


class SearchMessagesParams(PydanticBaseModel):
    """Parameters for searching messages."""

    query: str = Field(description="Search query string.")
    channel: ChannelRef | None = Field(default=None, description="Optional channel to limit search to.")
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


class ListAttachmentsParams(PydanticBaseModel):
    """Parameters for listing attachments in a channel's recent history."""

    channel: ChannelRef = Field(description="Channel to scan for attachments. Provide at least channel ID or name.")
    limit: int = Field(default=20, description="Number of recent messages to scan (1-100).", ge=1, le=100)


class DownloadAttachmentParams(PydanticBaseModel):
    """Parameters for downloading an attachment's content."""

    attachment_id: str = Field(description="ID of the attachment to download (from list_recent_attachments).")
    channel: ChannelRef = Field(description="Channel the attachment was posted in.")
    message_id: str | None = Field(
        default=None,
        description="ID of the message the attachment belongs to. Required by some backends (e.g. Symphony).",
    )
    max_bytes: int = Field(
        default=5_000_000,
        description="Maximum number of bytes to return (1-20MB). Larger files are rejected.",
        ge=1,
        le=20_000_000,
    )


class UploadFileParams(PydanticBaseModel):
    """Parameters for uploading a file/image to a channel."""

    channel: ChannelRef = Field(description="Channel to upload the file to.")
    filename: str = Field(description="Name of the file, including extension (e.g. 'chart.png').")
    data_base64: str = Field(description="The file content, base64-encoded.")
    content_type: str = Field(default="", description="MIME type of the file (e.g. 'image/png'). Inferred from filename if omitted.")
    content: str = Field(default="", description="Optional message text to accompany the file.")


class GetBotInfoParams(PydanticBaseModel):
    """Parameters for retrieving the bot's own profile (none required)."""


class GetPresenceParams(PydanticBaseModel):
    """Parameters for reading a user's presence."""

    user: UserRef = Field(description="User to read presence for. Provide at least one identifier.")


class RemoveReactionParams(PydanticBaseModel):
    """Parameters for removing a reaction."""

    message_id: str = Field(description="ID of the message to remove a reaction from.")
    emoji: str = Field(description="Emoji name or unicode character to remove.")
    channel: ChannelRef = Field(description="Channel containing the message.")


class DeleteMessageParams(PydanticBaseModel):
    """Parameters for deleting a message."""

    message_id: str = Field(description="ID of the message to delete.")
    channel: ChannelRef = Field(description="Channel containing the message.")


class SetPresenceParams(PydanticBaseModel):
    """Parameters for setting the bot's own presence."""

    status: str = Field(description="Presence status (e.g. 'available', 'away', 'busy').")
    status_text: str = Field(default="", description="Optional custom status text.")


_TOOL_DESCRIPTORS: list[dict[str, Any]] = [
    {
        "name": "read_channel_history",
        "description": (
            "Read message history from a chat channel. "
            "Returns messages ordered newest-to-oldest. "
            "Fetch the most recent messages by count with 'limit', a recent "
            "window with 'last_minutes' (e.g. 30), or a specific range with "
            "'after'/'before' ISO-8601 UTC timestamps. "
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
        "name": "get_bot_info",
        "description": (
            "Get the bot's own user profile (id, name, handle). Use this for "
            "self-identification — e.g. to tell whether a message was written by, "
            "or mentions, the bot itself."
        ),
        "params_model": GetBotInfoParams,
        "capability": None,
        "write": False,
    },
    {
        "name": "get_presence",
        "description": "Get a user's presence/status (online, away, busy, etc.).",
        "params_model": GetPresenceParams,
        "capability": Capability.PRESENCE,
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
    {
        "name": "remove_reaction",
        "description": "Remove an emoji reaction that was previously added to a message.",
        "params_model": RemoveReactionParams,
        "capability": Capability.EMOJI_REACTIONS,
        "write": True,
    },
    {
        "name": "delete_message",
        "description": "Delete a message. This is irreversible; use with care.",
        "params_model": DeleteMessageParams,
        "capability": Capability.DELETING,
        "write": True,
    },
    {
        "name": "set_presence",
        "description": "Set the bot's own presence/status (e.g. 'available', 'away').",
        "params_model": SetPresenceParams,
        "capability": Capability.PRESENCE,
        "write": True,
    },
    {
        "name": "list_recent_attachments",
        "description": (
            "List files, images, and documents attached to recent messages in a channel. "
            "Returns each attachment's id, filename, content_type, size, and the message_id "
            "it belongs to. Use this to discover attachments before downloading them."
        ),
        "params_model": ListAttachmentsParams,
        "capability": Capability.FILES,
        "write": False,
    },
    {
        "name": "download_attachment",
        "description": (
            "Download the content of an attachment (image or document) received in chat. "
            "Returns the bytes base64-encoded along with the filename and content_type. "
            "Use list_recent_attachments first to find the attachment_id."
        ),
        "params_model": DownloadAttachmentParams,
        "capability": Capability.FILES,
        "write": False,
    },
    {
        "name": "upload_file",
        "description": (
            "Upload a file, image, or document to a channel. Provide the content as "
            "base64-encoded data plus a filename. Use this to share generated images, "
            "charts, reports, or documents with the chat."
        ),
        "params_model": UploadFileParams,
        "capability": Capability.FILES,
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
        access_policy: AccessPolicy | None = None,
        disabled_tools: set[str] | None = None,
        max_tool_calls: int = 0,
        per_tool_limits: dict[str, int] | None = None,
    ) -> None:
        self._backend = backend
        self._read_only = read_only
        self._max_retries = max_retries
        self._policy = access_policy or AccessPolicy()
        self._disabled_tools = disabled_tools or set()
        # Per-run tool call budget. 0 disables the total cap; per-tool limits
        # may still apply. A single BackendToolset instance is expected to back
        # exactly one agent run, so these counters scope naturally to a run.
        self._max_tool_calls = max_tool_calls
        self._per_tool_limits = dict(per_tool_limits) if per_tool_limits else {}
        self._tool_calls_made = 0
        self._per_tool_calls: dict[str, int] = {}
        # Cache for membership checks to avoid repeated API calls
        self._membership_cache: dict[str, bool] = {}
        # Cache for channel resolution to avoid repeated name→ID lookups
        self._channel_cache: dict[str, Channel] = {}

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
        # Enforce the per-run / per-tool budget before doing any work. Return
        # the exhaustion as a tool result (not an exception) so the agent can
        # wrap up gracefully using what it has already gathered.
        try:
            self._enforce_budget(name)
        except ToolBudgetExceededError as e:
            logger.warning("Tool budget exceeded for '%s': %s", name, e)
            return {"error": "budget_exceeded", "message": str(e)}
        # Count this admitted call (denied/failed calls still consume budget,
        # so prompt injection cannot retry a blocked tool indefinitely).
        self._tool_calls_made += 1
        self._per_tool_calls[name] = self._per_tool_calls.get(name, 0) + 1
        # tool_args may be a validated Pydantic model — convert to dict
        if hasattr(tool_args, "model_dump"):
            tool_args = tool_args.model_dump()  # ty: ignore[call-non-callable]
        try:
            result = await handler(tool_args)
        except AccessDeniedError as e:
            # Return the denial as a tool result so the agent can inform the user
            # rather than crashing the entire run.
            logger.warning("Access denied for tool '%s': %s", name, e)
            return {"error": "access_denied", "message": str(e)}
        return _serialize_result(result)

    def _enforce_budget(self, name: str) -> None:
        """Raise ToolBudgetExceededError if this call would exceed a budget.

        Two independent limits are checked: a total per-run cap
        (``max_tool_calls``) and an optional per-tool cap from
        ``per_tool_limits``.  Either set to a falsy value disables that
        particular check.
        """
        if self._max_tool_calls and self._tool_calls_made >= self._max_tool_calls:
            raise ToolBudgetExceededError(
                f"Tool call budget exhausted ({self._max_tool_calls} calls used). "
                "Stop calling tools and answer using the information already gathered."
            )
        per_tool_limit = self._per_tool_limits.get(name)
        if per_tool_limit and self._per_tool_calls.get(name, 0) >= per_tool_limit:
            raise ToolBudgetExceededError(
                f"Per-tool budget for '{name}' exhausted ({per_tool_limit} calls used). Use the results already returned instead of calling it again."
            )

    def _should_include(self, desc: dict[str, Any]) -> bool:
        """Decide whether a tool descriptor should be exposed."""
        if desc["name"] in self._disabled_tools:
            return False
        if desc["write"] and self._read_only:
            return False
        cap = desc.get("capability")
        return not (cap is not None and self._backend.capabilities and not self._backend.capabilities.supports(cap))

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

    # ------------------------------------------------------------------
    # Access control enforcement
    # ------------------------------------------------------------------

    async def _check_channel_access(self, channel: Channel) -> None:
        """Enforce all access policy checks for a channel.

        Raises AccessDeniedError if the requesting user is not allowed to
        access the channel.
        """
        policy = self._policy
        channel_id = channel.id
        normalize = self._backend.normalize_channel_id
        norm_id = normalize(channel_id) if channel_id else channel_id

        # 1. Blocked channels — always denied
        if channel_id and norm_id in {normalize(c) for c in policy.blocked_channel_ids}:
            raise AccessDeniedError(f"Access to channel '{channel_id}' is blocked by policy.")

        # 2. Explicit whitelist — if set, only listed channels are allowed
        if policy.allowed_channel_ids is not None:
            if norm_id not in {normalize(c) for c in policy.allowed_channel_ids}:
                raise AccessDeniedError(f"Channel '{channel_id}' is not in the allowed channel list.")
            # If whitelisted, skip further checks (admin explicitly allowed)
            return

        # 3. Restrict to invoking channel
        if policy.restrict_to_invoking_channel and policy.invoking_channel_id:  # noqa: SIM102
            if channel_id and norm_id != normalize(policy.invoking_channel_id):
                raise AccessDeniedError(f"Access restricted to the invoking channel. Cannot read from channel '{channel.name or channel_id}'.")

        # 4. Block DM reads
        if policy.block_dm_reads:
            # Check if this is a DM by resolving channel info
            resolved = await self._resolve_channel_type(channel)
            if resolved in (ChannelType.DIRECT, ChannelType.GROUP):
                raise AccessDeniedError("Reading direct messages is blocked by policy.")

        # 5. Membership check
        if policy.require_membership:
            if not policy.requesting_user:
                raise AccessDeniedError("Membership verification required but no requesting user context available.")
            is_member = await self._check_membership(channel)
            if not is_member:
                raise AccessDeniedError(
                    f"User '{policy.requesting_user.name or policy.requesting_user.id}' is not a member of channel '{channel.name or channel_id}'."
                )

    async def _resolve_channel_full(self, channel: Channel) -> Channel:
        """Resolve a partial channel (name-only) to a full channel with ID.

        Results are cached for the lifetime of this toolset instance.
        """
        if channel.id:
            return channel
        cache_key = channel.name or ""
        if cache_key and cache_key in self._channel_cache:
            return self._channel_cache[cache_key]
        try:
            resolved = await self._backend.lookup_channel(
                id=channel.id or None,
                name=channel.name or None,
            )
            if resolved:
                if cache_key:
                    self._channel_cache[cache_key] = resolved
                return resolved
        except (NotImplementedError, Exception):  # noqa: BLE001, S110
            pass
        return channel

    async def _resolve_channel_type(self, channel: Channel) -> ChannelType:
        """Resolve the channel type, using backend lookup if needed."""
        if channel.channel_type != ChannelType.UNKNOWN:
            return channel.channel_type
        # Try resolving via _resolve_channel_full (uses cache)
        resolved = await self._resolve_channel_full(channel)
        if resolved is not channel and hasattr(resolved, "channel_type") and resolved.channel_type != ChannelType.UNKNOWN:
            return resolved.channel_type
        # Still unknown — do an explicit lookup by ID
        try:
            looked_up = await self._backend.lookup_channel(
                id=channel.id or None,
                name=channel.name or None,
            )
            if looked_up and hasattr(looked_up, "channel_type"):
                return looked_up.channel_type
        except (NotImplementedError, Exception):  # noqa: BLE001, S110
            pass
        return ChannelType.UNKNOWN

    async def _check_membership(self, channel: Channel) -> bool:
        """Check if the requesting user is a member of the channel.

        Results are cached for the lifetime of this toolset instance
        to avoid hammering the backend API.
        """
        policy = self._policy
        if not policy.requesting_user:
            # No user context — can't verify, deny by default
            return False

        channel_id = channel.id or channel.name
        if not channel_id:
            return False

        # Check cache
        if channel_id in self._membership_cache:
            return self._membership_cache[channel_id]

        # Try to verify via backend
        try:
            members = await self._backend.fetch_channel_members(channel)
            user_id = policy.requesting_user.id
            is_member = any(m.id == user_id for m in members)
            self._membership_cache[channel_id] = is_member
            return is_member
        except NotImplementedError:
            # Backend doesn't support membership listing.
            # Fail open only if we have no other way to verify — log a warning.
            logger.warning(
                "Backend does not support fetch_channel_members; cannot verify membership for channel '%s'. Denying access.",
                channel_id,
            )
            self._membership_cache[channel_id] = False
            return False
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Error checking membership for channel '%s': %s. Denying access.",
                channel_id,
                e,
            )
            self._membership_cache[channel_id] = False
            return False

    def _filter_messages_by_time(self, messages: list[Any]) -> list[Any]:
        """Filter messages to only those after history_visible_since."""
        policy = self._policy
        if not policy.history_visible_since:
            return messages

        cutoff = policy.history_visible_since
        filtered = []
        for msg in messages:
            # Support chatom Message objects and dicts
            ts = None
            if hasattr(msg, "timestamp"):
                ts = msg.timestamp
            elif isinstance(msg, dict):
                ts = msg.get("timestamp")
            if ts is None:
                # Can't determine timestamp — exclude for safety
                continue
            # Normalize to aware datetime for comparison
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                if cutoff.tzinfo is None:
                    cutoff = cutoff.replace(tzinfo=UTC)
                if ts >= cutoff:
                    filtered.append(msg)
            else:
                # Numeric timestamp (epoch millis or seconds)
                cutoff_ts = cutoff.timestamp()
                ts_val = float(ts)
                # Heuristic: if > 1e12, it's milliseconds
                if ts_val > 1e12:
                    ts_val = ts_val / 1000.0
                if ts_val >= cutoff_ts:
                    filtered.append(msg)
        return filtered

    async def _call_read_channel_history(self, args: dict[str, Any]) -> Any:
        channel = self._channel(args)
        channel = await self._resolve_channel_full(channel)
        await self._check_channel_access(channel)
        limit = min(args.get("limit", 50), self._policy.max_messages_per_request)
        after, before = resolve_history_bounds(args.get("after"), args.get("before"), args.get("last_minutes"))
        messages = await self._backend.fetch_messages(
            channel=channel,
            limit=limit,
            after=after,
            before=before,
        )
        if isinstance(messages, list):
            messages = self._filter_messages_by_time(messages)
        return messages

    async def _call_search_messages(self, args: dict[str, Any]) -> Any:
        ch = self._channel(args) if args.get("channel") else None
        # If searching a specific channel, enforce access
        if ch:
            await self._check_channel_access(ch)
        elif self._policy.restrict_to_invoking_channel:
            # No channel specified but policy restricts to invoking channel
            if self._policy.invoking_channel_id:
                ch = Channel(id=self._policy.invoking_channel_id)
            else:
                raise AccessDeniedError("Search must specify a channel when cross-channel access is restricted.")
        limit = min(args.get("limit", 20), self._policy.max_messages_per_request)
        results = await self._backend.search_messages(
            query=args["query"],
            channel=ch,
            limit=limit,
        )
        # Filter results by time and by channel access
        if isinstance(results, list):
            results = self._filter_messages_by_time(results)
            # If require_membership, filter out messages from channels user isn't in
            if self._policy.require_membership and self._policy.requesting_user:
                filtered = []
                for msg in results:
                    msg_channel_id = None
                    if hasattr(msg, "channel_id"):
                        msg_channel_id = msg.channel_id
                    elif hasattr(msg, "channel") and msg.channel:
                        msg_channel_id = msg.channel.id if hasattr(msg.channel, "id") else None
                    elif isinstance(msg, dict):
                        msg_channel_id = msg.get("channel_id") or (msg.get("channel", {}) or {}).get("id")
                    if msg_channel_id:
                        try:
                            await self._check_channel_access(Channel(id=msg_channel_id))
                            filtered.append(msg)
                        except AccessDeniedError:
                            continue
                    else:
                        filtered.append(msg)
                results = filtered
        return results

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
        channel = self._channel(args)
        await self._check_channel_access(channel)
        return await self._backend.fetch_channel_members(channel)

    async def _call_get_bot_info(self, args: dict[str, Any]) -> Any:
        return await self._backend.get_bot_info()

    async def _call_get_presence(self, args: dict[str, Any]) -> Any:
        user = self._user(args)
        return await self._backend.get_presence(user.id or user)

    async def _call_send_message(self, args: dict[str, Any]) -> Any:
        channel = self._channel(args)
        await self._check_channel_access(channel)
        return await self._backend.send_message(
            channel=channel,
            content=args["content"],
        )

    async def _call_edit_message(self, args: dict[str, Any]) -> Any:
        channel = self._channel(args)
        await self._check_channel_access(channel)
        return await self._backend.edit_message(
            message=args["message_id"],
            content=args["content"],
            channel=channel,
        )

    async def _call_add_reaction(self, args: dict[str, Any]) -> Any:
        channel = self._channel(args)
        await self._check_channel_access(channel)
        await self._backend.add_reaction(
            message=args["message_id"],
            emoji=args["emoji"],
            channel=channel,
        )
        return {"ok": True}

    async def _call_remove_reaction(self, args: dict[str, Any]) -> Any:
        channel = self._channel(args)
        await self._check_channel_access(channel)
        await self._backend.remove_reaction(
            message=args["message_id"],
            emoji=args["emoji"],
            channel=channel,
        )
        return {"ok": True}

    async def _call_delete_message(self, args: dict[str, Any]) -> Any:
        channel = self._channel(args)
        await self._check_channel_access(channel)
        await self._backend.delete_message(
            message=args["message_id"],
            channel=channel,
        )
        return {"ok": True}

    async def _call_set_presence(self, args: dict[str, Any]) -> Any:
        await self._backend.set_presence(
            args["status"],
            args.get("status_text") or None,
        )
        return {"ok": True}

    @staticmethod
    def _attachment_summary(att: Any, message_id: str = "") -> dict[str, Any]:
        """Build a compact, JSON-safe summary of an attachment."""
        return {
            "attachment_id": getattr(att, "id", "") or "",
            "filename": getattr(att, "filename", "") or "",
            "content_type": getattr(att, "content_type", "") or "",
            "size": getattr(att, "size", None),
            "attachment_type": getattr(getattr(att, "attachment_type", None), "value", "") or "",
            "message_id": message_id,
        }

    async def _call_list_recent_attachments(self, args: dict[str, Any]) -> Any:
        channel = self._channel(args)
        channel = await self._resolve_channel_full(channel)
        await self._check_channel_access(channel)
        limit = min(args.get("limit", 20), self._policy.max_messages_per_request)
        messages = await self._backend.fetch_messages(channel=channel, limit=limit)
        if isinstance(messages, list):
            messages = self._filter_messages_by_time(messages)
        result: list[dict[str, Any]] = []
        for msg in messages or []:
            msg_id = getattr(msg, "id", "") or ""
            for att in getattr(msg, "attachments", None) or []:
                result.append(self._attachment_summary(att, msg_id))
        return result

    async def _call_download_attachment(self, args: dict[str, Any]) -> Any:
        import base64

        channel = self._channel(args)
        channel = await self._resolve_channel_full(channel)
        await self._check_channel_access(channel)

        attachment_id = args["attachment_id"]
        message_id = args.get("message_id") or ""
        max_bytes = args.get("max_bytes", 5_000_000)

        # Locate the attachment within recent history so we get its full
        # metadata (url / platform IDs) rather than trusting model-supplied
        # fields. This keeps downloads scoped to the accessible channel.
        messages = await self._backend.fetch_messages(channel=channel, limit=self._policy.max_messages_per_request)
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
            return {
                "error": "not_found",
                "message": f"No attachment with id '{attachment_id}' found in the recent history of this channel.",
            }

        if getattr(found_att, "size", None) and found_att.size > max_bytes:
            return {
                "error": "too_large",
                "message": f"Attachment is {found_att.size} bytes which exceeds the {max_bytes}-byte limit.",
                "size": found_att.size,
            }

        data = await self._backend.download_attachment(found_att, message=found_msg)
        if len(data) > max_bytes:
            return {
                "error": "too_large",
                "message": f"Attachment is {len(data)} bytes which exceeds the {max_bytes}-byte limit.",
                "size": len(data),
            }

        return {
            "filename": getattr(found_att, "filename", "") or "",
            "content_type": getattr(found_att, "content_type", "") or "",
            "size": len(data),
            "data_base64": base64.b64encode(data).decode("ascii"),
        }

    async def _call_upload_file(self, args: dict[str, Any]) -> Any:
        import base64
        import binascii

        channel = self._channel(args)
        channel = await self._resolve_channel_full(channel)
        await self._check_channel_access(channel)

        try:
            data = base64.b64decode(args["data_base64"], validate=True)
        except (binascii.Error, ValueError) as e:
            return {"error": "invalid_data", "message": f"data_base64 is not valid base64: {e}"}

        content_type = args.get("content_type", "")
        if not content_type:
            import mimetypes

            content_type = mimetypes.guess_type(args["filename"])[0] or ""

        sent = await self._backend.upload_file(
            channel=channel,
            data=data,
            filename=args["filename"],
            content_type=content_type,
            content=args.get("content", ""),
        )
        return {"ok": True, "message_id": getattr(sent, "id", "") or ""}
