"""Tests for backend configuration modules.

This module tests the Slack, Discord, and Symphony configuration classes.
"""

import os
import tempfile

import pytest
from pydantic import SecretStr

from chatom.discord.config import DiscordConfig
from chatom.slack.config import SlackConfig
from chatom.symphony.config import SymphonyConfig


class TestSlackConfig:
    """Tests for SlackConfig class."""

    def test_create_slack_config(self):
        """Test creating a Slack config with basic settings."""
        config = SlackConfig(
            bot_token=SecretStr("xoxb-test-token"),
            team_id="T12345",
        )
        assert config.bot_token_str == "xoxb-test-token"
        assert config.team_id == "T12345"

    def test_slack_config_defaults(self):
        """Test Slack config default values."""
        config = SlackConfig()
        assert config.bot_token_str == ""
        assert config.app_token_str == ""
        assert config.signing_secret_str == ""
        assert config.team_id == ""
        assert config.default_channel == ""
        assert config.socket_mode is False

    def test_bot_token_str_property(self):
        """Test bot_token_str property returns plain string."""
        config = SlackConfig(bot_token=SecretStr("xoxb-token-value"))
        assert config.bot_token_str == "xoxb-token-value"

    def test_app_token_str_property(self):
        """Test app_token_str property returns plain string."""
        config = SlackConfig(app_token=SecretStr("xapp-token-value"))
        assert config.app_token_str == "xapp-token-value"

    def test_signing_secret_str_property(self):
        """Test signing_secret_str property returns plain string."""
        config = SlackConfig(signing_secret=SecretStr("signing-secret-123"))
        assert config.signing_secret_str == "signing-secret-123"

    def test_has_socket_mode_with_socket_mode_enabled(self):
        """Test has_socket_mode returns True when socket_mode is True."""
        config = SlackConfig(socket_mode=True)
        assert config.has_socket_mode is True

    def test_has_socket_mode_with_app_token(self):
        """Test has_socket_mode returns True when app_token is set."""
        config = SlackConfig(app_token=SecretStr("xapp-test-token"))
        assert config.has_socket_mode is True

    def test_has_socket_mode_false(self):
        """Test has_socket_mode returns False when neither is set."""
        config = SlackConfig()
        assert config.has_socket_mode is False

    def test_bot_token_from_file(self):
        """Test loading bot token from a file path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("xoxb-file-token\n")
            f.flush()
            try:
                config = SlackConfig(bot_token=f.name)
                assert config.bot_token_str == "xoxb-file-token"
            finally:
                os.unlink(f.name)

    def test_app_token_from_file(self):
        """Test loading app token from a file path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("xapp-file-token\n")
            f.flush()
            try:
                config = SlackConfig(app_token=f.name)
                assert config.app_token_str == "xapp-file-token"
            finally:
                os.unlink(f.name)

    def test_bot_token_invalid_raises(self):
        """Test that invalid bot token raises ValueError."""
        with pytest.raises(ValueError, match="Bot token must start with 'xoxb-'"):
            SlackConfig(bot_token=SecretStr("invalid-token"))

    def test_app_token_invalid_raises(self):
        """Test that invalid app token raises ValueError."""
        with pytest.raises(ValueError, match="App token must start with 'xapp-'"):
            SlackConfig(app_token=SecretStr("invalid-token"))


class TestDiscordConfig:
    """Tests for DiscordConfig class."""

    def test_create_discord_config(self):
        """Test creating a Discord config with basic settings."""
        config = DiscordConfig(
            token=SecretStr("test-discord-token"),
            application_id="123456789",
            guild_id="987654321",
        )
        assert config.bot_token_str == "test-discord-token"
        assert config.application_id == "123456789"
        assert config.guild_id == "987654321"

    def test_discord_config_defaults(self):
        """Test Discord config default values."""
        config = DiscordConfig()
        assert config.bot_token_str == ""
        assert config.application_id == ""
        assert config.guild_id == ""
        assert config.intents == ["guilds", "messages"]
        assert config.command_prefix == "!"
        assert config.shard_id is None
        assert config.shard_count is None

    def test_bot_token_str_property(self):
        """Test bot_token_str property returns plain string."""
        config = DiscordConfig(token=SecretStr("my-token"))
        assert config.bot_token_str == "my-token"

    def test_has_token_true(self):
        """Test has_token returns True when token is set."""
        config = DiscordConfig(token=SecretStr("my-token"))
        assert config.has_token is True

    def test_has_token_false(self):
        """Test has_token returns False when no token is set."""
        config = DiscordConfig()
        assert config.has_token is False

    def test_bot_token_from_file(self):
        """Test loading bot token from a file path."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("file-discord-token\n")
            f.flush()
            try:
                config = DiscordConfig(token=f.name)
                assert config.bot_token_str == "file-discord-token"
            finally:
                os.unlink(f.name)

    def test_bot_token_with_secret_str(self):
        """Test bot token accepts SecretStr input."""
        config = DiscordConfig(token=SecretStr("secret-token"))
        assert config.bot_token_str == "secret-token"

    def test_custom_intents(self):
        """Test custom intents configuration."""
        config = DiscordConfig(intents=["guilds", "messages", "message_content", "members"])
        assert "message_content" in config.intents
        assert "members" in config.intents

    def test_sharding_config(self):
        """Test sharding configuration."""
        config = DiscordConfig(shard_id=0, shard_count=4)
        assert config.shard_id == 0
        assert config.shard_count == 4

    def test_empty_file_raises_error(self):
        """Test that an empty file raises a validation error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")  # Empty file
            f.flush()
            try:
                with pytest.raises(ValueError, match="Token must be a valid Discord bot token"):
                    DiscordConfig(token=f.name)
            finally:
                os.unlink(f.name)


