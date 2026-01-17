"""Tests for mention utilities."""

import pytest

from chatom import Channel, User, mention_channel, mention_user
from chatom.discord import DiscordChannel, DiscordUser
from chatom.email import EmailUser
from chatom.irc import IRCUser
from chatom.matrix import MatrixUser
from chatom.slack import SlackChannel, SlackUser
from chatom.symphony import SymphonyUser


class TestMentionUser:
    """Tests for mention_user function."""

    @pytest.mark.parametrize(
        "user,expected",
        [
            # Discord mentions use <@id> format
            (DiscordUser(handle="jane_doe", id="456", name="Jane Doe"), "<@456>"),
            # Email without email falls back to name
            (EmailUser(handle="", id="789", name="Alice"), "Alice"),
            # Email with email uses mailto link
            (EmailUser(handle="", id="101", name="Bob", email="bob@example.com"), "<a href='mailto:bob@example.com'>Bob</a>"),
            # IRC uses nick
            (IRCUser(nick="charlie", id="112", name="Charlie"), "charlie"),
            # IRC without nick falls back to handle then name
            (IRCUser(id="131", name="David"), "David"),
            # Matrix uses user_id
            (MatrixUser(handle="eve", id="415", name="Eve", user_id="@eve:matrix.org"), "@eve:matrix.org"),
            # Slack uses <@id> format
            (SlackUser(handle="john_doe", id="123", name="John Doe"), "<@123>"),
            # Symphony uses MessageML mention tag
            (SymphonyUser(handle="frank", id="161", name="Frank"), '<mention uid="161"/>'),
            # Base User falls back to name
            (User(handle="ivan", id="202", name="Ivan"), "Ivan"),
        ],
    )
    def test_mention_user(self, user, expected):
        """Test mention_user produces expected output for each backend."""
        result = mention_user(user)
        assert result == expected

    def test_mention_user_with_base_user(self):
        """Test that base User falls back to name."""
        user = User(id="1", name="Test User", handle="testhandle")
        result = mention_user(user)
        assert result == "Test User"


class TestMentionChannel:
    """Tests for mention_channel function."""

    def test_mention_discord_channel(self):
        """Test Discord channel mention."""
        channel = DiscordChannel(id="123456", name="general")
        result = mention_channel(channel)
        assert result == "<#123456>"

    def test_mention_slack_channel(self):
        """Test Slack channel mention."""
        channel = SlackChannel(id="C123456", name="random")
        result = mention_channel(channel)
        assert result == "<#C123456>"

    def test_mention_base_channel(self):
        """Test base Channel mention falls back to #name."""
        channel = Channel(id="1", name="general")
        result = mention_channel(channel)
        assert result == "#general"


class TestSpecialMentions:
    """Tests for special mention functions."""

    def test_discord_role_mention(self):
        """Test Discord role mention."""
        from chatom.discord import mention_role

        assert mention_role("123") == "<@&123>"

    def test_discord_everyone(self):
        """Test Discord @everyone."""
        from chatom.discord import mention_everyone

        assert mention_everyone() == "@everyone"

    def test_discord_here(self):
        """Test Discord @here."""
        from chatom.discord import mention_here

        assert mention_here() == "@here"

    def test_slack_user_group(self):
        """Test Slack user group mention."""
        from chatom.slack import mention_user_group

        assert mention_user_group("S123") == "<!subteam^S123>"

    def test_slack_here(self):
        """Test Slack @here."""
        from chatom.slack import mention_here

        assert mention_here() == "<!here>"

    def test_slack_channel_all(self):
        """Test Slack @channel."""
        from chatom.slack import mention_channel_all

        assert mention_channel_all() == "<!channel>"

    def test_slack_everyone(self):
        """Test Slack @everyone."""
        from chatom.slack import mention_everyone

        assert mention_everyone() == "<!everyone>"

    def test_symphony_hashtag(self):
        """Test Symphony hashtag."""
        from chatom.symphony import format_hashtag

        assert format_hashtag("trading") == '<hash tag="trading"/>'

    def test_symphony_cashtag(self):
        """Test Symphony cashtag."""
        from chatom.symphony import format_cashtag

        assert format_cashtag("AAPL") == '<cash tag="AAPL"/>'

    def test_irc_highlight(self):
        """Test IRC highlight."""
        from chatom.irc import highlight_user

        # highlight_user takes nick and message
        result = highlight_user("johnny", "hello there")
        assert result == "johnny: hello there"

    def test_matrix_room_mention(self):
        """Test Matrix room mention."""
        from chatom.matrix import mention_room

        # mention_room only takes room_id
        result = mention_room("!abc:matrix.org")
        assert "!abc:matrix.org" in result

    def test_matrix_pill(self):
        """Test Matrix pill creation."""
        from chatom.matrix import create_pill

        result = create_pill("@john:matrix.org", "John")
        assert "matrix.to" in result
        assert "@john:matrix.org" in result


