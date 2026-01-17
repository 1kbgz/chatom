"""Discord-specific Message model.

This module provides the Discord-specific Message class.
"""

from enum import IntEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from chatom.base import Field, Message

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = (
    "DiscordMessage",
    "DiscordMessageType",
    "DiscordMessageFlags",
)


class DiscordMessageType(IntEnum):
    """Discord message types.

    Based on Discord API message types.
    """

    DEFAULT = 0
    RECIPIENT_ADD = 1
    RECIPIENT_REMOVE = 2
    CALL = 3
    CHANNEL_NAME_CHANGE = 4
    CHANNEL_ICON_CHANGE = 5
    CHANNEL_PINNED_MESSAGE = 6
    USER_JOIN = 7
    GUILD_BOOST = 8
    GUILD_BOOST_TIER_1 = 9
    GUILD_BOOST_TIER_2 = 10
    GUILD_BOOST_TIER_3 = 11
    CHANNEL_FOLLOW_ADD = 12
    GUILD_DISCOVERY_DISQUALIFIED = 14
    GUILD_DISCOVERY_REQUALIFIED = 15
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = 16
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = 17
    THREAD_CREATED = 18
    REPLY = 19
    CHAT_INPUT_COMMAND = 20
    THREAD_STARTER_MESSAGE = 21
    GUILD_INVITE_REMINDER = 22
    CONTEXT_MENU_COMMAND = 23
    AUTO_MODERATION_ACTION = 24
    ROLE_SUBSCRIPTION_PURCHASE = 25
    INTERACTION_PREMIUM_UPSELL = 26
    STAGE_START = 27
    STAGE_END = 28
    STAGE_SPEAKER = 29
    STAGE_TOPIC = 31
    GUILD_APPLICATION_PREMIUM_SUBSCRIPTION = 32


class DiscordMessageFlags(IntEnum):
    """Discord message flags.

    Based on Discord API message flags.
    """

    CROSSPOSTED = 1 << 0
    IS_CROSSPOST = 1 << 1
    SUPPRESS_EMBEDS = 1 << 2
    SOURCE_MESSAGE_DELETED = 1 << 3
    URGENT = 1 << 4
    HAS_THREAD = 1 << 5
    EPHEMERAL = 1 << 6
    LOADING = 1 << 7
    FAILED_TO_MENTION_SOME_ROLES_IN_THREAD = 1 << 8
    SUPPRESS_NOTIFICATIONS = 1 << 12
    IS_VOICE_MESSAGE = 1 << 13


