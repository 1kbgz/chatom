from chatom.base import mention_user

from .user import IRCUser

__all__ = ("mention_user",)


@mention_user.register
def mention_user(user: IRCUser) -> str:
    return f"{user.handle}" if user.handle else user.name
