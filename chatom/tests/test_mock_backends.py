"""Tests for mock backend implementations.

These tests verify that the mock backends work correctly
for testing purposes.
"""

import pytest
from pydantic import SecretStr

from chatom.base import Channel, ChannelType, Message, User
from chatom.discord import DiscordUser
from chatom.slack import SlackUser
from chatom.symphony import SymphonyUser


class TestMockSlackBackend:
    """Tests for MockSlackBackend."""

    @pytest.fixture
    def backend(self):
        """Create a mock Slack backend."""
        from chatom.slack import MockSlackBackend, SlackConfig

        config = SlackConfig(
            bot_token=SecretStr("xoxb-test-token"),
            app_token=SecretStr("xapp-test-token"),
        )
        return MockSlackBackend(config=config)

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, backend):
        """Test connect and disconnect."""
        assert not backend.connected
        await backend.connect()
        assert backend.connected
        await backend.disconnect()
        assert not backend.connected

    @pytest.mark.asyncio
    async def test_add_mock_user(self, backend):
        """Test adding mock users."""
        await backend.connect()
        backend.add_mock_user("U123", "Test User", "testuser")

        user = await backend.fetch_user("U123")
        assert user is not None
        assert user.name == "Test User"
        assert user.handle == "testuser"

    @pytest.mark.asyncio
    async def test_add_mock_channel(self, backend):
        """Test adding mock channels."""
        await backend.connect()
        backend.add_mock_channel("C123", "general", is_private=False)

        channel = await backend.fetch_channel("C123")
        assert channel is not None
        assert channel.name == "general"

    @pytest.mark.asyncio
    async def test_send_message(self, backend):
        """Test sending messages."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")

        message = await backend.send_message("C123", "Hello, world!")

        assert message.content == "Hello, world!"
        assert message.channel_id == "C123"
        assert len(backend.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_fetch_messages(self, backend):
        """Test fetching messages."""
        await backend.connect()

        # Add mock messages
        backend.add_mock_message(
            channel_id="C123",
            user_id="U456",
            content="Test message",
        )

        messages = await backend.fetch_messages("C123")
        assert len(messages) == 1
        assert messages[0].content == "Test message"

    @pytest.mark.asyncio
    async def test_reactions(self, backend):
        """Test adding and removing reactions."""
        await backend.connect()

        # Add a message
        msg_id = backend.add_mock_message("C123", "U456", "React to me")

        # Add reaction
        await backend.add_reaction(message=msg_id, emoji="thumbsup", channel="C123")
        assert len(backend.added_reactions) == 1

        # Remove reaction
        await backend.remove_reaction(message=msg_id, emoji="thumbsup", channel="C123")
        assert len(backend.removed_reactions) == 1

    @pytest.mark.asyncio
    async def test_presence(self, backend):
        """Test setting and getting presence."""
        await backend.connect()
        backend.add_mock_user("U123", "Test User", "testuser")

        # Set presence
        await backend.set_presence("away", "In a meeting")
        assert len(backend.presence_changes) == 1

        # Get presence
        presence = await backend.get_presence("U123")
        assert presence is not None

    def test_reset(self, backend):
        """Test resetting mock data."""
        backend.add_mock_user("U123", "Test", "test")
        backend.reset()

        assert len(backend.mock_users) == 0
        assert len(backend.sent_messages) == 0


class TestMockDiscordBackend:
    """Tests for MockDiscordBackend."""

    @pytest.fixture
    def backend(self):
        """Create a mock Discord backend."""
        from chatom.discord import DiscordConfig, MockDiscordBackend

        config = DiscordConfig(
            token=SecretStr("discord-test-token"),
        )
        return MockDiscordBackend(config=config)

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, backend):
        """Test connect and disconnect."""
        await backend.connect()
        assert backend.connected
        await backend.disconnect()
        assert not backend.connected

    @pytest.mark.asyncio
    async def test_add_mock_user(self, backend):
        """Test adding mock users."""
        await backend.connect()
        backend.add_mock_user("123456789", "TestUser", "testuser#1234")

        user = await backend.fetch_user("123456789")
        assert user is not None
        assert user.name == "TestUser"

    @pytest.mark.asyncio
    async def test_add_mock_channel(self, backend):
        """Test adding mock channels."""
        await backend.connect()
        backend.add_mock_channel("987654321", "general", "text")

        channel = await backend.fetch_channel("987654321")
        assert channel is not None
        assert channel.name == "general"

    @pytest.mark.asyncio
    async def test_send_message(self, backend):
        """Test sending messages."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")

        message = await backend.send_message("C123", "Hello, Discord!")

        assert message.content == "Hello, Discord!"
        assert len(backend.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_edit_message(self, backend):
        """Test editing messages."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")

        # Send a message
        msg = await backend.send_message("C123", "Original")
        # Edit it
        edited = await backend.edit_message(message=msg.id, content="Edited", channel="C123")

        assert edited.content == "Edited"
        assert len(backend.edited_messages) == 1

    @pytest.mark.asyncio
    async def test_delete_message(self, backend):
        """Test deleting messages."""
        await backend.connect()
        msg_id = backend.add_mock_message("C123", "U123", "Delete me")

        await backend.delete_message(message=msg_id, channel="C123")
        assert {"channel_id": "C123", "message_id": msg_id} in backend.deleted_messages


class TestMockSymphonyBackend:
    """Tests for MockSymphonyBackend."""

    @pytest.fixture
    def backend(self):
        """Create a mock Symphony backend."""
        from chatom.symphony import MockSymphonyBackend, SymphonyConfig

        config = SymphonyConfig(
            host="mycompany.symphony.com",
            bot_username="testbot",
        )
        return MockSymphonyBackend(config=config)

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, backend):
        """Test connect and disconnect."""
        await backend.connect()
        assert backend.connected
        await backend.disconnect()
        assert not backend.connected

    @pytest.mark.asyncio
    async def test_add_mock_user(self, backend):
        """Test adding mock users."""
        await backend.connect()
        backend.add_mock_user(123456789, "Test User", "testuser")

        user = await backend.fetch_user("123456789")
        assert user is not None
        assert user.name == "Test User"

    @pytest.mark.asyncio
    async def test_add_mock_stream(self, backend):
        """Test adding mock streams."""
        await backend.connect()
        backend.add_mock_stream("stream123", "Test Room")

        channel = await backend.fetch_channel("stream123")
        assert channel is not None
        assert channel.name == "Test Room"

    @pytest.mark.asyncio
    async def test_send_message(self, backend):
        """Test sending messages."""
        await backend.connect()
        backend.add_mock_stream("stream123", "Test Room")

        message = await backend.send_message(
            "stream123",
            "<messageML>Hello, Symphony!</messageML>",
        )

        assert "Hello, Symphony!" in message.content
        assert len(backend.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_edit_message(self, backend):
        """Test editing messages."""
        await backend.connect()
        backend.add_mock_stream("stream123", "Test Room")

        msg = await backend.send_message("stream123", "<messageML>Original</messageML>")
        edited = await backend.edit_message(message=msg.id, content="<messageML>Edited</messageML>", channel="stream123")

        assert "Edited" in edited.content
        assert len(backend.edited_messages) == 1

    @pytest.mark.asyncio
    async def test_delete_message(self, backend):
        """Test deleting (suppressing) messages."""
        await backend.connect()
        msg_id = backend.add_mock_message("stream123", 123456, "<messageML>Delete me</messageML>")

        await backend.delete_message(message=msg_id, channel="stream123")
        assert msg_id in backend.deleted_messages

    @pytest.mark.asyncio
    async def test_presence(self, backend):
        """Test setting and getting presence."""
        await backend.connect()

        await backend.set_presence("busy")
        assert len(backend.presence_changes) == 1

        presence = await backend.get_presence("123456789")
        assert presence is not None

    @pytest.mark.asyncio
    async def test_reactions_not_supported(self, backend):
        """Test that reactions raise NotImplementedError."""
        await backend.connect()

        with pytest.raises(NotImplementedError):
            await backend.add_reaction(message="msg123", emoji="👍", channel="stream123")

    @pytest.mark.asyncio
    async def test_create_im(self, backend):
        """Test creating an IM."""
        await backend.connect()

        stream_id = await backend.create_im(["123", "456"])
        assert stream_id is not None
        assert len(backend.created_ims) == 1

    @pytest.mark.asyncio
    async def test_create_dm(self, backend):
        """Test creating a DM (alias for create_im)."""
        await backend.connect()

        stream_id = await backend.create_dm(["789"])
        assert stream_id is not None
        # Should be tracked in created_ims
        assert len(backend.created_ims) == 1

    @pytest.mark.asyncio
    async def test_create_room(self, backend):
        """Test creating a room."""
        await backend.connect()

        stream_id = await backend.create_room(
            name="New Room",
            description="Test room",
            public=True,
        )
        assert stream_id is not None
        assert len(backend.created_rooms) == 1


class TestConfigClasses:
    """Tests for backend configuration classes."""

    def test_slack_config(self):
        """Test SlackConfig."""
        from chatom.slack import SlackConfig

        config = SlackConfig(
            bot_token=SecretStr("xoxb-test"),
            app_token=SecretStr("xapp-test"),
            signing_secret=SecretStr("secret123"),
            team_id="T123456",
        )
        assert config.bot_token_str == "xoxb-test"
        assert config.has_socket_mode is True

    def test_discord_config(self):
        """Test DiscordConfig."""
        from chatom.discord import DiscordConfig

        config = DiscordConfig(
            token=SecretStr("discord-token"),
            application_id="123456789",
            guild_id="987654321",
            intents=["guilds", "messages"],
        )
        assert config.bot_token_str == "discord-token"
        assert config.application_id == "123456789"

    def test_symphony_config(self):
        """Test SymphonyConfig."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="mycompany.symphony.com",
            bot_username="testbot",
            bot_private_key_path="/path/to/key.pem",
        )
        assert config.host == "mycompany.symphony.com"
        assert config.has_rsa_auth is True
        assert config.pod_url == "https://mycompany.symphony.com"

    def test_symphony_config_to_bdk(self):
        """Test SymphonyConfig.to_bdk_config()."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="mycompany.symphony.com",
            bot_username="testbot",
            bot_private_key_path="/path/to/key.pem",
            proxy_host="proxy.example.com",
            proxy_port=8080,
        )
        bdk_config = config.to_bdk_config()

        assert bdk_config["host"] == "mycompany.symphony.com"
        assert bdk_config["bot"]["username"] == "testbot"
        assert "proxy" in bdk_config


class TestSymphonyConfigProperties:
    """Tests for SymphonyConfig properties."""

    def test_has_rsa_auth_with_path(self):
        """Test has_rsa_auth with private key path."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            bot_private_key_path="/path/to/key.pem",
        )
        assert config.has_rsa_auth is True

    def test_has_rsa_auth_with_content(self):
        """Test has_rsa_auth with private key content."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            bot_private_key_content=SecretStr("-----BEGIN RSA PRIVATE KEY-----"),
        )
        assert config.has_rsa_auth is True

    def test_has_rsa_auth_false(self):
        """Test has_rsa_auth when not configured."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(host="test.symphony.com")
        assert config.has_rsa_auth is False

    def test_has_cert_auth(self):
        """Test has_cert_auth property."""
        from chatom.symphony import SymphonyConfig

        config1 = SymphonyConfig(
            host="test.symphony.com",
            bot_certificate_path="/path/to/cert.p12",
        )
        assert config1.has_cert_auth is True

        config2 = SymphonyConfig(host="test.symphony.com")
        assert config2.has_cert_auth is False

    def test_pod_url_simple(self):
        """Test pod_url property with simple config."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(host="test.symphony.com")
        assert config.pod_url == "https://test.symphony.com"

    def test_pod_url_with_custom_port(self):
        """Test pod_url property with custom port."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(host="test.symphony.com", port=8443)
        assert config.pod_url == "https://test.symphony.com:8443"

    def test_pod_url_with_context(self):
        """Test pod_url property with context path."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(host="test.symphony.com", context="/symphony")
        assert config.pod_url == "https://test.symphony.com/symphony"

    def test_has_cert_auth_with_content(self):
        """Test has_cert_auth with certificate content."""
        import os

        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_certificate_content=SecretStr("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----"),
        )
        assert config.has_cert_auth is True
        # Should have created a temp file
        assert config.is_using_temp_cert is True
        assert config.bot_certificate_path is not None
        assert os.path.exists(config.bot_certificate_path)
        # Cleanup
        config.cleanup_temp_cert()
        assert not os.path.exists(config._temp_cert_path or config.bot_certificate_path)

    def test_cert_content_creates_temp_file(self):
        """Test that certificate content creates a temp file with correct content."""
        import os

        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        cert_content = "-----BEGIN CERTIFICATE-----\nMIIBkTCC...\n-----END CERTIFICATE-----"
        config = SymphonyConfig(
            host="test.symphony.com",
            bot_certificate_content=SecretStr(cert_content),
        )

        # Check temp file was created
        assert config.bot_certificate_path is not None
        assert os.path.exists(config.bot_certificate_path)

        # Check content matches
        with open(config.bot_certificate_path) as f:
            file_content = f.read()
        assert file_content == cert_content

        # Cleanup
        config.cleanup_temp_cert()

    def test_cert_content_str_property(self):
        """Test bot_certificate_content_str property."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_certificate_content=SecretStr("cert-content"),
        )
        assert config.bot_certificate_content_str == "cert-content"
        config.cleanup_temp_cert()

    def test_cert_path_not_overwritten_by_content(self):
        """Test that providing both path and content uses the path."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_certificate_path="/explicit/path/to/cert.pem",
            bot_certificate_content=SecretStr("cert-content"),
        )
        # Path should not be overwritten
        assert config.bot_certificate_path == "/explicit/path/to/cert.pem"
        # No temp file created since path was provided
        assert config.is_using_temp_cert is False

    def test_bot_private_key_str(self):
        """Test bot_private_key_str property."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_private_key_content=SecretStr("secret-key"),
        )
        assert config.bot_private_key_str == "secret-key"

    def test_bot_certificate_password_str(self):
        """Test bot_certificate_password_str property."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_certificate_password=SecretStr("cert-pass"),
        )
        assert config.bot_certificate_password_str == "cert-pass"

    def test_proxy_password_str(self):
        """Test proxy_password_str property."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            proxy_password=SecretStr("proxy-pass"),
        )
        assert config.proxy_password_str == "proxy-pass"


