"""Tests for message conversion functionality.

This module tests the to_formatted() and from_formatted() methods
on the base Message class and backend-specific message classes.
"""

from chatom.base import Message
from chatom.format import Format, FormattedMessage, MessageBuilder


class TestBaseMessageConversion:
    """Tests for base Message class conversion methods."""

    def test_message_to_formatted_basic(self):
        """Test converting a basic message to FormattedMessage."""
        msg = Message(
            id="m1",
            content="Hello, world!",
            author_id="u1",
            channel_id="c1",
            backend="test",
        )
        formatted = msg.to_formatted()

        assert isinstance(formatted, FormattedMessage)
        assert "Hello, world!" in formatted.render(Format.PLAINTEXT)
        assert formatted.metadata["source_backend"] == "test"
        assert formatted.metadata["message_id"] == "m1"
        assert formatted.metadata["author_id"] == "u1"
        assert formatted.metadata["channel_id"] == "c1"

    def test_message_to_formatted_with_formatted_content(self):
        """Test that formatted_content is used when available."""
        msg = Message(
            id="m1",
            content="Plain text",
            formatted_content="<b>Rich text</b>",
            backend="test",
        )
        formatted = msg.to_formatted()

        # Should use formatted_content
        assert "<b>Rich text</b>" in formatted.render(Format.PLAINTEXT)

    def test_message_from_formatted_slack(self):
        """Test creating a message from FormattedMessage for Slack."""
        from chatom.slack import SlackMessage

        fm = MessageBuilder().bold("Hello").text(" world").build()
        msg = SlackMessage.from_formatted(fm)

        # Slack uses *text* for bold
        assert "*Hello* world" in msg.content or "*Hello* world" in msg.text

    def test_message_from_formatted_discord(self):
        """Test creating a message from FormattedMessage for Discord."""
        fm = MessageBuilder().bold("Hello").text(" world").build()
        msg = Message.from_formatted(fm, backend="discord")

        assert msg.backend == "discord"
        # Discord uses **text** for bold
        assert "**Hello** world" in msg.content

    def test_message_render_for(self):
        """Test rendering a message for different backends."""
        msg = Message(
            id="m1",
            content="Hello **world**",
            backend="discord",
        )

        # render_for should convert between backend formats
        result = msg.render_for("slack")
        # The base implementation uses to_formatted which adds plain text
        assert "Hello" in result

    def test_message_roundtrip(self):
        """Test converting message to formatted and back."""
        original = Message(
            id="m1",
            content="Test message",
            author_id="user123",
            channel_id="channel456",
            backend="test",
        )

        formatted = original.to_formatted()
        restored = Message.from_formatted(formatted, backend="test")

        assert restored.content == original.content


class TestSlackMessageConversion:
    """Tests for SlackMessage conversion methods."""

    def test_slack_message_to_formatted(self):
        """Test converting SlackMessage to FormattedMessage."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            ts="1234567890.123456",
            channel="C12345",
            sender_id="U12345",
            text="Hello from Slack!",
            team="T12345",
        )
        formatted = msg.to_formatted()

        assert formatted.metadata["source_backend"] == "slack"
        assert formatted.metadata["ts"] == "1234567890.123456"
        assert formatted.metadata["author_id"] == "U12345"
        assert formatted.metadata["channel_id"] == "C12345"
        assert "Hello from Slack!" in formatted.render(Format.PLAINTEXT)

    def test_slack_message_from_formatted(self):
        """Test creating SlackMessage from FormattedMessage."""
        from chatom.slack import SlackMessage

        fm = MessageBuilder().bold("Important").text(": Test").build()
        msg = SlackMessage.from_formatted(fm, channel="C12345", sender_id="U12345")

        assert "*Important*: Test" in msg.text
        assert msg.channel == "C12345"

    def test_slack_message_from_api_response(self):
        """Test creating SlackMessage from API response."""
        from chatom.slack import SlackMessage

        data = {
            "ts": "1234567890.123456",
            "channel": "C12345",
            "user": "U12345",
            "text": "Hello!",
            "team": "T12345",
            "bot_id": "B12345",
        }
        msg = SlackMessage.from_api_response(data)

        assert msg.ts == "1234567890.123456"
        assert msg.channel == "C12345"
        assert msg.channel_id == "C12345"
        assert msg.sender_id == "U12345"
        assert msg.author_id == "U12345"
        assert msg.is_bot is True
        assert msg.backend == "slack"
        assert msg.raw == data


class TestDiscordMessageConversion:
    """Tests for DiscordMessage conversion methods."""

    def test_discord_message_to_formatted(self):
        """Test converting DiscordMessage to FormattedMessage."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(
            id="123456789",
            content="Hello from Discord!",
            channel_id="987654321",
            author_id="111222333",
            guild_id="444555666",
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

        fm = MessageBuilder().bold("Announcement").text(": New feature!").build()
        msg = DiscordMessage.from_formatted(fm, channel_id="C12345")

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


