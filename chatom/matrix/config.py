"""Matrix backend configuration.

This module provides configuration classes for the Matrix backend.
"""

from pydantic import Field, SecretStr

from ..backend import BackendConfig

__all__ = ("MatrixConfig",)


class MatrixConfig(BackendConfig):
    """Configuration for Matrix backend.

    This configuration is used to connect to a Matrix homeserver
    using the matrix-python-sdk or similar library.

    Attributes:
        homeserver_url: The Matrix homeserver URL (e.g., https://matrix.org).
        access_token: Matrix access token for authentication.
        user_id: The Matrix user ID (@user:server).
        device_id: Optional device ID for this session.
        sync_filter_limit: Maximum messages per room in sync.
        validate_cert: Whether to validate the homeserver's TLS certificate.

    Example:
        >>> config = MatrixConfig(
        ...     homeserver_url="https://matrix.org",
        ...     access_token="your-access-token",
        ...     user_id="@mybot:matrix.org",
        ... )
        >>> backend = MatrixBackend(config=config)
    """

    homeserver_url: str = Field(
        default="",
        description="The Matrix homeserver URL (e.g., https://matrix.org).",
    )
    access_token: SecretStr = Field(
        default=SecretStr(""),
        description="Matrix access token for authentication.",
    )
    user_id: str = Field(
        default="",
        description="The Matrix user ID (@user:server).",
    )
    device_id: str = Field(
        default="",
        description="Optional device ID for this session.",
    )
    sync_filter_limit: int = Field(
        default=20,
        description="Maximum messages per room in sync.",
    )
    validate_cert: bool = Field(
        default=True,
        description="Whether to validate the homeserver's TLS certificate.",
    )
    sync_timeout_ms: int = Field(
        default=30000,
        description="Timeout for sync requests in milliseconds.",
    )

    @property
    def access_token_str(self) -> str:
        """Get the access token as a plain string.

        Returns:
            The access token string.
        """
        return self.access_token.get_secret_value()

    @property
    def has_token(self) -> bool:
        """Check if an access token is configured.

        Returns:
            True if an access token is set.
        """
        return bool(self.access_token.get_secret_value())

    @property
    def has_homeserver(self) -> bool:
        """Check if a homeserver URL is configured.

        Returns:
            True if a homeserver URL is set.
        """
        return bool(self.homeserver_url)
