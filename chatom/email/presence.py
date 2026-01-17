"""Email-specific Presence model.

This module provides the Email-specific Presence class.
Email doesn't have traditional presence, but can represent out-of-office status.
"""

from chatom.base import Field, Presence

__all__ = ("EmailPresence",)


class EmailPresence(Presence):
    """Email-specific presence.

    Email doesn't have real-time presence like chat platforms,
    but can represent out-of-office or auto-reply status.

    Attributes:
        out_of_office: Whether an out-of-office auto-reply is set.
        out_of_office_message: The out-of-office message.
        auto_reply_enabled: Whether auto-reply is enabled.
        auto_reply_subject: Subject line for auto-replies.
    """

    out_of_office: bool = Field(
        default=False,
        description="Whether an out-of-office auto-reply is set.",
    )
    out_of_office_message: str = Field(
        default="",
        description="The out-of-office message.",
    )
    auto_reply_enabled: bool = Field(
        default=False,
        description="Whether auto-reply is enabled.",
    )
    auto_reply_subject: str = Field(
        default="",
        description="Subject line for auto-replies.",
    )
