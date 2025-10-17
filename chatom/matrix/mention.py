from chatom.base import mention_user

from .user import MatrixUser

__all__ = ("mention_user",)


@mention_user.register
def mention_user(user: MatrixUser) -> str:
    return f"@{user.handle}:matrix.org" if user.handle else user.name
