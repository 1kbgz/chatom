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
    # Organization
    Organization,
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

    def test_mark_incomplete_complete(self):
        """Test mark_incomplete and mark_complete methods."""
        # Test the _incomplete flag via mark_incomplete/mark_complete
        obj = Identifiable(id="123", name="test")
        assert obj.is_incomplete is False  # Default is not incomplete

        obj.mark_incomplete()
        assert obj.is_incomplete is True  # Now marked incomplete

        obj.mark_complete()
        assert obj.is_incomplete is False  # Back to complete


class TestIdentifiable:
    """Tests for the Identifiable class."""

    def test_create_identifiable(self):
        """Test creating an identifiable object."""
        obj = Identifiable(id="123", name="Test Object")
        assert obj.id == "123"
        assert obj.name == "Test Object"


class TestOrganization:
    """Tests for the Organization class."""

    def test_create_organization(self):
        """Test creating an organization."""
        org = Organization(id="org123", name="My Org", description="A test org")
        assert org.id == "org123"
        assert org.name == "My Org"
        assert org.description == "A test org"

    def test_organization_defaults(self):
        """Test organization default values."""
        org = Organization(id="org1", name="Test")
        assert org.description == ""
        assert org.icon_url == ""
        assert org.member_count is None
        assert org.owner is None

    def test_organization_display_name(self):
        """Test organization display_name property."""
        org1 = Organization(id="org1", name="My Organization")
        assert org1.display_name == "My Organization"

        org2 = Organization(id="org2", name="")
        assert org2.display_name == "org2"

    def test_organization_owner_id(self):
        """Test organization owner_id property."""
        # Without owner
        org1 = Organization(id="org1", name="Test")
        assert org1.owner_id == ""

        # With owner
        owner = User(id="user123", name="Owner")
        org2 = Organization(id="org2", name="Test", owner=owner)
        assert org2.owner_id == "user123"


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

    def test_dm_to_creates_incomplete_channel(self):
        """Test Channel.dm_to() creates an incomplete DM channel."""
        user = User(id="u1", name="Alice")
        dm = Channel.dm_to(user)

        assert dm.channel_type == ChannelType.DIRECT
        assert dm.users == [user]
        assert dm.is_incomplete
        assert not dm.is_complete
        assert not dm.id  # No ID until resolved

    def test_group_dm_to_creates_incomplete_channel(self):
        """Test Channel.group_dm_to() creates an incomplete group DM."""
        user1 = User(id="u1", name="Alice")
        user2 = User(id="u2", name="Bob")
        group = Channel.group_dm_to([user1, user2])

        assert group.channel_type == ChannelType.GROUP
        assert group.users == [user1, user2]
        assert group.is_incomplete
        assert not group.is_complete
        assert not group.id  # No ID until resolved

    def test_direct_channel_requires_one_user(self):
        """Test DIRECT channel must have exactly 1 user."""
        user1 = User(id="u1", name="Alice")
        user2 = User(id="u2", name="Bob")

        # Valid: exactly 1 user
        dm = Channel(channel_type=ChannelType.DIRECT, users=[user1])
        assert len(dm.users) == 1

        # Invalid: 0 users (not an error - users is optional)
        empty = Channel(channel_type=ChannelType.DIRECT, users=[])
        assert len(empty.users) == 0  # Empty is allowed

        # Invalid: 2 users
        import pytest

        with pytest.raises(ValueError, match="DIRECT channel must have exactly 1 user"):
            Channel(channel_type=ChannelType.DIRECT, users=[user1, user2])

    def test_group_channel_requires_two_or_more_users(self):
        """Test GROUP channel must have at least 2 users."""
        user1 = User(id="u1", name="Alice")
        user2 = User(id="u2", name="Bob")
        user3 = User(id="u3", name="Charlie")

        # Valid: 2 users
        group2 = Channel(channel_type=ChannelType.GROUP, users=[user1, user2])
        assert len(group2.users) == 2

        # Valid: 3 users
        group3 = Channel(channel_type=ChannelType.GROUP, users=[user1, user2, user3])
        assert len(group3.users) == 3

        # Invalid: 1 user
        import pytest

        with pytest.raises(ValueError, match="GROUP channel must have at least 2 users"):
            Channel(channel_type=ChannelType.GROUP, users=[user1])

    def test_users_field_infers_channel_type(self):
        """Test that users field auto-infers channel type for UNKNOWN."""
        user1 = User(id="u1", name="Alice")
        user2 = User(id="u2", name="Bob")

        # 1 user -> DIRECT
        dm = Channel(users=[user1])
        assert dm.channel_type == ChannelType.DIRECT

        # 2+ users -> GROUP
        group = Channel(users=[user1, user2])
        assert group.channel_type == ChannelType.GROUP

    def test_dm_channel_is_resolvable(self):
        """Test that DM channels with users are resolvable."""
        user = User(id="u1", name="Alice")
        dm = Channel.dm_to(user)

        assert dm.is_resolvable
        assert dm.is_dm
        assert dm.is_direct_message

    def test_dm_channel_is_incomplete_without_id(self):
        """Test DM channel with users but no ID is incomplete."""
        user = User(id="u1", name="Alice")

        # DM with users but no ID - incomplete
        dm = Channel(channel_type=ChannelType.DIRECT, users=[user])
        dm.mark_incomplete()
        assert dm.is_incomplete
        assert not dm.is_complete

        # DM with users AND ID - can be complete
        dm_with_id = Channel(id="dm-123", channel_type=ChannelType.DIRECT, users=[user])
        assert dm_with_id.is_complete

    def test_channel_is_thread(self):
        """Test is_thread property."""
        thread_channel = Channel(id="t1", name="thread", channel_type=ChannelType.THREAD)
        assert thread_channel.is_thread is True

        regular_channel = Channel(id="c1", name="general", channel_type=ChannelType.PUBLIC)
        assert regular_channel.is_thread is False


