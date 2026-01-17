"""Mock email backend for testing.

This module provides a mock implementation of the Email backend
that doesn't require actual SMTP/IMAP servers.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional, Union

from pydantic import Field

from ..backend_registry import BackendBase
from ..base import (
    EMAIL_CAPABILITIES,
    BackendCapabilities,
    Channel,
    Message,
    Presence,
    User,
)
from ..format.variant import Format
from .channel import EmailChannel
from .config import EmailConfig
from .mention import mention_user as _mention_user
from .message import EmailMessage
from .user import EmailUser

__all__ = ("MockEmailBackend",)


class MockEmailBackend(BackendBase):
    """Mock email backend for testing.

    This provides a testing-friendly implementation that simulates
    email operations without requiring actual servers.

    Attributes:
        mock_users: Dictionary of mock users by email.
        mock_mailboxes: Dictionary of mailboxes containing messages.
        sent_emails: List of sent email messages for verification.
        deleted_emails: List of deleted message IDs.

    Example:
        >>> from chatom.email import MockEmailBackend, EmailConfig
        >>> backend = MockEmailBackend()
        >>> await backend.connect()
        >>> # Add mock data
        >>> backend.add_mock_user("test@example.com", "Test User")
        >>> backend.add_mock_message(
        ...     mailbox="INBOX",
        ...     from_addr="sender@example.com",
        ...     subject="Hello",
        ...     body="Test message",
        ... )
        >>> # Verify operations
        >>> messages = await backend.fetch_messages("INBOX")
        >>> await backend.send_message("recipient@example.com", "Hello", subject="Hi")
        >>> assert len(backend.sent_emails) == 1
    """

    name: ClassVar[str] = "email"
    display_name: ClassVar[str] = "Email (Mock)"
    format: ClassVar[Format] = Format.HTML

    capabilities: Optional[BackendCapabilities] = EMAIL_CAPABILITIES
    config: EmailConfig = Field(default_factory=EmailConfig)

    # Mock data stores
    mock_users: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    mock_mailboxes: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)

    # Tracking for verification
    sent_emails: List[Dict[str, Any]] = Field(default_factory=list)
    deleted_emails: List[str] = Field(default_factory=list)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    def add_mock_user(
        self,
        email: str,
        name: Optional[str] = None,
    ) -> None:
        """Add a mock user.

        Args:
            email: The user's email address.
            name: The user's display name.
        """
        self.mock_users[email] = {
            "email": email,
            "name": name or email,
        }

    def add_mock_message(
        self,
        mailbox: str,
        from_addr: str,
        subject: str,
        body: str,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        to_addr: Optional[str] = None,
        cc: Optional[str] = None,
    ) -> str:
        """Add a mock message to a mailbox.

        Args:
            mailbox: The mailbox name (e.g., "INBOX").
            from_addr: The sender's email address.
            subject: The email subject.
            body: The email body.
            message_id: Optional message ID. Generated if not provided.
            timestamp: Optional timestamp. Uses current time if not provided.
            to_addr: Optional recipient address.
            cc: Optional CC recipients.

        Returns:
            The message ID.
        """
        if mailbox not in self.mock_mailboxes:
            self.mock_mailboxes[mailbox] = []

        if message_id is None:
            message_id = f"<{uuid.uuid4()}@mock.example.com>"

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        msg = {
            "id": message_id,
            "from": from_addr,
            "to": to_addr or "inbox@example.com",
            "cc": cc,
            "subject": subject,
            "body": body,
            "timestamp": timestamp,
        }
        self.mock_mailboxes[mailbox].append(msg)
        return message_id

    async def connect(self) -> None:
        """Connect to mock email servers.

        Always succeeds immediately.
        """
        # Initialize default mailboxes
        if "INBOX" not in self.mock_mailboxes:
            self.mock_mailboxes["INBOX"] = []
        if "Sent" not in self.mock_mailboxes:
            self.mock_mailboxes["Sent"] = []
        if "Trash" not in self.mock_mailboxes:
            self.mock_mailboxes["Trash"] = []

        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from mock email servers."""
        self.connected = False

    async def fetch_user(
        self,
        identifier: Optional[Union[str, User]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Fetch a mock user by email address or other attributes.

        Args:
            identifier: A User object or email address string.
            id: Email address.
            name: Display name to search for.
            email: Email address (same as id).
            handle: Email address (same as id).

        Returns:
            The user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, EmailUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id (email)
        if identifier and not id:
            id = str(identifier)

        # email= and handle= are synonyms for id=
        if not id:
            id = email or handle

        # Check cache first
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached

            # Check mock data
            if id in self.mock_users:
                data = self.mock_users[id]
                user = EmailUser(
                    id=data["email"],
                    name=data["name"],
                    handle=data["email"],
                    email=data["email"],
                )
                self.users.add(user)
                return user

            # Create basic user from email
            user = EmailUser(
                id=id,
                name=id,
                handle=id,
                email=id,
            )
            self.users.add(user)
            return user

        # Search by name
        if name:
            name_lower = name.lower()
            for email_key, data in self.mock_users.items():
                if data["name"].lower() == name_lower:
                    return await self.fetch_user(email_key)

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel (mailbox).

        Args:
            identifier: A Channel object or mailbox name string.
            id: Mailbox name.
            name: Mailbox name (same as id).

        Returns:
            The channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, EmailChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # name= is same as id=
        if not id:
            id = name

        if not id:
            return None

        # Check cache first
        cached = self.channels.get_by_id(id)
        if cached:
            return cached

        # Check if mailbox exists
        if id in self.mock_mailboxes:
            channel = EmailChannel(
                id=id,
                name=id,
            )
            self.channels.add(channel)
            return channel

        return None

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch messages from a mock mailbox.

        Args:
            channel_id: The mailbox name.
            limit: Maximum number of messages.
            before: Fetch messages before this date (YYYY-MM-DD).
            after: Fetch messages after this date (YYYY-MM-DD).

        Returns:
            List of email messages.
        """
        if channel_id not in self.mock_mailboxes:
            return []

        messages_data = self.mock_mailboxes[channel_id]

        # Filter by date if specified
        filtered = messages_data
        if before:
            before_date = datetime.fromisoformat(before).replace(tzinfo=timezone.utc)
            filtered = [m for m in filtered if m["timestamp"] < before_date]
        if after:
            after_date = datetime.fromisoformat(after).replace(tzinfo=timezone.utc)
            filtered = [m for m in filtered if m["timestamp"] >= after_date]

        # Sort by timestamp (newest first) and limit
        filtered = sorted(filtered, key=lambda m: m["timestamp"], reverse=True)
        filtered = filtered[:limit]

        messages: List[Message] = []
        for raw in filtered:
            message = EmailMessage(
                id=raw["id"],
                content=raw["body"],
                timestamp=raw["timestamp"],
                user_id=raw["from"],
                channel_id=channel_id,
                subject=raw["subject"],
            )
            messages.append(message)

        return messages

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a mock email message.

        Args:
            channel_id: The recipient email address.
            content: The email body.
            **kwargs: Additional options (subject, cc, bcc).

        Returns:
            The sent message.
        """
        subject = kwargs.get("subject", "")
        cc = kwargs.get("cc", "")
        bcc = kwargs.get("bcc", "")
        reply_to = kwargs.get("reply_to", "")

        message_id = f"<{uuid.uuid4()}@mock.example.com>"
        timestamp = datetime.now(timezone.utc)

        # Track sent email
        sent = {
            "id": message_id,
            "from": self.config.effective_from_address,
            "to": channel_id,
            "cc": cc,
            "bcc": bcc,
            "reply_to": reply_to,
            "subject": subject,
            "body": content,
            "timestamp": timestamp,
        }
        self.sent_emails.append(sent)

        # Also add to Sent mailbox
        if "Sent" in self.mock_mailboxes:
            self.mock_mailboxes["Sent"].append(sent)

        return EmailMessage(
            id=message_id,
            content=content,
            timestamp=timestamp,
            user_id=self.config.effective_from_address,
            channel_id=channel_id,
            subject=subject,
        )

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit a message.

        Email doesn't support editing.

        Raises:
            NotImplementedError: Email doesn't support editing.
        """
        raise NotImplementedError("Email does not support message editing")

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete a mock email message.

        Args:
            channel_id: The mailbox containing the message.
            message_id: The message ID.
        """
        if channel_id in self.mock_mailboxes:
            original_len = len(self.mock_mailboxes[channel_id])
            self.mock_mailboxes[channel_id] = [m for m in self.mock_mailboxes[channel_id] if m["id"] != message_id]
            if len(self.mock_mailboxes[channel_id]) < original_len:
                self.deleted_emails.append(message_id)

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set presence.

        Email doesn't support presence.

        Raises:
            NotImplementedError: Email doesn't support presence.
        """
        raise NotImplementedError("Email does not support presence")

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get presence.

        Email doesn't support presence.

        Returns:
            None.
        """
        return None

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction.

        Email doesn't support reactions.

        Raises:
            NotImplementedError: Email doesn't support reactions.
        """
        raise NotImplementedError("Email does not support reactions")

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction.

        Email doesn't support reactions.

        Raises:
            NotImplementedError: Email doesn't support reactions.
        """
        raise NotImplementedError("Email does not support reactions")

    def mention_user(self, user: User) -> str:
        """Format a user mention.

        Args:
            user: The user to mention.

        Returns:
            HTML mailto link.
        """
        if isinstance(user, EmailUser):
            return _mention_user(user)
        email = user.email or user.id
        name = user.display_name
        return f"<a href='mailto:{email}'>{name}</a>"

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention.

        Args:
            channel: The channel to mention.

        Returns:
            The channel name.
        """
        return channel.name or channel.id

    def reset(self) -> None:
        """Reset all mock data and tracking.

        Useful for cleaning up between tests.
        """
        self.mock_users.clear()
        self.mock_mailboxes.clear()
        self.mock_mailboxes["INBOX"] = []
        self.mock_mailboxes["Sent"] = []
        self.mock_mailboxes["Trash"] = []
        self.sent_emails.clear()
        self.deleted_emails.clear()
        self.users.clear()
        self.channels.clear()
