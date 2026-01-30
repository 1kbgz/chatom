"""Symphony backend configuration.

This module provides the SymphonyConfig class for configuring
the Symphony backend with the Symphony BDK.
"""

import atexit
import logging
import os
import tempfile
import threading
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import Field, SecretStr, model_validator

from ..backend import BackendConfig

if TYPE_CHECKING:
    from .backend import SymphonyBackend

__all__ = ("SymphonyConfig", "SymphonyRoomMapper")

log = logging.getLogger(__name__)


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

    # Error handling and retry configuration
    error_room: Optional[str] = Field(
        None,
        description="A room to direct error messages to, if a message fails to be sent.",
    )
    inform_client: bool = Field(
        False,
        description="Whether to inform the intended recipient of a failed message.",
    )
    max_attempts: int = Field(
        10,
        description="Max attempts for datafeed and message post requests before raising exception.",
    )
    initial_interval_ms: int = Field(
        500,
        description="Initial interval to wait between attempts, in milliseconds.",
    )
    multiplier: float = Field(
        2.0,
        description="Multiplier between attempt delays for exponential backoff.",
    )
    max_interval_ms: int = Field(
        300000,
        description="Maximum delay between retry attempts, in milliseconds.",
    )
    datafeed_version: str = Field(
        "v2",
        description="Version of datafeed to use ('v1' or 'v2').",
    )

    # SSL configuration
    ssl_trust_store_path: Optional[str] = Field(
        None,
        description="Path to a custom CA certificate bundle file.",
    )
    ssl_verify: bool = Field(
        True,
        description="Whether to verify SSL certificates.",
    )

    @model_validator(mode="after")
    def _validate_config(self) -> "SymphonyConfig":
        """Validate configuration and handle certificate content."""
        # Validate required fields - allow pod_host as fallback for host
        effective_host = self.host or self.pod_host
        if effective_host and not self.host:
            object.__setattr__(self, "host", effective_host)
        # Only validate if we're not in a mock/testing context (has some connection config)
        # Skip validation if both are empty (allows mock backends)

        # Handle SSL verification
        if not self.ssl_verify:
            log.warning("SSL verification is disabled. This is not recommended for production.")
            self._patch_ssl_verify()

        # Handle certificate content -> temp file
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

    def _patch_ssl_verify(self) -> None:
        """Patch the BDK to disable SSL verification."""
        try:
            from symphony.bdk.gen.configuration import Configuration

            original_config_init = Configuration.__init__

            def patched_config_init(config_self, *args, **kwargs):
                original_config_init(config_self, *args, **kwargs)
                config_self.verify_ssl = False

            Configuration.__init__ = patched_config_init
            log.debug("SSL verification has been disabled via monkey patch")
        except ImportError as e:
            log.warning(f"Could not patch SSL verification: {e}")

    def get_bdk_config(self):
        """Build a BdkConfig from chatom config fields.

        Returns:
            A BdkConfig instance for use with symphony-bdk-python.
        """
        try:
            from symphony.bdk.core.config.model.bdk_config import BdkConfig

            return BdkConfig(**self.to_bdk_config())
        except ImportError:
            raise ImportError("symphony-bdk-python is required for get_bdk_config()")


