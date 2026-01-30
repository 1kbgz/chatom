"""Tests for chatom.base.testing module.

Tests for MockDataStore and MockBackendMixin classes used in backend testing.
"""

from datetime import datetime, timezone

import pytest

from chatom import Channel, Message, User
from chatom.base.presence import Presence, PresenceStatus
from chatom.base.testing import MockBackendMixin, MockDataStore


class TestMockDataStore:
    """Tests for MockDataStore class."""

    def test_create_empty_data_store(self):
        """Test creating an empty MockDataStore."""
        store = MockDataStore()

        assert store.mock_users == {}
        assert store.mock_channels == {}
        assert store.mock_messages == {}
        assert store.mock_presence == {}
        assert store.sent_messages == []
        assert store.edited_messages == []
        assert store.deleted_messages == []
        assert store.reactions_added == []
        assert store.reactions_removed == []
        assert store.presence_updates == []
        assert store.message_counter == 0

    def test_reset_clears_all_stores(self):
        """Test that reset clears all stores."""
        store = MockDataStore()

        # Add some data
        store.mock_users["123"] = User(id="123", name="Test")
        store.mock_channels["C123"] = Channel(id="C123", name="general")
        store.mock_messages["C123"] = [Message(id="msg1", content="Hello")]
        store.mock_presence["123"] = Presence(status=PresenceStatus.ONLINE)
        store.sent_messages.append(Message(id="msg2", content="Sent"))
        store.deleted_messages.append({"message_id": "msg1", "channel_id": "C123"})
        store.reactions_added.append({"emoji": "thumbsup"})
        store.message_counter = 5

        # Reset
        store.reset()

        assert store.mock_users == {}
        assert store.mock_channels == {}
        assert store.mock_messages == {}
        assert store.mock_presence == {}
        assert store.sent_messages == []
        assert store.deleted_messages == []
        assert store.reactions_added == []
        assert store.message_counter == 0

    def test_get_next_message_id(self):
        """Test generating sequential message IDs."""
        store = MockDataStore()

        id1 = store.get_next_message_id()
        id2 = store.get_next_message_id()
        id3 = store.get_next_message_id()

        assert id1 == "msg_1"
        assert id2 == "msg_2"
        assert id3 == "msg_3"
        assert store.message_counter == 3


class MockBackendUsingMixin(MockBackendMixin):
    """A concrete class using MockBackendMixin for testing.

    Note: We don't define users/channels attributes here because the mixin
    expects them to be sets, but User/Channel objects are not hashable in Pydantic v2.
    The mixin checks hasattr() before using them, so they're optional.
    """

    def __init__(self):
        self._init_mock_data()
        self.connected = False


