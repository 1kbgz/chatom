"""Matrix backend implementation for chatom.

This module provides the Matrix backend using matrix-python-sdk.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, ClassVar, List, Optional, Union

from pydantic import Field

from ..backend_registry import BackendBase
from ..base import (
    MATRIX_CAPABILITIES,
    BackendCapabilities,
    Channel,
    Message,
    Presence,
    PresenceStatus,
    User,
)
from ..format.variant import Format
from .channel import MatrixChannel
from .config import MatrixConfig
from .mention import mention_user as _mention_user
from .message import MatrixMessage
from .presence import MatrixPresence
from .user import MatrixUser

__all__ = ("MatrixBackend",)

# Try to import matrix_client
try:
    from matrix_client.api import MatrixHttpApi
    from matrix_client.client import MatrixClient
    from matrix_client.errors import MatrixRequestError

    HAS_MATRIX = True
except ImportError:
    HAS_MATRIX = False
    MatrixClient = None  # type: ignore
    MatrixHttpApi = None  # type: ignore
    MatrixRequestError = Exception  # type: ignore


def _matrix_status_to_presence(status: str) -> PresenceStatus:
    """Convert Matrix presence status to PresenceStatus."""
    status_map = {
        "online": PresenceStatus.ONLINE,
        "offline": PresenceStatus.OFFLINE,
        "unavailable": PresenceStatus.AWAY,
    }
    return status_map.get(status.lower(), PresenceStatus.UNKNOWN)


class MatrixBackend(BackendBase):
    """Matrix backend implementation using matrix-python-sdk.

    This provides the backend interface for Matrix using the matrix-python-sdk
    library. It supports all standard backend operations including messaging,
    presence, and reactions.

    Attributes:
        name: The backend identifier ('matrix').
        display_name: Human-readable name.
        format: Matrix uses HTML for formatted messages.
        capabilities: Matrix-specific capabilities.
        config: Matrix-specific configuration.

    Example:
        >>> from chatom.matrix import MatrixBackend, MatrixConfig
        >>> config = MatrixConfig(
        ...     homeserver_url="https://matrix.org",
        ...     access_token="your-token",
        ...     user_id="@mybot:matrix.org",
        ... )
        >>> backend = MatrixBackend(config=config)
        >>> await backend.connect()
        >>> user = await backend.fetch_user("@user:matrix.org")
    """

    name: ClassVar[str] = "matrix"
    display_name: ClassVar[str] = "Matrix"
    format: ClassVar[Format] = Format.HTML

    # Type classes for this backend (used by conversion module)
    user_class: ClassVar[type] = MatrixUser
    channel_class: ClassVar[type] = MatrixChannel
    presence_class: ClassVar[type] = MatrixPresence

    capabilities: Optional[BackendCapabilities] = MATRIX_CAPABILITIES
    config: MatrixConfig = Field(default_factory=MatrixConfig)

    # Matrix client instances
    _client: Any = None
    _api: Any = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    async def connect(self) -> None:
        """Connect to Matrix homeserver.

        This creates a Matrix client and authenticates using the access token.

        Raises:
            RuntimeError: If matrix-python-sdk is not installed or config is missing.
        """
        if not HAS_MATRIX:
            raise RuntimeError("matrix-python-sdk is not installed. Install with: pip install matrix-client")

        if not self.config.has_homeserver:
            raise RuntimeError("Matrix homeserver URL is required")

        if not self.config.has_token:
            raise RuntimeError("Matrix access token is required")

        # Create the client with access token (runs sync internally)
        def _create_client() -> MatrixClient:
            client = MatrixClient(
                self.config.homeserver_url,
                token=self.config.access_token_str,
                valid_cert_check=self.config.validate_cert,
                sync_filter_limit=self.config.sync_filter_limit,
            )
            return client

        self._client = await asyncio.to_thread(_create_client)
        self._api = self._client.api
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from Matrix."""
        if self._client is not None:
            # Stop listener thread if running
            def _disconnect() -> None:
                if hasattr(self._client, "stop_listener_thread"):
                    self._client.stop_listener_thread()
                if hasattr(self._client, "logout"):
                    try:
                        self._client.logout()
                    except Exception:
                        pass  # Ignore logout errors

            await asyncio.to_thread(_disconnect)
            self._client = None
            self._api = None
        self.connected = False

    async def fetch_user(
        self,
        identifier: Optional[Union[str, User]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[User]:
        """Fetch a user from Matrix.

        Accepts flexible inputs:
        - User ID as positional arg or id= (@user:server)
        - User object (returns as-is or refreshes)
        - name= to search by display name (cache only)
        - handle= treated same as id (Matrix user IDs are handles)

        Args:
            identifier: A User object or user ID string.
            id: Matrix user ID (@user:server).
            name: Display name to search for (cache only).
            email: Email (not directly supported by Matrix).
            handle: Same as id for Matrix.

        Returns:
            The user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, MatrixUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Handle is same as id for Matrix
        if handle and not id:
            id = handle

        # Check cache first
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached

        if self._api is None:
            return None

        # ID-based lookup
        if id:
            try:

                def _fetch_profile() -> dict:
                    return self._api.get_display_name(id)

                profile = await asyncio.to_thread(_fetch_profile)

                user = MatrixUser(
                    id=id,
                    name=profile.get("displayname", id),
                    handle=id,
                    user_id=id,
                )
                self.users.add(user)
                return user
            except Exception:
                pass

        # Name search - cache only
        if name:
            for cached_user in self.users._by_id.values():
                if isinstance(cached_user, MatrixUser):
                    if cached_user.name.lower() == name.lower():
                        return cached_user

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a room from Matrix.

        Accepts flexible inputs:
        - Room ID as positional arg or id= (!room:server)
        - Channel object (returns as-is or refreshes)
        - name= to search by room name (cache only)

        Args:
            identifier: A Channel object or room ID string.
            id: Matrix room ID (!room:server).
            name: Room name to search for (cache only).

        Returns:
            The channel/room if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, MatrixChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check cache first
        if id:
            cached = self.channels.get_by_id(id)
            if cached:
                return cached

        if self._api is None:
            return None

        # ID-based lookup
        if id:
            try:

                def _fetch_room_info() -> dict:
                    info = {"name": id, "topic": ""}
                    try:
                        name_resp = self._api.get_room_name(id)
                        info["name"] = name_resp.get("name", id)
                    except Exception:
                        pass
                    try:
                        topic_resp = self._api.get_room_topic(id)
                        info["topic"] = topic_resp.get("topic", "")
                    except Exception:
                        pass
                    return info

                info = await asyncio.to_thread(_fetch_room_info)

                channel = MatrixChannel(
                    id=id,
                    name=info.get("name", id),
                    topic=info.get("topic", ""),
                    room_id=id,
                )
                self.channels.add(channel)
                return channel
            except Exception:
                pass

        # Name search - cache only
        if name:
            for cached_channel in self.channels._by_id.values():
                if isinstance(cached_channel, MatrixChannel):
                    if cached_channel.name.lower() == name.lower():
                        return cached_channel

        return None

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Message]:
        """Fetch messages from a Matrix room.

        Args:
            channel_id: The room ID to fetch messages from.
            limit: Maximum number of messages.
            before: Pagination token for earlier messages.
            after: Pagination token for later messages (unused, Matrix paginates backwards).

        Returns:
            List of messages.
        """
        if self._api is None:
            raise RuntimeError("Not connected to Matrix")

        try:

            def _fetch_messages() -> dict:
                # Get room messages using pagination token
                direction = "b"  # backwards from most recent
                token = before if before else "end"

                # If we have a room in the client, use its events
                if self._client and channel_id in self._client.rooms:
                    room = self._client.rooms[channel_id]
                    # Return cached events from room
                    return {
                        "chunk": [
                            {
                                "event_id": getattr(e, "event_id", str(i)),
                                "content": {"body": getattr(e, "body", "")},
                                "origin_server_ts": getattr(e, "origin_server_ts", 0),
                                "sender": getattr(e, "sender", ""),
                            }
                            for i, e in enumerate(getattr(room, "events", []))
                        ][:limit]
                    }

                # Otherwise fetch from API
                return self._api.get_room_messages(channel_id, token, direction, limit=limit)

            response = await asyncio.to_thread(_fetch_messages)

            messages: List[Message] = []
            for event in response.get("chunk", []):
                content = event.get("content", {})
                if event.get("type") == "m.room.message" or "body" in content:
                    ts = event.get("origin_server_ts", 0)
                    timestamp = datetime.fromtimestamp(ts / 1000, tz=timezone.utc) if ts else datetime.now(timezone.utc)

                    message = MatrixMessage(
                        id=event.get("event_id", ""),
                        content=content.get("body", ""),
                        timestamp=timestamp,
                        user_id=event.get("sender", ""),
                        channel_id=channel_id,
                        event_id=event.get("event_id", ""),
                    )
                    messages.append(message)

            return messages
        except Exception as e:
            raise RuntimeError(f"Failed to fetch messages: {e}") from e

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a message to a Matrix room.

        Args:
            channel_id: The room ID to send to.
            content: The message content.
            **kwargs: Additional options:
                - msgtype: Message type (default: m.text).
                - formatted_body: HTML formatted body.
                - format: Message format (e.g., org.matrix.custom.html).

        Returns:
            The sent message.
        """
        if self._api is None:
            raise RuntimeError("Not connected to Matrix")

        try:
            msgtype = kwargs.get("msgtype", "m.text")

            def _send_message() -> dict:
                return self._api.send_message(channel_id, content, msgtype=msgtype)

            response = await asyncio.to_thread(_send_message)

            return MatrixMessage(
                id=response.get("event_id", ""),
                content=content,
                timestamp=datetime.now(timezone.utc),
                user_id=self.config.user_id,
                channel_id=channel_id,
                event_id=response.get("event_id", ""),
            )
        except Exception as e:
            raise RuntimeError(f"Failed to send message: {e}") from e

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit a Matrix message (send replacement event).

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
            content: The new content.
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        if self._api is None:
            raise RuntimeError("Not connected to Matrix")

        try:

            def _edit_message() -> dict:
                # Matrix edits are done via m.replace relation
                body = {
                    "msgtype": "m.text",
                    "body": f"* {content}",
                    "m.new_content": {
                        "msgtype": "m.text",
                        "body": content,
                    },
                    "m.relates_to": {
                        "rel_type": "m.replace",
                        "event_id": message_id,
                    },
                }
                return self._api.send_message_event(channel_id, "m.room.message", body)

            response = await asyncio.to_thread(_edit_message)

            return MatrixMessage(
                id=response.get("event_id", ""),
                content=content,
                timestamp=datetime.now(timezone.utc),
                user_id=self.config.user_id,
                channel_id=channel_id,
                event_id=response.get("event_id", ""),
                edited=True,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to edit message: {e}") from e

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Redact a Matrix message.

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
        """
        if self._api is None:
            raise RuntimeError("Not connected to Matrix")

        try:

            def _redact_message() -> None:
                self._api.redact_event(channel_id, message_id)

            await asyncio.to_thread(_redact_message)
        except Exception as e:
            raise RuntimeError(f"Failed to delete message: {e}") from e

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set user presence on Matrix.

        Args:
            status: Presence status ('online', 'offline', 'unavailable').
            status_text: Status message.
            **kwargs: Additional options.
        """
        if self._api is None:
            raise RuntimeError("Not connected to Matrix")

        try:

            def _set_presence() -> None:
                # Matrix presence is set via the sync endpoint's set_presence parameter
                # or via PUT /_matrix/client/r0/presence/{userId}/status
                # The matrix-python-sdk doesn't have a direct method, so we use the API
                presence = status.lower()
                if presence not in ("online", "offline", "unavailable"):
                    presence = "online"

                body: dict[str, Any] = {"presence": presence}
                if status_text:
                    body["status_msg"] = status_text

                # Use raw _send method
                self._api._send(
                    "PUT",
                    f"/presence/{self.config.user_id}/status",
                    body,
                )

            await asyncio.to_thread(_set_presence)
        except Exception as e:
            raise RuntimeError(f"Failed to set presence: {e}") from e

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get a user's presence on Matrix.

        Args:
            user_id: The user ID (@user:server).

        Returns:
            The user's presence.
        """
        if self._api is None:
            return None

        try:

            def _get_presence() -> dict:
                return self._api._send("GET", f"/presence/{user_id}/status")

            response = await asyncio.to_thread(_get_presence)

            return MatrixPresence(
                user_id=user_id,
                status=_matrix_status_to_presence(response.get("presence", "offline")),
                status_text=response.get("status_msg", ""),
                last_active_ago=response.get("last_active_ago"),
            )
        except Exception:
            return None

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message.

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
            emoji: The emoji (unicode).
        """
        if self._api is None:
            raise RuntimeError("Not connected to Matrix")

        try:

            def _add_reaction() -> None:
                # Matrix reactions are m.reaction events with m.annotation relation
                body = {
                    "m.relates_to": {
                        "rel_type": "m.annotation",
                        "event_id": message_id,
                        "key": emoji,
                    }
                }
                self._api.send_message_event(channel_id, "m.reaction", body)

            await asyncio.to_thread(_add_reaction)
        except Exception as e:
            raise RuntimeError(f"Failed to add reaction: {e}") from e

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction from a message.

        Note: Matrix doesn't have a direct "remove reaction" - you need to
        redact the reaction event. This requires knowing the reaction event ID.

        Args:
            channel_id: The room containing the message.
            message_id: The event ID.
            emoji: The emoji to remove.
        """
        # Matrix requires knowing the reaction event ID to redact it
        # This would need to search for the reaction event first
        raise NotImplementedError(
            "Removing reactions in Matrix requires finding the reaction event ID first. This is not implemented in the current version."
        )

    def mention_user(self, user: User) -> str:
        """Format a user mention for Matrix.

        Args:
            user: The user to mention.

        Returns:
            Matrix user ID format (@user:server).
        """
        if isinstance(user, MatrixUser):
            return _mention_user(user)
        # For base User, just return the ID (assuming it's a valid MXID)
        return f"@{user.id}" if not user.id.startswith("@") else user.id

    def mention_channel(self, channel: Channel) -> str:
        """Format a room mention for Matrix.

        Args:
            channel: The channel/room to mention.

        Returns:
            Matrix room alias or ID.
        """
        if isinstance(channel, MatrixChannel):
            return channel.room_alias or channel.room_id or channel.id
        return channel.name or channel.id
