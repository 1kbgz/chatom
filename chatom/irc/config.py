"""IRC backend configuration.

This module provides configuration classes for the IRC backend.
"""

from typing import List

from pydantic import Field, SecretStr

from ..backend import BackendConfig

__all__ = ("IRCConfig",)


class IRCConfig(BackendConfig):
    """Configuration for IRC backend.

    This configuration is used to connect to an IRC server
    using the irc package's asyncio client.

    Attributes:
        server: The IRC server hostname.
        port: The IRC server port (default: 6667, SSL: 6697).
        nickname: The bot's nickname.
        username: The username/ident.
        realname: The "real name" or GECOS field.
        password: Server password (if required).
        nickserv_password: NickServ password for authentication.
        use_ssl: Whether to use SSL/TLS.
        auto_join_channels: Channels to join on connect.

    Example:
        >>> config = IRCConfig(
        ...     server="irc.libera.chat",
        ...     port=6697,
        ...     nickname="mybot",
        ...     use_ssl=True,
        ...     auto_join_channels=["#mychannel"],
        ... )
        >>> backend = IRCBackend(config=config)
    """

    server: str = Field(
        default="",
        description="The IRC server hostname.",
    )
    port: int = Field(
        default=6667,
        description="The IRC server port.",
    )
    nickname: str = Field(
        default="",
        description="The bot's nickname.",
    )
    username: str = Field(
        default="",
        description="The username/ident.",
    )
    realname: str = Field(
        default="",
        description="The 'real name' or GECOS field.",
    )
    password: SecretStr = Field(
        default=SecretStr(""),
        description="Server password (if required).",
    )
    nickserv_password: SecretStr = Field(
        default=SecretStr(""),
        description="NickServ password for authentication.",
    )
    use_ssl: bool = Field(
        default=False,
        description="Whether to use SSL/TLS.",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates.",
    )
    auto_join_channels: List[str] = Field(
        default_factory=list,
        description="Channels to join on connect.",
    )
    command_prefix: str = Field(
        default="!",
        description="Prefix for bot commands.",
    )

    @property
    def password_str(self) -> str:
        """Get the server password as a plain string.

        Returns:
            The password string.
        """
        return self.password.get_secret_value()

    @property
    def nickserv_password_str(self) -> str:
        """Get the NickServ password as a plain string.

        Returns:
            The NickServ password string.
        """
        return self.nickserv_password.get_secret_value()

    @property
    def has_server(self) -> bool:
        """Check if a server is configured.

        Returns:
            True if a server is set.
        """
        return bool(self.server)

    @property
    def has_nickname(self) -> bool:
        """Check if a nickname is configured.

        Returns:
            True if a nickname is set.
        """
        return bool(self.nickname)

    @property
    def effective_username(self) -> str:
        """Get the effective username (falls back to nickname).

        Returns:
            The username or nickname.
        """
        return self.username or self.nickname

    @property
    def effective_realname(self) -> str:
        """Get the effective realname (falls back to nickname).

        Returns:
            The realname or nickname.
        """
        return self.realname or self.nickname
