"""Backend configuration for chatom.

This module provides base classes for configuring chat backends.
"""

from typing import Any, Dict

from pydantic import Field, SecretStr

from .base import BaseModel

__all__ = ("BackendConfig",)


class BackendConfig(BaseModel):
    """Base configuration for a chat backend.

    Subclass this for backend-specific configuration options.

    This base class provides common patterns for configuration:
    - get_secret(field_name): Get a SecretStr field's value as a plain string
    - has_field(field_name): Check if a field has a non-empty value

    Attributes:
        api_token: Authentication token for the backend API.
        api_url: Base URL for the backend API.
        timeout: Request timeout in seconds.
        retry_count: Number of retries for failed requests.
        extra: Additional backend-specific configuration.
    """

    api_token: str = Field(
        default="",
        description="Authentication token for the backend API.",
    )
    api_url: str = Field(
        default="",
        description="Base URL for the backend API.",
    )
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds.",
    )
    retry_count: int = Field(
        default=3,
        description="Number of retries for failed requests.",
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional backend-specific configuration.",
    )

    def get_secret(self, field_name: str) -> str:
        """Get a SecretStr field's value as a plain string.

        This is a helper method to avoid repeating the pattern of
        `self.field.get_secret_value()` in every config class.

        Args:
            field_name: The name of the SecretStr field.

        Returns:
            The secret value as a plain string, or empty string if not set.

        Raises:
            AttributeError: If the field doesn't exist.
            TypeError: If the field is not a SecretStr.

        Example:
            >>> config.get_secret("password")
            "my-secret-password"
        """
        value = getattr(self, field_name, None)
        if value is None:
            return ""
        if isinstance(value, SecretStr):
            return value.get_secret_value()
        return str(value)

    def has_field(self, field_name: str) -> bool:
        """Check if a field has a non-empty value.

        This is a helper method to check if optional configuration
        fields are set. Works with strings, SecretStr, and other types.

        Args:
            field_name: The name of the field to check.

        Returns:
            True if the field has a non-empty value.

        Example:
            >>> config.has_field("api_token")
            True
        """
        value = getattr(self, field_name, None)
        if value is None:
            return False
        if isinstance(value, SecretStr):
            return bool(value.get_secret_value())
        if isinstance(value, str):
            return bool(value)
        if isinstance(value, (list, dict)):
            return bool(value)
        return True

    @property
    def has_token(self) -> bool:
        """Check if an API token is configured.

        Returns:
            True if api_token is set.
        """
        return bool(self.api_token)

    @property
    def has_url(self) -> bool:
        """Check if an API URL is configured.

        Returns:
            True if api_url is set.
        """
        return bool(self.api_url)
