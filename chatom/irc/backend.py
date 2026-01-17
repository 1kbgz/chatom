"""IRC backend implementation for chatom.

This module provides the IRC backend using the irc package.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, ClassVar, List, Optional, Union

from pydantic import Field

from ..backend_registry import BackendBase
from ..base import (
    IRC_CAPABILITIES,
    BackendCapabilities,
    Channel,
    Message,
    Presence,
    User,
)
from ..format.variant import Format
from .channel import IRCChannel
from .config import IRCConfig
from .mention import mention_user as _mention_user
from .message import IRCMessage
from .presence import IRCPresence
from .user import IRCUser

__all__ = ("IRCBackend",)

# Try to import irc library
try:
    from irc.client import ServerNotConnectedError
    from irc.client_aio import AioConnection, AioReactor

    HAS_IRC = True
except ImportError:
    HAS_IRC = False
    AioReactor = None  # type: ignore
    AioConnection = None  # type: ignore
    ServerNotConnectedError = Exception  # type: ignore


class IRCBackend(BackendBase):
    """IRC backend implementation using the irc package.

    This provides the backend interface for IRC using the irc package's
    asyncio client. Note that IRC has limited capabilities compared to
    modern chat platforms - no message history, limited presence, etc.

    Attributes:
        name: The backend identifier ('irc').
        display_name: Human-readable name.
        format: IRC uses plain text.
        capabilities: IRC-specific capabilities.
        config: IRC-specific configuration.

    Example:
        >>> from chatom.irc import IRCBackend, IRCConfig
        >>> config = IRCConfig(
        ...     server="irc.libera.chat",
        ...     port=6697,
        ...     nickname="mybot",
        ...     use_ssl=True,
        ... )
        >>> backend = IRCBackend(config=config)
        >>> await backend.connect()
    """

    name: ClassVar[str] = "irc"
    display_name: ClassVar[str] = "IRC"
    format: ClassVar[Format] = Format.PLAINTEXT

    # Type classes for this backend (used by conversion module)
    user_class: ClassVar[type] = IRCUser
    channel_class: ClassVar[type] = IRCChannel
    presence_class: ClassVar[type] = IRCPresence

    capabilities: Optional[BackendCapabilities] = IRC_CAPABILITIES
    config: IRCConfig = Field(default_factory=IRCConfig)

    # IRC client instances
    _reactor: Any = None
    _connection: Any = None
    _message_counter: int = 0

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    async def connect(self) -> None:
        """Connect to IRC server.

        This creates an IRC client and connects to the configured server.

        Raises:
            RuntimeError: If irc package is not installed or config is missing.
        """
        if not HAS_IRC:
            raise RuntimeError("irc package is not installed. Install with: pip install irc")

        if not self.config.has_server:
            raise RuntimeError("IRC server is required")

        if not self.config.has_nickname:
            raise RuntimeError("IRC nickname is required")

        # Create reactor with current event loop
        loop = asyncio.get_event_loop()
        self._reactor = AioReactor(loop=loop)
        self._connection = self._reactor.server()

        # Build connection kwargs
        connect_kwargs: dict[str, Any] = {
            "server": self.config.server,
            "port": self.config.port,
            "nickname": self.config.nickname,
            "username": self.config.effective_username,
            "ircname": self.config.effective_realname,
        }

        if self.config.password_str:
            connect_kwargs["password"] = self.config.password_str

        # Connect to server
        await self._connection.connect(**connect_kwargs)
        self.connected = True

        # Auto-join channels
        for channel in self.config.auto_join_channels:
            self._connection.join(channel)

        # Identify with NickServ if configured
        if self.config.nickserv_password_str:
            self._connection.privmsg("NickServ", f"IDENTIFY {self.config.nickserv_password_str}")

    async def disconnect(self) -> None:
        """Disconnect from IRC."""
        if self._connection is not None:
            try:
                self._connection.quit("Goodbye")
            except Exception:
                pass
            self._connection = None

        if self._reactor is not None:
            self._reactor = None

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
        """Fetch a user from IRC by nick.

        Note: IRC doesn't have a user info API. This creates a basic
        user object from the nickname.

        Accepts flexible inputs:
        - Nickname as positional arg or id=
        - User object (returns as-is)
        - name= or handle= treated same as nickname

        Args:
            identifier: A User object or nickname string.
            id: IRC nickname.
            name: Same as nickname for IRC.
            email: Not supported by IRC.
            handle: Same as nickname for IRC.

        Returns:
            The user object.
        """
        # Handle User object input
        if isinstance(identifier, IRCUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id (nickname)
        if identifier and not id:
            id = str(identifier)

        # Name or handle work same as id for IRC
        if not id:
            id = name or handle

        if not id:
            return None

        # Check cache first
        cached = self.users.get_by_id(id)
        if cached:
            return cached

        # Create a basic user object (IRC doesn't have user info API)
        user = IRCUser(
            id=id,
            name=id,
            handle=id,
            nick=id,
        )
        self.users.add(user)
        return user

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel from IRC.

        Accepts flexible inputs:
        - Channel name as positional arg or id=
        - Channel object (returns as-is)
        - name= treated same as id

        Channel names are normalized to start with #.

        Args:
            identifier: A Channel object or channel name string.
            id: IRC channel name.
            name: Same as id for IRC.

        Returns:
            The channel object.
        """
        # Handle Channel object input
        if isinstance(identifier, IRCChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Name works same as id for IRC
        if not id:
            id = name

        if not id:
            return None

        # Normalize channel name
        channel_name = id if id.startswith("#") else f"#{id}"

        # Check cache first
        cached = self.channels.get_by_id(channel_name)
        if cached:
            return cached

        # Create a basic channel object
        channel = IRCChannel(
            id=channel_name,
            name=channel_name,
        )
        self.channels.add(channel)
        return channel

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch messages from IRC.

        Note: IRC doesn't have message history by default.
        This returns an empty list unless using a bouncer or logging service.

        Args:
            channel_id: The channel name.
            limit: Maximum number of messages.
            before: Not supported in IRC.
            after: Not supported in IRC.

        Returns:
            Empty list (IRC has no message history).
        """
        # IRC doesn't have message history
        return []

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a message to an IRC channel or user.

        Args:
            channel_id: The channel name or nick for private message.
            content: The message content.
            **kwargs: Additional options (unused in IRC).

        Returns:
            The sent message.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IRC")

        # Send PRIVMSG
        self._connection.privmsg(channel_id, content)

        # Create message object
        self._message_counter += 1
        message = IRCMessage(
            id=str(self._message_counter),
            content=content,
            timestamp=datetime.now(timezone.utc),
            user_id=self.config.nickname,
            channel_id=channel_id,
        )
        return message

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit an IRC message.

        Note: IRC doesn't support message editing.
        This raises NotImplementedError.

        Args:
            channel_id: The channel name.
            message_id: The message ID.
            content: The new content.
            **kwargs: Additional options.

        Raises:
            NotImplementedError: IRC doesn't support message editing.
        """
        raise NotImplementedError("IRC does not support message editing")

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete an IRC message.

        Note: IRC doesn't support message deletion.
        This raises NotImplementedError.

        Args:
            channel_id: The channel name.
            message_id: The message ID.

        Raises:
            NotImplementedError: IRC doesn't support message deletion.
        """
        raise NotImplementedError("IRC does not support message deletion")

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set user presence on IRC.

        IRC uses the AWAY command for presence. Setting status to anything
        other than 'online' or 'available' will set an away message.

        Args:
            status: Presence status ('online', 'away', etc.).
            status_text: Away message.
            **kwargs: Additional options.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IRC")

        status_lower = status.lower()
        if status_lower in ("online", "available", "back"):
            # Remove away status
            self._connection.send_raw("AWAY")
        else:
            # Set away message
            away_message = status_text or status.capitalize()
            self._connection.send_raw(f"AWAY :{away_message}")

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get a user's presence on IRC.

        Note: IRC doesn't have native presence queries.
        You would need to send a WHOIS and parse the response,
        which is not a simple request/response.

        Args:
            user_id: The nickname.

        Returns:
            None - IRC doesn't support simple presence queries.
        """
        # IRC presence requires WHOIS which is async and event-based
        # Return a basic presence from cache if available
        return None

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message.

        Note: IRC doesn't support reactions.
        This raises NotImplementedError.

        Args:
            channel_id: The channel name.
            message_id: The message ID.
            emoji: The emoji.

        Raises:
            NotImplementedError: IRC doesn't support reactions.
        """
        raise NotImplementedError("IRC does not support reactions")

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction from a message.

        Note: IRC doesn't support reactions.
        This raises NotImplementedError.

        Args:
            channel_id: The channel name.
            message_id: The message ID.
            emoji: The emoji.

        Raises:
            NotImplementedError: IRC doesn't support reactions.
        """
        raise NotImplementedError("IRC does not support reactions")

    async def join_channel(self, channel_id: str, **kwargs: Any) -> None:
        """Join an IRC channel.

        Args:
            channel_id: The channel name.
            **kwargs: Additional options:
                - key: Channel password/key.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IRC")

        key = kwargs.get("key")
        if key:
            self._connection.join(channel_id, key)
        else:
            self._connection.join(channel_id)

    async def leave_channel(self, channel_id: str, **kwargs: Any) -> None:
        """Leave an IRC channel.

        Args:
            channel_id: The channel name.
            **kwargs: Additional options:
                - message: Part message.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IRC")

        message = kwargs.get("message", "")
        self._connection.part(channel_id, message)

    async def part_channel(self, channel: str, message: str = "") -> None:
        """Leave an IRC channel.

        This is an alias for leave_channel using IRC terminology.

        Args:
            channel: The channel name.
            message: Optional part message.
        """
        await self.leave_channel(channel, message=message)

    async def send_action(self, target: str, action: str) -> None:
        """Send a CTCP ACTION (/me).

        Args:
            target: The channel or nick.
            action: The action text.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IRC")

        self._connection.action(target, action)

    async def send_notice(self, target: str, text: str) -> None:
        """Send a NOTICE message.

        Args:
            target: The channel or nick.
            text: The notice text.
        """
        if self._connection is None:
            raise RuntimeError("Not connected to IRC")

        self._connection.notice(target, text)

    def mention_user(self, user: User) -> str:
        """Format a user mention for IRC.

        Args:
            user: The user to mention.

        Returns:
            The user's nickname.
        """
        if isinstance(user, IRCUser):
            return _mention_user(user)
        return user.name or user.id

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for IRC.

        Args:
            channel: The channel to mention.

        Returns:
            The channel name (with # prefix if needed).
        """
        name = channel.name or channel.id
        if not name.startswith("#"):
            name = f"#{name}"
        return name
