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
from .organization import Organization
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

    FORWARD = "forward"
    """A forwarded message."""

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
        channel: Channel where the message was sent.
        thread: Thread the message belongs to, if any.
        message_type: Type of message.
        created_at: When the message was created.
        edited_at: When the message was last edited.
        is_edited: Whether the message has been edited.
        is_pinned: Whether the message is pinned.
        is_bot: Whether the message was sent by a bot.
        is_system: Whether this is a system message.
        mentions: Users mentioned in the message.
        attachments: File attachments on the message.
        embeds: Rich embeds in the message.
        reactions: Reactions on the message.
        reference: Reference to another message (for replies).
        reply_to: The message this is replying to.
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
    channel: Optional[Channel] = Field(
        default=None,
        description="Channel where the message was sent.",
    )
    thread: Optional[Thread] = Field(
        default=None,
        description="Thread the message belongs to, if any.",
    )
    organization: Optional["Organization"] = Field(
        default=None,
        description="Organization the message belongs to, if applicable.",
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
    forwarded_from: Optional["Message"] = Field(
        default=None,
        description="The original message if this is a forwarded message.",
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
    def mention_ids(self) -> List[str]:
        """Get the IDs of mentioned users.

        Returns:
            List[str]: List of user IDs mentioned in this message.
        """
        return [m.id for m in self.mentions if m.id]

    @property
    def author_id(self) -> str:
        """Get the author's ID.

        Returns:
            str: The author ID or empty string if no author.
        """
        return self.author.id if self.author else ""

    @property
    def channel_id(self) -> str:
        """Get the channel's ID.

        Returns:
            str: The channel ID or empty string if no channel.
        """
        return self.channel.id if self.channel else ""

    @property
    def thread_id(self) -> str:
        """Get the thread's ID.

        Returns:
            str: The thread ID or empty string if no thread.
        """
        return self.thread.id if self.thread else ""

    @property
    def reply_to_id(self) -> str:
        """Get the ID of the message this is replying to.

        Returns:
            str: The reply-to message ID or empty string if not a reply.
        """
        return self.reply_to.id if self.reply_to else ""

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

    @property
    def is_dm(self) -> bool:
        """Check if this message is from a direct message.

        Returns:
            bool: True if from a DM channel.
        """
        if self.channel:
            return self.channel.is_dm
        # Fall back to metadata
        return bool(self.metadata.get("is_dm") or self.metadata.get("is_im"))

    @property
    def is_direct_message(self) -> bool:
        """Alias for is_dm.

        Returns:
            bool: True if from a DM channel.
        """
        return self.is_dm

    @property
    def channel_name(self) -> str:
        """Get the channel name.

        Returns:
            str: The channel name or empty string if not available.
        """
        if self.channel:
            return self.channel.name
        return self.metadata.get("channel_name", "")

    @property
    def author_name(self) -> str:
        """Get the author name.

        Returns:
            str: The author name or empty string if not available.
        """
        if self.author:
            return self.author.name
        return self.metadata.get("author_name", "")

    def get_mentioned_user_ids(self) -> List[str]:
        """Parse and extract user IDs mentioned in the message content.

        This parses the message content using the backend's mention format
        and returns a list of user IDs that were mentioned. This is useful
        for detecting when specific users are mentioned in a message.

        Note: This parses the content text. For mentions that were already
        parsed by the backend, use the `mentions` property instead.

        Returns:
            List[str]: List of user IDs mentioned in the content.

        Example:
            >>> msg = Message(content="Hey <@U123> and <@U456>!", backend="slack")
            >>> msg.get_mentioned_user_ids()
            ['U123', 'U456']
        """
        from .mention import extract_mention_ids

        if not self.content or not self.backend:
            return []
        return extract_mention_ids(self.content, self.backend)

    def get_mentioned_channel_ids(self) -> List[str]:
        """Parse and extract channel IDs mentioned in the message content.

        This parses the message content using the backend's channel mention
        format and returns a list of channel IDs that were referenced.

        Returns:
            List[str]: List of channel IDs mentioned in the content.

        Example:
            >>> msg = Message(content="Join <#C123> and <#C456>!", backend="slack")
            >>> msg.get_mentioned_channel_ids()
            ['C123', 'C456']
        """
        from .mention import extract_channel_ids

        if not self.content or not self.backend:
            return []
        return extract_channel_ids(self.content, self.backend)

    def mentions_user(self, user_id: str) -> bool:
        """Check if a specific user is mentioned in this message.

        Checks both the parsed mentions list and parses the content
        to find mentions of the given user ID.

        Args:
            user_id: The user ID to check for.

        Returns:
            bool: True if the user is mentioned.

        Example:
            >>> if message.mentions_user(bot_user_id):
            ...     await handle_bot_mention(message)
        """
        # Check pre-parsed mentions first
        for user in self.mentions:
            if user.id == user_id:
                return True
        # Also check content
        return user_id in self.get_mentioned_user_ids()

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

        return False

    def is_in_thread(self) -> bool:
        """Check if this message is part of a thread.

        Returns:
            bool: True if the message is in a thread.
        """
        return self.thread is not None or bool(self.thread_id)

    @property
    def is_forwarded(self) -> bool:
        """Check if this message is a forwarded message.

        Returns:
            bool: True if this message was forwarded from another message.
        """
        return self.message_type == MessageType.FORWARD or self.forwarded_from is not None

    @property
    def forwarded_from_id(self) -> str:
        """Get the ID of the original message if this is a forward.

        Returns:
            str: The original message ID or empty string if not a forward.
        """
        return self.forwarded_from.id if self.forwarded_from else ""

    # -------------------------------------------------------------------------
    # Response Convenience Methods
    # -------------------------------------------------------------------------
    # These methods construct new Message instances based on this message.
    # They make it easy to create replies, forwards, or quotes.

    def as_reply(self, content: str, **kwargs: Any) -> "Message":
        """Create a new message as a reply to this message.

        Constructs a new message with the same channel, with this message
        set as the reply_to reference.

        Args:
            content: The reply content.
            **kwargs: Additional message attributes to set.

        Returns:
            A new Message instance configured as a reply.

        Example:
            >>> reply = message.as_reply("Thanks for letting me know!")
            >>> reply.reply_to is message
            True
        """
        return self.__class__(
            content=content,
            channel=self.channel,
            reply_to=self,
            message_type=MessageType.REPLY,
            backend=self.backend,
            **kwargs,
        )

    def as_thread_reply(self, content: str, **kwargs: Any) -> "Message":
        """Create a new message as a reply in this message's thread.

        If this message is already in a thread, the new message is placed
        in that thread. Otherwise, a new thread is started on this message.

        Args:
            content: The reply content.
            **kwargs: Additional message attributes to set.

        Returns:
            A new Message instance configured as a thread reply.

        Example:
            >>> reply = message.as_thread_reply("Following up on this...")
            >>> reply.thread is not None
            True
        """
        # If already in a thread, use that thread; otherwise create thread from this message
        thread = self.thread if self.thread else Thread(id=self.id, parent_message=self)
        return self.__class__(
            content=content,
            channel=self.channel,
            thread=thread,
            reply_to=self,
            message_type=MessageType.REPLY,
            backend=self.backend,
            **kwargs,
        )

    def as_dm_to_author(self, content: str, **kwargs: Any) -> "Message":
        """Create a new message as a DM to this message's author.

        Constructs a new message in an incomplete DM channel that will
        be resolved by the backend when sent.

        Args:
            content: The DM content.
            **kwargs: Additional message attributes to set.

        Returns:
            A new Message instance configured for a DM to the author.

        Example:
            >>> dm = message.as_dm_to_author("I'll follow up privately.")
            >>> dm.channel.users[0] is message.author
            True
        """
        if not self.author:
            raise ValueError("Cannot create DM: message has no author")

        # Create an incomplete DM channel that the backend will resolve
        dm_channel = Channel.dm_to(self.author)

        return self.__class__(
            content=content,
            channel=dm_channel,
            backend=self.backend,
            **kwargs,
        )

    def as_forward(self, target_channel: Channel, **kwargs: Any) -> "Message":
        """Create a new message as a forward of this message to another channel.

        Constructs a new message with forwarded content and attribution
        to the original author and channel.

        Args:
            target_channel: The channel to forward to.
            **kwargs: Additional message attributes to set.

        Returns:
            A new Message instance configured as a forward.

        Example:
            >>> forward = message.as_forward(log_channel)
            >>> forward.forwarded_from is message
            True
        """
        # Build forwarded content with attribution
        author_name = self.author_name or "Unknown"
        channel_name = self.channel_name or (self.channel.id if self.channel else "unknown")
        forwarded_content = f"[Forwarded from {author_name} in #{channel_name}]\n{self.content}"

        return self.__class__(
            content=forwarded_content,
            channel=target_channel,
            forwarded_from=self,
            message_type=MessageType.FORWARD,
            backend=self.backend,
            **kwargs,
        )

    def as_quote_reply(self, content: str, **kwargs: Any) -> "Message":
        """Create a new message that quotes this message.

        Constructs a new message with the original content quoted,
        followed by the reply content.

        Args:
            content: The reply content (after the quote).
            **kwargs: Additional message attributes to set.

        Returns:
            A new Message instance with quoted content.

        Example:
            >>> quote = message.as_quote_reply("I agree with this point!")
            >>> "> " in quote.content
            True
        """
        # Build quoted content
        quoted_lines = [f"> {line}" for line in self.content.split("\n")]
        quoted = "\n".join(quoted_lines)
        full_content = f"{quoted}\n\n{content}"

        # If in a thread, stay in that thread; otherwise create thread from this message
        thread = self.thread if self.thread else Thread(id=self.id, parent_message=self)

        return self.__class__(
            content=full_content,
            channel=self.channel,
            thread=thread,
            reply_to=self,
            message_type=MessageType.REPLY,
            backend=self.backend,
            **kwargs,
        )

    def reply_context(self) -> Dict[str, Any]:
        """Get context information for creating a reply.

        Returns useful objects for manually constructing a reply.

        Returns:
            Dict with channel, message, thread, author objects.

        Example:
            >>> ctx = message.reply_context()
            >>> new_msg = Message(
            ...     channel=ctx["channel"],
            ...     content="My reply",
            ...     reply_to=ctx["message"],
            ... )
        """
        return {
            "channel": self.channel,
            "message": self,
            "thread": self.thread,
            "author": self.author,
        }
