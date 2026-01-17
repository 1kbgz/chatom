"""Slack-specific User model.

This module provides the Slack-specific User class.
"""

from chatom.base import Field, User

__all__ = ("SlackUser",)


class SlackUser(User):
    """Slack-specific user with additional Slack fields.

    Attributes:
        real_name: The user's real name from their profile.
        display_name: The user's display name.
        team_id: The ID of the user's workspace/team.
        is_admin: Whether the user is a workspace admin.
        is_owner: Whether the user is a workspace owner.
        is_restricted: Whether the user is a multi-channel guest.
        is_ultra_restricted: Whether the user is a single-channel guest.
        tz: The user's timezone identifier.
        tz_offset: The user's timezone offset in seconds.
        title: The user's job title.
        phone: The user's phone number.
        skype: The user's Skype name.
        status_text: The user's current status text.
        status_emoji: The user's current status emoji.
    """

    real_name: str = Field(
        default="",
        description="The user's real name from their profile.",
    )
    display_name: str = Field(
        default="",
        description="The user's display name.",
    )
    team_id: str = Field(
        default="",
        description="The ID of the user's workspace/team.",
    )
    is_admin: bool = Field(
        default=False,
        description="Whether the user is a workspace admin.",
    )
    is_owner: bool = Field(
        default=False,
        description="Whether the user is a workspace owner.",
    )
    is_restricted: bool = Field(
        default=False,
        description="Whether the user is a multi-channel guest.",
    )
    is_ultra_restricted: bool = Field(
        default=False,
        description="Whether the user is a single-channel guest.",
    )
    tz: str = Field(
        default="",
        description="The user's timezone identifier.",
    )
    tz_offset: int = Field(
        default=0,
        description="The user's timezone offset in seconds.",
    )
    title: str = Field(
        default="",
        description="The user's job title.",
    )
    phone: str = Field(
        default="",
        description="The user's phone number.",
    )
    skype: str = Field(
        default="",
        description="The user's Skype name.",
    )
    status_text: str = Field(
        default="",
        description="The user's current status text.",
    )
    status_emoji: str = Field(
        default="",
        description="The user's current status emoji.",
    )

    @property
    def mention_name(self) -> str:
        """Get the best name to use when mentioning.

        Returns:
            str: The display name, real name, or handle.
        """
        return self.display_name or self.real_name or self.handle or self.name
