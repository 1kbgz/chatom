"""Authorization utilities for chatom.

This module provides a simple authorization framework for bot development.
It allows defining policies for what users can do in different channels.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .base import BaseModel, Field
from .channel import Channel
from .user import User

__all__ = (
    "AuthorizationPolicy",
    "SimpleAuthorizationPolicy",
    "Permission",
    "is_user_authorized",
    "AuthorizationResult",
)


class Permission(str, Enum):
    """Common permissions that can be checked."""

    # Message permissions
    SEND_MESSAGES = "send_messages"
    """Can send messages in a channel."""

    READ_MESSAGES = "read_messages"
    """Can read messages in a channel."""

    DELETE_MESSAGES = "delete_messages"
    """Can delete messages (own or others)."""

    EDIT_MESSAGES = "edit_messages"
    """Can edit messages."""

    # Command permissions
    EXECUTE_COMMANDS = "execute_commands"
    """Can execute bot commands."""

    ADMIN_COMMANDS = "admin_commands"
    """Can execute administrative commands."""

    # Channel permissions
    MANAGE_CHANNEL = "manage_channel"
    """Can modify channel settings."""

    INVITE_USERS = "invite_users"
    """Can invite users to channel."""

    # Bot-specific permissions
    USE_BOT = "use_bot"
    """Can interact with the bot at all."""

    CONFIGURE_BOT = "configure_bot"
    """Can configure bot settings."""


class AuthorizationResult(BaseModel):
    """Result of an authorization check.

    Attributes:
        authorized: Whether the action is authorized.
        reason: Human-readable reason for the result.
        required_permissions: Permissions that were required.
        missing_permissions: Permissions that the user lacks.
    """

    authorized: bool = Field(
        description="Whether the action is authorized.",
    )
    reason: str = Field(
        default="",
        description="Human-readable reason for the result.",
    )
    required_permissions: List[str] = Field(
        default_factory=list,
        description="Permissions that were required.",
    )
    missing_permissions: List[str] = Field(
        default_factory=list,
        description="Permissions that the user lacks.",
    )

    def __bool__(self) -> bool:
        """Allow using the result directly in boolean context."""
        return self.authorized


class AuthorizationPolicy(ABC):
    """Abstract base class for authorization policies.

    Implement this class to define custom authorization logic
    for your bot. The policy can check user permissions, roles,
    channel membership, or any other criteria.

    Example:
        >>> class MyPolicy(AuthorizationPolicy):
        ...     def __init__(self, admin_users: List[str]):
        ...         self.admin_users = set(admin_users)
        ...
        ...     async def is_authorized(
        ...         self, user: User, permission: str, channel: Optional[Channel] = None
        ...     ) -> AuthorizationResult:
        ...         if user.id in self.admin_users:
        ...             return AuthorizationResult(authorized=True)
        ...         return AuthorizationResult(
        ...             authorized=False,
        ...             reason="Not an admin user"
        ...         )
    """

    @abstractmethod
    async def is_authorized(
        self,
        user: User,
        permission: str,
        channel: Optional[Channel] = None,
        **context: Any,
    ) -> AuthorizationResult:
        """Check if a user is authorized for a permission.

        Args:
            user: The user to check.
            permission: The permission to check for (can be a Permission enum value
                        or a custom string).
            channel: Optional channel context for channel-specific permissions.
            **context: Additional context that may be needed for the check.

        Returns:
            AuthorizationResult indicating whether authorized and why.
        """
        raise NotImplementedError("Subclass must implement is_authorized()")

    async def check_permissions(
        self,
        user: User,
        permissions: List[str],
        channel: Optional[Channel] = None,
        require_all: bool = True,
        **context: Any,
    ) -> AuthorizationResult:
        """Check multiple permissions at once.

        Args:
            user: The user to check.
            permissions: List of permissions to check.
            channel: Optional channel context.
            require_all: If True, user must have all permissions.
                         If False, user needs any one permission.
            **context: Additional context.

        Returns:
            AuthorizationResult with missing permissions listed.
        """
        missing: List[str] = []
        granted: List[str] = []

        for perm in permissions:
            result = await self.is_authorized(user, perm, channel, **context)
            if result.authorized:
                granted.append(perm)
                if not require_all:
                    # Only need one, and we got it
                    return AuthorizationResult(
                        authorized=True,
                        required_permissions=permissions,
                    )
            else:
                missing.append(perm)
                if require_all:
                    # Need all but missing one - early exit
                    return AuthorizationResult(
                        authorized=False,
                        reason=f"Missing permission: {perm}",
                        required_permissions=permissions,
                        missing_permissions=[perm],
                    )

        if require_all:
            # Got here means we have all permissions
            return AuthorizationResult(
                authorized=True,
                required_permissions=permissions,
            )
        else:
            # Got here means we have none of the required permissions
            return AuthorizationResult(
                authorized=False,
                reason="Missing all required permissions",
                required_permissions=permissions,
                missing_permissions=missing,
            )


class SimpleAuthorizationPolicy(AuthorizationPolicy):
    """A simple authorization policy based on user/channel allow lists.

    This policy allows you to define:
    - Global admins who can do anything
    - Per-permission allow lists of user IDs
    - Per-channel permission overrides
    - Default behavior (allow or deny)

    Example:
        >>> policy = SimpleAuthorizationPolicy(
        ...     admin_users=["U123", "U456"],  # These users can do anything
        ...     default_authorized=False,  # Deny by default
        ... )
        >>> # Allow specific users to use commands
        >>> policy.allow_permission("execute_commands", ["U789", "U999"])
        >>>
        >>> # Check authorization
        >>> result = await policy.is_authorized(user, "execute_commands")
    """

    def __init__(
        self,
        admin_users: Optional[List[str]] = None,
        admin_channels: Optional[List[str]] = None,
        default_authorized: bool = False,
    ):
        """Initialize the policy.

        Args:
            admin_users: List of user IDs who have all permissions.
            admin_channels: List of channel IDs where default is to allow.
            default_authorized: Default authorization when no specific rule matches.
        """
        self._admin_users: Set[str] = set(admin_users or [])
        self._admin_channels: Set[str] = set(admin_channels or [])
        self._default_authorized = default_authorized

        # permission -> set of user IDs
        self._permission_users: Dict[str, Set[str]] = {}

        # channel_id -> permission -> set of user IDs (channel-specific overrides)
        self._channel_permissions: Dict[str, Dict[str, Set[str]]] = {}

        # permission -> set of channel IDs where it's blocked
        self._blocked_channels: Dict[str, Set[str]] = {}

    def add_admin(self, user_id: str) -> None:
        """Add a user as a global admin.

        Args:
            user_id: The user ID to add as admin.
        """
        self._admin_users.add(user_id)

    def remove_admin(self, user_id: str) -> None:
        """Remove a user from global admins.

        Args:
            user_id: The user ID to remove.
        """
        self._admin_users.discard(user_id)

    def allow_permission(
        self,
        permission: str,
        user_ids: List[str],
        channel_id: Optional[str] = None,
    ) -> None:
        """Allow specific users to have a permission.

        Args:
            permission: The permission to allow.
            user_ids: List of user IDs to allow.
            channel_id: If provided, only allow in this channel.
        """
        perm_str = permission.value if isinstance(permission, Permission) else permission

        if channel_id:
            if channel_id not in self._channel_permissions:
                self._channel_permissions[channel_id] = {}
            if perm_str not in self._channel_permissions[channel_id]:
                self._channel_permissions[channel_id][perm_str] = set()
            self._channel_permissions[channel_id][perm_str].update(user_ids)
        else:
            if perm_str not in self._permission_users:
                self._permission_users[perm_str] = set()
            self._permission_users[perm_str].update(user_ids)

    def block_permission_in_channel(
        self,
        permission: str,
        channel_ids: List[str],
    ) -> None:
        """Block a permission in specific channels.

        Args:
            permission: The permission to block.
            channel_ids: List of channel IDs where to block.
        """
        perm_str = permission.value if isinstance(permission, Permission) else permission
        if perm_str not in self._blocked_channels:
            self._blocked_channels[perm_str] = set()
        self._blocked_channels[perm_str].update(channel_ids)

    async def is_authorized(
        self,
        user: User,
        permission: str,
        channel: Optional[Channel] = None,
        **context: Any,
    ) -> AuthorizationResult:
        """Check if a user is authorized for a permission.

        Args:
            user: The user to check.
            permission: The permission to check for.
            channel: Optional channel context.
            **context: Additional context (ignored by this policy).

        Returns:
            AuthorizationResult indicating whether authorized.
        """
        perm_str = permission.value if isinstance(permission, Permission) else permission
        channel_id = channel.id if channel else None

        # Global admins can do anything
        if user.id in self._admin_users:
            return AuthorizationResult(
                authorized=True,
                reason="User is a global admin",
                required_permissions=[perm_str],
            )

        # Check if permission is blocked in this channel
        if channel_id and perm_str in self._blocked_channels:
            if channel_id in self._blocked_channels[perm_str]:
                return AuthorizationResult(
                    authorized=False,
                    reason=f"Permission '{perm_str}' is blocked in this channel",
                    required_permissions=[perm_str],
                    missing_permissions=[perm_str],
                )

        # Check channel-specific permissions first
        if channel_id and channel_id in self._channel_permissions:
            channel_perms = self._channel_permissions[channel_id]
            if perm_str in channel_perms:
                if user.id in channel_perms[perm_str]:
                    return AuthorizationResult(
                        authorized=True,
                        reason="User has channel-specific permission",
                        required_permissions=[perm_str],
                    )

        # Check global permission list
        if perm_str in self._permission_users:
            if user.id in self._permission_users[perm_str]:
                return AuthorizationResult(
                    authorized=True,
                    reason="User has global permission",
                    required_permissions=[perm_str],
                )

        # Check if channel is an admin channel (allows everything by default)
        if channel_id and channel_id in self._admin_channels:
            return AuthorizationResult(
                authorized=True,
                reason="Channel allows all actions by default",
                required_permissions=[perm_str],
            )

        # Fall back to default
        return AuthorizationResult(
            authorized=self._default_authorized,
            reason="No specific rule found, using default",
            required_permissions=[perm_str],
            missing_permissions=[] if self._default_authorized else [perm_str],
        )


async def is_user_authorized(
    user: User,
    permission: str,
    policy: AuthorizationPolicy,
    channel: Optional[Channel] = None,
    **context: Any,
) -> bool:
    """Convenience function to check user authorization.

    This is a simple wrapper that returns just a boolean.

    Args:
        user: The user to check.
        permission: The permission to check for.
        policy: The authorization policy to use.
        channel: Optional channel context.
        **context: Additional context for the policy.

    Returns:
        bool: True if authorized, False otherwise.

    Example:
        >>> policy = SimpleAuthorizationPolicy(admin_users=["U123"])
        >>> if await is_user_authorized(user, Permission.ADMIN_COMMANDS, policy):
        ...     await handle_admin_command(message)
    """
    result = await policy.is_authorized(user, permission, channel, **context)
    return result.authorized
