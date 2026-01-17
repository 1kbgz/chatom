"""Message model for chatom.

This module provides the Message class representing a chat message.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .attachment import Attachment
from .base import BaseModel, Field, Identifiable
from .channel import Channel
from .embed import Embed
from .reaction import Reaction
from .thread import Thread
from .user import User

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = ("Message", "MessageType", "MessageReference")


class MessageType(str, Enum):
    """Types of messages."""

    DEFAULT = "default"
    """A normal user message."""

    REPLY = "reply"
    """A reply to another message."""

    SYSTEM = "system"
    """A system-generated message."""

    JOIN = "join"
    """User joined notification."""

    LEAVE = "leave"
    """User left notification."""

    PIN = "pin"
    """Message pin notification."""

    THREAD_CREATED = "thread_created"
    """Thread creation notification."""

    CALL = "call"
    """Voice/video call notification."""

    UNKNOWN = "unknown"
    """Unknown message type."""


class MessageReference(BaseModel):
    """Reference to another message (for replies, forwards, etc.).

    Attributes:
        message_id: ID of the referenced message.
        channel_id: ID of the channel containing the message.
        guild_id: ID of the guild/server, if applicable.
    """

    message_id: str = Field(
        default="",
        description="ID of the referenced message.",
    )
    channel_id: str = Field(
        default="",
        description="ID of the channel containing the message.",
    )
    guild_id: str = Field(
        default="",
        description="ID of the guild/server, if applicable.",
    )


class Message(Identifiable):
    """Represents a message on a chat platform.

    Attributes:
        id: Platform-specific unique identifier.
        content: Text content of the message.
        author: User who sent the message.
        author_id: ID of the user who sent the message.
        channel: Channel where the message was sent.
        channel_id: ID of the channel where the message was sent.
        thread: Thread the message belongs to, if any.
        thread_id: ID of the thread, if in a thread.
        message_type: Type of message.
        created_at: When the message was created.
        edited_at: When the message was last edited.
        is_edited: Whether the message has been edited.
        is_pinned: Whether the message is pinned.
        is_bot: Whether the message was sent by a bot.
        is_system: Whether this is a system message.
        mentions: Users mentioned in the message.
        mention_ids: IDs of users mentioned in the message.
        attachments: File attachments on the message.
        embeds: Rich embeds in the message.
        reactions: Reactions on the message.
        reference: Reference to another message (for replies).
        reply_to: The message this is replying to.
        reply_to_id: ID of the message being replied to.
        formatted_content: Rich/formatted version of content (HTML, MessageML, etc.).
        raw: The raw message data from the backend.
        backend: The backend this message originated from.
        metadata: Additional platform-specific data.
    """

    content: str = Field(
        default="",
        description="Text content of the message.",
        alias="text",
    )
    author: Optional[User] = Field(
        default=None,
        description="User who sent the message.",
        alias="user",
    )
    author_id: str = Field(
        default="",
        description="ID of the user who sent the message.",
    )
    channel: Optional[Channel] = Field(
        default=None,
        description="Channel where the message was sent.",
    )
    channel_id: str = Field(
        default="",
        description="ID of the channel where the message was sent.",
    )
    thread: Optional[Thread] = Field(
        default=None,
        description="Thread the message belongs to, if any.",
    )
    thread_id: str = Field(
        default="",
        description="ID of the thread, if in a thread.",
    )
    message_type: MessageType = Field(
        default=MessageType.DEFAULT,
        description="Type of message.",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="When the message was created.",
    )
    edited_at: Optional[datetime] = Field(
        default=None,
        description="When the message was last edited.",
    )
    is_edited: bool = Field(
        default=False,
        description="Whether the message has been edited.",
    )
    is_pinned: bool = Field(
        default=False,
        description="Whether the message is pinned.",
    )
    is_bot: bool = Field(
        default=False,
        description="Whether the message was sent by a bot.",
    )
    is_system: bool = Field(
        default=False,
        description="Whether this is a system message.",
    )
    mentions: List[User] = Field(
        default_factory=list,
        description="Users mentioned in the message.",
        alias="tags",
    )
    mention_ids: List[str] = Field(
        default_factory=list,
        description="IDs of users mentioned in the message.",
    )
    attachments: List[Attachment] = Field(
        default_factory=list,
        description="File attachments on the message.",
    )
    embeds: List[Embed] = Field(
        default_factory=list,
        description="Rich embeds in the message.",
    )
    reactions: List[Reaction] = Field(
        default_factory=list,
        description="Reactions on the message.",
    )
    reference: Optional[MessageReference] = Field(
        default=None,
        description="Reference to another message (for replies).",
    )
    reply_to: Optional["Message"] = Field(
        default=None,
        description="The message this is replying to.",
    )
    reply_to_id: str = Field(
        default="",
        description="ID of the message being replied to.",
    )
    formatted_content: str = Field(
        default="",
        description="Rich/formatted version of content (HTML, MessageML, etc.).",
    )
    raw: Optional[Any] = Field(
        default=None,
        description="The raw message data from the backend.",
    )
    backend: str = Field(
        default="",
        description="The backend this message originated from.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional platform-specific data.",
    )

    @property
    def text(self) -> str:
        """Alias for content for backwards compatibility.

        Returns:
            str: The message content.
        """
        return self.content

    @property
    def user(self) -> Optional[User]:
        """Alias for author for backwards compatibility.

        Returns:
            Optional[User]: The message author.
        """
        return self.author

    @property
    def tags(self) -> List[User]:
        """Alias for mentions for backwards compatibility.

        Returns:
            List[User]: The mentioned users.
        """
        return self.mentions

    @property
    def is_reply(self) -> bool:
        """Check if this message is a reply.

        Returns:
            bool: True if this is a reply to another message.
        """
        return self.message_type == MessageType.REPLY or self.reference is not None or self.reply_to is not None

    @property
    def has_attachments(self) -> bool:
        """Check if message has any attachments.

        Returns:
            bool: True if message has attachments.
        """
        return len(self.attachments) > 0

    @property
    def has_embeds(self) -> bool:
        """Check if message has any embeds.

        Returns:
            bool: True if message has embeds.
        """
        return len(self.embeds) > 0

    def to_formatted(self) -> "FormattedMessage":
        """Convert this message to a FormattedMessage.

        Creates a FormattedMessage from the message content,
        preserving formatting based on the backend's format.

        Returns:
            FormattedMessage: The formatted message representation.

        Example:
            >>> msg = Message(content="Hello **world**", backend="discord")
            >>> formatted = msg.to_formatted()
            >>> formatted.render(Format.SLACK_MARKDOWN)
            'Hello *world*'
        """
        from chatom.format import FormattedAttachment, FormattedMessage

        fm = FormattedMessage()

        # Use formatted_content if available, otherwise use content
        text_content = self.formatted_content or self.content

        if text_content:
            # Parse the content based on the backend format
            # For now, add as plain text - subclasses can override for richer parsing
            fm.add_text(text_content)

        # Add attachments
        for att in self.attachments:
            fm.attachments.append(
                FormattedAttachment(
                    filename=att.filename,
                    url=att.url,
                    content_type=att.content_type,
                    size=att.size,
                )
            )

        # Add metadata
        fm.metadata["source_backend"] = self.backend
        fm.metadata["message_id"] = self.id
        if self.author_id:
            fm.metadata["author_id"] = self.author_id
        if self.channel_id:
            fm.metadata["channel_id"] = self.channel_id

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        backend: str = "",
        **kwargs: Any,
    ) -> "Message":
        """Create a Message from a FormattedMessage.

        Renders the FormattedMessage in the appropriate format for the
        target backend and creates a Message instance.

        Args:
            formatted: The FormattedMessage to convert.
            backend: The target backend (e.g., 'slack', 'discord').
            **kwargs: Additional message attributes.

        Returns:
            Message: A new message instance.

        Example:
            >>> from chatom.format import MessageBuilder
            >>> fm = MessageBuilder().bold("Hello").text(" world").build()
            >>> msg = Message.from_formatted(fm, backend="slack")
            >>> msg.content
            '*Hello* world'
        """
        from chatom.format import Format, get_format_for_backend

        # Determine the format for rendering
        if backend:
            target_format = get_format_for_backend(backend)
        else:
            target_format = Format.PLAINTEXT

        # Render the content
        content = formatted.render(target_format)

        # Build attachments
        from .attachment import Attachment

        attachments = [
            Attachment(
                filename=att.filename,
                url=att.url,
                content_type=att.content_type,
                size=att.size,
            )
            for att in formatted.attachments
        ]

        return cls(
            content=content,
            backend=backend,
            attachments=attachments,
            metadata=dict(formatted.metadata),
            **kwargs,
        )

    def render_for(self, backend: str) -> str:
        """Render this message's content for a specific backend.

        Converts the message to a FormattedMessage and renders it
        for the target backend's format.

        Args:
            backend: The target backend (e.g., 'slack', 'discord').

        Returns:
            str: The rendered message content.

        Example:
            >>> msg = DiscordMessage(content="Hello **world**")
            >>> msg.render_for("slack")
            'Hello *world*'
        """
        formatted = self.to_formatted()
        return formatted.render_for(backend)

    @property
    def is_direct_message(self) -> bool:
        """Check if this message was sent in a direct/private message channel.

        Returns True if the message's channel is a DM/IM/group DM.
        Returns False if no channel is set.

        Returns:
            bool: True if this is a direct message.

        Example:
            >>> if message.is_direct_message:
            ...     # Handle DM differently
            ...     pass
        """
        if self.channel is not None:
            return self.channel.is_direct_message
        return False

    @property
    def is_dm(self) -> bool:
        """Alias for is_direct_message.

        Returns:
            bool: True if this is a direct message.
        """
        return self.is_direct_message

    def is_message_to_user(self, user: User) -> bool:
        """Check if this message mentions or is directed at a specific user.

        This method checks if the given user is mentioned in the message.
        It checks both the mentions list (User objects) and the mention_ids
        list (user IDs as strings).

        Args:
            user: The user to check for.

        Returns:
            bool: True if the user is mentioned in this message.

        Example:
            >>> bot_user = User(id="U123", name="MyBot")
            >>> if message.is_message_to_user(bot_user):
            ...     # This message mentions the bot
            ...     await handle_command(message)
        """
        # Check if user is in the mentions list by ID
        for mentioned in self.mentions:
            if mentioned.id == user.id:
                return True

        # Also check mention_ids list
        if user.id in self.mention_ids:
            return True

        return False

    def is_in_thread(self) -> bool:
        """Check if this message is part of a thread.

        Returns:
            bool: True if the message is in a thread.
        """
        return self.thread is not None or bool(self.thread_id)
