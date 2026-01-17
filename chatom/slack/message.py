"""Slack-specific Message model.

This module provides the Slack-specific Message class.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from chatom.base import Field, Message

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = (
    "SlackMessage",
    "SlackMessageSubtype",
)


class SlackMessageSubtype(str, Enum):
    """Slack message subtypes.

    Based on Slack API message subtypes.
    """

    BOT_MESSAGE = "bot_message"
    ME_MESSAGE = "me_message"
    MESSAGE_CHANGED = "message_changed"
    MESSAGE_DELETED = "message_deleted"
    MESSAGE_REPLIED = "message_replied"
    CHANNEL_JOIN = "channel_join"
    CHANNEL_LEAVE = "channel_leave"
    CHANNEL_TOPIC = "channel_topic"
    CHANNEL_PURPOSE = "channel_purpose"
    CHANNEL_NAME = "channel_name"
    CHANNEL_ARCHIVE = "channel_archive"
    CHANNEL_UNARCHIVE = "channel_unarchive"
    FILE_SHARE = "file_share"
    FILE_COMMENT = "file_comment"
    FILE_MENTION = "file_mention"
    PINNED_ITEM = "pinned_item"
    UNPINNED_ITEM = "unpinned_item"
    THREAD_BROADCAST = "thread_broadcast"
    REMINDER_ADD = "reminder_add"
    SLACKBOT_RESPONSE = "slackbot_response"


class SlackMessage(Message):
    """Slack-specific message with additional Slack fields.

    Based on the Slack API message structure.

    Attributes:
        ts: The message timestamp (unique identifier).
        channel: The channel ID.
        sender_id: The user ID who sent the message (Slack-specific).
        team: The team/workspace ID.
        subtype: The message subtype.
        bot_id: Bot ID if sent by a bot.
        app_id: App ID if sent by an app.
        blocks: Slack Block Kit blocks.
        text: The message text (may differ from content due to mentions).
        thread_ts: Thread parent timestamp.
        reply_count: Number of replies in thread.
        reply_users_count: Number of users in thread.
        latest_reply: Timestamp of latest reply.
        reply_users: List of user IDs who replied.
        is_locked: Whether the thread is locked.
        subscribed: Whether user is subscribed to thread.
        last_read: Timestamp of last read message in thread.
        reactions: List of reactions on the message.
        files: List of attached files.
        upload: Whether this is a file upload message.
        display_as_bot: Whether to display as bot.
        edited: Edit information if message was edited.
        client_msg_id: Client-side message ID.
        metadata: Message metadata.
    """

    ts: str = Field(
        default="",
        description="The message timestamp (unique identifier).",
    )
    channel: str = Field(
        default="",
        description="The channel ID.",
    )
    sender_id: Optional[str] = Field(
        default=None,
        description="The Slack user ID who sent the message.",
    )
    team: Optional[str] = Field(
        default=None,
        description="The team/workspace ID.",
    )
    subtype: Optional[SlackMessageSubtype] = Field(
        default=None,
        description="The message subtype.",
    )
    bot_id: Optional[str] = Field(
        default=None,
        description="Bot ID if sent by a bot.",
    )
    app_id: Optional[str] = Field(
        default=None,
        description="App ID if sent by an app.",
    )
    blocks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Slack Block Kit blocks.",
    )
    text: str = Field(
        default="",
        description="The message text.",
    )
    thread_ts: Optional[str] = Field(
        default=None,
        description="Thread parent timestamp.",
    )
    reply_count: int = Field(
        default=0,
        description="Number of replies in thread.",
    )
    reply_users_count: int = Field(
        default=0,
        description="Number of users in thread.",
    )
    latest_reply: Optional[str] = Field(
        default=None,
        description="Timestamp of latest reply.",
    )
    reply_users: List[str] = Field(
        default_factory=list,
        description="List of user IDs who replied.",
    )
    is_locked: bool = Field(
        default=False,
        description="Whether the thread is locked.",
    )
    subscribed: bool = Field(
        default=False,
        description="Whether user is subscribed to thread.",
    )
    last_read: Optional[str] = Field(
        default=None,
        description="Timestamp of last read message in thread.",
    )
    files: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of attached files.",
    )
    upload: bool = Field(
        default=False,
        description="Whether this is a file upload message.",
    )
    display_as_bot: bool = Field(
        default=False,
        description="Whether to display as bot.",
    )
    edited: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Edit information if message was edited.",
    )
    client_msg_id: Optional[str] = Field(
        default=None,
        description="Client-side message ID.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Message metadata.",
    )

    @property
    def is_thread_reply(self) -> bool:
        """Check if this message is a reply in a thread."""
        return self.thread_ts is not None and self.ts != self.thread_ts

    @property
    def is_thread_parent(self) -> bool:
        """Check if this message started a thread."""
        return self.reply_count > 0

    @property
    def is_bot_message(self) -> bool:
        """Check if this message is from a bot."""
        return self.bot_id is not None or self.subtype == SlackMessageSubtype.BOT_MESSAGE

    @property
    def is_edited(self) -> bool:
        """Check if this message was edited."""
        return self.edited is not None

    @property
    def has_blocks(self) -> bool:
        """Check if this message has Block Kit blocks."""
        return len(self.blocks) > 0

    @property
    def has_files(self) -> bool:
        """Check if this message has attached files."""
        return len(self.files) > 0

    def mentions_user(self, user_id: str) -> bool:
        """Check if this message mentions a specific user.

        Slack mentions are in the format <@USER_ID> in the message text.

        Args:
            user_id: The user ID to check for (e.g., 'U12345678').

        Returns:
            True if the user is mentioned, False otherwise.
        """
        mention_format = f"<@{user_id}>"

        # Check content field
        if self.content and mention_format in self.content:
            return True

        # Check text field (may differ from content)
        if self.text and mention_format in self.text:
            return True

        # Check mentions list if populated
        if self.mentions and user_id in self.mentions:
            return True

        # Check mention_ids list if populated
        if self.mention_ids and user_id in self.mention_ids:
            return True

        return False

    @property
    def permalink(self) -> Optional[str]:
        """Get the message permalink if channel and ts are available."""
        if self.channel and self.ts:
            # Note: This is a simplified permalink format
            # Real permalinks require the workspace domain
            ts_no_dot = self.ts.replace(".", "")
            return f"https://slack.com/archives/{self.channel}/p{ts_no_dot}"
        return None

    def to_formatted(self) -> "FormattedMessage":
        """Convert this Slack message to a FormattedMessage.

        Parses Slack mrkdwn formatting and converts to a FormattedMessage
        that can be rendered for other backends.

        Returns:
            FormattedMessage: The formatted message representation.
        """
        from chatom.format import FormattedAttachment, FormattedMessage

        fm = FormattedMessage()

        # Use the text content (which contains Slack mrkdwn)
        content = self.text or self.content
        if content:
            # Store as plain text - could be enhanced to parse mrkdwn
            fm.add_text(content)

        # Add file attachments
        for file_info in self.files:
            fm.attachments.append(
                FormattedAttachment(
                    filename=file_info.get("name", ""),
                    url=file_info.get("url_private", file_info.get("permalink", "")),
                    content_type=file_info.get("mimetype", ""),
                    size=file_info.get("size", 0),
                )
            )

        # Add metadata
        fm.metadata["source_backend"] = "slack"
        fm.metadata["message_id"] = self.id or self.ts
        fm.metadata["ts"] = self.ts
        if self.sender_id:
            fm.metadata["author_id"] = self.sender_id
        if self.channel:
            fm.metadata["channel_id"] = self.channel
        if self.thread_ts:
            fm.metadata["thread_ts"] = self.thread_ts
        if self.team:
            fm.metadata["team_id"] = self.team

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        **kwargs: Any,
    ) -> "SlackMessage":
        """Create a SlackMessage from a FormattedMessage.

        Renders the FormattedMessage in Slack mrkdwn format.

        Args:
            formatted: The FormattedMessage to convert.
            **kwargs: Additional message attributes.

        Returns:
            SlackMessage: A new SlackMessage instance.
        """
        from chatom.format import Format

        content = formatted.render(Format.SLACK_MARKDOWN)

        return cls(
            content=content,
            text=content,
            metadata=dict(formatted.metadata),
            **kwargs,
        )

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "SlackMessage":
        """Create a SlackMessage from a Slack API response.

        Args:
            data: The API response data.

        Returns:
            A SlackMessage instance.
        """
        subtype = None
        if "subtype" in data:
            try:
                subtype = SlackMessageSubtype(data["subtype"])
            except ValueError:
                pass

        return cls(
            id=data.get("client_msg_id", data.get("ts", "")),
            ts=data.get("ts", ""),
            channel=data.get("channel", ""),
            channel_id=data.get("channel", ""),
            sender_id=data.get("user"),
            author_id=data.get("user", ""),
            team=data.get("team"),
            subtype=subtype,
            bot_id=data.get("bot_id"),
            app_id=data.get("app_id"),
            is_bot=data.get("bot_id") is not None,
            blocks=data.get("blocks", []),
            text=data.get("text", ""),
            content=data.get("text", ""),
            thread_ts=data.get("thread_ts"),
            thread_id=data.get("thread_ts", ""),
            reply_count=data.get("reply_count", 0),
            reply_users_count=data.get("reply_users_count", 0),
            latest_reply=data.get("latest_reply"),
            reply_users=data.get("reply_users", []),
            is_locked=data.get("is_locked", False),
            subscribed=data.get("subscribed", False),
            last_read=data.get("last_read"),
            files=data.get("files", []),
            upload=data.get("upload", False),
            display_as_bot=data.get("display_as_bot", False),
            edited=data.get("edited"),
            client_msg_id=data.get("client_msg_id"),
            raw=data,
            backend="slack",
        )
