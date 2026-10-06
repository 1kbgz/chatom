"""LINE-specific user model."""

from collections.abc import Mapping
from typing import Any

from ..base import Field, User
from ..base.conversion import register_backend_type
from ..base.user import Avatar

__all__ = ("LineUser",)


class LineUser(User):
    """User profile returned by the LINE Messaging API."""

    picture_url: str = Field(default="")
    status_message: str = Field(default="")
    language: str = Field(default="")

    @classmethod
    def from_api(cls, data: Mapping[str, Any]) -> "LineUser":
        """Build a user from a LINE profile response."""
        return cls(
            id=str(data.get("userId", "")),
            name=str(data.get("displayName", "")),
            display_name=str(data.get("displayName", "")),
            avatar=Avatar(url=str(data.get("pictureUrl", ""))) if data.get("pictureUrl") else None,
            picture_url=str(data.get("pictureUrl", "")),
            status_message=str(data.get("statusMessage", "")),
            language=str(data.get("language", "")),
        )


register_backend_type("line", User, LineUser)
