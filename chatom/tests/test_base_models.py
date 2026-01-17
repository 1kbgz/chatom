"""Tests for chatom base models."""

from chatom.base import (
    DISCORD_CAPABILITIES,
    SLACK_CAPABILITIES,
    # Presence
    Activity,
    ActivityType,
    # Attachment
    Attachment,
    AttachmentType,
    # Capabilities
    BackendCapabilities,
    # Base classes
    BaseModel,
    Capability,
    # Channel
    Channel,
    ChannelType,
    # Embed
    Embed,
    EmbedAuthor,
    EmbedField,
    Emoji,
    File,
    Identifiable,
    Image,
    # Message
    Message,
    MessageReference,
    MessageType,
    Presence,
    PresenceStatus,
    Reaction,
    # Thread
    Thread,
    # User
    User,
)


class TestBaseModel:
    """Tests for the BaseModel class."""

    def test_to_dict(self):
        """Test conversion to dictionary."""

        class TestModel(BaseModel):
            name: str
            value: int

        model = TestModel(name="test", value=42)
        result = model.to_dict()
        assert result == {"name": "test", "value": 42}

    def test_copy_with(self):
        """Test copying with modifications."""

        class TestModel(BaseModel):
            name: str
            value: int

        original = TestModel(name="original", value=1)
        copy = original.copy_with(value=2)
        assert copy.name == "original"
        assert copy.value == 2
        assert original.value == 1  # Original unchanged


class TestIdentifiable:
    """Tests for the Identifiable class."""

    def test_create_identifiable(self):
        """Test creating an identifiable object."""
        obj = Identifiable(id="123", name="Test Object")
        assert obj.id == "123"
        assert obj.name == "Test Object"


class TestUser:
    """Tests for the User class."""

    def test_create_user(self):
        """Test creating a user."""
        user = User(id="123", name="John Doe", handle="johndoe")
        assert user.id == "123"
        assert user.name == "John Doe"
        assert user.handle == "johndoe"

    def test_user_display_name(self):
        """Test display name property."""
        user1 = User(id="1", name="John Doe")
        assert user1.display_name == "John Doe"

        user2 = User(id="2", name="", handle="johndoe")
        assert user2.display_name == "johndoe"

    def test_user_mention_name(self):
        """Test mention name property."""
        user1 = User(id="1", name="John", handle="johndoe")
        assert user1.mention_name == "johndoe"

        user2 = User(id="2", name="Jane Doe")
        assert user2.mention_name == "Jane Doe"

    def test_user_defaults(self):
        """Test user default values."""
        user = User(id="1", name="Test")
        assert user.handle == ""
        assert user.email == ""  # Empty string, not None
        assert user.avatar_url == ""
        assert user.is_bot is False


class TestChannel:
    """Tests for the Channel class."""

    def test_create_channel(self):
        """Test creating a channel."""
        channel = Channel(id="456", name="general", topic="General chat")
        assert channel.id == "456"
        assert channel.name == "general"
        assert channel.topic == "General chat"

    def test_channel_type(self):
        """Test channel type enum."""
        public = Channel(id="1", name="public", channel_type=ChannelType.PUBLIC)
        private = Channel(id="2", name="private", channel_type=ChannelType.PRIVATE)
        dm = Channel(id="3", name="dm", channel_type=ChannelType.DIRECT)

        assert public.channel_type == ChannelType.PUBLIC
        assert private.channel_type == ChannelType.PRIVATE
        assert dm.channel_type == ChannelType.DIRECT

    def test_channel_defaults(self):
        """Test channel default values."""
        channel = Channel(id="1", name="test")
        assert channel.topic == ""  # Empty string, not None
        assert channel.channel_type == ChannelType.UNKNOWN
        assert channel.is_archived is False


class TestThread:
    """Tests for the Thread class."""

    def test_create_thread(self):
        """Test creating a thread."""
        parent = Channel(id="parent", name="parent-channel")
        thread = Thread(
            id="thread-1",
            name="Discussion Thread",
            parent_channel=parent,
            parent_message_id="msg-123",
        )
        assert thread.id == "thread-1"
        assert thread.parent_channel.id == "parent"
        assert thread.parent_message_id == "msg-123"


