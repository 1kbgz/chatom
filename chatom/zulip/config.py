"""Zulip backend configuration."""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator

from ..backend import BackendConfig

__all__ = ("ZulipConfig",)


class ZulipConfig(BackendConfig):
    """Credentials and defaults for a Zulip bot or user."""

    site: str = Field(default="", description="Zulip organization URL.")
    email: str = Field(default="", description="Bot or user API email address.")
    api_key: str | SecretStr = Field(default=SecretStr(""), description="Zulip API key or path to a file containing it.")
    config_file: str | None = Field(default=None, description="Path to a zuliprc file. Takes precedence over explicit credentials.")
    client_name: str = Field(default="chatom", description="Client name reported to Zulip.")
    default_topic: str = Field(default="chatom", description="Topic used when sending a channel message without a thread or topic.")
    insecure: bool = Field(default=False, description="Disable TLS certificate verification.")

    @field_validator("api_key", mode="before")
    @classmethod
    def _load_api_key(cls, value: str | SecretStr | None) -> SecretStr:
        if value is None:
            return SecretStr("")
        if isinstance(value, SecretStr):
            return value
        if isinstance(value, str):
            path = Path(value).expanduser()
            if value and path.is_file():
                return SecretStr(path.read_text().strip())
            return SecretStr(value)
        raise ValueError("api_key must be a string, SecretStr, or file path")

    @property
    def api_key_str(self) -> str:
        """Return API key without SecretStr wrapping."""
        return self.api_key.get_secret_value() if isinstance(self.api_key, SecretStr) else self.api_key
