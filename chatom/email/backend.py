"""Email backend implementation for chatom.

This module provides the Email backend using Python's native
smtplib and imaplib libraries.
"""

import asyncio
import email as email_lib
import imaplib
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any, ClassVar, List, Optional, Union

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
from .presence import EmailPresence
from .user import EmailUser

__all__ = ("EmailBackend",)


class EmailBackend(BackendBase):
    """Email backend implementation using smtplib and imaplib.

    This provides the backend interface for Email using Python's
    native email libraries. Note that email has different semantics
    than chat - no real-time messaging, no presence, etc.

    Attributes:
        name: The backend identifier ('email').
        display_name: Human-readable name.
        format: Email typically uses HTML.
        capabilities: Email-specific capabilities.
        config: Email-specific configuration.

    Example:
        >>> from chatom.email import EmailBackend, EmailConfig
        >>> config = EmailConfig(
        ...     smtp_host="smtp.example.com",
        ...     imap_host="imap.example.com",
        ...     username="bot@example.com",
        ...     password="secret",
        ... )
        >>> backend = EmailBackend(config=config)
        >>> await backend.connect()
    """

    name: ClassVar[str] = "email"
    display_name: ClassVar[str] = "Email"
    format: ClassVar[Format] = Format.HTML

    # Type classes for this backend (used by conversion module)
    user_class: ClassVar[type] = EmailUser
    channel_class: ClassVar[type] = EmailChannel
    presence_class: ClassVar[type] = EmailPresence

    capabilities: Optional[BackendCapabilities] = EMAIL_CAPABILITIES
    config: EmailConfig = Field(default_factory=EmailConfig)

    # Connection instances
    _smtp: Any = None
    _imap: Any = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    async def connect(self) -> None:
        """Connect to email servers (SMTP/IMAP).

        This connects to both SMTP (for sending) and IMAP (for receiving)
        servers if configured.

        Raises:
            RuntimeError: If neither SMTP nor IMAP is configured.
        """
        if not self.config.has_smtp and not self.config.has_imap:
            raise RuntimeError("Either SMTP or IMAP must be configured")

        # Connect to SMTP
        if self.config.has_smtp:
            await self._connect_smtp()

        # Connect to IMAP
        if self.config.has_imap:
            await self._connect_imap()

        self.connected = True

    async def _connect_smtp(self) -> None:
        """Connect to SMTP server."""

        def _do_connect() -> smtplib.SMTP:
            if self.config.smtp_use_ssl:
                smtp = smtplib.SMTP_SSL(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self.config.timeout,
                )
            else:
                smtp = smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self.config.timeout,
                )
                if self.config.smtp_use_tls:
                    smtp.starttls()

            if self.config.username and self.config.password_str:
                smtp.login(self.config.username, self.config.password_str)

            return smtp

        self._smtp = await asyncio.to_thread(_do_connect)

    async def _connect_imap(self) -> None:
        """Connect to IMAP server."""

        def _do_connect() -> imaplib.IMAP4:
            if self.config.imap_use_ssl:
                imap = imaplib.IMAP4_SSL(
                    self.config.imap_host,
                    self.config.imap_port,
                )
            else:
                imap = imaplib.IMAP4(
                    self.config.imap_host,
                    self.config.imap_port,
                )

            if self.config.username and self.config.password_str:
                imap.login(self.config.username, self.config.password_str)

            # Select default mailbox
            imap.select(self.config.default_mailbox)

            return imap

        self._imap = await asyncio.to_thread(_do_connect)

    async def disconnect(self) -> None:
        """Disconnect from email servers."""
        if self._smtp is not None:
            try:

                def _close_smtp() -> None:
                    self._smtp.quit()

                await asyncio.to_thread(_close_smtp)
            except Exception:
                pass
            self._smtp = None

        if self._imap is not None:
            try:

                def _close_imap() -> None:
                    self._imap.close()
                    self._imap.logout()

                await asyncio.to_thread(_close_imap)
            except Exception:
                pass
            self._imap = None

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
        """Fetch a user by email address.

        Note: Email doesn't have a user lookup API. This creates
        a basic user object from the email address.

        Accepts flexible inputs:
        - Email address as positional arg, id=, or email=
        - User object (returns as-is)
        - name= to search by name (cache only)

        Args:
            identifier: A User object or email address string.
            id: Email address.
            name: Display name to search for (cache only).
            email: Email address (same as id).
            handle: Treated same as email.

        Returns:
            The user object.
        """
        # Handle User object input
        if isinstance(identifier, EmailUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id (email)
        if identifier and not id:
            id = str(identifier)

        # email= and handle= are synonyms for id= in Email backend
        if not id:
            id = email or handle

        # Check cache first
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached

        # Search by name in cache
        if name:
            for cached_user in self.users._by_id.values():
                if isinstance(cached_user, EmailUser):
                    if cached_user.name.lower() == name.lower():
                        return cached_user

        # Create user from email address
        if id:
            # Parse email address
            parsed_name, email_addr = parseaddr(id)

            user = EmailUser(
                id=email_addr or id,
                name=parsed_name or email_addr or id,
                handle=email_addr or id,
                email=email_addr or id,
            )
            self.users.add(user)
            return user

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel (mailbox/folder).

        Accepts flexible inputs:
        - Mailbox name as positional arg or id=
        - Channel object (returns as-is)
        - name= treated same as id

        Args:
            identifier: A Channel object or mailbox name string.
            id: Mailbox/folder name (e.g., "INBOX", "Sent").
            name: Same as id.

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

        # name= is synonym for id=
        if not id:
            id = name

        if not id:
            return None

        # Check cache first
        cached = self.channels.get_by_id(id)
        if cached:
            return cached

        if self._imap is None:
            # If not connected to IMAP, just create the channel object
            channel = EmailChannel(
                id=id,
                name=id,
            )
            self.channels.add(channel)
            return channel

        try:

            def _check_mailbox() -> bool:
                status, _ = self._imap.select(id, readonly=True)
                return status == "OK"

            exists = await asyncio.to_thread(_check_mailbox)

            if exists:
                channel = EmailChannel(
                    id=id,
                    name=id,
                )
                self.channels.add(channel)
                return channel
        except Exception:
            pass

        return None

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch messages (emails) from a mailbox.

        Args:
            channel_id: The mailbox/folder name.
            limit: Maximum number of messages.
            before: Fetch messages before this date (YYYY-MM-DD).
            after: Fetch messages after this date (YYYY-MM-DD).

        Returns:
            List of email messages.
        """
        if self._imap is None:
            raise RuntimeError("IMAP not connected")

        try:

            def _fetch_messages() -> List[dict]:
                # Select mailbox
                self._imap.select(channel_id, readonly=True)

                # Build search criteria
                criteria = ["ALL"]
                if before:
                    criteria = [f"BEFORE {before}"]
                if after:
                    criteria = [f"SINCE {after}"]

                # Search for messages
                _, data = self._imap.search(None, *criteria)
                message_ids = data[0].split()

                # Get latest messages up to limit
                message_ids = message_ids[-limit:] if len(message_ids) > limit else message_ids

                messages = []
                for msg_id in reversed(message_ids):  # Newest first
                    _, msg_data = self._imap.fetch(msg_id, "(RFC822)")
                    if msg_data[0] is not None:
                        email_body = msg_data[0][1]
                        email_message = email_lib.message_from_bytes(email_body)

                        # Extract basic info
                        subject = email_message.get("Subject", "")
                        from_addr = email_message.get("From", "")
                        date_str = email_message.get("Date", "")
                        message_id = email_message.get("Message-ID", str(msg_id))

                        # Parse date
                        try:
                            timestamp = parsedate_to_datetime(date_str)
                        except Exception:
                            timestamp = datetime.now(timezone.utc)

                        # Get body
                        body = ""
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = email_message.get_payload(decode=True).decode("utf-8", errors="ignore")

                        messages.append(
                            {
                                "id": message_id,
                                "subject": subject,
                                "from": from_addr,
                                "body": body,
                                "timestamp": timestamp,
                            }
                        )

                return messages

            raw_messages = await asyncio.to_thread(_fetch_messages)

            messages: List[Message] = []
            for raw in raw_messages:
                _, sender_email = parseaddr(raw["from"])
                message = EmailMessage(
                    id=raw["id"],
                    content=raw["body"],
                    timestamp=raw["timestamp"],
                    user_id=sender_email,
                    channel_id=channel_id,
                    subject=raw["subject"],
                )
                messages.append(message)

            return messages

        except Exception as e:
            raise RuntimeError(f"Failed to fetch messages: {e}") from e

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send an email message.

        Args:
            channel_id: The recipient email address or comma-separated list.
            content: The email body (HTML).
            **kwargs: Additional options:
                - subject: Email subject.
                - cc: CC recipients.
                - bcc: BCC recipients.
                - reply_to: Reply-To address.
                - plain_text: Plain text alternative body.

        Returns:
            The sent message.
        """
        if self._smtp is None:
            raise RuntimeError("SMTP not connected")

        subject = kwargs.get("subject", "")
        cc = kwargs.get("cc", "")
        bcc = kwargs.get("bcc", "")
        reply_to = kwargs.get("reply_to", "")
        plain_text = kwargs.get("plain_text", "")

        try:

            def _send_email() -> str:
                # Create message
                msg = MIMEMultipart("alternative")
                msg["From"] = self.config.formatted_from
                msg["To"] = channel_id
                msg["Subject"] = subject

                if cc:
                    msg["Cc"] = cc
                if reply_to:
                    msg["Reply-To"] = reply_to

                # Generate message ID
                message_id = f"<{uuid.uuid4()}@{self.config.smtp_host}>"
                msg["Message-ID"] = message_id

                # Add content with signature
                body_content = content
                if self.config.signature:
                    body_content += f"\n\n{self.config.signature}"

                # Add plain text and HTML parts
                if plain_text:
                    msg.attach(MIMEText(plain_text, "plain"))
                msg.attach(MIMEText(body_content, "html"))

                # Build recipient list
                recipients = [addr.strip() for addr in channel_id.split(",")]
                if cc:
                    recipients.extend([addr.strip() for addr in cc.split(",")])
                if bcc:
                    recipients.extend([addr.strip() for addr in bcc.split(",")])

                # Send
                self._smtp.sendmail(
                    self.config.effective_from_address,
                    recipients,
                    msg.as_string(),
                )

                return message_id

            message_id = await asyncio.to_thread(_send_email)

            return EmailMessage(
                id=message_id,
                content=content,
                timestamp=datetime.now(timezone.utc),
                user_id=self.config.effective_from_address,
                channel_id=channel_id,
                subject=subject,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to send email: {e}") from e

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit an email message.

        Note: Email doesn't support editing. This raises NotImplementedError.

        Args:
            channel_id: The mailbox.
            message_id: The message ID.
            content: The new content.
            **kwargs: Additional options.

        Raises:
            NotImplementedError: Email doesn't support editing.
        """
        raise NotImplementedError("Email does not support message editing")

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete an email message.

        Note: This marks the message as deleted in IMAP.
        The message may still exist in Trash depending on server config.

        Args:
            channel_id: The mailbox containing the message.
            message_id: The message ID.
        """
        if self._imap is None:
            raise RuntimeError("IMAP not connected")

        try:

            def _delete_message() -> None:
                self._imap.select(channel_id)
                # Search for message by ID
                _, data = self._imap.search(None, f'HEADER Message-ID "{message_id}"')
                for num in data[0].split():
                    # Mark as deleted
                    self._imap.store(num, "+FLAGS", "\\Deleted")
                # Expunge deleted messages
                self._imap.expunge()

            await asyncio.to_thread(_delete_message)

        except Exception as e:
            raise RuntimeError(f"Failed to delete email: {e}") from e

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set presence for email.

        Note: Email doesn't support presence.

        Args:
            status: Presence status.
            status_text: Status text.
            **kwargs: Additional options.

        Raises:
            NotImplementedError: Email doesn't support presence.
        """
        raise NotImplementedError("Email does not support presence")

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get a user's presence.

        Note: Email doesn't support presence.

        Args:
            user_id: The email address.

        Returns:
            None - Email doesn't support presence.
        """
        return None

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message.

        Note: Email doesn't support reactions.

        Args:
            channel_id: The mailbox.
            message_id: The message ID.
            emoji: The emoji.

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
        """Remove a reaction from a message.

        Note: Email doesn't support reactions.

        Args:
            channel_id: The mailbox.
            message_id: The message ID.
            emoji: The emoji.

        Raises:
            NotImplementedError: Email doesn't support reactions.
        """
        raise NotImplementedError("Email does not support reactions")

    def mention_user(self, user: User) -> str:
        """Format a user mention for email.

        Args:
            user: The user to mention.

        Returns:
            HTML mailto link.
        """
        if isinstance(user, EmailUser):
            return _mention_user(user)
        # For base User, create mailto link
        email = user.email or user.id
        name = user.display_name
        return f"<a href='mailto:{email}'>{name}</a>"

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for email.

        Args:
            channel: The channel (mailing list) to mention.

        Returns:
            The mailing list address or name.
        """
        return channel.name or channel.id
