"""Slack backend configuration.

This module provides configuration classes for the Slack backend.
"""

from pydantic import Field, SecretStr

from ..backend import BackendConfig

__all__ = ("SlackConfig",)


class SlackConfig(BackendConfig):
    """Configuration for Slack backend.

    Attributes:
        bot_token: Slack Bot User OAuth Token (xoxb-...).
        app_token: Slack App-Level Token (xapp-...) for Socket Mode.
        signing_secret: Slack signing secret for request verification.
        team_id: The Slack workspace/team ID.
        default_channel: Default channel ID for sending messages.
        socket_mode: Whether to use Socket Mode for events.

    Example:
        >>> config = SlackConfig(
        ...     bot_token="xoxb-your-token",
        ...     app_token="xapp-your-app-token",  # For Socket Mode
        ...     signing_secret="your-signing-secret",
        ... )
        >>> backend = SlackBackend(config=config)
    """

    bot_token: SecretStr = Field(
        default=SecretStr(""),
        description="Slack Bot User OAuth Token (xoxb-...).",
    )
    app_token: SecretStr = Field(
        default=SecretStr(""),
        description="Slack App-Level Token (xapp-...) for Socket Mode.",
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
