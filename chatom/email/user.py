"""Email-specific User model.

This module provides the Email-specific User class.
"""

from chatom.base import Field, User

__all__ = ("EmailUser",)


class EmailUser(User):
    """Email-specific user with additional email fields.

    Attributes:
        first_name: The user's first name.
        last_name: The user's last name.
        display_name: The user's preferred display name.
        reply_to: Alternative reply-to email address.
        organization: The user's organization.
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
        description="The user's preferred display name.",
    )
    reply_to: str = Field(
        default="",
        description="Alternative reply-to email address.",
    )
    organization: str = Field(
        default="",
        description="The user's organization.",
    )

    @property
    def full_name(self) -> str:
        """Get the user's full name.

        Returns:
            str: First and last name combined, or display name.
        """
        parts = [self.first_name, self.last_name]
        full = " ".join(p for p in parts if p)
        return full or self.display_name or self.name

    @property
    def formatted_address(self) -> str:
        """Get the formatted email address with name.

        Returns:
            str: Formatted as 'Name <email@example.com>'.
        """
        name = self.full_name
        if name and self.email:
            return f"{name} <{self.email}>"
        return self.email or name
