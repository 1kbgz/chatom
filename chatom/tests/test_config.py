"""Tests for backend configuration modules.

This module tests the IRC, Slack, and Matrix configuration classes.
"""

from pydantic import SecretStr

from chatom.irc.config import IRCConfig
from chatom.matrix.config import MatrixConfig
from chatom.slack.config import SlackConfig


class TestIRCConfig:
    """Tests for IRCConfig class."""

    def test_create_irc_config(self):
        """Test creating an IRC config with basic settings."""
        config = IRCConfig(
            server="irc.libera.chat",
            port=6697,
            nickname="testbot",
            use_ssl=True,
        )
        assert config.server == "irc.libera.chat"
        assert config.port == 6697
        assert config.nickname == "testbot"
        assert config.use_ssl is True

    def test_irc_config_defaults(self):
        """Test IRC config default values."""
        config = IRCConfig()
        assert config.server == ""
        assert config.port == 6667
        assert config.nickname == ""
        assert config.use_ssl is False
        assert config.verify_ssl is True
        assert config.auto_join_channels == []
        assert config.command_prefix == "!"

    def test_password_str_property(self):
        """Test password_str property returns plain string."""
        config = IRCConfig(password=SecretStr("secret123"))
        assert config.password_str == "secret123"

    def test_nickserv_password_str_property(self):
        """Test nickserv_password_str property returns plain string."""
        config = IRCConfig(nickserv_password=SecretStr("nickpass456"))
        assert config.nickserv_password_str == "nickpass456"

    def test_has_server_true(self):
        """Test has_server returns True when server is set."""
        config = IRCConfig(server="irc.example.com")
        assert config.has_server is True

    def test_has_server_false(self):
        """Test has_server returns False when server is empty."""
        config = IRCConfig()
        assert config.has_server is False

    def test_has_nickname_true(self):
        """Test has_nickname returns True when nickname is set."""
        config = IRCConfig(nickname="mybot")
        assert config.has_nickname is True

    def test_has_nickname_false(self):
        """Test has_nickname returns False when nickname is empty."""
        config = IRCConfig()
        assert config.has_nickname is False

    def test_effective_username_with_username(self):
        """Test effective_username returns username when set."""
        config = IRCConfig(username="myuser", nickname="mynick")
        assert config.effective_username == "myuser"

    def test_effective_username_fallback_to_nickname(self):
        """Test effective_username falls back to nickname when username is empty."""
        config = IRCConfig(nickname="mynick")
        assert config.effective_username == "mynick"

    def test_effective_realname_with_realname(self):
        """Test effective_realname returns realname when set."""
        config = IRCConfig(realname="My Real Name", nickname="mynick")
        assert config.effective_realname == "My Real Name"

    def test_effective_realname_fallback_to_nickname(self):
        """Test effective_realname falls back to nickname when realname is empty."""
        config = IRCConfig(nickname="mynick")
        assert config.effective_realname == "mynick"


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


class TestMatrixConfig:
    """Tests for MatrixConfig class."""

    def test_create_matrix_config(self):
        """Test creating a Matrix config with basic settings."""
        config = MatrixConfig(
            homeserver_url="https://matrix.org",
            access_token=SecretStr("access-token-123"),
            user_id="@mybot:matrix.org",
        )
        assert config.homeserver_url == "https://matrix.org"
        assert config.access_token_str == "access-token-123"
        assert config.user_id == "@mybot:matrix.org"

    def test_matrix_config_defaults(self):
        """Test Matrix config default values."""
        config = MatrixConfig()
        assert config.homeserver_url == ""
        assert config.access_token_str == ""
        assert config.user_id == ""
        assert config.device_id == ""
        assert config.sync_filter_limit == 20
        assert config.validate_cert is True
        assert config.sync_timeout_ms == 30000

    def test_access_token_str_property(self):
        """Test access_token_str property returns plain string."""
        config = MatrixConfig(access_token=SecretStr("my-access-token"))
        assert config.access_token_str == "my-access-token"

    def test_has_token_true(self):
        """Test has_token returns True when access_token is set."""
        config = MatrixConfig(access_token=SecretStr("token123"))
        assert config.has_token is True

    def test_has_token_false(self):
        """Test has_token returns False when access_token is empty."""
        config = MatrixConfig()
        assert config.has_token is False

    def test_has_homeserver_true(self):
        """Test has_homeserver returns True when homeserver_url is set."""
        config = MatrixConfig(homeserver_url="https://matrix.example.com")
        assert config.has_homeserver is True

    def test_has_homeserver_false(self):
        """Test has_homeserver returns False when homeserver_url is empty."""
        config = MatrixConfig()
        assert config.has_homeserver is False
