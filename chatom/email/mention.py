"""Email-specific mention utilities.

This module registers Email-specific mention formatting.
"""

from chatom.base import mention_user

from .user import EmailUser

__all__ = ("mention_user",)


@mention_user.register
def _mention_email_user(user: EmailUser) -> str:
    """Generate an email mention (mailto link) for a user.

    Args:
        user: The email user to mention.

    Returns:
        str: HTML mailto link or just the name if no email.
    """
    if user.email:
        name = user.full_name or user.email
        return f"<a href='mailto:{user.email}'>{name}</a>"
    return user.full_name or user.name
