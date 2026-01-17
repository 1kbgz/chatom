"""Slack backend implementation for chatom."""

import asyncio
from datetime import datetime
from typing import Any, AsyncIterator, ClassVar, List, Optional, Union

from pydantic import Field

from ..backend_registry import BackendBase
from ..base import (
    SLACK_CAPABILITIES,
    BackendCapabilities,
    Channel,
    PresenceStatus,
    User,
)
from ..format.variant import Format
from .channel import SlackChannel
from .config import SlackConfig
from .mention import mention_channel as _mention_channel, mention_user as _mention_user
from .message import SlackMessage
from .presence import SlackPresence, SlackPresenceStatus
from .user import SlackUser

__all__ = ("SlackBackend",)


class SlackBackend(BackendBase):
    """Slack backend implementation.

    This provides the backend interface for Slack using the
    slack_sdk library for API calls.

    Attributes:
        name: The backend identifier ('slack').
        display_name: Human-readable name.
        format: Slack uses its own mrkdwn format.
        capabilities: Slack-specific capabilities.
        config: Slack-specific configuration.

    Example:
        >>> config = SlackConfig(bot_token="xoxb-your-token")
        >>> backend = SlackBackend(config=config)
        >>> await backend.connect()
        >>> messages = await backend.fetch_messages("C123456")
    """

    name: ClassVar[str] = "slack"
    display_name: ClassVar[str] = "Slack"
    format: ClassVar[Format] = Format.SLACK_MARKDOWN

    # Type classes for this backend (used by conversion module)
    user_class: ClassVar[type] = SlackUser
    channel_class: ClassVar[type] = SlackChannel
    presence_class: ClassVar[type] = SlackPresence

    capabilities: Optional[BackendCapabilities] = SLACK_CAPABILITIES
    config: SlackConfig = Field(default_factory=SlackConfig)

    # Internal client (set during connect)
    _client: Any = None
    _async_client: Any = None

    class Config:
        arbitrary_types_allowed = True

    async def connect(self) -> None:
        """Connect to Slack using the configured credentials.

        Initializes the Slack WebClient with the bot token from config.

        Raises:
            ImportError: If slack_sdk is not installed.
            SlackApiError: If authentication fails.
        """
        try:
            from slack_sdk.web.async_client import AsyncWebClient
        except ImportError:
            raise ImportError("slack_sdk is required for Slack backend. Install with: pip install slack_sdk")

        token = self.config.bot_token_str
        if not token:
            raise ValueError("bot_token is required in SlackConfig")

        self._async_client = AsyncWebClient(token=token)

        # Verify the connection by calling auth.test
        response = await self._async_client.auth_test()
        if response.get("ok"):
            self.connected = True
        else:
            raise ConnectionError(f"Slack auth failed: {response.get('error')}")

    async def disconnect(self) -> None:
        """Disconnect from Slack."""
        self._async_client = None
        self._client = None
        self.connected = False

    def _ensure_connected(self) -> None:
        """Ensure the client is connected."""
        if not self.connected or self._async_client is None:
            raise ConnectionError("Not connected to Slack. Call connect() first.")

    async def fetch_user(
        self,
        identifier: Optional[Union[str, "SlackUser"]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        handle: Optional[str] = None,
    ) -> Optional[SlackUser]:
        """Fetch a user from Slack.

        Accepts flexible inputs:
        - User ID as positional arg or id=
        - SlackUser object (returns as-is or refreshes)
        - name= to search by display name or real name
        - email= to search by email address
        - handle= to search by username

        Args:
            identifier: A SlackUser object or user ID string.
            id: User ID.
            name: Display name or real name to search for.
            email: Email address to search for.
            handle: Username to search for.

        Returns:
            The user if found, None otherwise.
        """
        self._ensure_connected()

        # Handle User object input
        if isinstance(identifier, SlackUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            # It's a User-like object
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = identifier

        # Check cache first for ID lookup
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached if isinstance(cached, SlackUser) else None

        # If we have an ID, fetch directly
        if id:
            return await self._fetch_user_by_id(id)

        # Search by email using users.lookupByEmail
        if email:
            try:
                response = await self._async_client.users_lookupByEmail(email=email)
                if response.get("ok"):
                    user_data = response.get("user", {})
                    return await self._fetch_user_by_id(user_data.get("id"))
            except Exception:
                pass

        # Search by name or handle requires listing users
        if name or handle:
            try:
                cursor = None
                while True:
                    response = await self._async_client.users_list(limit=200, cursor=cursor)
                    if not response.get("ok"):
                        break

                    for user_data in response.get("members", []):
                        user_name = user_data.get("name", "")
                        profile = user_data.get("profile", {})
                        display_name = profile.get("display_name", "")
                        real_name = profile.get("real_name", "")

                        # Match handle (username)
                        if handle and user_name.lower() == handle.lower():
                            return await self._fetch_user_by_id(user_data.get("id"))

                        # Match name (display_name or real_name)
                        if name:
                            if display_name.lower() == name.lower() or real_name.lower() == name.lower() or user_name.lower() == name.lower():
                                return await self._fetch_user_by_id(user_data.get("id"))

                    # Pagination
                    cursor = response.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
            except Exception:
                pass

        return None

    async def _fetch_user_by_id(self, user_id: str) -> Optional[SlackUser]:
        """Fetch a user by ID from the Slack API."""
        try:
            response = await self._async_client.users_info(user=user_id)
            if response.get("ok"):
                user_data = response.get("user", {})
                profile = user_data.get("profile", {})
                user = SlackUser(
                    id=user_data.get("id", user_id),
                    name=user_data.get("name", ""),
                    handle=user_data.get("name", ""),
                    email=profile.get("email", ""),
                    real_name=profile.get("real_name", ""),
                    display_name=profile.get("display_name", ""),
                    team_id=user_data.get("team_id", ""),
                    is_admin=user_data.get("is_admin", False),
                    is_owner=user_data.get("is_owner", False),
                    is_bot=user_data.get("is_bot", False),
                    tz=user_data.get("tz", ""),
                    tz_offset=user_data.get("tz_offset", 0),
                    status_text=profile.get("status_text", ""),
                    status_emoji=profile.get("status_emoji", ""),
                )
                self.users.add(user)
                return user
        except Exception:
            pass
        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, "SlackChannel"]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[SlackChannel]:
        """Fetch a channel from Slack.

        Accepts flexible inputs:
        - Channel ID as positional arg or id=
        - SlackChannel object (returns as-is or refreshes)
        - name= to search by channel name

        Args:
            identifier: A SlackChannel object or channel ID string.
            id: Channel ID.
            name: Channel name to search for.

        Returns:
            The channel if found, None otherwise.
        """
        self._ensure_connected()

        # Handle Channel object input
        if isinstance(identifier, SlackChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            # It's a Channel-like object
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = identifier

        # Check cache first for ID lookup
        if id:
            cached = self.channels.get_by_id(id)
            if cached:
                return cached if isinstance(cached, SlackChannel) else None

        # If we have an ID, fetch directly
        if id:
            return await self._fetch_channel_by_id(id)

        # Search by name requires listing conversations
        if name:
            try:
                cursor = None
                while True:
                    response = await self._async_client.conversations_list(
                        types="public_channel,private_channel",
                        limit=200,
                        cursor=cursor,
                    )
                    if not response.get("ok"):
                        break

                    for channel_data in response.get("channels", []):
                        if channel_data.get("name", "").lower() == name.lower():
                            return await self._fetch_channel_by_id(channel_data.get("id"))

                    # Pagination
                    cursor = response.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
            except Exception:
                pass

        return None

    async def _fetch_channel_by_id(self, channel_id: str) -> Optional[SlackChannel]:
        """Fetch a channel by ID from the Slack API."""
        try:
            response = await self._async_client.conversations_info(channel=channel_id)
            if response.get("ok"):
                channel_data = response.get("channel", {})
                channel = SlackChannel(
                    id=channel_data.get("id", channel_id),
                    name=channel_data.get("name", ""),
                    topic=channel_data.get("topic", {}).get("value", ""),
                    is_channel=channel_data.get("is_channel", False),
                    is_group=channel_data.get("is_group", False),
                    is_im=channel_data.get("is_im", False),
                    is_mpim=channel_data.get("is_mpim", False),
                    is_private=channel_data.get("is_private", False),
                    is_shared=channel_data.get("is_shared", False),
                    is_ext_shared=channel_data.get("is_ext_shared", False),
                    is_org_shared=channel_data.get("is_org_shared", False),
                    creator=channel_data.get("creator", ""),
                    purpose=channel_data.get("purpose", {}).get("value", ""),
                    num_members=channel_data.get("num_members"),
                )
                self.channels.add(channel)
                return channel
        except Exception:
            pass
        return None

    def _parse_slack_message(self, msg_data: dict, channel_id: str) -> SlackMessage:
        """Parse a Slack API message into a SlackMessage object."""
        ts = msg_data.get("ts", "")
        # Convert Slack timestamp to datetime
        try:
            timestamp = float(ts.split(".")[0]) if ts else 0
            created_at = datetime.fromtimestamp(timestamp) if timestamp else None
        except (ValueError, TypeError):
            created_at = None

        # Get user ID - this is a string, not a User object
        user_id = msg_data.get("user")

        return SlackMessage(
            id=ts,
            ts=ts,
            content=msg_data.get("text", ""),
            channel=channel_id,
            sender_id=user_id,  # Use sender_id for the string user ID
            author_id=user_id or "",  # Set author_id as well
            team=msg_data.get("team"),
            created_at=created_at,
            bot_id=msg_data.get("bot_id"),
            blocks=msg_data.get("blocks", []),
            thread_ts=msg_data.get("thread_ts"),
            reply_count=msg_data.get("reply_count", 0),
        )

    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[SlackMessage]:
        """Fetch messages from a Slack channel.

        Uses the conversations.history API.

        Args:
            channel_id: The channel to fetch messages from.
            limit: Maximum number of messages (1-1000).
            before: Fetch messages before this timestamp (latest).
            after: Fetch messages after this timestamp (oldest).

        Returns:
            List of messages, newest first.
        """
        self._ensure_connected()

        kwargs: dict = {"channel": channel_id, "limit": min(limit, 1000)}
        if before:
            kwargs["latest"] = before
        if after:
            kwargs["oldest"] = after

        response = await self._async_client.conversations_history(**kwargs)

        if not response.get("ok"):
            raise RuntimeError(f"Failed to fetch messages: {response.get('error')}")

        messages = []
        for msg_data in response.get("messages", []):
            messages.append(self._parse_slack_message(msg_data, channel_id))

        # Slack returns newest first, reverse for oldest first
        return list(reversed(messages))

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> SlackMessage:
        """Send a message to a Slack channel.

        Uses the chat.postMessage API.

        Args:
            channel_id: The channel to send to.
            content: The message content.
            **kwargs: Additional options. Accepts both:
                      - thread_id (chatom standard) - translated to thread_ts
                      - thread_ts (Slack native)
                      Plus: blocks, attachments, unfurl_links, etc.

        Returns:
            The sent message.
        """
        self._ensure_connected()

        # Translate thread_id to thread_ts for Slack API
        if "thread_id" in kwargs and "thread_ts" not in kwargs:
            kwargs["thread_ts"] = kwargs.pop("thread_id")

        response = await self._async_client.chat_postMessage(
            channel=channel_id,
            text=content,
            **kwargs,
        )

        if not response.get("ok"):
            raise RuntimeError(f"Failed to send message: {response.get('error')}")

        msg_data = response.get("message", {})
        msg_data["ts"] = response.get("ts", msg_data.get("ts", ""))
        return self._parse_slack_message(msg_data, channel_id)

    async def edit_message(
        self,
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> SlackMessage:
        """Edit a Slack message.

        Uses the chat.update API.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp (ts).
            content: The new content.
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        self._ensure_connected()

        response = await self._async_client.chat_update(
            channel=channel_id,
            ts=message_id,
            text=content,
            **kwargs,
        )

        if not response.get("ok"):
            raise RuntimeError(f"Failed to edit message: {response.get('error')}")

        msg_data = response.get("message", {})
        msg_data["ts"] = response.get("ts", msg_data.get("ts", message_id))
        return self._parse_slack_message(msg_data, channel_id)

    async def delete_message(
        self,
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete a Slack message.

        Uses the chat.delete API.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp (ts).
        """
        self._ensure_connected()

        response = await self._async_client.chat_delete(
            channel=channel_id,
            ts=message_id,
        )

        if not response.get("ok"):
            raise RuntimeError(f"Failed to delete message: {response.get('error')}")

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set user presence on Slack.

        Uses the users.setPresence API for presence and
        users.profile.set for status text.

        Args:
            status: Presence status ('auto' or 'away').
            status_text: Status text to display.
            **kwargs: Additional options (status_emoji,
                      status_expiration, etc.).
        """
        self._ensure_connected()

        # Set presence (auto or away)
        response = await self._async_client.users_setPresence(presence=status)
        if not response.get("ok"):
            raise RuntimeError(f"Failed to set presence: {response.get('error')}")

        # Set status text if provided
        if status_text is not None:
            profile = {"status_text": status_text}
            if "status_emoji" in kwargs:
                profile["status_emoji"] = kwargs["status_emoji"]
            if "status_expiration" in kwargs:
                profile["status_expiration"] = kwargs["status_expiration"]

            response = await self._async_client.users_profile_set(profile=profile)
            if not response.get("ok"):
                raise RuntimeError(f"Failed to set status: {response.get('error')}")

    async def get_presence(self, user_id: str) -> Optional[SlackPresence]:
        """Get a user's presence on Slack.

        Uses the users.getPresence API.

        Args:
            user_id: The user ID.

        Returns:
            The user's presence.
        """
        self._ensure_connected()

        response = await self._async_client.users_getPresence(user=user_id)

        if not response.get("ok"):
            return None

        presence_str = response.get("presence", "away")
        slack_status = SlackPresenceStatus.ACTIVE if presence_str == "active" else SlackPresenceStatus.AWAY

        return SlackPresence(
            status=(PresenceStatus.ONLINE if slack_status == SlackPresenceStatus.ACTIVE else PresenceStatus.IDLE),
            slack_presence=slack_status,
            auto_away=response.get("auto_away", False),
            manual_away=response.get("manual_away", False),
            connection_count=response.get("connection_count", 0),
            last_activity=response.get("last_activity"),
        )

    async def add_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message.

        Uses the reactions.add API.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp (ts).
            emoji: The emoji name (without colons).
        """
        self._ensure_connected()

        # Remove colons if present
        emoji = emoji.strip(":")

        response = await self._async_client.reactions_add(
            channel=channel_id,
            timestamp=message_id,
            name=emoji,
        )

        if not response.get("ok"):
            error = response.get("error")
            # Ignore already_reacted error
            if error != "already_reacted":
                raise RuntimeError(f"Failed to add reaction: {error}")

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction from a message.

        Uses the reactions.remove API.

        Args:
            channel_id: The channel containing the message.
            message_id: The message timestamp (ts).
            emoji: The emoji name to remove.
        """
        self._ensure_connected()

        # Remove colons if present
        emoji = emoji.strip(":")

        response = await self._async_client.reactions_remove(
            channel=channel_id,
            timestamp=message_id,
            name=emoji,
        )

        if not response.get("ok"):
            error = response.get("error")
            # Ignore no_reaction error
            if error != "no_reaction":
                raise RuntimeError(f"Failed to remove reaction: {error}")

    def mention_user(self, user: User) -> str:
        """Format a user mention for Slack.

        Args:
            user: The user to mention.

        Returns:
            Slack user mention format (<@user_id>).
        """
        if isinstance(user, SlackUser):
            return _mention_user(user)
        return f"<@{user.id}>"

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for Slack.

        Args:
            channel: The channel to mention.

        Returns:
            Slack channel mention format (<#channel_id>).
        """
        if isinstance(channel, SlackChannel):
            return _mention_channel(channel)
        return f"<#{channel.id}>"

    async def create_dm(self, user_ids: List[str]) -> Optional[str]:
        """Create a DM/IM channel with the specified users.

        Uses conversations.open API to create or retrieve a DM channel.
        For a single user, creates a 1:1 DM. For multiple users, creates
        a group DM (multi-party DM).

        Args:
            user_ids: List of user IDs to include in the DM.
                      Can be a single user ID or a list.

        Returns:
            The DM channel ID, or None if creation failed.
        """
        self._ensure_connected()

        # Handle both single user_id string and list of user_ids
        if isinstance(user_ids, str):
            user_ids = [user_ids]

        if len(user_ids) == 1:
            # Single user DM
            response = await self._async_client.conversations_open(
                users=user_ids[0],
            )
        else:
            # Multi-party DM (group DM)
            response = await self._async_client.conversations_open(
                users=",".join(user_ids),
            )

        if response.get("ok"):
            channel = response.get("channel", {})
            return channel.get("id")
        else:
            error = response.get("error", "Unknown error")
            raise RuntimeError(f"Failed to create DM: {error}")

    async def create_channel(
        self,
        name: str,
        description: str = "",
        public: bool = True,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a new Slack channel.

        Uses conversations.create API to create a public or private channel.

        Args:
            name: The channel name (will be lowercased and spaces replaced).
            description: Optional channel description/purpose.
            public: Whether the channel is public (default True).
                   Private channels are created with is_private=True.
            **kwargs: Additional options:
                - team_id: Workspace ID for Enterprise Grid.

        Returns:
            The channel ID of the created channel, or None if failed.
        """
        self._ensure_connected()

        # Normalize channel name (Slack requires lowercase, no spaces)
        name = name.lower().replace(" ", "-")

        response = await self._async_client.conversations_create(
            name=name,
            is_private=not public,
            **{k: v for k, v in kwargs.items() if k in ["team_id"]},
        )

        if response.get("ok"):
            channel = response.get("channel", {})
            channel_id = channel.get("id")

            # Set the description/purpose if provided
            if description and channel_id:
                await self._async_client.conversations_setPurpose(
                    channel=channel_id,
                    purpose=description,
                )

            return channel_id
        else:
            error = response.get("error", "Unknown error")
            raise RuntimeError(f"Failed to create channel: {error}")

    async def get_bot_info(self) -> Optional[User]:
        """Get information about the connected bot user.

        Returns:
            The bot's User object.
        """
        self._ensure_connected()

        try:
            response = await self._async_client.auth_test()
            if response.get("ok"):
                user_id = response.get("user_id")
                user_name = response.get("user", "bot")

                # Try to fetch full user info
                user = await self.fetch_user(user_id)
                if user:
                    return user

                # Fall back to basic info
                return SlackUser(
                    id=user_id,
                    name=user_name,
                    handle=user_name,
                )
        except Exception:
            pass

        return None

    async def stream_messages(
        self,
        channel_id: Optional[str] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[SlackMessage]:
        """Stream incoming messages in real-time using Socket Mode.

        This requires an app token (xapp-...) to be configured.

        Args:
            channel_id: Optional channel ID to filter messages.
            skip_own: If True (default), skip messages sent by the bot itself.
            skip_history: If True (default), skip messages that existed before
                         the stream started. Only yields new messages.

        Yields:
            Message: Each message as it arrives.
        """
        self._ensure_connected()

        if not self.config.app_token:
            raise RuntimeError("Socket Mode requires an app token (xapp-...). Set app_token in SlackConfig to enable message streaming.")

        try:
            from slack_sdk.socket_mode.aiohttp import SocketModeClient
            from slack_sdk.socket_mode.request import SocketModeRequest
            from slack_sdk.socket_mode.response import SocketModeResponse
        except ImportError as e:
            raise RuntimeError(f"slack_sdk socket_mode required for streaming: {e}. Install with: pip install slack_sdk[socket_mode]") from e

        # Get bot info for filtering
        bot_info = await self.get_bot_info()
        bot_user_id = bot_info.id if bot_info else None

        # Track when the stream started for skip_history
        stream_start_ts = datetime.now().timestamp()

        # Create a queue for messages
        message_queue: asyncio.Queue[SlackMessage] = asyncio.Queue()
        stop_event = asyncio.Event()

        # IMPORTANT: aiohttp SocketModeClient runs handlers in the same event loop,
        # so handlers MUST be async and can use regular await
        async def handle_message(client: SocketModeClient, req: SocketModeRequest):
            try:
                # Acknowledge the event
                response = SocketModeResponse(envelope_id=req.envelope_id)
                await client.send_socket_mode_response(response)

                if req.type == "events_api":
                    event = req.payload.get("event", {})
                    event_type = event.get("type")

                    # Handle message events
                    if event_type in ("message", "app_mention"):
                        user_id = event.get("user")
                        event_channel_id = event.get("channel")
                        text = event.get("text", "")
                        ts = event.get("ts")
                        thread_ts = event.get("thread_ts")

                        # Skip bot's own messages
                        if skip_own and user_id == bot_user_id:
                            return

                        # Filter by channel if specified
                        if channel_id and event_channel_id != channel_id:
                            return

                        # Skip messages from before the stream started
                        if skip_history and ts and float(ts) < stream_start_ts:
                            return
                        # Create SlackMessage
                        slack_msg = SlackMessage(
                            id=ts,
                            ts=ts,
                            content=text,
                            text=text,
                            author_id=user_id or "",
                            channel_id=event_channel_id or "",
                            thread_id=thread_ts or "",
                            timestamp=datetime.fromtimestamp(float(ts)) if ts else datetime.now(),
                        )

                        # Put message on queue (same event loop, no thread-safe needed)
                        await message_queue.put(slack_msg)
            except Exception:
                # Silently handle errors to keep stream running
                pass

        # Create Socket Mode client - use app_token_str to get the actual token value
        socket_client = SocketModeClient(
            app_token=self.config.app_token_str,
            web_client=self._async_client,
        )
        socket_client.socket_mode_request_listeners.append(handle_message)

        # Start Socket Mode in background
        socket_task = asyncio.create_task(socket_client.connect())

        # Wait for the socket connection to be established
        await asyncio.sleep(5)

        try:
            while not stop_event.is_set():
                try:
                    # Wait for messages with a timeout to allow checking stop_event
                    message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                    yield message
                except asyncio.TimeoutError:
                    continue
        finally:
            # Clean up
            stop_event.set()
            await socket_client.close()
            socket_task.cancel()
            try:
                await socket_task
            except asyncio.CancelledError:
                pass