class TestMentionUserForBackend:
    """Tests for mention_user_for_backend function."""

    def test_mention_for_slack(self):
        """Test mentioning a user for Slack backend."""
        from chatom import User, mention_user_for_backend

        user = User(id="U123456", name="John Doe")
        result = mention_user_for_backend(user, "slack")
        assert result == "<@U123456>"

    def test_mention_for_discord(self):
        """Test mentioning a user for Discord backend."""
        from chatom import User, mention_user_for_backend

        user = User(id="123456789", name="Jane Doe")
        result = mention_user_for_backend(user, "discord")
        assert result == "<@123456789>"

    def test_mention_for_symphony_with_id(self):
        """Test mentioning a user for Symphony backend with ID."""
        from chatom import User, mention_user_for_backend

        user = User(id="12345678901234", name="Bob")
        result = mention_user_for_backend(user, "symphony")
        assert result == '<mention uid="12345678901234"/>'

    def test_mention_for_symphony_with_email(self):
        """Test mentioning a user for Symphony backend with email."""
        from chatom import User, mention_user_for_backend

        user = User(name="Alice", email="alice@example.com")
        result = mention_user_for_backend(user, "symphony")
        assert result == '<mention email="alice@example.com"/>'

    def test_mention_for_symphony_fallback(self):
        """Test mentioning a user for Symphony backend with no id/email."""
        from chatom import User, mention_user_for_backend

        user = User(name="Charlie")
        result = mention_user_for_backend(user, "symphony")
        assert result == "@Charlie"

    def test_mention_for_matrix(self):
        """Test mentioning a user for Matrix backend."""
        from chatom import User, mention_user_for_backend

        user = User(handle="eve", name="Eve")
        result = mention_user_for_backend(user, "matrix")
        assert "@eve:matrix.org" in result

    def test_mention_for_irc(self):
        """Test mentioning a user for IRC backend."""
        from chatom import User, mention_user_for_backend

        user = User(handle="johnny", name="John")
        result = mention_user_for_backend(user, "irc")
        assert result == "johnny"

    def test_mention_for_email_with_email(self):
        """Test mentioning a user for email backend with email."""
        from chatom import User, mention_user_for_backend

        user = User(name="Frank", email="frank@example.com")
        result = mention_user_for_backend(user, "email")
        assert "mailto:frank@example.com" in result
        assert "Frank" in result

    def test_mention_for_email_without_email(self):
        """Test mentioning a user for email backend without email."""
        from chatom import User, mention_user_for_backend

        user = User(name="Grace")
        result = mention_user_for_backend(user, "email")
        assert result == "Grace"

    def test_mention_for_unknown_backend(self):
        """Test mentioning a user for unknown backend falls back to name."""
        from chatom import User, mention_user_for_backend

        user = User(id="123", name="Unknown User")
        result = mention_user_for_backend(user, "unknown_platform")
        assert result == "Unknown User"

    def test_mention_case_insensitive_backend(self):
        """Test backend name is case-insensitive."""
        from chatom import User, mention_user_for_backend

        user = User(id="123", name="Test")
        assert mention_user_for_backend(user, "SLACK") == "<@123>"
        assert mention_user_for_backend(user, "Slack") == "<@123>"
        assert mention_user_for_backend(user, "slack") == "<@123>"