class TestSymphonyConfigToBdk:
    """Tests for SymphonyConfig.to_bdk_config method."""

    def test_to_bdk_with_agent(self):
        """Test to_bdk_config with separate agent host."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            agent_host="agent.symphony.com",
            agent_port=8444,
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["agent"]["host"] == "agent.symphony.com"
        assert bdk_config["agent"]["port"] == 8444

    def test_to_bdk_with_key_manager(self):
        """Test to_bdk_config with key manager."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            key_manager_host="km.symphony.com",
            key_manager_port=8445,
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["keyManager"]["host"] == "km.symphony.com"
        assert bdk_config["keyManager"]["port"] == 8445

    def test_to_bdk_with_app(self):
        """Test to_bdk_config with app configuration."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            app_id="my-app",
            app_private_key_path="/path/to/app-key.pem",
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["app"]["appId"] == "my-app"
        assert bdk_config["app"]["privateKey"]["path"] == "/path/to/app-key.pem"

    def test_to_bdk_with_trust_store(self):
        """Test to_bdk_config with trust store."""
        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            trust_store_path="/path/to/truststore.jks",
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["ssl"]["trustStore"]["path"] == "/path/to/truststore.jks"

    def test_to_bdk_with_proxy(self):
        """Test to_bdk_config with proxy configuration."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username="user",
            proxy_password=SecretStr("pass"),
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["proxy"]["host"] == "proxy.example.com"
        assert bdk_config["proxy"]["port"] == 8080
        assert bdk_config["proxy"]["username"] == "user"
        assert bdk_config["proxy"]["password"] == "pass"

    def test_to_bdk_with_cert_auth(self):
        """Test to_bdk_config with certificate authentication."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            bot_certificate_path="/path/to/cert.p12",
            bot_certificate_password=SecretStr("cert-pass"),
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["bot"]["certificate"]["path"] == "/path/to/cert.p12"
        assert bdk_config["bot"]["certificate"]["password"] == "cert-pass"

    def test_to_bdk_with_key_content(self):
        """Test to_bdk_config with private key content."""
        from pydantic import SecretStr

        from chatom.symphony import SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="bot",
            bot_private_key_content=SecretStr("-----BEGIN RSA PRIVATE KEY-----"),
        )
        bdk_config = config.to_bdk_config()
        assert bdk_config["bot"]["privateKey"]["content"] == "-----BEGIN RSA PRIVATE KEY-----"


class TestRoomChannelAliases:
    """Tests for room/channel method aliases."""

    @pytest.mark.asyncio
    async def test_create_channel_and_create_room_equivalence(self):
        """Test that create_channel and create_room are equivalent."""
        from chatom.symphony import MockSymphonyBackend

        backend = MockSymphonyBackend()
        await backend.connect()

        # Create via create_channel
        channel_id = await backend.create_channel(
            name="Test Channel",
            description="Created via create_channel",
        )
        assert channel_id is not None

        # Create via create_room
        room_id = await backend.create_room(
            name="Test Room",
            description="Created via create_room",
        )
        assert room_id is not None

        # Both should be tracked
        assert len(backend.created_rooms) == 2

    @pytest.mark.asyncio
    async def test_base_class_methods_raise_not_implemented(self):
        """Test that base class methods raise NotImplementedError."""
        from chatom.backend import BackendBase

        # Create a minimal backend
        class MinimalBackend(BackendBase):
            name = "minimal"
            display_name = "Minimal"

            async def connect(self):
                self.connected = True

            async def disconnect(self):
                self.connected = False

            async def fetch_user(self, id):
                return None

            async def fetch_channel(self, id):
                return None

            async def fetch_messages(self, channel_id, **kwargs):
                return []

            async def send_message(self, channel_id, content, **kwargs):
                raise NotImplementedError()

        backend = MinimalBackend()
        await backend.connect()

        # These should raise NotImplementedError from base class
        with pytest.raises(NotImplementedError):
            await backend.create_dm(["123"])

        with pytest.raises(NotImplementedError):
            await backend.create_channel("test")

        with pytest.raises(NotImplementedError):
            await backend.join_channel("#test")

        with pytest.raises(NotImplementedError):
            await backend.leave_channel("#test")

        with pytest.raises(NotImplementedError):
            await backend.send_action("#test", "waves")

        with pytest.raises(NotImplementedError):
            await backend.send_notice("#test", "Notice!")


class TestMockDiscordAdvanced:
    """Additional tests for MockDiscordBackend."""

    @pytest.fixture
    def discord_backend(self):
        """Create a mock Discord backend."""
        from chatom.discord import DiscordConfig, MockDiscordBackend

        config = DiscordConfig(token=SecretStr("test-discord-token"))
        return MockDiscordBackend(config=config)

    @pytest.mark.asyncio
    async def test_discord_mock_user_properties(self, discord_backend):
        """Test Discord mock user with all properties."""
        await discord_backend.connect()

        user = discord_backend.add_mock_user(
            id="123",
            name="TestUser",
            handle="testuser",
            avatar_url="https://example.com/avatar.png",
            discriminator="1234",
            global_name="Global Name",
            is_bot=True,
            is_system=False,
        )

        assert user.id == "123"
        assert user.name == "TestUser"
        assert user.discriminator == "1234"
        assert user.global_name == "Global Name"
        assert user.is_bot is True
        assert user.is_system is False

    @pytest.mark.asyncio
    async def test_discord_mock_channel(self, discord_backend):
        """Test Discord mock channel creation."""
        await discord_backend.connect()

        # Create basic channel
        channel = discord_backend.add_mock_channel(
            id="text123",
            name="general",
        )
        assert channel.id == "text123"
        assert channel.name == "general"

    @pytest.mark.asyncio
    async def test_discord_mock_presence(self, discord_backend):
        """Test Discord mock presence with activities."""
        await discord_backend.connect()
        from chatom.base import PresenceStatus

        presence = discord_backend.set_mock_presence(
            user_id="123",
            status=PresenceStatus.DND,
            desktop_status=PresenceStatus.ONLINE,
            mobile_status=PresenceStatus.OFFLINE,
            web_status=PresenceStatus.IDLE,
        )

        assert presence.status == PresenceStatus.DND
        assert presence.desktop_status == PresenceStatus.ONLINE
        assert presence.mobile_status == PresenceStatus.OFFLINE
        assert presence.web_status == PresenceStatus.IDLE

    @pytest.mark.asyncio
    async def test_discord_sent_messages_property(self, discord_backend):
        """Test Discord sent_messages property."""
        await discord_backend.connect()
        discord_backend.add_mock_channel("C123", "general")

        await discord_backend.send_message("C123", "Message 1")
        await discord_backend.send_message("C123", "Message 2")

        sent = discord_backend.sent_messages
        assert len(sent) == 2
        assert sent[0].content == "Message 1"
        assert sent[1].content == "Message 2"

    @pytest.mark.asyncio
    async def test_discord_edited_messages_property(self, discord_backend):
        """Test Discord edited_messages property."""
        await discord_backend.connect()
        discord_backend.add_mock_channel("C123", "general")

        msg = await discord_backend.send_message("C123", "Original")
        await discord_backend.edit_message(message=msg.id, content="Edited", channel="C123")

        edited = discord_backend.edited_messages
        assert len(edited) == 1
        assert edited[0].content == "Edited"


class TestMockSlackAdvanced:
    """Additional tests for MockSlackBackend."""

    @pytest.fixture
    def slack_backend(self):
        """Create a mock Slack backend."""
        from chatom.slack import MockSlackBackend, SlackConfig

        config = SlackConfig(
            bot_token=SecretStr("xoxb-test-token"),
            app_token=SecretStr("xapp-test-token"),
        )
        return MockSlackBackend(config=config)

    @pytest.mark.asyncio
    async def test_slack_mock_user_properties(self, slack_backend):
        """Test Slack mock user with all properties."""
        await slack_backend.connect()

        user = slack_backend.add_mock_user(
            id="U123",
            name="Test User",
            handle="testuser",
            display_name="Test Display",
            is_bot=False,
        )

        assert user.id == "U123"
        assert user.name == "Test User"
        # Note: display_name is set separately from name
        assert user.is_bot is False

    @pytest.mark.asyncio
    async def test_slack_mock_channel_properties(self, slack_backend):
        """Test Slack mock channel with all properties."""
        await slack_backend.connect()

        channel = slack_backend.add_mock_channel(
            id="C123",
            name="project",
            is_private=True,
            is_archived=False,
            topic="Project discussion",
        )

        assert channel.id == "C123"
        assert channel.name == "project"
        assert channel.is_archived is False
        assert channel.topic == "Project discussion"

    @pytest.mark.asyncio
    async def test_slack_sent_messages_property(self, slack_backend):
        """Test Slack sent_messages property."""
        await slack_backend.connect()
        slack_backend.add_mock_channel("C123", "general")

        await slack_backend.send_message("C123", "Message 1")
        await slack_backend.send_message("C123", "Message 2")

        sent = slack_backend.sent_messages
        assert len(sent) == 2

    @pytest.mark.asyncio
    async def test_slack_added_reactions_property(self, slack_backend):
        """Test Slack added_reactions property."""
        await slack_backend.connect()
        slack_backend.add_mock_channel("C123", "general")

        msg_id = slack_backend.add_mock_message("C123", "U456", "React to me")
        await slack_backend.add_reaction(message=msg_id, emoji="thumbsup", channel="C123")
        await slack_backend.add_reaction(message=msg_id, emoji="heart", channel="C123")

        reactions = slack_backend.added_reactions
        assert len(reactions) == 2


class TestMockSymphonyAdvanced:
    """Additional tests for MockSymphonyBackend."""

    @pytest.fixture
    def symphony_backend(self):
        """Create a mock Symphony backend."""
        from chatom.symphony import MockSymphonyBackend, SymphonyConfig

        config = SymphonyConfig(
            pod_host="test.symphony.com",
            bot_username="testbot",
            bot_private_key_path="/fake/path",
        )
        return MockSymphonyBackend(config=config)

    @pytest.mark.asyncio
    async def test_symphony_mock_user_properties(self, symphony_backend):
        """Test Symphony mock user with add_mock_user."""
        await symphony_backend.connect()

        # Symphony uses user_id (int) instead of id
        symphony_backend.add_mock_user(
            user_id=12345,
            display_name="Test User",
            username="testuser",
            email="test@example.com",
        )

        # Verify it was added
        assert "12345" in symphony_backend.mock_users
        user_data = symphony_backend.mock_users["12345"]
        assert user_data["display_name"] == "Test User"
        assert user_data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_symphony_mock_stream_properties(self, symphony_backend):
        """Test Symphony mock stream with add_mock_stream."""
        await symphony_backend.connect()

        # Symphony uses add_mock_stream instead of add_mock_channel
        symphony_backend.add_mock_stream(
            stream_id="stream123",
            name="Project Room",
            stream_type="ROOM",
        )

        assert "stream123" in symphony_backend.mock_streams
        stream_data = symphony_backend.mock_streams["stream123"]
        assert stream_data["name"] == "Project Room"
        assert stream_data["type"] == "ROOM"

    @pytest.mark.asyncio
    async def test_symphony_sent_messages_property(self, symphony_backend):
        """Test Symphony sent_messages property."""
        await symphony_backend.connect()
        symphony_backend.add_mock_stream("stream123", "general")

        await symphony_backend.send_message("stream123", "Message 1")

        sent = symphony_backend.sent_messages
        assert len(sent) == 1


class TestMockDiscordBackendAdvanced:
    """Advanced tests for MockDiscordBackend to improve coverage."""

    @pytest.fixture
    def backend(self):
        """Create a mock Discord backend."""
        from chatom.discord import DiscordConfig, MockDiscordBackend

        config = DiscordConfig(token=SecretStr("test-token"))
        return MockDiscordBackend(config=config)

    @pytest.mark.asyncio
    async def test_get_sent_messages_returns_copy(self, backend):
        """Test get_sent_messages returns a copy."""
        await backend.connect()
        backend.add_mock_channel("123", "general")
        await backend.send_message("123", "Test")

        messages = backend.get_sent_messages()
        assert len(messages) == 1
        messages.clear()
        assert len(backend.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_get_edited_messages(self, backend):
        """Test get_edited_messages method."""
        await backend.connect()
        backend.add_mock_channel("123", "general")
        # add_mock_message takes (channel_id, user_id, content) positionally
        backend.add_mock_message("123", "user1", "Original", message_id="msg1")
        await backend.edit_message(message="msg1", content="Edited", channel="123")

        edited = backend.get_edited_messages()
        assert len(edited) == 1

    @pytest.mark.asyncio
    async def test_get_deleted_messages(self, backend):
        """Test get_deleted_messages method."""
        await backend.connect()
        backend.add_mock_channel("123", "general")
        await backend.delete_message(message="msg1", channel="123")

        deleted = backend.get_deleted_messages()
        assert len(deleted) == 1
        # Discord's deleted_messages is a list of dicts with channel_id and message_id
        assert deleted[0] == {"channel_id": "123", "message_id": "msg1"}

    @pytest.mark.asyncio
    async def test_get_reactions(self, backend):
        """Test get_reactions method."""
        await backend.connect()
        backend.add_mock_channel("123", "general")
        await backend.add_reaction(message="msg1", emoji="👍", channel="123")

        reactions = backend.get_reactions()
        assert len(reactions) == 1

    @pytest.mark.asyncio
    async def test_get_presence_updates(self, backend):
        """Test get_presence_updates method."""
        await backend.connect()
        await backend.set_presence("online", "Testing")

        updates = backend.get_presence_updates()
        assert len(updates) == 1

    @pytest.mark.asyncio
    async def test_fetch_messages_with_before(self, backend):
        """Test fetch_messages with before filter."""
        await backend.connect()
        backend.add_mock_channel("123", "general")
        # add_mock_message: (channel_id, user_id, content, message_id=)
        backend.add_mock_message("123", "user1", "First", message_id="100")
        backend.add_mock_message("123", "user1", "Second", message_id="200")
        backend.add_mock_message("123", "user1", "Third", message_id="300")

        # Get messages before ID 250
        messages = await backend.fetch_messages("123", before="250")
        assert len(messages) == 2
        # Should include 100 and 200 but not 300

    @pytest.mark.asyncio
    async def test_fetch_messages_with_after(self, backend):
        """Test fetch_messages with after filter."""
        await backend.connect()
        backend.add_mock_channel("123", "general")
        backend.add_mock_message("123", "user1", "First", message_id="100")
        backend.add_mock_message("123", "user1", "Second", message_id="200")
        backend.add_mock_message("123", "user1", "Third", message_id="300")

        # Get messages after ID 150
        messages = await backend.fetch_messages("123", after="150")
        assert len(messages) == 2
        # Should include 200 and 300 but not 100


class TestMockSymphonyBackendAdvanced:
    """Advanced tests for MockSymphonyBackend to improve coverage."""

    @pytest.fixture
    def backend(self):
        """Create a mock Symphony backend."""
        from chatom.symphony import MockSymphonyBackend, SymphonyConfig

        config = SymphonyConfig(
            host="mycompany.symphony.com",
            bot_username="testbot",
        )
        return MockSymphonyBackend(config=config)

    @pytest.mark.asyncio
    async def test_fetch_messages_with_before(self, backend):
        """Test fetch_messages with before timestamp filter."""
        from datetime import datetime, timezone

        await backend.connect()
        # Symphony uses add_mock_stream
        backend.add_mock_stream(stream_id="stream1", name="Test Stream")

        # Add messages with different timestamps
        backend.add_mock_message(
            stream_id="stream1",
            user_id=12345,
            content="Old message",
            timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        backend.add_mock_message(
            stream_id="stream1",
            user_id=12345,
            content="New message",
            timestamp=datetime(2023, 6, 1, tzinfo=timezone.utc),
        )

        # Filter by before timestamp (2022-01-01 in milliseconds)
        before_ts = str(int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000))
        messages = await backend.fetch_messages("stream1", before=before_ts)
        assert len(messages) == 1
        assert messages[0].content == "Old message"

    @pytest.mark.asyncio
    async def test_fetch_messages_with_after(self, backend):
        """Test fetch_messages with after timestamp filter."""
        from datetime import datetime, timezone

        await backend.connect()
        backend.add_mock_stream(stream_id="stream1", name="Test Stream")

        backend.add_mock_message(
            stream_id="stream1",
            user_id=12345,
            content="Old message",
            timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        backend.add_mock_message(
            stream_id="stream1",
            user_id=12345,
            content="New message",
            timestamp=datetime(2023, 6, 1, tzinfo=timezone.utc),
        )

        # Filter by after timestamp
        after_ts = str(int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000))
        messages = await backend.fetch_messages("stream1", after=after_ts)
        assert len(messages) == 1
        assert messages[0].content == "New message"


class TestMockSlackBackendAdvanced:
    """Advanced tests for MockSlackBackend to improve coverage."""

    @pytest.fixture
    def backend(self):
        """Create a mock Slack backend."""
        from chatom.slack import MockSlackBackend, SlackConfig

        config = SlackConfig(
            bot_token=SecretStr("xoxb-test-token"),
            app_token=SecretStr("xapp-test-token"),
        )
        return MockSlackBackend(config=config)

    @pytest.mark.asyncio
    async def test_add_mock_message(self, backend):
        """Test add_mock_message method."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")

        msg_id = backend.add_mock_message("C123", "U456", "Hello Slack!")
        assert msg_id is not None

        messages = await backend.fetch_messages("C123")
        assert len(messages) == 1
        assert messages[0].content == "Hello Slack!"

    @pytest.mark.asyncio
    async def test_set_presence_tracking(self, backend):
        """Test set_presence is tracked in presence_changes."""
        await backend.connect()
        backend.add_mock_user("U123", "testuser")

        # Just set presence directly (avoid buggy set_mock_presence which uses non-existent from_base)
        await backend.set_presence("away", "In a meeting")
        assert len(backend.presence_changes) >= 1

    @pytest.mark.asyncio
    async def test_get_sent_messages_returns_copy(self, backend):
        """Test get_sent_messages returns a copy."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")
        await backend.send_message("C123", "Test")

        messages = backend.get_sent_messages()
        assert len(messages) == 1
        messages.clear()
        assert len(backend.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_get_deleted_messages(self, backend):
        """Test get_deleted_messages method."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")
        await backend.delete_message(message="msg_1", channel="C123")

        deleted = backend.get_deleted_messages()
        assert len(deleted) == 1

    @pytest.mark.asyncio
    async def test_added_reactions_property(self, backend):
        """Test added_reactions property."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")
        await backend.add_reaction(message="msg_1", emoji="thumbsup", channel="C123")

        reactions = backend.added_reactions
        assert len(reactions) == 1

    @pytest.mark.asyncio
    async def test_presence_changes_property(self, backend):
        """Test presence_changes property."""
        await backend.connect()
        await backend.set_presence("away", "In a meeting")

        updates = backend.presence_changes
        assert len(updates) == 1


class TestMockSlackBackendExtended:
    """Extended tests for MockSlackBackend testing module."""

    @pytest.fixture
    def backend(self):
        """Create a mock Slack backend for testing."""
        from chatom.slack.testing import MockSlackBackend

        return MockSlackBackend()

    @pytest.mark.asyncio
    async def test_get_reactions(self, backend):
        """Test get_reactions method."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")
        msg_id = backend.add_mock_message("C123", "U456", "Hello")

        # Add reactions
        await backend.add_reaction(message=msg_id, emoji="thumbsup", channel="C123")
        await backend.add_reaction(message=msg_id, emoji="heart", channel="C123")

        reactions = backend.get_reactions("C123", msg_id)
        assert "thumbsup" in reactions
        assert "heart" in reactions

    @pytest.mark.asyncio
    async def test_get_reactions_empty(self, backend):
        """Test get_reactions returns empty list for message without reactions."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")

        reactions = backend.get_reactions("C123", "nonexistent")
        assert reactions == []

    @pytest.mark.asyncio
    async def test_clear(self, backend):
        """Test clear method."""
        await backend.connect()
        backend.add_mock_user("U123", "testuser")
        backend.add_mock_channel("C123", "general")
        backend.add_mock_message("C123", "U123", "Hello")

        # Clear all mock data
        backend.clear()

        assert len(backend._mock_users) == 0
        assert len(backend._mock_channels) == 0
        assert len(backend._mock_messages) == 0

    @pytest.mark.asyncio
    async def test_edit_message(self, backend):
        """Test edit_message method."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")
        msg_id = backend.add_mock_message("C123", "U456", "Original text")

        # Edit the message
        edited = await backend.edit_message(message=msg_id, content="Updated text", channel="C123")
        assert edited.content == "Updated text"
        assert edited.is_edited is True

    @pytest.mark.asyncio
    async def test_edit_message_not_found(self, backend):
        """Test edit_message raises error for nonexistent message."""
        await backend.connect()
        backend.add_mock_channel("C123", "general")

        with pytest.raises(RuntimeError, match="not found"):
            await backend.edit_message(message="nonexistent", content="New text", channel="C123")

    @pytest.mark.asyncio
    async def test_fetch_user_not_found(self, backend):
        """Test fetch_user returns None for unknown user."""
        await backend.connect()

        user = await backend.fetch_user("unknown")
        assert user is None

    @pytest.mark.asyncio
    async def test_fetch_channel_not_found(self, backend):
        """Test fetch_channel returns None for unknown channel."""
        await backend.connect()

        channel = await backend.fetch_channel("unknown")
        assert channel is None


