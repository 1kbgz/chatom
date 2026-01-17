"""Symphony-specific User model.

This module provides the Symphony-specific User class.
"""

from typing import List

from chatom.base import Field, User

__all__ = ("SymphonyUser",)


class SymphonyUser(User):
    """Symphony-specific user with additional Symphony fields.

    Attributes:
        first_name: The user's first name.
        last_name: The user's last name.
        display_name: The user's display name.
        company: The user's company name.
        department: The user's department.
        title: The user's job title.
        location: The user's location.
        work_phone: The user's work phone number.
        mobile_phone: The user's mobile phone number.
        account_type: The type of Symphony account.
        roles: List of user roles.
    """

    first_name: str = Field(
        default="",
        description="The user's first name.",
    )
    last_name: str = Field(
        default="",
        description="The user's last name.",
    )
    display_name: str = Field(
        default="",
        description="The user's display name.",
    )
    company: str = Field(
        default="",
        description="The user's company name.",
    )
    department: str = Field(
        default="",
        description="The user's department.",
    )
    title: str = Field(
        default="",
        description="The user's job title.",
    )
    location: str = Field(
        default="",
        description="The user's location.",
    )
    work_phone: str = Field(
        default="",
        description="The user's work phone number.",
    )
    mobile_phone: str = Field(
        default="",
        description="The user's mobile phone number.",
    )
    account_type: str = Field(
        default="",
        description="The type of Symphony account.",
    )
    roles: List[str] = Field(
        default_factory=list,
        description="List of user roles.",
    )

    @property
    def full_name(self) -> str:
        """Get the user's full name.

        Returns:
            str: First and last name combined.
        """
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.display_name or self.name

    @property
    def mention_name(self) -> str:
        """Get the best name to use when mentioning.

        Returns:
            str: The display name or full name.
        """
        return self.display_name or self.full_name
