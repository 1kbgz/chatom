"""IRC-specific Message model.

This module provides the IRC-specific Message class.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from chatom.base import Field, Message

if TYPE_CHECKING:
    from chatom.format import FormattedMessage

__all__ = (
    "IRCMessage",
    "IRCMessageType",
)


class IRCMessageType(str, Enum):
    """IRC message types.

    Common IRC message types based on IRC protocol.
    """

    PRIVMSG = "PRIVMSG"
    NOTICE = "NOTICE"
    ACTION = "ACTION"
    CTCP = "CTCP"
    CTCP_REPLY = "CTCP_REPLY"


class IRCMessage(Message):
    """IRC-specific message with additional IRC fields.

    Based on IRC protocol message structure.

    Attributes:
        message_type: The IRC message type (PRIVMSG, NOTICE, etc.).
        target: The target of the message (channel or nick).
        prefix: The message prefix (nick!user@host).
        nick: The sender's nickname.
        username: The sender's username (from nick!user@host).
        host: The sender's hostname.
        is_action: Whether this is a CTCP ACTION (/me).
        is_notice: Whether this is a NOTICE.
        ctcp_command: CTCP command if this is a CTCP message.
        ctcp_params: CTCP parameters if this is a CTCP message.
        raw: The raw IRC message line.
    """

    message_type: IRCMessageType = Field(
        default=IRCMessageType.PRIVMSG,
        description="The IRC message type.",
    )
    target: str = Field(
        default="",
        description="The target of the message (channel or nick).",
    )
    prefix: Optional[str] = Field(
        default=None,
        description="The message prefix (nick!user@host).",
    )
    nick: Optional[str] = Field(
        default=None,
        description="The sender's nickname.",
    )
    username: Optional[str] = Field(
        default=None,
        description="The sender's username (from prefix).",
    )
    host: Optional[str] = Field(
        default=None,
        description="The sender's hostname.",
    )
    is_action: bool = Field(
        default=False,
        description="Whether this is a CTCP ACTION (/me).",
    )
    is_notice: bool = Field(
        default=False,
        description="Whether this is a NOTICE.",
    )
    ctcp_command: Optional[str] = Field(
        default=None,
        description="CTCP command if this is a CTCP message.",
    )
    ctcp_params: Optional[str] = Field(
        default=None,
        description="CTCP parameters if this is a CTCP message.",
    )
    raw: Optional[str] = Field(
        default=None,
        description="The raw IRC message line.",
    )

    @property
    def is_channel_message(self) -> bool:
        """Check if this message was sent to a channel."""
        return self.target.startswith("#") or self.target.startswith("&")

    @property
    def is_private_message(self) -> bool:
        """Check if this is a private message (query)."""
        return not self.is_channel_message

    @property
    def is_ctcp(self) -> bool:
        """Check if this is a CTCP message."""
        return self.ctcp_command is not None

    @classmethod
    def from_raw(cls, raw: str) -> "IRCMessage":
        """Parse an IRC message from a raw line.

        Args:
            raw: The raw IRC message line.

        Returns:
            An IRCMessage instance.
        """
        # Basic parsing - in practice you'd use a proper IRC parser
        prefix = None
        nick = None
        username = None
        host = None

        line = raw.strip()

        # Parse prefix if present
        if line.startswith(":"):
            prefix, line = line[1:].split(" ", 1)
            if "!" in prefix:
                nick, rest = prefix.split("!", 1)
                if "@" in rest:
                    username, host = rest.split("@", 1)
                else:
                    username = rest
            elif "@" in prefix:
                nick, host = prefix.split("@", 1)
            else:
                nick = prefix

        # Parse command and params
        parts = line.split(" ", 2)
        command = parts[0].upper() if parts else ""
        target = parts[1] if len(parts) > 1 else ""
        content = parts[2][1:] if len(parts) > 2 and parts[2].startswith(":") else ""

        # Determine message type
        msg_type = IRCMessageType.PRIVMSG
        is_action = False
        is_notice = False
        ctcp_command = None
        ctcp_params = None

        if command == "NOTICE":
            msg_type = IRCMessageType.NOTICE
            is_notice = True
        elif command == "PRIVMSG":
            # Check for CTCP
            if content.startswith("\x01") and content.endswith("\x01"):
                content = content[1:-1]
                if content.startswith("ACTION "):
                    msg_type = IRCMessageType.ACTION
                    is_action = True
                    content = content[7:]
                else:
                    msg_type = IRCMessageType.CTCP
                    if " " in content:
                        ctcp_command, ctcp_params = content.split(" ", 1)
                    else:
                        ctcp_command = content
                        ctcp_params = ""
                    content = ""

        return cls(
            id=raw[:50],  # Use first 50 chars as ID
            content=content,
            message_type=msg_type,
            target=target,
            channel_id=target if target.startswith("#") or target.startswith("&") else "",
            prefix=prefix,
            nick=nick,
            author_id=nick or "",
            username=username,
            host=host,
            is_action=is_action,
            is_notice=is_notice,
            ctcp_command=ctcp_command,
            ctcp_params=ctcp_params,
            raw=raw,
            backend="irc",
        )

    def to_formatted(self) -> "FormattedMessage":
        """Convert this IRC message to a FormattedMessage.

        IRC messages are plain text, so this creates a simple
        FormattedMessage from the content.

        Returns:
            FormattedMessage: The formatted message representation.
        """
        from chatom.format import FormattedMessage

        fm = FormattedMessage()

        # Handle ACTION messages specially
        if self.is_action:
            fm.add_italic(f"* {self.nick} {self.content}")
        else:
            fm.add_text(self.content)

        # Add metadata
        fm.metadata["source_backend"] = "irc"
        fm.metadata["message_id"] = self.id
        if self.nick:
            fm.metadata["author_id"] = self.nick
            fm.metadata["nick"] = self.nick
        if self.target:
            fm.metadata["target"] = self.target
            if self.is_channel_message:
                fm.metadata["channel_id"] = self.target
        if self.prefix:
            fm.metadata["prefix"] = self.prefix
        if self.ctcp_command:
            fm.metadata["ctcp_command"] = self.ctcp_command
        fm.metadata["is_action"] = self.is_action
        fm.metadata["is_notice"] = self.is_notice

        return fm

    @classmethod
    def from_formatted(
        cls,
        formatted: "FormattedMessage",
        **kwargs: Any,
    ) -> "IRCMessage":
        """Create an IRCMessage from a FormattedMessage.

        Renders the FormattedMessage in plain text for IRC.

        Args:
            formatted: The FormattedMessage to convert.
            **kwargs: Additional message attributes.

        Returns:
            IRCMessage: A new IRCMessage instance.
        """
        from chatom.format import Format

        content = formatted.render(Format.PLAINTEXT)

        return cls(
            content=content,
            metadata=dict(formatted.metadata),
            backend="irc",
            **kwargs,
        )