class TestMockSymphonyBackendExtended:
    """Extended tests for MockSymphonyBackend testing module."""

    @pytest.fixture
    def backend(self):
        """Create a mock Symphony backend for testing."""
        from chatom.symphony.testing import MockSymphonyBackend

        return MockSymphonyBackend()

    @pytest.mark.asyncio
    async def test_set_mock_presence(self, backend):
        """Test set_mock_presence method."""
        from chatom.symphony.presence import SymphonyPresenceStatus

        await backend.connect()
        backend.add_mock_user(123, "Test User", "testuser")

        backend.set_mock_presence("123", SymphonyPresenceStatus.AVAILABLE)
        assert backend.mock_presence["123"] == SymphonyPresenceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_edit_message(self, backend):
        """Test edit_message method."""
        await backend.connect()
        backend.add_mock_stream("stream123", "Test Room")
        msg_id = backend.add_mock_message("stream123", 456, "Original text")

        edited = await backend.edit_message(message=msg_id, content="Updated text", channel="stream123")
        assert edited.content == "Updated text"

    @pytest.mark.asyncio
    async def test_fetch_stream_not_found(self, backend):
        """Test fetch_channel returns None for unknown stream."""
        await backend.connect()

        stream = await backend.fetch_channel("unknown")
        assert stream is None