class TestThread:
    """Tests for the Thread class."""

    def test_create_thread(self):
        """Test creating a thread."""
        parent = Channel(id="parent", name="parent-channel")
        parent_msg = Message(id="msg-123", content="Thread starter")
        thread = Thread(
            id="thread-1",
            name="Discussion Thread",
            parent_channel=parent,
            parent_message=parent_msg,
        )
        assert thread.id == "thread-1"
        assert thread.parent_channel.id == "parent"
        assert thread.parent_message is parent_msg
        assert thread.parent_message_id == "msg-123"

    def test_thread_is_resolvable(self):
        """Test is_resolvable property."""
        # Thread with ID is resolvable
        thread1 = Thread(id="thread-1", name="Thread with ID")
        assert thread1.is_resolvable is True

        # Thread with parent message is resolvable
        parent_msg = Message(id="msg-123", content="Parent")
        thread2 = Thread(id="", name="Thread with parent", parent_message=parent_msg)
        assert thread2.is_resolvable is True

        # Thread without ID or parent message is not resolvable
        thread3 = Thread(id="", name="Empty thread")
        assert thread3.is_resolvable is False


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

    def test_message_channel_name(self):
        """Test channel_name property."""
        channel = Channel(id="c1", name="general")
        msg1 = Message(id="m1", content="Test", channel=channel)
        assert msg1.channel_name == "general"

        # Test fallback to metadata
        msg2 = Message(id="m2", content="Test", metadata={"channel_name": "alt-channel"})
        assert msg2.channel_name == "alt-channel"

        # Test empty
        msg3 = Message(id="m3", content="Test")
        assert msg3.channel_name == ""

    def test_message_author_name(self):
        """Test author_name property."""
        user = User(id="u1", name="Alice")
        msg1 = Message(id="m1", content="Test", author=user)
        assert msg1.author_name == "Alice"

        # Test fallback to metadata
        msg2 = Message(id="m2", content="Test", metadata={"author_name": "Bob"})
        assert msg2.author_name == "Bob"

        # Test empty
        msg3 = Message(id="m3", content="Test")
        assert msg3.author_name == ""

    def test_message_get_mentioned_user_ids(self):
        """Test get_mentioned_user_ids method."""
        msg = Message(id="m1", content="Hey <@U123> and <@U456>!", backend="slack")
        ids = msg.get_mentioned_user_ids()
        assert "U123" in ids
        assert "U456" in ids

    def test_message_get_mentioned_channel_ids(self):
        """Test get_mentioned_channel_ids method."""
        msg = Message(id="m1", content="Join <#C123>!", backend="slack")
        ids = msg.get_mentioned_channel_ids()
        assert "C123" in ids

    def test_message_mentions_user(self):
        """Test mentions_user method."""
        user = User(id="U123", name="Alice")
        msg1 = Message(id="m1", content="Test", tags=[user])
        assert msg1.mentions_user("U123") is True
        assert msg1.mentions_user("U999") is False

        # Also test via content parsing
        msg2 = Message(id="m2", content="Hey <@U456>!", backend="slack")
        assert msg2.mentions_user("U456") is True


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

    def test_embed_add_field(self):
        """Test embed add_field method."""
        embed = Embed(title="Test")
        result = embed.add_field("Name", "Value", inline=True)
        assert result is embed  # Returns self for chaining
        assert len(embed.fields) == 1
        assert embed.fields[0].name == "Name"
        assert embed.fields[0].value == "Value"
        assert embed.fields[0].inline is True


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


