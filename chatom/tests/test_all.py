"""Smoke tests to verify all imports work correctly."""


class TestImports:
    """Test that all major imports work."""

    def test_import_main_module(self):
        """Test importing the main chatom module."""
        import chatom

        assert hasattr(chatom, "__version__")

    def test_import_base_models(self):
        """Test importing base models."""
        from chatom import (
            Channel,
            Message,
            User,
        )

        # Just verify they can be imported
        assert User is not None
        assert Channel is not None
        assert Message is not None

    def test_import_format_system(self):
        """Test importing format system."""
        from chatom import (
            Format,
            TextNode,
        )

        assert Format is not None
        assert TextNode is not None

    def test_import_backend_config(self):
        """Test importing backend configuration."""
        from chatom import BackendConfig

        assert BackendConfig is not None

    def test_import_enums(self):
        """Test importing backend enums."""
        from chatom import (
            ALL_BACKENDS,
            DISCORD,
            SLACK,
        )

        assert DISCORD in ALL_BACKENDS
        assert SLACK in ALL_BACKENDS

    def test_import_discord_backend(self):
        """Test importing Discord backend."""
        from chatom.discord import (
            DiscordUser,
        )

        assert DiscordUser is not None

    def test_import_slack_backend(self):
        """Test importing Slack backend."""
        from chatom.slack import (
            SlackUser,
        )

        assert SlackUser is not None

    def test_import_symphony_backend(self):
        """Test importing Symphony backend."""
        from chatom.symphony import (
            SymphonyUser,
        )

        assert SymphonyUser is not None


class TestIntegration:
    """Integration tests for chatom."""

    def test_create_message_chain(self):
        """Test creating a full message with all components."""
        from chatom import Channel, Emoji, Message, Reaction, User

        user = User(id="u1", name="Alice")
        channel = Channel(id="c1", name="general")
        emoji = Emoji(name="thumbsup", unicode="👍")
        reaction = Reaction(emoji=emoji, count=1)

        msg = Message(
            id="m1",
            content="Hello everyone!",
            author=user,
            channel=channel,
            reactions=[reaction],
        )

        assert msg.author.name == "Alice"
        assert msg.channel.name == "general"
        assert len(msg.reactions) == 1

    def test_format_and_render_message(self):
        """Test building and rendering a formatted message."""
        from chatom import (
            Bold,
            Format,
            FormattedMessage,
            Paragraph,
            Span,
            Text,
        )

        msg = FormattedMessage(
            content=[
                Span(
                    children=[
                        Text(content="Hello, "),
                        Bold(child=Text(content="world")),
                        Text(content="!"),
                    ]
                ),
                Paragraph(children=[Text(content="This is a test message.")]),
            ]
        )

        markdown = msg.render(Format.MARKDOWN)
        html = msg.render(Format.HTML)
        plaintext = msg.render(Format.PLAINTEXT)

        assert "world" in markdown
        assert "world" in html
        assert "world" in plaintext

    def test_table_rendering(self):
        """Test table creation and rendering."""
        from chatom import Format, Table

        data = [
            ["Alice", "100"],
            ["Bob", "85"],
        ]
        table = Table.from_data(data, headers=["name", "score"])

        markdown = table.render(Format.MARKDOWN)
        html = table.render(Format.HTML)

        assert "Alice" in markdown
        assert "<table>" in html

    def test_backend_capabilities(self):
        """Test backend capabilities checking."""
        from chatom import (
            DISCORD_CAPABILITIES,
            SLACK_CAPABILITIES,
            Capability,
        )

        # Both should have emoji reactions
        assert DISCORD_CAPABILITIES.supports(Capability.EMOJI_REACTIONS)
        assert SLACK_CAPABILITIES.supports(Capability.EMOJI_REACTIONS)


class TestEmojiStr:
    """Tests for Emoji __str__ method."""

    def test_emoji_str_with_unicode(self):
        """Test str(emoji) returns unicode character when available."""
        from chatom import Emoji

        emoji = Emoji(name="thumbsup", unicode="👍")
        assert str(emoji) == "👍"

    def test_emoji_str_without_unicode(self):
        """Test str(emoji) returns :name: format for custom emoji."""
        from chatom import Emoji

        emoji = Emoji(name="custom_emoji", id="123456")
        assert str(emoji) == ":custom_emoji:"