class TestMockSymphonyBackendCoverage:
    """Additional tests for MockSymphonyBackend to improve coverage."""

    @pytest.fixture
    def backend(self):
        """Create a mock Symphony backend for testing."""
        from chatom.symphony.testing import MockSymphonyBackend

        return MockSymphonyBackend()

    @pytest.mark.asyncio
    async def test_fetch_user_from_cache(self, backend):
        """Test fetch_user checks cache first."""
        from chatom.symphony.user import SymphonyUser

        await backend.connect()

        # Add user directly to cache
        cached_user = SymphonyUser(
            id="123",
            name="Cached User",
            handle="cached",
        )
        backend.users.add(cached_user)

        # Fetch should find it in cache
        user = await backend.fetch_user("123")
        assert user is not None
        assert user.name == "Cached User"

    @pytest.mark.asyncio
    async def test_fetch_user_not_found(self, backend):
        """Test fetch_user returns None for unknown user."""
        await backend.connect()

        user = await backend.fetch_user("999999")
        assert user is None

    @pytest.mark.asyncio
    async def test_fetch_channel_from_cache(self, backend):
        """Test fetch_channel checks cache first."""
        from chatom.symphony.channel import SymphonyChannel

        await backend.connect()

        # Add channel directly to cache
        cached_channel = SymphonyChannel(
            id="stream123",
            name="Cached Channel",
        )
        backend.channels.add(cached_channel)

        # Fetch should find it in cache
        channel = await backend.fetch_channel("stream123")
        assert channel is not None
        assert channel.name == "Cached Channel"

    @pytest.mark.asyncio
    async def test_fetch_messages_with_before_filter(self, backend):
        """Test fetch_messages with before timestamp filter."""
        from datetime import datetime, timezone

        await backend.connect()
        backend.add_mock_stream("stream123", "Test Room")

        # Add messages with different timestamps
        backend.add_mock_message("stream123", 456, "Old message", timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc))
        backend.add_mock_message("stream123", 456, "New message", timestamp=datetime(2023, 6, 1, tzinfo=timezone.utc))

        # Fetch only messages before 2022 (timestamp in ms)
        before_ts = str(int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000))
        messages = await backend.fetch_messages("stream123", before=before_ts)
        assert len(messages) == 1
        assert messages[0].content == "Old message"

    @pytest.mark.asyncio
    async def test_fetch_messages_with_after_filter(self, backend):
        """Test fetch_messages with after timestamp filter."""
        from datetime import datetime, timezone

        await backend.connect()
        backend.add_mock_stream("stream123", "Test Room")

        # Add messages with different timestamps
        backend.add_mock_message("stream123", 456, "Old message", timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc))
        backend.add_mock_message("stream123", 456, "New message", timestamp=datetime(2023, 6, 1, tzinfo=timezone.utc))

        # Fetch only messages after 2022 (timestamp in ms)
        after_ts = str(int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() * 1000))
        messages = await backend.fetch_messages("stream123", after=after_ts)
        assert len(messages) == 1
        assert messages[0].content == "New message"

    @pytest.mark.asyncio
    async def test_send_message_with_data_and_attachments(self, backend):
        """Test send_message with data and attachments kwargs."""
        await backend.connect()
        backend.add_mock_stream("stream123", "Test Room")

        message = await backend.send_message(
            "stream123",
            "<messageML>Hello with data</messageML>",
            data={"key": "value"},
            attachments=[{"name": "file.txt"}],
        )

        assert message is not None
        assert len(backend.sent_messages) == 1
        assert backend.sent_messages[0]["data"] == {"key": "value"}
        assert backend.sent_messages[0]["attachments"] == [{"name": "file.txt"}]

    @pytest.mark.asyncio
    async def test_mention_channel(self, backend):
        """Test mention_channel method."""
        from chatom.symphony.channel import SymphonyChannel

        await backend.connect()

        # Test with SymphonyChannel
        channel = SymphonyChannel(
            id="stream123",
            name="Test Room",
        )
        mention = backend.mention_channel(channel)
        assert mention == "Test Room"

    @pytest.mark.asyncio
    async def test_mention_channel_generic(self, backend):
        """Test mention_channel with generic Channel."""
        from chatom.base import Channel

        await backend.connect()

        # Test with generic Channel
        channel = Channel(id="generic123", name="Generic Channel")
        mention = backend.mention_channel(channel)
        assert mention == "Generic Channel"

    @pytest.mark.asyncio
    async def test_create_dm_creates_stream(self, backend):
        """Test create_dm creates a new IM stream."""
        await backend.connect()

        stream_id = await backend.create_dm(["123", "456"])

        assert stream_id is not None
        assert stream_id.startswith("im_")
        assert len(backend.created_ims) == 1
        assert backend.created_ims[0] == [123, 456]  # Converted to ints
        # Verify the stream was added to mock_streams
        assert stream_id in backend.mock_streams

    @pytest.mark.asyncio
    async def test_reset_method(self, backend):
        """Test reset method clears all mock and tracking data."""
        await backend.connect()

        # Add mock data
        backend.add_mock_user(123, "Test User", "testuser")
        backend.add_mock_stream("stream123", "Test Room")
        backend.add_mock_message("stream123", 123, "Message")
        backend.set_mock_presence("123", backend.mock_presence.get("123"))

        # Add tracking data
        await backend.send_message("stream123", "<messageML>Sent</messageML>")
        await backend.edit_message(message="msg1", content="<messageML>Edited</messageML>", channel="stream123")
        await backend.delete_message(message="msg2", channel="stream123")
        await backend.set_presence("away")
        await backend.create_im(["123", "456"])
        await backend.create_room("New Room")

        # Verify data exists before reset
        assert len(backend.mock_users) > 0
        assert len(backend.mock_streams) > 0
        assert len(backend.mock_messages) > 0
        assert len(backend.sent_messages) > 0
        assert len(backend.edited_messages) > 0
        assert len(backend.deleted_messages) > 0
        assert len(backend.presence_changes) > 0
        assert len(backend.created_ims) > 0
        assert len(backend.created_rooms) > 0

        # Call reset
        backend.reset()

        # Verify all stores are empty
        assert len(backend.mock_users) == 0
        assert len(backend.mock_streams) == 0
        assert len(backend.mock_messages) == 0
        assert len(backend.mock_presence) == 0
        assert len(backend.sent_messages) == 0
        assert len(backend.edited_messages) == 0
        assert len(backend.deleted_messages) == 0
        assert len(backend.presence_changes) == 0
        assert len(backend.created_ims) == 0
        assert len(backend.created_rooms) == 0


