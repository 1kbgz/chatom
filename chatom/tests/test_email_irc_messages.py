"""Tests for email and IRC message implementations."""

from datetime import datetime


class TestEmailAddress:
    """Tests for EmailAddress class."""

    def test_email_address_with_name(self):
        """Test EmailAddress with display name."""
        from chatom.email.message import EmailAddress

        addr = EmailAddress("john@example.com", "John Doe")
        assert addr.address == "john@example.com"
        assert addr.name == "John Doe"
        assert str(addr) == '"John Doe" <john@example.com>'

    def test_email_address_without_name(self):
        """Test EmailAddress without display name."""
        from chatom.email.message import EmailAddress

        addr = EmailAddress("john@example.com")
        assert addr.address == "john@example.com"
        assert addr.name is None
        assert str(addr) == "john@example.com"

    def test_email_address_repr(self):
        """Test EmailAddress repr."""
        from chatom.email.message import EmailAddress

        addr = EmailAddress("john@example.com", "John")
        result = repr(addr)
        assert "john@example.com" in result
        assert "John" in result


class TestEmailPriority:
    """Tests for EmailPriority enum."""

    def test_email_priority_values(self):
        """Test all EmailPriority values exist."""
        from chatom.email.message import EmailPriority

        assert EmailPriority.HIGHEST.value == "highest"
        assert EmailPriority.HIGH.value == "high"
        assert EmailPriority.NORMAL.value == "normal"
        assert EmailPriority.LOW.value == "low"
        assert EmailPriority.LOWEST.value == "lowest"


class TestEmailMessage:
    """Tests for EmailMessage class."""

    def test_create_email_message(self):
        """Test creating an email message."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="msg1",
            content="Hello World",
            subject="Test Subject",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
        )
        assert msg.subject == "Test Subject"
        assert msg.from_address == "sender@example.com"
        assert len(msg.to_addresses) == 1

    def test_email_body_property(self):
        """Test email body property prefers HTML."""
        from chatom.email.message import EmailMessage

        # HTML body takes precedence
        msg1 = EmailMessage(
            id="1",
            content="content",
            plain_body="plain",
            html_body="<b>html</b>",
        )
        assert msg1.body == "<b>html</b>"

        # Falls back to plain body
        msg2 = EmailMessage(
            id="2",
            content="content",
            plain_body="plain",
        )
        assert msg2.body == "plain"

        # Falls back to content
        msg3 = EmailMessage(
            id="3",
            content="content",
        )
        assert msg3.body == "content"

    def test_email_is_reply(self):
        """Test email is_reply property."""
        from chatom.email.message import EmailMessage

        msg1 = EmailMessage(id="1", content="Test", in_reply_to="<original@example.com>")
        assert msg1.is_reply is True

        msg2 = EmailMessage(id="2", content="Test")
        assert msg2.is_reply is False

    def test_email_is_thread(self):
        """Test email is_thread property."""
        from chatom.email.message import EmailMessage

        msg1 = EmailMessage(id="1", content="Test", in_reply_to="<original@example.com>")
        assert msg1.is_thread is True

        msg2 = EmailMessage(id="2", content="Test", references=["<msg1@example.com>", "<msg2@example.com>"])
        assert msg2.is_thread is True

        msg3 = EmailMessage(id="3", content="Test")
        assert msg3.is_thread is False

    def test_email_recipient_count(self):
        """Test email recipient_count property."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            to_addresses=["a@example.com", "b@example.com"],
            cc_addresses=["c@example.com"],
            bcc_addresses=["d@example.com"],
        )
        assert msg.recipient_count == 4

    def test_email_all_recipients(self):
        """Test email all_recipients property."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            to_addresses=["a@example.com"],
            cc_addresses=["b@example.com"],
            bcc_addresses=["c@example.com"],
        )
        assert len(msg.all_recipients) == 3
        assert "a@example.com" in msg.all_recipients
        assert "b@example.com" in msg.all_recipients
        assert "c@example.com" in msg.all_recipients

    def test_email_with_priority(self):
        """Test email with priority."""
        from chatom.email.message import EmailMessage, EmailPriority

        msg = EmailMessage(id="1", content="Urgent!", priority=EmailPriority.HIGH)
        assert msg.priority == EmailPriority.HIGH

    def test_email_flags(self):
        """Test email flags."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            is_read=True,
            is_flagged=True,
            is_draft=False,
        )
        assert msg.is_read is True
        assert msg.is_flagged is True
        assert msg.is_draft is False

    def test_email_folder_and_labels(self):
        """Test email folder and labels."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            folder="INBOX",
            labels=["important", "work"],
        )
        assert msg.folder == "INBOX"
        assert len(msg.labels) == 2
        assert "important" in msg.labels

    def test_email_date(self):
        """Test email date field."""
        from chatom.email.message import EmailMessage

        now = datetime.now()
        msg = EmailMessage(id="1", content="Test", date=now)
        assert msg.date == now

    def test_email_headers(self):
        """Test email headers."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            headers={"X-Custom-Header": "custom value", "X-Priority": "1"},
        )
        assert msg.headers["X-Custom-Header"] == "custom value"


