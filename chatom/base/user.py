"""User model for chatom.

This module provides the base User class representing a chat platform user.
"""

from .base import Field, Identifiable

__all__ = ("User",)


class User(Identifiable):
    """Represents a user on a chat platform.

    Attributes:
        id: Platform-specific unique identifier.
        name: Display name of the user.
        handle: Username or handle (e.g., @username).
        email: Email address of the user, if available.
        avatar_url: URL to the user's avatar image.
        is_bot: Whether the user is a bot.
    """

    handle: str = Field(
        default="",
        description="Username or handle (e.g., @username).",
    )
    email: str = Field(
        default="",
        description="Email address of the user, if available.",
    )
    avatar_url: str = Field(
        default="",
        description="URL to the user's avatar image.",
    )
    is_bot: bool = Field(
        default=False,
        description="Whether the user is a bot.",
    )

    @property
    def display_name(self) -> str:
        """Get the best available display name for the user.

        Returns:
            str: The name, handle, or id (in order of preference).
        """
        return self.name or self.handle or self.id

    @property
    def mention_name(self) -> str:
        """Get the best name to use when mentioning the user.

        Returns:
            str: The handle or name, whichever is available.
        """
        return self.handle or self.name
