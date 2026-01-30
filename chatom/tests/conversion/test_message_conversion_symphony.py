from chatom.format import MessageBuilder
from chatom.symphony.channel import SymphonyChannel
from chatom.symphony.user import SymphonyUser


class TestSymphonyMessageConversion:
    """Tests for SymphonyMessage conversion methods."""

    def test_symphony_message_to_formatted(self):
        """Test converting SymphonyMessage to FormattedMessage."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            author=SymphonyUser(id="12345", name="Symphony User"),
            id="ABC123",  # Use id instead of message_id (message_id is now a property)
            channel=SymphonyChannel(id="stream_xyz"),
            content="Hello from Symphony!",
            message_ml="<messageML>Hello from Symphony!</messageML>",
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

        assert msg.channel.id == "stream_123"
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
        assert msg.channel.id == "stream_xyz"
        assert msg.channel_id == "stream_xyz"
        assert msg.author_id == "12345"
        assert msg.backend == "symphony"


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
        from chatom.symphony.user import SymphonyUser

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            mentions=[SymphonyUser(id="12345"), SymphonyUser(id="67890")],
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


class TestSymphonyMentionsUser:
    """Tests for SymphonyMessage.mentions_user() method."""

    def test_mentions_user_in_mentions(self):
        """Test mentions_user finds user in mentions (User objects)."""
        from chatom.symphony import SymphonyMessage
        from chatom.symphony.user import SymphonyUser

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            mentions=[SymphonyUser(id="12345"), SymphonyUser(id="67890")],
        )
        assert msg.mentions_user("12345") is True
        assert msg.mentions_user("99999") is False

    def test_mentions_user_in_entity_data(self):
        """Test mentions_user finds user in entity_data."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            entity_data={
                "mention0": {
                    "type": "com.symphony.user.mention",
                    "id": [{"value": "12345"}],
                }
            },
        )
        assert msg.mentions_user("12345") is True
        assert msg.mentions_user("99999") is False

    def test_mentions_user_in_data_field(self):
        """Test mentions_user extracts from data field when entity_data is empty."""
        import json

        from chatom.symphony import SymphonyMessage

        data = json.dumps(
            {
                "mention0": {
                    "type": "com.symphony.user.mention",
                    "id": [{"value": "12345"}],
                }
            }
        )
        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            data=data,
        )
        assert msg.mentions_user("12345") is True
        assert msg.mentions_user("99999") is False

    def test_mentions_user_with_non_numeric_id(self):
        """Test mentions_user handles non-numeric user IDs gracefully."""
        from chatom.symphony import SymphonyMessage
        from chatom.symphony.user import SymphonyUser

        msg = SymphonyMessage(
            id="m1",
            message_id="msgid1",
            mentions=[SymphonyUser(id="abc-user")],
        )
        assert msg.mentions_user("abc-user") is True
        # Non-numeric can't match int mentions list
        assert msg.mentions_user("xyz") is False

    def test_mentions_user_no_mentions(self):
        """Test mentions_user returns False when no mentions exist."""
        from chatom.symphony import SymphonyMessage

        msg = SymphonyMessage(id="m1", message_id="msgid1")
        assert msg.mentions_user("12345") is False


class TestSymphonyExtractMentionsFromData:
    """Tests for SymphonyMessage.extract_mentions_from_data() static method."""

    def test_extract_mentions_from_valid_data(self):
        """Test extracting mentions from valid JSON data."""
        import json

        from chatom.symphony import SymphonyMessage

        data = json.dumps(
            {
                "mention0": {
                    "type": "com.symphony.user.mention",
                    "id": [{"value": "12345"}],
                },
                "mention1": {
                    "type": "com.symphony.user.mention",
                    "id": [{"value": "67890"}],
                },
            }
        )
        result = SymphonyMessage.extract_mentions_from_data(data)
        assert result == [12345, 67890]

    def test_extract_mentions_from_empty_data(self):
        """Test extracting mentions from None data."""
        from chatom.symphony import SymphonyMessage

        assert SymphonyMessage.extract_mentions_from_data(None) == []
        assert SymphonyMessage.extract_mentions_from_data("") == []

    def test_extract_mentions_from_invalid_json(self):
        """Test extracting mentions from invalid JSON."""
        from chatom.symphony import SymphonyMessage

        assert SymphonyMessage.extract_mentions_from_data("not json") == []
        assert SymphonyMessage.extract_mentions_from_data("{invalid}") == []

    def test_extract_mentions_ignores_non_mention_entities(self):
        """Test that non-mention entities are ignored."""
        import json

        from chatom.symphony import SymphonyMessage

        data = json.dumps(
            {
                "hashtag0": {"type": "org.symphonyoss.taxonomy", "value": "test"},
                "mention0": {
                    "type": "com.symphony.user.mention",
                    "id": [{"value": "12345"}],
                },
            }
        )
        result = SymphonyMessage.extract_mentions_from_data(data)
        assert result == [12345]

    def test_extract_mentions_handles_missing_id_field(self):
        """Test handling entities with missing id field."""
        import json

        from chatom.symphony import SymphonyMessage

        data = json.dumps(
            {
                "mention0": {
                    "type": "com.symphony.user.mention",
                    # No id field
                },
            }
        )
        result = SymphonyMessage.extract_mentions_from_data(data)
        assert result == []

    def test_extract_mentions_handles_empty_id_list(self):
        """Test handling entities with empty id list."""
        import json

        from chatom.symphony import SymphonyMessage

        data = json.dumps(
            {
                "mention0": {
                    "type": "com.symphony.user.mention",
                    "id": [],
                },
            }
        )
        result = SymphonyMessage.extract_mentions_from_data(data)
        assert result == []

    def test_extract_mentions_handles_non_dict_entity(self):
        """Test handling non-dict entity values."""
        import json

        from chatom.symphony import SymphonyMessage

        data = json.dumps(
            {
                "mention0": "not a dict",
                "mention1": {
                    "type": "com.symphony.user.mention",
                    "id": [{"value": "12345"}],
                },
            }
        )
        result = SymphonyMessage.extract_mentions_from_data(data)
        assert result == [12345]