class TestIRCMessageType:
    """Tests for IRCMessageType enum."""

    def test_irc_message_type_values(self):
        """Test all IRCMessageType values exist."""
        from chatom.irc.message import IRCMessageType

        assert IRCMessageType.PRIVMSG.value == "PRIVMSG"
        assert IRCMessageType.NOTICE.value == "NOTICE"
        assert IRCMessageType.ACTION.value == "ACTION"
        assert IRCMessageType.CTCP.value == "CTCP"
        assert IRCMessageType.CTCP_REPLY.value == "CTCP_REPLY"


class TestIRCMessage:
    """Tests for IRCMessage class."""

    def test_create_irc_message(self):
        """Test creating an IRC message."""
        from chatom.irc.message import IRCMessage

        msg = IRCMessage(
            id="1",
            content="Hello World",
            target="#channel",
            nick="sender",
        )
        assert msg.content == "Hello World"
        assert msg.target == "#channel"
        assert msg.nick == "sender"

    def test_irc_is_channel_message(self):
        """Test IRC is_channel_message property."""
        from chatom.irc.message import IRCMessage

        msg1 = IRCMessage(id="1", content="Hi", target="#channel")
        assert msg1.is_channel_message is True

        msg2 = IRCMessage(id="2", content="Hi", target="&channel")
        assert msg2.is_channel_message is True

        msg3 = IRCMessage(id="3", content="Hi", target="user")
        assert msg3.is_channel_message is False

    def test_irc_is_private_message(self):
        """Test IRC is_private_message property."""
        from chatom.irc.message import IRCMessage

        msg1 = IRCMessage(id="1", content="Hi", target="user")
        assert msg1.is_private_message is True

        msg2 = IRCMessage(id="2", content="Hi", target="#channel")
        assert msg2.is_private_message is False

    def test_irc_is_ctcp(self):
        """Test IRC is_ctcp property."""
        from chatom.irc.message import IRCMessage

        msg1 = IRCMessage(id="1", content="Hi", target="#channel", ctcp_command="VERSION")
        assert msg1.is_ctcp is True

        msg2 = IRCMessage(id="2", content="Hi", target="#channel")
        assert msg2.is_ctcp is False

    def test_irc_is_action(self):
        """Test IRC action message."""
        from chatom.irc.message import IRCMessage, IRCMessageType

        msg = IRCMessage(
            id="1",
            content="waves hello",
            target="#channel",
            message_type=IRCMessageType.ACTION,
            is_action=True,
        )
        assert msg.is_action is True
        assert msg.message_type == IRCMessageType.ACTION

    def test_irc_is_notice(self):
        """Test IRC notice message."""
        from chatom.irc.message import IRCMessage, IRCMessageType

        msg = IRCMessage(
            id="1",
            content="Server notice",
            target="user",
            message_type=IRCMessageType.NOTICE,
            is_notice=True,
        )
        assert msg.is_notice is True
        assert msg.message_type == IRCMessageType.NOTICE

    def test_irc_from_raw_privmsg(self):
        """Test parsing IRC PRIVMSG from raw."""
        from chatom.irc.message import IRCMessage, IRCMessageType

        raw = ":nick!user@host PRIVMSG #channel :Hello world"
        msg = IRCMessage.from_raw(raw)
        assert msg.nick == "nick"
        assert msg.username == "user"
        assert msg.host == "host"
        assert msg.target == "#channel"
        assert msg.content == "Hello world"
        assert msg.message_type == IRCMessageType.PRIVMSG

    def test_irc_from_raw_notice(self):
        """Test parsing IRC NOTICE from raw."""
        from chatom.irc.message import IRCMessage, IRCMessageType

        raw = ":server NOTICE user :Server notice"
        msg = IRCMessage.from_raw(raw)
        assert msg.is_notice is True
        assert msg.message_type == IRCMessageType.NOTICE

    def test_irc_from_raw_action(self):
        """Test parsing IRC ACTION from raw."""
        from chatom.irc.message import IRCMessage, IRCMessageType

        raw = ":nick!user@host PRIVMSG #channel :\x01ACTION waves\x01"
        msg = IRCMessage.from_raw(raw)
        assert msg.is_action is True
        assert msg.message_type == IRCMessageType.ACTION
        assert msg.content == "waves"

    def test_irc_from_raw_ctcp(self):
        """Test parsing IRC CTCP from raw."""
        from chatom.irc.message import IRCMessage, IRCMessageType

        raw = ":nick!user@host PRIVMSG bot :\x01VERSION\x01"
        msg = IRCMessage.from_raw(raw)
        assert msg.is_ctcp is True
        assert msg.ctcp_command == "VERSION"
        assert msg.message_type == IRCMessageType.CTCP

    def test_irc_from_raw_ctcp_with_params(self):
        """Test parsing IRC CTCP with parameters."""
        from chatom.irc.message import IRCMessage

        raw = ":nick!user@host PRIVMSG bot :\x01PING 12345\x01"
        msg = IRCMessage.from_raw(raw)
        assert msg.ctcp_command == "PING"
        assert msg.ctcp_params == "12345"

    def test_irc_from_raw_simple_prefix(self):
        """Test parsing IRC message with simple prefix."""
        from chatom.irc.message import IRCMessage

        raw = ":server PRIVMSG #channel :Message"
        msg = IRCMessage.from_raw(raw)
        assert msg.nick == "server"
        assert msg.username is None
        assert msg.host is None

    def test_irc_from_raw_prefix_with_host(self):
        """Test parsing IRC message with nick@host prefix."""
        from chatom.irc.message import IRCMessage

        raw = ":nick@host PRIVMSG #channel :Message"
        msg = IRCMessage.from_raw(raw)
        assert msg.nick == "nick"
        assert msg.host == "host"

    def test_irc_prefix_property(self):
        """Test IRC message prefix property."""
        from chatom.irc.message import IRCMessage

        msg = IRCMessage(
            id="1",
            content="Hi",
            target="#channel",
            prefix="nick!user@host",
        )
        assert msg.prefix == "nick!user@host"