class TestMentionChannelForBackend:
    """Tests for mention_channel_for_backend function."""

    def test_mention_channel_for_slack(self):
        """Test mentioning a channel for Slack backend."""
        from chatom import Channel, mention_channel_for_backend

        channel = Channel(id="C123456", name="general")
        result = mention_channel_for_backend(channel, "slack")
        assert result == "<#C123456>"

    def test_mention_channel_for_discord(self):
        """Test mentioning a channel for Discord backend."""
        from chatom import Channel, mention_channel_for_backend

        channel = Channel(id="123456789", name="general")
        result = mention_channel_for_backend(channel, "discord")
        assert result == "<#123456789>"

    def test_mention_channel_for_other_backend(self):
        """Test mentioning a channel for other backends."""
        from chatom import Channel, mention_channel_for_backend

        channel = Channel(id="123", name="general")
        result = mention_channel_for_backend(channel, "matrix")
        assert result == "#general"


class TestMentionEdgeCases:
    """Additional edge case tests for mention utilities."""

    def test_mention_user_for_discord_no_id(self):
        """Test Discord mention without user ID falls back to display_name."""
        from chatom import User, mention_user_for_backend

        user = User(name="Test User")  # No id
        result = mention_user_for_backend(user, "discord")
        assert result == "Test User"

    def test_mention_user_for_slack_no_id(self):
        """Test Slack mention without user ID falls back to display_name."""
        from chatom import User, mention_user_for_backend

        user = User(name="Test User")  # No id
        result = mention_user_for_backend(user, "slack")
        assert result == "Test User"

    def test_mention_user_for_symphony_with_email(self):
        """Test Symphony mention with email but no ID."""
        from chatom import User, mention_user_for_backend

        user = User(name="Test User", email="test@example.com")  # No id
        result = mention_user_for_backend(user, "symphony")
        assert 'mention email="test@example.com"' in result

    def test_mention_user_for_symphony_no_id_no_email(self):
        """Test Symphony mention without ID or email falls back to @name."""
        from chatom import User, mention_user_for_backend

        user = User(name="Test User")  # No id, no email
        result = mention_user_for_backend(user, "symphony")
        assert result == "@Test User"

    def test_mention_user_for_matrix_no_handle(self):
        """Test Matrix mention without handle falls back to display_name."""
        from chatom import User, mention_user_for_backend

        user = User(name="Test User")  # No handle, no user_id
        result = mention_user_for_backend(user, "matrix")
        assert result == "Test User"

    def test_mention_channel_for_slack_no_id(self):
        """Test Slack channel mention without ID falls back to #name."""
        from chatom import Channel, mention_channel_for_backend

        channel = Channel(name="general")  # No id
        result = mention_channel_for_backend(channel, "slack")
        assert result == "#general"

    def test_mention_channel_for_discord_no_id(self):
        """Test Discord channel mention without ID falls back to #name."""
        from chatom import Channel, mention_channel_for_backend

        channel = Channel(name="general")  # No id
        result = mention_channel_for_backend(channel, "discord")
        assert result == "#general"

    def test_mention_channel_no_name(self):
        """Test channel mention without name uses ID."""
        from chatom import Channel, mention_channel

        channel = Channel(id="C12345")  # name is empty string by default
        result = mention_channel(channel)
        assert "#C12345" in result

    def test_mention_channel_for_backend_no_name(self):
        """Test channel mention for backend without name uses ID."""
        from chatom import Channel, mention_channel_for_backend

        channel = Channel(id="C12345", name="")  # No name
        result = mention_channel_for_backend(channel, "matrix")
        assert result == "#C12345"
