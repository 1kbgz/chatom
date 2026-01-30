from chatom.format import Format, MessageBuilder


class TestDiscordMessageConversion:
    """Tests for DiscordMessage conversion methods."""

    def test_discord_message_to_formatted(self):
        """Test converting DiscordMessage to FormattedMessage."""
        from chatom.base import Organization
        from chatom.discord import DiscordMessage
        from chatom.discord.channel import DiscordChannel
        from chatom.discord.user import DiscordUser

        msg = DiscordMessage(
            id="123456789",
            content="Hello from Discord!",
            channel=DiscordChannel(id="987654321"),
            author=DiscordUser(id="111222333", name="Test User"),
            guild=Organization(id="444555666"),
        )
        formatted = msg.to_formatted()

        assert formatted.metadata["source_backend"] == "discord"
        assert formatted.metadata["message_id"] == "123456789"
        assert formatted.metadata["channel_id"] == "987654321"
        assert formatted.metadata["guild_id"] == "444555666"
        assert "Hello from Discord!" in formatted.render(Format.PLAINTEXT)

    def test_discord_message_from_formatted(self):
        """Test creating DiscordMessage from FormattedMessage."""
        from chatom.discord import DiscordMessage
        from chatom.discord.channel import DiscordChannel

        fm = MessageBuilder().bold("Announcement").text(": New feature!").build()
        msg = DiscordMessage.from_formatted(fm, channel=DiscordChannel(id="C12345"))

        assert "**Announcement**: New feature!" in msg.content

    def test_discord_message_from_api_response(self):
        """Test creating DiscordMessage from API response."""
        from chatom.discord import DiscordMessage

        data = {
            "id": "123456789",
            "content": "Hello!",
            "channel_id": "987654321",
            "author": {"id": "111222333", "bot": True},
            "guild_id": "444555666",
            "type": 0,
            "pinned": True,
        }
        msg = DiscordMessage.from_api_response(data)

        assert msg.id == "123456789"
        assert msg.channel_id == "987654321"
        assert msg.author_id == "111222333"
        assert msg.is_bot is True
        assert msg.is_pinned is True
        assert msg.backend == "discord"
