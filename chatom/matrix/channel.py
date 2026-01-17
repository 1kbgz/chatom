"""Matrix-specific Channel (Room) model.

This module provides the Matrix-specific Channel class, representing a Matrix room.
Based on the matrix-python-sdk Room class.
"""

from enum import Enum
from typing import Dict, List

from chatom.base import Channel, ChannelType, Field

__all__ = (
    "MatrixChannel",
    "MatrixRoom",
    "MatrixRoomType",
    "MatrixJoinRule",
    "MatrixGuestAccess",
    "MatrixRoomVisibility",
)


class MatrixRoomType(str, Enum):
    """Matrix room types."""

    SPACE = "m.space"
    """A Matrix space (container for other rooms)."""

    DEFAULT = ""
    """Default room type (regular chat room)."""


class MatrixJoinRule(str, Enum):
    """How users can join a Matrix room."""

    PUBLIC = "public"
    """Anyone can join without an invite."""

    INVITE = "invite"
    """Users must be invited to join."""

    KNOCK = "knock"
    """Users can request to join (knock)."""

    RESTRICTED = "restricted"
    """Join is restricted based on other conditions."""

    PRIVATE = "private"
    """Alias for invite (deprecated)."""


class MatrixGuestAccess(str, Enum):
    """Guest access settings for a Matrix room."""

    CAN_JOIN = "can_join"
    """Guests can join the room."""

    FORBIDDEN = "forbidden"
    """Guests cannot join the room."""


class MatrixRoomVisibility(str, Enum):
    """Room visibility in the room directory."""

    PUBLIC = "public"
    """Room is listed in the public room directory."""

    PRIVATE = "private"
    """Room is not listed in the public room directory."""


class MatrixChannel(Channel):
    """Matrix-specific channel (room) with additional Matrix fields.

    This class represents a Matrix room with all its associated metadata.
    Based on the matrix-python-sdk Room class.

    Attributes:
        room_id: The Matrix room ID (e.g., !abc123:matrix.org).
        canonical_alias: The canonical alias for the room (e.g., #room:server).
        aliases: List of room aliases.
        room_type: The type of room (space, default).
        join_rule: How users can join the room.
        guest_access: Whether guests can join.
        visibility: Room visibility in the directory.
        encrypted: Whether the room has encryption enabled.
        federated: Whether the room is federated.
        history_visibility: Who can see room history.
        creator: User ID of the room creator.
        version: Room version.
        predecessor_room_id: ID of the room this replaced.
        power_levels: Power level settings for the room.
        members: Dict of member user IDs to display names.
        member_count: Number of members in the room.
        prev_batch: Token for pagination of messages.
        unread_count: Number of unread messages.
        highlight_count: Number of highlighted/mentioned messages.
        direct: Whether this is a direct message room.
        avatar_mxc: MXC URI for the room avatar.
    """

    room_id: str = Field(
        default="",
        description="The Matrix room ID (e.g., !abc123:matrix.org).",
    )
    canonical_alias: str = Field(
        default="",
        description="The canonical alias for the room (e.g., #room:server).",
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="List of room aliases.",
    )
    room_type: MatrixRoomType = Field(
        default=MatrixRoomType.DEFAULT,
        description="The type of room.",
    )
    join_rule: MatrixJoinRule = Field(
        default=MatrixJoinRule.INVITE,
        description="How users can join the room.",
    )
    guest_access: MatrixGuestAccess = Field(
        default=MatrixGuestAccess.FORBIDDEN,
        description="Whether guests can join.",
    )
    visibility: MatrixRoomVisibility = Field(
        default=MatrixRoomVisibility.PRIVATE,
        description="Room visibility in the directory.",
    )
    encrypted: bool = Field(
        default=False,
        description="Whether the room has encryption enabled.",
    )
    federated: bool = Field(
        default=True,
        description="Whether the room is federated across servers.",
    )
    history_visibility: str = Field(
        default="shared",
        description="Who can see room history (shared, invited, joined, world_readable).",
    )
    creator: str = Field(
        default="",
        description="User ID of the room creator.",
    )
    version: str = Field(
        default="",
        description="Room version.",
    )
    predecessor_room_id: str = Field(
        default="",
        description="ID of the room this replaced (for room upgrades).",
    )
    power_levels: Dict = Field(
        default_factory=dict,
        description="Power level settings for the room.",
    )
    members: Dict[str, str] = Field(
        default_factory=dict,
        description="Dict of member user IDs to display names.",
    )
    prev_batch: str = Field(
        default="",
        description="Token for pagination of messages.",
    )
    unread_count: int = Field(
        default=0,
        description="Number of unread messages.",
    )
    highlight_count: int = Field(
        default=0,
        description="Number of highlighted/mentioned messages.",
    )
    direct: bool = Field(
        default=False,
        description="Whether this is a direct message room.",
    )
    avatar_mxc: str = Field(
        default="",
        description="MXC URI for the room avatar.",
    )

    @property
    def display_name(self) -> str:
        """Calculate the display name for the room.

        Priority: name > canonical_alias > first alias > room_id

        Returns:
            str: The best available display name.
        """
        if self.name:
            return self.name
        if self.canonical_alias:
            return self.canonical_alias
        if self.aliases:
            return self.aliases[0]
        return self.room_id or self.id

    @property
    def generic_channel_type(self) -> ChannelType:
        """Convert Matrix room type to generic channel type.

        Returns:
            ChannelType: The generic channel type.
        """
        if self.direct:
            return ChannelType.DIRECT
        if self.room_type == MatrixRoomType.SPACE:
            return ChannelType.FORUM  # Spaces are like forum categories
        if self.join_rule == MatrixJoinRule.PUBLIC:
            return ChannelType.PUBLIC
        return ChannelType.PRIVATE

    @property
    def is_public(self) -> bool:
        """Check if the room is publicly joinable.

        Returns:
            bool: True if anyone can join.
        """
        return self.join_rule == MatrixJoinRule.PUBLIC

    @property
    def is_invite_only(self) -> bool:
        """Check if the room requires an invite to join.

        Returns:
            bool: True if invite is required.
        """
        return self.join_rule == MatrixJoinRule.INVITE

    @property
    def is_space(self) -> bool:
        """Check if this is a Matrix space.

        Returns:
            bool: True if this is a space.
        """
        return self.room_type == MatrixRoomType.SPACE

    @property
    def is_encrypted(self) -> bool:
        """Check if the room has encryption enabled.

        Returns:
            bool: True if encrypted.
        """
        return self.encrypted

    @property
    def homeserver(self) -> str:
        """Extract the homeserver from the room ID.

        Returns:
            str: The homeserver domain.
        """
        if self.room_id and ":" in self.room_id:
            return self.room_id.split(":", 1)[1]
        return ""


# Alias for semantic clarity
MatrixRoom = MatrixChannel
