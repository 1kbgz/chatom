"""Discord-specific Guild (Organization) model.

This module provides the Discord-specific Guild class which extends Organization.
"""

from typing import Any, Optional

from chatom.base import Field, Organization

from .user import DiscordUser

__all__ = ("DiscordGuild",)


class DiscordGuild(Organization):
    """Discord-specific guild (server) with additional Discord fields.

    A Discord guild is the organization unit in Discord (commonly called a "server").

    Attributes:
        premium_tier: The guild's boost level (0-3).
        nsfw_level: The guild's NSFW content level.
        preferred_locale: The guild's preferred locale.
        approximate_member_count: Approximate number of members (may differ from member_count).
        approximate_presence_count: Approximate number of online members.
        vanity_url_code: The guild's vanity invite code if set.
        features: List of guild features (e.g., "COMMUNITY", "PARTNERED").
    """

    premium_tier: int = Field(
        default=0,
        description="The guild's boost level (0-3).",
    )
    nsfw_level: int = Field(
        default=0,
        description="The guild's NSFW content level.",
    )
    preferred_locale: str = Field(
        default="en-US",
        description="The guild's preferred locale.",
    )
    approximate_member_count: Optional[int] = Field(
        default=None,
        description="Approximate number of members.",
    )
    approximate_presence_count: Optional[int] = Field(
        default=None,
        description="Approximate number of online members.",
    )
    vanity_url_code: Optional[str] = Field(
        default=None,
        description="The guild's vanity invite code if set.",
    )
    features: list = Field(
        default_factory=list,
        description="List of guild features.",
    )

    @classmethod
    def from_discord_guild(cls, guild: Any) -> "DiscordGuild":
        """Create a DiscordGuild from a discord.py Guild object.

        Args:
            guild: A discord.py Guild object.

        Returns:
            DiscordGuild instance.
        """
        return cls(
            id=str(guild.id),
            name=guild.name,
            description=guild.description or "",
            icon_url=str(guild.icon.url) if guild.icon else "",
            member_count=guild.member_count,
            owner=DiscordUser.from_discord_user(guild.owner) if guild.owner else None,
            premium_tier=guild.premium_tier,
            nsfw_level=guild.nsfw_level.value if hasattr(guild.nsfw_level, "value") else 0,
            preferred_locale=str(guild.preferred_locale),
            approximate_member_count=guild.approximate_member_count,
            approximate_presence_count=guild.approximate_presence_count,
            vanity_url_code=guild.vanity_url_code,
            features=list(guild.features) if guild.features else [],
        )
