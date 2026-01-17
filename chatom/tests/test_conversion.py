"""Tests for the type conversion and validation system."""

import pytest

from chatom import (
    # Backend constants
    DISCORD,
    EMAIL,
    IRC,
    MATRIX,
    SLACK,
    SYMPHONY,
    BackendNotFoundError,
    Channel,
    # Exceptions
    Presence,
    PresenceStatus,
    User,
    ValidationResult,
    # Conversion functions
    can_promote,
    demote,
    get_backend_type,
    get_base_type,
    list_backends_for_type,
    promote,
    validate_for_backend,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_validation_result_valid(self):
        """Test a valid ValidationResult."""
        result = ValidationResult(valid=True)
        assert result.valid
        assert bool(result) is True
        assert result.missing_required == []
        assert result.invalid_fields == {}
        assert result.warnings == []

    def test_validation_result_invalid(self):
        """Test an invalid ValidationResult."""
        result = ValidationResult(
            valid=False,
            missing_required=["field1"],
            invalid_fields={"field2": "invalid value"},
            warnings=["some warning"],
        )
        assert not result.valid
        assert bool(result) is False
        assert result.missing_required == ["field1"]
        assert result.invalid_fields == {"field2": "invalid value"}
        assert result.warnings == ["some warning"]

    def test_validation_result_repr(self):
        """Test ValidationResult string representation."""
        result = ValidationResult(valid=True)
        repr_str = repr(result)
        assert "valid=True" in repr_str
        assert "missing_required=" in repr_str


class TestRegistryFunctions:
    """Tests for type registry functions."""

    def test_get_backend_type_discord(self):
        """Test getting Discord backend type for User."""
        from chatom.discord import DiscordUser

        backend_type = get_backend_type(User, DISCORD)
        assert backend_type is DiscordUser

    def test_get_backend_type_slack(self):
        """Test getting Slack backend type for User."""
        from chatom.slack import SlackUser

        backend_type = get_backend_type(User, SLACK)
        assert backend_type is SlackUser

    def test_get_backend_type_symphony(self):
        """Test getting Symphony backend type for User."""
        from chatom.symphony import SymphonyUser

        backend_type = get_backend_type(User, SYMPHONY)
        assert backend_type is SymphonyUser

    def test_get_backend_type_email(self):
        """Test getting Email backend type for User."""
        from chatom.email import EmailUser

        backend_type = get_backend_type(User, EMAIL)
        assert backend_type is EmailUser

    def test_get_backend_type_irc(self):
        """Test getting IRC backend type for User."""
        from chatom.irc import IRCUser

        backend_type = get_backend_type(User, IRC)
        assert backend_type is IRCUser

    def test_get_backend_type_matrix(self):
        """Test getting Matrix backend type for User."""
        from chatom.matrix import MatrixUser

        backend_type = get_backend_type(User, MATRIX)
        assert backend_type is MatrixUser

    def test_get_backend_type_not_found(self):
        """Test getting backend type for unregistered type."""
        result = get_backend_type(User, "unknown_backend")
        assert result is None

    def test_get_base_type(self):
        """Test getting base type from backend type."""
        from chatom.discord import DiscordUser

        base_type = get_base_type(DiscordUser)
        assert base_type is User

    def test_list_backends_for_user(self):
        """Test listing backends for User type."""
        backends = list_backends_for_type(User)
        assert DISCORD in backends
        assert SLACK in backends
        assert SYMPHONY in backends
        assert EMAIL in backends
        assert IRC in backends
        assert MATRIX in backends

    def test_list_backends_for_channel(self):
        """Test listing backends for Channel type."""
        backends = list_backends_for_type(Channel)
        assert DISCORD in backends
        assert SLACK in backends
        assert SYMPHONY in backends


class TestValidateForBackend:
    """Tests for validate_for_backend function."""

    def test_validate_user_for_discord(self):
        """Test validating a User for Discord."""
        user = User(id="123", name="Test User", handle="testuser")
        result = validate_for_backend(user, DISCORD)
        assert result.valid

    def test_validate_user_for_slack(self):
        """Test validating a User for Slack."""
        user = User(id="U123", name="Test User")
        result = validate_for_backend(user, SLACK)
        assert result.valid

    def test_validate_user_for_symphony(self):
        """Test validating a User for Symphony."""
        user = User(id="123456789", name="Test User", email="test@example.com")
        result = validate_for_backend(user, SYMPHONY)
        assert result.valid

    def test_validate_for_unknown_backend(self):
        """Test validation fails for unknown backend."""
        user = User(id="123", name="Test")
        with pytest.raises(BackendNotFoundError):
            validate_for_backend(user, "nonexistent_backend")


class TestCanPromote:
    """Tests for can_promote function."""

    def test_can_promote_user_to_discord(self):
        """Test user can be promoted to Discord."""
        user = User(id="123", name="Test User")
        assert can_promote(user, DISCORD)

    def test_can_promote_user_to_slack(self):
        """Test user can be promoted to Slack."""
        user = User(id="U123", name="Test User")
        assert can_promote(user, SLACK)

    def test_can_promote_user_to_symphony(self):
        """Test user can be promoted to Symphony."""
        user = User(id="123456789", name="Test User")
        assert can_promote(user, SYMPHONY)

    def test_can_promote_channel_to_discord(self):
        """Test channel can be promoted to Discord."""
        channel = Channel(id="456", name="general")
        assert can_promote(channel, DISCORD)

    def test_can_promote_channel_to_slack(self):
        """Test channel can be promoted to Slack."""
        channel = Channel(id="C456", name="general")
        assert can_promote(channel, SLACK)


class TestPromote:
    """Tests for promote function."""

    def test_promote_user_to_discord(self):
        """Test promoting User to DiscordUser."""
        from chatom.discord import DiscordUser

        user = User(id="123456789", name="Test User", handle="testuser", is_bot=False)
        discord_user = promote(user, DISCORD)

        assert isinstance(discord_user, DiscordUser)
        assert discord_user.id == "123456789"
        assert discord_user.name == "Test User"
        assert discord_user.handle == "testuser"
        assert discord_user.is_bot is False
        # Discord-specific fields should have defaults
        assert discord_user.discriminator == "0"

    def test_promote_user_to_discord_with_extra_fields(self):
        """Test promoting User to DiscordUser with extra Discord fields."""
        from chatom.discord import DiscordUser

        user = User(id="123456789", name="Test User")
        discord_user = promote(
            user,
            DISCORD,
            discriminator="1234",
            global_name="Display Name",
            is_system=True,
        )

        assert isinstance(discord_user, DiscordUser)
        assert discord_user.id == "123456789"
        assert discord_user.discriminator == "1234"
        assert discord_user.global_name == "Display Name"
        assert discord_user.is_system is True

    def test_promote_user_to_slack(self):
        """Test promoting User to SlackUser."""
        from chatom.slack import SlackUser

        user = User(id="U123ABC", name="Test User", email="test@example.com")
        slack_user = promote(user, SLACK)

        assert isinstance(slack_user, SlackUser)
        assert slack_user.id == "U123ABC"
        assert slack_user.name == "Test User"
        assert slack_user.email == "test@example.com"
        # Slack-specific fields should have defaults
        assert slack_user.team_id == ""
        assert slack_user.is_admin is False

    def test_promote_user_to_slack_with_extra_fields(self):
        """Test promoting User to SlackUser with extra Slack fields."""
        from chatom.slack import SlackUser

        user = User(id="U123ABC", name="Test User")
        slack_user = promote(
            user,
            SLACK,
            team_id="T123",
            is_admin=True,
            real_name="Real Name",
            title="Engineer",
        )

        assert isinstance(slack_user, SlackUser)
        assert slack_user.team_id == "T123"
        assert slack_user.is_admin is True
        assert slack_user.real_name == "Real Name"
        assert slack_user.title == "Engineer"

    def test_promote_user_to_symphony(self):
        """Test promoting User to SymphonyUser."""
        from chatom.symphony import SymphonyUser

        user = User(id="123456789", name="Test User", email="test@example.com")
        symphony_user = promote(user, SYMPHONY)

        assert isinstance(symphony_user, SymphonyUser)
        assert symphony_user.id == "123456789"
        assert symphony_user.name == "Test User"
        # Symphony-specific fields should have defaults
        assert symphony_user.company == ""

    def test_promote_user_to_symphony_with_extra_fields(self):
        """Test promoting User to SymphonyUser with extra Symphony fields."""
        from chatom.symphony import SymphonyUser

        user = User(id="123456789", name="Test User")
        symphony_user = promote(
            user,
            SYMPHONY,
            first_name="Test",
            last_name="User",
            company="ACME Corp",
            department="Engineering",
        )

        assert isinstance(symphony_user, SymphonyUser)
        assert symphony_user.first_name == "Test"
        assert symphony_user.last_name == "User"
        assert symphony_user.company == "ACME Corp"
        assert symphony_user.department == "Engineering"

    def test_promote_user_to_email(self):
        """Test promoting User to EmailUser."""
        from chatom.email import EmailUser

        user = User(id="user@example.com", name="Test User", email="user@example.com")
        email_user = promote(user, EMAIL)

        assert isinstance(email_user, EmailUser)
        assert email_user.email == "user@example.com"

    def test_promote_user_to_irc(self):
        """Test promoting User to IRCUser."""
        from chatom.irc import IRCUser

        user = User(id="testuser", name="Test User", handle="testuser")
        irc_user = promote(user, IRC)

        assert isinstance(irc_user, IRCUser)
        assert irc_user.handle == "testuser"

    def test_promote_user_to_matrix(self):
        """Test promoting User to MatrixUser."""
        from chatom.matrix import MatrixUser

        user = User(id="@user:server.org", name="Test User", handle="user")
        matrix_user = promote(user, MATRIX)

        assert isinstance(matrix_user, MatrixUser)

    def test_promote_channel_to_discord(self):
        """Test promoting Channel to DiscordChannel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        channel = Channel(id="123456789", name="general", topic="General chat")
        discord_channel = promote(
            channel,
            DISCORD,
            guild_id="987654321",
            discord_type=DiscordChannelType.GUILD_TEXT,
        )

        assert isinstance(discord_channel, DiscordChannel)
        assert discord_channel.id == "123456789"
        assert discord_channel.name == "general"
        assert discord_channel.topic == "General chat"
        assert discord_channel.guild_id == "987654321"
        assert discord_channel.discord_type == DiscordChannelType.GUILD_TEXT

    def test_promote_channel_to_slack(self):
        """Test promoting Channel to SlackChannel."""
        from chatom.slack import SlackChannel

        channel = Channel(id="C123ABC", name="general")
        slack_channel = promote(channel, SLACK, is_channel=True, creator="U123", purpose="General channel")

        assert isinstance(slack_channel, SlackChannel)
        assert slack_channel.is_channel is True
        assert slack_channel.creator == "U123"
        assert slack_channel.purpose == "General channel"

    def test_promote_presence_to_discord(self):
        """Test promoting Presence to DiscordPresence."""
        from chatom.discord import DiscordPresence

        presence = Presence(status=PresenceStatus.ONLINE)
        discord_presence = promote(presence, DISCORD)

        assert isinstance(discord_presence, DiscordPresence)
        assert discord_presence.status == PresenceStatus.ONLINE

    def test_promote_to_unknown_backend_raises(self):
        """Test promoting to unknown backend raises error."""
        user = User(id="123", name="Test")
        with pytest.raises(BackendNotFoundError):
            promote(user, "unknown_backend")


class TestDemote:
    """Tests for demote function."""

    def test_demote_discord_user(self):
        """Test demoting DiscordUser to User."""
        from chatom.discord import DiscordUser

        discord_user = DiscordUser(
            id="123456789",
            name="Test User",
            handle="testuser",
            email="test@example.com",
            discriminator="1234",
            global_name="Display Name",
            is_system=True,
        )
        user = demote(discord_user)

        assert type(user) is User
        assert user.id == "123456789"
        assert user.name == "Test User"
        assert user.handle == "testuser"
        assert user.email == "test@example.com"
        # Discord-specific fields should be stripped
        assert not hasattr(user, "discriminator") or user.model_dump().get("discriminator") is None

    def test_demote_slack_user(self):
        """Test demoting SlackUser to User."""
        from chatom.slack import SlackUser

        slack_user = SlackUser(
            id="U123ABC",
            name="Test User",
            handle="testuser",
            team_id="T123",
            is_admin=True,
            real_name="Real Name",
        )
        user = demote(slack_user)

        assert type(user) is User
        assert user.id == "U123ABC"
        assert user.name == "Test User"

    def test_demote_symphony_user(self):
        """Test demoting SymphonyUser to User."""
        from chatom.symphony import SymphonyUser

        symphony_user = SymphonyUser(
            id="123456789",
            name="Test User",
            first_name="Test",
            last_name="User",
            company="ACME",
        )
        user = demote(symphony_user)

        assert type(user) is User
        assert user.id == "123456789"
        assert user.name == "Test User"

    def test_demote_email_user(self):
        """Test demoting EmailUser to User."""
        from chatom.email import EmailUser

        email_user = EmailUser(
            id="user@example.com",
            name="Test User",
            email="user@example.com",
            first_name="Test",
            last_name="User",
            organization="ACME",
        )
        user = demote(email_user)

        assert type(user) is User
        assert user.id == "user@example.com"
        assert user.email == "user@example.com"

    def test_demote_irc_user(self):
        """Test demoting IRCUser to User."""
        from chatom.irc import IRCUser

        irc_user = IRCUser(
            id="testuser",
            name="Test User",
            nick="testnick",
            ident="testident",
            host="test.host.com",
        )
        user = demote(irc_user)

        assert type(user) is User
        assert user.id == "testuser"

    def test_demote_matrix_user(self):
        """Test demoting MatrixUser to User."""
        from chatom.matrix import MatrixUser

        matrix_user = MatrixUser(
            id="@user:server.org",
            name="Test User",
            user_id="@user:server.org",
            homeserver="server.org",
        )
        user = demote(matrix_user)

        assert type(user) is User
        assert user.id == "@user:server.org"

    def test_demote_discord_channel(self):
        """Test demoting DiscordChannel to Channel."""
        from chatom.discord import DiscordChannel, DiscordChannelType

        discord_channel = DiscordChannel(
            id="123456789",
            name="general",
            topic="General chat",
            guild_id="987654321",
            discord_type=DiscordChannelType.GUILD_TEXT,
            position=5,
            nsfw=False,
        )
        channel = demote(discord_channel)

        assert type(channel) is Channel
        assert channel.id == "123456789"
        assert channel.name == "general"
        assert channel.topic == "General chat"

    def test_demote_base_type_returns_copy(self):
        """Test demoting a base type returns a copy."""
        user = User(id="123", name="Test")
        demoted = demote(user)

        assert type(demoted) is User
        assert demoted.id == "123"
        assert demoted is not user  # Should be a copy


class TestRoundTrip:
    """Tests for round-trip conversion (promote then demote)."""

    def test_roundtrip_user_discord(self):
        """Test User -> DiscordUser -> User roundtrip."""
        original = User(
            id="123",
            name="Test User",
            handle="testuser",
            email="test@example.com",
            is_bot=False,
        )

        # Promote
        discord_user = promote(original, DISCORD, discriminator="1234")
        assert discord_user.discriminator == "1234"

        # Demote back
        final = demote(discord_user)
        assert type(final) is User
        assert final.id == original.id
        assert final.name == original.name
        assert final.handle == original.handle
        assert final.email == original.email
        assert final.is_bot == original.is_bot

    def test_roundtrip_user_slack(self):
        """Test User -> SlackUser -> User roundtrip."""
        original = User(
            id="U123",
            name="Test User",
            handle="testuser",
            email="test@example.com",
        )

        # Promote
        slack_user = promote(original, SLACK, team_id="T123")
        assert slack_user.team_id == "T123"

        # Demote back
        final = demote(slack_user)
        assert type(final) is User
        assert final.id == original.id
        assert final.name == original.name

    def test_roundtrip_user_symphony(self):
        """Test User -> SymphonyUser -> User roundtrip."""
        original = User(id="123", name="Test User", email="test@example.com")

        # Promote
        symphony_user = promote(original, SYMPHONY, company="ACME")
        assert symphony_user.company == "ACME"

        # Demote back
        final = demote(symphony_user)
        assert type(final) is User
        assert final.id == original.id
        assert final.name == original.name

    def test_roundtrip_channel_discord(self):
        """Test Channel -> DiscordChannel -> Channel roundtrip."""
        original = Channel(id="456", name="general", topic="General discussion")

        # Promote
        discord_channel = promote(original, DISCORD, guild_id="123")
        assert discord_channel.guild_id == "123"

        # Demote back
        final = demote(discord_channel)
        assert type(final) is Channel
        assert final.id == original.id
        assert final.name == original.name
        assert final.topic == original.topic


class TestCrossBackendConversion:
    """Tests for converting between different backends."""

    def test_discord_to_slack_user(self):
        """Test converting DiscordUser -> User -> SlackUser."""
        from chatom.discord import DiscordUser
        from chatom.slack import SlackUser

        # Start with Discord user
        discord_user = DiscordUser(
            id="123456789",
            name="Test User",
            handle="testuser",
            email="test@example.com",
            discriminator="1234",
        )

        # Demote to base
        base_user = demote(discord_user)
        assert type(base_user) is User

        # Promote to Slack
        slack_user = promote(base_user, SLACK, team_id="T123")
        assert isinstance(slack_user, SlackUser)
        assert slack_user.id == "123456789"
        assert slack_user.name == "Test User"
        assert slack_user.team_id == "T123"

    def test_slack_to_symphony_user(self):
        """Test converting SlackUser -> User -> SymphonyUser."""
        from chatom.slack import SlackUser
        from chatom.symphony import SymphonyUser

        # Start with Slack user
        slack_user = SlackUser(
            id="U123",
            name="Test User",
            email="test@example.com",
            team_id="T123",
            real_name="Real Name",
        )

        # Demote to base
        base_user = demote(slack_user)

        # Promote to Symphony
        symphony_user = promote(base_user, SYMPHONY, company="ACME")
        assert isinstance(symphony_user, SymphonyUser)
        assert symphony_user.id == "U123"
        assert symphony_user.name == "Test User"
        assert symphony_user.company == "ACME"


class TestPresenceConversion:
    """Tests for Presence type conversions."""

    def test_promote_presence_to_slack(self):
        """Test promoting Presence to SlackPresence."""
        from chatom.slack import SlackPresence

        presence = Presence(status=PresenceStatus.ONLINE, status_text="Working")
        slack_presence = promote(presence, SLACK)

        assert isinstance(slack_presence, SlackPresence)
        assert slack_presence.status == PresenceStatus.ONLINE
        assert slack_presence.status_text == "Working"

    def test_promote_presence_to_symphony(self):
        """Test promoting Presence to SymphonyPresence."""
        from chatom.symphony import SymphonyPresence

        presence = Presence(status=PresenceStatus.DND)
        symphony_presence = promote(presence, SYMPHONY)

        assert isinstance(symphony_presence, SymphonyPresence)

    def test_demote_slack_presence(self):
        """Test demoting SlackPresence to Presence."""
        from chatom.slack import SlackPresence, SlackPresenceStatus

        slack_presence = SlackPresence(
            status=PresenceStatus.ONLINE,
            slack_presence=SlackPresenceStatus.ACTIVE,
            connection_count=5,
        )
        presence = demote(slack_presence)

        assert type(presence) is Presence
        assert presence.status == PresenceStatus.ONLINE


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_promote_already_promoted_user(self):
        """Test promoting an already-promoted user to a different backend."""
        from chatom.discord import DiscordUser
        from chatom.slack import SlackUser

        # Create a DiscordUser
        discord_user = DiscordUser(id="123", name="Test", discriminator="1234")

        # Try to promote it to Slack (should use base fields)
        slack_user = promote(discord_user, SLACK)
        assert isinstance(slack_user, SlackUser)
        assert slack_user.id == "123"
        assert slack_user.name == "Test"

    def test_promote_with_none_optional_fields(self):
        """Test promoting with None optional fields."""
        from chatom.discord import DiscordUser

        user = User(id="123", name="Test")
        # email and avatar_url are empty strings by default
        discord_user = promote(user, DISCORD)

        assert isinstance(discord_user, DiscordUser)
        assert discord_user.email == ""
        assert discord_user.avatar_url == ""

    def test_validate_minimal_user(self):
        """Test validating a minimal user."""
        user = User(id="123")  # Only id provided
        result = validate_for_backend(user, DISCORD)
        assert result.valid

    def test_validate_empty_user(self):
        """Test validating an empty user."""
        user = User()  # All defaults
        result = validate_for_backend(user, DISCORD)
        assert result.valid  # Should work with defaults


class TestConversionEdgeCases:
    """Edge case tests for conversion functions."""

    def test_promote_user_to_email(self):
        """Test promoting user to Email backend."""
        from chatom.email import EmailUser

        user = User(id="user@example.com", name="Test User", email="user@example.com")
        email_user = promote(user, EMAIL)
        assert isinstance(email_user, EmailUser)
        assert email_user.email == "user@example.com"

    def test_promote_user_to_irc(self):
        """Test promoting user to IRC backend."""
        from chatom.irc import IRCUser

        user = User(id="testuser", name="Test User")
        irc_user = promote(user, IRC)
        assert isinstance(irc_user, IRCUser)

    def test_promote_user_to_matrix(self):
        """Test promoting user to Matrix backend."""
        from chatom.matrix import MatrixUser

        user = User(id="@user:matrix.org", name="Test User")
        matrix_user = promote(user, MATRIX)
        assert isinstance(matrix_user, MatrixUser)

    def test_promote_channel_to_email(self):
        """Test promoting channel to Email backend."""
        from chatom.email import EmailChannel

        channel = Channel(id="INBOX", name="INBOX")
        email_channel = promote(channel, EMAIL)
        assert isinstance(email_channel, EmailChannel)

    def test_promote_channel_to_irc(self):
        """Test promoting channel to IRC backend."""
        from chatom.irc import IRCChannel

        channel = Channel(id="#general", name="#general")
        irc_channel = promote(channel, IRC)
        assert isinstance(irc_channel, IRCChannel)

    def test_promote_channel_to_matrix(self):
        """Test promoting channel to Matrix backend."""
        from chatom.matrix import MatrixChannel

        channel = Channel(id="!room:matrix.org", name="Test Room")
        matrix_channel = promote(channel, MATRIX)
        assert isinstance(matrix_channel, MatrixChannel)

    def test_validate_for_email_backend(self):
        """Test validate_for_backend with Email backend."""
        user = User(id="user@example.com", name="Test")
        result = validate_for_backend(user, EMAIL)
        assert result.valid

    def test_validate_for_irc_backend(self):
        """Test validate_for_backend with IRC backend."""
        user = User(id="testuser", name="Test")
        result = validate_for_backend(user, IRC)
        assert result.valid

    def test_validate_for_matrix_backend(self):
        """Test validate_for_backend with Matrix backend."""
        user = User(id="@user:matrix.org", name="Test")
        result = validate_for_backend(user, MATRIX)
        assert result.valid

    def test_can_promote_to_email(self):
        """Test can_promote with Email backend."""
        user = User(id="user@example.com", name="Test")
        assert can_promote(user, EMAIL)

    def test_can_promote_to_irc(self):
        """Test can_promote with IRC backend."""
        user = User(id="testuser", name="Test")
        assert can_promote(user, IRC)

    def test_can_promote_to_matrix(self):
        """Test can_promote with Matrix backend."""
        user = User(id="@user:matrix.org", name="Test")
        assert can_promote(user, MATRIX)

    def test_demote_email_user(self):
        """Test demoting EmailUser to base User."""
        from chatom.email import EmailUser

        email_user = EmailUser(id="user@example.com", name="Test", handle="user@example.com", email="user@example.com")
        base_user = demote(email_user)
        assert isinstance(base_user, User)
        assert base_user.id == "user@example.com"

    def test_demote_irc_user(self):
        """Test demoting IRCUser to base User."""
        from chatom.irc import IRCUser

        irc_user = IRCUser(id="testuser", name="Test", handle="testuser", nick="testuser")
        base_user = demote(irc_user)
        assert isinstance(base_user, User)

    def test_demote_matrix_user(self):
        """Test demoting MatrixUser to base User."""
        from chatom.matrix import MatrixUser

        matrix_user = MatrixUser(id="@user:matrix.org", name="Test", handle="@user:matrix.org")
        base_user = demote(matrix_user)
        assert isinstance(base_user, User)

    def test_promote_presence_to_discord(self):
        """Test promoting Presence to Discord."""
        from chatom.discord import DiscordPresence

        presence = Presence(user_id="123", status=PresenceStatus.ONLINE)
        discord_presence = promote(presence, DISCORD)
        assert isinstance(discord_presence, DiscordPresence)

    def test_promote_presence_to_slack(self):
        """Test promoting Presence to Slack."""
        from chatom.slack import SlackPresence

        presence = Presence(user_id="U123", status=PresenceStatus.ONLINE)
        slack_presence = promote(presence, SLACK)
        assert isinstance(slack_presence, SlackPresence)

    def test_promote_presence_to_symphony(self):
        """Test promoting Presence to Symphony."""
        from chatom.symphony import SymphonyPresence

        presence = Presence(user_id="12345", status=PresenceStatus.ONLINE)
        symphony_presence = promote(presence, SYMPHONY)
        assert isinstance(symphony_presence, SymphonyPresence)

    def test_promote_presence_to_matrix(self):
        """Test promoting Presence to Matrix."""
        from chatom.matrix import MatrixPresence

        presence = Presence(user_id="@user:matrix.org", status=PresenceStatus.ONLINE)
        matrix_presence = promote(presence, MATRIX)
        assert isinstance(matrix_presence, MatrixPresence)

    def test_demote_discord_presence(self):
        """Test demoting DiscordPresence to base Presence."""
        from chatom.discord import DiscordPresence

        discord_presence = DiscordPresence(user_id="123", status=PresenceStatus.ONLINE)
        base_presence = demote(discord_presence)
        assert isinstance(base_presence, Presence)
        assert base_presence.status == PresenceStatus.ONLINE

    def test_demote_slack_presence(self):
        """Test demoting SlackPresence to base Presence."""
        from chatom.slack import SlackPresence

        slack_presence = SlackPresence(user_id="U123", status=PresenceStatus.ONLINE)
        base_presence = demote(slack_presence)
        assert isinstance(base_presence, Presence)

    def test_validate_channel_for_symphony(self):
        """Test validate_for_backend for Channel to Symphony."""
        channel = Channel(id="stream123", name="Test Stream")
        result = validate_for_backend(channel, SYMPHONY)
        assert result.valid

    def test_validate_channel_for_email(self):
        """Test validate_for_backend for Channel to Email."""
        channel = Channel(id="INBOX", name="Inbox")
        result = validate_for_backend(channel, EMAIL)
        assert result.valid

    def test_validate_channel_for_irc(self):
        """Test validate_for_backend for Channel to IRC."""
        channel = Channel(id="#general", name="#general")
        result = validate_for_backend(channel, IRC)
        assert result.valid

    def test_validate_channel_for_matrix(self):
        """Test validate_for_backend for Channel to Matrix."""
        channel = Channel(id="!room:matrix.org", name="Test")
        result = validate_for_backend(channel, MATRIX)
        assert result.valid
