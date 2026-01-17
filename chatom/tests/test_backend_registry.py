"""Tests for backend registry and backend base class."""

from typing import ClassVar

import pytest

from chatom import (
    BackendBase,
    BackendRegistry,
    Channel,
    Message,
    User,
    get_backend,
    get_backend_format,
    list_backends,
    register_backend,
)
from chatom.format import Format


class TestBackendBase:
    """Tests for BackendBase class."""

    def test_backend_base_has_required_attributes(self):
        """Test that BackendBase has all required class attributes."""
        assert hasattr(BackendBase, "name")
        assert hasattr(BackendBase, "display_name")
        assert hasattr(BackendBase, "format")

    def test_backend_base_default_values(self):
        """Test BackendBase default instance values."""

        # Create a concrete subclass for testing
        class TestBackend(BackendBase):
            name: ClassVar[str] = "test"
            display_name: ClassVar[str] = "Test Backend"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        backend = TestBackend()
        assert backend.connected is False
        assert backend.users is not None
        assert backend.channels is not None

    def test_backend_get_format(self):
        """Test get_format method returns class format."""

        class TestBackend(BackendBase):
            name: ClassVar[str] = "test_format"
            format: ClassVar[Format] = Format.SLACK_MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        backend = TestBackend()
        assert backend.get_format() == Format.SLACK_MARKDOWN


class TestSyncHelper:
    """Tests for the SyncHelper class."""

    def test_sync_helper_exists(self):
        """Test that backends have a sync attribute."""

        class TestBackend(BackendBase):
            name: ClassVar[str] = "test_sync"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return User(id=id, name=f"User {id}")

            async def fetch_channel(self, id: str):
                return Channel(id=id, name=f"Channel {id}")

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        backend = TestBackend()
        assert hasattr(backend, "sync")
        assert backend.sync is not None

    def test_sync_connect(self):
        """Test sync helper connect method."""

        class TestBackend(BackendBase):
            name: ClassVar[str] = "test_sync_connect"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        backend = TestBackend()
        assert backend.connected is False
        backend.sync.connect()
        assert backend.connected is True

    def test_sync_disconnect(self):
        """Test sync helper disconnect method."""

        class TestBackend(BackendBase):
            name: ClassVar[str] = "test_sync_disconnect"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        backend = TestBackend()
        backend.sync.connect()
        assert backend.connected is True
        backend.sync.disconnect()
        assert backend.connected is False

    def test_sync_lookup_user(self):
        """Test sync helper lookup_user method."""

        class TestBackend(BackendBase):
            name: ClassVar[str] = "test_sync_lookup"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str = None, name: str = None, email: str = None, handle: str = None):
                if id:
                    return User(id=id, name=f"User {id}")
                return None

            async def fetch_channel(self, id: str = None, name: str = None):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        backend = TestBackend()
        user = backend.sync.lookup_user(id="123")
        assert user is not None
        assert user.id == "123"
        assert user.name == "User 123"


