"""Discord-specific User model.

This module provides the Discord-specific User class.
"""

from typing import Optional

from chatom.base import Field, User

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

    @property
    def display_name(self) -> str:
        """Get the best display name for Discord.

        Returns:
            str: Global name, name, or handle.
        """
        return self.global_name or self.name or self.handle or self.id

    @property
    def full_username(self) -> str:
        """Get the full username with discriminator (legacy format).

        Returns:
            str: Username#discriminator or just username for new usernames.
        """
        if self.discriminator and self.discriminator != "0":
            return f"{self.handle}#{self.discriminator}"
        return self.handle
