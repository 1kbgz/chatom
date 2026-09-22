"""Matrix backend configuration."""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator

from ..backend.backend_config import BackendConfig

__all__ = ("MatrixConfig",)


class MatrixConfig(BackendConfig):
    """Configuration for a Matrix client session."""

    homeserver: str = Field(default="", description="Matrix homeserver URL.")
    user_id: str = Field(default="", description="Full Matrix user ID.")
    access_token: SecretStr = Field(default=SecretStr(""), description="Existing Matrix access token.")
    password: SecretStr = Field(default=SecretStr(""), description="Password used when no access token is supplied.")
    device_id: str = Field(default="", description="Existing Matrix device ID.")
    device_name: str = Field(default="chatom", description="Device name used for password login.")
    store_path: str = Field(default="", description="matrix-nio store directory.")
    sync_timeout: int = Field(default=30000, description="Long-poll timeout in milliseconds.")

    @field_validator("access_token", "password", mode="before")
    @classmethod
    def _load_secret(cls, value):
        """Load credentials from an existing file path."""
        if isinstance(value, str):
            path = Path(value).expanduser()
            if value and path.is_file():
                value = path.read_text().strip()
            return SecretStr(value)
        return value

    @property
    def access_token_str(self) -> str:
        """Return unwrapped access token."""
        return self.access_token.get_secret_value()

    @property
    def password_str(self) -> str:
        """Return unwrapped password."""
        return self.password.get_secret_value()