class TestBackendRegistry:
    """Tests for BackendRegistry class."""

    def test_register_backend_decorator(self):
        """Test registering a backend with decorator."""

        @register_backend
        class CustomBackend(BackendBase):
            name: ClassVar[str] = "custom_test"
            display_name: ClassVar[str] = "Custom Test"
            format: ClassVar[Format] = Format.HTML

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        # Should be able to get the backend
        retrieved = BackendRegistry.get("custom_test")
        assert retrieved is CustomBackend

    def test_register_backend_with_name(self):
        """Test registering a backend with explicit name."""

        @register_backend(name="my_custom_backend")
        class AnotherBackend(BackendBase):
            name: ClassVar[str] = "another"
            format: ClassVar[Format] = Format.PLAINTEXT

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        retrieved = BackendRegistry.get("my_custom_backend")
        assert retrieved is AnotherBackend

    def test_get_nonexistent_backend_raises_error(self):
        """Test that getting a non-existent backend raises KeyError."""
        with pytest.raises(KeyError):
            BackendRegistry.get("nonexistent_backend_12345")

    def test_get_format_for_registered_backend(self):
        """Test getting format for a registered backend."""

        @register_backend
        class FormatTestBackend(BackendBase):
            name: ClassVar[str] = "format_test"
            format: ClassVar[Format] = Format.SYMPHONY_MESSAGEML

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        format_val = BackendRegistry.get_format("format_test")
        assert format_val == Format.SYMPHONY_MESSAGEML

    def test_list_backends(self):
        """Test listing all registered backends."""
        backends = BackendRegistry.list()
        assert isinstance(backends, list)
        # Should include our test backends
        assert "custom_test" in backends or "format_test" in backends

    def test_get_instance_creates_backend(self):
        """Test get_instance creates and caches a backend."""

        @register_backend
        class InstanceTestBackend(BackendBase):
            name: ClassVar[str] = "instance_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        instance1 = BackendRegistry.get_instance("instance_test")
        instance2 = BackendRegistry.get_instance("instance_test")
        assert instance1 is instance2  # Same instance returned


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_backend_function(self):
        """Test get_backend convenience function."""

        @register_backend
        class ConvenienceTestBackend(BackendBase):
            name: ClassVar[str] = "convenience_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        backend_class = get_backend("convenience_test")
        assert backend_class is ConvenienceTestBackend

    def test_get_backend_format_function(self):
        """Test get_backend_format convenience function."""

        @register_backend
        class FormatConvenienceBackend(BackendBase):
            name: ClassVar[str] = "format_convenience"
            format: ClassVar[Format] = Format.DISCORD_MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="1", content=content)

        format_val = get_backend_format("format_convenience")
        assert format_val == Format.DISCORD_MARKDOWN

    def test_list_backends_function(self):
        """Test list_backends convenience function."""
        backends = list_backends()
        assert isinstance(backends, list)


class TestBuiltinBackends:
    """Tests for the built-in backend implementations."""

    def test_discord_backend_exists(self):
        """Test Discord backend can be imported."""
        from chatom.discord import DiscordBackend

        assert DiscordBackend.name == "discord"
        assert DiscordBackend.format == Format.DISCORD_MARKDOWN

    def test_slack_backend_exists(self):
        """Test Slack backend can be imported."""
        from chatom.slack import SlackBackend

        assert SlackBackend.name == "slack"
        assert SlackBackend.format == Format.SLACK_MARKDOWN

    def test_symphony_backend_exists(self):
        """Test Symphony backend can be imported."""
        from chatom.symphony import SymphonyBackend

        assert SymphonyBackend.name == "symphony"
        assert SymphonyBackend.format == Format.SYMPHONY_MESSAGEML

    def test_matrix_backend_exists(self):
        """Test Matrix backend can be imported."""
        from chatom.matrix import MatrixBackend

        assert MatrixBackend.name == "matrix"
        assert MatrixBackend.format == Format.HTML

    def test_irc_backend_exists(self):
        """Test IRC backend can be imported."""
        from chatom.irc import IRCBackend

        assert IRCBackend.name == "irc"
        assert IRCBackend.format == Format.PLAINTEXT

    def test_email_backend_exists(self):
        """Test Email backend can be imported."""
        from chatom.email import EmailBackend

        assert EmailBackend.name == "email"
        assert EmailBackend.format == Format.HTML

    @pytest.mark.asyncio
    async def test_discord_backend_connect(self):
        """Test Discord backend connect/disconnect with mock."""
        from chatom.discord import DiscordConfig, MockDiscordBackend

        config = DiscordConfig(bot_token="test-token")
        backend = MockDiscordBackend(config=config)
        assert backend.connected is False
        await backend.connect()
        assert backend.connected is True
        await backend.disconnect()
        assert backend.connected is False

    @pytest.mark.asyncio
    async def test_slack_backend_connect(self):
        """Test Slack backend connect/disconnect with mock."""
        from chatom.slack import MockSlackBackend, SlackConfig

        config = SlackConfig(bot_token="xoxb-test-token")
        backend = MockSlackBackend(config=config)
        assert backend.connected is False
        await backend.connect()
        assert backend.connected is True
        await backend.disconnect()
        assert backend.connected is False


