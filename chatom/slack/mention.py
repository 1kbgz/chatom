from chatom.base import mention_user

from .user import SlackUser

__all__ = ("mention_user",)


@mention_user.register
def mention_user(user: SlackUser) -> str:
    return f"<@{user.id}>"
