"""Symphony-specific Message model.

This module provides the Symphony-specific Message class.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from chatom.base import Field, Message, User

from .channel import SymphonyChannel
from .user import SymphonyUser

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = (
    "SymphonyMessage",
    "SymphonyMessageFormat",
)


class SymphonyMessageFormat(str, Enum):
    """Symphony message format types."""

    MESSAGEML = "com.symphony.messageml.v2"
    PRESENTATIONML = "com.symphony.presentationml"


class SymphonyMessage(Message):
    """Symphony-specific message with additional Symphony fields.

    Based on the Symphony REST API message structure.

    Attributes:
        message_ml: The MessageML content.
        presentation_ml: The PresentationML rendered content.
        entity_data: Entity data for structured objects.
        data: The JSON data associated with the message.
        shared_message: Shared/forwarded message info.
        ingestion_date: When the message was ingested.
        diagnostic: Diagnostic information.
        sid: Session ID.
        original_format: The original message format.
        is_chime: Whether this is a chime message.
        is_copy_disabled: Whether copying is disabled.
        attachments_metadata: Metadata about attachments.
        hashtags: List of hashtags in the message.
        cashtags: List of cashtags in the message.
        mentions: List of user mentions in the message.
    """

    # message_id
    # stream_id

    message_ml: Optional[str] = Field(
        default=None,
        description="The MessageML content.",
    )
    presentation_ml: Optional[str] = Field(
        default=None,
        description="The PresentationML rendered content.",
    )
    entity_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Entity data for structured objects.",
    )
    data: Optional[str] = Field(
        default=None,
        description="The JSON data associated with the message.",
    )
    shared_message: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Shared/forwarded message info.",
    )
    ingestion_date: Optional[datetime] = Field(
        default=None,
        description="When the message was ingested.",
    )
    diagnostic: Optional[str] = Field(
        default=None,
        description="Diagnostic information.",
    )
    sid: Optional[str] = Field(
        default=None,
        description="Session ID.",
    )
    original_format: SymphonyMessageFormat = Field(
        default=SymphonyMessageFormat.MESSAGEML,
        description="The original message format.",
    )
    is_chime: bool = Field(
        default=False,
        description="Whether this is a chime message.",
    )
    is_copy_disabled: bool = Field(
        default=False,
        description="Whether copying is disabled.",
    )
    attachments_metadata: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Metadata about attachments.",
    )
    hashtags: List[str] = Field(
        default_factory=list,
        description="List of hashtags in the message.",
    )
    cashtags: List[str] = Field(
        default_factory=list,
        description="List of cashtags in the message.",
    )

    @property
    def is_shared_message(self) -> bool:
        """Check if this is a shared/forwarded message."""
        return self.shared_message is not None

    @property
    def message_id(self) -> str:
        """Get the message ID (same as id).

        Returns the message's id for backward compatibility.
        """
        return self.id

    @property
    def stream_id(self) -> str:
        """Get the stream ID (channel.id).

        Returns the channel's id, or empty string if no channel.
        """
        return self.channel.id if self.channel else ""

    @property
    def has_entity_data(self) -> bool:
        """Check if this message has entity data."""
        return len(self.entity_data) > 0

    @property
    def has_hashtags(self) -> bool:
        """Check if this message contains hashtags."""
        return len(self.hashtags) > 0

    @property
    def has_cashtags(self) -> bool:
        """Check if this message contains cashtags."""
        return len(self.cashtags) > 0

    @property
    def has_mentions(self) -> bool:
        """Check if this message contains user mentions."""
        return len(self.mentions) > 0

    def mentions_user(self, user_or_id: Union[str, User]) -> bool:
        """Check if this message mentions a specific user.

        Args:
            user_or_id: The user ID (as string) or User object to check for.

        Returns:
            True if the user is mentioned in this message.
        """
        # Extract user_id from User object or use as-is
        user_id_str = user_or_id.id if isinstance(user_or_id, User) else str(user_or_id)
        user_id_int = int(user_id_str) if user_id_str.isdigit() else None

        # Check mentions (User objects from base class)
        for user in self.mentions:
            if user.id == user_id_str:
                return True

        # Check entity_data for mention entities
        for key, entity in self.entity_data.items():
            if isinstance(entity, dict) and entity.get("type") == "com.symphony.user.mention":
                mentioned_id = entity.get("id", [{}])[0].get("value")
                if mentioned_id and str(mentioned_id) == user_id_str:
                    return True

        # Also check the data field (JSON string) if entity_data is empty
        if self.data and not self.entity_data:
            extracted = self.extract_mentions_from_data(self.data)
            if user_id_int is not None and user_id_int in extracted:
                return True

        return False

    @staticmethod
    def extract_mentions_from_data(data: Optional[str]) -> List[int]:
        """Extract user IDs from Symphony data field (JSON entity data).

        Symphony encodes mentions in the data field as JSON with entity
        references like {"mention0": {"type": "com.symphony.user.mention", "id": [{"value": "123"}]}}.

        Args:
            data: The JSON data string from the message.

        Returns:
            List of user IDs (as integers) mentioned in the message.
        """
        import json

        if not data:
            return []

        try:
            entities = json.loads(data)
            mentions = []
            for key, entity in entities.items():
                if isinstance(entity, dict) and entity.get("type") == "com.symphony.user.mention":
                    id_list = entity.get("id", [])
                    if id_list and isinstance(id_list, list) and len(id_list) > 0:
                        user_id = id_list[0].get("value")
                        if user_id:
                            mentions.append(int(user_id))
            return mentions
        except (json.JSONDecodeError, ValueError, TypeError):
            return []

    @property
    def rendered_content(self) -> str:
        """Get the rendered content, preferring PresentationML."""
        return self.presentation_ml or self.message_ml or self.content

    def _parse_symphony_content(self, content: str) -> str:
        """Parse Symphony MessageML/PresentationML and extract plain text.

        Strips all HTML/XML tags and converts to plain text, preserving
        meaningful whitespace.

        Args:
            content: The MessageML or PresentationML content.

        Returns:
            Plain text extracted from the content.
        """
        import html
        import re

        if not content:
            return ""

        text = content

        # Replace common block elements with newlines
        text = re.sub(r"<br\s*/?>\s*", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>\s*", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</div>\s*", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</li>\s*", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</tr>\s*", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</td>\s*", " | ", text, flags=re.IGNORECASE)
        text = re.sub(r"</th>\s*", " | ", text, flags=re.IGNORECASE)

        # Remove all remaining HTML/XML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = html.unescape(text)

        # Normalize whitespace (but preserve intentional newlines)
        lines = text.split("\n")
        lines = [" ".join(line.split()) for line in lines]  # normalize spaces per line
        text = "\n".join(lines)

        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "SymphonyMessage":
        """Create a SymphonyMessage from an API response.

        Args:
            data: The API response data.

        Returns:
            A SymphonyMessage instance.
        """
        user_data = data.get("user", {})
        stream_data = data.get("stream", {})
        timestamp = data.get("timestamp")

        return cls(
            id=data.get("messageId", ""),
            channel=SymphonyChannel(id=stream_data.get("streamId", "")),
            content=data.get("message", ""),
            message_ml=data.get("message", ""),
            formatted_content=data.get("message", ""),
            author=SymphonyUser(id=str(user_data.get("userId", ""))),
            created_at=datetime.fromtimestamp(timestamp / 1000) if timestamp else None,
            data=data.get("data"),
            entity_data=data.get("entityData", {}),
            attachments_metadata=data.get("attachments", []),
            raw=data,
            backend="symphony",
        )

    def to_formatted(self) -> "FormattedMessage":
        """Convert this Symphony message to a FormattedMessage.

        Parses Symphony MessageML/PresentationML formatting and converts to a
        FormattedMessage that can be rendered for other backends.

        Returns:
            FormattedMessage: The formatted message representation.
        """
        from chatom.format import FormattedAttachment, FormattedMessage

        fm = FormattedMessage()

        # Use rendered content (PresentationML > MessageML > content)
        content = self.rendered_content
        if content:
            # Parse the MessageML/PresentationML to extract plain text and formatting
            plain_text = self._parse_symphony_content(content)
            fm.add_text(plain_text)

        # Add attachment metadata
        for att_meta in self.attachments_metadata:
            fm.attachments.append(
                FormattedAttachment(
                    filename=att_meta.get("name", ""),
                    url=att_meta.get("url", ""),
                    content_type=att_meta.get("contentType", ""),
                    size=att_meta.get("size", 0),
                )
            )

        # Add metadata
        fm.metadata["source_backend"] = "symphony"
        fm.metadata["message_id"] = self.message_id
        if self.channel:
            fm.metadata["stream_id"] = self.channel.id
            fm.metadata["channel_id"] = self.channel.id
        if self.author:
            fm.metadata["author_id"] = str(self.author.id)
        if self.hashtags:
            fm.metadata["hashtags"] = self.hashtags
        if self.cashtags:
            fm.metadata["cashtags"] = self.cashtags
        if self.mentions:
            fm.metadata["mention_ids"] = [m.id for m in self.mentions]
        if self.entity_data:
            fm.metadata["entity_data"] = self.entity_data

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        **kwargs: Any,
    ) -> "SymphonyMessage":
        """Create a SymphonyMessage from a FormattedMessage.

        Renders the FormattedMessage in Symphony MessageML format.

        Args:
            formatted: The FormattedMessage to convert.
            **kwargs: Additional message attributes.

        Returns:
            SymphonyMessage: A new SymphonyMessage instance.
        """
        from chatom.format import Format

        content = formatted.render(Format.SYMPHONY_MESSAGEML)

        if "stream_id" in kwargs and "channel" not in kwargs:
            kwargs["channel"] = SymphonyChannel(id=kwargs.pop("stream_id"))

        return cls(
            content=content,
            message_ml=content,
            formatted_content=content,
            metadata=dict(formatted.metadata),
            **kwargs,
        )