class TestMessage:
    """Tests for the Message class."""

    def test_create_message(self):
        """Test creating a message."""
        user = User(id="u1", name="Alice")
        channel = Channel(id="c1", name="general")
        msg = Message(
            id="m1",
            content="Hello, world!",
            author=user,
            channel=channel,
        )
        assert msg.id == "m1"
        assert msg.content == "Hello, world!"
        assert msg.author.name == "Alice"
        assert msg.channel.name == "general"

    def test_message_backwards_compatibility(self):
        """Test backwards compatible aliases."""
        user = User(id="u1", name="Alice")
        channel = Channel(id="c1", name="general")
        msg = Message(
            id="m1",
            content="Test",
            author=user,
            channel=channel,
        )
        # Test aliases
        assert msg.text == msg.content
        assert msg.user == msg.author

    def test_message_type(self):
        """Test message type enum."""
        user = User(id="u1", name="Alice")
        channel = Channel(id="c1", name="general")

        default_msg = Message(id="m1", content="Hi", author=user, channel=channel)
        assert default_msg.message_type == MessageType.DEFAULT

        system_msg = Message(
            id="m2",
            content="Alice joined",
            author=user,
            channel=channel,
            message_type=MessageType.SYSTEM,
        )
        assert system_msg.message_type == MessageType.SYSTEM

    def test_message_with_reply(self):
        """Test message with reply reference."""
        user = User(id="u1", name="Alice")
        channel = Channel(id="c1", name="general")
        ref = MessageReference(
            message_id="original-msg",
            channel_id="c1",
        )
        reply = Message(
            id="m2",
            content="Reply to your message",
            author=user,
            channel=channel,
            reference=ref,
        )
        assert reply.reference is not None
        assert reply.reference.message_id == "original-msg"


class TestAttachment:
    """Tests for Attachment classes."""

    def test_create_attachment(self):
        """Test creating a basic attachment."""
        attachment = Attachment(
            id="a1",
            filename="document.pdf",
            url="https://example.com/doc.pdf",
            size=1024,
        )
        assert attachment.filename == "document.pdf"
        assert attachment.size == 1024

    def test_create_image(self):
        """Test creating an image attachment."""
        image = Image(
            id="img1",
            filename="photo.png",
            url="https://example.com/photo.png",
            width=800,
            height=600,
            alt_text="A nice photo",
        )
        assert image.width == 800
        assert image.height == 600
        assert image.alt_text == "A nice photo"
        assert image.attachment_type == AttachmentType.IMAGE

    def test_create_file(self):
        """Test creating a file attachment."""
        file = File(
            id="f1",
            filename="data.csv",
            url="https://example.com/data.csv",
            size=2048,
        )
        assert file.attachment_type == AttachmentType.FILE


class TestEmbed:
    """Tests for Embed classes."""

    def test_create_embed(self):
        """Test creating an embed."""
        embed = Embed(
            title="Article Title",
            description="Article description here",
            url="https://example.com/article",
            color=0x3498DB,
        )
        assert embed.title == "Article Title"
        assert embed.color == 0x3498DB

    def test_embed_with_author(self):
        """Test embed with author."""
        author = EmbedAuthor(
            name="John Doe",
            url="https://example.com/john",
            icon_url="https://example.com/john/avatar.png",
        )
        embed = Embed(title="Post", author=author)
        assert embed.author.name == "John Doe"

    def test_embed_with_fields(self):
        """Test embed with fields."""
        fields = [
            EmbedField(name="Field 1", value="Value 1"),
            EmbedField(name="Field 2", value="Value 2", inline=True),
        ]
        embed = Embed(title="Info", fields=fields)
        assert len(embed.fields) == 2
        assert embed.fields[1].inline is True


class TestReaction:
    """Tests for Emoji and Reaction classes."""

    def test_create_emoji(self):
        """Test creating an emoji."""
        emoji = Emoji(name="thumbsup", unicode="👍")
        assert emoji.name == "thumbsup"
        assert emoji.unicode == "👍"
        assert emoji.is_custom is False

    def test_create_custom_emoji(self):
        """Test creating a custom emoji."""
        emoji = Emoji(
            name="custom_emoji",
            id="12345",
            is_custom=True,
            url="https://example.com/emoji.png",
        )
        assert emoji.is_custom is True
        assert emoji.id == "12345"

    def test_create_reaction(self):
        """Test creating a reaction."""
        emoji = Emoji(name="heart", unicode="❤️")
        reaction = Reaction(emoji=emoji, count=5)
        assert reaction.count == 5
        assert reaction.emoji.unicode == "❤️"