class TestEmailMessageToFormatted:
    """Tests for EmailMessage.to_formatted method."""

    def test_email_to_formatted_with_html(self):
        """Test converting email with HTML body to formatted."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="fallback",
            html_body="<b>Bold text</b>",
        )
        fm = msg.to_formatted()
        assert fm is not None
        assert len(fm.content) > 0

    def test_email_to_formatted_with_plain(self):
        """Test converting email with plain body to formatted."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="fallback",
            plain_body="Plain text content",
        )
        fm = msg.to_formatted()
        assert fm is not None

    def test_email_to_formatted_with_content_only(self):
        """Test converting email with only content to formatted."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Just content",
        )
        fm = msg.to_formatted()
        assert fm is not None


class TestIRCMessageToFormatted:
    """Tests for IRCMessage.to_formatted method."""

    def test_irc_to_formatted(self):
        """Test converting IRC message to formatted."""
        from chatom.irc.message import IRCMessage

        msg = IRCMessage(
            id="1",
            content="Hello world",
            target="#channel",
        )
        fm = msg.to_formatted()
        assert fm is not None
        assert len(fm.content) > 0

    def test_irc_action_to_formatted(self):
        """Test converting IRC action to formatted."""
        from chatom.irc.message import IRCMessage

        msg = IRCMessage(
            id="1",
            content="waves hello",
            target="#channel",
            is_action=True,
            nick="user",
        )
        fm = msg.to_formatted()
        assert fm is not None


class TestEmailMessageToFormattedMetadata:
    """Tests for EmailMessage.to_formatted metadata."""

    def test_email_to_formatted_with_subject(self):
        """Test email to formatted includes subject in metadata."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            subject="Important Subject",
        )
        fm = msg.to_formatted()
        assert fm.metadata["subject"] == "Important Subject"

    def test_email_to_formatted_with_addresses(self):
        """Test email to formatted includes addresses in metadata."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            from_address="sender@example.com",
            to_addresses=["a@example.com", "b@example.com"],
            cc_addresses=["c@example.com"],
        )
        fm = msg.to_formatted()
        assert fm.metadata["from_address"] == "sender@example.com"
        assert "a@example.com" in fm.metadata["to_addresses"]
        assert "c@example.com" in fm.metadata["cc_addresses"]

    def test_email_to_formatted_with_threading(self):
        """Test email to formatted includes threading info."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            in_reply_to="<original@example.com>",
            references=["<msg1@example.com>", "<msg2@example.com>"],
        )
        fm = msg.to_formatted()
        assert fm.metadata["in_reply_to"] == "<original@example.com>"
        assert len(fm.metadata["references"]) == 2

    def test_email_to_formatted_with_folder(self):
        """Test email to formatted includes folder info."""
        from chatom.email.message import EmailMessage

        msg = EmailMessage(
            id="1",
            content="Test",
            folder="INBOX",
        )
        fm = msg.to_formatted()
        assert fm.metadata["folder"] == "INBOX"
        assert fm.metadata["channel_id"] == "INBOX"

    def test_email_to_formatted_includes_priority(self):
        """Test email to formatted includes priority."""
        from chatom.email.message import EmailMessage, EmailPriority

        msg = EmailMessage(id="1", content="Test", priority=EmailPriority.HIGH)
        fm = msg.to_formatted()
        assert fm.metadata["priority"] == "high"


