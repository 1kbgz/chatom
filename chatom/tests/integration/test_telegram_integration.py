"""Integration tests for Telegram backend.

These tests run against a real Telegram bot when credentials are available.

Environment Variables Required:
    TELEGRAM_TOKEN: Telegram bot token

Environment Variables Optional:
    TELEGRAM_TEST_CHAT_ID: Numeric chat ID for tests
    TELEGRAM_TEST_CHAT_NAME: Public chat username for tests, without @
"""

import os
from contextlib import asynccontextmanager

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TELEGRAM_TOKEN"),
    reason="Telegram credentials not available (set TELEGRAM_TOKEN)",
)


@pytest.fixture
def telegram_config():
    """Create Telegram configuration from environment."""
    from chatom.telegram import TelegramConfig

    return TelegramConfig(bot_token=os.environ.get("TELEGRAM_TOKEN", ""))


@pytest.fixture
def chat_id():
    """Get test chat ID."""
    return os.environ.get("TELEGRAM_TEST_CHAT_ID", "")


@pytest.fixture
def chat_name():
    """Get test chat username."""
    return os.environ.get("TELEGRAM_TEST_CHAT_NAME", "")


@asynccontextmanager
async def create_telegram_backend(config):
    """Create and connect a Telegram backend as async context manager."""
    from chatom.telegram import TelegramBackend

    backend = TelegramBackend(config=config)
    await backend.connect()
    try:
        yield backend
    finally:
        await backend.disconnect()


async def fetch_test_chat(backend, chat_id, chat_name):
    """Fetch configured Telegram chat by ID or public username."""
    if chat_id:
        channel = await backend.fetch_channel(chat_id)
        if channel is not None:
            return channel

    if chat_name:
        channel = await backend.fetch_channel(name=chat_name)
        if channel is not None:
            return channel

    pytest.skip("Telegram test chat not found (set TELEGRAM_TEST_CHAT_ID or public TELEGRAM_TEST_CHAT_NAME)")


class TestTelegramConnection:
    """Test Telegram connection."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, telegram_config):
        """Test basic connection and disconnection."""
        from chatom.telegram import TelegramBackend

        backend = TelegramBackend(config=telegram_config)
        await backend.connect()

        assert backend.connected
        assert backend.name == "telegram"
        assert backend.display_name == "Telegram"
        assert backend.bot_user_id

        await backend.disconnect()
        assert not backend.connected

    @pytest.mark.asyncio
    async def test_get_bot_info(self, telegram_config):
        """Test fetching connected bot info."""
        async with create_telegram_backend(telegram_config) as backend:
            user = await backend.get_bot_info()

            assert user is not None
            assert user.id is not None
            assert user.is_bot


class TestTelegramChatLookup:
    """Test Telegram chat operations."""

    @pytest.mark.asyncio
    async def test_fetch_chat(self, telegram_config, chat_id, chat_name):
        """Test looking up a chat by configured ID or public username."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            assert channel is not None
            assert channel.id is not None

    @pytest.mark.asyncio
    async def test_fetch_chat_by_id(self, telegram_config, chat_id, chat_name):
        """Test looking up a chat by ID."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)
            channel2 = await backend.fetch_channel(id=channel.id)

            assert channel2 is not None
            assert channel2.id == channel.id


class TestTelegramMessaging:
    """Test Telegram messaging operations."""

    @pytest.mark.asyncio
    async def test_send_message(self, telegram_config, chat_id, chat_name):
        """Test sending a simple message."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            message = await backend.send_message(
                channel=channel.id,
                content="Integration test message from chatom",
            )

            assert message is not None
            assert message.id is not None
            assert message.channel_id == channel.id

    @pytest.mark.asyncio
    async def test_send_formatted_message(self, telegram_config, chat_id, chat_name):
        """Test sending a formatted message."""
        from chatom.format import FormattedMessage
        from chatom.format.variant import Format

        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            msg = FormattedMessage()
            msg.add_bold("Test")
            msg.add_text(" - ")
            msg.add_italic("formatted message")
            msg.add_code(" with code")

            message = await backend.send_message(
                channel=channel.id,
                content=msg.render(Format.TELEGRAM_HTML),
            )

            assert message is not None
            assert message.id is not None

    @pytest.mark.asyncio
    async def test_reply_to_message(self, telegram_config, chat_id, chat_name):
        """Test replying to a message."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            parent = await backend.send_message(
                channel=channel.id,
                content="Parent message for reply test",
            )
            reply = await backend.send_message(
                channel=channel.id,
                content="Reply message",
                reply_to=parent,
            )

            assert reply is not None
            assert reply.id is not None
            assert reply.reply_to_message_id == int(parent.id)

    @pytest.mark.asyncio
    async def test_edit_and_delete_message(self, telegram_config, chat_id, chat_name):
        """Test editing and deleting a bot message."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            message = await backend.send_message(
                channel=channel.id,
                content="Message before edit",
            )
            edited = await backend.edit_message(
                message=message.id,
                channel=channel.id,
                content="Message after edit",
            )

            assert edited is not None
            assert edited.id == message.id

            try:
                await backend.delete_message(message=message.id, channel=channel.id)
            except Exception as e:
                pytest.skip(f"Telegram message deletion unavailable: {str(e)[:100]}")

    @pytest.mark.asyncio
    async def test_upload_file(self, telegram_config, chat_id, chat_name):
        """Test uploading a file."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            message = await backend.upload_file(
                channel=channel.id,
                data=b"chatom telegram integration test\n",
                filename="chatom-telegram-integration.txt",
                content_type="text/plain",
                content="Telegram file upload test",
            )

            assert message is not None
            assert message.id is not None


class TestTelegramReactions:
    """Test Telegram reaction operations."""

    @pytest.mark.asyncio
    async def test_add_and_remove_reaction(self, telegram_config, chat_id, chat_name):
        """Test adding and removing a reaction."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            message = await backend.send_message(
                channel=channel.id,
                content="Message for reaction test",
            )

            try:
                await backend.add_reaction(
                    message=message.id,
                    channel=channel.id,
                    emoji="👍",
                )
                await backend.remove_reaction(
                    message=message.id,
                    channel=channel.id,
                    emoji="👍",
                )
            except Exception as e:
                pytest.skip(f"Telegram reactions unavailable: {str(e)[:100]}")


class TestTelegramMessageHistory:
    """Test Telegram message history operations."""

    @pytest.mark.asyncio
    async def test_read_messages_returns_empty(self, telegram_config, chat_id, chat_name):
        """Test Telegram's message history limitation."""
        async with create_telegram_backend(telegram_config) as backend:
            channel = await fetch_test_chat(backend, chat_id, chat_name)

            messages = await backend.fetch_messages(channel=channel.id, limit=5)

            assert messages == []