class TestPresence:
    """Tests for Presence classes."""

    def test_create_presence(self):
        """Test creating a presence."""
        presence = Presence(
            status=PresenceStatus.ONLINE,
        )
        assert presence.status == PresenceStatus.ONLINE
        assert presence.is_online is True
        assert presence.is_available is True

    def test_presence_statuses(self):
        """Test different presence statuses."""
        online = Presence(status=PresenceStatus.ONLINE)
        idle = Presence(status=PresenceStatus.IDLE)
        dnd = Presence(status=PresenceStatus.DND)
        offline = Presence(status=PresenceStatus.OFFLINE)

        assert online.is_online is True
        assert online.is_available is True

        assert idle.is_online is True
        assert idle.is_available is True  # Implementation considers IDLE as available

        assert dnd.is_online is True
        assert dnd.is_available is False

        assert offline.is_online is False
        assert offline.is_available is False

    def test_presence_with_activity(self):
        """Test presence with activity."""
        activity = Activity(
            name="Playing a game",
            activity_type=ActivityType.PLAYING,
        )
        presence = Presence(
            status=PresenceStatus.ONLINE,
            activity=activity,
        )
        assert presence.activity.name == "Playing a game"
        assert presence.activity.activity_type == ActivityType.PLAYING


class TestCapabilities:
    """Tests for BackendCapabilities."""

    def test_create_capabilities(self):
        """Test creating capabilities."""
        caps = BackendCapabilities(
            capabilities=frozenset(
                {
                    Capability.EMOJI_REACTIONS,
                    Capability.THREADS,
                    Capability.EMBEDS,
                }
            )
        )
        assert caps.supports(Capability.EMOJI_REACTIONS)
        assert caps.supports(Capability.THREADS)

    def test_supports_all(self):
        """Test supports_all method."""
        caps = BackendCapabilities(
            capabilities=frozenset(
                {
                    Capability.EMOJI_REACTIONS,
                    Capability.THREADS,
                }
            )
        )
        assert caps.supports_all(Capability.EMOJI_REACTIONS, Capability.THREADS)

    def test_supports_any(self):
        """Test supports_any method."""
        caps = BackendCapabilities(capabilities=frozenset({Capability.EMOJI_REACTIONS}))
        assert caps.supports_any(Capability.EMOJI_REACTIONS, Capability.THREADS)

    def test_predefined_capabilities(self):
        """Test predefined backend capabilities."""
        # Discord should have many capabilities
        assert DISCORD_CAPABILITIES.supports(Capability.EMOJI_REACTIONS)
        assert DISCORD_CAPABILITIES.supports(Capability.THREADS)
        assert DISCORD_CAPABILITIES.supports(Capability.EMBEDS)

        # Slack should have reactions and threads
        assert SLACK_CAPABILITIES.supports(Capability.EMOJI_REACTIONS)
        assert SLACK_CAPABILITIES.supports(Capability.THREADS)


class TestAttachmentFromContentType:
    """Tests for Attachment.from_content_type method."""

    def test_image_content_types(self):
        """Test image MIME types are recognized."""
        assert Attachment.from_content_type("image/png") == AttachmentType.IMAGE
        assert Attachment.from_content_type("image/jpeg") == AttachmentType.IMAGE
        assert Attachment.from_content_type("image/gif") == AttachmentType.IMAGE
        assert Attachment.from_content_type("image/webp") == AttachmentType.IMAGE

    def test_video_content_types(self):
        """Test video MIME types are recognized."""
        assert Attachment.from_content_type("video/mp4") == AttachmentType.VIDEO
        assert Attachment.from_content_type("video/webm") == AttachmentType.VIDEO
        assert Attachment.from_content_type("video/quicktime") == AttachmentType.VIDEO

    def test_audio_content_types(self):
        """Test audio MIME types are recognized."""
        assert Attachment.from_content_type("audio/mpeg") == AttachmentType.AUDIO
        assert Attachment.from_content_type("audio/wav") == AttachmentType.AUDIO
        assert Attachment.from_content_type("audio/ogg") == AttachmentType.AUDIO

    def test_document_content_types(self):
        """Test document MIME types are recognized."""
        assert Attachment.from_content_type("application/pdf") == AttachmentType.DOCUMENT
        assert Attachment.from_content_type("application/msword") == AttachmentType.DOCUMENT
        assert Attachment.from_content_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document") == AttachmentType.DOCUMENT

    def test_archive_content_types(self):
        """Test archive MIME types are recognized."""
        assert Attachment.from_content_type("application/zip") == AttachmentType.ARCHIVE
        assert Attachment.from_content_type("application/x-tar") == AttachmentType.ARCHIVE
        assert Attachment.from_content_type("application/gzip") == AttachmentType.ARCHIVE

    def test_code_content_types(self):
        """Test text/code MIME types are recognized."""
        assert Attachment.from_content_type("text/plain") == AttachmentType.CODE
        assert Attachment.from_content_type("text/html") == AttachmentType.CODE
        assert Attachment.from_content_type("text/javascript") == AttachmentType.CODE

    def test_unknown_content_types(self):
        """Test unknown MIME types return FILE."""
        assert Attachment.from_content_type("application/octet-stream") == AttachmentType.FILE
        assert Attachment.from_content_type("application/json") == AttachmentType.FILE