class DiscordMessage(Message):
    """Discord-specific message with additional Discord fields.

    Based on the Discord API message structure.

    Attributes:
        discord_type: The Discord message type.
        channel_id: The channel ID.
        guild_id: The guild/server ID.
        author_id: The author's user ID.
        member: Guild member data for the author.
        mention_everyone: Whether @everyone was mentioned.
        mentions: List of mentioned user IDs.
        mention_roles: List of mentioned role IDs.
        mention_channels: List of mentioned channel IDs.
        nonce: Used for message send verification.
        pinned: Whether the message is pinned.
        webhook_id: Webhook ID if sent by a webhook.
        flags: Message flags.
        referenced_message: The message being replied to.
        interaction: Interaction data if from an interaction.
        thread: Thread spawned from this message.
        components: Message components (buttons, etc.).
        sticker_items: Stickers in the message.
        position: Position in thread.
    """

    discord_type: DiscordMessageType = Field(
        default=DiscordMessageType.DEFAULT,
        description="The Discord message type.",
    )
    channel_id: str = Field(
        default="",
        description="The channel ID.",
    )
    guild_id: Optional[str] = Field(
        default=None,
        description="The guild/server ID.",
    )
    author_id: Optional[str] = Field(
        default=None,
        description="The author's user ID.",
    )
    member: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Guild member data for the author.",
    )
    mention_everyone: bool = Field(
        default=False,
        description="Whether @everyone was mentioned.",
    )
    mentions: List[str] = Field(
        default_factory=list,
        description="List of mentioned user IDs.",
    )
    mention_roles: List[str] = Field(
        default_factory=list,
        description="List of mentioned role IDs.",
    )
    mention_channels: List[str] = Field(
        default_factory=list,
        description="List of mentioned channel IDs.",
    )
    nonce: Optional[str] = Field(
        default=None,
        description="Used for message send verification.",
    )
    pinned: bool = Field(
        default=False,
        description="Whether the message is pinned.",
    )
    webhook_id: Optional[str] = Field(
        default=None,
        description="Webhook ID if sent by a webhook.",
    )
    flags: int = Field(
        default=0,
        description="Message flags.",
    )
    interaction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Interaction data if from an interaction.",
    )
    components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Message components (buttons, select menus, etc.).",
    )
    sticker_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Stickers in the message.",
    )
    position: Optional[int] = Field(
        default=None,
        description="Position in thread.",
    )

    @property
    def is_reply(self) -> bool:
        """Check if this message is a reply."""
        return self.discord_type == DiscordMessageType.REPLY or self.reply_to is not None

    @property
    def is_ephemeral(self) -> bool:
        """Check if this is an ephemeral message."""
        return bool(self.flags & DiscordMessageFlags.EPHEMERAL)

    @property
    def is_crossposted(self) -> bool:
        """Check if this message was crossposted."""
        return bool(self.flags & DiscordMessageFlags.CROSSPOSTED)

    @property
    def has_thread(self) -> bool:
        """Check if this message has a thread."""
        return bool(self.flags & DiscordMessageFlags.HAS_THREAD)

    @property
    def is_voice_message(self) -> bool:
        """Check if this is a voice message."""
        return bool(self.flags & DiscordMessageFlags.IS_VOICE_MESSAGE)

    @property
    def suppresses_embeds(self) -> bool:
        """Check if embeds are suppressed."""
        return bool(self.flags & DiscordMessageFlags.SUPPRESS_EMBEDS)

    @property
    def suppresses_notifications(self) -> bool:
        """Check if notifications are suppressed."""
        return bool(self.flags & DiscordMessageFlags.SUPPRESS_NOTIFICATIONS)

    def has_flag(self, flag: DiscordMessageFlags) -> bool:
        """Check if a specific flag is set.

        Args:
            flag: The flag to check.

        Returns:
            True if the flag is set.
        """
        return bool(self.flags & flag)

    def to_formatted(self) -> "FormattedMessage":
        """Convert this Discord message to a FormattedMessage.

        Parses Discord markdown formatting and converts to a FormattedMessage
        that can be rendered for other backends.

        Returns:
            FormattedMessage: The formatted message representation.
        """
        from chatom.format import FormattedAttachment, FormattedMessage

        fm = FormattedMessage()

        # Use the content (which contains Discord markdown)
        if self.content:
            fm.add_text(self.content)

        # Add attachments from the base class
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
        fm.metadata["source_backend"] = "discord"
        fm.metadata["message_id"] = self.id
        if self.author_id:
            fm.metadata["author_id"] = self.author_id
        if self.channel_id:
            fm.metadata["channel_id"] = self.channel_id
        if self.guild_id:
            fm.metadata["guild_id"] = self.guild_id
        if self.mentions:
            fm.metadata["mention_ids"] = self.mentions
        if self.webhook_id:
            fm.metadata["webhook_id"] = self.webhook_id

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        **kwargs: Any,
    ) -> "DiscordMessage":
        """Create a DiscordMessage from a FormattedMessage.

        Renders the FormattedMessage in Discord markdown format.

        Args:
            formatted: The FormattedMessage to convert.
            **kwargs: Additional message attributes.

        Returns:
            DiscordMessage: A new DiscordMessage instance.
        """
        from chatom.format import Format

        content = formatted.render(Format.DISCORD_MARKDOWN)

        return cls(
            content=content,
            backend="discord",
            metadata=dict(formatted.metadata),
            **kwargs,
        )

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "DiscordMessage":
        """Create a DiscordMessage from a Discord API response.

        Args:
            data: The API response data.

        Returns:
            A DiscordMessage instance.
        """
        author = data.get("author", {})

        return cls(
            id=data.get("id", ""),
            content=data.get("content", ""),
            discord_type=DiscordMessageType(data.get("type", 0)),
            channel_id=data.get("channel_id", ""),
            guild_id=data.get("guild_id"),
            author_id=author.get("id", ""),
            is_bot=author.get("bot", False),
            member=data.get("member"),
            mention_everyone=data.get("mention_everyone", False),
            mentions=[m.get("id", "") for m in data.get("mentions", [])],
            mention_ids=[m.get("id", "") for m in data.get("mentions", [])],
            mention_roles=data.get("mention_roles", []),
            mention_channels=[c.get("id", "") for c in data.get("mention_channels", [])],
            nonce=data.get("nonce"),
            pinned=data.get("pinned", False),
            is_pinned=data.get("pinned", False),
            webhook_id=data.get("webhook_id"),
            flags=data.get("flags", 0),
            interaction=data.get("interaction"),
            components=data.get("components", []),
            sticker_items=data.get("sticker_items", []),
            position=data.get("position"),
            raw=data,
            backend="discord",
        )
