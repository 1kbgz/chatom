"""Discord-specific User model.

This module provides the Discord-specific User class.
"""

from typing import Any, Optional, Self

from pydantic import model_validator

from chatom.base import Avatar, Field, User

__all__ = ("DiscordUser",)


class DiscordUser(User):
    """Discord-specific user with additional Discord fields.

    Attributes:
        discriminator: The user's 4-digit discriminator (legacy).
        global_name: The user's global display name.
        is_system: Whether this is a Discord system user.
        accent_color: The user's banner color.
        banner_url: URL to the user's banner image.
    """

    discriminator: str = Field(
        default="0",
        description="The user's 4-digit discriminator (legacy).",
    )
    global_name: Optional[str] = Field(
        default=None,
        description="The user's global display name.",
    )
    is_system: bool = Field(
        default=False,
        description="Whether this is a Discord system user.",
    )
    accent_color: Optional[int] = Field(
        default=None,
        description="The user's banner color.",
    )
    banner_url: str = Field(
        default="",
        description="URL to the user's banner image.",
    )

    @model_validator(mode="after")
    def _set_display_name(self) -> Self:
        """Set display_name from global_name if not explicitly set."""
        if not self.__dict__.get("display_name"):
            # Use object.__setattr__ to bypass pydantic validation
            object.__setattr__(self, "display_name", self.global_name or self.name or self.handle or self.id)
        return self

    @property
    def full_username(self) -> str:
        """Get the full username with discriminator (legacy format).

        Returns:
            str: Username#discriminator or just username for new usernames.
        """
        if self.discriminator and self.discriminator != "0":
            return f"{self.handle}#{self.discriminator}"
        return self.handle

    @classmethod
    def from_discord_user(cls, user: Any) -> "DiscordUser":
        """Create a DiscordUser from a discord.py User or Member object.

        This factory method converts a discord.py User or Member object
        into a chatom DiscordUser.

        Args:
            user: A discord.py User or Member object.

        Returns:
            A DiscordUser instance.

        Example:
            >>> # From a discord.py event
            >>> discord_user = DiscordUser.from_discord_user(event.author)
        """
        avatar_url = ""
        if hasattr(user, "avatar") and user.avatar:
            avatar_url = str(user.avatar.url) if hasattr(user.avatar, "url") else str(user.avatar)

        banner_url = ""
        if hasattr(user, "banner") and user.banner:
            banner_url = str(user.banner.url) if hasattr(user.banner, "url") else str(user.banner)

        # Create Avatar object if we have a URL
        avatar = Avatar(url=avatar_url) if avatar_url else None

        return cls(
            id=str(user.id),
            name=user.name,
            handle=user.name,
            display_name=getattr(user, "display_name", user.name),
            discriminator=getattr(user, "discriminator", "0"),
            global_name=getattr(user, "global_name", None),
            is_bot=getattr(user, "bot", False),
            is_system=getattr(user, "system", False),
            avatar=avatar,
            banner_url=banner_url,
            accent_color=getattr(user, "accent_color", None) or getattr(user, "accent_colour", None),
        )
