"""Discord-specific Channel model.

This module provides the Discord-specific Channel class.
"""

from enum import Enum
from typing import Optional

from chatom.base import Channel, Field

__all__ = ("DiscordChannel", "DiscordChannelType")


class DiscordChannelType(str, Enum):
    """Discord-specific channel types."""

    GUILD_TEXT = "guild_text"
    DM = "dm"
    GUILD_VOICE = "guild_voice"
    GROUP_DM = "group_dm"
    GUILD_CATEGORY = "guild_category"
    GUILD_ANNOUNCEMENT = "guild_announcement"
    ANNOUNCEMENT_THREAD = "announcement_thread"
    PUBLIC_THREAD = "public_thread"
    PRIVATE_THREAD = "private_thread"
    GUILD_STAGE_VOICE = "guild_stage_voice"
    GUILD_DIRECTORY = "guild_directory"
    GUILD_FORUM = "guild_forum"
    GUILD_MEDIA = "guild_media"


class DiscordChannel(Channel):
    """Discord-specific channel with additional Discord fields.

    Attributes:
        guild_id: The ID of the guild this channel belongs to.
        position: Sorting position of the channel.
        nsfw: Whether the channel is NSFW.
        slowmode_delay: Slowmode delay in seconds.
        discord_type: Discord-specific channel type.
        bitrate: Voice channel bitrate.
        user_limit: Voice channel user limit.
        rate_limit_per_user: Slowmode rate limit.
    """

    guild_id: str = Field(
        default="",
        description="The ID of the guild this channel belongs to.",
    )
    position: int = Field(
        default=0,
        description="Sorting position of the channel.",
    )
    nsfw: bool = Field(
        default=False,
        description="Whether the channel is NSFW.",
    )
    slowmode_delay: int = Field(
        default=0,
        description="Slowmode delay in seconds.",
    )
    discord_type: DiscordChannelType = Field(
        default=DiscordChannelType.GUILD_TEXT,
        description="Discord-specific channel type.",
    )
    bitrate: Optional[int] = Field(
        default=None,
        description="Voice channel bitrate.",
    )
    user_limit: Optional[int] = Field(
        default=None,
        description="Voice channel user limit.",
    )
    rate_limit_per_user: int = Field(
        default=0,
        description="Slowmode rate limit.",
    )

    @property
    def is_voice(self) -> bool:
        """Check if this is a voice channel.

        Returns:
            bool: True if this is a voice channel.
        """
        return self.discord_type in (
            DiscordChannelType.GUILD_VOICE,
            DiscordChannelType.GUILD_STAGE_VOICE,
        )

    @property
    def is_text(self) -> bool:
        """Check if this is a text channel.

        Returns:
            bool: True if this is a text channel.
        """
        return self.discord_type in (
            DiscordChannelType.GUILD_TEXT,
            DiscordChannelType.GUILD_ANNOUNCEMENT,
            DiscordChannelType.DM,
            DiscordChannelType.GROUP_DM,
        )
