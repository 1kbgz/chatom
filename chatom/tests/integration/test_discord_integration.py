"""Integration tests for Discord backend.

These tests run against a real Discord server when credentials are available.

Environment Variables Required:
    DISCORD_TOKEN: Discord bot token
    DISCORD_GUILD_NAME: Discord server/guild name
    DISCORD_TEST_CHANNEL_NAME: Channel name for tests
    DISCORD_TEST_USER_NAME: Username for mention tests
"""

import os
from contextlib import asynccontextmanager

import pytest

# Skip all tests if Discord credentials not available
pytestmark = pytest.mark.skipif(
    not os.environ.get("DISCORD_TOKEN") or not os.environ.get("DISCORD_GUILD_NAME"),
    reason="Discord credentials not available (set DISCORD_TOKEN and DISCORD_GUILD_NAME)",
)


@pytest.fixture
def discord_config():
    """Create Discord configuration from environment."""
    from chatom.discord import DiscordConfig

    return DiscordConfig(
        token=os.environ.get("DISCORD_TOKEN", ""),
        intents=["guilds", "guild_messages"],
    )


@pytest.fixture
def guild_name():
    """Get test guild name."""
    return os.environ.get("DISCORD_GUILD_NAME", "")


@pytest.fixture
def channel_name():
    """Get test channel name."""
    return os.environ.get("DISCORD_TEST_CHANNEL_NAME", "")


@pytest.fixture
def user_name():
    """Get test user name."""
    return os.environ.get("DISCORD_TEST_USER_NAME", "")


@asynccontextmanager
async def create_discord_backend(config, guild_name=None):
    """Create and connect a Discord backend as async context manager."""
    from chatom.discord import DiscordBackend

    backend = DiscordBackend(config=config)
    await backend.connect()

    # Resolve guild if provided
    if guild_name:
        guild = await backend.fetch_organization(name=guild_name)
        if guild:
            backend.config.guild_id = guild.id

    try:
        yield backend
    finally:
        await backend.disconnect()


class TestDiscordConnection:
    """Test Discord connection."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, discord_config):
        """Test basic connection and disconnection."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend(config=discord_config)
        await backend.connect()

        assert backend.connected
        assert backend.name == "discord"
        assert backend.display_name == "Discord"

        await backend.disconnect()
        assert not backend.connected


class TestDiscordOrganization:
    """Test Discord organization (guild) operations."""

    @pytest.mark.asyncio
    async def test_list_organizations(self, discord_config, guild_name):
        """Test listing guilds."""
        async with create_discord_backend(discord_config, guild_name) as backend:
            guilds = await backend.list_organizations()

            assert len(guilds) >= 1
            assert all(g.id for g in guilds)
            assert all(g.name for g in guilds)

    @pytest.mark.asyncio
    async def test_fetch_organization_by_name_parameter(self, discord_config, guild_name):
        """Test fetching a guild by name using the name parameter."""
        async with create_discord_backend(discord_config, guild_name) as backend:
            guild = await backend.fetch_organization(name=guild_name)

            assert guild is not None
            assert guild.id is not None
            assert guild.name.lower() == guild_name.lower()


class TestDiscordChannelLookup:
    """Test Discord channel operations."""

    @pytest.mark.asyncio
    async def test_fetch_channel_by_name(self, discord_config, guild_name, channel_name):
        """Test looking up a channel by name."""
        if not channel_name:
            pytest.skip("DISCORD_TEST_CHANNEL_NAME not set")

        async with create_discord_backend(discord_config, guild_name) as backend:
            channel = await backend.fetch_channel(name=channel_name)

            assert channel is not None
            assert channel.id is not None


class TestDiscordMessaging:
    """Test Discord messaging operations."""

    @pytest.mark.asyncio
    async def test_send_message(self, discord_config, guild_name, channel_name):
        """Test sending a simple message."""
        if not channel_name:
            pytest.skip("DISCORD_TEST_CHANNEL_NAME not set")

        async with create_discord_backend(discord_config, guild_name) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            assert channel is not None

            message = await backend.send_message(
                channel=channel.id,
                content="Integration test message from chatom 🧪",
            )

            assert message is not None
            assert message.id is not None
            assert message.channel_id == channel.id

    @pytest.mark.asyncio
    async def test_send_formatted_message(self, discord_config, guild_name, channel_name):
        """Test sending a formatted message."""
        from chatom.format import FormattedMessage
        from chatom.format.variant import Format

        if not channel_name:
            pytest.skip("DISCORD_TEST_CHANNEL_NAME not set")

        async with create_discord_backend(discord_config, guild_name) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            assert channel is not None

            msg = FormattedMessage()
            msg.add_bold("Test")
            msg.add_text(" - ")
            msg.add_italic("formatted message")
            msg.add_code(" with code")

            content = msg.render(Format.DISCORD_MARKDOWN)

            message = await backend.send_message(
                channel=channel.id,
                content=content,
            )

            assert message is not None
            assert message.id is not None


class TestDiscordReactions:
    """Test Discord reaction operations."""

    @pytest.mark.asyncio
    async def test_add_reaction(self, discord_config, guild_name, channel_name):
        """Test adding a reaction."""
        if not channel_name:
            pytest.skip("DISCORD_TEST_CHANNEL_NAME not set")

        async with create_discord_backend(discord_config, guild_name) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            assert channel is not None

            # Send a message
            message = await backend.send_message(
                channel=channel.id,
                content="Message for reaction test",
            )

            # Add reaction - explicitly pass channel
            await backend.add_reaction(
                message=message.id,
                channel=channel.id,
                emoji="👍",
            )

            # If we got here without errors, the test passed


class TestDiscordMessageHistory:
    """Test Discord message history operations."""

    @pytest.mark.asyncio
    async def test_read_messages(self, discord_config, guild_name, channel_name):
        """Test reading message history."""
        if not channel_name:
            pytest.skip("DISCORD_TEST_CHANNEL_NAME not set")

        async with create_discord_backend(discord_config, guild_name) as backend:
            channel = await backend.fetch_channel(name=channel_name)
            assert channel is not None

            # Read last 5 messages
            messages = await backend.fetch_messages(channel=channel.id, limit=5)

            # Should get at least 1 message (we just sent some)
            assert len(messages) >= 1
            assert all(m.id for m in messages)