class TestSymphonyMessageConversion:
    """Tests for SymphonyMessage conversion methods."""

    def test_symphony_message_to_formatted(self):
        """Test converting SymphonyMessage to FormattedMessage."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            message_id="ABC123",
            stream_id="stream_xyz",
            content="Hello from Symphony!",
            message_ml="<messageML>Hello from Symphony!</messageML>",
            from_user_id=12345,
            hashtags=["#test"],
            cashtags=["$AAPL"],
        )
        formatted = msg.to_formatted()

        assert formatted.metadata["source_backend"] == "symphony"
        assert formatted.metadata["message_id"] == "ABC123"
        assert formatted.metadata["stream_id"] == "stream_xyz"
        assert formatted.metadata["hashtags"] == ["#test"]
        assert formatted.metadata["cashtags"] == ["$AAPL"]

    def test_symphony_message_from_formatted(self):
        """Test creating SymphonyMessage from FormattedMessage."""
        from chatom.symphony import SymphonyMessage

        fm = MessageBuilder().bold("Alert").text(": Check this out").build()
        msg = SymphonyMessage.from_formatted(fm, stream_id="stream_123")

        assert msg.stream_id == "stream_123"
        # Symphony uses <b> tags
        assert "<b>Alert</b>" in msg.message_ml or "Alert" in msg.message_ml

    def test_symphony_message_from_api_response(self):
        """Test creating SymphonyMessage from API response."""
        from chatom.symphony import SymphonyMessage

        data = {
            "messageId": "ABC123",
            "stream": {"streamId": "stream_xyz"},
            "message": "<messageML>Hello!</messageML>",
            "user": {"userId": 12345},
            "timestamp": 1609459200000,
        }
        msg = SymphonyMessage.from_api_response(data)

        assert msg.message_id == "ABC123"
        assert msg.stream_id == "stream_xyz"
        assert msg.channel_id == "stream_xyz"
        assert msg.author_id == "12345"
        assert msg.backend == "symphony"


class TestMatrixMessageConversion:
    """Tests for MatrixMessage conversion methods."""

    def test_matrix_message_to_formatted(self):
        """Test converting MatrixMessage to FormattedMessage."""
        from chatom.matrix import MatrixMessage, MatrixMessageFormat

        msg = MatrixMessage(
            event_id="$abc123",
            room_id="!room:example.com",
            sender="@user:example.com",
            content="Hello from Matrix!",
            formatted_body="<b>Hello</b> from Matrix!",
            format=MatrixMessageFormat.HTML.value,
        )
        formatted = msg.to_formatted()

        assert formatted.metadata["source_backend"] == "matrix"
        assert formatted.metadata["event_id"] == "$abc123"
        assert formatted.metadata["room_id"] == "!room:example.com"
        assert formatted.metadata["sender"] == "@user:example.com"
        assert formatted.metadata["has_html"] is True

    def test_matrix_message_from_formatted(self):
        """Test creating MatrixMessage from FormattedMessage."""
        from chatom.matrix import MatrixMessage

        fm = MessageBuilder().bold("Notice").text(": Hello").build()
        msg = MatrixMessage.from_formatted(fm, room_id="!room:example.com")

        assert msg.room_id == "!room:example.com"
        assert msg.backend == "matrix"
        assert msg.formatted_body  # Should have HTML formatted body

    def test_matrix_message_from_event(self):
        """Test creating MatrixMessage from Matrix event."""
        from chatom.matrix import MatrixMessage

        event = {
            "event_id": "$abc123",
            "room_id": "!room:example.com",
            "sender": "@user:example.com",
            "type": "m.room.message",
            "content": {
                "msgtype": "m.text",
                "body": "Hello!",
                "format": "org.matrix.custom.html",
                "formatted_body": "<b>Hello!</b>",
            },
            "origin_server_ts": 1609459200000,
        }
        msg = MatrixMessage.from_event(event)

        assert msg.event_id == "$abc123"
        assert msg.room_id == "!room:example.com"
        assert msg.channel_id == "!room:example.com"
        assert msg.sender == "@user:example.com"
        assert msg.author_id == "@user:example.com"
        assert msg.formatted_body == "<b>Hello!</b>"
        assert msg.backend == "matrix"


class TestIRCMessageConversion:
    """Tests for IRCMessage conversion methods."""

    def test_irc_message_to_formatted(self):
        """Test converting IRCMessage to FormattedMessage."""
        from chatom.irc import IRCMessage

        msg = IRCMessage(
            id="msg1",
            content="Hello from IRC!",
            nick="user123",
            target="#channel",
        )
        formatted = msg.to_formatted()

        assert formatted.metadata["source_backend"] == "irc"
        assert formatted.metadata["nick"] == "user123"
        assert formatted.metadata["target"] == "#channel"
        assert "Hello from IRC!" in formatted.render(Format.PLAINTEXT)

    def test_irc_action_message_to_formatted(self):
        """Test converting IRC ACTION message to FormattedMessage."""
        from chatom.irc import IRCMessage

        msg = IRCMessage(
            id="msg1",
            content="waves hello",
            nick="user123",
            target="#channel",
            is_action=True,
        )
        formatted = msg.to_formatted()

        assert formatted.metadata["is_action"] is True
        # ACTION should be rendered as italic /me style
        rendered = formatted.render(Format.PLAINTEXT)
        assert "user123" in rendered
        assert "waves hello" in rendered

    def test_irc_message_from_formatted(self):
        """Test creating IRCMessage from FormattedMessage."""
        from chatom.irc import IRCMessage

        fm = MessageBuilder().text("Hello everyone!").build()
        msg = IRCMessage.from_formatted(fm, target="#channel", nick="bot")

        assert msg.target == "#channel"
        assert msg.nick == "bot"
        assert msg.backend == "irc"
        assert "Hello everyone!" in msg.content

    def test_irc_message_from_raw(self):
        """Test parsing IRC message from raw line."""
        from chatom.irc import IRCMessage

        raw = ":nick!user@host PRIVMSG #channel :Hello, world!"
        msg = IRCMessage.from_raw(raw)

        assert msg.nick == "nick"
        assert msg.target == "#channel"
        assert msg.content == "Hello, world!"
        assert msg.is_channel_message is True
        assert msg.channel_id == "#channel"
        assert msg.author_id == "nick"
        assert msg.backend == "irc"


class TestEmailMessageConversion:
    """Tests for EmailMessage conversion methods."""

    def test_email_message_to_formatted(self):
        """Test converting EmailMessage to FormattedMessage."""
        from chatom.email import EmailMessage

        msg = EmailMessage(
            message_id="<abc123@example.com>",
            subject="Test Email",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            html_body="<p>Hello from Email!</p>",
            plain_body="Hello from Email!",
        )
        formatted = msg.to_formatted()

        assert formatted.metadata["source_backend"] == "email"
        assert formatted.metadata["subject"] == "Test Email"
        assert formatted.metadata["from_address"] == "sender@example.com"
        assert "Hello from Email!" in formatted.render(Format.PLAINTEXT)

    def test_email_message_from_formatted(self):
        """Test creating EmailMessage from FormattedMessage."""
        from chatom.email import EmailMessage

        fm = MessageBuilder().bold("Important").text(": Check this").build()
        msg = EmailMessage.from_formatted(
            fm,
            subject="Test",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
        )

        assert msg.subject == "Test"
        assert msg.backend == "email"
        assert msg.html_body  # Should have HTML body
        assert msg.plain_body  # Should have plain body


class TestCrossBackendConversion:
    """Tests for converting messages between backends."""

    def test_slack_to_discord(self):
        """Test converting Slack message format to Discord format."""
        from chatom.discord import DiscordMessage
        from chatom.slack import SlackMessage

        slack_msg = SlackMessage(
            ts="1234567890.123456",
            channel="C12345",
            sender_id="U12345",
            text="Hello *bold* and _italic_",
        )

        # Convert to FormattedMessage
        formatted = slack_msg.to_formatted()

        # Convert to Discord
        discord_msg = DiscordMessage.from_formatted(formatted, channel_id="D12345")

        assert discord_msg.backend == "discord"

    def test_symphony_to_slack(self):
        """Test converting Symphony message to Slack format."""
        from chatom.slack import SlackMessage
        from chatom.symphony import SymphonyMessage

        symphony_msg = SymphonyMessage(
            message_id="ABC123",
            stream_id="stream_xyz",
            message_ml="<messageML><b>Alert</b>: New message</messageML>",
        )

        formatted = symphony_msg.to_formatted()
        slack_msg = SlackMessage.from_formatted(formatted, channel="C12345")

        assert slack_msg.channel == "C12345"

    def test_email_to_matrix(self):
        """Test converting Email message to Matrix format."""
        from chatom.email import EmailMessage
        from chatom.matrix import MatrixMessage

        email_msg = EmailMessage(
            message_id="<abc@example.com>",
            subject="Hello",
            html_body="<p>Hello <strong>world</strong>!</p>",
            plain_body="Hello world!",
        )

        formatted = email_msg.to_formatted()
        matrix_msg = MatrixMessage.from_formatted(formatted, room_id="!room:example.com")

        assert matrix_msg.room_id == "!room:example.com"
        assert matrix_msg.backend == "matrix"


class TestNewBaseMessageAttributes:
    """Tests for new shared attributes in base Message class."""

    def test_channel_id_attribute(self):
        """Test channel_id attribute."""
        msg = Message(id="m1", channel_id="c123")
        assert msg.channel_id == "c123"

    def test_author_id_attribute(self):
        """Test author_id attribute."""
        msg = Message(id="m1", author_id="u123")
        assert msg.author_id == "u123"

    def test_is_bot_attribute(self):
        """Test is_bot attribute."""
        msg = Message(id="m1", is_bot=True)
        assert msg.is_bot is True

    def test_is_system_attribute(self):
        """Test is_system attribute."""
        msg = Message(id="m1", is_system=True)
        assert msg.is_system is True

    def test_mention_ids_attribute(self):
        """Test mention_ids attribute."""
        msg = Message(id="m1", mention_ids=["u1", "u2", "u3"])
        assert msg.mention_ids == ["u1", "u2", "u3"]

    def test_reply_to_id_attribute(self):
        """Test reply_to_id attribute."""
        msg = Message(id="m1", reply_to_id="m0")
        assert msg.reply_to_id == "m0"

    def test_formatted_content_attribute(self):
        """Test formatted_content attribute."""
        msg = Message(id="m1", formatted_content="<b>Rich</b> text")
        assert msg.formatted_content == "<b>Rich</b> text"

    def test_raw_attribute(self):
        """Test raw attribute."""
        raw_data = {"type": "message", "text": "Hello"}
        msg = Message(id="m1", raw=raw_data)
        assert msg.raw == raw_data

    def test_backend_attribute(self):
        """Test backend attribute."""
        msg = Message(id="m1", backend="slack")
        assert msg.backend == "slack"


class TestSlackMessageProperties:
    """Tests for SlackMessage computed properties."""

    def test_is_thread_reply_true(self):
        """Test is_thread_reply returns True when in a thread."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="m1",
            ts="1234567890.000002",
            thread_ts="1234567890.000001",
        )
        assert msg.is_thread_reply is True

    def test_is_thread_reply_false_no_thread(self):
        """Test is_thread_reply returns False when not in a thread."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001")
        assert msg.is_thread_reply is False

    def test_is_thread_reply_false_same_ts(self):
        """Test is_thread_reply returns False when ts == thread_ts (parent)."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="m1",
            ts="1234567890.000001",
            thread_ts="1234567890.000001",
        )
        assert msg.is_thread_reply is False

    def test_is_thread_parent(self):
        """Test is_thread_parent returns True when reply_count > 0."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001", reply_count=5)
        assert msg.is_thread_parent is True

    def test_is_thread_parent_false(self):
        """Test is_thread_parent returns False when reply_count == 0."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001")
        assert msg.is_thread_parent is False

    def test_is_bot_message_by_bot_id(self):
        """Test is_bot_message returns True when bot_id is set."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001", bot_id="B12345")
        assert msg.is_bot_message is True

    def test_is_bot_message_by_subtype(self):
        """Test is_bot_message returns True for bot_message subtype."""
        from chatom.slack import SlackMessage, SlackMessageSubtype

        msg = SlackMessage(id="m1", ts="1234567890.000001", subtype=SlackMessageSubtype.BOT_MESSAGE)
        assert msg.is_bot_message is True

    def test_is_bot_message_false(self):
        """Test is_bot_message returns False for regular messages."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001")
        assert msg.is_bot_message is False

    def test_has_blocks(self):
        """Test has_blocks returns True when blocks are present."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="m1",
            ts="1234567890.000001",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}}],
        )
        assert msg.has_blocks is True

    def test_has_blocks_false(self):
        """Test has_blocks returns False when no blocks."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001")
        assert msg.has_blocks is False

    def test_has_files(self):
        """Test has_files returns True when files are attached."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="m1",
            ts="1234567890.000001",
            files=[{"id": "F123", "name": "file.txt"}],
        )
        assert msg.has_files is True

    def test_has_files_false(self):
        """Test has_files returns False when no files."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001")
        assert msg.has_files is False

    def test_permalink(self):
        """Test permalink generation."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="m1",
            ts="1234567890.000001",
            channel="C12345",
        )
        permalink = msg.permalink
        assert permalink is not None
        assert "C12345" in permalink
        assert "1234567890000001" in permalink

    def test_permalink_none_without_channel(self):
        """Test permalink returns None without channel."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", ts="1234567890.000001")
        assert msg.permalink is None