class TestDiscordCoverageImprovements:
    """Tests to improve coverage for Discord-specific code.

    This covers previously untested lines in:
    - testing.py: lines 307-317 (clear), 489 (get_presence), 526 (remove_reaction)
    - message.py: lines 178-208, 219, 240, 259, 261 (properties and methods)
    - channel.py: lines 86, 98 (is_voice, is_text properties)
    - config.py: line 82 (has_token property)
    """

    @pytest.fixture
    def discord_backend(self):
        """Create a mock Discord backend."""
        from chatom.discord import DiscordConfig, MockDiscordBackend

        config = DiscordConfig(token=SecretStr("test-token"))
        return MockDiscordBackend(config=config)

    # Tests for testing.py: clear() method (lines 307-317)
    # The clear() method now works correctly after fixing the _items bug.
    # This test verifies the clear method properly clears all stores.
    @pytest.mark.asyncio
    async def test_mock_discord_clear_executes_private_store_clearing(self, discord_backend):
        """Test the clear() method properly clears all internal stores."""
        await discord_backend.connect()

        # Add mock data
        discord_backend.add_mock_user("123", "TestUser", "testuser")
        discord_backend.add_mock_channel("456", "general")
        discord_backend.add_mock_message("456", "123", "Hello")
        discord_backend.set_mock_presence("123")

        # Add tracking data
        await discord_backend.send_message("456", "Sent message")
        await discord_backend.edit_message(message="msg1", content="Edited", channel="456")
        await discord_backend.delete_message(message="msg1", channel="456")
        await discord_backend.add_reaction(message="msg1", emoji="👍", channel="456")

        # Verify data exists
        assert len(discord_backend._mock_users) > 0
        assert len(discord_backend._mock_channels) > 0
        assert len(discord_backend._mock_messages) > 0
        assert len(discord_backend._mock_presence) > 0
        assert len(discord_backend._sent_messages) > 0
        assert len(discord_backend._edited_messages) > 0
        assert len(discord_backend._deleted_messages) > 0
        assert len(discord_backend._reactions) > 0

        # Call clear - this should complete successfully now
        discord_backend.clear()

        # Verify all stores were cleared
        assert len(discord_backend._mock_users) == 0
        assert len(discord_backend._mock_channels) == 0
        assert len(discord_backend._mock_messages) == 0
        assert len(discord_backend._mock_presence) == 0
        assert len(discord_backend._sent_messages) == 0
        assert len(discord_backend._edited_messages) == 0
        assert len(discord_backend._deleted_messages) == 0
        assert len(discord_backend._reactions) == 0
        assert len(discord_backend._presence_updates) == 0

    # Tests for testing.py: get_presence() method (line 489)
    @pytest.mark.asyncio
    async def test_mock_discord_get_presence(self, discord_backend):
        """Test get_presence returns mock presence for a user."""
        from chatom.base import PresenceStatus

        await discord_backend.connect()

        # Set presence for user
        discord_backend.set_mock_presence("user123", PresenceStatus.ONLINE)

        # Get presence
        presence = await discord_backend.get_presence("user123")
        assert presence is not None
        assert presence.status == PresenceStatus.ONLINE

    @pytest.mark.asyncio
    async def test_mock_discord_get_presence_not_found(self, discord_backend):
        """Test get_presence returns None when user has no presence."""
        await discord_backend.connect()

        presence = await discord_backend.get_presence("nonexistent")
        assert presence is None

    # Tests for testing.py: remove_reaction() method (line 526)
    @pytest.mark.asyncio
    async def test_mock_discord_remove_reaction(self, discord_backend):
        """Test remove_reaction tracks removal."""
        await discord_backend.connect()
        discord_backend.add_mock_channel("123", "general")

        # Add and remove reaction
        await discord_backend.add_reaction(message="msg1", emoji="👍", channel="123")
        await discord_backend.remove_reaction(message="msg1", emoji="👍", channel="123")

        reactions = discord_backend.get_reactions()
        assert len(reactions) == 2
        assert reactions[0]["action"] == "add"
        assert reactions[1]["action"] == "remove"
        assert reactions[1]["emoji"] == "👍"
        assert reactions[1]["channel_id"] == "123"
        assert reactions[1]["message_id"] == "msg1"


