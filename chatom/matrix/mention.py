"""Matrix-specific mention utilities.

This module registers Matrix-specific mention formatting.
"""

from chatom.base import mention_user

from .user import MatrixUser

__all__ = ("mention_user", "mention_room")


@mention_user.register
def _mention_matrix_user(user: MatrixUser) -> str:
    """Generate a Matrix mention string for a user.

    Args:
        user: The Matrix user to mention.

    Returns:
        str: The Matrix user ID in @user:server format.
    """
    if user.user_id:
        return user.user_id
    if user.handle and user.homeserver:
        return f"@{user.handle}:{user.homeserver}"
    if user.handle:
        return f"@{user.handle}:matrix.org"
    return user.name


def mention_room(room_id: str) -> str:
    """Generate a Matrix room mention/link.

    Args:
        room_id: The room ID or alias.

    Returns:
        str: The room reference.
    """
    return room_id


def create_pill(user_id: str, display_name: str = "") -> str:
    """Create a Matrix 'pill' mention (HTML format).

    Pills are the rich mention format used in Matrix clients.

    Args:
        user_id: The full Matrix user ID.
        display_name: Optional display name for the pill.

    Returns:
        str: HTML anchor tag for the pill.
    """
    name = display_name or user_id
    return f'<a href="https://matrix.to/#/{user_id}">{name}</a>'
