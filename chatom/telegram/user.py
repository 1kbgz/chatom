"""Telegram-specific User model.

This module provides the Telegram-specific User class.
"""

from typing import Any, Self

from pydantic import model_validator

from chatom.base import Field, User
from chatom.base.conversion import register_backend_type

__all__ = ("TelegramUser",)


class TelegramUser(User):
    """Telegram-specific user with additional Telegram fields.

    Attributes:
        first_name: User's first name.
        last_name: User's last name.
        username: User's Telegram username (without @).
        language_code: IETF language tag of the user's language.
        is_premium: Whether the user has Telegram Premium.
        added_to_attachment_menu: Whether the user added the bot to attachment menu.
    """

    first_name: str = Field(
        default="",
        description="User's first name.",
    )
    last_name: str = Field(
        default="",
        description="User's last name.",
    )
    username: str = Field(
        default="",
        description="User's Telegram username (without @).",
    )
    language_code: str = Field(
        default="",
        description="IETF language tag of the user's language.",
    )
    is_premium: bool = Field(
        default=False,
        description="Whether the user has Telegram Premium.",
    )
    added_to_attachment_menu: bool = Field(
        default=False,
        description="Whether the user added the bot to attachment menu.",
    )

    @model_validator(mode="after")
    def _set_display_name(self) -> Self:
        """Set display_name from first_name + last_name if not explicitly set."""
        if not self.__dict__.get("display_name"):
            full = f"{self.first_name} {self.last_name}".strip() if self.first_name else ""
            object.__setattr__(self, "display_name", full or self.name or self.username or self.handle or self.id)
        return self

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p)

    @classmethod
    def from_telegram_user(cls, user: Any) -> "TelegramUser":
        """Create a TelegramUser from a python-telegram-bot User object.

        Args:
            user: A telegram.User object.

        Returns:
            A TelegramUser instance.
        """
        return cls(
            id=str(user.id),
            name=user.full_name or user.first_name or "",
            handle=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            username=user.username or "",
            language_code=user.language_code or "",
            is_bot=user.is_bot,
            is_premium=getattr(user, "is_premium", False) or False,
            added_to_attachment_menu=getattr(user, "added_to_attachment_menu", False) or False,
        )


# Register with conversion system
register_backend_type("telegram", User, TelegramUser)
