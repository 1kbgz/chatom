from chatom.base import Message
from chatom.format import Format, FormattedMessage, MessageBuilder


class TestBaseMessageConversion:
    """Tests for base Message class conversion methods."""

    def test_message_to_formatted_basic(self):
        """Test converting a basic message to FormattedMessage."""
        from chatom.base import Channel, User

        msg = Message(
            id="m1",
            content="Hello, world!",
            author=User(id="u1", name="Test User"),
            channel=Channel(id="c1", name="test-channel"),
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
        from chatom.base import Channel, User

        original = Message(
            id="m1",
            content="Test message",
            author=User(id="user123"),
            channel=Channel(id="channel456"),
            backend="test",
        )

        formatted = original.to_formatted()
        restored = Message.from_formatted(formatted, backend="test")

        assert restored.content == original.content

    def test_message_to_formatted_with_attachments(self):
        """Test converting a message with attachments to FormattedMessage."""
        from chatom.base import Attachment

        attachment = Attachment(
            id="a1",
            filename="document.pdf",
            url="https://example.com/document.pdf",
            content_type="application/pdf",
            size=1024,
        )
        msg = Message(
            id="m1",
            content="Check out this file!",
            attachments=[attachment],
            backend="test",
        )
        formatted = msg.to_formatted()

        assert len(formatted.attachments) == 1
        assert formatted.attachments[0].filename == "document.pdf"
        assert formatted.attachments[0].url == "https://example.com/document.pdf"
        assert formatted.attachments[0].content_type == "application/pdf"
        assert formatted.attachments[0].size == 1024


class TestNewBaseMessageAttributes:
    """Tests for new shared attributes in base Message class."""

    def test_channel_id_property(self):
        """Test channel_id is derived from channel object."""
        from chatom.base import Channel

        msg = Message(id="m1", channel=Channel(id="c123"))
        assert msg.channel_id == "c123"

    def test_channel_id_empty_when_no_channel(self):
        """Test channel_id returns empty string when no channel."""
        msg = Message(id="m1")
        assert msg.channel_id == ""

    def test_author_id_property(self):
        """Test author_id is derived from author object."""
        from chatom.base import User

        msg = Message(id="m1", author=User(id="u123"))
        assert msg.author_id == "u123"

    def test_author_id_empty_when_no_author(self):
        """Test author_id returns empty string when no author."""
        msg = Message(id="m1")
        assert msg.author_id == ""

    def test_is_bot_attribute(self):
        """Test is_bot attribute."""
        msg = Message(id="m1", is_bot=True)
        assert msg.is_bot is True

    def test_is_system_attribute(self):
        """Test is_system attribute."""
        msg = Message(id="m1", is_system=True)
        assert msg.is_system is True

    def test_mentions_and_mention_ids(self):
        """Test mentions list and mention_ids."""
        from chatom.base import User

        users = [User(id="u1"), User(id="u2"), User(id="u3")]
        msg = Message(id="m1", tags=users)
        # mention_ids should be populated from mentions (once we convert it)
        # For now, test mentions directly
        assert len(msg.mentions) == 3
        assert msg.mentions[0].id == "u1"

    def test_reply_to_and_reply_to_id(self):
        """Test reply_to object and reply_to_id property."""
        parent_msg = Message(id="m0", content="Parent")
        msg = Message(id="m1", reply_to=parent_msg)
        # reply_to_id is now derived from reply_to
        assert msg.reply_to.id == "m0"
        assert msg.reply_to_id == "m0"

    def test_reply_to_id_empty_when_no_reply(self):
        """Test reply_to_id returns empty string when no reply_to."""
        msg = Message(id="m1")
        assert msg.reply_to_id == ""

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
