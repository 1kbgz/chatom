"""User model for chatom.

This module provides the base User class representing a chat platform user.
"""

from typing import Optional, Self

from pydantic import model_validator

from .base import Field, Identifiable

__all__ = ("User",)


class Avatar(Identifiable):
    """Represents a user's avatar image.

    Attributes:
        id: Platform-specific unique identifier.
        url: URL to the avatar image.
        is_default: Whether this is the default avatar.
    """

    url: str = Field(
        default="",
        description="URL to the avatar image.",
    )
    is_default: bool = Field(
        default=False,
        description="Whether this is the default avatar.",
    )


class User(Identifiable):
    """Represents a user on a chat platform.

    Attributes:
        id: Platform-specific unique identifier.
        name: Display name of the user.
        display_name: Display name (alias, can differ from name).
        handle: Username or handle (e.g., @username).
        email: Email address of the user, if available.
        avatar_url: URL to the user's avatar image.
        is_bot: Whether the user is a bot.
        app_id: App ID associated with the bot (for bot users).
    """

    display_name: str = Field(
        default="",
        description="Display name (can differ from name).",
    )
    handle: str = Field(
        default="",
        description="Username or handle (e.g., @username).",
    )
    email: str = Field(
        default="",
        description="Email address of the user, if available.",
    )
    avatar: Optional[Avatar] = Field(
        default=None,
        description="User's Avatar",
    )
    is_bot: bool = Field(
        default=False,
        description="Whether the user is a bot.",
    )
    app_id: Optional[str] = Field(
        default=None,
        description="App ID associated with the bot (for bot users).",
    )

    @model_validator(mode="after")
    def _set_display_name(self) -> Self:
        """Set display_name from name/handle if not explicitly set."""
        if not self.__dict__.get("display_name"):
            # Use object.__setattr__ to bypass pydantic validation
            object.__setattr__(self, "display_name", self.name or self.handle or self.id)
        return self

    @property
    def best_display_name(self) -> str:
        """Get the best available display name for the user.

        Returns:
            str: The display_name, name, handle, or id (in order of preference).
        """
        return self.display_name or self.name or self.handle or self.id

    @property
    def mention_name(self) -> str:
        """Get the best name to use when mentioning the user.

        Returns:
            str: The handle or name, whichever is available.
        """
        return self.handle or self.name

    @property
    def avatar_url(self) -> str:
        """Get the URL to the user's avatar image.

        Returns:
            str: The avatar URL, or empty string if no avatar is set.
        """
        return self.avatar.url if self.avatar else ""

    @property
    def is_resolvable(self) -> bool:
        """Check if this user can be resolved by a backend.

        A user is resolvable if it has an id, name, handle, or email.

        Returns:
            bool: True if the user can potentially be resolved.
        """
        return bool(self.id or self.name or self.handle or self.email)
