"""Matrix-specific Message model.

This module provides the Matrix-specific Message class.
Based on the matrix-python-sdk message event structures.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from chatom.base import Field, Message

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = (
    "MatrixMessage",
    "MatrixMessageType",
    "MatrixMessageFormat",
    "MatrixRelationType",
    "MatrixEventType",
)


class MatrixMessageType(str, Enum):
    """Matrix message types (msgtype).

    These are the m.room.message msgtype values.
    """

    TEXT = "m.text"
    EMOTE = "m.emote"
    NOTICE = "m.notice"
    IMAGE = "m.image"
    FILE = "m.file"
    AUDIO = "m.audio"
    VIDEO = "m.video"
    LOCATION = "m.location"
    KEY_VERIFICATION_REQUEST = "m.key.verification.request"


class MatrixMessageFormat(str, Enum):
    """Matrix message formats.

    Specifies the format of the formatted_body.
    """

    HTML = "org.matrix.custom.html"


class MatrixRelationType(str, Enum):
    """Matrix message relation types.

    Used in m.relates_to for threading, replies, and edits.
    """

    REPLY = "m.in_reply_to"
    REPLACE = "m.replace"
    THREAD = "m.thread"
    ANNOTATION = "m.annotation"
    REFERENCE = "m.reference"


class MatrixEventType(str, Enum):
    """Matrix event types.

    Common event types in Matrix.
    """

    ROOM_MESSAGE = "m.room.message"
    ROOM_ENCRYPTED = "m.room.encrypted"
    ROOM_MEMBER = "m.room.member"
    ROOM_NAME = "m.room.name"
    ROOM_TOPIC = "m.room.topic"
    ROOM_AVATAR = "m.room.avatar"
    ROOM_CREATE = "m.room.create"
    ROOM_POWER_LEVELS = "m.room.power_levels"
    ROOM_REDACTION = "m.room.redaction"
    REACTION = "m.reaction"
    STICKER = "m.sticker"
    CALL_INVITE = "m.call.invite"
    CALL_ANSWER = "m.call.answer"
    CALL_HANGUP = "m.call.hangup"


class MatrixMessage(Message):
    """Matrix-specific message with additional Matrix fields.

    Based on the Matrix Client-Server API message event structure,
    this provides Matrix-specific message attributes and functionality.

    Attributes:
        event_id: The unique event ID.
        room_id: The room ID where the message was sent.
        sender: The sender's Matrix user ID.
        event_type: The event type (e.g., m.room.message).
        msgtype: The message type (e.g., m.text, m.image).
        format: The format of formatted_body.
        formatted_body: HTML-formatted body content.
        origin_server_ts: Server timestamp in milliseconds.
        unsigned: Unsigned event metadata.
        relates_to: Relation information for replies/edits/threads.
        in_reply_to_event_id: Event ID being replied to.
        replaces_event_id: Event ID being edited/replaced.
        thread_root_event_id: Root event ID of thread.
        transaction_id: Client-assigned transaction ID.
        redacted: Whether the message has been redacted.
        redacted_by: Event ID that redacted this message.
        decrypted: Whether an encrypted message was decrypted.
        verified: Whether sender verification passed.
        file_url: MXC URL for file attachments.
        file_name: Filename for attachments.
        file_info: File metadata (size, mimetype, etc.).
        thumbnail_url: MXC URL for thumbnail.
        thumbnail_info: Thumbnail metadata.
        geo_uri: Geographic URI for location messages.
    """

    event_id: str = Field(
        default="",
        description="The unique event ID.",
    )
    room_id: str = Field(
        default="",
        description="The room ID where the message was sent.",
    )
    sender: str = Field(
        default="",
        description="The sender's Matrix user ID.",
    )
    event_type: str = Field(
        default="m.room.message",
        description="The event type (e.g., m.room.message).",
    )
    msgtype: str = Field(
        default="m.text",
        description="The message type (e.g., m.text, m.image).",
    )
    format: str = Field(
        default="",
        description="The format of formatted_body (e.g., org.matrix.custom.html).",
    )
    formatted_body: str = Field(
        default="",
        description="HTML-formatted body content.",
    )
    origin_server_ts: int = Field(
        default=0,
        description="Server timestamp in milliseconds since epoch.",
    )
    unsigned: Dict[str, Any] = Field(
        default_factory=dict,
        description="Unsigned event metadata (age, transaction_id, etc.).",
    )
    relates_to: Dict[str, Any] = Field(
        default_factory=dict,
        description="Relation information for replies/edits/threads.",
    )
    in_reply_to_event_id: str = Field(
        default="",
        description="Event ID being replied to.",
    )
    replaces_event_id: str = Field(
        default="",
        description="Event ID being edited/replaced.",
    )
    thread_root_event_id: str = Field(
        default="",
        description="Root event ID of thread.",
    )
    transaction_id: str = Field(
        default="",
        description="Client-assigned transaction ID.",
    )
    redacted: bool = Field(
        default=False,
        description="Whether the message has been redacted.",
    )
    redacted_by: str = Field(
        default="",
        description="Event ID that redacted this message.",
    )
    decrypted: bool = Field(
        default=False,
        description="Whether an encrypted message was decrypted.",
    )
    verified: bool = Field(
        default=False,
        description="Whether sender verification passed.",
    )

    # Media/file attachment fields
    file_url: str = Field(
        default="",
        description="MXC URL for file attachments.",
    )
    file_name: str = Field(
        default="",
        description="Filename for attachments.",
    )
    file_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="File metadata (size, mimetype, etc.).",
    )
    thumbnail_url: str = Field(
        default="",
        description="MXC URL for thumbnail.",
    )
    thumbnail_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Thumbnail metadata.",
    )

    # Location fields
    geo_uri: str = Field(
        default="",
        description="Geographic URI for location messages.",
    )

    @property
    def is_text(self) -> bool:
        """Check if this is a text message.

        Returns:
            bool: True if msgtype is m.text.
        """
        return self.msgtype == MatrixMessageType.TEXT.value

    @property
    def is_notice(self) -> bool:
        """Check if this is a notice message (typically from bots).

        Returns:
            bool: True if msgtype is m.notice.
        """
        return self.msgtype == MatrixMessageType.NOTICE.value

    @property
    def is_emote(self) -> bool:
        """Check if this is an emote message (/me style).

        Returns:
            bool: True if msgtype is m.emote.
        """
        return self.msgtype == MatrixMessageType.EMOTE.value

    @property
    def is_media(self) -> bool:
        """Check if this is a media message.

        Returns:
            bool: True if msgtype is image, file, audio, or video.
        """
        return self.msgtype in (
            MatrixMessageType.IMAGE.value,
            MatrixMessageType.FILE.value,
            MatrixMessageType.AUDIO.value,
            MatrixMessageType.VIDEO.value,
        )

    @property
    def is_location(self) -> bool:
        """Check if this is a location message.

        Returns:
            bool: True if msgtype is m.location.
        """
        return self.msgtype == MatrixMessageType.LOCATION.value

    @property
    def is_reply(self) -> bool:
        """Check if this message is a reply to another message.

        Returns:
            bool: True if in_reply_to_event_id is set.
        """
        return bool(self.in_reply_to_event_id)

    @property
    def is_edit(self) -> bool:
        """Check if this message is an edit of another message.

        Returns:
            bool: True if replaces_event_id is set.
        """
        return bool(self.replaces_event_id)

    @property
    def is_threaded(self) -> bool:
        """Check if this message is part of a thread.

        Returns:
            bool: True if thread_root_event_id is set.
        """
        return bool(self.thread_root_event_id)

    @property
    def is_encrypted(self) -> bool:
        """Check if this message was encrypted.

        Returns:
            bool: True if event_type is m.room.encrypted.
        """
        return self.event_type == MatrixEventType.ROOM_ENCRYPTED.value

    @property
    def is_redacted(self) -> bool:
        """Check if this message has been redacted.

        Returns:
            bool: True if redacted flag is set.
        """
        return self.redacted

    @property
    def has_html(self) -> bool:
        """Check if this message has HTML formatting.

        Returns:
            bool: True if formatted_body is set with HTML format.
        """
        return bool(self.formatted_body) and self.format == MatrixMessageFormat.HTML.value

    @property
    def age_ms(self) -> Optional[int]:
        """Get the age of the event in milliseconds.

        Returns:
            Optional[int]: The age from unsigned data, or None.
        """
        return self.unsigned.get("age")

    @property
    def server_name(self) -> str:
        """Get the server name from the room ID.

        Returns:
            str: The homeserver domain.
        """
        if self.room_id and ":" in self.room_id:
            return self.room_id.split(":", 1)[1]
        return ""

    @property
    def sender_localpart(self) -> str:
        """Get the local part of the sender's user ID.

        Returns:
            str: The part before the colon, without @.
        """
        if self.sender and self.sender.startswith("@") and ":" in self.sender:
            return self.sender[1:].split(":")[0]
        return ""

    def get_file_http_url(self, homeserver_url: str = "") -> str:
        """Convert MXC file URL to HTTP URL.

        Args:
            homeserver_url: The homeserver base URL (e.g., https://matrix.org).

        Returns:
            str: The HTTP URL for the file, or empty string if no file.
        """
        if not self.file_url:
            return ""
        if not self.file_url.startswith("mxc://"):
            return self.file_url

        # Parse mxc://server/media_id
        mxc_path = self.file_url[6:]  # Remove "mxc://"
        if "/" not in mxc_path:
            return ""

        server, media_id = mxc_path.split("/", 1)
        base = homeserver_url.rstrip("/") if homeserver_url else f"https://{server}"
        return f"{base}/_matrix/media/r0/download/{server}/{media_id}"

    def get_thumbnail_http_url(self, homeserver_url: str = "") -> str:
        """Convert MXC thumbnail URL to HTTP URL.

        Args:
            homeserver_url: The homeserver base URL (e.g., https://matrix.org).

        Returns:
            str: The HTTP URL for the thumbnail, or empty string if no thumbnail.
        """
        if not self.thumbnail_url:
            return ""
        if not self.thumbnail_url.startswith("mxc://"):
            return self.thumbnail_url

        # Parse mxc://server/media_id
        mxc_path = self.thumbnail_url[6:]  # Remove "mxc://"
        if "/" not in mxc_path:
            return ""

        server, media_id = mxc_path.split("/", 1)
        base = homeserver_url.rstrip("/") if homeserver_url else f"https://{server}"
        return f"{base}/_matrix/media/r0/download/{server}/{media_id}"

    @classmethod
    def from_event(cls, event: Dict[str, Any]) -> "MatrixMessage":
        """Create a MatrixMessage from a Matrix event dictionary.

        Args:
            event: A Matrix event dictionary from the API.

        Returns:
            MatrixMessage: A new MatrixMessage instance.
        """
        content = event.get("content", {})
        unsigned = event.get("unsigned", {})
        relates_to = content.get("m.relates_to", {})

        # Extract relation information
        in_reply_to = relates_to.get("m.in_reply_to", {}).get("event_id", "")
        replaces = ""
        thread_root = ""

        if relates_to.get("rel_type") == "m.replace":
            replaces = relates_to.get("event_id", "")
        elif relates_to.get("rel_type") == "m.thread":
            thread_root = relates_to.get("event_id", "")

        # Check for redaction
        redacted = "redacted_because" in unsigned
        redacted_by = ""
        if redacted:
            redacted_by = unsigned.get("redacted_because", {}).get("event_id", "")

        sender = event.get("sender", "")
        room_id = event.get("room_id", "")
        event_id = event.get("event_id", "")
        body = content.get("body", "")
        formatted_body = content.get("formatted_body", "")

        return cls(
            id=event_id,
            event_id=event_id,
            room_id=room_id,
            channel_id=room_id,
            sender=sender,
            author_id=sender,
            event_type=event.get("type", "m.room.message"),
            content=body,
            msgtype=content.get("msgtype", "m.text"),
            format=content.get("format", ""),
            formatted_body=formatted_body,
            formatted_content=formatted_body or body,
            origin_server_ts=event.get("origin_server_ts", 0),
            unsigned=unsigned,
            relates_to=relates_to,
            in_reply_to_event_id=in_reply_to,
            reply_to_id=in_reply_to,
            replaces_event_id=replaces,
            thread_root_event_id=thread_root,
            thread_id=thread_root,
            transaction_id=unsigned.get("transaction_id", ""),
            redacted=redacted,
            redacted_by=redacted_by,
            file_url=content.get("url", ""),
            file_name=content.get("filename", content.get("body", "")),
            file_info=content.get("info", {}),
            thumbnail_url=content.get("info", {}).get("thumbnail_url", ""),
            thumbnail_info=content.get("info", {}).get("thumbnail_info", {}),
            geo_uri=content.get("geo_uri", ""),
            raw=event,
            backend="matrix",
        )

    def to_content(self) -> Dict[str, Any]:
        """Convert to a Matrix message content dictionary.

        Returns:
            Dict[str, Any]: Message content suitable for sending via API.
        """
        content: Dict[str, Any] = {
            "msgtype": self.msgtype,
            "body": self.text,
        }

        # Add HTML formatting
        if self.formatted_body:
            content["format"] = self.format or MatrixMessageFormat.HTML.value
            content["formatted_body"] = self.formatted_body

        # Add media info
        if self.file_url:
            content["url"] = self.file_url
            if self.file_name:
                content["filename"] = self.file_name
            if self.file_info:
                content["info"] = self.file_info.copy()
                if self.thumbnail_url:
                    content["info"]["thumbnail_url"] = self.thumbnail_url
                if self.thumbnail_info:
                    content["info"]["thumbnail_info"] = self.thumbnail_info

        # Add location info
        if self.geo_uri:
            content["geo_uri"] = self.geo_uri

        # Add relations
        if self.in_reply_to_event_id or self.replaces_event_id or self.thread_root_event_id:
            relates_to: Dict[str, Any] = {}
            if self.in_reply_to_event_id:
                relates_to["m.in_reply_to"] = {"event_id": self.in_reply_to_event_id}
            if self.replaces_event_id:
                relates_to["rel_type"] = "m.replace"
                relates_to["event_id"] = self.replaces_event_id
            if self.thread_root_event_id:
                relates_to["rel_type"] = "m.thread"
                relates_to["event_id"] = self.thread_root_event_id
            content["m.relates_to"] = relates_to

        return content

    def to_formatted(self) -> "FormattedMessage":
        """Convert this Matrix message to a FormattedMessage.

        Parses Matrix HTML formatting and converts to a FormattedMessage
        that can be rendered for other backends.

        Returns:
            FormattedMessage: The formatted message representation.
        """
        from chatom.format import FormattedAttachment, FormattedImage, FormattedMessage

        fm = FormattedMessage()

        # Use formatted_body (HTML) if available, otherwise use content/body
        if self.formatted_body and self.format == MatrixMessageFormat.HTML.value:
            # Store the HTML content
            fm.add_text(self.formatted_body)
            fm.metadata["has_html"] = True
        elif self.content:
            fm.add_text(self.content)

        # Add media attachments
        if self.is_media:
            if self.msgtype == MatrixMessageType.IMAGE.value:
                fm.content.append(
                    FormattedImage(
                        url=self.file_url,
                        alt_text=self.file_name or self.content,
                    )
                )
            else:
                fm.attachments.append(
                    FormattedAttachment(
                        filename=self.file_name,
                        url=self.file_url,
                        content_type=self.file_info.get("mimetype", ""),
                        size=self.file_info.get("size", 0),
                    )
                )

        # Add metadata
        fm.metadata["source_backend"] = "matrix"
        fm.metadata["message_id"] = self.event_id
        fm.metadata["event_id"] = self.event_id
        if self.room_id:
            fm.metadata["room_id"] = self.room_id
            fm.metadata["channel_id"] = self.room_id
        if self.sender:
            fm.metadata["author_id"] = self.sender
            fm.metadata["sender"] = self.sender
        if self.msgtype:
            fm.metadata["msgtype"] = self.msgtype
        if self.in_reply_to_event_id:
            fm.metadata["reply_to_id"] = self.in_reply_to_event_id
        if self.thread_root_event_id:
            fm.metadata["thread_root_id"] = self.thread_root_event_id

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        **kwargs: Any,
    ) -> "MatrixMessage":
        """Create a MatrixMessage from a FormattedMessage.

        Renders the FormattedMessage in HTML format for Matrix.

        Args:
            formatted: The FormattedMessage to convert.
            **kwargs: Additional message attributes.

        Returns:
            MatrixMessage: A new MatrixMessage instance.
        """
        from chatom.format import Format

        # Matrix uses HTML for rich content
        html_content = formatted.render(Format.HTML)
        plain_content = formatted.render(Format.PLAINTEXT)

        return cls(
            content=plain_content,
            formatted_body=html_content,
            format=MatrixMessageFormat.HTML.value if html_content != plain_content else "",
            msgtype=MatrixMessageType.TEXT.value,
            metadata=dict(formatted.metadata),
            backend="matrix",
            **kwargs,
        )
