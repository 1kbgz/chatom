"""Telegram-specific Presence model.

This module provides the Telegram-specific Presence class.

Note: Telegram has very limited presence support. Bots cannot see
user online/offline status. Only "last seen" approximations are
available for some users, and even that is privacy-controlled.
"""

from chatom.base import Field, Presence

__all__ = ("TelegramPresence",)


class TelegramPresence(Presence):
    """Telegram-specific presence.

    Telegram provides limited presence information. Bots can only see
    a user's status if the user has not restricted that in privacy settings.

    Attributes:
        last_seen_approximate: Approximate last seen description
            (e.g. "recently", "within a week", "within a month", "long time ago").
    """

    last_seen_approximate: str = Field(
        default="",
        description="Approximate last seen description.",
    )
