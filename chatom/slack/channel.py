"""Slack-specific Channel model.

This module provides the Slack-specific Channel class.
"""

from typing import Optional

from chatom.base import Channel, ChannelType, Field

__all__ = ("SlackChannel",)


class SlackChannel(Channel):
    """Slack-specific channel with additional Slack fields.

    Attributes:
        is_channel: Whether this is a public channel.
        is_group: Whether this is a private channel.
        is_im: Whether this is a direct message.
        is_mpim: Whether this is a multi-party direct message.
        is_private: Whether this is a private channel.
        is_shared: Whether this channel is shared with other workspaces.
        is_ext_shared: Whether this channel is shared externally.
        is_org_shared: Whether this channel is shared org-wide.
        creator: User ID of the channel creator.
        purpose: Channel purpose text.
        num_members: Number of members in the channel.
        unread_count: Number of unread messages.
        last_read: Timestamp of last read message.
        latest: Timestamp of latest message.
    """

    is_channel: bool = Field(
        default=False,
        description="Whether this is a public channel.",
    )
    is_group: bool = Field(
        default=False,
        description="Whether this is a private channel.",
    )
    is_im: bool = Field(
        default=False,
        description="Whether this is a direct message.",
    )
    is_mpim: bool = Field(
        default=False,
        description="Whether this is a multi-party direct message.",
    )
    is_private: bool = Field(
        default=False,
        description="Whether this is a private channel.",
    )
    is_shared: bool = Field(
        default=False,
        description="Whether this channel is shared with other workspaces.",
    )
    is_ext_shared: bool = Field(
        default=False,
        description="Whether this channel is shared externally.",
    )
    is_org_shared: bool = Field(
        default=False,
        description="Whether this channel is shared org-wide.",
    )
    creator: str = Field(
        default="",
        description="User ID of the channel creator.",
    )
    purpose: str = Field(
        default="",
        description="Channel purpose text.",
    )
    num_members: Optional[int] = Field(
        default=None,
        description="Number of members in the channel.",
    )
    unread_count: int = Field(
        default=0,
        description="Number of unread messages.",
    )
    last_read: str = Field(
        default="",
        description="Timestamp of last read message.",
    )
    latest: str = Field(
        default="",
        description="Timestamp of latest message.",
    )

    @property
    def slack_channel_type(self) -> ChannelType:
        """Determine the channel type from Slack flags.

        Returns:
            ChannelType: The generic channel type.
        """
        if self.is_im:
            return ChannelType.DIRECT
        elif self.is_mpim:
            return ChannelType.GROUP
        elif self.is_private or self.is_group:
            return ChannelType.PRIVATE
        elif self.is_channel:
            return ChannelType.PUBLIC
        return ChannelType.UNKNOWN