class TestEmailMessageFromFormatted:
    """Tests for EmailMessage.from_formatted method."""

    def test_email_from_formatted_basic(self):
        """Test creating EmailMessage from FormattedMessage."""
        from chatom.email.message import EmailMessage
        from chatom.format import FormattedMessage

        fm = FormattedMessage()
        fm.add_text("Hello world")

        msg = EmailMessage.from_formatted(fm, id="msg1", subject="Test Subject")
        assert msg.plain_body == "Hello world"
        assert msg.html_body is not None
        assert msg.subject == "Test Subject"
        assert msg.backend == "email"

    def test_email_from_formatted_preserves_metadata(self):
        """Test that metadata is preserved."""
        from chatom.email.message import EmailMessage
        from chatom.format import FormattedMessage

        fm = FormattedMessage()
        fm.add_text("Test")
        fm.metadata["custom"] = "value"

        msg = EmailMessage.from_formatted(fm, id="1")
        assert msg.metadata["custom"] == "value"


class TestMatrixMentions:
    """Tests for Matrix mention utilities."""

    def test_mention_matrix_user_with_user_id(self):
        """Test mentioning Matrix user with user_id."""
        from chatom.base import mention_user
        from chatom.matrix import MatrixUser

        user = MatrixUser(id="1", name="Test", user_id="@test:matrix.org")
        result = mention_user(user)
        assert result == "@test:matrix.org"

    def test_mention_matrix_user_with_handle_and_homeserver(self):
        """Test mentioning Matrix user with handle and homeserver."""
        from chatom.base import mention_user
        from chatom.matrix import MatrixUser

        user = MatrixUser(id="1", name="Test", handle="test", homeserver="example.com")
        result = mention_user(user)
        assert result == "@test:example.com"

    def test_mention_matrix_user_with_handle_only(self):
        """Test mentioning Matrix user with handle only (defaults to matrix.org)."""
        from chatom.base import mention_user
        from chatom.matrix import MatrixUser

        user = MatrixUser(id="1", name="Test", handle="test")
        result = mention_user(user)
        assert result == "@test:matrix.org"

    def test_mention_matrix_user_fallback_to_name(self):
        """Test mentioning Matrix user falls back to name."""
        from chatom.base import mention_user
        from chatom.matrix import MatrixUser

        user = MatrixUser(id="1", name="Test User")
        result = mention_user(user)
        assert result == "Test User"

    def test_mention_room(self):
        """Test Matrix room mention."""
        from chatom.matrix.mention import mention_room

        result = mention_room("!room:example.com")
        assert result == "!room:example.com"

    def test_create_pill(self):
        """Test creating Matrix pill."""
        from chatom.matrix.mention import create_pill

        result = create_pill("@user:matrix.org", "User Name")
        assert '<a href="https://matrix.to/#/@user:matrix.org">' in result
        assert "User Name" in result

    def test_create_pill_default_name(self):
        """Test creating Matrix pill with default name."""
        from chatom.matrix.mention import create_pill

        result = create_pill("@user:matrix.org")
        assert "@user:matrix.org</a>" in result


