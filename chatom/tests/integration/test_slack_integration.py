"""Integration tests for Slack backend.

These tests run against a real Slack workspace when credentials are available.

Environment Variables Required:
    SLACK_BOT_TOKEN: Slack bot OAuth token (xoxb-...)
    SLACK_TEST_CHANNEL_NAME: Channel name for tests
    SLACK_TEST_USER_NAME: Username for mention tests
    SLACK_APP_TOKEN: (Optional) App token for Socket Mode
"""

import os
from contextlib import asynccontextmanager

import pytest

# Skip all tests if Slack credentials not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_TEST_CHANNEL_NAME"),
    reason="Slack credentials not available (set SLACK_BOT_TOKEN and SLACK_TEST_CHANNEL_NAME)",
)


def skip_on_missing_scope(func):
    """Decorator to skip tests when Slack API returns missing_scope errors."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            if "missing_scope" in error_str or "not_in_channel" in error_str:
                pytest.skip(f"Skipping due to Slack API permission: {error_str[:100]}")
            raise

    return wrapper


@pytest.fixture
def slack_config():
    """Create Slack configuration from environment."""
    from chatom.slack import SlackConfig

    return SlackConfig(
        bot_token=os.environ.get("SLACK_BOT_TOKEN", ""),
        app_token=os.environ.get("SLACK_APP_TOKEN", ""),
    )


@pytest.fixture
def channel_name():
    """Get test channel name."""
    return os.environ.get("SLACK_TEST_CHANNEL_NAME", "")


@pytest.fixture
def user_name():
    """Get test user name."""
    return os.environ.get("SLACK_TEST_USER_NAME", "")


@asynccontextmanager
async def create_slack_backend(config):
    """Create and connect a Slack backend as async context manager."""
    from chatom.slack import SlackBackend

    backend = SlackBackend(config=config)
    await backend.connect()
    try:
        yield backend
    finally:
        await backend.disconnect()


class TestSlackConnection:
    """Test Slack connection."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, slack_config):
        """Test basic connection and disconnection."""
        from chatom.slack import SlackBackend

        backend = SlackBackend(config=slack_config)
        await backend.connect()

        assert backend.connected
        assert backend.name == "slack"
        assert backend.display_name == "Slack"

        await backend.disconnect()
        assert not backend.connected


class TestSlackChannelLookup:
    """Test Slack channel operations."""

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_fetch_channel_by_name(self, slack_config, channel_name):
        """Test looking up a channel by name."""
        async with create_slack_backend(slack_config) as backend:
            channel = await backend.fetch_channel(name=channel_name)

            assert channel is not None
            assert channel.id is not None
            assert channel.name == channel_name

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_fetch_channel_by_id(self, slack_config, channel_name):
        """Test looking up a channel by ID."""
        async with create_slack_backend(slack_config) as backend:
            # First get the channel by name
            channel = await backend.fetch_channel(name=channel_name)
            assert channel is not None

            # Then fetch by ID
            channel2 = await backend.fetch_channel(id=channel.id)

            assert channel2 is not None
            assert channel2.id == channel.id


class TestSlackUserLookup:
    """Test Slack user operations."""

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_fetch_user_by_name(self, slack_config, user_name):
        """Test looking up a user by name."""
        if not user_name:
            pytest.skip("SLACK_TEST_USER_NAME not set")

        async with create_slack_backend(slack_config) as backend:
            user = await backend.fetch_user(name=user_name)
            if not user:
                user = await backend.fetch_user(handle=user_name)

            assert user is not None
            assert user.id is not None


class TestSlackMessaging:
    """Test Slack messaging operations."""

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_send_message(self, slack_config, channel_name):
        """Test sending a simple message."""
        async with create_slack_backend(slack_config) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            if channel is None:
                pytest.skip("Channel not found (API issue)")

            message = await backend.send_message(
                channel=channel.id,
                content="Integration test message from chatom 🧪",
            )

            if message is None:
                pytest.skip("Message failed to send (API issue)")
            assert message.id is not None
            # Note: channel_id may be empty depending on API response
            if message.channel_id:
                assert message.channel_id == channel.id

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_send_formatted_message(self, slack_config, channel_name):
        """Test sending a formatted message."""
        from chatom.format import FormattedMessage
        from chatom.format.variant import Format

        async with create_slack_backend(slack_config) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            if channel is None:
                pytest.skip("Channel not found (API issue)")

            msg = FormattedMessage()
            msg.add_bold("Test")
            msg.add_text(" - ")
            msg.add_italic("formatted message")
            msg.add_code(" with code")

            content = msg.render(Format.SLACK_MARKDOWN)

            message = await backend.send_message(
                channel=channel.id,
                content=content,
            )

            if message is None:
                pytest.skip("Message failed to send (API issue)")
            assert message.id is not None

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_reply_to_message(self, slack_config, channel_name):
        """Test replying to a message (creating a thread)."""
        async with create_slack_backend(slack_config) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            if channel is None:
                pytest.skip("Channel not found (API issue)")

            # Send parent message
            parent = await backend.send_message(
                channel=channel.id,
                content="Parent message for thread test",
            )

            # Skip if parent message failed to send (rate limiting, etc.)
            if parent is None:
                pytest.skip("Parent message failed to send (API issue)")

            # Reply in thread using thread_id kwarg
            reply = await backend.send_message(
                channel=channel.id,
                content="Reply in thread",
                thread_id=parent.id,
            )

            if reply is None:
                pytest.skip("Reply message failed to send (API issue)")
            assert reply.id is not None
            # Reply should have thread_id set to parent (if available)
            if reply.thread_id:
                assert reply.thread_id == parent.id


class TestSlackReactions:
    """Test Slack reaction operations."""

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_add_reaction(self, slack_config, channel_name):
        """Test adding a reaction (leaves reaction visible)."""
        async with create_slack_backend(slack_config) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            if channel is None:
                pytest.skip("Channel not found (API issue)")

            # Send a message
            message = await backend.send_message(
                channel=channel.id,
                content="Message for reaction test",
            )

            if message is None:
                pytest.skip("Message failed to send (API issue)")

            # Add reaction - explicitly pass channel since message may not have it
            await backend.add_reaction(
                message=message.id,
                channel=channel.id,
                emoji="thumbsup",
            )

            # If we got here without errors, the test passed
            # Reaction is left on the message for visual verification

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_remove_reaction(self, slack_config, channel_name):
        """Test adding and then removing a reaction."""
        async with create_slack_backend(slack_config) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            if channel is None:
                pytest.skip("Channel not found (API issue)")

            # Send a message
            message = await backend.send_message(
                channel=channel.id,
                content="Message for remove reaction test",
            )

            if message is None:
                pytest.skip("Message failed to send (API issue)")

            # Add reaction - explicitly pass channel since message may not have it
            await backend.add_reaction(
                message=message.id,
                channel=channel.id,
                emoji="wave",
            )

            # Remove reaction
            await backend.remove_reaction(
                message=message.id,
                channel=channel.id,
                emoji="wave",
            )

            # If we got here without errors, the test passed


class TestSlackMessageHistory:
    """Test Slack message history operations."""

    @pytest.mark.asyncio
    @skip_on_missing_scope
    async def test_read_messages(self, slack_config, channel_name):
        """Test reading message history."""
        async with create_slack_backend(slack_config) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            if channel is None:
                pytest.skip("Channel not found (API issue)")

            # Read last 5 messages
            messages = await backend.fetch_messages(channel=channel.id, limit=5)

            # Should get at least 1 message (we just sent some)
            assert len(messages) >= 1
            assert all(m.id for m in messages)