class SymphonyRoomMapper:
    """Thread-safe mapper for Symphony room names and IDs.

    This class maintains a cache of room name to ID mappings and vice versa,
    using the stream service to resolve unknown rooms.
    """

    def __init__(self, stream_service=None, backend: Optional["SymphonyBackend"] = None):
        """Initialize the room mapper.

        Args:
            stream_service: Optional StreamService from SymphonyBdk.
            backend: Optional chatom SymphonyBackend for room resolution.
        """
        self._name_to_id: Dict[str, str] = {}
        self._id_to_name: Dict[str, str] = {}
        self._stream_service = stream_service
        self._backend = backend
        self._lock = threading.Lock()

    def set_stream_service(self, stream_service):
        """Set the stream service for room resolution."""
        self._stream_service = stream_service

    def set_backend(self, backend: "SymphonyBackend"):
        """Set the chatom backend for room resolution."""
        self._backend = backend

    def get_room_id(self, room_name: str) -> Optional[str]:
        """Get the room ID for a given room name.

        Args:
            room_name: The display name of the room.

        Returns:
            The room's stream ID, or None if not found.
        """
        with self._lock:
            if room_name in self._name_to_id:
                return self._name_to_id[room_name]

            # If it looks like a stream ID already, return it
            if len(room_name) > 20 and " " not in room_name:
                return room_name

            return None

    async def get_room_id_async(self, room_name: str) -> Optional[str]:
        """Get the room ID for a given room name, using async calls if needed.

        Args:
            room_name: The display name of the room.

        Returns:
            The room's stream ID, or None if not found.
        """
        # Check cache first
        cached = self.get_room_id(room_name)
        if cached:
            return cached

        # Try chatom backend first
        if self._backend is not None:
            channel = await self._backend.fetch_channel(name=room_name)
            if channel:
                with self._lock:
                    self._name_to_id[room_name] = channel.id
                    self._id_to_name[channel.id] = room_name
                return channel.id

        # Fall back to direct stream service
        if self._stream_service is None:
            return None

        try:
            from symphony.bdk.gen.pod_model.v2_room_search_criteria import V2RoomSearchCriteria

            results = await self._stream_service.search_rooms(V2RoomSearchCriteria(query=room_name), limit=10)
            if results and results.rooms:
                for room in results.rooms:
                    room_attrs = room.room_attributes
                    room_info = room.room_system_info
                    if room_attrs and room_info and room_attrs.name == room_name:
                        room_id = room_info.id
                        with self._lock:
                            self._name_to_id[room_name] = room_id
                            self._id_to_name[room_id] = room_name
                        return room_id
        except Exception as e:
            log.error(f"Error searching for room '{room_name}': {e}")

        return None

    def get_room_name(self, room_id: str) -> Optional[str]:
        """Get the room name for a given room ID.

        Args:
            room_id: The room's stream ID.

        Returns:
            The room's display name, or None if not found.
        """
        with self._lock:
            return self._id_to_name.get(room_id)

    async def get_room_name_async(self, room_id: str) -> Optional[str]:
        """Get the room name for a given room ID, using async calls if needed.

        Args:
            room_id: The room's stream ID.

        Returns:
            The room's display name, or None if not found.
        """
        # Check cache first
        cached = self.get_room_name(room_id)
        if cached:
            return cached

        # Try chatom backend first
        if self._backend is not None:
            channel = await self._backend.fetch_channel(id=room_id)
            if channel and channel.name:
                with self._lock:
                    self._name_to_id[channel.name] = room_id
                    self._id_to_name[room_id] = channel.name
                return channel.name

        # Fall back to direct stream service
        if self._stream_service is None:
            return None

        try:
            room_info = await self._stream_service.get_room_info(room_id)
            if room_info and room_info.room_attributes:
                room_name = room_info.room_attributes.name
                with self._lock:
                    self._name_to_id[room_name] = room_id
                    self._id_to_name[room_id] = room_name
                return room_name
        except Exception as e:
            log.error(f"Error getting room info for '{room_id}': {e}")

        return None

    def set_im_id(self, user_identifier: str, stream_id: str):
        """Register an IM stream ID for a user.

        Args:
            user_identifier: The user's display name or user ID.
            stream_id: The IM stream ID.
        """
        with self._lock:
            self._id_to_name[stream_id] = user_identifier
            self._name_to_id[user_identifier] = stream_id

    def register_room(self, room_name: str, room_id: str):
        """Manually register a room name to ID mapping.

        Args:
            room_name: The display name of the room.
            room_id: The room's stream ID.
        """
        with self._lock:
            self._name_to_id[room_name] = room_id
            self._id_to_name[room_id] = room_name