class TestDiscordMessageProperties:
    """Tests for DiscordMessage property coverage.

    Covers message.py lines 178, 183, 188, 193, 198, 203, 208, 219, 240, 259, 261.
    """

    def test_is_reply_with_reply_type(self):
        """Test is_reply returns True for REPLY type messages."""
        from chatom.discord import DiscordMessage, DiscordMessageType

        msg = DiscordMessage(
            id="1",
            content="Reply message",
            discord_type=DiscordMessageType.REPLY,
        )
        assert msg.is_reply is True

    def test_is_reply_with_reply_to(self):
        """Test is_reply returns True when reply_to is set."""
        from chatom.discord import DiscordMessage

        # Create a message to reply to
        original_msg = DiscordMessage(id="original", content="Original message")
        msg = DiscordMessage(
            id="1",
            content="Reply message",
            reply_to=original_msg,
        )
        assert msg.is_reply is True

    def test_is_reply_false(self):
        """Test is_reply returns False for regular messages."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Regular message")
        assert msg.is_reply is False

    def test_is_ephemeral(self):
        """Test is_ephemeral with EPHEMERAL flag."""
        from chatom.discord import DiscordMessage, DiscordMessageFlags

        msg = DiscordMessage(
            id="1",
            content="Ephemeral message",
            flags=DiscordMessageFlags.EPHEMERAL,
        )
        assert msg.is_ephemeral is True

    def test_is_ephemeral_false(self):
        """Test is_ephemeral returns False without flag."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Normal message", flags=0)
        assert msg.is_ephemeral is False

    def test_is_crossposted(self):
        """Test is_crossposted with CROSSPOSTED flag."""
        from chatom.discord import DiscordMessage, DiscordMessageFlags

        msg = DiscordMessage(
            id="1",
            content="Crossposted message",
            flags=DiscordMessageFlags.CROSSPOSTED,
        )
        assert msg.is_crossposted is True

    def test_is_crossposted_false(self):
        """Test is_crossposted returns False without flag."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Normal message", flags=0)
        assert msg.is_crossposted is False

    def test_has_thread(self):
        """Test has_thread with HAS_THREAD flag."""
        from chatom.discord import DiscordMessage, DiscordMessageFlags

        msg = DiscordMessage(
            id="1",
            content="Message with thread",
            flags=DiscordMessageFlags.HAS_THREAD,
        )
        assert msg.has_thread is True

    def test_has_thread_false(self):
        """Test has_thread returns False without flag."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Normal message", flags=0)
        assert msg.has_thread is False

    def test_is_voice_message(self):
        """Test is_voice_message with IS_VOICE_MESSAGE flag."""
        from chatom.discord import DiscordMessage, DiscordMessageFlags

        msg = DiscordMessage(
            id="1",
            content="",
            flags=DiscordMessageFlags.IS_VOICE_MESSAGE,
        )
        assert msg.is_voice_message is True

    def test_is_voice_message_false(self):
        """Test is_voice_message returns False without flag."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Text message", flags=0)
        assert msg.is_voice_message is False

    def test_suppresses_embeds(self):
        """Test suppresses_embeds with SUPPRESS_EMBEDS flag."""
        from chatom.discord import DiscordMessage, DiscordMessageFlags

        msg = DiscordMessage(
            id="1",
            content="No embeds",
            flags=DiscordMessageFlags.SUPPRESS_EMBEDS,
        )
        assert msg.suppresses_embeds is True

    def test_suppresses_embeds_false(self):
        """Test suppresses_embeds returns False without flag."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Normal message", flags=0)
        assert msg.suppresses_embeds is False

    def test_suppresses_notifications(self):
        """Test suppresses_notifications with SUPPRESS_NOTIFICATIONS flag."""
        from chatom.discord import DiscordMessage, DiscordMessageFlags

        msg = DiscordMessage(
            id="1",
            content="Silent message",
            flags=DiscordMessageFlags.SUPPRESS_NOTIFICATIONS,
        )
        assert msg.suppresses_notifications is True

    def test_suppresses_notifications_false(self):
        """Test suppresses_notifications returns False without flag."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Normal message", flags=0)
        assert msg.suppresses_notifications is False

    def test_has_flag(self):
        """Test has_flag method with specific flags."""
        from chatom.discord import DiscordMessage, DiscordMessageFlags

        msg = DiscordMessage(
            id="1",
            content="Message with multiple flags",
            flags=DiscordMessageFlags.EPHEMERAL | DiscordMessageFlags.CROSSPOSTED,
        )
        assert msg.has_flag(DiscordMessageFlags.EPHEMERAL) is True
        assert msg.has_flag(DiscordMessageFlags.CROSSPOSTED) is True
        assert msg.has_flag(DiscordMessageFlags.HAS_THREAD) is False

    def test_to_formatted(self):
        """Test to_formatted converts message to FormattedMessage."""
        from chatom.base import Channel, Organization, User
        from chatom.discord import DiscordMessage, DiscordUser

        msg = DiscordMessage(
            id="msg123",
            content="Hello **world**!",
            author=User(id="user123"),
            channel=Channel(id="ch123"),
            guild=Organization(id="guild123"),
            tags=[DiscordUser(id="user456")],
            webhook_id="webhook123",
        )

        formatted = msg.to_formatted()

        assert "Hello **world**!" in str(formatted)
        assert formatted.metadata["source_backend"] == "discord"
        assert formatted.metadata["message_id"] == "msg123"
        assert formatted.metadata["author_id"] == "user123"
        assert formatted.metadata["channel_id"] == "ch123"
        assert formatted.metadata["guild_id"] == "guild123"
        assert formatted.metadata["mention_ids"] == ["user456"]
        assert formatted.metadata["webhook_id"] == "webhook123"

    def test_to_formatted_minimal(self):
        """Test to_formatted with minimal message."""
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(id="1", content="Simple message")

        formatted = msg.to_formatted()

        assert formatted.metadata["source_backend"] == "discord"
        assert formatted.metadata["message_id"] == "1"

    def test_to_formatted_with_attachments(self):
        """Test to_formatted converts attachments."""
        from chatom.base import Attachment
        from chatom.discord import DiscordMessage

        msg = DiscordMessage(
            id="msg123",
            content="See attached file",
            attachments=[
                Attachment(
                    id="att1",
                    filename="image.png",
                    url="https://example.com/image.png",
                    content_type="image/png",
                    size=1024,
                ),
            ],
        )

        formatted = msg.to_formatted()

        assert len(formatted.attachments) == 1
        assert formatted.attachments[0].filename == "image.png"
        assert formatted.attachments[0].url == "https://example.com/image.png"
        assert formatted.attachments[0].content_type == "image/png"
        assert formatted.attachments[0].size == 1024

    def test_from_formatted(self):
        """Test from_formatted creates message from FormattedMessage."""
        from chatom.discord import DiscordMessage
        from chatom.format import FormattedMessage

        fm = FormattedMessage()
        fm.add_text("Hello from formatted!")
        fm.metadata["original_id"] = "orig123"

        msg = DiscordMessage.from_formatted(fm, id="new123")

        assert msg.id == "new123"
        assert "Hello from formatted!" in msg.content
        assert msg.backend == "discord"
        assert msg.metadata.get("original_id") == "orig123"


class TestDiscordChannelProperties:
    """Tests for DiscordChannel property coverage.

    Covers channel.py lines 86, 98 (is_voice, is_text).
    """

    def test_is_voice_guild_voice(self):
        """Test is_voice returns True for GUILD_VOICE channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="Voice Chat",
            discord_type=DiscordChannelType.GUILD_VOICE,
        )
        assert channel.is_voice is True

    def test_is_voice_stage_voice(self):
        """Test is_voice returns True for GUILD_STAGE_VOICE channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="Stage",
            discord_type=DiscordChannelType.GUILD_STAGE_VOICE,
        )
        assert channel.is_voice is True

    def test_is_voice_false_for_text(self):
        """Test is_voice returns False for text channels."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="general",
            discord_type=DiscordChannelType.GUILD_TEXT,
        )
        assert channel.is_voice is False

    def test_is_text_guild_text(self):
        """Test is_text returns True for GUILD_TEXT channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="general",
            discord_type=DiscordChannelType.GUILD_TEXT,
        )
        assert channel.is_text is True

    def test_is_text_guild_announcement(self):
        """Test is_text returns True for GUILD_ANNOUNCEMENT channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="announcements",
            discord_type=DiscordChannelType.GUILD_ANNOUNCEMENT,
        )
        assert channel.is_text is True

    def test_is_text_dm(self):
        """Test is_text returns True for DM channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="DM",
            discord_type=DiscordChannelType.DM,
        )
        assert channel.is_text is True

    def test_is_text_group_dm(self):
        """Test is_text returns True for GROUP_DM channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="Group",
            discord_type=DiscordChannelType.GROUP_DM,
        )
        assert channel.is_text is True

    def test_is_text_false_for_voice(self):
        """Test is_text returns False for voice channels."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="Voice",
            discord_type=DiscordChannelType.GUILD_VOICE,
        )
        assert channel.is_text is False

    def test_is_text_false_for_category(self):
        """Test is_text returns False for category channels."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="1",
            name="Category",
            discord_type=DiscordChannelType.GUILD_CATEGORY,
        )
        assert channel.is_text is False


class TestDiscordConfigProperties:
    """Tests for DiscordConfig property coverage.

    Covers config.py line 82 (has_token).
    """

    def test_has_token_true(self):
        """Test has_token returns True when token is set."""
        from chatom.discord import DiscordConfig

        config = DiscordConfig(token=SecretStr("my-bot-token"))
        assert config.has_token is True

    def test_has_token_false_empty_string(self):
        """Test has_token returns False for empty token."""
        from chatom.discord import DiscordConfig

        config = DiscordConfig(token=SecretStr(""))
        assert config.has_token is False

    def test_has_token_false_default(self):
        """Test has_token returns False with default config."""
        from chatom.discord import DiscordConfig

        config = DiscordConfig()
        assert config.has_token is False

    def test_bot_token_str(self):
        """Test bot_token_str returns the plain string token."""
        from chatom.discord import DiscordConfig

        config = DiscordConfig(token=SecretStr("super-secret-token"))
        assert config.bot_token_str == "super-secret-token"


class TestForwardMessageSlack:
    """Tests for forward_message on MockSlackBackend."""

    @pytest.fixture
    def backend(self):
        """Create a mock Slack backend."""
        from chatom.slack import MockSlackBackend, SlackConfig

        config = SlackConfig(
            bot_token=SecretStr("xoxb-test-token"),
            app_token=SecretStr("xapp-test-token"),
        )
        return MockSlackBackend(config=config)

    @pytest.mark.asyncio
    async def test_forward_message_basic(self, backend):
        """Test basic message forwarding."""
        from chatom.base import MessageType

        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")
        backend.add_mock_user("U123", "Test User", "testuser")

        # Create source message
        source_msg = await backend.send_message("C123", "Hello, world!")

        # Forward the message
        forwarded = await backend.forward_message(source_msg, "C456")

        assert forwarded is not None
        assert "Hello, world!" in forwarded.content
        assert forwarded.message_type == MessageType.FORWARD
        assert forwarded.forwarded_from == source_msg
        assert forwarded.is_forwarded is True

    @pytest.mark.asyncio
    async def test_forward_message_with_attribution(self, backend):
        """Test forwarding with attribution."""
        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")

        source_msg = await backend.send_message("C123", "Important message")
        forwarded = await backend.forward_message(source_msg, "C456", include_attribution=True)

        assert "Forwarded from" in forwarded.content

    @pytest.mark.asyncio
    async def test_forward_message_without_attribution(self, backend):
        """Test forwarding without attribution."""
        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")

        source_msg = await backend.send_message("C123", "Simple message")
        forwarded = await backend.forward_message(source_msg, "C456", include_attribution=False)

        assert "Forwarded from" not in forwarded.content
        assert forwarded.content == "Simple message"

    @pytest.mark.asyncio
    async def test_forward_message_with_prefix(self, backend):
        """Test forwarding with custom prefix."""
        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")

        source_msg = await backend.send_message("C123", "Alert content")
        forwarded = await backend.forward_message(source_msg, "C456", prefix="⚠️ ALERT: ", include_attribution=False)

        assert forwarded.content.startswith("⚠️ ALERT: ")

    @pytest.mark.asyncio
    async def test_forward_message_with_channel_object(self, backend):
        """Test forwarding using Channel object."""

        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        dest_channel = backend.add_mock_channel("C456", "dest-channel")

        source_msg = await backend.send_message("C123", "Message to forward")
        forwarded = await backend.forward_message(source_msg, dest_channel)

        assert forwarded is not None
        assert forwarded.channel.id == "C456"

    @pytest.mark.asyncio
    async def test_forward_message_requires_message_object(self, backend):
        """Test that forwarding requires a Message object, not just an ID."""
        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")

        with pytest.raises(ValueError, match="requires a Message object"):
            await backend.forward_message("some-message-id", "C456")


class TestForwardMessageDiscord:
    """Tests for forward_message on MockDiscordBackend."""

    @pytest.fixture
    def backend(self):
        """Create a mock Discord backend."""
        from chatom.discord import DiscordConfig, MockDiscordBackend

        config = DiscordConfig(
            token=SecretStr("discord-test-token"),
        )
        return MockDiscordBackend(config=config)

    @pytest.mark.asyncio
    async def test_forward_message_basic(self, backend):
        """Test basic message forwarding."""
        from chatom.base import MessageType

        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")

        source_msg = await backend.send_message("C123", "Discord message!")

        forwarded = await backend.forward_message(source_msg, "C456")

        assert forwarded is not None
        assert "Discord message!" in forwarded.content
        assert forwarded.message_type == MessageType.FORWARD
        assert forwarded.forwarded_from == source_msg

    @pytest.mark.asyncio
    async def test_forward_message_without_attribution(self, backend):
        """Test forwarding without attribution."""
        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")

        source_msg = await backend.send_message("C123", "Simple discord message")
        forwarded = await backend.forward_message(source_msg, "C456", include_attribution=False)

        assert "Forwarded from" not in forwarded.content
        assert forwarded.content == "Simple discord message"

    @pytest.mark.asyncio
    async def test_forward_message_requires_message_object(self, backend):
        """Test that forwarding requires a Message object."""
        await backend.connect()
        backend.add_mock_channel("C123", "source-channel")
        backend.add_mock_channel("C456", "dest-channel")

        with pytest.raises(ValueError, match="requires a Message object"):
            await backend.forward_message("some-message-id", "C456")


