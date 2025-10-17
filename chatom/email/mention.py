from chatom.base import mention_user

from .user import EmailUser

__all__ = ("mention_user",)


@mention_user.register
def mention_user(user: EmailUser) -> str:
    return f"<a href='mailto:{user.email}'>{user.name}</a>" if user.email else user.name