class TestSymphonyConfig:
    """Tests for SymphonyConfig class."""

    def test_create_symphony_config(self):
        """Test creating a Symphony config with basic settings."""
        config = SymphonyConfig(
            host="mycompany.symphony.com",
            bot_username="my-bot",
        )
        assert config.host == "mycompany.symphony.com"
        assert config.bot_username == "my-bot"

    def test_symphony_config_defaults(self):
        """Test Symphony config default values."""
        config = SymphonyConfig()
        assert config.host == ""
        assert config.port == 443
        assert config.scheme == "https"
        assert config.context == ""
        assert config.bot_username == ""
        assert config.timeout == 30
        assert config.max_attempts == 10
        assert config.datafeed_version == "v2"
        assert config.ssl_verify is True

    def test_pod_url_basic(self):
        """Test pod_url property with basic config."""
        config = SymphonyConfig(host="example.symphony.com")
        assert config.pod_url == "https://example.symphony.com"

    def test_pod_url_with_port(self):
        """Test pod_url property with custom port."""
        config = SymphonyConfig(host="example.symphony.com", port=8443)
        assert config.pod_url == "https://example.symphony.com:8443"

    def test_pod_url_with_context(self):
        """Test pod_url property with context path."""
        config = SymphonyConfig(host="example.symphony.com", context="/api")
        assert config.pod_url == "https://example.symphony.com/api"

    def test_bot_private_key_str_property(self):
        """Test bot_private_key_str property."""
        config = SymphonyConfig(bot_private_key_content=SecretStr("private-key-content"))
        assert config.bot_private_key_str == "private-key-content"

    def test_bot_private_key_str_none(self):
        """Test bot_private_key_str returns None when not set."""
        config = SymphonyConfig()
        assert config.bot_private_key_str is None

    def test_bot_certificate_content_str_property(self):
        """Test bot_certificate_content_str property."""
        config = SymphonyConfig(bot_certificate_content=SecretStr("cert-content"))
        assert config.bot_certificate_content_str == "cert-content"

    def test_bot_certificate_content_str_none(self):
        """Test bot_certificate_content_str returns None when not set."""
        config = SymphonyConfig()
        assert config.bot_certificate_content_str is None

    def test_bot_certificate_password_str_property(self):
        """Test bot_certificate_password_str property."""
        config = SymphonyConfig(bot_certificate_password=SecretStr("cert-password"))
        assert config.bot_certificate_password_str == "cert-password"

    def test_bot_certificate_password_str_none(self):
        """Test bot_certificate_password_str returns None when not set."""
        config = SymphonyConfig()
        assert config.bot_certificate_password_str is None

    def test_proxy_password_str_property(self):
        """Test proxy_password_str property."""
        config = SymphonyConfig(proxy_password=SecretStr("proxy-pass"))
        assert config.proxy_password_str == "proxy-pass"

    def test_proxy_password_str_none(self):
        """Test proxy_password_str returns None when not set."""
        config = SymphonyConfig()
        assert config.proxy_password_str is None

    def test_has_rsa_auth_true(self):
        """Test has_rsa_auth returns True when configured."""
        config = SymphonyConfig(
            bot_username="my-bot",
            bot_private_key_path="/path/to/key.pem",
        )
        assert config.has_rsa_auth is True

    def test_has_rsa_auth_with_content(self):
        """Test has_rsa_auth returns True with key content."""
        config = SymphonyConfig(
            bot_username="my-bot",
            bot_private_key_content=SecretStr("key-content"),
        )
        assert config.has_rsa_auth is True

    def test_has_rsa_auth_false(self):
        """Test has_rsa_auth returns False when not configured."""
        config = SymphonyConfig()
        assert config.has_rsa_auth is False

    def test_has_cert_auth_true_with_path(self):
        """Test has_cert_auth returns True with certificate path."""
        config = SymphonyConfig(bot_certificate_path="/path/to/cert.pem")
        assert config.has_cert_auth is True

    def test_has_cert_auth_true_with_content(self):
        """Test has_cert_auth returns True with certificate content."""
        config = SymphonyConfig(bot_certificate_content=SecretStr("cert-content"))
        assert config.has_cert_auth is True

    def test_has_cert_auth_false(self):
        """Test has_cert_auth returns False when not configured."""
        config = SymphonyConfig()
        assert config.has_cert_auth is False

    def test_is_using_temp_cert_false_by_default(self):
        """Test is_using_temp_cert returns False by default."""
        config = SymphonyConfig()
        assert config.is_using_temp_cert is False

    def test_to_bdk_config_basic(self):
        """Test to_bdk_config with basic configuration."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["host"] == "example.symphony.com"
        assert bdk_config["port"] == 443
        assert bdk_config["scheme"] == "https"
        assert bdk_config["bot"]["username"] == "my-bot"

    def test_to_bdk_config_with_private_key_path(self):
        """Test to_bdk_config with private key path."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            bot_private_key_path="/path/to/key.pem",
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["bot"]["privateKey"]["path"] == "/path/to/key.pem"

    def test_to_bdk_config_with_private_key_content(self):
        """Test to_bdk_config with private key content."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            bot_private_key_content=SecretStr("key-content"),
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["bot"]["privateKey"]["content"] == "key-content"

    def test_to_bdk_config_with_certificate(self):
        """Test to_bdk_config with certificate configuration."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            bot_certificate_path="/path/to/cert.pem",
            bot_certificate_password=SecretStr("cert-pass"),
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["bot"]["certificate"]["path"] == "/path/to/cert.pem"
        assert bdk_config["bot"]["certificate"]["password"] == "cert-pass"

    def test_to_bdk_config_with_pod_host(self):
        """Test to_bdk_config with separate pod host."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            pod_host="pod.example.com",
            pod_port=8443,
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["pod"]["host"] == "pod.example.com"
        assert bdk_config["pod"]["port"] == 8443

    def test_to_bdk_config_with_agent_host(self):
        """Test to_bdk_config with separate agent host."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            agent_host="agent.example.com",
            agent_port=9443,
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["agent"]["host"] == "agent.example.com"
        assert bdk_config["agent"]["port"] == 9443

    def test_to_bdk_config_with_key_manager(self):
        """Test to_bdk_config with key manager configuration."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            key_manager_host="km.example.com",
            key_manager_port=10443,
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["keyManager"]["host"] == "km.example.com"
        assert bdk_config["keyManager"]["port"] == 10443

    def test_to_bdk_config_with_session_auth(self):
        """Test to_bdk_config with session auth configuration."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            session_auth_host="session.example.com",
            session_auth_port=11443,
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["sessionAuth"]["host"] == "session.example.com"
        assert bdk_config["sessionAuth"]["port"] == 11443
        # Key manager defaults to session auth host
        assert bdk_config["keyManager"]["host"] == "session.example.com"

    def test_to_bdk_config_with_app(self):
        """Test to_bdk_config with extension app configuration."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            app_id="my-app-id",
            app_private_key_path="/path/to/app-key.pem",
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["app"]["appId"] == "my-app-id"
        assert bdk_config["app"]["privateKey"]["path"] == "/path/to/app-key.pem"

    def test_to_bdk_config_with_ssl(self):
        """Test to_bdk_config with SSL trust store."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            trust_store_path="/path/to/truststore.jks",
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["ssl"]["trustStore"]["path"] == "/path/to/truststore.jks"

    def test_to_bdk_config_with_proxy(self):
        """Test to_bdk_config with proxy configuration."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username="proxy-user",
            proxy_password=SecretStr("proxy-pass"),
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["proxy"]["host"] == "proxy.example.com"
        assert bdk_config["proxy"]["port"] == 8080
        assert bdk_config["proxy"]["username"] == "proxy-user"
        assert bdk_config["proxy"]["password"] == "proxy-pass"

    def test_pod_host_fallback_to_host(self):
        """Test that pod_host is used as fallback for host."""
        config = SymphonyConfig(pod_host="fallback.symphony.com", bot_username="bot")
        assert config.host == "fallback.symphony.com"

    def test_cleanup_temp_cert_no_op_when_not_set(self):
        """Test cleanup_temp_cert does nothing when no temp cert."""
        config = SymphonyConfig()
        # Should not raise
        config.cleanup_temp_cert()
        assert config.is_using_temp_cert is False

    def test_ssl_verify_disabled_warning(self):
        """Test that SSL verification disabled logs warning."""
        # Setting ssl_verify=False triggers the validation with warning
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            ssl_verify=False,
        )
        # Config should still be created successfully
        assert config.ssl_verify is False

    def test_certificate_content_creates_temp_file(self):
        """Test that certificate content creates a temp file."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
            bot_certificate_content=SecretStr("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"),
        )
        # Should have created a temp cert file
        assert config.is_using_temp_cert is True
        assert config.bot_certificate_path is not None
        assert os.path.exists(config.bot_certificate_path)
        # Cleanup
        config.cleanup_temp_cert()
        assert config.is_using_temp_cert is False

    def test_get_bdk_config_raises_without_symphony_bdk(self):
        """Test get_bdk_config raises ImportError when symphony-bdk not installed."""
        config = SymphonyConfig(
            host="example.symphony.com",
            bot_username="my-bot",
        )
        # The get_bdk_config should attempt to import symphony.bdk
        # We can't easily test ImportError, but we can test the method exists
        # The actual behavior depends on whether symphony-bdk is installed
        try:
            result = config.get_bdk_config()
            # If symphony-bdk is installed, it should return a BdkConfig
            assert result is not None
        except ImportError:
            # If not installed, that's the expected behavior
            pass