class TestAttachmentTypes:
    """Tests for AttachmentType enum."""

    def test_all_attachment_types_exist(self):
        """Test all expected attachment types exist."""
        assert AttachmentType.FILE
        assert AttachmentType.IMAGE
        assert AttachmentType.VIDEO
        assert AttachmentType.AUDIO
        assert AttachmentType.DOCUMENT
        assert AttachmentType.ARCHIVE
        assert AttachmentType.CODE
        assert AttachmentType.UNKNOWN

    def test_attachment_type_values(self):
        """Test attachment type values are strings."""
        assert AttachmentType.FILE.value == "file"
        assert AttachmentType.IMAGE.value == "image"
        assert AttachmentType.VIDEO.value == "video"


class TestImageAttachment:
    """Tests for Image attachment class."""

    def test_image_default_type(self):
        """Test Image has correct default attachment type."""
        img = Image(id="1", filename="test.png", url="http://example.com/test.png")
        assert img.attachment_type == AttachmentType.IMAGE

    def test_image_dimensions(self):
        """Test Image dimension attributes."""
        img = Image(
            id="1",
            filename="test.png",
            url="http://example.com/test.png",
            width=1920,
            height=1080,
        )
        assert img.width == 1920
        assert img.height == 1080

    def test_image_thumbnail(self):
        """Test Image thumbnail URL."""
        img = Image(
            id="1",
            filename="test.png",
            url="http://example.com/test.png",
            thumbnail_url="http://example.com/thumb.png",
        )
        assert img.thumbnail_url == "http://example.com/thumb.png"


class TestFileAttachment:
    """Tests for File attachment class."""

    def test_file_default_type(self):
        """Test File has correct default attachment type."""
        f = File(id="1", filename="data.csv", url="http://example.com/data.csv")
        assert f.attachment_type == AttachmentType.FILE

    def test_file_preview(self):
        """Test File preview attribute."""
        f = File(
            id="1",
            filename="readme.txt",
            url="http://example.com/readme.txt",
            preview="This is the first line...",
        )
        assert f.preview == "This is the first line..."


class TestReactionModel:
    """Additional tests for Reaction model."""

    def test_reaction_count_default(self):
        """Test reaction default count."""
        emoji = Emoji(name="heart", unicode="❤️")
        reaction = Reaction(emoji=emoji)
        assert reaction.count == 1

    def test_reaction_with_me(self):
        """Test reaction me flag."""
        emoji = Emoji(name="thumbsup", unicode="👍")
        reaction = Reaction(emoji=emoji, count=5, me=True)
        assert reaction.me is True


class TestMessageReference:
    """Tests for MessageReference class."""

    def test_message_reference_basic(self):
        """Test basic message reference."""
        ref = MessageReference(message_id="msg-123")
        assert ref.message_id == "msg-123"
        assert ref.channel_id == ""
        assert ref.guild_id == ""

    def test_message_reference_full(self):
        """Test message reference with all fields."""
        ref = MessageReference(
            message_id="msg-123",
            channel_id="ch-456",
            guild_id="guild-789",
        )
        assert ref.message_id == "msg-123"
        assert ref.channel_id == "ch-456"
        assert ref.guild_id == "guild-789"
