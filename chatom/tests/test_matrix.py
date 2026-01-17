"""Tests for Matrix-specific models.

This module tests the Matrix backend implementation including
MatrixUser, MatrixChannel/MatrixRoom, MatrixMessage, and related enums.
"""

from chatom.matrix import (
    # Channel/Room
    MatrixChannel,
    MatrixEventType,
    MatrixGuestAccess,
    MatrixJoinRule,
    # Message
    MatrixMessage,
    MatrixMessageFormat,
    MatrixMessageType,
    # Presence
    MatrixPresence,
    MatrixPresenceStatus,
    MatrixRelationType,
    MatrixRoom,
    MatrixRoomType,
    MatrixRoomVisibility,
    # User
    MatrixUser,
    create_pill,
    mention_room,
    # Mention utilities
    mention_user,
)


class TestMatrixUser:
    """Tests for MatrixUser model."""

    def test_create_basic_user(self):
        """Test creating a basic MatrixUser."""
        user = MatrixUser(
            id="@alice:matrix.org",
            user_id="@alice:matrix.org",
            name="Alice",
            handle="alice",
            homeserver="matrix.org",
        )
        assert user.id == "@alice:matrix.org"
        assert user.user_id == "@alice:matrix.org"
        assert user.name == "Alice"
        assert user.handle == "alice"
        assert user.homeserver == "matrix.org"

    def test_localpart_property(self):
        """Test localpart extraction from user_id."""
        user = MatrixUser(user_id="@alice:matrix.org")
        assert user.localpart == "alice"

    def test_localpart_fallback_to_handle(self):
        """Test localpart fallback when user_id is empty."""
        user = MatrixUser(handle="alice")
        assert user.localpart == "alice"

    def test_full_user_id_from_user_id(self):
        """Test full_user_id when user_id is set."""
        user = MatrixUser(user_id="@alice:matrix.org")
        assert user.full_user_id == "@alice:matrix.org"

    def test_full_user_id_constructed(self):
        """Test full_user_id construction from handle and homeserver."""
        user = MatrixUser(handle="alice", homeserver="matrix.org")
        assert user.full_user_id == "@alice:matrix.org"

    def test_server_name_from_user_id(self):
        """Test server_name extraction from user_id."""
        user = MatrixUser(user_id="@alice:matrix.org")
        assert user.server_name == "matrix.org"

    def test_server_name_fallback(self):
        """Test server_name fallback to homeserver field."""
        user = MatrixUser(homeserver="matrix.org")
        assert user.server_name == "matrix.org"

    def test_mxid_alias(self):
        """Test mxid is alias for full_user_id."""
        user = MatrixUser(user_id="@alice:matrix.org")
        assert user.mxid == user.full_user_id

    def test_display_name_property(self):
        """Test display_name property from base class."""
        user = MatrixUser(name="Alice Smith", handle="alice")
        assert user.display_name == "Alice Smith"

    def test_display_name_fallback(self):
        """Test display_name fallback."""
        user = MatrixUser(handle="alice")
        assert user.display_name == "alice"

    def test_avatar_mxc(self):
        """Test avatar_mxc field."""
        user = MatrixUser(avatar_mxc="mxc://matrix.org/abc123")
        assert user.avatar_mxc == "mxc://matrix.org/abc123"

    def test_get_avatar_http_url(self):
        """Test converting MXC avatar URL to HTTP URL."""
        user = MatrixUser(avatar_mxc="mxc://matrix.org/abc123")
        url = user.get_avatar_http_url("https://matrix.org")
        assert url == "https://matrix.org/_matrix/media/r0/download/matrix.org/abc123"

    def test_get_avatar_http_url_default_server(self):
        """Test converting MXC URL with default server."""
        user = MatrixUser(avatar_mxc="mxc://matrix.org/abc123")
        url = user.get_avatar_http_url()
        assert url == "https://matrix.org/_matrix/media/r0/download/matrix.org/abc123"

    def test_guest_user(self):
        """Test guest user flag."""
        user = MatrixUser(is_guest=True)
        assert user.is_guest is True

    def test_deactivated_user(self):
        """Test deactivated user flag."""
        user = MatrixUser(deactivated=True)
        assert user.deactivated is True

    def test_currently_active(self):
        """Test currently_active field."""
        user = MatrixUser(currently_active=True, last_active_ago=1000)
        assert user.currently_active is True
        assert user.last_active_ago == 1000