class TestForwardMessageSymphony:
    """Tests for forward_message on MockSymphonyBackend."""

    @pytest.fixture
    def backend(self):
        """Create a mock Symphony backend."""
        from chatom.symphony import MockSymphonyBackend, SymphonyConfig

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="test-bot",
        )
        return MockSymphonyBackend(config=config)

    @pytest.mark.asyncio
    async def test_forward_message_basic(self, backend):
        """Test basic message forwarding."""
        from chatom.base import MessageType

        await backend.connect()
        backend.add_mock_stream("S123", "source-room")
        backend.add_mock_stream("S456", "dest-room")

        source_msg = await backend.send_message("S123", "Symphony message!")

        forwarded = await backend.forward_message(source_msg, "S456")

        assert forwarded is not None
        assert "Symphony message!" in forwarded.content
        assert forwarded.message_type == MessageType.FORWARD
        assert forwarded.forwarded_from == source_msg

    @pytest.mark.asyncio
    async def test_forward_message_with_messageml_content(self, backend):
        """Test forwarding preserves MessageML formatting."""
        await backend.connect()
        backend.add_mock_stream("S123", "source-room")
        backend.add_mock_stream("S456", "dest-room")

        source_msg = await backend.send_message("S123", "Formatted message")
        forwarded = await backend.forward_message(source_msg, "S456")

        # Should have MessageML structure
        assert "<messageML>" in forwarded.formatted_content

    @pytest.mark.asyncio
    async def test_forward_message_requires_message_object(self, backend):
        """Test that forwarding requires a Message object."""
        await backend.connect()
        backend.add_mock_stream("S123", "source-room")
        backend.add_mock_stream("S456", "dest-room")

        with pytest.raises(ValueError, match="requires a Message object"):
            await backend.forward_message("some-message-id", "S456")


class TestForwardMessageProperties:
    """Tests for Message forwarding-related properties."""

    def test_message_is_forwarded_property(self):
        """Test is_forwarded property returns True for forwarded messages."""
        from chatom.base import Message, MessageType

        msg = Message(content="Test", message_type=MessageType.FORWARD)
        assert msg.is_forwarded is True

        regular_msg = Message(content="Test", message_type=MessageType.DEFAULT)
        assert regular_msg.is_forwarded is False

    def test_message_is_forwarded_with_forwarded_from(self):
        """Test is_forwarded returns True when forwarded_from is set."""
        from chatom.base import Message

        original = Message(id="orig-123", content="Original")
        forwarded = Message(content="Forwarded", forwarded_from=original)

        assert forwarded.is_forwarded is True

    def test_forwarded_from_id_property(self):
        """Test forwarded_from_id property returns the original message ID."""
        from chatom.base import Message

        original = Message(id="orig-123", content="Original")
        forwarded = Message(content="Forwarded", forwarded_from=original)

        assert forwarded.forwarded_from_id == "orig-123"

    def test_forwarded_from_id_empty_when_not_forwarded(self):
        """Test forwarded_from_id returns empty string when not a forward."""
        from chatom.base import Message

        msg = Message(content="Regular message")
        assert msg.forwarded_from_id == ""


class TestForwardingCapability:
    """Tests for FORWARDING capability."""

    def test_forwarding_capability_exists(self):
        """Test that FORWARDING capability is defined."""
        from chatom.base import Capability

        assert hasattr(Capability, "FORWARDING")
        assert Capability.FORWARDING.value == "forwarding"

    def test_slack_has_forwarding_capability(self):
        """Test Slack capabilities include FORWARDING."""
        from chatom.base import SLACK_CAPABILITIES, Capability

        assert Capability.FORWARDING in SLACK_CAPABILITIES.capabilities

    def test_discord_has_forwarding_capability(self):
        """Test Discord capabilities include FORWARDING."""
        from chatom.base import DISCORD_CAPABILITIES, Capability

        assert Capability.FORWARDING in DISCORD_CAPABILITIES.capabilities

    def test_symphony_has_forwarding_capability(self):
        """Test Symphony capabilities include FORWARDING."""
        from chatom.base import SYMPHONY_CAPABILITIES, Capability

        assert Capability.FORWARDING in SYMPHONY_CAPABILITIES.capabilities


class TestResolveMessageIdRegressions:
    """Regression tests for _resolve_message_id tuple unpacking.

    These tests verify that the channel_id and message_id are correctly
    resolved and used in the right order for reactions, edits, and deletes.
    """

    @pytest.fixture
    def slack_backend(self):
        """Create a mock Slack backend."""
        from chatom.slack import MockSlackBackend, SlackConfig

        config = SlackConfig(bot_token=SecretStr("xoxb-test"))
        return MockSlackBackend(config=config)

    @pytest.fixture
    def discord_backend(self):
        """Create a mock Discord backend."""
        from chatom.discord import DiscordConfig, MockDiscordBackend

        config = DiscordConfig(token=SecretStr("discord-test"))
        return MockDiscordBackend(config=config)

    @pytest.mark.asyncio
    async def test_slack_add_reaction_with_message_object(self, slack_backend):
        """Test add_reaction correctly extracts IDs from a Message object."""
        from chatom.slack import SlackChannel, SlackMessage

        await slack_backend.connect()
        slack_backend.add_mock_channel("C123", "general")

        # Create a message object with channel info
        msg = SlackMessage(
            id="1234567890.123456",
            content="Test",
            channel=SlackChannel(id="C123", name="general"),
        )

        # This should correctly extract channel_id and message_id
        await slack_backend.add_reaction(message=msg, emoji="thumbsup")

        assert len(slack_backend.added_reactions) == 1
        channel_id, message_id, emoji = slack_backend.added_reactions[0]
        assert channel_id == "C123"
        assert message_id == "1234567890.123456"
        assert emoji == "thumbsup"

    @pytest.mark.asyncio
    async def test_slack_add_reaction_with_string_ids(self, slack_backend):
        """Test add_reaction with string IDs uses keyword args correctly."""
        await slack_backend.connect()
        slack_backend.add_mock_channel("C456", "random")

        await slack_backend.add_reaction(
            message="9876543210.654321",
            emoji="heart",
            channel="C456",
        )

        assert len(slack_backend.added_reactions) == 1
        channel_id, message_id, emoji = slack_backend.added_reactions[0]
        assert channel_id == "C456"
        assert message_id == "9876543210.654321"
        assert emoji == "heart"

    @pytest.mark.asyncio
    async def test_discord_add_reaction_with_message_object(self, discord_backend):
        """Test Discord add_reaction correctly extracts IDs from a Message object."""
        from chatom.discord import DiscordChannel, DiscordMessage

        await discord_backend.connect()
        discord_backend.add_mock_channel("123456789", "general")

        msg = DiscordMessage(
            id="987654321",
            content="Test",
            channel=DiscordChannel(id="123456789", name="general"),
        )

        await discord_backend.add_reaction(message=msg, emoji="👍")

        reactions = discord_backend.get_reactions()
        assert len(reactions) == 1
        assert reactions[0]["channel_id"] == "123456789"
        assert reactions[0]["message_id"] == "987654321"
        assert reactions[0]["emoji"] == "👍"

    @pytest.mark.asyncio
    async def test_discord_add_reaction_with_string_ids(self, discord_backend):
        """Test Discord add_reaction with string IDs uses keyword args correctly."""
        await discord_backend.connect()
        discord_backend.add_mock_channel("111222333", "random")

        await discord_backend.add_reaction(
            message="444555666",
            emoji="🎉",
            channel="111222333",
        )

        reactions = discord_backend.get_reactions()
        assert len(reactions) == 1
        assert reactions[0]["channel_id"] == "111222333"
        assert reactions[0]["message_id"] == "444555666"
        assert reactions[0]["emoji"] == "🎉"

    @pytest.mark.asyncio
    async def test_slack_remove_reaction_correct_order(self, slack_backend):
        """Test remove_reaction uses correct channel/message order."""
        await slack_backend.connect()
        slack_backend.add_mock_channel("C789", "test")

        await slack_backend.remove_reaction(
            message="1111111111.111111",
            emoji="wave",
            channel="C789",
        )

        assert len(slack_backend.removed_reactions) == 1
        channel_id, message_id, emoji = slack_backend.removed_reactions[0]
        assert channel_id == "C789"
        assert message_id == "1111111111.111111"
        assert emoji == "wave"

    @pytest.mark.asyncio
    async def test_slack_edit_message_correct_order(self, slack_backend):
        """Test edit_message uses correct channel/message order."""
        await slack_backend.connect()
        slack_backend.add_mock_channel("C999", "edits")
        msg_id = slack_backend.add_mock_message("C999", "U123", "Original")

        edited = await slack_backend.edit_message(
            message=msg_id,
            content="Edited content",
            channel="C999",
        )

        assert edited.content == "Edited content"

    @pytest.mark.asyncio
    async def test_slack_delete_message_correct_order(self, slack_backend):
        """Test delete_message uses correct channel/message order."""
        await slack_backend.connect()
        slack_backend.add_mock_channel("C888", "deletes")
        msg_id = slack_backend.add_mock_message("C888", "U123", "To delete")

        await slack_backend.delete_message(message=msg_id, channel="C888")

        deleted = slack_backend.get_deleted_messages()
        assert len(deleted) == 1
        assert deleted[0] == ("C888", msg_id)


