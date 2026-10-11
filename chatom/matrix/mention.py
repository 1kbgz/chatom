"""Matrix mention formatting."""

from html import escape
from urllib.parse import quote

from chatom.base import mention_channel, mention_user

from .channel import MatrixChannel
from .user import MatrixUser

__all__ = ("mention_channel", "mention_user")


def _matrix_to(identifier: str) -> str:
    return f"https://matrix.to/#/{quote(identifier, safe=':@!#$')}"


@mention_user.register
def _mention_matrix_user(user: MatrixUser) -> str:
    """Render a Matrix user mention as a matrix.to HTML link."""
    label = user.mention_name or user.id
    return f'<a href="{_matrix_to(user.id)}">{escape(label)}</a>'


@mention_channel.register
def _mention_matrix_channel(channel: MatrixChannel) -> str:
    """Render a Matrix room mention as a matrix.to HTML link."""
    identifier = channel.canonical_alias or channel.id
    label = channel.name or identifier
    return f'<a href="{_matrix_to(identifier)}">{escape(label)}</a>'