class TestSymphonyMessageProperties:
    """Tests for SymphonyMessage computed properties."""

    def test_is_shared_message_true(self):
        """Test is_shared_message returns True when shared_message is set."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            shared_message={"message_id": "orig1", "content": "Shared content"},
        )
        assert msg.is_shared_message is True

    def test_is_shared_message_false(self):
        """Test is_shared_message returns False without shared_message."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(id="m1", message_id="msgid1")
        assert msg.is_shared_message is False

    def test_has_entity_data_true(self):
        """Test has_entity_data returns True when entity data is present."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            entity_data={"entity1": {"type": "custom"}},
        )
        assert msg.has_entity_data is True

    def test_has_entity_data_false(self):
        """Test has_entity_data returns False without entity data."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(id="m1", message_id="msgid1")
        assert msg.has_entity_data is False

    def test_has_hashtags_true(self):
        """Test has_hashtags returns True when hashtags are present."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            hashtags=["python", "symphony"],
        )
        assert msg.has_hashtags is True

    def test_has_hashtags_false(self):
        """Test has_hashtags returns False without hashtags."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(id="m1", message_id="msgid1")
        assert msg.has_hashtags is False

    def test_has_cashtags_true(self):
        """Test has_cashtags returns True when cashtags are present."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            cashtags=["AAPL", "GOOGL"],
        )
        assert msg.has_cashtags is True

    def test_has_cashtags_false(self):
        """Test has_cashtags returns False without cashtags."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(id="m1", message_id="msgid1")
        assert msg.has_cashtags is False

    def test_has_mentions_true(self):
        """Test has_mentions returns True when mentions are present."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            mentions=[12345, 67890],
        )
        assert msg.has_mentions is True

    def test_has_mentions_false(self):
        """Test has_mentions returns False without mentions."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(id="m1", message_id="msgid1")
        assert msg.has_mentions is False

    def test_rendered_content_presentation_ml(self):
        """Test rendered_content returns presentation_ml first."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            presentation_ml="<div>Rendered</div>",
            message_ml="<messageML>Original</messageML>",
            content="Plain text",
        )
        assert msg.rendered_content == "<div>Rendered</div>"

    def test_rendered_content_message_ml(self):
        """Test rendered_content falls back to message_ml."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            message_ml="<messageML>Original</messageML>",
            content="Plain text",
        )
        assert msg.rendered_content == "<messageML>Original</messageML>"

    def test_rendered_content_content(self):
        """Test rendered_content falls back to content."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            content="Plain text",
        )
        assert msg.rendered_content == "Plain text"
