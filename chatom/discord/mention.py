from chatom.base import mention_user

from .user import DiscordUser

__all__ = ("mention_user",)


@mention_user.register
def mention_user(user: DiscordUser) -> str:
    return f"<@!{user.id}>"