class TestBackendMentionMethods:
    """Tests for backend mention methods."""

    def test_discord_mention_user(self):
        """Test Discord backend mention_user method."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend()
        user = User(id="123456789", name="TestUser")
        mention = backend.mention_user(user)
        assert mention == "<@123456789>"

    def test_discord_mention_channel(self):
        """Test Discord backend mention_channel method."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend()
        channel = Channel(id="987654321", name="general")
        mention = backend.mention_channel(channel)
        assert mention == "<#987654321>"

    def test_slack_mention_user(self):
        """Test Slack backend mention_user method."""
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        user = User(id="U123456", name="TestUser")
        mention = backend.mention_user(user)
        assert mention == "<@U123456>"

    def test_slack_mention_channel(self):
        """Test Slack backend mention_channel method."""
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        channel = Channel(id="C789012", name="general")
        mention = backend.mention_channel(channel)
        assert mention == "<#C789012>"

    def test_matrix_mention_user(self):
        """Test Matrix backend mention_user method."""
        from chatom.matrix import MatrixBackend

        backend = MatrixBackend()
        user = User(id="@alice:matrix.org", name="Alice")
        mention = backend.mention_user(user)
        assert mention == "@alice:matrix.org"

    def test_irc_mention_user(self):
        """Test IRC backend mention_user method."""
        from chatom.irc import IRCBackend

        backend = IRCBackend()
        user = User(id="alice", name="alice")
        mention = backend.mention_user(user)
        assert mention == "alice"

    def test_email_mention_user(self):
        """Test Email backend mention_user method."""
        from chatom.email import EmailBackend

        backend = EmailBackend()
        user = User(id="alice@example.com", name="Alice", email="alice@example.com")
        mention = backend.mention_user(user)
        assert "mailto:" in mention
        assert "alice@example.com" in mention


