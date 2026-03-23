from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from chatom.backend import BackendBase
from chatom.base import Channel, Message
from chatom.format.variant import Format


class MessageSummary(BaseModel):
    """Compact representation of a single message for LLM consumption."""

    id: str = ""
    author: str = ""
    content: str = ""
    timestamp: Optional[datetime] = None

    @classmethod
    def from_message(cls, msg: Message) -> "MessageSummary":
        author = ""
        if msg.author:
            author = msg.author.display_name or msg.author.name or msg.author.id or ""

        # Use the format system to convert backend-specific content
        # (Slack mrkdwn, Symphony MessageML, etc.) into plain text.
        content = msg.to_formatted().render(Format.PLAINTEXT)

        return cls(
            id=msg.id or "",
            author=author,
            content=content,
            timestamp=msg.created_at,
        )


class ChannelContext(BaseModel):
    """Aggregated channel data suitable for inclusion in an LLM prompt.

    Contains the channel metadata, recent messages, and participating
    users — everything an agent needs to reason about a conversation.
    """

    channel_id: str = ""
    channel_name: str = ""
    topic: str = ""
    messages: List[MessageSummary] = Field(default_factory=list)
    participants: List[str] = Field(default_factory=list)

    def format_for_llm(self) -> str:
        """Render the context as a human-readable text block.

        Returns:
            A string suitable for direct inclusion in an LLM prompt.
        """
        lines: list[str] = []
        if self.channel_name:
            lines.append(f"Channel: #{self.channel_name}")
        if self.topic:
            lines.append(f"Topic: {self.topic}")
        if self.participants:
            lines.append(f"Participants: {', '.join(self.participants)}")
        lines.append("")
        for msg in self.messages:
            ts = msg.timestamp.strftime("%Y-%m-%d %H:%M") if msg.timestamp else ""
            prefix = f"[{ts}] " if ts else ""
            lines.append(f"{prefix}{msg.author}: {msg.content}")
        return "\n".join(lines)


async def build_channel_context(
    backend: BackendBase,
    channel: Union[str, Channel],
    *,
    limit: int = 50,
    token_budget: Optional[int] = None,
) -> ChannelContext:
    """Build a :class:`ChannelContext` from a live backend.

    Args:
        backend: The connected backend to query.
        channel: Channel ID, name, or :class:`Channel` object.
        limit: Maximum messages to fetch.
        token_budget: If given, truncate messages so the formatted output
            stays under approximately this many tokens (estimated at
            ~4 characters per token).  Oldest messages are dropped first.

    Returns:
        A populated :class:`ChannelContext`.
    """
    # Resolve channel metadata
    if isinstance(channel, str):
        ch = await backend.lookup_channel(id=channel) or await backend.lookup_channel(name=channel)
    else:
        ch = channel
    channel_id = ch.id if ch else (channel if isinstance(channel, str) else channel.id or "")
    channel_name = ch.name if ch else ""
    topic = ch.topic if ch else ""

    # Fetch messages
    messages = await backend.fetch_messages(channel=channel_id or channel, limit=limit)
    summaries = [MessageSummary.from_message(m) for m in messages]

    # Collect unique participant names
    seen: set[str] = set()
    participants: list[str] = []
    for s in summaries:
        if s.author and s.author not in seen:
            seen.add(s.author)
            participants.append(s.author)

    ctx = ChannelContext(
        channel_id=channel_id or "",
        channel_name=channel_name or "",
        topic=topic or "",
        messages=summaries,
        participants=participants,
    )

    # Token budget enforcement — drop oldest messages first
    if token_budget is not None:
        chars_budget = token_budget * 4
        formatted_len = len(ctx.format_for_llm())
        while ctx.messages and formatted_len > chars_budget:
            removed = ctx.messages.pop(0)
            ts = removed.timestamp.strftime("%Y-%m-%d %H:%M") if removed.timestamp else ""
            prefix = f"[{ts}] " if ts else ""
            line = f"{prefix}{removed.author}: {removed.content}"
            formatted_len -= len(line) + 1  # +1 for newline

    return ctx
