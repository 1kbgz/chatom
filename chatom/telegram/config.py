"""Telegram-specific configuration.

This module provides the Telegram-specific configuration class.
"""

from pydantic import Field, SecretStr, field_validator

from ..backend.backend_config import BackendConfig

__all__ = ("TelegramConfig",)


class TelegramConfig(BackendConfig):
    """Configuration for the Telegram backend.

    Attributes:
        bot_token: The Telegram Bot API token (from @BotFather).
        api_url: Custom Telegram Bot API URL (for local API servers).
        timeout: HTTP request timeout in seconds.
        connect_timeout: Connection timeout in seconds.
        read_timeout: Read timeout in seconds.
        write_timeout: Write timeout in seconds.
        pool_timeout: Connection pool timeout in seconds.
    """

    bot_token: SecretStr = Field(
        default=SecretStr(""),
        description="Telegram Bot API token from @BotFather.",
    )
    connect_timeout: float = Field(
        default=5.0,
        description="Connection timeout in seconds.",
    )
    read_timeout: float = Field(
        default=5.0,
        description="Read timeout in seconds.",
    )
    write_timeout: float = Field(
        default=5.0,
        description="Write timeout in seconds.",
    )
    pool_timeout: float = Field(
        default=1.0,
        description="Connection pool timeout in seconds.",
    )

    @field_validator("bot_token", mode="before")
    @classmethod
    def _load_bot_token(cls, v):
        """Support loading token from a file path."""
        if isinstance(v, str):
            if v and not v.startswith(("bot", " ")) and "/" in v:
                try:
                    with open(v) as f:
                        v = f.read().strip()
                except (OSError, IOError):
                    pass
            return SecretStr(v) if not isinstance(v, SecretStr) else v
        return v

    @property
    def bot_token_str(self) -> str:
        """Get the bot token as a plain string."""
        return self.bot_token.get_secret_value()

    @property
    def has_token(self) -> bool:
        """Check if a bot token is configured."""
        return bool(self.bot_token_str)
