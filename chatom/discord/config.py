"""Discord backend configuration.

This module provides configuration classes for the Discord backend.
"""

from pathlib import Path
from typing import Optional, Union

from pydantic import Field, SecretStr, field_validator

from ..backend import BackendConfig

__all__ = ("DiscordConfig",)


class DiscordConfig(BackendConfig):
    """Configuration for Discord backend.

    This configuration is used to connect to Discord using the discord.py library.
    You need a bot token from the Discord Developer Portal.

    Attributes:
        bot_token: Discord bot token (can be a file path).
        application_id: Discord application ID.
        guild_id: Default guild/server ID (optional).
        intents: Discord gateway intents to request.
        command_prefix: Prefix for bot commands (if using commands extension).

    Example:
        >>> config = DiscordConfig(
        ...     bot_token="your-bot-token",
        ...     application_id="123456789",
        ...     intents=["guilds", "messages", "message_content"],
        ... )
        >>> backend = DiscordBackend(config=config)
    """

    token: Union[str, SecretStr] = Field(
        default=SecretStr(""),
        description="Discord bot token from Developer Portal (can be a file path).",
    )
    application_id: str = Field(
        default="",
        description="Discord application ID.",
    )
    guild_id: str = Field(
        default="",
        description="Default guild/server ID (optional).",
    )
    intents: list = Field(
        default_factory=lambda: ["guilds", "messages"],
        description="Discord gateway intents to request.",
    )
    command_prefix: str = Field(
        default="!",
        description="Prefix for bot commands.",
    )
    shard_id: Optional[int] = Field(
        default=None,
        description="Shard ID for sharded bots.",
    )
    shard_count: Optional[int] = Field(
        default=None,
        description="Total number of shards.",
    )

    @field_validator("token", mode="before")
    @classmethod
    def validate_token(cls, v):
        """Validate and load bot token, supporting file paths."""
        if v is None or v == "":
            return SecretStr("")

        # Handle SecretStr input
        if isinstance(v, SecretStr):
            v = v.get_secret_value()

        # Check for empty string after extracting from SecretStr
        if not v:
            return SecretStr("")

        # Check if it's a file path (but not a directory or special path)
        path = Path(v)
        if path.exists() and path.is_file():
            v = path.read_text().strip()

        # Accept any non-empty token (don't validate length for flexibility in testing)
        if v:
            return SecretStr(v)

        raise ValueError("Token must be a valid Discord bot token or a file path containing one")

    @property
    def bot_token_str(self) -> str:
        """Get the bot token as a plain string.

        Returns:
            The bot token string.
        """
        return self.token.get_secret_value() if isinstance(self.token, SecretStr) else self.token

    @property
    def has_token(self) -> bool:
        """Check if a bot token is configured.

        Returns:
            True if a bot token is set.
        """
        return bool(self.token.get_secret_value() if isinstance(self.token, SecretStr) else self.token)