class TestBackendLookupMethods:
    """Tests for backend lookup methods."""

    def test_lookup_user_from_cache(self):
        """Test looking up a user from cache."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend()
        user = User(id="123", name="TestUser", email="test@example.com")
        backend.users.add(user)

        found = backend.sync.lookup_user(id="123")
        assert found is not None
        assert found.id == "123"
        assert found.name == "TestUser"

    def test_lookup_channel_from_cache(self):
        """Test looking up a channel from cache."""
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        channel = Channel(id="C123", name="general")
        backend.channels.add(channel)

        found = backend.sync.lookup_channel(id="C123")
        assert found is not None
        assert found.id == "C123"
        assert found.name == "general"

    def test_lookup_user_not_found(self):
        """Test looking up a non-existent user."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend()
        found = backend.sync.lookup_user(id="nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_lookup_channel_not_found(self):
        """Test looking up a non-existent channel with mock backend."""
        from chatom.slack import MockSlackBackend, SlackConfig

        config = SlackConfig(bot_token="xoxb-test-token")
        backend = MockSlackBackend(config=config)
        await backend.connect()
        found = await backend.lookup_channel(id="nonexistent")
        assert found is None


class TestFetchMessages:
    """Tests for fetch_messages functionality."""

    def test_fetch_messages_abstract_method(self):
        """Test that fetch_messages is defined as abstract in BackendBase."""

        from chatom.backend_registry import BackendBase

        # Verify the method exists
        assert hasattr(BackendBase, "fetch_messages")
        method = getattr(BackendBase, "fetch_messages")
        assert callable(method)

    def test_fetch_messages_signature(self):
        """Test that fetch_messages has the correct signature."""
        import inspect

        from chatom.backend_registry import BackendBase

        sig = inspect.signature(BackendBase.fetch_messages)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "channel_id" in params
        assert "limit" in params
        assert "before" in params
        assert "after" in params

    def test_sync_fetch_messages_exists(self):
        """Test that sync helper can call fetch_messages method dynamically."""
        from chatom.backend_registry import BackendBase, SyncHelper

        # Create a mock backend to test with
        class MockBackend(BackendBase):
            name = "mock"

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                return None

            async def fetch_messages(self, channel_id, limit=100, before=None, after=None):
                return []

            async def send_message(self, channel_id, content, **kwargs):
                return None

        backend = MockBackend()
        sync = SyncHelper(backend)
        # With __getattr__, we can access fetch_messages dynamically
        assert callable(sync.fetch_messages)

    def test_irc_fetch_messages_returns_empty_list(self):
        """Test that IRC fetch_messages returns empty list (no history)."""
        from chatom.irc import IRCBackend

        backend = IRCBackend()
        messages = backend.sync.fetch_messages("##general")
        assert messages == []

    @pytest.mark.asyncio
    async def test_discord_fetch_messages_requires_connection(self):
        """Test that Discord fetch_messages requires connection."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend()
        with pytest.raises(RuntimeError):  # Not connected
            await backend.fetch_messages("123456789")

    @pytest.mark.asyncio
    async def test_slack_fetch_messages_requires_connection(self):
        """Test that Slack fetch_messages requires connection."""
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        with pytest.raises(ConnectionError):  # Not connected
            await backend.fetch_messages("C123456")

    @pytest.mark.asyncio
    async def test_symphony_fetch_messages_requires_connection(self):
        """Test that Symphony fetch_messages requires connection."""
        from chatom.symphony import SymphonyBackend

        backend = SymphonyBackend()
        with pytest.raises(RuntimeError):  # Not connected
            await backend.fetch_messages("stream123")

    @pytest.mark.asyncio
    async def test_matrix_fetch_messages_requires_connection(self):
        """Test that Matrix fetch_messages requires connection."""
        from chatom.matrix import MatrixBackend

        backend = MatrixBackend()
        with pytest.raises(RuntimeError):  # Not connected
            await backend.fetch_messages("!room:matrix.org")

    @pytest.mark.asyncio
    async def test_email_fetch_messages_requires_connection(self):
        """Test that Email fetch_messages requires connection."""
        from chatom.email import EmailBackend

        backend = EmailBackend()
        with pytest.raises(RuntimeError):  # IMAP not connected
            await backend.fetch_messages("INBOX")

    def test_custom_backend_fetch_messages_implementation(self):
        """Test custom backend with implemented fetch_messages."""

        class CustomBackend(BackendBase):
            name: ClassVar[str] = "custom_fetch_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                # Return some test messages
                return [
                    Message(id="1", content="First message"),
                    Message(id="2", content="Second message"),
                ]

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="new", content=content)

        backend = CustomBackend()
        messages = backend.sync.fetch_messages("test-channel")
        assert len(messages) == 2
        assert messages[0].content == "First message"
        assert messages[1].content == "Second message"

    def test_fetch_messages_with_limit(self):
        """Test fetch_messages respects limit parameter."""

        class LimitTestBackend(BackendBase):
            name: ClassVar[str] = "limit_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                # Return up to 'limit' messages
                all_messages = [Message(id=str(i), content=f"Message {i}") for i in range(10)]
                return all_messages[:limit]

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="new", content=content)

        backend = LimitTestBackend()

        # Test with default limit
        messages = backend.sync.fetch_messages("channel")
        assert len(messages) == 10

        # Test with explicit limit
        messages = backend.sync.fetch_messages("channel", limit=5)
        assert len(messages) == 5

    def test_fetch_messages_with_pagination(self):
        """Test fetch_messages with before/after pagination parameters."""

        class PaginationTestBackend(BackendBase):
            name: ClassVar[str] = "pagination_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                messages = [Message(id=str(i), content=f"Message {i}") for i in range(1, 11)]
                if after:
                    messages = [m for m in messages if int(m.id) > int(after)]
                if before:
                    messages = [m for m in messages if int(m.id) < int(before)]
                return messages[:limit]

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="new", content=content)

        backend = PaginationTestBackend()

        # Test after parameter
        messages = backend.sync.fetch_messages("channel", after="5")
        assert len(messages) == 5
        assert all(int(m.id) > 5 for m in messages)

        # Test before parameter
        messages = backend.sync.fetch_messages("channel", before="5")
        assert len(messages) == 4
        assert all(int(m.id) < 5 for m in messages)


class TestPresenceMethods:
    """Tests for get_presence and set_presence functionality."""

    def test_get_presence_method_exists(self):
        """Test that get_presence is defined in BackendBase."""
        from chatom.backend_registry import BackendBase

        assert hasattr(BackendBase, "get_presence")
        method = getattr(BackendBase, "get_presence")
        assert callable(method)

    def test_set_presence_method_exists(self):
        """Test that set_presence is defined in BackendBase."""
        from chatom.backend_registry import BackendBase

        assert hasattr(BackendBase, "set_presence")
        method = getattr(BackendBase, "set_presence")
        assert callable(method)

    def test_get_presence_signature(self):
        """Test that get_presence has the correct signature."""
        import inspect

        from chatom.backend_registry import BackendBase

        sig = inspect.signature(BackendBase.get_presence)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "user_id" in params

    def test_set_presence_signature(self):
        """Test that set_presence has the correct signature."""
        import inspect

        from chatom.backend_registry import BackendBase

        sig = inspect.signature(BackendBase.set_presence)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "status" in params
        assert "status_text" in params
        assert "kwargs" in params

    def test_sync_get_presence_exists(self):
        """Test that sync helper can call get_presence method dynamically."""
        from chatom.backend_registry import BackendBase, SyncHelper

        class MockBackend(BackendBase):
            name = "mock"

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                return None

            async def fetch_messages(self, channel_id, limit=100, before=None, after=None):
                return []

            async def send_message(self, channel_id, content, **kwargs):
                return None

            async def get_presence(self, user_id):
                return None

        backend = MockBackend()
        sync = SyncHelper(backend)
        assert callable(sync.get_presence)

    def test_sync_set_presence_exists(self):
        """Test that sync helper can call set_presence method dynamically."""
        from chatom.backend_registry import BackendBase, SyncHelper

        class MockBackend(BackendBase):
            name = "mock"

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                return None

            async def fetch_messages(self, channel_id, limit=100, before=None, after=None):
                return []

            async def send_message(self, channel_id, content, **kwargs):
                return None

            async def set_presence(self, status, status_text=None, **kwargs):
                pass

        backend = MockBackend()
        sync = SyncHelper(backend)
        assert callable(sync.set_presence)

    def test_irc_get_presence_returns_none(self):
        """Test that IRC get_presence returns None (no presence support)."""
        from chatom.irc import IRCBackend

        backend = IRCBackend()
        presence = backend.sync.get_presence("nick")
        assert presence is None

    def test_email_get_presence_returns_none(self):
        """Test that Email get_presence returns None (no presence support)."""
        from chatom.email import EmailBackend

        backend = EmailBackend()
        presence = backend.sync.get_presence("user@example.com")
        assert presence is None

    @pytest.mark.asyncio
    async def test_discord_get_presence_requires_connection(self):
        """Test that Discord get_presence requires connection or returns cached presence."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend()
        # Discord get_presence may return cached presence or require connection
        # It doesn't raise NotImplementedError anymore
        result = await backend.get_presence("123456789")
        # Should return None or a cached presence (no exception expected)
        assert result is None or hasattr(result, "status")

    @pytest.mark.asyncio
    async def test_slack_get_presence_requires_connection(self):
        """Test that Slack get_presence requires connection."""
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        with pytest.raises(ConnectionError):  # Not connected
            await backend.get_presence("U123456")

    @pytest.mark.asyncio
    async def test_symphony_get_presence_requires_connection(self):
        """Test that Symphony get_presence requires connection or returns default."""
        from chatom.symphony import SymphonyBackend

        backend = SymphonyBackend()
        # Symphony returns default presence when not connected
        result = await backend.get_presence("12345")
        assert result is None or hasattr(result, "status")

    @pytest.mark.asyncio
    async def test_matrix_get_presence_requires_connection(self):
        """Test that Matrix get_presence requires connection or returns None."""
        from chatom.matrix import MatrixBackend

        backend = MatrixBackend()
        # Matrix returns None when not connected
        result = await backend.get_presence("@user:matrix.org")
        assert result is None

    @pytest.mark.asyncio
    async def test_discord_set_presence_requires_connection(self):
        """Test that Discord set_presence requires connection."""
        from chatom.discord import DiscordBackend

        backend = DiscordBackend()
        with pytest.raises(RuntimeError):  # Not connected
            await backend.set_presence("online")

    @pytest.mark.asyncio
    async def test_slack_set_presence_requires_connection(self):
        """Test that Slack set_presence requires connection."""
        from chatom.slack import SlackBackend

        backend = SlackBackend()
        with pytest.raises(ConnectionError):  # Not connected
            await backend.set_presence("auto")

    @pytest.mark.asyncio
    async def test_symphony_set_presence_requires_connection(self):
        """Test that Symphony set_presence requires connection."""
        from chatom.symphony import SymphonyBackend

        backend = SymphonyBackend()
        with pytest.raises(RuntimeError):  # Not connected
            await backend.set_presence("AVAILABLE")

    @pytest.mark.asyncio
    async def test_matrix_set_presence_requires_connection(self):
        """Test that Matrix set_presence requires connection."""
        from chatom.matrix import MatrixBackend

        backend = MatrixBackend()
        with pytest.raises(RuntimeError):  # Not connected
            await backend.set_presence("online")

    @pytest.mark.asyncio
    async def test_irc_set_presence_requires_connection(self):
        """Test that IRC set_presence requires connection."""
        from chatom.irc import IRCBackend

        backend = IRCBackend()
        with pytest.raises(RuntimeError):  # Not connected
            await backend.set_presence("away", "Gone fishing")

    @pytest.mark.asyncio
    async def test_email_set_presence_raises_not_implemented(self):
        """Test that Email set_presence raises NotImplementedError."""
        from chatom.email import EmailBackend

        backend = EmailBackend()
        with pytest.raises(NotImplementedError):
            await backend.set_presence("available")

    def test_custom_backend_get_presence_implementation(self):
        """Test custom backend with implemented get_presence."""
        from chatom.base import Presence, PresenceStatus

        class CustomPresenceBackend(BackendBase):
            name: ClassVar[str] = "custom_presence_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return User(id=id, name=f"User {id}")

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="new", content=content)

            async def get_presence(self, user_id: str):
                return Presence(
                    status=PresenceStatus.ONLINE,
                    status_text="Working",
                )

            async def set_presence(self, status: str, status_text: str = None, **kwargs):
                pass  # No-op for test

        backend = CustomPresenceBackend()
        presence = backend.sync.get_presence("user123")
        assert presence is not None
        assert presence.status == PresenceStatus.ONLINE
        assert presence.status_text == "Working"

    def test_custom_backend_set_presence_implementation(self):
        """Test custom backend with implemented set_presence."""
        from chatom.base import Presence, PresenceStatus

        class StatefulPresenceBackend(BackendBase):
            name: ClassVar[str] = "stateful_presence_test"
            format: ClassVar[Format] = Format.MARKDOWN
            _current_status: str = "offline"
            _current_status_text: str = ""

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="new", content=content)

            async def get_presence(self, user_id: str):
                status_map = {
                    "online": PresenceStatus.ONLINE,
                    "away": PresenceStatus.IDLE,
                    "dnd": PresenceStatus.DND,
                    "offline": PresenceStatus.OFFLINE,
                }
                return Presence(
                    status=status_map.get(self._current_status, PresenceStatus.UNKNOWN),
                    status_text=self._current_status_text,
                )

            async def set_presence(self, status: str, status_text: str = None, **kwargs):
                self._current_status = status
                self._current_status_text = status_text or ""

        backend = StatefulPresenceBackend()

        # Initially offline
        presence = backend.sync.get_presence("me")
        assert presence.status == PresenceStatus.OFFLINE

        # Set to online
        backend.sync.set_presence("online", "Available")
        presence = backend.sync.get_presence("me")
        assert presence.status == PresenceStatus.ONLINE
        assert presence.status_text == "Available"

        # Set to away
        backend.sync.set_presence("away", "In a meeting")
        presence = backend.sync.get_presence("me")
        assert presence.status == PresenceStatus.IDLE
        assert presence.status_text == "In a meeting"

        # Set to DND
        backend.sync.set_presence("dnd")
        presence = backend.sync.get_presence("me")
        assert presence.status == PresenceStatus.DND


