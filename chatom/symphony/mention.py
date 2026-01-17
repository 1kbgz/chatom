"""Symphony-specific mention utilities.

This module registers Symphony-specific mention formatting using MessageML.
"""

from chatom.base import mention_user

from .user import SymphonyUser

__all__ = ("mention_user", "mention_user_by_email", "mention_user_by_uid")


@mention_user.register
def _mention_symphony_user(user: SymphonyUser) -> str:
    """Generate a Symphony mention string for a user.

    Uses MessageML format with uid if available, otherwise email.

    Args:
        user: The Symphony user to mention.

    Returns:
        str: The Symphony MessageML mention tag.
    """
    if user.id:
        return f'<mention uid="{user.id}"/>'
    elif user.email:
        return f'<mention email="{user.email}"/>'
    return f"@{user.display_name or user.name}"


def mention_user_by_email(email: str) -> str:
    """Generate a Symphony mention by email address.

    Args:
        email: The email address to mention.

    Returns:
        str: The Symphony MessageML mention tag.
    """
    return f'<mention email="{email}"/>'


def mention_user_by_uid(uid: str) -> str:
    """Generate a Symphony mention by user ID.

    Args:
        uid: The user ID to mention.

    Returns:
        str: The Symphony MessageML mention tag.
    """
    return f'<mention uid="{uid}"/>'


def format_hashtag(tag: str) -> str:
    """Format a Symphony hashtag.

    Args:
        tag: The hashtag text (without #).

    Returns:
        str: The Symphony MessageML hash tag.
    """
    return f'<hash tag="{tag}"/>'


def format_cashtag(tag: str) -> str:
    """Format a Symphony cashtag (stock ticker).

    Args:
        tag: The cashtag text (without $).

    Returns:
        str: The Symphony MessageML cash tag.
    """
    return f'<cash tag="{tag}"/>'
