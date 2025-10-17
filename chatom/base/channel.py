from .base import BaseModel, Field

__all__ = ("Channel",)


class Channel(BaseModel):
    id: str = Field(
        default="",
        description="id of the room, if necessary",
    )
    name: str = Field(
        default="",
        description="The channel/room name.",
    )
