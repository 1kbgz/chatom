"""LINE Messaging API configuration."""

from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator

from ..backend import BackendConfig

__all__ = ("LineConfig",)


class LineConfig(BackendConfig):
    """Configuration for a LINE Official Account bot."""

    api_url: str = "https://api.line.me"
    data_api_url: str = "https://api-data.line.me"
    channel_access_token: SecretStr = Field(default=SecretStr(""))
    channel_secret: SecretStr = Field(default=SecretStr(""))

    @field_validator("channel_access_token", "channel_secret", mode="before")
    @classmethod
    def _load_secret(cls, value: Any) -> Any:
        if not isinstance(value, str) or not value:
            return value
        path = Path(value)
        if path.is_file():
            return SecretStr(path.read_text().strip())
        return SecretStr(value)

    @property
    def channel_access_token_str(self) -> str:
        """Return channel access token as plain text."""
        return self.channel_access_token.get_secret_value()

    @property
    def channel_secret_str(self) -> str:
        """Return channel secret as plain text."""
        return self.channel_secret.get_secret_value()
