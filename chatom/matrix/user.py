"""Matrix-specific User model.

This module provides the Matrix-specific User class.
Based on the matrix-python-sdk User class.
"""

from typing import Optional

from chatom.base import Field, User

__all__ = ("MatrixUser",)


class MatrixUser(User):
    """Matrix-specific user with additional Matrix fields.

    Based on the matrix-python-sdk User class, this provides Matrix-specific
    user attributes and functionality.

    Note: The base `name` field is used for the display name. Use the
    `display_name` property inherited from User to get the best display name.

    Attributes:
        user_id: The Matrix user ID (e.g., @user:server.org).
        homeserver: The user's homeserver.
        avatar_mxc: The MXC URI for the user's avatar.
        is_guest: Whether this is a guest account.
        deactivated: Whether the account is deactivated.
        currently_active: Whether the user is currently active.
        last_active_ago: Milliseconds since the user was last active.
        status_msg: User's status message.
        device_id: Current device ID for the user.
    """

    user_id: str = Field(
        default="",
        description="The Matrix user ID (e.g., @user:server.org).",
    )
    homeserver: str = Field(
        default="",
        description="The user's homeserver.",
    )
    avatar_mxc: str = Field(
        default="",
        description="The MXC URI for the user's avatar.",
    )
    is_guest: bool = Field(
        default=False,
        description="Whether this is a guest account.",
    )
    deactivated: bool = Field(
        default=False,
        description="Whether the account is deactivated.",
    )
    currently_active: bool = Field(
        default=False,
        description="Whether the user is currently active.",
    )
    last_active_ago: Optional[int] = Field(
        default=None,
        description="Milliseconds since the user was last active.",
    )
    status_msg: str = Field(
        default="",
        description="User's status message.",
    )
    device_id: str = Field(
        default="",
        description="Current device ID for the user.",
    )

    @property
    def localpart(self) -> str:
        """Get the local part of the user ID.

        Returns:
            str: The part before the colon, without @.
        """
        if self.user_id and self.user_id.startswith("@") and ":" in self.user_id:
            return self.user_id[1:].split(":")[0]
        return self.handle or ""

    @property
    def full_user_id(self) -> str:
        """Get or construct the full Matrix user ID.

        Returns:
            str: The full user ID in @user:server format.
        """
        if self.user_id:
            return self.user_id
        if self.handle and self.homeserver:
            return f"@{self.handle}:{self.homeserver}"
        return self.handle or self.id

    @property
    def server_name(self) -> str:
        """Get the server name from the user ID.

        Returns:
            str: The homeserver domain.
        """
        if self.user_id and ":" in self.user_id:
            return self.user_id.split(":", 1)[1]
        return self.homeserver

    @property
    def mxid(self) -> str:
        """Alias for full_user_id (Matrix ID).

        Returns:
            str: The full Matrix user ID.
        """
        return self.full_user_id

    def get_avatar_http_url(self, homeserver_url: str = "") -> str:
        """Convert MXC avatar URL to HTTP URL.

        Args:
            homeserver_url: The homeserver base URL (e.g., https://matrix.org).

        Returns:
            str: The HTTP URL for the avatar, or empty string if no avatar.
        """
        if not self.avatar_mxc:
            return self.avatar_url
        if not self.avatar_mxc.startswith("mxc://"):
            return self.avatar_mxc

        # Parse mxc://server/media_id
        mxc_path = self.avatar_mxc[6:]  # Remove "mxc://"
        if "/" not in mxc_path:
            return ""

        server, media_id = mxc_path.split("/", 1)
        base = homeserver_url.rstrip("/") if homeserver_url else f"https://{server}"
        return f"{base}/_matrix/media/r0/download/{server}/{media_id}"