class TestSymphonyMentions:
    """Tests for Symphony mention utilities."""

    def test_symphony_mention_user_with_id(self):
        """Test Symphony mention with user ID."""
        from chatom.symphony import SymphonyUser
        from chatom.symphony.mention import mention_user as symphony_mention

        user = SymphonyUser(id="12345", name="Test User")
        result = symphony_mention(user)
        assert '<mention uid="12345"/>' in result

    def test_symphony_mention_user_with_email(self):
        """Test Symphony mention with email fallback."""
        from chatom.base import mention_user
        from chatom.symphony import SymphonyUser

        user = SymphonyUser(id="", name="Test User", email="test@example.com")
        result = mention_user(user)
        # Should use email or name
        assert "test@example.com" in result or "Test User" in result


class TestSymphonyChannel:
    """Tests for SymphonyChannel class."""

    def test_symphony_channel_stream_type_im(self):
        """Test Symphony IM stream type."""
        from chatom.base import ChannelType
        from chatom.symphony import SymphonyChannel, SymphonyStreamType

        channel = SymphonyChannel(
            id="stream1",
            name="DM",
            stream_type=SymphonyStreamType.IM,
        )
        assert channel.generic_channel_type == ChannelType.DIRECT

    def test_symphony_channel_stream_type_mim(self):
        """Test Symphony MIM stream type."""
        from chatom.base import ChannelType
        from chatom.symphony import SymphonyChannel, SymphonyStreamType

        channel = SymphonyChannel(
            id="stream2",
            name="Group",
            stream_type=SymphonyStreamType.MIM,
        )
        assert channel.generic_channel_type == ChannelType.GROUP

    def test_symphony_channel_stream_type_room_public(self):
        """Test Symphony ROOM stream type with public flag."""
        from chatom.base import ChannelType
        from chatom.symphony import SymphonyChannel, SymphonyStreamType

        channel = SymphonyChannel(
            id="stream3",
            name="Room",
            stream_type=SymphonyStreamType.ROOM,
            public=True,
        )
        assert channel.generic_channel_type == ChannelType.PUBLIC

    def test_symphony_channel_stream_type_room_private(self):
        """Test Symphony ROOM stream type defaults to private."""
        from chatom.base import ChannelType
        from chatom.symphony import SymphonyChannel, SymphonyStreamType

        channel = SymphonyChannel(
            id="stream3",
            name="Room",
            stream_type=SymphonyStreamType.ROOM,
            public=False,
        )
        assert channel.generic_channel_type == ChannelType.PRIVATE

    def test_symphony_channel_stream_type_post(self):
        """Test Symphony POST stream type (defaults to private)."""
        from chatom.base import ChannelType
        from chatom.symphony import SymphonyChannel, SymphonyStreamType

        channel = SymphonyChannel(
            id="stream4",
            name="Post",
            stream_type=SymphonyStreamType.POST,
        )
        assert channel.generic_channel_type == ChannelType.PRIVATE


