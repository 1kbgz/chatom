"""Tests for Connection and Registry classes."""

import pytest

from chatom import (
    Channel,
    ChannelRegistry,
    LookupError,
    User,
    UserRegistry,
)


class TestUserRegistry:
    """Tests for UserRegistry."""

    def test_add_and_get_by_id(self):
        """Test adding a user and retrieving by ID."""
        registry = UserRegistry()
        user = User(id="123", name="John Doe", email="john@example.com")
        registry.add(user)

        result = registry.get_by_id("123")
        assert result is not None
        assert result.id == "123"
        assert result.name == "John Doe"

    def test_get_by_name(self):
        """Test retrieving by name."""
        registry = UserRegistry()
        user = User(id="123", name="John Doe")
        registry.add(user)

        result = registry.get_by_name("John Doe")
        assert result is not None
        assert result.id == "123"

    def test_get_by_email(self):
        """Test retrieving by email."""
        registry = UserRegistry()
        user = User(id="123", name="John", email="john@example.com")
        registry.add(user)

        result = registry.get_by_email("john@example.com")
        assert result is not None
        assert result.id == "123"

    def test_get_by_email_case_insensitive(self):
        """Test email lookup is case-insensitive."""
        registry = UserRegistry()
        user = User(id="123", name="John", email="John@Example.com")
        registry.add(user)

        result = registry.get_by_email("JOHN@EXAMPLE.COM")
        assert result is not None
        assert result.id == "123"

    def test_get_by_handle(self):
        """Test retrieving by handle."""
        registry = UserRegistry()
        user = User(id="123", name="John", handle="johndoe")
        registry.add(user)

        result = registry.get_by_handle("johndoe")
        assert result is not None
        assert result.id == "123"

    def test_lookup_by_any(self):
        """Test lookup finds user by any identifier."""
        registry = UserRegistry()
        user = User(id="123", name="John", email="john@example.com", handle="jdoe")
        registry.add(user)

        assert registry.lookup(id="123") is not None
        assert registry.lookup(name="John") is not None
        assert registry.lookup(email="john@example.com") is not None
        assert registry.lookup(handle="jdoe") is not None

    def test_lookup_not_found(self):
        """Test lookup returns None when not found."""
        registry = UserRegistry()
        assert registry.lookup(id="999") is None
        assert registry.lookup(email="notfound@example.com") is None

    def test_user_to_id(self):
        """Test user_to_id returns the user's ID."""
        registry = UserRegistry()
        user = User(id="123", name="John")
        assert registry.user_to_id(user) == "123"

    def test_user_to_id_raises_on_missing(self):
        """Test user_to_id raises when user has no ID."""
        registry = UserRegistry()
        user = User(name="John")
        with pytest.raises(LookupError):
            registry.user_to_id(user)

    def test_user_to_name(self):
        """Test user_to_name returns display name."""
        registry = UserRegistry()
        user = User(id="123", name="John Doe")
        assert registry.user_to_name(user) == "John Doe"

    def test_user_to_email(self):
        """Test user_to_email returns email or None."""
        registry = UserRegistry()
        user_with_email = User(id="1", name="John", email="john@example.com")
        user_without_email = User(id="2", name="Jane")

        assert registry.user_to_email(user_with_email) == "john@example.com"
        assert registry.user_to_email(user_without_email) is None

    def test_id_to_user(self):
        """Test id_to_user returns the user."""
        registry = UserRegistry()
        user = User(id="123", name="John")
        registry.add(user)

        result = registry.id_to_user("123")
        assert result.name == "John"

    def test_id_to_user_raises_on_not_found(self):
        """Test id_to_user raises when not found."""
        registry = UserRegistry()
        with pytest.raises(LookupError):
            registry.id_to_user("999")

    def test_name_to_user(self):
        """Test name_to_user returns the user."""
        registry = UserRegistry()
        user = User(id="123", name="John")
        registry.add(user)

        result = registry.name_to_user("John")
        assert result.id == "123"

    def test_email_to_user(self):
        """Test email_to_user returns the user."""
        registry = UserRegistry()
        user = User(id="123", name="John", email="john@example.com")
        registry.add(user)

        result = registry.email_to_user("john@example.com")
        assert result.id == "123"

    def test_all(self):
        """Test all returns all users."""
        registry = UserRegistry()
        user1 = User(id="1", name="John")
        user2 = User(id="2", name="Jane")
        registry.add(user1)
        registry.add(user2)

        users = registry.all()
        assert len(users) == 2
        assert any(u.name == "John" for u in users)
        assert any(u.name == "Jane" for u in users)

    def test_clear(self):
        """Test clear removes all users."""
        registry = UserRegistry()
        registry.add(User(id="1", name="John", email="john@example.com"))
        registry.clear()

        assert registry.get_by_id("1") is None
        assert registry.get_by_email("john@example.com") is None
        assert len(registry.all()) == 0


