class TestCrossBackendConversion:
    """Tests for converting messages between backends."""

    def test_slack_to_discord(self):
        """Test converting Slack message format to Discord format."""
        from chatom.discord import DiscordMessage
        from chatom.discord.channel import DiscordChannel
        from chatom.slack import SlackMessage
        from chatom.slack.channel import SlackChannel
        from chatom.slack.user import SlackUser

        slack_msg = SlackMessage(
            id="1234567890.123456",
            channel=SlackChannel(id="C12345"),
            author=SlackUser(id="U12345"),
            text="Hello *bold* and _italic_",
        )

        # Convert to FormattedMessage
        formatted = slack_msg.to_formatted()

        # Convert to Discord
        discord_msg = DiscordMessage.from_formatted(formatted, channel=DiscordChannel(id="D12345"))

        assert discord_msg.backend == "discord"

    def test_symphony_to_slack(self):
        """Test converting Symphony message to Slack format."""
        from chatom.slack import SlackMessage
        from chatom.slack.channel import SlackChannel
        from chatom.symphony import SymphonyMessage
        from chatom.symphony.channel import SymphonyChannel

        symphony_msg = SymphonyMessage(
            id="ABC123",
            channel=SymphonyChannel(id="stream_xyz"),
            message_ml="<messageML><b>Alert</b>: New message</messageML>",
        )

        formatted = symphony_msg.to_formatted()
        slack_msg = SlackMessage.from_formatted(formatted, channel=SlackChannel(id="C12345"))

        assert slack_msg.channel_id == "C12345"
