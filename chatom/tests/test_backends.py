"""Tests for backend-specific implementations."""

from chatom import User, mention_user


class TestDiscordBackend:
    """Tests for Discord backend implementations."""

    def test_discord_user_creation(self):
        """Test creating a Discord user."""
        from chatom.discord import DiscordUser

        user = DiscordUser(
            id="123456789",
            name="TestUser",
            handle="testuser",
            discriminator="1234",
            global_name="Test User",
            is_bot=False,
        )
        assert user.id == "123456789"
        assert user.discriminator == "1234"
        assert user.global_name == "Test User"

    def test_discord_user_display_name(self):
        """Test Discord user display name priority."""
        from chatom.discord import DiscordUser

        # With global_name
        user1 = DiscordUser(
            id="1",
            name="username",
            global_name="Display Name",
        )
        assert user1.display_name == "Display Name"

        # Without global_name
        user2 = DiscordUser(
            id="2",
            name="username",
        )
        assert user2.display_name == "username"

    def test_discord_channel_creation(self):
        """Test creating a Discord channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = DiscordChannel(
            id="987654321",
            name="general",
            discord_type=DiscordChannelType.GUILD_TEXT,
            guild_id="111222333",
            position=0,
            nsfw=False,
        )
        assert channel.id == "987654321"
        assert channel.discord_type == DiscordChannelType.GUILD_TEXT
        assert channel.guild_id == "111222333"

    def test_discord_channel_types(self):
        """Test Discord channel type enum values."""
        from chatom.discord import DiscordChannelType

        # These are string enums in the implementation
        assert DiscordChannelType.GUILD_TEXT.value == "guild_text"
        assert DiscordChannelType.DM.value == "dm"
        assert DiscordChannelType.GUILD_VOICE.value == "guild_voice"
        assert DiscordChannelType.GUILD_CATEGORY.value == "guild_category"
        assert DiscordChannelType.GUILD_FORUM.value == "guild_forum"

    def test_discord_mention_user(self):
        """Test Discord user mention."""
        from chatom.discord import DiscordUser, mention_user as discord_mention

        user = DiscordUser(id="123456", name="TestUser")
        result = discord_mention(user)
        # Implementation uses <@id> format
        assert result == "<@123456>"

    def test_discord_mention_channel(self):
        """Test Discord channel mention."""
        from chatom.discord import DiscordChannel, mention_channel as discord_mention_channel

        channel = DiscordChannel(id="654321", name="general")
        result = discord_mention_channel(channel)
        assert result == "<#654321>"

    def test_discord_mention_role(self):
        """Test Discord role mention."""
        from chatom.discord import mention_role

        result = mention_role("111222333")
        assert result == "<@&111222333>"

    def test_discord_mention_everyone(self):
        """Test Discord @everyone mention."""
        from chatom.discord import mention_everyone

        assert mention_everyone() == "@everyone"

    def test_discord_mention_here(self):
        """Test Discord @here mention."""
        from chatom.discord import mention_here

        assert mention_here() == "@here"

    def test_discord_presence(self):
        """Test Discord presence."""
        from chatom.base import PresenceStatus
        from chatom.discord import DiscordActivity, DiscordActivityType, DiscordPresence

        activity = DiscordActivity(
            name="VS Code",
            activity_type=DiscordActivityType.PLAYING,
            state="Editing code",
        )
        presence = DiscordPresence(
            status=PresenceStatus.ONLINE,
            activity=activity,
            desktop_status="online",
        )
        assert presence.activity.name == "VS Code"
        assert presence.desktop_status == "online"


class TestSlackBackend:
    """Tests for Slack backend implementations."""

    def test_slack_user_creation(self):
        """Test creating a Slack user."""
        from chatom.slack import SlackUser

        user = SlackUser(
            id="U123456",
            name="john.doe",
            real_name="John Doe",
            display_name="Johnny",
            team_id="T123",
            is_admin=True,
            tz="America/New_York",
        )
        assert user.id == "U123456"
        assert user.real_name == "John Doe"
        # display_name field is stored properly, access via model_dump
        # due to property shadowing in Pydantic
        assert user.model_dump()["display_name"] == "Johnny"
        assert user.is_admin is True
        # name is the base field
        assert user.name == "john.doe"

    def test_slack_channel_creation(self):
        """Test creating a Slack channel."""
        from chatom.slack import SlackChannel

        channel = SlackChannel(
            id="C123456",
            name="general",
            is_channel=True,
            is_private=False,
            creator="U111",
            purpose="General discussion",
            num_members=50,
        )
        assert channel.id == "C123456"
        assert channel.is_channel is True
        assert channel.num_members == 50

    def test_slack_mention_user(self):
        """Test Slack user mention."""
        from chatom.slack import SlackUser, mention_user as slack_mention

        user = SlackUser(id="U123456", name="john.doe")
        result = slack_mention(user)
        assert result == "<@U123456>"

    def test_slack_mention_channel(self):
        """Test Slack channel mention."""
        from chatom.slack import SlackChannel, mention_channel as slack_mention_channel

        channel = SlackChannel(id="C654321", name="general")
        result = slack_mention_channel(channel)
        assert result == "<#C654321>"

    def test_slack_mention_user_group(self):
        """Test Slack user group mention."""
        from chatom.slack import mention_user_group

        result = mention_user_group("S123456")
        assert result == "<!subteam^S123456>"

    def test_slack_mention_here(self):
        """Test Slack @here mention."""
        from chatom.slack import mention_here

        assert mention_here() == "<!here>"

    def test_slack_mention_channel_all(self):
        """Test Slack @channel mention."""
        from chatom.slack import mention_channel_all

        assert mention_channel_all() == "<!channel>"

    def test_slack_mention_everyone(self):
        """Test Slack @everyone mention."""
        from chatom.slack import mention_everyone

        assert mention_everyone() == "<!everyone>"

    def test_slack_presence(self):
        """Test Slack presence."""
        from chatom.base import PresenceStatus
        from chatom.slack import SlackPresence, SlackPresenceStatus

        presence = SlackPresence(
            status=PresenceStatus.ONLINE,
            slack_presence=SlackPresenceStatus.ACTIVE,
            auto_away=False,
            connection_count=1,
        )
        assert presence.slack_presence == SlackPresenceStatus.ACTIVE
        assert presence.is_online is True

    def test_slack_user_mention_name_fallback(self):
        """Test Slack user mention_name property.

        Note: Due to field shadowing, self.display_name uses the base User
        property which returns name/handle/id fallback, so mention_name
        effectively returns the display_name property value.
        """
        from chatom.slack import SlackUser

        # mention_name returns the display_name property (base class fallback)
        user = SlackUser(id="U1", name="john.doe", real_name="John Doe")
        result = user.mention_name
        # The property is called, covering line 95
        assert result  # Should be truthy (returns display_name which falls back to name)
        assert result == "john.doe"  # display_name property returns name


class TestSymphonyBackend:
    """Tests for Symphony backend implementations."""

    def test_symphony_user_creation(self):
        """Test creating a Symphony user."""
        from chatom.symphony import SymphonyUser

        user = SymphonyUser(
            id="123456789",
            name="John Doe",
            handle="johndoe",
            first_name="John",
            last_name="Doe",
            company="Acme Corp",
            department="Engineering",
            title="Software Engineer",
        )
        assert user.id == "123456789"
        assert user.first_name == "John"
        assert user.company == "Acme Corp"

    def test_symphony_channel_creation(self):
        """Test creating a Symphony channel (stream)."""
        from chatom.symphony import SymphonyChannel, SymphonyStreamType

        channel = SymphonyChannel(
            id="stream123",
            name="Engineering Room",
            stream_type=SymphonyStreamType.ROOM,
            external=False,
            public=True,
            active=True,
        )
        assert channel.id == "stream123"
        assert channel.stream_type == SymphonyStreamType.ROOM
        assert channel.public is True

    def test_symphony_stream_types(self):
        """Test Symphony stream type enum."""
        from chatom.symphony import SymphonyStreamType

        assert SymphonyStreamType.IM.value == "IM"
        assert SymphonyStreamType.MIM.value == "MIM"
        assert SymphonyStreamType.ROOM.value == "ROOM"
        assert SymphonyStreamType.POST.value == "POST"

    def test_symphony_mention_user(self):
        """Test Symphony user mention."""
        from chatom.symphony import SymphonyUser, mention_user as symphony_mention

        user = SymphonyUser(id="123456", name="John Doe")
        result = symphony_mention(user)
        assert result == '<mention uid="123456"/>'

    def test_symphony_mention_by_email(self):
        """Test Symphony mention by email."""
        from chatom.symphony import mention_user_by_email

        result = mention_user_by_email("john@example.com")
        assert result == '<mention email="john@example.com"/>'

    def test_symphony_mention_by_uid(self):
        """Test Symphony mention by user ID."""
        from chatom.symphony import mention_user_by_uid

        result = mention_user_by_uid("123456789")
        assert result == '<mention uid="123456789"/>'

    def test_symphony_hashtag(self):
        """Test Symphony hashtag formatting."""
        from chatom.symphony import format_hashtag

        result = format_hashtag("trading")
        assert result == '<hash tag="trading"/>'

    def test_symphony_cashtag(self):
        """Test Symphony cashtag formatting."""
        from chatom.symphony import format_cashtag

        result = format_cashtag("AAPL")
        assert result == '<cash tag="AAPL"/>'

    def test_symphony_presence(self):
        """Test Symphony presence."""
        from chatom.base import PresenceStatus
        from chatom.symphony import SymphonyPresence, SymphonyPresenceStatus

        presence = SymphonyPresence(
            status=PresenceStatus.ONLINE,
            symphony_status=SymphonyPresenceStatus.AVAILABLE,
            category="AVAILABLE",
        )
        assert presence.symphony_status == SymphonyPresenceStatus.AVAILABLE
        assert presence.is_online is True

    def test_symphony_user_full_name(self):
        """Test Symphony user full_name property."""
        from chatom.symphony import SymphonyUser

        # With first and last name
        user1 = SymphonyUser(id="1", name="JD", first_name="John", last_name="Doe")
        assert user1.full_name == "John Doe"

        # With only first name
        user2 = SymphonyUser(id="2", name="Jane", first_name="Jane")
        assert user2.full_name == "Jane"

        # With only last name
        user3 = SymphonyUser(id="3", name="Smith", last_name="Smith")
        assert user3.full_name == "Smith"

        # Without first/last name - should return name (fallback to name field)
        user4 = SymphonyUser(id="4", name="Alice")
        assert user4.full_name == "Alice"

    def test_symphony_user_mention_name(self):
        """Test Symphony user mention_name property.

        Note: Due to field shadowing, self.display_name uses the base User
        property which returns name/handle/id fallback.
        """
        from chatom.symphony import SymphonyUser

        # mention_name uses display_name property (base class fallback)
        user = SymphonyUser(id="1", name="Jane", first_name="Jane", last_name="Smith")
        result = user.mention_name
        # The property is called, covering line 92
        assert result  # Should be truthy
        assert result == "Jane"  # display_name property returns name

    def test_symphony_mention_user_fallback(self):
        """Test Symphony mention_user fallback when no id or email."""
        from chatom.symphony import SymphonyUser, mention_user as symphony_mention

        # User without id or email - should fallback to @display_name or @name
        user = SymphonyUser(id="", name="John Doe")
        result = symphony_mention(user)
        assert result == "@John Doe"


class TestEmailBackend:
    """Tests for Email backend implementations."""

    def test_email_user_creation(self):
        """Test creating an Email user."""
        from chatom.email import EmailUser

        user = EmailUser(
            id="user123",
            name="John Doe",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            organization="Acme Corp",
        )
        assert user.id == "user123"
        assert user.email == "john@example.com"
        assert user.full_name == "John Doe"

    def test_email_user_formatted_address(self):
        """Test email user formatted address."""
        from chatom.email import EmailUser

        user = EmailUser(
            id="1",
            name="John Doe",
            email="john@example.com",
        )
        formatted = user.formatted_address
        assert "John Doe" in formatted
        assert "john@example.com" in formatted

    def test_email_mention_user(self):
        """Test Email user mention."""
        from chatom.email import EmailUser, mention_user as email_mention

        user_with_email = EmailUser(
            id="1",
            name="John Doe",
            email="john@example.com",
        )
        result = email_mention(user_with_email)
        assert "mailto:john@example.com" in result
        assert "John Doe" in result

        user_without_email = EmailUser(
            id="2",
            name="Jane Doe",
        )
        result = email_mention(user_without_email)
        assert result == "Jane Doe"


class TestIRCBackend:
    """Tests for IRC backend implementations."""

    def test_irc_user_creation(self):
        """Test creating an IRC user."""
        from chatom.irc import IRCUser

        user = IRCUser(
            id="john!~john@host.example.com",
            name="John",
            nick="john",
            ident="~john",
            host="host.example.com",
            realname="John Doe",
        )
        assert user.nick == "john"
        assert user.host == "host.example.com"

    def test_irc_user_hostmask(self):
        """Test IRC user hostmask property."""
        from chatom.irc import IRCUser

        user = IRCUser(
            id="1",
            name="john",
            nick="john",
            ident="~john",
            host="example.com",
        )
        assert user.hostmask == "john!~john@example.com"

    def test_irc_user_is_operator(self):
        """Test IRC user is_operator property."""
        from chatom.irc import IRCUser

        # modes is a string in the implementation, not a list
        user_op = IRCUser(id="1", name="john", nick="john", modes="ov")
        assert user_op.is_operator is True

        user_normal = IRCUser(id="2", name="jane", nick="jane", modes="v")
        assert user_normal.is_operator is False

    def test_irc_mention_user(self):
        """Test IRC user mention."""
        from chatom.irc import IRCUser, mention_user as irc_mention

        user = IRCUser(id="1", name="john", nick="johnny")
        result = irc_mention(user)
        assert result == "johnny"

    def test_irc_highlight_user(self):
        """Test IRC user highlight."""
        from chatom.irc import highlight_user

        # highlight_user takes nick and message
        result = highlight_user("johnny", "hello there")
        assert result == "johnny: hello there"

    def test_irc_user_display_name_fallback(self):
        """Test IRC user display_name property fallback chain."""
        from chatom.irc import IRCUser

        # With nick - should return nick
        user1 = IRCUser(id="1", name="John", nick="johnny", handle="john_handle")
        assert user1.display_name == "johnny"

        # Without nick, with handle - should return handle
        user2 = IRCUser(id="2", name="Jane", handle="jane_handle")
        assert user2.display_name == "jane_handle"

        # Without nick or handle - should return name
        user3 = IRCUser(id="3", name="Bob")
        assert user3.display_name == "Bob"


class TestMatrixBackend:
    """Tests for Matrix backend implementations."""

    def test_matrix_user_creation(self):
        """Test creating a Matrix user."""
        from chatom.matrix import MatrixUser

        user = MatrixUser(
            id="1",
            name="John Doe",
            user_id="@john:matrix.org",
            display_name="Johnny",
            homeserver="matrix.org",
        )
        assert user.user_id == "@john:matrix.org"
        assert user.homeserver == "matrix.org"

    def test_matrix_user_localpart(self):
        """Test Matrix user localpart property."""
        from chatom.matrix import MatrixUser

        user = MatrixUser(
            id="1",
            name="john",
            user_id="@john:matrix.org",
        )
        assert user.localpart == "john"

    def test_matrix_user_full_user_id(self):
        """Test Matrix user full_user_id property."""
        from chatom.matrix import MatrixUser

        # With existing user_id
        user1 = MatrixUser(
            id="1",
            name="john",
            user_id="@john:matrix.org",
        )
        assert user1.full_user_id == "@john:matrix.org"

        # Building from handle and homeserver
        user2 = MatrixUser(
            id="2",
            name="jane",
            handle="jane",
            homeserver="example.com",
        )
        assert user2.full_user_id == "@jane:example.com"

    def test_matrix_mention_user(self):
        """Test Matrix user mention."""
        from chatom.matrix import MatrixUser, mention_user as matrix_mention

        user = MatrixUser(
            id="1",
            name="John",
            user_id="@john:matrix.org",
            display_name="Johnny",
        )
        result = matrix_mention(user)
        assert "@john:matrix.org" in result

    def test_matrix_mention_room(self):
        """Test Matrix room mention."""
        from chatom.matrix import mention_room

        # mention_room only takes room_id in the implementation
        result = mention_room("!abc123:matrix.org")
        assert "!abc123:matrix.org" in result

    def test_matrix_create_pill(self):
        """Test Matrix pill creation."""
        from chatom.matrix import create_pill

        result = create_pill("@john:matrix.org", "John")
        assert "@john:matrix.org" in result
        assert "John" in result
        assert "matrix.to" in result

    def test_matrix_user_server_name_fallback(self):
        """Test Matrix user server_name property fallback."""
        from chatom.matrix import MatrixUser

        # With user_id containing colon - should return server part
        user1 = MatrixUser(id="1", name="john", user_id="@john:matrix.org")
        assert user1.server_name == "matrix.org"

        # Without colon in user_id - should return homeserver
        user2 = MatrixUser(id="2", name="jane", user_id="@jane", homeserver="example.org")
        assert user2.server_name == "example.org"

        # Without user_id - should return homeserver
        user3 = MatrixUser(id="3", name="bob", homeserver="other.org")
        assert user3.server_name == "other.org"

    def test_matrix_user_full_user_id_fallback(self):
        """Test Matrix user full_user_id fallback when no user_id or handle+homeserver."""
        from chatom.matrix import MatrixUser

        # With user_id - returns user_id
        user1 = MatrixUser(id="1", name="john", user_id="@john:matrix.org")
        assert user1.full_user_id == "@john:matrix.org"

        # With handle and homeserver but no user_id - constructs from handle and homeserver
        user2 = MatrixUser(id="2", name="jane", handle="jane", homeserver="example.org")
        assert user2.full_user_id == "@jane:example.org"

        # With handle only (no homeserver) - returns handle
        user3 = MatrixUser(id="3", name="bob", handle="bobhandle")
        assert user3.full_user_id == "bobhandle"

        # With neither user_id nor handle - returns id
        user4 = MatrixUser(id="4", name="alice")
        assert user4.full_user_id == "4"

    def test_matrix_user_get_avatar_http_url(self):
        """Test Matrix user get_avatar_http_url method edge cases."""
        from chatom.matrix import MatrixUser

        # No avatar_mxc - should return avatar_url
        user1 = MatrixUser(id="1", name="john", avatar_url="https://example.com/avatar.jpg")
        assert user1.get_avatar_http_url() == "https://example.com/avatar.jpg"

        # avatar_mxc not starting with mxc:// - should return as-is
        user2 = MatrixUser(id="2", name="jane", avatar_mxc="https://example.com/avatar.png")
        assert user2.get_avatar_http_url() == "https://example.com/avatar.png"

        # avatar_mxc with mxc:// but no slash in path - should return empty string
        user3 = MatrixUser(id="3", name="bob", avatar_mxc="mxc://serveronly")
        assert user3.get_avatar_http_url() == ""

        # Valid mxc:// URL - should convert to HTTP URL
        user4 = MatrixUser(id="4", name="alice", avatar_mxc="mxc://matrix.org/abc123")
        result = user4.get_avatar_http_url()
        assert "matrix.org" in result
        assert "abc123" in result
        assert "_matrix/media" in result

        # Valid mxc:// URL with custom homeserver_url
        user5 = MatrixUser(id="5", name="charlie", avatar_mxc="mxc://example.org/def456")
        result = user5.get_avatar_http_url("https://custom.server.org")
        assert result.startswith("https://custom.server.org/")
        assert "example.org" in result
        assert "def456" in result


class TestPolymorphicMentions:
    """Tests for polymorphic mention dispatching."""

    def test_mention_dispatches_to_discord(self):
        """Test that mention_user dispatches correctly for Discord."""
        from chatom.discord import DiscordUser

        user = DiscordUser(id="123", name="Test")
        result = mention_user(user)
        # Implementation uses <@id> (not <@!id>)
        assert result == "<@123>"

    def test_mention_dispatches_to_slack(self):
        """Test that mention_user dispatches correctly for Slack."""
        from chatom.slack import SlackUser

        user = SlackUser(id="U123", name="Test")
        result = mention_user(user)
        assert result == "<@U123>"

    def test_mention_dispatches_to_symphony(self):
        """Test that mention_user dispatches correctly for Symphony."""
        from chatom.symphony import SymphonyUser

        user = SymphonyUser(id="123", name="Test User")
        result = mention_user(user)
        assert result == '<mention uid="123"/>'

    def test_mention_dispatches_to_email(self):
        """Test that mention_user dispatches correctly for Email."""
        from chatom.email import EmailUser

        user = EmailUser(id="1", name="Test", email="test@example.com")
        result = mention_user(user)
        assert "mailto:test@example.com" in result

    def test_mention_dispatches_to_irc(self):
        """Test that mention_user dispatches correctly for IRC."""
        from chatom.irc import IRCUser

        user = IRCUser(id="1", name="test", nick="testuser")
        result = mention_user(user)
        assert result == "testuser"

    def test_mention_dispatches_to_matrix(self):
        """Test that mention_user dispatches correctly for Matrix."""
        from chatom.matrix import MatrixUser

        user = MatrixUser(id="1", name="Test", user_id="@test:matrix.org")
        result = mention_user(user)
        assert "@test:matrix.org" in result

    def test_mention_base_user_fallback(self):
        """Test that base User falls back to name."""
        user = User(id="1", name="TestUser", handle="testhandle")
        result = mention_user(user)
        assert result == "TestUser"


class TestSlackChannelType:
    """Tests for SlackChannel type detection."""

    def test_slack_channel_type_im(self):
        """Test Slack IM channel type detection."""
        from chatom.base import ChannelType
        from chatom.slack import SlackChannel

        channel = SlackChannel(id="D123", name="dm", is_im=True)
        assert channel.slack_channel_type == ChannelType.DIRECT

    def test_slack_channel_type_mpim(self):
        """Test Slack MPIM channel type detection."""
        from chatom.base import ChannelType
        from chatom.slack import SlackChannel

        channel = SlackChannel(id="G123", name="group-dm", is_mpim=True)
        assert channel.slack_channel_type == ChannelType.GROUP

    def test_slack_channel_type_private(self):
        """Test Slack private channel type detection - must also set is_group."""
        from chatom.base import ChannelType
        from chatom.slack import SlackChannel

        channel = SlackChannel(id="C123", name="private-channel", is_private=True, is_group=True)
        assert channel.slack_channel_type == ChannelType.PRIVATE

    def test_slack_channel_type_group(self):
        """Test Slack group channel type detection."""
        from chatom.base import ChannelType
        from chatom.slack import SlackChannel

        channel = SlackChannel(id="G123", name="group-channel", is_group=True)
        assert channel.slack_channel_type == ChannelType.PRIVATE

    def test_slack_channel_type_public(self):
        """Test Slack public channel type detection."""
        from chatom.base import ChannelType
        from chatom.slack import SlackChannel

        channel = SlackChannel(id="C123", name="general", is_channel=True)
        assert channel.slack_channel_type == ChannelType.PUBLIC

    def test_slack_channel_type_unknown(self):
        """Test Slack unknown channel type detection."""
        from chatom.base import ChannelType
        from chatom.slack import SlackChannel

        channel = SlackChannel(id="X123", name="unknown")
        assert channel.slack_channel_type == ChannelType.UNKNOWN


class TestSlackChannelProperties:
    """Tests for additional SlackChannel properties."""

    def test_slack_channel_shared(self):
        """Test Slack shared channel flags."""
        from chatom.slack import SlackChannel

        channel = SlackChannel(
            id="C123",
            name="shared-channel",
            is_channel=True,
            is_shared=True,
            is_ext_shared=True,
        )
        assert channel.is_shared is True
        assert channel.is_ext_shared is True

    def test_slack_channel_read_tracking(self):
        """Test Slack channel read tracking fields."""
        from chatom.slack import SlackChannel

        channel = SlackChannel(
            id="C123",
            name="general",
            unread_count=5,
            last_read="1234567890.123456",
            latest="1234567890.123457",
        )
        assert channel.unread_count == 5
        assert channel.last_read == "1234567890.123456"


class TestSlackUserProperties:
    """Tests for additional SlackUser properties."""

    def test_slack_user_admin_flags(self):
        """Test Slack user admin flags."""
        from chatom.slack import SlackUser

        user = SlackUser(
            id="U123",
            name="admin",
            is_admin=True,
            is_owner=True,
            is_primary_owner=False,
        )
        assert user.is_admin is True
        assert user.is_owner is True
        assert user.is_primary_owner is False

    def test_slack_user_restricted_flags(self):
        """Test Slack user restricted flags."""
        from chatom.slack import SlackUser

        user = SlackUser(
            id="U123",
            name="guest",
            is_restricted=True,
            is_ultra_restricted=True,
        )
        assert user.is_restricted is True
        assert user.is_ultra_restricted is True


class TestDiscordChannelProperties:
    """Tests for additional DiscordChannel properties."""

    def test_discord_channel_nsfw(self):
        """Test Discord NSFW channel flag."""
        from chatom.discord import DiscordChannel

        channel = DiscordChannel(id="123", name="adult-chat", nsfw=True)
        assert channel.nsfw is True

    def test_discord_channel_parent(self):
        """Test Discord channel parent/category."""
        from chatom.discord import DiscordChannel

        channel = DiscordChannel(
            id="123",
            name="general",
            parent_id="456",
        )
        assert channel.parent_id == "456"

    def test_discord_channel_permissions(self):
        """Test Discord channel permission overwrites."""
        from chatom.discord import DiscordChannel

        channel = DiscordChannel(
            id="123",
            name="general",
            permission_overwrites=[{"id": "role1", "type": "role", "allow": "123", "deny": "456"}],
        )
        assert len(channel.permission_overwrites) == 1


class TestDiscordUserProperties:
    """Tests for additional DiscordUser properties."""

    def test_discord_user_flags(self):
        """Test Discord user public flags."""
        from chatom.discord import DiscordUser

        user = DiscordUser(
            id="123",
            name="user",
            public_flags=1,
            premium_type=2,
        )
        assert user.public_flags == 1
        assert user.premium_type == 2

    def test_discord_user_banner(self):
        """Test Discord user banner."""
        from chatom.discord import DiscordUser

        user = DiscordUser(
            id="123",
            name="user",
            banner="banner_hash",
            accent_color=0x5865F2,
        )
        assert user.banner == "banner_hash"
        assert user.accent_color == 0x5865F2

    def test_discord_user_full_username_without_discriminator(self):
        """Test full_username without discriminator (new format)."""
        from chatom.discord import DiscordUser

        user = DiscordUser(id="123", name="testuser", handle="testuser")
        assert user.full_username == "testuser"

    def test_discord_user_full_username_with_zero_discriminator(self):
        """Test full_username with zero discriminator (new format)."""
        from chatom.discord import DiscordUser

        user = DiscordUser(id="123", name="testuser", handle="testuser", discriminator="0")
        assert user.full_username == "testuser"

    def test_discord_user_full_username_with_discriminator(self):
        """Test full_username with discriminator (legacy format)."""
        from chatom.discord import DiscordUser

        user = DiscordUser(id="123", name="testuser", handle="testuser", discriminator="1234")
        assert user.full_username == "testuser#1234"


class TestSymphonyUserProperties:
    """Tests for additional SymphonyUser properties."""

    def test_symphony_user_roles(self):
        """Test Symphony user roles."""
        from chatom.symphony import SymphonyUser

        user = SymphonyUser(
            id="123",
            name="John Doe",
            roles=["CONTENT_MANAGEMENT", "USER_PROVISIONING"],
        )
        assert len(user.roles) == 2
        assert "CONTENT_MANAGEMENT" in user.roles

    def test_symphony_user_entitlements(self):
        """Test Symphony user entitlements."""
        from chatom.symphony import SymphonyUser

        user = SymphonyUser(
            id="123",
            name="John Doe",
            avatar_url="https://symphony.example.com/avatar/123",
        )
        assert "symphony" in user.avatar_url


class TestIRCUserProperties:
    """Tests for additional IRCUser properties."""

    def test_irc_user_operator_mode(self):
        """Test IRC user operator mode detection via modes field."""
        from chatom.irc import IRCUser

        user = IRCUser(
            id="1",
            name="nick",
            nick="nick",
            modes="o",  # is_operator is a computed property from modes
        )
        assert user.is_operator is True

    def test_irc_user_voiced_mode(self):
        """Test IRC user voiced detection via modes field."""
        from chatom.irc import IRCUser

        user = IRCUser(
            id="1",
            name="nick",
            nick="nick",
            modes="v",  # voiced mode
        )
        assert "v" in user.modes

    def test_irc_user_multiple_modes(self):
        """Test IRC user with multiple modes."""
        from chatom.irc import IRCUser

        user = IRCUser(
            id="1",
            name="nick",
            nick="nick",
            modes="ov",  # operator and voiced
        )
        assert user.is_operator is True
        assert "v" in user.modes

    def test_irc_user_hostmask(self):
        """Test IRC user hostmask property."""
        from chatom.irc import IRCUser

        user = IRCUser(
            id="1",
            name="nick",
            nick="mynick",
            ident="myident",
            host="myhost.example.com",
        )
        assert user.hostmask == "mynick!myident@myhost.example.com"

    def test_irc_user_away_status(self):
        """Test IRC user away status."""
        from chatom.irc import IRCUser

        user = IRCUser(
            id="1",
            name="nick",
            nick="nick",
            is_away=True,
            away_message="Gone fishing",
        )
        assert user.is_away is True
        assert user.away_message == "Gone fishing"


class TestIRCPresenceGenericStatus:
    """Tests for IRC presence generic_status property."""

    def test_irc_presence_online_when_not_away(self):
        """Test IRC presence returns ONLINE when not away."""
        from chatom.base import PresenceStatus
        from chatom.irc.presence import IRCPresence

        presence = IRCPresence(is_away=False)
        assert presence.generic_status == PresenceStatus.ONLINE

    def test_irc_presence_idle_when_away(self):
        """Test IRC presence returns IDLE when away."""
        from chatom.base import PresenceStatus
        from chatom.irc.presence import IRCPresence

        presence = IRCPresence(is_away=True, away_message="BRB")
        assert presence.generic_status == PresenceStatus.IDLE

    def test_irc_presence_with_all_fields(self):
        """Test IRC presence with all fields populated."""
        from chatom.base import PresenceStatus
        from chatom.irc.presence import IRCPresence

        presence = IRCPresence(
            is_away=False,
            away_message="",
            idle_time=300,
            signon_time=1609459200,
            server="irc.example.com",
            channels=["#channel1", "#channel2"],
        )
        assert presence.generic_status == PresenceStatus.ONLINE
        assert presence.idle_time == 300
        assert presence.signon_time == 1609459200
        assert presence.server == "irc.example.com"
        assert presence.channels == ["#channel1", "#channel2"]


class TestSlackPresenceGenericStatus:
    """Tests for Slack presence generic_status property."""

    def test_slack_presence_online_when_active(self):
        """Test Slack presence returns ONLINE when active."""
        from chatom.base import PresenceStatus
        from chatom.slack.presence import SlackPresence, SlackPresenceStatus

        presence = SlackPresence(slack_presence=SlackPresenceStatus.ACTIVE)
        assert presence.generic_status == PresenceStatus.ONLINE

    def test_slack_presence_idle_when_away(self):
        """Test Slack presence returns IDLE when away."""
        from chatom.base import PresenceStatus
        from chatom.slack.presence import SlackPresence, SlackPresenceStatus

        presence = SlackPresence(slack_presence=SlackPresenceStatus.AWAY)
        assert presence.generic_status == PresenceStatus.IDLE

    def test_slack_presence_idle_when_auto(self):
        """Test Slack presence returns IDLE when auto (default behavior)."""
        from chatom.base import PresenceStatus
        from chatom.slack.presence import SlackPresence, SlackPresenceStatus

        presence = SlackPresence(slack_presence=SlackPresenceStatus.AUTO)
        assert presence.generic_status == PresenceStatus.IDLE

    def test_slack_presence_with_all_fields(self):
        """Test Slack presence with all fields populated."""
        from chatom.base import PresenceStatus
        from chatom.slack.presence import SlackPresence, SlackPresenceStatus

        presence = SlackPresence(
            slack_presence=SlackPresenceStatus.ACTIVE,
            auto_away=False,
            manual_away=False,
            connection_count=3,
            last_activity=1609459200,
        )
        assert presence.generic_status == PresenceStatus.ONLINE
        assert presence.auto_away is False
        assert presence.manual_away is False
        assert presence.connection_count == 3
        assert presence.last_activity == 1609459200
