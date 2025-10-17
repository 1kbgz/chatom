from singledispatch import singledispatch

from .user import User

__all__ = ("mention_user",)


@singledispatch
def mention_user(user: User) -> str:
    """Generate a mention string for a user based on the backend platform.

    Args:
        user (User): The user to mention.

    Returns:
        str: The formatted mention string.
    """
    return user.name  # Default to using the user's name if no specific implementation exists