class TestChannelRegistry:
    """Tests for ChannelRegistry."""

    def test_add_and_get_by_id(self):
        """Test adding a channel and retrieving by ID."""
        registry = ChannelRegistry()
        channel = Channel(id="C123", name="general")
        registry.add(channel)

        result = registry.get_by_id("C123")
        assert result is not None
        assert result.name == "general"

    def test_get_by_name(self):
        """Test retrieving by name."""
        registry = ChannelRegistry()
        channel = Channel(id="C123", name="general")
        registry.add(channel)

        result = registry.get_by_name("general")
        assert result is not None
        assert result.id == "C123"

    def test_lookup_by_any(self):
        """Test lookup finds channel by any identifier."""
        registry = ChannelRegistry()
        channel = Channel(id="C123", name="general")
        registry.add(channel)

        assert registry.lookup(id="C123") is not None
        assert registry.lookup(name="general") is not None

    def test_channel_to_id(self):
        """Test channel_to_id returns the channel's ID."""
        registry = ChannelRegistry()
        channel = Channel(id="C123", name="general")
        assert registry.channel_to_id(channel) == "C123"

    def test_channel_to_id_raises_on_missing(self):
        """Test channel_to_id raises when channel has no ID."""
        registry = ChannelRegistry()
        channel = Channel(name="general")
        with pytest.raises(LookupError):
            registry.channel_to_id(channel)

    def test_channel_to_name(self):
        """Test channel_to_name returns name or id."""
        registry = ChannelRegistry()
        channel_with_name = Channel(id="C123", name="general")
        channel_without_name = Channel(id="C456")

        assert registry.channel_to_name(channel_with_name) == "general"
        assert registry.channel_to_name(channel_without_name) == "C456"

    def test_id_to_channel(self):
        """Test id_to_channel returns the channel."""
        registry = ChannelRegistry()
        channel = Channel(id="C123", name="general")
        registry.add(channel)

        result = registry.id_to_channel("C123")
        assert result.name == "general"

    def test_id_to_channel_raises_on_not_found(self):
        """Test id_to_channel raises when not found."""
        registry = ChannelRegistry()
        with pytest.raises(LookupError):
            registry.id_to_channel("C999")

    def test_name_to_channel(self):
        """Test name_to_channel returns the channel."""
        registry = ChannelRegistry()
        channel = Channel(id="C123", name="general")
        registry.add(channel)

        result = registry.name_to_channel("general")
        assert result.id == "C123"

    def test_clear(self):
        """Test clear removes all channels."""
        registry = ChannelRegistry()
        registry.add(Channel(id="C123", name="general"))
        registry.clear()

        assert registry.get_by_id("C123") is None
        assert len(registry.all()) == 0


class TestConnection:
    """Tests for Connection base class."""

    def test_connection_has_registries(self):
        """Test that Connection has user and channel registries."""
        # Note: Connection is abstract, but we can test its attributes
        # by using duck typing to check its definition
        from chatom.base.connection import Connection as ConnectionClass

        # Check that Connection has the expected fields
        assert hasattr(ConnectionClass, "model_fields")
        assert "users" in ConnectionClass.model_fields
        assert "channels" in ConnectionClass.model_fields
        assert "backend" in ConnectionClass.model_fields
        assert "connected" in ConnectionClass.model_fields

    def test_connection_repr(self):
        """Test Connection repr."""
        from chatom.base.connection import Connection

        # We can instantiate with required fields for testing
        class TestConnection(Connection):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                return None

        conn = TestConnection(backend="test", connected=True)
        assert "test" in repr(conn)
        assert "True" in repr(conn)


