"""Zulip-specific user model."""

from ..base import Field, User

__all__ = ("ZulipUser",)


class ZulipUser(User):
    """User fields exposed by Zulip's users API."""

    role: int | None = Field(default=None, description="Zulip organization role value.")
    is_active: bool = Field(default=True, description="Whether the account is active.")
    is_admin: bool = Field(default=False, description="Whether the user is an organization administrator.")
    is_owner: bool = Field(default=False, description="Whether the user is an organization owner.")
    timezone: str = Field(default="", description="User's configured timezone.")

    @property
    def mention_name(self) -> str:
        return self.name or self.display_name or self.email or self.id