class TestMatrixChannel:
    """Tests for MatrixChannel/MatrixRoom model."""

    def test_create_basic_channel(self):
        """Test creating a basic MatrixChannel."""
        channel = MatrixChannel(
            id="!abc123:matrix.org",
            room_id="!abc123:matrix.org",
            name="General",
        )
        assert channel.id == "!abc123:matrix.org"
        assert channel.room_id == "!abc123:matrix.org"
        assert channel.name == "General"

    def test_matrix_room_alias(self):
        """Test MatrixRoom is alias for MatrixChannel."""
        assert MatrixRoom is MatrixChannel
        room = MatrixRoom(id="!abc:matrix.org")
        assert isinstance(room, MatrixChannel)

    def test_display_name_from_name(self):
        """Test display_name returns room name."""
        channel = MatrixChannel(name="General Chat")
        assert channel.display_name == "General Chat"

    def test_display_name_from_canonical_alias(self):
        """Test display_name fallback to canonical_alias."""
        channel = MatrixChannel(canonical_alias="#general:matrix.org")
        assert channel.display_name == "#general:matrix.org"

    def test_display_name_from_room_id(self):
        """Test display_name fallback to room_id."""
        channel = MatrixChannel(room_id="!abc123:matrix.org")
        assert channel.display_name == "!abc123:matrix.org"

    def test_homeserver_extraction(self):
        """Test homeserver property."""
        channel = MatrixChannel(room_id="!abc123:matrix.org")
        assert channel.homeserver == "matrix.org"

    def test_aliases(self):
        """Test room aliases."""
        channel = MatrixChannel(
            aliases=["#general:matrix.org", "#chat:matrix.org"],
            canonical_alias="#general:matrix.org",
        )
        assert len(channel.aliases) == 2
        assert channel.canonical_alias == "#general:matrix.org"

    def test_room_type_default(self):
        """Test default room type."""
        channel = MatrixChannel()
        assert channel.room_type == MatrixRoomType.DEFAULT

    def test_room_type_space(self):
        """Test space room type."""
        channel = MatrixChannel(room_type=MatrixRoomType.SPACE)
        assert channel.room_type == MatrixRoomType.SPACE
        assert channel.is_space is True

    def test_join_rule_public(self):
        """Test public join rule."""
        channel = MatrixChannel(join_rule=MatrixJoinRule.PUBLIC)
        assert channel.join_rule == MatrixJoinRule.PUBLIC
        assert channel.is_public is True
        assert channel.is_invite_only is False

    def test_join_rule_invite(self):
        """Test invite-only join rule."""
        channel = MatrixChannel(join_rule=MatrixJoinRule.INVITE)
        assert channel.join_rule == MatrixJoinRule.INVITE
        assert channel.is_invite_only is True
        assert channel.is_public is False

    def test_guest_access(self):
        """Test guest access settings."""
        channel = MatrixChannel(guest_access=MatrixGuestAccess.CAN_JOIN)
        assert channel.guest_access == MatrixGuestAccess.CAN_JOIN

    def test_visibility(self):
        """Test room visibility."""
        channel = MatrixChannel(visibility=MatrixRoomVisibility.PUBLIC)
        assert channel.visibility == MatrixRoomVisibility.PUBLIC

    def test_encrypted_room(self):
        """Test encrypted room flag."""
        channel = MatrixChannel(encrypted=True)
        assert channel.encrypted is True
        assert channel.is_encrypted is True

    def test_federated_room(self):
        """Test federated room flag."""
        channel = MatrixChannel(federated=True)
        assert channel.federated is True

    def test_power_levels(self):
        """Test power levels dict."""
        power_levels = {
            "users": {"@admin:matrix.org": 100, "@mod:matrix.org": 50},
            "events_default": 0,
            "state_default": 50,
        }
        channel = MatrixChannel(power_levels=power_levels)
        assert channel.power_levels["users"]["@admin:matrix.org"] == 100

    def test_members_dict(self):
        """Test members dictionary (user_id -> displayname)."""
        channel = MatrixChannel(members={"@alice:matrix.org": "Alice", "@bob:matrix.org": "Bob"})
        assert len(channel.members) == 2
        assert "@alice:matrix.org" in channel.members
        assert channel.members["@alice:matrix.org"] == "Alice"

    def test_prev_batch_for_pagination(self):
        """Test prev_batch token for pagination."""
        channel = MatrixChannel(prev_batch="s12345_67890")
        assert channel.prev_batch == "s12345_67890"

    def test_unread_counts(self):
        """Test unread and highlight counts."""
        channel = MatrixChannel(unread_count=5, highlight_count=2)
        assert channel.unread_count == 5
        assert channel.highlight_count == 2

    def test_direct_message_room(self):
        """Test direct message room flag."""
        channel = MatrixChannel(direct=True)
        assert channel.direct is True

    def test_avatar_mxc(self):
        """Test room avatar MXC URI."""
        channel = MatrixChannel(avatar_mxc="mxc://matrix.org/roomavatar")
        assert channel.avatar_mxc == "mxc://matrix.org/roomavatar"

    def test_predecessor_room(self):
        """Test predecessor room for room upgrades."""
        channel = MatrixChannel(
            predecessor_room_id="!old123:matrix.org",
            version="6",
        )
        assert channel.predecessor_room_id == "!old123:matrix.org"
        assert channel.version == "6"

    def test_generic_channel_type_dm(self):
        """Test generic channel type for DM."""
        from chatom.base import ChannelType

        channel = MatrixChannel(direct=True)
        assert channel.generic_channel_type == ChannelType.DIRECT

    def test_generic_channel_type_group(self):
        """Test generic channel type for private room."""
        from chatom.base import ChannelType

        channel = MatrixChannel(join_rule=MatrixJoinRule.INVITE, direct=False)
        # Invite-only non-DM rooms are PRIVATE in the generic type
        assert channel.generic_channel_type == ChannelType.PRIVATE

    def test_generic_channel_type_public(self):
        """Test generic channel type for public room."""
        from chatom.base import ChannelType

        channel = MatrixChannel(join_rule=MatrixJoinRule.PUBLIC)
        assert channel.generic_channel_type == ChannelType.PUBLIC