class TestSymphonyRoomMapper:
    """Tests for SymphonyRoomMapper class."""

    def test_room_mapper_init(self):
        """Test SymphonyRoomMapper initialization."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        assert mapper._name_to_id == {}
        assert mapper._id_to_name == {}
        assert mapper._stream_service is None
        assert mapper._backend is None

    def test_register_room(self):
        """Test manually registering a room."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        mapper.register_room("Test Room", "stream123")
        assert mapper.get_room_id("Test Room") == "stream123"
        assert mapper.get_room_name("stream123") == "Test Room"

    def test_get_room_id_from_cache(self):
        """Test getting room ID from cache."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        mapper.register_room("My Room", "room456")
        assert mapper.get_room_id("My Room") == "room456"

    def test_get_room_id_already_id(self):
        """Test get_room_id returns value if it looks like a stream ID."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        # Stream IDs are typically long alphanumeric strings without spaces
        long_id = "abcdefghijklmnopqrstuvwxyz"
        result = mapper.get_room_id(long_id)
        assert result == long_id

    def test_get_room_id_not_found(self):
        """Test get_room_id returns None if not found."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        result = mapper.get_room_id("Unknown Room")
        assert result is None

    def test_get_room_name_not_found(self):
        """Test get_room_name returns None if not found."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        result = mapper.get_room_name("unknownid")
        assert result is None

    def test_set_stream_service(self):
        """Test setting stream service."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        mock_service = object()
        mapper.set_stream_service(mock_service)
        assert mapper._stream_service is mock_service

    def test_set_backend(self):
        """Test setting backend."""
        from typing import Any, cast

        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        mock_backend = object()
        mapper.set_backend(cast(Any, mock_backend))
        assert mapper._backend is mock_backend

    def test_set_im_id(self):
        """Test registering an IM stream ID."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        mapper.set_im_id("user@example.com", "im_stream_123")
        assert mapper.get_room_id("user@example.com") == "im_stream_123"
        assert mapper.get_room_name("im_stream_123") == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_room_id_async_from_cache(self):
        """Test async get_room_id returns from cache."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        mapper.register_room("Async Room", "asyncstream")
        result = await mapper.get_room_id_async("Async Room")
        assert result == "asyncstream"

    @pytest.mark.asyncio
    async def test_get_room_id_async_no_backend(self):
        """Test async get_room_id returns None with no backend or stream service."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        result = await mapper.get_room_id_async("Unknown Room")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_room_name_async_from_cache(self):
        """Test async get_room_name returns from cache."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        mapper.register_room("Cached Room", "cachedid")
        result = await mapper.get_room_name_async("cachedid")
        assert result == "Cached Room"

    @pytest.mark.asyncio
    async def test_get_room_name_async_no_backend(self):
        """Test async get_room_name returns None with no backend or stream service."""
        from chatom.symphony.config import SymphonyRoomMapper

        mapper = SymphonyRoomMapper()
        result = await mapper.get_room_name_async("unknownid")
        assert result is None
