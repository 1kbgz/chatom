"""Organization model for chatom.

This module provides the base Organization class representing a chat platform
organization (e.g., Discord guild, Slack workspace, Symphony pod).
"""

from typing import Optional

from .base import Field, Identifiable

__all__ = ("Organization",)


class Organization(Identifiable):
    """Represents an organization on a chat platform.

    An organization is the top-level container for users and channels.
    This maps to different concepts on different platforms:
    - Discord: Guild (server)
    - Slack: Workspace (team)
    - Symphony: Pod

    Attributes:
        id: Platform-specific unique identifier.
        name: Display name of the organization.
        description: Description or purpose of the organization.
        icon_url: URL to the organization's icon/logo image.
        member_count: Approximate number of members, if available.
        owner_id: ID of the organization owner, if applicable.
    """

    description: str = Field(
        default="",
        description="Description or purpose of the organization.",
    )
    icon_url: str = Field(
        default="",
        description="URL to the organization's icon/logo image.",
    )
    member_count: Optional[int] = Field(
        default=None,
        description="Approximate number of members, if available.",
    )
    owner_id: str = Field(
        default="",
        description="ID of the organization owner, if applicable.",
    )

    @property
    def display_name(self) -> str:
        """Get the best available display name for the organization.

        Returns:
            str: The name or id (in order of preference).
        """
        return self.name or self.id
