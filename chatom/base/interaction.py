"""Interaction model for chatom.

Represents a user interaction with a message component (button click,
select menu choice, modal submit, etc.). Platform-agnostic.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import Field, Identifiable
from .channel import Channel
from .user import User

__all__ = ("Interaction", "InteractionType")


class InteractionType(str, Enum):
    """The kind of component interaction."""

    BUTTON = "button"
    """A button click."""

    SELECT = "select"
    """A select menu selection."""

    MODAL_SUBMIT = "modal_submit"
    """A modal form submission."""

    OTHER = "other"
    """Any other interaction (future types)."""


class Interaction(Identifiable):
    """A user interaction with a message component.

    Emitted by backends when a user clicks a button, picks from a select
    menu, or submits a modal. Handlers can be registered against
    ``action_id`` via :class:`chatom.handlers.InteractionRegistry` or
    consumed as a stream via ``backend.stream_interactions()``.

    Attributes:
        id: Platform-specific interaction ID (e.g. Slack ``action_ts``
            or Discord interaction snowflake).
        type: The kind of interaction.
        action_id: The ``action_id`` declared on the source component.
            This is the primary dispatch key.
        values: Selected/submitted values. For buttons this is typically
            a single-element list with the button's ``value``; for
            selects it's the picked option values; for modals it's all
            submitted input values keyed by their ``action_id``.
        user: The user who triggered the interaction.
        channel: The channel the source message lives in.
        message_id: The ID of the message that contained the component.
        response_token: Opaque, short-lived token some platforms require
            to reply to the interaction (e.g. Discord interaction token,
            Slack ``response_url``).
        created_at: When the interaction happened.
        raw: The raw event payload from the backend.
        backend: Name of the backend that produced this interaction.
        metadata: Additional platform-specific data.
    """

    type: InteractionType = Field(
        default=InteractionType.OTHER,
        description="The kind of component interaction.",
    )
    action_id: str = Field(
        default="",
        description="Action identifier from the source component.",
    )
    values: List[str] = Field(
        default_factory=list,
        description="Selected/submitted values.",
    )
    user: Optional[User] = Field(
        default=None,
        description="The user who triggered the interaction.",
    )
    channel: Optional[Channel] = Field(
        default=None,
        description="The channel containing the source message.",
    )
    message_id: str = Field(
        default="",
        description="ID of the message that contained the component.",
    )
    response_token: str = Field(
        default="",
        description="Short-lived token for replying to this interaction.",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="When the interaction happened.",
    )
    raw: Optional[Any] = Field(
        default=None,
        description="Raw event payload from the backend.",
    )
    backend: str = Field(
        default="",
        description="Backend that produced this interaction.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional platform-specific data.",
    )

    @property
    def value(self) -> str:
        """Convenience: the first value, or empty string."""
        return self.values[0] if self.values else ""

    @property
    def channel_id(self) -> str:
        """Convenience: the channel ID, or empty string."""
        return self.channel.id if self.channel else ""

    @property
    def user_id(self) -> str:
        """Convenience: the user ID, or empty string."""
        return self.user.id if self.user else ""