class TestMatrixMessage:
    """Tests for MatrixMessage model."""

    def test_create_basic_message(self):
        """Test creating a basic MatrixMessage."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            room_id="!room:matrix.org",
            sender="@alice:matrix.org",
            text="Hello, world!",
        )
        assert msg.event_id == "$abc123"
        assert msg.room_id == "!room:matrix.org"
        assert msg.sender == "@alice:matrix.org"
        assert msg.text == "Hello, world!"

    def test_default_msgtype(self):
        """Test default msgtype is m.text."""
        msg = MatrixMessage()
        assert msg.msgtype == "m.text"
        assert msg.event_type == "m.room.message"

    def test_is_text(self):
        """Test is_text property."""
        msg = MatrixMessage(msgtype="m.text")
        assert msg.is_text is True
        assert msg.is_notice is False

    def test_is_notice(self):
        """Test is_notice property."""
        msg = MatrixMessage(msgtype="m.notice")
        assert msg.is_notice is True
        assert msg.is_text is False

    def test_is_emote(self):
        """Test is_emote property."""
        msg = MatrixMessage(msgtype="m.emote")
        assert msg.is_emote is True

    def test_is_media_image(self):
        """Test is_media for image."""
        msg = MatrixMessage(msgtype="m.image")
        assert msg.is_media is True

    def test_is_media_file(self):
        """Test is_media for file."""
        msg = MatrixMessage(msgtype="m.file")
        assert msg.is_media is True

    def test_is_media_audio(self):
        """Test is_media for audio."""
        msg = MatrixMessage(msgtype="m.audio")
        assert msg.is_media is True

    def test_is_media_video(self):
        """Test is_media for video."""
        msg = MatrixMessage(msgtype="m.video")
        assert msg.is_media is True

    def test_is_location(self):
        """Test is_location property."""
        msg = MatrixMessage(msgtype="m.location", geo_uri="geo:51.5,-0.1")
        assert msg.is_location is True
        assert msg.geo_uri == "geo:51.5,-0.1"

    def test_formatted_body(self):
        """Test HTML formatted body."""
        msg = MatrixMessage(
            text="Hello *world*",
            format="org.matrix.custom.html",
            formatted_body="Hello <b>world</b>",
        )
        assert msg.has_html is True
        assert msg.formatted_body == "Hello <b>world</b>"

    def test_reply_message(self):
        """Test reply to another message."""
        msg = MatrixMessage(
            in_reply_to_event_id="$original123",
            text="This is a reply",
        )
        assert msg.is_reply is True
        assert msg.in_reply_to_event_id == "$original123"

    def test_edit_message(self):
        """Test message edit."""
        msg = MatrixMessage(
            replaces_event_id="$original123",
            text="Edited text",
        )
        assert msg.is_edit is True
        assert msg.replaces_event_id == "$original123"

    def test_threaded_message(self):
        """Test threaded message."""
        msg = MatrixMessage(
            thread_root_event_id="$thread_root",
            text="Message in thread",
        )
        assert msg.is_threaded is True
        assert msg.thread_root_event_id == "$thread_root"

    def test_encrypted_message(self):
        """Test encrypted message detection."""
        msg = MatrixMessage(event_type="m.room.encrypted")
        assert msg.is_encrypted is True

    def test_redacted_message(self):
        """Test redacted message."""
        msg = MatrixMessage(redacted=True, redacted_by="$redact_event")
        assert msg.is_redacted is True
        assert msg.redacted_by == "$redact_event"

    def test_file_attachment(self):
        """Test file attachment fields."""
        msg = MatrixMessage(
            msgtype="m.file",
            file_url="mxc://matrix.org/file123",
            file_name="document.pdf",
            file_info={"size": 1024, "mimetype": "application/pdf"},
        )
        assert msg.file_url == "mxc://matrix.org/file123"
        assert msg.file_name == "document.pdf"
        assert msg.file_info["size"] == 1024

    def test_get_file_http_url(self):
        """Test converting file MXC to HTTP URL."""
        msg = MatrixMessage(file_url="mxc://matrix.org/file123")
        url = msg.get_file_http_url("https://matrix.org")
        assert url == "https://matrix.org/_matrix/media/r0/download/matrix.org/file123"

    def test_thumbnail(self):
        """Test thumbnail fields."""
        msg = MatrixMessage(
            thumbnail_url="mxc://matrix.org/thumb123",
            thumbnail_info={"w": 100, "h": 100},
        )
        assert msg.thumbnail_url == "mxc://matrix.org/thumb123"
        assert msg.thumbnail_info["w"] == 100

    def test_get_thumbnail_http_url(self):
        """Test converting thumbnail MXC to HTTP URL."""
        msg = MatrixMessage(thumbnail_url="mxc://matrix.org/thumb123")
        url = msg.get_thumbnail_http_url("https://matrix.org")
        assert url == "https://matrix.org/_matrix/media/r0/download/matrix.org/thumb123"

    def test_origin_server_ts(self):
        """Test origin server timestamp."""
        msg = MatrixMessage(origin_server_ts=1699999999999)
        assert msg.origin_server_ts == 1699999999999

    def test_unsigned_data(self):
        """Test unsigned event metadata."""
        msg = MatrixMessage(unsigned={"age": 1234, "transaction_id": "tx123"})
        assert msg.age_ms == 1234
        assert msg.unsigned["transaction_id"] == "tx123"

    def test_server_name_from_room_id(self):
        """Test server_name extraction from room_id."""
        msg = MatrixMessage(room_id="!room:matrix.org")
        assert msg.server_name == "matrix.org"

    def test_sender_localpart(self):
        """Test sender_localpart extraction."""
        msg = MatrixMessage(sender="@alice:matrix.org")
        assert msg.sender_localpart == "alice"

    def test_from_event(self):
        """Test creating MatrixMessage from event dict."""
        event = {
            "event_id": "$abc123",
            "room_id": "!room:matrix.org",
            "sender": "@alice:matrix.org",
            "type": "m.room.message",
            "origin_server_ts": 1699999999999,
            "content": {
                "msgtype": "m.text",
                "body": "Hello, world!",
                "format": "org.matrix.custom.html",
                "formatted_body": "<b>Hello</b>, world!",
            },
            "unsigned": {"age": 1234},
        }
        msg = MatrixMessage.from_event(event)
        assert msg.event_id == "$abc123"
        assert msg.room_id == "!room:matrix.org"
        assert msg.sender == "@alice:matrix.org"
        assert msg.text == "Hello, world!"
        assert msg.msgtype == "m.text"
        assert msg.has_html is True
        assert msg.age_ms == 1234

    def test_from_event_with_reply(self):
        """Test creating MatrixMessage from reply event."""
        event = {
            "event_id": "$reply123",
            "room_id": "!room:matrix.org",
            "sender": "@alice:matrix.org",
            "type": "m.room.message",
            "content": {
                "msgtype": "m.text",
                "body": "This is a reply",
                "m.relates_to": {
                    "m.in_reply_to": {"event_id": "$original123"},
                },
            },
        }
        msg = MatrixMessage.from_event(event)
        assert msg.is_reply is True
        assert msg.in_reply_to_event_id == "$original123"

    def test_from_event_with_edit(self):
        """Test creating MatrixMessage from edit event."""
        event = {
            "event_id": "$edit123",
            "room_id": "!room:matrix.org",
            "sender": "@alice:matrix.org",
            "type": "m.room.message",
            "content": {
                "msgtype": "m.text",
                "body": "* Edited text",
                "m.relates_to": {
                    "rel_type": "m.replace",
                    "event_id": "$original123",
                },
            },
        }
        msg = MatrixMessage.from_event(event)
        assert msg.is_edit is True
        assert msg.replaces_event_id == "$original123"

    def test_from_event_redacted(self):
        """Test creating MatrixMessage from redacted event."""
        event = {
            "event_id": "$redacted123",
            "room_id": "!room:matrix.org",
            "sender": "@alice:matrix.org",
            "type": "m.room.message",
            "content": {},
            "unsigned": {
                "redacted_because": {"event_id": "$redact_event"},
            },
        }
        msg = MatrixMessage.from_event(event)
        assert msg.is_redacted is True
        assert msg.redacted_by == "$redact_event"

    def test_to_content_text(self):
        """Test converting message to content dict."""
        msg = MatrixMessage(text="Hello, world!", msgtype="m.text")
        content = msg.to_content()
        assert content["msgtype"] == "m.text"
        assert content["body"] == "Hello, world!"

    def test_to_content_with_html(self):
        """Test converting message with HTML to content dict."""
        msg = MatrixMessage(
            text="Hello *world*",
            formatted_body="Hello <b>world</b>",
            format="org.matrix.custom.html",
        )
        content = msg.to_content()
        assert content["format"] == "org.matrix.custom.html"
        assert content["formatted_body"] == "Hello <b>world</b>"

    def test_to_content_with_file(self):
        """Test converting file message to content dict."""
        msg = MatrixMessage(
            msgtype="m.file",
            text="document.pdf",
            file_url="mxc://matrix.org/file123",
            file_name="document.pdf",
            file_info={"size": 1024, "mimetype": "application/pdf"},
        )
        content = msg.to_content()
        assert content["url"] == "mxc://matrix.org/file123"
        assert content["filename"] == "document.pdf"
        assert content["info"]["size"] == 1024

    def test_to_content_with_reply(self):
        """Test converting reply to content dict."""
        msg = MatrixMessage(
            text="This is a reply",
            in_reply_to_event_id="$original123",
        )
        content = msg.to_content()
        assert "m.relates_to" in content
        assert content["m.relates_to"]["m.in_reply_to"]["event_id"] == "$original123"


class TestMatrixEnums:
    """Tests for Matrix enum types."""

    def test_message_type_values(self):
        """Test MatrixMessageType enum values."""
        assert MatrixMessageType.TEXT.value == "m.text"
        assert MatrixMessageType.NOTICE.value == "m.notice"
        assert MatrixMessageType.EMOTE.value == "m.emote"
        assert MatrixMessageType.IMAGE.value == "m.image"
        assert MatrixMessageType.FILE.value == "m.file"
        assert MatrixMessageType.AUDIO.value == "m.audio"
        assert MatrixMessageType.VIDEO.value == "m.video"
        assert MatrixMessageType.LOCATION.value == "m.location"

    def test_message_format_values(self):
        """Test MatrixMessageFormat enum values."""
        assert MatrixMessageFormat.HTML.value == "org.matrix.custom.html"

    def test_relation_type_values(self):
        """Test MatrixRelationType enum values."""
        assert MatrixRelationType.REPLY.value == "m.in_reply_to"
        assert MatrixRelationType.REPLACE.value == "m.replace"
        assert MatrixRelationType.THREAD.value == "m.thread"
        assert MatrixRelationType.ANNOTATION.value == "m.annotation"

    def test_event_type_values(self):
        """Test MatrixEventType enum values."""
        assert MatrixEventType.ROOM_MESSAGE.value == "m.room.message"
        assert MatrixEventType.ROOM_ENCRYPTED.value == "m.room.encrypted"
        assert MatrixEventType.ROOM_MEMBER.value == "m.room.member"
        assert MatrixEventType.REACTION.value == "m.reaction"

    def test_room_type_values(self):
        """Test MatrixRoomType enum values."""
        assert MatrixRoomType.DEFAULT.value == ""
        assert MatrixRoomType.SPACE.value == "m.space"

    def test_join_rule_values(self):
        """Test MatrixJoinRule enum values."""
        assert MatrixJoinRule.PUBLIC.value == "public"
        assert MatrixJoinRule.INVITE.value == "invite"
        assert MatrixJoinRule.KNOCK.value == "knock"
        assert MatrixJoinRule.RESTRICTED.value == "restricted"
        assert MatrixJoinRule.PRIVATE.value == "private"

    def test_guest_access_values(self):
        """Test MatrixGuestAccess enum values."""
        assert MatrixGuestAccess.CAN_JOIN.value == "can_join"
        assert MatrixGuestAccess.FORBIDDEN.value == "forbidden"

    def test_room_visibility_values(self):
        """Test MatrixRoomVisibility enum values."""
        assert MatrixRoomVisibility.PUBLIC.value == "public"
        assert MatrixRoomVisibility.PRIVATE.value == "private"


class TestMatrixPresence:
    """Tests for MatrixPresence model."""

    def test_create_presence(self):
        """Test creating MatrixPresence."""
        presence = MatrixPresence(
            user_id="@alice:matrix.org",
            status=MatrixPresenceStatus.ONLINE,
            status_message="Working",
        )
        assert presence.user_id == "@alice:matrix.org"
        assert presence.status == MatrixPresenceStatus.ONLINE
        assert presence.status_message == "Working"

    def test_presence_status_values(self):
        """Test MatrixPresenceStatus enum values."""
        assert MatrixPresenceStatus.ONLINE.value == "online"
        assert MatrixPresenceStatus.OFFLINE.value == "offline"
        assert MatrixPresenceStatus.UNAVAILABLE.value == "unavailable"

    def test_generic_status_online(self):
        """Test generic_status for online."""
        from chatom.base import PresenceStatus

        presence = MatrixPresence(matrix_presence=MatrixPresenceStatus.ONLINE)
        assert presence.generic_status == PresenceStatus.ONLINE

    def test_generic_status_offline(self):
        """Test generic_status for offline."""
        from chatom.base import PresenceStatus

        presence = MatrixPresence(matrix_presence=MatrixPresenceStatus.OFFLINE)
        assert presence.generic_status == PresenceStatus.OFFLINE

    def test_generic_status_unavailable(self):
        """Test generic_status for unavailable."""
        from chatom.base import PresenceStatus

        presence = MatrixPresence(matrix_presence=MatrixPresenceStatus.UNAVAILABLE)
        assert presence.generic_status == PresenceStatus.IDLE


class TestMatrixMentions:
    """Tests for Matrix mention utilities."""

    def test_mention_user_with_mxid(self):
        """Test mentioning user with Matrix ID via User object."""
        user = MatrixUser(user_id="@alice:matrix.org", name="Alice")
        result = mention_user(user)
        assert "@alice:matrix.org" in result or "Alice" in result

    def test_mention_user_with_user_object(self):
        """Test mentioning user with MatrixUser object."""
        user = MatrixUser(user_id="@alice:matrix.org", name="Alice")
        result = mention_user(user)
        assert "@alice:matrix.org" in result or "Alice" in result

    def test_mention_room_with_alias(self):
        """Test mentioning room with alias."""
        result = mention_room("#general:matrix.org")
        assert "#general:matrix.org" in result

    def test_create_pill_user(self):
        """Test creating Matrix pill for user."""
        pill = create_pill("@alice:matrix.org", "Alice")
        assert "alice" in pill.lower() or "@alice:matrix.org" in pill


class TestMatrixIntegration:
    """Integration tests for Matrix models working together."""

    def test_user_in_channel_members(self):
        """Test user ID in channel members dict."""
        user = MatrixUser(user_id="@alice:matrix.org")
        channel = MatrixChannel(
            room_id="!room:matrix.org",
            members={"@alice:matrix.org": "Alice", "@bob:matrix.org": "Bob"},
        )
        assert user.user_id in channel.members

    def test_message_references_room_and_user(self):
        """Test message with room and sender references."""
        user = MatrixUser(user_id="@alice:matrix.org", name="Alice")
        channel = MatrixChannel(room_id="!room:matrix.org", name="General")
        msg = MatrixMessage(
            event_id="$msg123",
            room_id=channel.room_id,
            sender=user.user_id,
            text="Hello!",
        )
        assert msg.room_id == channel.room_id
        assert msg.sender == user.user_id
        assert msg.sender_localpart == user.localpart

    def test_power_levels_user_check(self):
        """Test checking user power level in channel."""
        user = MatrixUser(user_id="@admin:matrix.org")
        channel = MatrixChannel(
            room_id="!room:matrix.org",
            power_levels={
                "users": {
                    "@admin:matrix.org": 100,
                    "@mod:matrix.org": 50,
                },
                "users_default": 0,
            },
        )
        assert channel.power_levels["users"].get(user.user_id) == 100

    def test_dm_room_detection(self):
        """Test detecting DM room."""
        channel = MatrixChannel(
            room_id="!dm:matrix.org",
            direct=True,
            join_rule=MatrixJoinRule.INVITE,
            members={"@alice:matrix.org": "Alice", "@bob:matrix.org": "Bob"},
        )
        assert channel.direct is True
        assert channel.is_invite_only is True
        assert len(channel.members) == 2


class TestMatrixMessageProperties:
    """Tests for MatrixMessage computed properties."""

    def test_sender_localpart_property(self):
        """Test sender_localpart extracts local part from sender."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            sender="@alice:matrix.org",
        )
        assert msg.sender_localpart == "alice"

    def test_sender_localpart_empty_without_sender(self):
        """Test sender_localpart returns empty string without sender."""
        msg = MatrixMessage(id="$abc123", event_id="$abc123")
        assert msg.sender_localpart == ""

    def test_sender_localpart_empty_invalid(self):
        """Test sender_localpart returns empty string for invalid sender."""
        msg = MatrixMessage(id="$abc123", event_id="$abc123", sender="invalid")
        assert msg.sender_localpart == ""

    def test_get_file_http_url(self):
        """Test get_file_http_url converts mxc URL."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            file_url="mxc://matrix.org/abc123",
        )
        url = msg.get_file_http_url()
        assert "matrix.org" in url
        assert "abc123" in url
        assert "_matrix/media" in url

    def test_get_file_http_url_with_homeserver(self):
        """Test get_file_http_url with custom homeserver."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            file_url="mxc://matrix.org/abc123",
        )
        url = msg.get_file_http_url("https://custom.server.org")
        assert "custom.server.org" in url

    def test_get_file_http_url_empty_without_file(self):
        """Test get_file_http_url returns empty string without file_url."""
        msg = MatrixMessage(id="$abc123", event_id="$abc123")
        assert msg.get_file_http_url() == ""

    def test_get_file_http_url_returns_http_url(self):
        """Test get_file_http_url returns http URL unchanged."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            file_url="https://matrix.org/media/abc123",
        )
        assert msg.get_file_http_url() == "https://matrix.org/media/abc123"

    def test_get_file_http_url_invalid_mxc(self):
        """Test get_file_http_url handles invalid mxc URL."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            file_url="mxc://invalid",
        )
        assert msg.get_file_http_url() == ""

    def test_get_thumbnail_http_url(self):
        """Test get_thumbnail_http_url converts mxc URL."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            thumbnail_url="mxc://matrix.org/thumb123",
        )
        url = msg.get_thumbnail_http_url()
        assert "matrix.org" in url
        assert "thumb123" in url
        assert "_matrix/media" in url

    def test_get_thumbnail_http_url_empty_without_thumbnail(self):
        """Test get_thumbnail_http_url returns empty without thumbnail."""
        msg = MatrixMessage(id="$abc123", event_id="$abc123")
        assert msg.get_thumbnail_http_url() == ""

    def test_get_thumbnail_http_url_returns_http(self):
        """Test get_thumbnail_http_url returns http URL unchanged."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            thumbnail_url="https://matrix.org/thumb/abc",
        )
        assert msg.get_thumbnail_http_url() == "https://matrix.org/thumb/abc"

    def test_get_thumbnail_http_url_invalid_mxc(self):
        """Test get_thumbnail_http_url handles invalid mxc URL."""
        msg = MatrixMessage(
            id="$abc123",
            event_id="$abc123",
            thumbnail_url="mxc://invalid",
        )
        assert msg.get_thumbnail_http_url() == ""