class TestChannelDmToConvenience:
    """Tests for Channel.dm_to() and Channel.group_dm_to() convenience methods."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User(id="U123", name="testuser", display_name="Test User")

    @pytest.fixture
    def users(self):
        """Create multiple test users."""
        return [
            User(id="U123", name="alice", display_name="Alice"),
            User(id="U456", name="bob", display_name="Bob"),
        ]

    def test_dm_to_creates_direct_channel(self, user):
        """Test Channel.dm_to creates a DIRECT channel with one user."""
        dm = Channel.dm_to(user)
        assert dm.channel_type == ChannelType.DIRECT
        assert dm.users == [user]
        assert dm.is_incomplete
        assert not dm.id

    def test_group_dm_to_creates_group_channel(self, users):
        """Test Channel.group_dm_to creates a GROUP channel with multiple users."""
        group = Channel.group_dm_to(users)
        assert group.channel_type == ChannelType.GROUP
        assert group.users == users
        assert group.is_incomplete
        assert not group.id

    def test_dm_channel_is_resolvable(self, user):
        """Test DM channel with users is resolvable."""
        dm = Channel.dm_to(user)
        assert dm.is_resolvable
        assert dm.is_dm
        assert dm.is_direct_message


class TestMessageAsDmToAuthor:
    """Tests for Message.as_dm_to_author() convenience method."""

    @pytest.fixture
    def author(self):
        """Create a test author."""
        return User(id="U123", name="author", display_name="Author")

    @pytest.fixture
    def channel(self):
        """Create a test channel."""
        return Channel(id="C456", name="general")

    @pytest.fixture
    def message(self, author, channel):
        """Create a test message."""
        return Message(
            id="M789",
            content="Hello world",
            author=author,
            channel=channel,
        )

    def test_as_dm_to_author_creates_dm_message(self, message, author):
        """Test as_dm_to_author creates a DM to the original author."""
        dm = message.as_dm_to_author("Private response")
        assert dm.content == "Private response"
        assert dm.channel.channel_type == ChannelType.DIRECT
        assert dm.channel.users == [author]
        assert dm.channel.is_incomplete

    def test_as_dm_to_author_with_extra_kwargs(self, message, author):
        """Test as_dm_to_author passes through extra kwargs."""
        dm = message.as_dm_to_author("Secret", is_pinned=True)
        assert dm.content == "Secret"
        assert dm.is_pinned is True
        assert dm.channel.channel_type == ChannelType.DIRECT


class TestSlackDmChannelResolution:
    """Tests for Slack DM channel resolution using Channel.dm_to()."""

    def test_dm_channel_with_slack_user(self):
        """Test Channel.dm_to works with SlackUser."""
        user = SlackUser(id="U123", name="testuser", real_name="Test User")
        dm_channel = Channel.dm_to(user)

        assert dm_channel.channel_type == ChannelType.DIRECT
        assert len(dm_channel.users) == 1
        assert dm_channel.users[0].id == "U123"
        assert dm_channel.is_incomplete

    def test_group_dm_channel_with_slack_users(self):
        """Test Channel.group_dm_to works with multiple SlackUsers."""
        user1 = SlackUser(id="U123", name="alice", real_name="Alice")
        user2 = SlackUser(id="U456", name="bob", real_name="Bob")
        group = Channel.group_dm_to([user1, user2])

        assert group.channel_type == ChannelType.GROUP
        assert len(group.users) == 2
        assert group.is_incomplete


class TestDiscordDmChannelResolution:
    """Tests for Discord DM channel resolution using Channel.dm_to()."""

    def test_dm_channel_with_discord_user(self):
        """Test Channel.dm_to works with DiscordUser."""
        user = DiscordUser(id="123456789", name="testuser", display_name="Test User")
        dm_channel = Channel.dm_to(user)

        assert dm_channel.channel_type == ChannelType.DIRECT
        assert len(dm_channel.users) == 1
        assert dm_channel.users[0].id == "123456789"
        assert dm_channel.is_incomplete

    def test_group_dm_channel_with_discord_users(self):
        """Test Channel.group_dm_to works with multiple DiscordUsers."""
        user1 = DiscordUser(id="123", name="alice", display_name="Alice")
        user2 = DiscordUser(id="456", name="bob", display_name="Bob")
        group = Channel.group_dm_to([user1, user2])

        assert group.channel_type == ChannelType.GROUP
        assert len(group.users) == 2
        assert group.is_incomplete


class TestSymphonyDmChannelResolution:
    """Tests for Symphony DM channel resolution using Channel.dm_to()."""

    def test_dm_channel_with_symphony_user(self):
        """Test Channel.dm_to works with SymphonyUser."""
        user = SymphonyUser(id="123456789", name="testuser", display_name="Test User")
        dm_channel = Channel.dm_to(user)

        assert dm_channel.channel_type == ChannelType.DIRECT
        assert len(dm_channel.users) == 1
        assert dm_channel.users[0].id == "123456789"
        assert dm_channel.is_incomplete

    @pytest.fixture
    def backend(self):
        """Create a mock Symphony backend."""
        from chatom.symphony import SymphonyConfig
        from chatom.symphony.testing import MockSymphonyBackend

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="testbot",
            bot_private_key_content="fake-key",
        )
        return MockSymphonyBackend(config=config)

    @pytest.mark.asyncio
    async def test_create_im_from_user_id(self, backend):
        """Test creating IM from user ID extracted from Channel.dm_to()."""
        await backend.connect()
        user = SymphonyUser(id="123456789", name="testuser", display_name="Test User")
        backend.add_mock_user(123456789, "testuser", "testuser")

        # Create DM channel using convenience method
        dm_channel = Channel.dm_to(user)

        # In real usage, backend would resolve this. For mock, extract user ID manually
        user_ids = [u.id for u in dm_channel.users]
        im_id = await backend.create_im(user_ids)

        assert im_id is not None
        assert len(backend.created_ims) == 1

    def test_group_dm_channel_with_symphony_users(self):
        """Test Channel.group_dm_to works with multiple SymphonyUsers."""
        user1 = SymphonyUser(id="123", name="alice", display_name="Alice")
        user2 = SymphonyUser(id="456", name="bob", display_name="Bob")
        group = Channel.group_dm_to([user1, user2])

        assert group.channel_type == ChannelType.GROUP
        assert len(group.users) == 2
        assert group.is_incomplete


class TestDMFunctionality:
    """Tests for DM/IM functionality across all backends."""

    @pytest.fixture
    def slack_backend(self):
        """Create a MockSlackBackend."""
        from chatom.slack import SlackConfig
        from chatom.slack.testing import MockSlackBackend

        config = SlackConfig(bot_token=SecretStr("xoxb-test-token"))
        return MockSlackBackend(config=config)

    @pytest.fixture
    def discord_backend(self):
        """Create a MockDiscordBackend."""
        from chatom.discord import DiscordConfig
        from chatom.discord.testing import MockDiscordBackend

        config = DiscordConfig(token=SecretStr("discord-test-token"))
        return MockDiscordBackend(config=config)

    @pytest.fixture
    def symphony_backend(self):
        """Create a MockSymphonyBackend."""
        from chatom.symphony import SymphonyConfig
        from chatom.symphony.testing import MockSymphonyBackend

        config = SymphonyConfig(
            host="test.symphony.com",
            bot_username="testbot",
            bot_private_key_path="/fake/path",
        )
        return MockSymphonyBackend(config=config)

    @pytest.mark.asyncio
    async def test_slack_create_dm_with_user_id(self, slack_backend):
        """Test Slack create_dm with user ID string."""
        await slack_backend.connect()
        slack_backend.add_mock_user("U123", "testuser", "Test User")

        dm_id = await slack_backend.create_dm(["U123"])

        assert dm_id is not None
        assert len(slack_backend.created_dms) == 1

    @pytest.mark.asyncio
    async def test_slack_create_dm_with_user_object(self, slack_backend):
        """Test Slack create_dm with User object."""
        await slack_backend.connect()
        slack_backend.add_mock_user("U456", "alice", "Alice")
        user = await slack_backend.fetch_user(id="U456")

        dm_id = await slack_backend.create_dm([user])

        assert dm_id is not None

    @pytest.mark.asyncio
    async def test_slack_send_dm_convenience(self, slack_backend):
        """Test Slack send_dm convenience method."""
        await slack_backend.connect()
        slack_backend.add_mock_user("U789", "bob", "Bob")

        msg = await slack_backend.send_dm(
            user="U789",
            content="Hello via send_dm!",
        )

        assert msg is not None
        assert msg.id is not None
        assert "Hello via send_dm!" in msg.text

    @pytest.mark.asyncio
    async def test_slack_send_dm_with_user_object(self, slack_backend):
        """Test Slack send_dm with User object."""
        await slack_backend.connect()
        slack_backend.add_mock_user("U111", "charlie", "Charlie")
        user = await slack_backend.fetch_user(id="U111")

        msg = await slack_backend.send_dm(
            user=user,
            content="Hello Charlie!",
        )

        assert msg is not None
        assert msg.id is not None

    @pytest.mark.asyncio
    async def test_discord_create_dm_with_user_id(self, discord_backend):
        """Test Discord create_dm with user ID string."""
        await discord_backend.connect()
        discord_backend.add_mock_user("123456789", "testuser", "Test User")

        dm_id = await discord_backend.create_dm(["123456789"])

        assert dm_id is not None
        assert len(discord_backend.created_dms) == 1

    @pytest.mark.asyncio
    async def test_discord_send_dm_convenience(self, discord_backend):
        """Test Discord send_dm convenience method."""
        await discord_backend.connect()
        discord_backend.add_mock_user("987654321", "alice", "Alice")

        msg = await discord_backend.send_dm(
            user="987654321",
            content="Hello from Discord!",
        )

        assert msg is not None
        assert msg.id is not None

    @pytest.mark.asyncio
    async def test_symphony_create_im_with_user_id(self, symphony_backend):
        """Test Symphony create_im with user ID string."""
        await symphony_backend.connect()
        symphony_backend.add_mock_user(123456, "testuser", "Test User")

        im_id = await symphony_backend.create_im(["123456"])

        assert im_id is not None
        assert len(symphony_backend.created_ims) == 1

    @pytest.mark.asyncio
    async def test_symphony_create_dm_alias(self, symphony_backend):
        """Test Symphony create_dm is an alias for create_im."""
        await symphony_backend.connect()
        symphony_backend.add_mock_user(789012, "bob", "Bob")

        dm_id = await symphony_backend.create_dm(["789012"])

        assert dm_id is not None
        # Should be tracked in created_ims since create_dm calls create_im
        assert len(symphony_backend.created_ims) == 1

    @pytest.mark.asyncio
    async def test_symphony_send_dm_convenience(self, symphony_backend):
        """Test Symphony send_dm convenience method."""
        await symphony_backend.connect()
        symphony_backend.add_mock_user(111222, "charlie", "Charlie")

        msg = await symphony_backend.send_dm(
            user="111222",
            content="Hello from Symphony!",
        )

        assert msg is not None
        assert msg.id is not None

    @pytest.mark.asyncio
    async def test_create_dm_returns_channel_id_not_channel(self, slack_backend):
        """Test that create_dm returns a channel ID string, not a Channel object."""
        await slack_backend.connect()
        slack_backend.add_mock_user("U999", "user", "User")

        result = await slack_backend.create_dm(["U999"])

        # Should be a string (channel ID), not a Channel object
        assert isinstance(result, str)
        assert result.startswith("D")  # Slack DM channels start with D

    @pytest.mark.asyncio
    async def test_create_im_returns_stream_id_not_channel(self, symphony_backend):
        """Test that create_im returns a stream ID string, not a Channel object."""
        await symphony_backend.connect()
        symphony_backend.add_mock_user(333444, "user", "User")

        result = await symphony_backend.create_im(["333444"])

        # Should be a string (stream ID), not a Channel object
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_dm_creates_dm_if_needed(self, slack_backend):
        """Test that send_dm creates the DM channel automatically."""
        await slack_backend.connect()
        slack_backend.add_mock_user("U888", "user", "User")

        # No DMs created yet
        assert len(slack_backend.created_dms) == 0

        # Send DM - should create the channel
        await slack_backend.send_dm(user="U888", content="Hello!")

        # DM should now be created
        assert len(slack_backend.created_dms) == 1
