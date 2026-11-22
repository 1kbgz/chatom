"""Tests for Discord channel conversion helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatom.base import ChannelType
from chatom.discord import DiscordBackend, DiscordChannelType, DiscordConfig
from chatom.discord.backend import _discord_channel_from_api


def test_discord_dm_channel_from_api_sets_dm_types() -> None:
    channel = SimpleNamespace(id=123, type=SimpleNamespace(value=1))

    result = _discord_channel_from_api(channel)

    assert result.id == "123"
    assert result.name == "DM"
    assert result.channel_type == ChannelType.DIRECT
    assert result.discord_type == DiscordChannelType.DM
    assert result.is_dm is True


def test_discord_text_channel_from_api_sets_public_type() -> None:
    guild = SimpleNamespace(id=456)
    channel = SimpleNamespace(
        id=123,
        name="general",
        type=SimpleNamespace(value=0),
        guild=guild,
        position=3,
        nsfw=False,
        slowmode_delay=0,
    )

    result = _discord_channel_from_api(channel)

    assert result.id == "123"
    assert result.name == "general"
    assert result.guild_id == "456"
    assert result.channel_type == ChannelType.PUBLIC
    assert result.discord_type == DiscordChannelType.GUILD_TEXT
    assert result.is_dm is False


@pytest.mark.asyncio
async def test_fetch_channel_by_name_queries_configured_guild() -> None:
    api_channel = SimpleNamespace(id=789, name="bot-test", topic=None, position=0, nsfw=False, slowmode_delay=0, type=SimpleNamespace(value=0))
    guild = SimpleNamespace(id=456, fetch_channels=AsyncMock(return_value=[api_channel]))
    backend = DiscordBackend(config=DiscordConfig(token="token", guild_id="456"))
    backend._client = MagicMock(fetch_guild=AsyncMock(return_value=guild))

    channel = await backend.fetch_channel(name="bot-test")

    assert channel is not None
    assert channel.id == "789"
    backend._client.fetch_guild.assert_awaited_once_with(456)
