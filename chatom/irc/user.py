"""IRC-specific User model.

This module provides the IRC-specific User class.
"""

from typing import List

from chatom.base import Field, User

__all__ = ("IRCUser",)


class IRCUser(User):
    """IRC-specific user (nick) with additional IRC fields.

    Attributes:
        nick: The user's IRC nickname.
        ident: The user's ident/username.
        host: The user's hostname.
        realname: The user's real name (GECOS).
        server: The server the user is connected to.
        modes: User modes (e.g., 'o' for operator).
        channels: List of channels the user is in.
        is_away: Whether the user is marked as away.
        away_message: The user's away message.
    """

    nick: str = Field(
        default="",
        description="The user's IRC nickname.",
    )
    ident: str = Field(
        default="",
        description="The user's ident/username.",
    )
    host: str = Field(
        default="",
        description="The user's hostname.",
    )
    realname: str = Field(
        default="",
        description="The user's real name (GECOS).",
    )
    server: str = Field(
        default="",
        description="The server the user is connected to.",
    )
    modes: str = Field(
        default="",
        description="User modes (e.g., 'o' for operator).",
    )
    channels: List[str] = Field(
        default_factory=list,
        description="List of channels the user is in.",
    )
    is_away: bool = Field(
        default=False,
        description="Whether the user is marked as away.",
    )
    away_message: str = Field(
        default="",
        description="The user's away message.",
    )

    @property
    def hostmask(self) -> str:
        """Get the full IRC hostmask.

        Returns:
            str: The hostmask in nick!ident@host format.
        """
        return f"{self.nick}!{self.ident}@{self.host}"

    @property
    def display_name(self) -> str:
        """Get the display name (nick).

        Returns:
            str: The user's nickname.
        """
        return self.nick or self.handle or self.name

    @property
    def is_operator(self) -> bool:
        """Check if user is an IRC operator.

        Returns:
            bool: True if user has operator mode.
        """
        return "o" in self.modes