class TestRegistryEdgeCases:
    """Edge case tests for Registry, UserRegistry, and ChannelRegistry."""

    def test_user_registry_id_to_user_not_found(self):
        """Test id_to_user raises LookupError when not found."""
        from chatom.base.connection import UserRegistry

        registry = UserRegistry()
        with pytest.raises(LookupError, match="User not found with ID"):
            registry.id_to_user("nonexistent")

    def test_user_registry_name_to_user_not_found(self):
        """Test name_to_user raises LookupError when not found."""
        from chatom.base.connection import UserRegistry

        registry = UserRegistry()
        with pytest.raises(LookupError, match="User not found with name"):
            registry.name_to_user("nonexistent")

    def test_user_registry_email_to_user_not_found(self):
        """Test email_to_user raises LookupError when not found."""
        from chatom.base.connection import UserRegistry

        registry = UserRegistry()
        with pytest.raises(LookupError, match="User not found with email"):
            registry.email_to_user("nonexistent@example.com")

    def test_channel_registry_id_to_channel_not_found(self):
        """Test id_to_channel raises LookupError when not found."""
        from chatom.base.connection import ChannelRegistry

        registry = ChannelRegistry()
        with pytest.raises(LookupError, match="Channel not found with ID"):
            registry.id_to_channel("nonexistent")

    def test_channel_registry_name_to_channel_not_found(self):
        """Test name_to_channel raises LookupError when not found."""
        from chatom.base.connection import ChannelRegistry

        registry = ChannelRegistry()
        with pytest.raises(LookupError, match="Channel not found with name"):
            registry.name_to_channel("nonexistent")


class TestConnectionGetMethods:
    """Tests for Connection.get_user and get_channel methods."""

    @pytest.mark.asyncio
    async def test_get_user_from_backend(self):
        """Test get_user fetches from backend when not in registry."""
        from chatom.base import User
        from chatom.base.connection import Connection

        class TestConnection(Connection):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                if id == "user123":
                    return User(id=id, name="Fetched User")
                return None

            async def fetch_channel(self, id):
                return None

        conn = TestConnection(backend="test")
        user = await conn.get_user(id="user123")
        assert user is not None
        assert user.name == "Fetched User"
        # Should be added to cache
        cached = conn.users.get_by_id("user123")
        assert cached is not None

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """Test get_user returns None when not found."""
        from chatom.base.connection import Connection

        class TestConnection(Connection):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                return None

        conn = TestConnection(backend="test")
        user = await conn.get_user(id="nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_channel_from_backend(self):
        """Test get_channel fetches from backend when not in registry."""
        from chatom.base import Channel
        from chatom.base.connection import Connection

        class TestConnection(Connection):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                if id == "chan123":
                    return Channel(id=id, name="Fetched Channel")
                return None

        conn = TestConnection(backend="test")
        channel = await conn.get_channel(id="chan123")
        assert channel is not None
        assert channel.name == "Fetched Channel"
        # Should be added to cache
        cached = conn.channels.get_by_id("chan123")
        assert cached is not None

    @pytest.mark.asyncio
    async def test_get_channel_not_found(self):
        """Test get_channel returns None when not found."""
        from chatom.base.connection import Connection

        class TestConnection(Connection):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                return None

        conn = TestConnection(backend="test")
        channel = await conn.get_channel(id="nonexistent")
        assert channel is None

    @pytest.mark.asyncio
    async def test_get_user_from_cache(self):
        """Test get_user returns from cache without fetching."""
        from chatom.base import User
        from chatom.base.connection import Connection

        class TestConnection(Connection):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                raise RuntimeError("Should not fetch from backend")

            async def fetch_channel(self, id):
                return None

        conn = TestConnection(backend="test")
        # Pre-populate cache
        conn.users.add(User(id="cached123", name="Cached User"))

        user = await conn.get_user(id="cached123")
        assert user is not None
        assert user.name == "Cached User"

    @pytest.mark.asyncio
    async def test_get_channel_from_cache(self):
        """Test get_channel returns from cache without fetching."""
        from chatom.base import Channel
        from chatom.base.connection import Connection

        class TestConnection(Connection):
            async def connect(self):
                pass

            async def disconnect(self):
                pass

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                raise RuntimeError("Should not fetch from backend")

        conn = TestConnection(backend="test")
        # Pre-populate cache
        conn.channels.add(Channel(id="cached123", name="Cached Channel"))

        channel = await conn.get_channel(id="cached123")
        assert channel is not None
        assert channel.name == "Cached Channel"