class TestMockBackendMixin:
    """Tests for MockBackendMixin class."""

    @pytest.fixture
    def backend(self):
        """Create a MockBackendUsingMixin instance."""
        return MockBackendUsingMixin()

    def test_add_mock_user_data(self, backend):
        """Test adding a mock user."""
        user = backend.add_mock_user_data(id="123", name="Test User", email="test@example.com")

        assert user.id == "123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert backend._data.mock_users["123"] == user

    def test_add_mock_user_data_without_handle(self, backend):
        """Test adding a mock user generates handle from name."""
        user = backend.add_mock_user_data(id="123", name="Test User")

        # Handle should be generated from name (lowercase, no spaces)
        assert user.handle == "testuser"

    def test_add_mock_channel_data(self, backend):
        """Test adding a mock channel."""
        channel = backend.add_mock_channel_data(id="C123", name="general", topic="General chat")

        assert channel.id == "C123"
        assert channel.name == "general"
        assert channel.topic == "General chat"
        assert backend._data.mock_channels["C123"] == channel
        # Channel should also be in mock_messages as an empty list
        assert "C123" in backend._data.mock_messages

    def test_add_mock_message_data(self, backend):
        """Test adding a mock message."""
        # First add a channel
        backend.add_mock_channel_data(id="C123", name="general")

        # Add a message
        message = backend.add_mock_message_data(
            channel_id="C123",
            content="Hello world",
            author_id="U123",
        )

        assert message.content == "Hello world"
        assert message.channel_id == "C123"
        assert message.author_id == "U123"
        assert message.id.startswith("msg_")
        assert message in backend._data.mock_messages["C123"]

    def test_add_mock_message_data_with_custom_id(self, backend):
        """Test adding a mock message with a custom ID."""
        message = backend.add_mock_message_data(
            channel_id="C123",
            content="Hello",
            author_id="U123",
            message_id="custom_id_123",
        )

        assert message.id == "custom_id_123"

    def test_add_mock_message_data_with_timestamp(self, backend):
        """Test adding a mock message with a custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        message = backend.add_mock_message_data(
            channel_id="C123",
            content="Hello",
            author_id="U123",
            timestamp=custom_time,
        )

        assert message.timestamp == custom_time

    def test_set_mock_presence_data(self, backend):
        """Test setting mock presence."""
        presence = backend.set_mock_presence_data(
            user_id="U123",
            status=PresenceStatus.ONLINE,
            status_text="Working",
        )

        assert presence.status == PresenceStatus.ONLINE
        assert presence.status_text == "Working"
        assert backend._data.mock_presence["U123"] == presence
        # Presence update should be tracked
        assert len(backend._data.presence_updates) == 1

    def test_reset_mock_data(self, backend):
        """Test resetting all mock data."""
        # Add some data
        backend.add_mock_user_data(id="123", name="Test")
        backend.add_mock_channel_data(id="C123", name="general")

        # Reset
        backend.reset_mock_data()

        assert backend._data.mock_users == {}
        assert backend._data.mock_channels == {}

    def test_sent_messages_data_property(self, backend):
        """Test sent_messages_data property."""
        msg = Message(id="msg1", content="Test")
        backend._data.sent_messages.append(msg)

        assert backend.sent_messages_data == [msg]

    def test_deleted_messages_data_property(self, backend):
        """Test deleted_messages_data property."""
        deleted = {"message_id": "msg1", "channel_id": "C123"}
        backend._data.deleted_messages.append(deleted)

        assert backend.deleted_messages_data == [deleted]

    def test_reactions_added_data_property(self, backend):
        """Test reactions_added_data property."""
        reaction = {"message_id": "msg1", "emoji": "thumbsup"}
        backend._data.reactions_added.append(reaction)

        assert backend.reactions_added_data == [reaction]

    def test_reactions_removed_data_property(self, backend):
        """Test reactions_removed_data property."""
        reaction = {"message_id": "msg1", "emoji": "thumbsup"}
        backend._data.reactions_removed.append(reaction)

        assert backend.reactions_removed_data == [reaction]

    def test_presence_updates_data_property(self, backend):
        """Test presence_updates_data property."""
        update = {"status": "online", "status_text": "Working"}
        backend._data.presence_updates.append(update)

        assert backend.presence_updates_data == [update]


class TestMockBackendMixinAsyncMethods:
    """Tests for async methods in MockBackendMixin."""

    @pytest.fixture
    def backend(self):
        """Create a MockBackendUsingMixin instance."""
        return MockBackendUsingMixin()

    @pytest.mark.asyncio
    async def test_mock_connect(self, backend):
        """Test mock connect sets connected to True."""
        assert backend.connected is False
        await backend._mock_connect()
        assert backend.connected is True

    @pytest.mark.asyncio
    async def test_mock_disconnect(self, backend):
        """Test mock disconnect sets connected to False."""
        backend.connected = True
        await backend._mock_disconnect()
        assert backend.connected is False

    @pytest.mark.asyncio
    async def test_mock_fetch_user(self, backend):
        """Test fetching a mock user."""
        backend.add_mock_user_data(id="123", name="Test User")

        user = await backend._mock_fetch_user("123")
        assert user is not None
        assert user.id == "123"

        # Non-existent user
        user2 = await backend._mock_fetch_user("nonexistent")
        assert user2 is None

    @pytest.mark.asyncio
    async def test_mock_fetch_channel(self, backend):
        """Test fetching a mock channel."""
        backend.add_mock_channel_data(id="C123", name="general")

        channel = await backend._mock_fetch_channel("C123")
        assert channel is not None
        assert channel.id == "C123"

        # Non-existent channel
        channel2 = await backend._mock_fetch_channel("nonexistent")
        assert channel2 is None

    @pytest.mark.asyncio
    async def test_mock_fetch_messages(self, backend):
        """Test fetching mock messages."""
        backend.add_mock_channel_data(id="C123", name="general")
        backend.add_mock_message_data(channel_id="C123", content="Message 1", author_id="U123")
        backend.add_mock_message_data(channel_id="C123", content="Message 2", author_id="U123")
        backend.add_mock_message_data(channel_id="C123", content="Message 3", author_id="U123")

        messages = await backend._mock_fetch_messages("C123")
        assert len(messages) == 3

        # Test limit
        limited = await backend._mock_fetch_messages("C123", limit=2)
        assert len(limited) == 2

    @pytest.mark.asyncio
    async def test_mock_send_message(self, backend):
        """Test sending a mock message."""
        message = await backend._mock_send_message("C123", "Hello world!")

        assert message.content == "Hello world!"
        assert message.channel_id == "C123"
        assert message in backend._data.sent_messages
        assert message in backend._data.mock_messages["C123"]

    @pytest.mark.asyncio
    async def test_mock_delete_message(self, backend):
        """Test deleting a mock message."""
        backend.add_mock_channel_data(id="C123", name="general")
        msg = backend.add_mock_message_data(channel_id="C123", content="To be deleted", author_id="U123")

        await backend._mock_delete_message("C123", msg.id)

        assert {"channel_id": "C123", "message_id": msg.id} in backend._data.deleted_messages
        # Message should be removed from channel
        assert msg not in backend._data.mock_messages["C123"]

    @pytest.mark.asyncio
    async def test_mock_add_reaction(self, backend):
        """Test adding a mock reaction."""
        await backend._mock_add_reaction("C123", "msg1", ":thumbsup:")

        assert len(backend._data.reactions_added) == 1
        assert backend._data.reactions_added[0]["emoji"] == "thumbsup"
        assert backend._data.reactions_added[0]["message_id"] == "msg1"

    @pytest.mark.asyncio
    async def test_mock_remove_reaction(self, backend):
        """Test removing a mock reaction."""
        await backend._mock_remove_reaction("C123", "msg1", ":thumbsup:")

        assert len(backend._data.reactions_removed) == 1
        assert backend._data.reactions_removed[0]["emoji"] == "thumbsup"

    @pytest.mark.asyncio
    async def test_mock_set_presence(self, backend):
        """Test setting mock presence."""
        await backend._mock_set_presence("online", status_text="Working", extra_field="value")

        assert len(backend._data.presence_updates) == 1
        update = backend._data.presence_updates[0]
        assert update["status"] == "online"
        assert update["status_text"] == "Working"
        assert update["extra_field"] == "value"

    @pytest.mark.asyncio
    async def test_mock_get_presence(self, backend):
        """Test getting mock presence."""
        backend.set_mock_presence_data(user_id="U123", status=PresenceStatus.ONLINE)

        presence = await backend._mock_get_presence("U123")
        assert presence is not None
        assert presence.status == PresenceStatus.ONLINE

        # Non-existent user
        presence2 = await backend._mock_get_presence("nonexistent")
        assert presence2 is None
