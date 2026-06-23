"""Tests for Discord channel conversion helpers."""

from types import SimpleNamespace

from chatom.base import ChannelType
from chatom.discord import DiscordChannelType
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
