"""IRC backend configuration."""

from pydantic import Field, SecretStr, field_validator

from ..backend import BackendConfig

__all__ = ("IRCConfig",)


class IRCConfig(BackendConfig):
    """Connection settings for an IRC server."""

    server: str = Field(default="", description="IRC server hostname.")
    port: int = Field(default=6697, ge=1, le=65535)
    nickname: str = Field(default="chatom", min_length=1)
    username: str = Field(default="chatom", min_length=1)
    realname: str = Field(default="chatom bot", min_length=1)
    password: SecretStr = Field(default=SecretStr(""))
    use_tls: bool = True
    tls_verify: bool = True
    channels: list[str] = Field(default_factory=list)

    @field_validator("password", mode="before")
    @classmethod
    def _load_password(cls, value):
        if isinstance(value, str):
            try:
                from pathlib import Path

                path = Path(value)
                if value and path.is_file():
                    value = path.read_text().strip()
            except OSError:
                pass
            return SecretStr(value)
        return value

    @property
    def password_str(self) -> str:
        return self.password.get_secret_value()
