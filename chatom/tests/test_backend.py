"""Tests for BackendConfig class."""

from chatom import BackendConfig


class TestBackendConfig:
    """Tests for BackendConfig class."""

    def test_create_config(self):
        """Test creating a backend config."""
        config = BackendConfig(
            api_token="test-token",
            api_url="https://api.example.com",
            timeout=60.0,
            retry_count=5,
        )
        assert config.api_token == "test-token"
        assert config.api_url == "https://api.example.com"
        assert config.timeout == 60.0
        assert config.retry_count == 5

    def test_config_defaults(self):
        """Test backend config defaults."""
        config = BackendConfig()
        assert config.api_token == ""
        assert config.api_url == ""
        assert config.timeout == 30.0
        assert config.retry_count == 3
        assert config.extra == {}

    def test_config_extra_settings(self):
        """Test extra configuration settings."""
        config = BackendConfig(
            extra={
                "custom_setting": "value",
                "debug": True,
            }
        )
        assert config.extra["custom_setting"] == "value"
        assert config.extra["debug"] is True
