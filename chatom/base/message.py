from typing import List

from .base import BaseModel, Field
from .channel import Channel
from .user import User

__all__ = ("Message",)


class Message(BaseModel):
    text: str = Field(
        default="",
        description="The content of the message.",
    )
    channel: Channel = Field(
        description="The channel/room where the message wssas/should be sent.",
    )
    user: User = Field(
        description="The user who authored the message.",
    )
    tags: List[User] = Field(
        default_factory=list,
        description="List of users tagged in the message.",
    )