class TestMessageProperties:
    """Tests for Message computed properties."""

    def test_user_alias_returns_author(self):
        """Test user property returns author (backwards compat alias)."""
        user = User(id="u1", name="Alice")
        msg = Message(id="m1", content="Hello", author=user)
        assert msg.user == user
        assert msg.user.name == "Alice"

    def test_user_none_when_no_author(self):
        """Test user property returns None when no author."""
        msg = Message(id="m1", content="Hello")
        assert msg.user is None

    def test_tags_returns_mentions(self):
        """Test tags property returns mentions list."""
        user1 = User(id="u1", name="Alice")
        user2 = User(id="u2", name="Bob")
        msg = Message(id="m1", content="Hello", tags=[user1, user2])
        assert msg.tags == [user1, user2]
        assert len(msg.tags) == 2

    def test_tags_empty_by_default(self):
        """Test tags property returns empty list when no mentions."""
        msg = Message(id="m1", content="Hello")
        assert msg.tags == []

    def test_has_attachments_true(self):
        """Test has_attachments returns True when attachments present."""
        attachment = Attachment(id="a1", filename="file.txt", url="http://example.com/file.txt")
        msg = Message(id="m1", content="Hello", attachments=[attachment])
        assert msg.has_attachments is True

    def test_has_attachments_false(self):
        """Test has_attachments returns False when no attachments."""
        msg = Message(id="m1", content="Hello")
        assert msg.has_attachments is False

    def test_has_embeds_true(self):
        """Test has_embeds returns True when embeds present."""
        embed = Embed(title="Test Embed", description="A test")
        msg = Message(id="m1", content="Hello", embeds=[embed])
        assert msg.has_embeds is True

    def test_has_embeds_false(self):
        """Test has_embeds returns False when no embeds."""
        msg = Message(id="m1", content="Hello")
        assert msg.has_embeds is False

    def test_is_reply_with_reference(self):
        """Test is_reply returns True when reference is set."""
        ref = MessageReference(message_id="orig-msg")
        msg = Message(id="m1", content="Hello", reference=ref)
        assert msg.is_reply is True

    def test_is_reply_with_message_type_reply(self):
        """Test is_reply returns True when message_type is REPLY."""
        msg = Message(id="m1", content="Hello", message_type=MessageType.REPLY)
        assert msg.is_reply is True

    def test_is_reply_false(self):
        """Test is_reply returns False for regular messages."""
        msg = Message(id="m1", content="Hello")
        assert msg.is_reply is False


