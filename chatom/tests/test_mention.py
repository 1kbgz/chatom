"""Tests for mention utilities."""

import pytest

from chatom import Channel, User, mention_channel, mention_user
from chatom.discord import DiscordChannel, DiscordUser
from chatom.slack import SlackChannel, SlackUser
from chatom.symphony import SymphonyUser


class TestMentionUser:
    """Tests for mention_user function."""

    @pytest.mark.parametrize(
        "user,expected",
        [
            # Discord mentions use <@id> format
            (DiscordUser(handle="jane_doe", id="456", name="Jane Doe"), "<@456>"),
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
        result = mention_channel_for_backend(channel, "unknown_backend")
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
        result = mention_channel_for_backend(channel, "unknown_backend")
        assert result == "#C12345"


class TestParseMentions:
    """Tests for parse_mentions function."""

    def test_parse_mentions_slack(self):
        """Test parsing Slack mentions."""
        from chatom.base.mention import parse_mentions

        mentions = parse_mentions("Hey <@U123> and <@U456>!", "slack")
        assert len(mentions) == 2
        assert mentions[0].user_id == "U123"
        assert mentions[1].user_id == "U456"

    def test_parse_mentions_discord(self):
        """Test parsing Discord mentions."""
        from chatom.base.mention import parse_mentions

        mentions = parse_mentions("<@123456789> Hello!", "discord")
        assert len(mentions) == 1
        assert mentions[0].user_id == "123456789"

    def test_parse_mentions_symphony(self):
        """Test parsing Symphony mentions."""
        from chatom.base.mention import parse_mentions

        mentions = parse_mentions('<mention uid="12345"/>!', "symphony")
        assert len(mentions) == 1
        assert mentions[0].user_id == "12345"

    def test_parse_mentions_symphony_email(self):
        """Test parsing Symphony mentions with email."""
        from chatom.base.mention import parse_mentions

        mentions = parse_mentions('<mention email="test@example.com"/>!', "symphony")
        assert len(mentions) == 1
        assert mentions[0].user_id == "test@example.com"

    def test_parse_mentions_unknown_backend(self):
        """Test parsing mentions for unknown backend returns empty list."""
        from chatom.base.mention import parse_mentions

        mentions = parse_mentions("<@U123>!", "unknown")
        assert len(mentions) == 0


class TestExtractMentionIds:
    """Tests for extract_mention_ids function."""

    def test_extract_mention_ids_slack(self):
        """Test extracting mention IDs for Slack."""
        from chatom.base.mention import extract_mention_ids

        ids = extract_mention_ids("Hey <@U123> and <@U456>!", "slack")
        assert ids == ["U123", "U456"]


class TestParseChannelMentions:
    """Tests for parse_channel_mentions function."""

    def test_parse_channel_mentions_slack(self):
        """Test parsing Slack channel mentions."""
        from chatom.base.mention import parse_channel_mentions

        mentions = parse_channel_mentions("Join <#C123> and <#C456>!", "slack")
        assert len(mentions) == 2
        assert mentions[0].channel_id == "C123"
        assert mentions[1].channel_id == "C456"

    def test_parse_channel_mentions_discord(self):
        """Test parsing Discord channel mentions."""
        from chatom.base.mention import parse_channel_mentions

        mentions = parse_channel_mentions("Check <#987654321>!", "discord")
        assert len(mentions) == 1
        assert mentions[0].channel_id == "987654321"

    def test_parse_channel_mentions_unknown_backend(self):
        """Test parsing channel mentions for unknown backend returns empty list."""
        from chatom.base.mention import parse_channel_mentions

        mentions = parse_channel_mentions("<#C123>!", "unknown")
        assert len(mentions) == 0


class TestExtractChannelIds:
    """Tests for extract_channel_ids function."""

    def test_extract_channel_ids_slack(self):
        """Test extracting channel IDs for Slack."""
        from chatom.base.mention import extract_channel_ids

        ids = extract_channel_ids("Join <#C123> and <#C456>!", "slack")
        assert ids == ["C123", "C456"]
