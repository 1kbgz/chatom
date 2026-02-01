"""Integration tests for Symphony backend.

These tests run against a real Symphony pod when credentials are available.

Environment Variables Required:
    SYMPHONY_HOST: Symphony pod hostname
    SYMPHONY_BOT_USERNAME: Bot's service account username
    SYMPHONY_TEST_ROOM_NAME: Room name for tests
    SYMPHONY_TEST_USER_NAME: Username for mention tests

    Authentication (one of):
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key
        SYMPHONY_BOT_PRIVATE_KEY_CONTENT: RSA private key content
        SYMPHONY_BOT_COMBINED_CERT_PATH: Path to combined cert
        SYMPHONY_BOT_COMBINED_CERT_CONTENT: Combined cert content
"""

import os
from contextlib import asynccontextmanager

import pytest


# Check if Symphony credentials are available
def has_symphony_credentials() -> bool:
    """Check if Symphony credentials are configured."""
    if not os.environ.get("SYMPHONY_HOST"):
        return False
    if not os.environ.get("SYMPHONY_BOT_USERNAME"):
        return False

    # Check for authentication method
    has_rsa = os.environ.get("SYMPHONY_BOT_PRIVATE_KEY_PATH") or os.environ.get("SYMPHONY_BOT_PRIVATE_KEY_CONTENT")
    has_cert = os.environ.get("SYMPHONY_BOT_COMBINED_CERT_PATH") or os.environ.get("SYMPHONY_BOT_COMBINED_CERT_CONTENT")

    return bool(has_rsa or has_cert)


# Skip all tests if Symphony credentials not available
pytestmark = pytest.mark.skipif(
    not has_symphony_credentials(),
    reason="Symphony credentials not available",
)


@pytest.fixture
def symphony_config():
    """Create Symphony configuration from environment."""
    from pydantic import SecretStr

    from chatom.symphony import SymphonyConfig

    config_kwargs = {
        "host": os.environ.get("SYMPHONY_HOST", ""),
        "bot_username": os.environ.get("SYMPHONY_BOT_USERNAME", ""),
    }

    # Authentication
    if os.environ.get("SYMPHONY_BOT_PRIVATE_KEY_PATH"):
        config_kwargs["bot_private_key_path"] = os.environ["SYMPHONY_BOT_PRIVATE_KEY_PATH"]
    elif os.environ.get("SYMPHONY_BOT_PRIVATE_KEY_CONTENT"):
        config_kwargs["bot_private_key_content"] = SecretStr(os.environ["SYMPHONY_BOT_PRIVATE_KEY_CONTENT"])
    elif os.environ.get("SYMPHONY_BOT_COMBINED_CERT_PATH"):
        config_kwargs["bot_certificate_path"] = os.environ["SYMPHONY_BOT_COMBINED_CERT_PATH"]
    elif os.environ.get("SYMPHONY_BOT_COMBINED_CERT_CONTENT"):
        config_kwargs["bot_certificate_content"] = SecretStr(os.environ["SYMPHONY_BOT_COMBINED_CERT_CONTENT"])

    # Optional hosts
    if os.environ.get("SYMPHONY_AGENT_HOST"):
        config_kwargs["agent_host"] = os.environ["SYMPHONY_AGENT_HOST"]
    if os.environ.get("SYMPHONY_SESSION_AUTH_HOST"):
        config_kwargs["session_auth_host"] = os.environ["SYMPHONY_SESSION_AUTH_HOST"]
    if os.environ.get("SYMPHONY_KEY_MANAGER_HOST"):
        config_kwargs["key_manager_host"] = os.environ["SYMPHONY_KEY_MANAGER_HOST"]

    return SymphonyConfig(**config_kwargs)


@pytest.fixture
def room_name():
    """Get test room name."""
    return os.environ.get("SYMPHONY_TEST_ROOM_NAME", "")


@pytest.fixture
def user_name():
    """Get test user name."""
    return os.environ.get("SYMPHONY_TEST_USER_NAME", "")


@asynccontextmanager
async def create_symphony_backend(config):
    """Create and connect a Symphony backend as async context manager."""
    from chatom.symphony import SymphonyBackend

    backend = SymphonyBackend(config=config)
    await backend.connect()
    try:
        yield backend
    finally:
        await backend.disconnect()


class TestSymphonyConnection:
    """Test Symphony connection."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, symphony_config):
        """Test basic connection and disconnection."""
        from chatom.symphony import SymphonyBackend

        backend = SymphonyBackend(config=symphony_config)
        await backend.connect()

        assert backend.connected
        assert backend.name == "symphony"
        assert backend.display_name == "Symphony"

        await backend.disconnect()
        assert not backend.connected


class TestSymphonyRoomLookup:
    """Test Symphony room operations."""

    @pytest.mark.asyncio
    async def test_fetch_room_by_name(self, symphony_config, room_name):
        """Test looking up a room by name."""
        if not room_name:
            pytest.skip("SYMPHONY_TEST_ROOM_NAME not set")

        async with create_symphony_backend(symphony_config) as backend:
            room = await backend.fetch_channel(name=room_name)

            assert room is not None
            assert room.id is not None


class TestSymphonyUserLookup:
    """Test Symphony user operations."""

    @pytest.mark.asyncio
    async def test_fetch_user_by_name(self, symphony_config, user_name):
        """Test looking up a user by name."""
        if not user_name:
            pytest.skip("SYMPHONY_TEST_USER_NAME not set")

        async with create_symphony_backend(symphony_config) as backend:
            user = await backend.fetch_user(name=user_name)
            if not user:
                user = await backend.fetch_user(handle=user_name)

            assert user is not None
            assert user.id is not None


class TestSymphonyMessaging:
    """Test Symphony messaging operations."""

    @pytest.mark.asyncio
    async def test_send_message(self, symphony_config, room_name):
        """Test sending a simple message."""
        if not room_name:
            pytest.skip("SYMPHONY_TEST_ROOM_NAME not set")

        async with create_symphony_backend(symphony_config) as backend:
            room = await backend.fetch_channel(name=room_name)
            assert room is not None

            message = await backend.send_message(
                channel=room.id,
                content="Integration test message from chatom 🧪",
            )

            assert message is not None
            assert message.id is not None

    @pytest.mark.asyncio
    async def test_send_formatted_message(self, symphony_config, room_name):
        """Test sending a formatted message."""
        from chatom.format import FormattedMessage
        from chatom.format.variant import Format

        if not room_name:
            pytest.skip("SYMPHONY_TEST_ROOM_NAME not set")

        async with create_symphony_backend(symphony_config) as backend:
            room = await backend.fetch_channel(name=room_name)
            assert room is not None

            msg = FormattedMessage()
            msg.add_bold("Test")
            msg.add_text(" - ")
            msg.add_italic("formatted message")
            msg.add_code(" with code")

            content = msg.render(Format.SYMPHONY_MESSAGEML)

            message = await backend.send_message(
                channel=room.id,
                content=content,
            )

            assert message is not None
            assert message.id is not None


class TestSymphonyMessageHistory:
    """Test Symphony message history operations."""

    @pytest.mark.asyncio
    async def test_read_messages(self, symphony_config, room_name):
        """Test reading message history."""
        if not room_name:
            pytest.skip("SYMPHONY_TEST_ROOM_NAME not set")

        async with create_symphony_backend(symphony_config) as backend:
            room = await backend.fetch_channel(name=room_name)
            assert room is not None

            # Read last 5 messages
            messages = await backend.fetch_messages(channel=room.id, limit=5)

            # Should get at least 1 message (we just sent some)
            assert len(messages) >= 1
            assert all(m.id for m in messages)