class TestMessageConvenienceMethods:
    """Tests for Message convenience methods for creating new messages."""

    def setup_method(self):
        """Set up test fixtures."""
        self.author = User(id="u1", name="Alice")
        self.channel = Channel(id="c1", name="general")
        self.target_channel = Channel(id="c2", name="logs")
        self.thread = Thread(id="t1")
        self.message = Message(
            id="m1",
            content="Hello world",
            author=self.author,
            channel=self.channel,
            backend="test",
        )
        self.threaded_message = Message(
            id="m2",
            content="Thread reply",
            author=self.author,
            channel=self.channel,
            thread=self.thread,
            backend="test",
        )

    def test_as_reply(self):
        """Test as_reply creates a new reply message."""
        result = self.message.as_reply("My reply")
        assert isinstance(result, Message)
        assert result.content == "My reply"
        assert result.channel is self.channel
        assert result.reply_to is self.message
        assert result.message_type == MessageType.REPLY
        assert result.backend == "test"

    def test_as_reply_with_extra_kwargs(self):
        """Test as_reply passes through extra kwargs."""
        result = self.message.as_reply("My reply", is_pinned=True)
        assert isinstance(result, Message)
        assert result.content == "My reply"
        assert result.is_pinned is True

    def test_as_thread_reply_on_regular_message(self):
        """Test as_thread_reply on non-threaded message creates thread."""
        result = self.message.as_thread_reply("Continue thread")
        assert isinstance(result, Message)
        assert result.content == "Continue thread"
        assert result.channel is self.channel
        assert result.thread is not None
        assert result.thread.id == "m1"  # Thread from parent message
        assert result.reply_to is self.message
        assert result.message_type == MessageType.REPLY

    def test_as_thread_reply_on_threaded_message(self):
        """Test as_thread_reply on threaded message continues thread."""
        result = self.threaded_message.as_thread_reply("Continue thread")
        assert isinstance(result, Message)
        assert result.content == "Continue thread"
        assert result.channel is self.channel
        assert result.thread is self.thread  # Uses existing thread

    def test_as_forward(self):
        """Test as_forward creates a forwarded message."""
        result = self.message.as_forward(self.target_channel)
        assert isinstance(result, Message)
        assert result.channel is self.target_channel
        assert result.forwarded_from is self.message
        assert result.message_type == MessageType.FORWARD
        assert "Forwarded from Alice in #general" in result.content
        assert "Hello world" in result.content
        assert result.backend == "test"

    def test_as_forward_with_extra_kwargs(self):
        """Test as_forward passes through extra kwargs."""
        result = self.message.as_forward(self.target_channel, is_pinned=True)
        assert isinstance(result, Message)
        assert result.channel is self.target_channel
        assert result.is_pinned is True

    def test_as_quote_reply(self):
        """Test as_quote_reply creates quoted message."""
        result = self.message.as_quote_reply("I agree!")
        assert isinstance(result, Message)
        assert result.channel is self.channel
        assert "> Hello world" in result.content
        assert "I agree!" in result.content
        assert result.reply_to is self.message
        assert result.thread is not None
        assert result.message_type == MessageType.REPLY

    def test_as_quote_reply_multiline(self):
        """Test as_quote_reply handles multiline content."""
        multi = Message(
            id="m3",
            content="Line 1\nLine 2\nLine 3",
            author=self.author,
            channel=self.channel,
        )
        result = multi.as_quote_reply("My response")
        assert isinstance(result, Message)
        assert "> Line 1" in result.content
        assert "> Line 2" in result.content
        assert "> Line 3" in result.content
        assert "My response" in result.content

    def test_reply_context(self):
        """Test reply_context returns useful context dict."""
        result = self.message.reply_context()
        assert result["channel"] is self.channel
        assert result["message"] is self.message
        assert result["thread"] is None  # No thread on this message
        assert result["author"] is self.author

    def test_reply_context_with_thread(self):
        """Test reply_context uses existing thread object."""
        result = self.threaded_message.reply_context()
        assert result["thread"] is self.thread
        assert result["message"] is self.threaded_message

    def test_as_reply_preserves_subclass(self):
        """Test that as_reply returns same class as original."""

        # Create a subclass instance
        class CustomMessage(Message):
            pass

        custom = CustomMessage(
            id="c1",
            content="Custom",
            channel=self.channel,
        )
        result = custom.as_reply("Reply")
        assert isinstance(result, CustomMessage)
        assert type(result) is CustomMessage

    def test_as_dm_to_author(self):
        """Test as_dm_to_author creates DM message to original author."""
        result = self.message.as_dm_to_author("Private message")
        assert isinstance(result, Message)
        assert result.content == "Private message"
        # Channel should be a DM to the author
        assert result.channel.channel_type == ChannelType.DIRECT
        assert result.channel.users == [self.author]
        assert result.channel.is_incomplete
        assert not result.channel.id  # No ID until resolved

    def test_as_dm_to_author_with_extra_kwargs(self):
        """Test as_dm_to_author passes through extra kwargs."""
        result = self.message.as_dm_to_author("Secret", is_pinned=True)
        assert isinstance(result, Message)
        assert result.content == "Secret"
        assert result.channel.channel_type == ChannelType.DIRECT
        assert result.is_pinned is True
