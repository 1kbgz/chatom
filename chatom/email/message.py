"""Email-specific Message model.

This module provides the Email-specific Message class.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from chatom.base import Field, Message

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = (
    "EmailMessage",
    "EmailPriority",
    "EmailAddress",
)


class EmailPriority(str, Enum):
    """Email priority levels."""

    HIGHEST = "highest"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    LOWEST = "lowest"


class EmailAddress:
    """Represents an email address with optional display name.

    Attributes:
        address: The email address.
        name: Optional display name.
    """

    def __init__(self, address: str, name: Optional[str] = None):
        self.address = address
        self.name = name

    def __str__(self) -> str:
        if self.name:
            return f'"{self.name}" <{self.address}>'
        return self.address

    def __repr__(self) -> str:
        return f"EmailAddress(address={self.address!r}, name={self.name!r})"


class EmailMessage(Message):
    """Email-specific message with additional email fields.

    Based on RFC 5322 email message structure.

    Attributes:
        subject: The email subject line.
        from_address: The sender's email address.
        to_addresses: List of recipient email addresses.
        cc_addresses: List of CC recipient addresses.
        bcc_addresses: List of BCC recipient addresses.
        reply_to: Reply-to address.
        in_reply_to: Message-ID being replied to.
        references: List of referenced Message-IDs (for threading).
        message_id: The unique Message-ID header.
        date: The Date header value.
        html_body: HTML version of the message body.
        plain_body: Plain text version of the message body.
        headers: Additional email headers.
        priority: Email priority.
        is_read: Whether the email has been read.
        is_flagged: Whether the email is flagged/starred.
        is_draft: Whether this is a draft.
        folder: The mailbox folder containing this email.
        labels: Labels/tags applied to this email.
    """

    subject: str = Field(
        default="",
        description="The email subject line.",
    )
    from_address: Optional[str] = Field(
        default=None,
        description="The sender's email address.",
    )
    to_addresses: List[str] = Field(
        default_factory=list,
        description="List of recipient email addresses.",
    )
    cc_addresses: List[str] = Field(
        default_factory=list,
        description="List of CC recipient addresses.",
    )
    bcc_addresses: List[str] = Field(
        default_factory=list,
        description="List of BCC recipient addresses.",
    )
    reply_to: Optional[str] = Field(
        default=None,
        description="Reply-to address.",
    )
    in_reply_to: Optional[str] = Field(
        default=None,
        description="Message-ID being replied to.",
    )
    references: List[str] = Field(
        default_factory=list,
        description="List of referenced Message-IDs for threading.",
    )
    message_id: Optional[str] = Field(
        default=None,
        description="The unique Message-ID header.",
    )
    date: Optional[datetime] = Field(
        default=None,
        description="The Date header value.",
    )
    html_body: Optional[str] = Field(
        default=None,
        description="HTML version of the message body.",
    )
    plain_body: Optional[str] = Field(
        default=None,
        description="Plain text version of the message body.",
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional email headers.",
    )
    priority: EmailPriority = Field(
        default=EmailPriority.NORMAL,
        description="Email priority.",
    )
    is_read: bool = Field(
        default=False,
        description="Whether the email has been read.",
    )
    is_flagged: bool = Field(
        default=False,
        description="Whether the email is flagged/starred.",
    )
    is_draft: bool = Field(
        default=False,
        description="Whether this is a draft.",
    )
    folder: Optional[str] = Field(
        default=None,
        description="The mailbox folder containing this email.",
    )
    labels: List[str] = Field(
        default_factory=list,
        description="Labels/tags applied to this email.",
    )

    @property
    def body(self) -> str:
        """Get the message body, preferring HTML if available."""
        return self.html_body or self.plain_body or self.content

    @property
    def is_reply(self) -> bool:
        """Check if this is a reply to another email."""
        return self.in_reply_to is not None

    @property
    def is_thread(self) -> bool:
        """Check if this email is part of a thread."""
        return len(self.references) > 0 or self.in_reply_to is not None

    @property
    def recipient_count(self) -> int:
        """Get total number of recipients (to + cc + bcc)."""
        return len(self.to_addresses) + len(self.cc_addresses) + len(self.bcc_addresses)

    @property
    def all_recipients(self) -> List[str]:
        """Get all recipient addresses."""
        return self.to_addresses + self.cc_addresses + self.bcc_addresses

    def to_formatted(self) -> "FormattedMessage":
        """Convert this email message to a FormattedMessage.

        Creates a FormattedMessage from the email content,
        preferring HTML body if available.

        Returns:
            FormattedMessage: The formatted message representation.
        """
        from chatom.format import FormattedAttachment, FormattedMessage

        fm = FormattedMessage()

        # Use HTML body if available, otherwise plain body/content
        body_content = self.html_body or self.plain_body or self.content
        if body_content:
            fm.add_text(body_content)

        # Add attachments
        for att in self.attachments:
            fm.attachments.append(
                FormattedAttachment(
                    filename=att.filename,
                    url=att.url,
                    content_type=att.content_type,
                    size=att.size,
                )
            )

        # Add metadata
        fm.metadata["source_backend"] = "email"
        fm.metadata["message_id"] = self.message_id or self.id
        if self.subject:
            fm.metadata["subject"] = self.subject
        if self.from_address:
            fm.metadata["author_id"] = self.from_address
            fm.metadata["from_address"] = self.from_address
        if self.to_addresses:
            fm.metadata["to_addresses"] = self.to_addresses
        if self.cc_addresses:
            fm.metadata["cc_addresses"] = self.cc_addresses
        if self.in_reply_to:
            fm.metadata["in_reply_to"] = self.in_reply_to
        if self.references:
            fm.metadata["references"] = self.references
        if self.folder:
            fm.metadata["folder"] = self.folder
            fm.metadata["channel_id"] = self.folder
        fm.metadata["priority"] = self.priority.value

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        **kwargs: Any,
    ) -> "EmailMessage":
        """Create an EmailMessage from a FormattedMessage.

        Renders the FormattedMessage in HTML format for email.

        Args:
            formatted: The FormattedMessage to convert.
            **kwargs: Additional message attributes.

        Returns:
            EmailMessage: A new EmailMessage instance.
        """
        from chatom.format import Format

        html_content = formatted.render(Format.HTML)
        plain_content = formatted.render(Format.PLAINTEXT)

        return cls(
            content=plain_content,
            html_body=html_content,
            plain_body=plain_content,
            formatted_content=html_content,
            metadata=dict(formatted.metadata),
            backend="email",
            **kwargs,
        )

    @classmethod
    def from_email_message(cls, msg: Any) -> "EmailMessage":
        """Create an EmailMessage from a Python email.message.Message.

        Args:
            msg: A Python email.message.Message object.

        Returns:
            An EmailMessage instance.
        """
        from email.utils import parseaddr, parsedate_to_datetime

        # Parse sender
        from_header = msg.get("From", "")
        from_name, from_addr = parseaddr(from_header)

        # Parse recipients
        to_list = [parseaddr(addr)[1] for addr in msg.get_all("To", [])]
        cc_list = [parseaddr(addr)[1] for addr in msg.get_all("Cc", [])]
        bcc_list = [parseaddr(addr)[1] for addr in msg.get_all("Bcc", [])]

        # Parse date
        date_str = msg.get("Date")
        date = None
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                pass

        # Get body
        plain_body = None
        html_body = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not plain_body:
                    plain_body = part.get_payload(decode=True)
                    if isinstance(plain_body, bytes):
                        plain_body = plain_body.decode("utf-8", errors="replace")
                elif content_type == "text/html" and not html_body:
                    html_body = part.get_payload(decode=True)
                    if isinstance(html_body, bytes):
                        html_body = html_body.decode("utf-8", errors="replace")
        else:
            content = msg.get_payload(decode=True)
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            if msg.get_content_type() == "text/html":
                html_body = content
            else:
                plain_body = content

        return cls(
            id=msg.get("Message-ID", ""),
            message_id=msg.get("Message-ID"),
            subject=msg.get("Subject", ""),
            from_address=from_addr,
            author_id=from_addr,
            to_addresses=to_list,
            cc_addresses=cc_list,
            bcc_addresses=bcc_list,
            reply_to=parseaddr(msg.get("Reply-To", ""))[1] or None,
            in_reply_to=msg.get("In-Reply-To"),
            reply_to_id=msg.get("In-Reply-To", ""),
            references=[ref.strip() for ref in msg.get("References", "").split() if ref.strip()],
            date=date,
            created_at=date,
            html_body=html_body,
            plain_body=plain_body,
            content=plain_body or "",
            formatted_content=html_body or plain_body or "",
            raw=msg,
            backend="email",
        )
