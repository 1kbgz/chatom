"""Slack backend configuration.

This module provides configuration classes for the Slack backend.
"""

from pathlib import Path
from ssl import SSLContext
from typing import Optional, Union

from pydantic import Field, SecretStr, field_validator

from ..backend import BackendConfig

__all__ = ("SlackConfig",)


class SlackConfig(BackendConfig):
    """Configuration for Slack backend.

    Attributes:
        bot_token: Slack Bot User OAuth Token (xoxb-...) or path to file.
        app_token: Slack App-Level Token (xapp-...) or path to file.
        signing_secret: Slack signing secret for request verification.
        team_id: The Slack workspace/team ID.
        default_channel: Default channel ID for sending messages.
        socket_mode: Whether to use Socket Mode for events.
        ssl: Optional SSL context for connections.

    Example:
        >>> config = SlackConfig(
        ...     bot_token="xoxb-your-token",
        ...     app_token="xapp-your-app-token",  # For Socket Mode
        ...     signing_secret="your-signing-secret",
        ... )
        >>> backend = SlackBackend(config=config)
    """

    model_config = {"arbitrary_types_allowed": True}

    bot_token: SecretStr = Field(
        default=SecretStr(""),
        description="Slack Bot User OAuth Token (xoxb-...) or path to file.",
    )
    app_token: SecretStr = Field(
        default=SecretStr(""),
        description="Slack App-Level Token (xapp-...) or path to file.",
    )
    signing_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Slack signing secret for request verification.",
    )
    team_id: str = Field(
        default="",
        description="The Slack workspace/team ID.",
    )
    default_channel: str = Field(
        default="",
        description="Default channel ID for sending messages.",
    )
    socket_mode: bool = Field(
        default=False,
        description="Whether to use Socket Mode for events.",
    )
    ssl: Optional[SSLContext] = Field(
        default=None,
        description="Optional SSL context for connections.",
    )

    @field_validator("app_token", mode="before")
    @classmethod
    def validate_app_token(cls, v: Union[str, SecretStr, None]) -> SecretStr:
        """Validate app token - can be a token string or path to file."""
        if v is None or v == "":
            return SecretStr("")
        if isinstance(v, SecretStr):
            return v
        if isinstance(v, str):
            if v.startswith("xapp-"):
                return SecretStr(v)
            elif Path(v).exists():
                return SecretStr(Path(v).read_text().strip())
        raise ValueError("App token must start with 'xapp-' or be a file path")

    @field_validator("bot_token", mode="before")
    @classmethod
    def validate_bot_token(cls, v: Union[str, SecretStr, None]) -> SecretStr:
        """Validate bot token - can be a token string or path to file."""
        if v is None or v == "":
            return SecretStr("")
        if isinstance(v, SecretStr):
            return v
        if isinstance(v, str):
            if v.startswith("xoxb-"):
                return SecretStr(v)
            elif Path(v).exists():
                return SecretStr(Path(v).read_text().strip())
        raise ValueError("Bot token must start with 'xoxb-' or be a file path")

    @property
    def bot_token_str(self) -> str:
        """Get the bot token as a plain string.

        Returns:
            The bot token string.
        """
        return self.bot_token.get_secret_value()

    @property
    def app_token_str(self) -> str:
        """Get the app token as a plain string.

        Returns:
            The app token string.
        """
        return self.app_token.get_secret_value()

    @property
    def signing_secret_str(self) -> str:
        """Get the signing secret as a plain string.

        Returns:
            The signing secret string.
        """
        return self.signing_secret.get_secret_value()

    @property
    def has_socket_mode(self) -> bool:
        """Check if Socket Mode is configured.

        Returns True if both socket_mode is enabled and app_token is set.

        Returns:
            True if Socket Mode is configured, False otherwise.
        """
        return self.socket_mode or bool(self.app_token.get_secret_value())
