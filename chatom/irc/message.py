"""IRC-specific message model."""

from pydantic import AliasChoices

from ..base import Field, Message

__all__ = ("IRCMessage",)


class IRCMessage(Message):
    """Message received from an IRC command."""

    command: str = Field(default="PRIVMSG")
    target: str = Field(default="")
    irc_tags: dict[str, str] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("irc_tags", "tags"),
        serialization_alias="tags",
    )
    hostmask: str = Field(default="")

    @property
    def msgid(self) -> str:
        return self.irc_tags.get("msgid", self.id)
