from chatom.base import mention_user

from .user import SymphonyUser

__all__ = ("mention_user",)


@mention_user.register
def mention_user(user: SymphonyUser) -> str:
    return f"@{user.name}"