class TestReplyInThread:
    """Tests for reply_in_thread method."""

    @pytest.mark.asyncio
    async def test_reply_in_thread_uses_thread_id(self):
        """Test reply_in_thread uses existing thread_id."""

        class ThreadBackend(BackendBase):
            name: ClassVar[str] = "thread_test"
            format: ClassVar[Format] = Format.MARKDOWN
            last_thread_id: str = None

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, thread_id: str = None, **kwargs):
                self.last_thread_id = thread_id
                return Message(id="reply", content=content, thread_id=thread_id)

        backend = ThreadBackend()
        msg = Message(id="msg1", content="Hello", channel_id="chan1", thread_id="thread123")
        reply = await backend.reply_in_thread(msg, "Reply content")

        assert backend.last_thread_id == "thread123"
        assert reply.content == "Reply content"

    @pytest.mark.asyncio
    async def test_reply_in_thread_starts_new_thread(self):
        """Test reply_in_thread starts new thread when message has no thread_id."""

        class ThreadBackend(BackendBase):
            name: ClassVar[str] = "thread_test2"
            format: ClassVar[Format] = Format.MARKDOWN
            last_thread_id: str = None

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, thread_id: str = None, **kwargs):
                self.last_thread_id = thread_id
                return Message(id="reply", content=content, thread_id=thread_id)

        backend = ThreadBackend()
        msg = Message(id="msg1", content="Hello", channel_id="chan1")
        _ = await backend.reply_in_thread(msg, "Reply content")

        # When no thread_id, uses message id as thread_id
        assert backend.last_thread_id == "msg1"

    @pytest.mark.asyncio
    async def test_reply_in_thread_no_channel_raises(self):
        """Test reply_in_thread raises when message has no channel info."""

        class ThreadBackend(BackendBase):
            name: ClassVar[str] = "thread_test3"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="reply", content=content)

        backend = ThreadBackend()
        msg = Message(id="msg1", content="Hello")  # No channel_id

        with pytest.raises(ValueError, match="Cannot reply"):
            await backend.reply_in_thread(msg, "Reply content")


