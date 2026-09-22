"""LINE-specific presence model."""

from ..base import Presence

__all__ = ("LinePresence",)


class LinePresence(Presence):
    """LINE exposes no live presence data to Official Account bots."""
