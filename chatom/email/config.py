"""Email backend configuration.

This module provides configuration classes for the Email backend.
"""

from pydantic import Field, SecretStr

from ..backend import BackendConfig

__all__ = ("EmailConfig",)


class EmailConfig(BackendConfig):
    """Configuration for Email backend.

    This configuration is used to connect to email servers
    using the native Python smtplib and imaplib libraries.

    Attributes:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port.
        smtp_use_ssl: Whether to use SSL for SMTP.
        smtp_use_tls: Whether to use STARTTLS for SMTP.
        imap_host: IMAP server hostname.
        imap_port: IMAP server port.
        imap_use_ssl: Whether to use SSL for IMAP.
        username: Email username/address for authentication.
        password: Email password.
        from_address: Default "From" address for outgoing emails.
        from_name: Default "From" name for outgoing emails.

    Example:
        >>> config = EmailConfig(
        ...     smtp_host="smtp.gmail.com",
        ...     smtp_port=587,
        ...     smtp_use_tls=True,
        ...     imap_host="imap.gmail.com",
        ...     imap_port=993,
        ...     imap_use_ssl=True,
        ...     username="mybot@gmail.com",
        ...     password="app-password",
        ... )
        >>> backend = EmailBackend(config=config)
    """

    smtp_host: str = Field(
        default="",
        description="SMTP server hostname.",
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port.",
    )
    smtp_use_ssl: bool = Field(
        default=False,
        description="Whether to use SSL for SMTP (port 465).",
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="Whether to use STARTTLS for SMTP.",
    )
    imap_host: str = Field(
        default="",
        description="IMAP server hostname.",
    )
    imap_port: int = Field(
        default=993,
        description="IMAP server port.",
    )
    imap_use_ssl: bool = Field(
        default=True,
        description="Whether to use SSL for IMAP.",
    )
    username: str = Field(
        default="",
        description="Email username/address for authentication.",
    )
    password: SecretStr = Field(
        default=SecretStr(""),
        description="Email password.",
    )
    from_address: str = Field(
        default="",
        description="Default 'From' address for outgoing emails.",
    )
    from_name: str = Field(
        default="",
        description="Default 'From' name for outgoing emails.",
    )
    default_mailbox: str = Field(
        default="INBOX",
        description="Default IMAP mailbox to select.",
    )
    signature: str = Field(
        default="",
        description="Email signature to append to messages.",
    )

    @property
    def password_str(self) -> str:
        """Get the password as a plain string.

        Returns:
            The password string.
        """
        return self.password.get_secret_value()

    @property
    def has_smtp(self) -> bool:
        """Check if SMTP is configured.

        Returns:
            True if SMTP host is set.
        """
        return bool(self.smtp_host)

    @property
    def has_imap(self) -> bool:
        """Check if IMAP is configured.

        Returns:
            True if IMAP host is set.
        """
        return bool(self.imap_host)

    @property
    def effective_from_address(self) -> str:
        """Get the effective from address (falls back to username).

        Returns:
            The from address or username.
        """
        return self.from_address or self.username

    @property
    def formatted_from(self) -> str:
        """Get the formatted From header value.

        Returns:
            "Name <email>" or just email.
        """
        if self.from_name:
            return f"{self.from_name} <{self.effective_from_address}>"
        return self.effective_from_address
