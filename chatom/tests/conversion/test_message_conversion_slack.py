from chatom.base import Organization, Thread
from chatom.format import Format, MessageBuilder


class TestSlackMessageConversion:
    """Tests for SlackMessage conversion methods."""

    def test_slack_message_to_formatted(self):
        """Test converting SlackMessage to FormattedMessage."""
        from chatom.slack import SlackMessage
        from chatom.slack.channel import SlackChannel
        from chatom.slack.user import SlackUser

        msg = SlackMessage(
            id="1234567890.123456",
            channel=SlackChannel(id="C12345"),
            author=SlackUser(id="U12345", name="Test User"),
            text="Hello from Slack!",
            organization=Organization(id="T12345"),
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
        from chatom.slack.channel import SlackChannel
        from chatom.slack.user import SlackUser

        fm = MessageBuilder().bold("Important").text(": Test").build()
        msg = SlackMessage.from_formatted(
            fm,
            channel=SlackChannel(id="C12345"),
            author=SlackUser(id="U12345", name="Test"),
        )

        assert "*Important*: Test" in msg.text
        assert msg.channel_id == "C12345"

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

        assert msg.id == "1234567890.123456"
        assert msg.channel.id == "C12345"
        assert msg.sender_id == "U12345"
        assert msg.author_id == "U12345"
        assert msg.is_bot is True
        assert msg.backend == "slack"
        assert msg.raw == data

    def test_slack_message_to_formatted_with_files(self):
        """Test converting SlackMessage with file attachments to FormattedMessage."""
        from chatom.slack import SlackMessage
        from chatom.slack.channel import SlackChannel
        from chatom.slack.user import SlackUser

        msg = SlackMessage(
            id="1234567890.123456",
            channel=SlackChannel(id="C12345"),
            author=SlackUser(id="U12345", name="Test User"),
            text="Check out this file!",
            files=[
                {
                    "name": "document.pdf",
                    "url_private": "https://files.slack.com/doc.pdf",
                    "mimetype": "application/pdf",
                    "size": 1024,
                },
                {
                    "name": "image.png",
                    "permalink": "https://files.slack.com/img.png",
                    "mimetype": "image/png",
                    "size": 2048,
                },
            ],
            thread=Thread(id="1234567890.000001"),
            organization=Organization(id="T12345"),
        )
        formatted = msg.to_formatted()

        assert len(formatted.attachments) == 2
        assert formatted.attachments[0].filename == "document.pdf"
        assert formatted.attachments[0].content_type == "application/pdf"
        assert formatted.attachments[1].filename == "image.png"
        assert formatted.metadata["thread_ts"] == "1234567890.000001"
        assert formatted.metadata["team_id"] == "T12345"

    def test_slack_message_from_api_response_with_subtype(self):
        """Test creating SlackMessage from API response with message subtype."""
        from chatom.slack import SlackMessage, SlackMessageSubtype

        data = {
            "ts": "1234567890.123456",
            "channel": "C12345",
            "user": "U12345",
            "text": "has joined the channel",
            "subtype": "channel_join",
        }
        msg = SlackMessage.from_api_response(data)

        assert msg.subtype == SlackMessageSubtype.CHANNEL_JOIN
        assert msg.text == "has joined the channel"

    def test_slack_message_from_api_response_with_unknown_subtype(self):
        """Test creating SlackMessage from API response with unknown subtype."""
        from chatom.slack import SlackMessage

        data = {
            "ts": "1234567890.123456",
            "channel": "C12345",
            "user": "U12345",
            "text": "Something happened",
            "subtype": "unknown_future_subtype",
        }
        msg = SlackMessage.from_api_response(data)

        # Unknown subtypes should not crash, just be None
        assert msg.subtype is None


class TestSlackMessageProperties:
    """Tests for SlackMessage computed properties."""

    def test_is_thread_reply_true(self):
        """Test is_thread_reply returns True when in a thread."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="1234567890.000002",
            thread=Thread(id="1234567890.000001"),
        )
        assert msg.is_thread_reply is True

    def test_is_thread_reply_false_no_thread(self):
        """Test is_thread_reply returns False when not in a thread."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1")
        assert msg.is_thread_reply is False

    def test_is_thread_reply_false_same_ts(self):
        """Test is_thread_reply returns False when ts == thread_ts (parent)."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="1234567890.000001",
            thread=Thread(id="1234567890.000001"),
        )
        assert msg.is_thread_reply is False

    def test_is_thread_parent(self):
        """Test is_thread_parent returns True when reply_count > 0."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", reply_count=5)
        assert msg.is_thread_parent is True

    def test_is_thread_parent_false(self):
        """Test is_thread_parent returns False when reply_count == 0."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1")
        assert msg.is_thread_parent is False

    def test_is_bot_message_by_is_bot(self):
        """Test is_bot_message returns True when author has is_bot=True."""
        from chatom.slack import SlackMessage
        from chatom.slack.user import SlackUser

        author = SlackUser(id="B12345", name="Bot", is_bot=True)
        msg = SlackMessage(id="m1", author=author, is_bot=True)
        assert msg.is_bot_message is True

    def test_is_bot_message_by_subtype(self):
        """Test is_bot_message returns True for bot_message subtype."""
        from chatom.slack import SlackMessage, SlackMessageSubtype

        msg = SlackMessage(id="m1", subtype=SlackMessageSubtype.BOT_MESSAGE)
        assert msg.is_bot_message is True

    def test_is_bot_message_false(self):
        """Test is_bot_message returns False for regular messages."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1")
        assert msg.is_bot_message is False

    def test_has_blocks(self):
        """Test has_blocks returns True when blocks are present."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="1234567890.000001",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}}],
        )
        assert msg.has_blocks is True

    def test_has_blocks_false(self):
        """Test has_blocks returns False when no blocks."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1")
        assert msg.has_blocks is False

    def test_has_files(self):
        """Test has_files returns True when files are attached."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="1234567890.000001",
            files=[{"id": "F123", "name": "file.txt"}],
        )
        assert msg.has_files is True

    def test_has_files_false(self):
        """Test has_files returns False when no files."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1")
        assert msg.has_files is False

    def test_permalink(self):
        """Test permalink generation."""
        from chatom.slack import SlackMessage
        from chatom.slack.channel import SlackChannel

        msg = SlackMessage(
            id="1234567890.000001",
            channel=SlackChannel(id="C12345"),
        )
        permalink = msg.permalink
        assert permalink is not None
        assert "C12345" in permalink
        assert "1234567890000001" in permalink

    def test_permalink_none_without_channel(self):
        """Test permalink returns None without channel."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="1234567890.000001")
        assert msg.permalink is None

    def test_mentions_user_in_content(self):
        """Test mentions_user finds mention in content field."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="1234567890.000001",
            content="Hello <@U12345678>!",
        )
        assert msg.mentions_user("U12345678") is True
        assert msg.mentions_user("U99999999") is False

    def test_mentions_user_in_text(self):
        """Test mentions_user finds mention in text field."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(
            id="1234567890.000001",
            text="Hi <@U12345678>, please review",
        )
        assert msg.mentions_user("U12345678") is True
        assert msg.mentions_user("U99999999") is False

    def test_mentions_user_in_mentions_list(self):
        """Test mentions_user finds user in mentions list."""
        from chatom.slack import SlackMessage
        from chatom.slack.user import SlackUser

        msg = SlackMessage(
            id="1234567890.000001",
            tags=[SlackUser(id="U12345678"), SlackUser(id="U87654321")],
        )
        assert msg.mentions_user("U12345678") is True
        assert msg.mentions_user("U99999999") is False

    def test_mentions_user_false_when_empty(self):
        """Test mentions_user returns False when no mentions."""
        from chatom.slack import SlackMessage

        msg = SlackMessage(id="m1", content="Hello world!")
        assert msg.mentions_user("U12345678") is False