class TestEmailMessageFromEmailMessage:
    """Tests for EmailMessage.from_email_message class method."""

    def test_from_email_message_simple(self):
        """Test parsing a simple email message."""
        from email.message import EmailMessage as StdEmailMessage

        from chatom.email.message import EmailMessage

        msg = StdEmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Test Subject"
        msg["Message-ID"] = "<test-id@example.com>"
        msg["Date"] = "Mon, 01 Jan 2024 12:00:00 +0000"
        msg.set_content("Hello, this is a test email.")

        email_msg = EmailMessage.from_email_message(msg)

        assert email_msg.from_address == "sender@example.com"
        assert email_msg.subject == "Test Subject"
        assert email_msg.plain_body is not None

    def test_from_email_message_with_display_names(self):
        """Test parsing email with display names in addresses."""
        from email.message import EmailMessage as StdEmailMessage

        from chatom.email.message import EmailMessage

        msg = StdEmailMessage()
        msg["From"] = '"John Doe" <john@example.com>'
        msg["To"] = '"Jane Doe" <jane@example.com>'
        msg["Subject"] = "Display Name Test"
        msg.set_content("Email with display names")

        email_msg = EmailMessage.from_email_message(msg)
        assert email_msg.from_address == "john@example.com"

    def test_from_email_message_multipart(self):
        """Test parsing a multipart email with HTML and plain text."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        from chatom.email.message import EmailMessage

        msg = MIMEMultipart("alternative")
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "Multipart Email"
        msg["Message-ID"] = "<multipart-id@example.com>"

        plain_part = MIMEText("Plain text version", "plain")
        html_part = MIMEText("<html><body><b>HTML version</b></body></html>", "html")

        msg.attach(plain_part)
        msg.attach(html_part)

        email_msg = EmailMessage.from_email_message(msg)
        assert email_msg.plain_body == "Plain text version"
        assert email_msg.html_body is not None
        assert "<b>HTML version</b>" in email_msg.html_body

    def test_from_email_message_html_only(self):
        """Test parsing email with only HTML content."""
        from email.message import EmailMessage as StdEmailMessage

        from chatom.email.message import EmailMessage

        msg = StdEmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "HTML Only Email"
        msg.set_content("<html><body>HTML content</body></html>", subtype="html")

        email_msg = EmailMessage.from_email_message(msg)
        assert email_msg.html_body is not None

    def test_from_email_message_with_reply_to(self):
        """Test parsing email with Reply-To header."""
        from email.message import EmailMessage as StdEmailMessage

        from chatom.email.message import EmailMessage

        msg = StdEmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Reply-To"] = "reply@example.com"
        msg["Subject"] = "Reply-To Test"
        msg.set_content("Test content")

        email_msg = EmailMessage.from_email_message(msg)
        assert email_msg.reply_to == "reply@example.com"

    def test_from_email_message_with_in_reply_to(self):
        """Test parsing email with In-Reply-To header."""
        from email.message import EmailMessage as StdEmailMessage

        from chatom.email.message import EmailMessage

        msg = StdEmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["In-Reply-To"] = "<original-message@example.com>"
        msg["Subject"] = "Re: Original Subject"
        msg.set_content("Reply content")

        email_msg = EmailMessage.from_email_message(msg)
        assert email_msg.in_reply_to == "<original-message@example.com>"

    def test_from_email_message_invalid_date(self):
        """Test parsing email with invalid date header."""
        from email.message import EmailMessage as StdEmailMessage

        from chatom.email.message import EmailMessage

        msg = StdEmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Date"] = "invalid date format"
        msg["Subject"] = "Invalid Date Test"
        msg.set_content("Test content")

        # Should not raise an error, date should be None
        email_msg = EmailMessage.from_email_message(msg)
        assert email_msg.date is None

    def test_from_email_message_no_date(self):
        """Test parsing email without date header."""
        from email.message import EmailMessage as StdEmailMessage

        from chatom.email.message import EmailMessage

        msg = StdEmailMessage()
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "No Date Test"
        msg.set_content("Test content")

        email_msg = EmailMessage.from_email_message(msg)
        assert email_msg.date is None
