from .backend import BACKEND
from .user import User


def mention_user(user: User, backend: BACKEND) -> str:
    """Generate a mention string for a user based on the backend platform.

    Args:
        user (User): The user to mention.
        backend (BACKEND): The backend platform.

    Returns:
        str: The formatted mention string.
    """
    match backend:
        case "discord":
            return f"<@!{user.id}>"
        case "email":
            return f"<a href='mailto:{user.email}'>{user.name}</a>" if user.email else user.name
        case "irc":
            return f"{user.handle}" if user.handle else user.name
        case "matrix":
            return f"@{user.handle}:matrix.org" if user.handle else user.name
        case "mattermost":
            return f"@{user.handle}" if user.handle else user.name
        case "messenger":
            return f"@{user.name}"
        case "slack":
            return f"<@{user.id}>"
        case "teams":
            return f"<at>{user.name}</at>"
        case "telegram":
            return f"@{user.handle}" if user.handle else user.name
        case "symphony":
            return f"@{user.name}"
        case "whatsapp":
            return f"@{user.name}"
        case "zulip":
            return f"@**{user.name}**"
        case _:
            # Fallback to full name if no specific format is defined
            return user.name
