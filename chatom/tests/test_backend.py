"""Tests for BackendConfig class."""

from pydantic import SecretStr

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


class TestBackendConfigGetSecret:
    """Tests for BackendConfig.get_secret() method."""

    def test_get_secret_with_secret_str(self):
        """Test get_secret returns value from SecretStr field."""
        # Create a config subclass with a SecretStr field for testing
        from pydantic import Field

        class TestConfig(BackendConfig):
            password: SecretStr = Field(default=SecretStr(""))

        config = TestConfig(password=SecretStr("my-secret-password"))
        assert config.get_secret("password") == "my-secret-password"

    def test_get_secret_with_empty_secret_str(self):
        """Test get_secret returns empty string for empty SecretStr."""
        from pydantic import Field

        class TestConfig(BackendConfig):
            password: SecretStr = Field(default=SecretStr(""))

        config = TestConfig()
        assert config.get_secret("password") == ""

    def test_get_secret_with_none_value(self):
        """Test get_secret returns empty string when field is None."""
        config = BackendConfig()
        # Simulate None by accessing a non-existent optional field
        # Use a workaround since we can't set None directly
        config.__dict__["test_field"] = None
        # getattr will return None
        assert config.get_secret("test_field") == ""

    def test_get_secret_with_regular_string(self):
        """Test get_secret returns string value for regular string fields."""
        config = BackendConfig(api_token="plain-token")
        assert config.get_secret("api_token") == "plain-token"


class TestBackendConfigHasField:
    """Tests for BackendConfig.has_field() method."""

    def test_has_field_with_string_value(self):
        """Test has_field returns True for non-empty string."""
        config = BackendConfig(api_token="test-token")
        assert config.has_field("api_token") is True

    def test_has_field_with_empty_string(self):
        """Test has_field returns False for empty string."""
        config = BackendConfig(api_token="")
        assert config.has_field("api_token") is False

    def test_has_field_with_none(self):
        """Test has_field returns False for None value."""
        config = BackendConfig()
        config.__dict__["test_field"] = None
        assert config.has_field("test_field") is False

    def test_has_field_with_secret_str(self):
        """Test has_field returns True for non-empty SecretStr."""
        from pydantic import Field

        class TestConfig(BackendConfig):
            password: SecretStr = Field(default=SecretStr(""))

        config = TestConfig(password=SecretStr("secret123"))
        assert config.has_field("password") is True

    def test_has_field_with_empty_secret_str(self):
        """Test has_field returns False for empty SecretStr."""
        from pydantic import Field

        class TestConfig(BackendConfig):
            password: SecretStr = Field(default=SecretStr(""))

        config = TestConfig()
        assert config.has_field("password") is False

    def test_has_field_with_list(self):
        """Test has_field returns True for non-empty list."""
        config = BackendConfig(extra={"items": [1, 2, 3]})
        assert config.has_field("extra") is True

    def test_has_field_with_empty_list(self):
        """Test has_field returns False for empty list."""
        from typing import List

        from pydantic import Field

        class TestConfig(BackendConfig):
            items: List[str] = Field(default_factory=list)

        config = TestConfig()
        assert config.has_field("items") is False

    def test_has_field_with_dict(self):
        """Test has_field returns True for non-empty dict."""
        config = BackendConfig(extra={"key": "value"})
        assert config.has_field("extra") is True

    def test_has_field_with_empty_dict(self):
        """Test has_field returns False for empty dict."""
        config = BackendConfig(extra={})
        assert config.has_field("extra") is False

    def test_has_field_with_int(self):
        """Test has_field returns True for integer values."""
        config = BackendConfig(retry_count=5)
        assert config.has_field("retry_count") is True

    def test_has_field_with_zero_int(self):
        """Test has_field returns True for zero (it's a valid value)."""
        config = BackendConfig(retry_count=0)
        # Zero is a valid non-None value
        assert config.has_field("retry_count") is True


class TestBackendConfigProperties:
    """Tests for BackendConfig property accessors."""

    def test_has_token_true(self):
        """Test has_token returns True when api_token is set."""
        config = BackendConfig(api_token="test-token")
        assert config.has_token is True

    def test_has_token_false(self):
        """Test has_token returns False when api_token is empty."""
        config = BackendConfig()
        assert config.has_token is False

    def test_has_url_true(self):
        """Test has_url returns True when api_url is set."""
        config = BackendConfig(api_url="https://api.example.com")
        assert config.has_url is True

    def test_has_url_false(self):
        """Test has_url returns False when api_url is empty."""
        config = BackendConfig()
        assert config.has_url is False
