"""IRC-specific user model."""

from ..base import Field, User
from ..base.conversion import register_backend_type

__all__ = ("IRCUser",)


class IRCUser(User):
    """IRC user identified primarily by nickname."""

    nickname: str = Field(default="")
    username: str = Field(default="")
    hostname: str = Field(default="")
    account: str = Field(default="")
    away: bool = Field(default=False)

    @property
    def hostmask(self) -> str:
        if not self.username and not self.hostname:
            return self.nickname or self.id
        return f"{self.nickname or self.id}!{self.username}@{self.hostname}"

    @classmethod
    def from_prefix(cls, prefix: str) -> "IRCUser":
        nickname, separator, remainder = prefix.partition("!")
        username, host_separator, hostname = remainder.partition("@")
        return cls(
            id=nickname,
            name=nickname,
            handle=nickname,
            nickname=nickname,
            username=username if separator else "",
            hostname=hostname if host_separator else "",
        )


register_backend_type("irc", User, IRCUser)
