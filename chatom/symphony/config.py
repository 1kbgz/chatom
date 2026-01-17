"""Symphony backend configuration.

This module provides the SymphonyConfig class for configuring
the Symphony backend with the Symphony BDK.
"""

import atexit
import os
import tempfile
from typing import Any, Dict, Optional

from pydantic import Field, SecretStr, model_validator

from ..backend import BackendConfig

__all__ = ("SymphonyConfig",)


class SymphonyConfig(BackendConfig):
    """Configuration for the Symphony backend.

    This class holds all Symphony-specific configuration needed
    for the Symphony BDK, including pod URL, bot credentials,
    and optional application settings.

    Attributes:
        host: The Symphony pod hostname (e.g., "mycompany.symphony.com").
        port: The Symphony pod port (default: 443).
        scheme: The URL scheme (default: "https").
        context: Optional context path (default: "").
        bot_username: The bot's username.
        bot_private_key_path: Path to the bot's RSA private key file.
        bot_private_key_content: Direct content of the RSA private key.
        bot_certificate_path: Path to the bot's certificate (for cert auth).
        bot_certificate_content: Direct content of the certificate (PEM format).
            If provided without bot_certificate_path, a temp file is created
            automatically since Symphony BDK requires a file path.
        bot_certificate_password: Password for the certificate.
        app_id: Optional extension app ID.
        app_private_key_path: Path to the app's RSA private key.
        agent_host: Optional separate agent host (if different from pod).
        agent_port: Optional agent port.
        session_auth_host: Optional session auth host (if different from pod).
        session_auth_port: Optional session auth port.
        key_manager_host: Optional key manager host.
        key_manager_port: Optional key manager port.
        trust_store_path: Path to custom trust store.
        proxy_host: Optional proxy host.
        proxy_port: Optional proxy port.
        proxy_username: Optional proxy username.
        proxy_password: Optional proxy password.

    Example:
        >>> # Using RSA key file
        >>> config = SymphonyConfig(
        ...     host="mycompany.symphony.com",
        ...     bot_username="my-bot",
        ...     bot_private_key_path="/path/to/private-key.pem",
        ... )
        >>> backend = SymphonyBackend(config=config)

        >>> # Using certificate content (temp file created automatically)
        >>> config = SymphonyConfig(
        ...     host="mycompany.symphony.com",
        ...     bot_username="my-bot",
        ...     bot_certificate_content=SecretStr(cert_pem_string),
        ... )
    """

    # Pod configuration
    host: str = ""
    port: int = 443
    scheme: str = "https"
    context: str = ""

    # Bot authentication (RSA)
    bot_username: str = ""
    bot_private_key_path: Optional[str] = None
    bot_private_key_content: Optional[SecretStr] = None

    # Bot authentication (Certificate)
    bot_certificate_path: Optional[str] = None
    bot_certificate_content: Optional[SecretStr] = Field(
        default=None,
        description="Direct content of the certificate PEM. If provided without bot_certificate_path, a temp file will be created automatically.",
    )
    bot_certificate_password: Optional[SecretStr] = None

    # Internal: Path to temp cert file (created from bot_certificate_content)
    _temp_cert_path: Optional[str] = None

    # Application configuration (for extension apps)
    app_id: Optional[str] = None
    app_private_key_path: Optional[str] = None

    # Separate agent/keymanager/session auth hosts (optional)
    pod_host: Optional[str] = None
    pod_port: Optional[int] = None
    agent_host: Optional[str] = None
    agent_port: Optional[int] = None
    session_auth_host: Optional[str] = None
    session_auth_port: Optional[int] = None
    key_manager_host: Optional[str] = None
    key_manager_port: Optional[int] = None

    # SSL/Trust configuration
    trust_store_path: Optional[str] = None

    # Proxy configuration
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[SecretStr] = None

    # Connection settings
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @model_validator(mode="after")
    def _handle_certificate_content(self) -> "SymphonyConfig":
        """Create temp file from certificate content if needed.

        Symphony BDK only supports certificate paths, not content directly.
        If bot_certificate_content is provided without bot_certificate_path,
        we create a temporary file and set the path automatically.
        """
        if self.bot_certificate_content and not self.bot_certificate_path:
            # Create temp file for certificate content
            cert_content = self.bot_certificate_content.get_secret_value()
            fd, temp_path = tempfile.mkstemp(suffix=".pem", prefix="chatom_cert_")
            try:
                os.write(fd, cert_content.encode("utf-8"))
            finally:
                os.close(fd)

            # Store and set the temp path
            object.__setattr__(self, "_temp_cert_path", temp_path)
            object.__setattr__(self, "bot_certificate_path", temp_path)

            # Register cleanup on exit
            def cleanup_temp_cert():
                try:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                except OSError:
                    pass

            atexit.register(cleanup_temp_cert)

        return self

    # Custom URL overrides (for non-standard Symphony deployments)
    # Use {sid} for stream ID, {datafeed_id} for datafeed ID, {room_id} for room ID
    message_create_url: Optional[str] = Field(
        None,
        description="Custom URL for message creation. Template: https://{host}/agent/v4/stream/{sid}/message/create",
    )
    datafeed_create_url: Optional[str] = Field(
        None,
        description="Custom URL for datafeed creation. Template: https://{host}/agent/v5/datafeeds",
    )
    datafeed_delete_url: Optional[str] = Field(
        None,
        description="Custom URL for datafeed deletion. Template: https://{host}/agent/v5/datafeeds/{datafeed_id}",
    )
    datafeed_read_url: Optional[str] = Field(
        None,
        description="Custom URL for datafeed reading. Template: https://{host}/agent/v5/datafeeds/{datafeed_id}/read",
    )
    room_search_url: Optional[str] = Field(
        None,
        description="Custom URL for room search. Template: https://{host}/pod/v3/room/search",
    )
    room_info_url: Optional[str] = Field(
        None,
        description="Custom URL for room info. Template: https://{host}/pod/v3/room/{room_id}/info",
    )
    im_create_url: Optional[str] = Field(
        None,
        description="Custom URL for IM creation. Template: https://{host}/pod/v1/im/create",
    )
    room_members_url: Optional[str] = Field(
        None,
        description="Custom URL for room members. Template: https://{host}/pod/v2/room/{room_id}/membership/list",
    )
    presence_url: Optional[str] = Field(
        None,
        description="Custom URL for user presence. Template: https://{host}/pod/v2/user/presence",
    )
    user_detail_url: Optional[str] = Field(
        None,
        description="Custom URL for user detail. Template: https://{host}/pod/v2/admin/user/{uid}",
    )
    user_search_url: Optional[str] = Field(
        None,
        description="Custom URL for user search. Template: https://{host}/pod/v3/users",
    )
    user_lookup_url: Optional[str] = Field(
        None,
        description="Custom URL for user lookup by email/username. Template: https://{host}/pod/v3/users",
    )

    @property
    def bot_private_key_str(self) -> Optional[str]:
        """Get the bot private key content as string."""
        if self.bot_private_key_content:
            return self.bot_private_key_content.get_secret_value()
        return None

    @property
    def bot_certificate_content_str(self) -> Optional[str]:
        """Get the certificate content as string."""
        if self.bot_certificate_content:
            return self.bot_certificate_content.get_secret_value()
        return None

    @property
    def bot_certificate_password_str(self) -> Optional[str]:
        """Get the certificate password as string."""
        if self.bot_certificate_password:
            return self.bot_certificate_password.get_secret_value()
        return None

    @property
    def proxy_password_str(self) -> Optional[str]:
        """Get the proxy password as string."""
        if self.proxy_password:
            return self.proxy_password.get_secret_value()
        return None

    @property
    def has_rsa_auth(self) -> bool:
        """Check if RSA authentication is configured."""
        return bool(self.bot_username and (self.bot_private_key_path or self.bot_private_key_content))

    @property
    def has_cert_auth(self) -> bool:
        """Check if certificate authentication is configured."""
        return bool(self.bot_certificate_path or self.bot_certificate_content)

    @property
    def is_using_temp_cert(self) -> bool:
        """Check if a temporary certificate file was created."""
        return self._temp_cert_path is not None

    def cleanup_temp_cert(self) -> None:
        """Manually cleanup temporary certificate file if created.

        This is called automatically on process exit, but can be called
        manually for explicit cleanup.
        """
        if self._temp_cert_path and os.path.exists(self._temp_cert_path):
            try:
                os.unlink(self._temp_cert_path)
                object.__setattr__(self, "_temp_cert_path", None)
            except OSError:
                pass

    @property
    def pod_url(self) -> str:
        """Build the pod URL."""
        base = f"{self.scheme}://{self.host}"
        if self.port and self.port != 443:
            base += f":{self.port}"
        if self.context:
            base += f"/{self.context.strip('/')}"
        return base

    def to_bdk_config(self) -> Dict[str, Any]:
        """Convert to Symphony BDK configuration format.

        Returns:
            Dictionary suitable for passing to SymphonyBdk.
        """
        config: Dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "scheme": self.scheme,
            "context": self.context,
        }

        # Bot configuration
        bot_config: Dict[str, Any] = {"username": self.bot_username}

        if self.bot_private_key_path:
            bot_config["privateKey"] = {"path": self.bot_private_key_path}
        elif self.bot_private_key_content:
            bot_config["privateKey"] = {"content": self.bot_private_key_str}

        if self.bot_certificate_path:
            cert_config: Dict[str, Any] = {"path": self.bot_certificate_path}
            if self.bot_certificate_password:
                cert_config["password"] = self.bot_certificate_password_str
            bot_config["certificate"] = cert_config

        config["bot"] = bot_config

        # Pod configuration (only if explicitly set)
        if self.pod_host:
            config["pod"] = {"host": self.pod_host}
            if self.pod_port:
                config["pod"]["port"] = self.pod_port

        # Agent configuration
        # Only set if explicitly specified; BDK defaults to main host if not set
        if self.agent_host:
            config["agent"] = {"host": self.agent_host}
            if self.agent_port:
                config["agent"]["port"] = self.agent_port

        # Key manager configuration
        # Default to session_auth_host if not set (common deployment pattern where KM auth is separate)
        effective_km_host = self.key_manager_host or self.session_auth_host
        if effective_km_host:
            config["keyManager"] = {"host": effective_km_host}
            if self.key_manager_port:
                config["keyManager"]["port"] = self.key_manager_port

        # Session auth configuration (if separate)
        if self.session_auth_host:
            config["sessionAuth"] = {"host": self.session_auth_host}
            if self.session_auth_port:
                config["sessionAuth"]["port"] = self.session_auth_port

        # App configuration
        if self.app_id:
            app_config: Dict[str, Any] = {"appId": self.app_id}
            if self.app_private_key_path:
                app_config["privateKey"] = {"path": self.app_private_key_path}
            config["app"] = app_config

        # SSL configuration
        if self.trust_store_path:
            config["ssl"] = {"trustStore": {"path": self.trust_store_path}}

        # Proxy configuration
        if self.proxy_host:
            proxy_config: Dict[str, Any] = {
                "host": self.proxy_host,
            }
            if self.proxy_port:
                proxy_config["port"] = self.proxy_port
            if self.proxy_username:
                proxy_config["username"] = self.proxy_username
            if self.proxy_password:
                proxy_config["password"] = self.proxy_password_str
            config["proxy"] = proxy_config

        return config
