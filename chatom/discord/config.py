"""Discord backend configuration.

This module provides configuration classes for the Discord backend.
"""

from typing import Optional

from pydantic import Field, SecretStr

from ..backend import BackendConfig

__all__ = ("DiscordConfig",)


class DiscordConfig(BackendConfig):
    """Configuration for Discord backend.

    This configuration is used to connect to Discord using the discord.py library.
    You need a bot token from the Discord Developer Portal.

    Attributes:
        bot_token: Discord bot token.
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

    bot_token: SecretStr = Field(
        default=SecretStr(""),
        description="Discord bot token from Developer Portal.",
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

    @property
    def bot_token_str(self) -> str:
        """Get the bot token as a plain string.

        Returns:
            The bot token string.
        """
        return self.bot_token.get_secret_value()

    @property
    def has_token(self) -> bool:
        """Check if a bot token is configured.

        Returns:
            True if a bot token is set.
        """
        return bool(self.bot_token.get_secret_value())