class TestSyncHelperMethods:
    """Tests for SyncHelper wrapper methods."""

    def test_sync_helper_close(self):
        """Test SyncHelper close method."""

        class BasicBackend(BackendBase):
            name: ClassVar[str] = "close_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

        backend = BasicBackend()
        sync = backend.sync

        # Run something to initialize the loop
        sync.connect()
        sync.disconnect()

        # Close should clean up resources
        sync.close()
        assert sync._executor is None
        assert sync._loop is None or sync._loop.is_closed()

    def test_sync_helper_send_action(self):
        """Test SyncHelper send_action method."""

        class ActionBackend(BackendBase):
            name: ClassVar[str] = "action_test"
            format: ClassVar[Format] = Format.MARKDOWN
            action_sent: bool = False

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

            async def send_action(self, target: str, action: str):
                self.action_sent = True

        backend = ActionBackend()
        backend.sync.send_action("#channel", "waves")
        assert backend.action_sent

    def test_sync_helper_send_notice(self):
        """Test SyncHelper send_notice method."""

        class NoticeBackend(BackendBase):
            name: ClassVar[str] = "notice_test"
            format: ClassVar[Format] = Format.MARKDOWN
            notice_sent: bool = False

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

            async def send_notice(self, target: str, text: str):
                self.notice_sent = True

        backend = NoticeBackend()
        backend.sync.send_notice("#channel", "Notice text")
        assert backend.notice_sent

    def test_sync_helper_join_room_alias(self):
        """Test SyncHelper join_room is alias for join_channel."""

        class RoomBackend(BackendBase):
            name: ClassVar[str] = "room_test"
            format: ClassVar[Format] = Format.MARKDOWN
            joined_channel: str = None

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

            async def join_channel(self, channel_id: str, **kwargs):
                self.joined_channel = channel_id

            async def join_room(self, room_id: str, **kwargs):
                return await self.join_channel(room_id, **kwargs)

        backend = RoomBackend()
        backend.sync.join_room("room123")
        assert backend.joined_channel == "room123"

    def test_sync_helper_leave_room_alias(self):
        """Test SyncHelper leave_room is alias for leave_channel."""

        class LeaveBackend(BackendBase):
            name: ClassVar[str] = "leave_test"
            format: ClassVar[Format] = Format.MARKDOWN
            left_channel: str = None

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

            async def leave_channel(self, channel_id: str, **kwargs):
                self.left_channel = channel_id

            async def leave_room(self, room_id: str, **kwargs):
                return await self.leave_channel(room_id, **kwargs)

        backend = LeaveBackend()
        backend.sync.leave_room("room123")
        assert backend.left_channel == "room123"

    def test_sync_helper_create_im_alias(self):
        """Test SyncHelper create_im is alias for create_dm."""

        class DMBackend(BackendBase):
            name: ClassVar[str] = "dm_test"
            format: ClassVar[Format] = Format.MARKDOWN
            dm_user_ids: list = None

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

            async def create_dm(self, user_ids: list):
                self.dm_user_ids = user_ids
                return "dm_channel_123"

            async def create_im(self, user_ids: list):
                return await self.create_dm(user_ids)

        backend = DMBackend()
        result = backend.sync.create_im(["user1", "user2"])
        assert result == "dm_channel_123"
        assert backend.dm_user_ids == ["user1", "user2"]

    def test_sync_helper_create_room_alias(self):
        """Test SyncHelper create_room is alias for create_channel."""

        class CreateBackend(BackendBase):
            name: ClassVar[str] = "create_test"
            format: ClassVar[Format] = Format.MARKDOWN
            created_name: str = None

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

            async def create_channel(self, name: str, **kwargs):
                self.created_name = name
                return "new_channel_123"

            async def create_room(self, name: str, **kwargs):
                return await self.create_channel(name, **kwargs)

        backend = CreateBackend()
        result = backend.sync.create_room("new-room")
        assert result == "new_channel_123"
        assert backend.created_name == "new-room"

    def test_sync_helper_fetch_room_alias(self):
        """Test SyncHelper fetch_room is alias for fetch_channel."""

        class FetchBackend(BackendBase):
            name: ClassVar[str] = "fetch_room_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return Channel(id=id, name="test-channel")

            async def fetch_room(self, id: str):
                return await self.fetch_channel(id)

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

        backend = FetchBackend()
        result = backend.sync.fetch_room("room123")
        assert result.id == "room123"
        assert result.name == "test-channel"


class TestBackendBaseRepr:
    """Tests for BackendBase __repr__ method."""

    def test_repr_connected(self):
        """Test __repr__ when connected."""

        class ReprBackend(BackendBase):
            name: ClassVar[str] = "repr_test"
            format: ClassVar[Format] = Format.MARKDOWN

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id: str):
                return None

            async def fetch_channel(self, id: str):
                return None

            async def fetch_messages(self, channel_id: str, limit: int = 100, before=None, after=None):
                return []

            async def send_message(self, channel_id: str, content: str, **kwargs):
                return Message(id="msg", content=content)

        backend = ReprBackend()
        assert "connected=False" in repr(backend)

        backend.connected = True
        assert "connected=True" in repr(backend)
