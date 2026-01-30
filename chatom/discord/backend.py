"""Discord backend implementation for chatom.

This module provides the Discord backend using the discord.py library.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncIterator, ClassVar, List, Optional, Union

from pydantic import Field

from ..backend import BackendBase
from ..base import (
    DISCORD_CAPABILITIES,
    BackendCapabilities,
    Channel,
    Message,
    Organization,
    Presence,
    PresenceStatus,
    User,
)
from ..format.variant import Format
from .channel import DiscordChannel, DiscordChannelType
from .config import DiscordConfig
from .guild import DiscordGuild
from .mention import mention_channel as _mention_channel, mention_user as _mention_user
from .message import DiscordMessage
from .presence import DiscordPresence
from .user import DiscordUser

__all__ = ("DiscordBackend",)

# Try to import discord.py
try:
    import discord
    from discord import Status as DiscordStatus
    from discord.activity import Activity, ActivityType, Game

    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False
    discord = None  # type: ignore
    DiscordStatus = None  # type: ignore
    Game = None  # type: ignore
    Activity = None  # type: ignore
    ActivityType = None  # type: ignore


def _status_to_discord(status: str) -> Any:
    """Convert status string to Discord Status enum."""
    if not HAS_DISCORD:
        return None
    status_map = {
        "online": DiscordStatus.online,
        "idle": DiscordStatus.idle,
        "dnd": DiscordStatus.dnd,
        "do_not_disturb": DiscordStatus.dnd,
        "invisible": DiscordStatus.invisible,
        "offline": DiscordStatus.offline,
    }
    return status_map.get(status.lower(), DiscordStatus.online)


def _discord_status_to_presence(status: Any) -> PresenceStatus:
    """Convert Discord Status to PresenceStatus."""
    if not HAS_DISCORD or status is None:
        return PresenceStatus.UNKNOWN
    status_map = {
        DiscordStatus.online: PresenceStatus.ONLINE,
        DiscordStatus.idle: PresenceStatus.AWAY,
        DiscordStatus.dnd: PresenceStatus.DND,
        DiscordStatus.invisible: PresenceStatus.INVISIBLE,
        DiscordStatus.offline: PresenceStatus.OFFLINE,
    }
    return status_map.get(status, PresenceStatus.UNKNOWN)


def _discord_channel_type_to_enum(channel_type: int) -> DiscordChannelType:
    """Convert Discord channel type int to DiscordChannelType enum."""
    type_map = {
        0: DiscordChannelType.GUILD_TEXT,
        1: DiscordChannelType.DM,
        2: DiscordChannelType.GUILD_VOICE,
        3: DiscordChannelType.GROUP_DM,
        4: DiscordChannelType.GUILD_CATEGORY,
        5: DiscordChannelType.GUILD_ANNOUNCEMENT,
        10: DiscordChannelType.ANNOUNCEMENT_THREAD,
        11: DiscordChannelType.PUBLIC_THREAD,
        12: DiscordChannelType.PRIVATE_THREAD,
        13: DiscordChannelType.GUILD_STAGE_VOICE,
        14: DiscordChannelType.GUILD_DIRECTORY,
        15: DiscordChannelType.GUILD_FORUM,
        16: DiscordChannelType.GUILD_MEDIA,
    }
    return type_map.get(channel_type, DiscordChannelType.GUILD_TEXT)


class DiscordBackend(BackendBase):
    """Discord backend implementation using discord.py.

    This provides the backend interface for Discord using the discord.py library.
    It supports all standard backend operations including messaging, presence,
    and reactions.

    Attributes:
        name: The backend identifier ('discord').
        display_name: Human-readable name.
        format: Discord uses its own markdown flavor.
        capabilities: Discord-specific capabilities.
        config: Discord-specific configuration.

    Example:
        >>> from chatom.discord import DiscordBackend, DiscordConfig
        >>> config = DiscordConfig(bot_token="your-token")
        >>> backend = DiscordBackend(config=config)
        >>> await backend.connect()
        >>> user = await backend.fetch_user("123456789")
    """

    name: ClassVar[str] = "discord"
    display_name: ClassVar[str] = "Discord"
    format: ClassVar[Format] = Format.DISCORD_MARKDOWN

    # Type classes for this backend (used by conversion module)
    user_class: ClassVar[type] = DiscordUser
    channel_class: ClassVar[type] = DiscordChannel
    presence_class: ClassVar[type] = DiscordPresence
    guild_class: ClassVar[type] = DiscordGuild

    capabilities: Optional[BackendCapabilities] = DISCORD_CAPABILITIES
    config: DiscordConfig = Field(default_factory=DiscordConfig)

    # Discord.py client instance
    _client: Any = None

    # Cached bot info (set during connect or on first get_bot_info call)
    _bot_user_id: Optional[str] = None
    _bot_user_name: Optional[str] = None

    @property
    def bot_user_id(self) -> Optional[str]:
        """Get the bot's user ID (cached from connect/get_bot_info)."""
        return self._bot_user_id

    @property
    def bot_user_name(self) -> Optional[str]:
        """Get the bot's username (cached from connect/get_bot_info)."""
        return self._bot_user_name

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    def _get_intents(self) -> Any:
        """Build Discord Intents from config."""
        if not HAS_DISCORD:
            return None

        intents = discord.Intents.default()
        for intent_name in self.config.intents:
            if hasattr(intents, intent_name):
                setattr(intents, intent_name, True)
        return intents

    async def connect(self) -> None:
        """Connect to Discord using the configured bot token.

        This creates a Discord client and logs in using the bot token.
        Note that for full event handling, you may need to run the client
        with client.start() instead.

        Raises:
            RuntimeError: If discord.py is not installed or token is missing.
        """
        if not HAS_DISCORD:
            raise RuntimeError("discord.py is not installed. Install with: pip install discord.py")

        if not self.config.has_token:
            raise RuntimeError("Discord bot token is required")

        # Create client with configured intents
        intents = self._get_intents()
        self._client = discord.Client(intents=intents)

        # Login to Discord (this validates the token)
        await self._client.login(self.config.bot_token_str)
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from Discord."""
        if self._client is not None:
            await self._client.close()
            self._client = None
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
        """Fetch a user from Discord.

        Accepts flexible inputs:
        - User ID as positional arg or id=
        - User object (returns as-is or refreshes)
        - name= to search by display name (limited)
        - handle= to search by username (limited)

        Note: Discord API has limited user search capabilities.
        ID-based lookup is most reliable.

        Args:
            identifier: A User object or user ID string.
            id: User ID.
            name: Display name to search for.
            email: Email (not supported by Discord).
            handle: Username to search for.

        Returns:
            The user if found, None otherwise.
        """
        # Handle User object input
        if isinstance(identifier, DiscordUser):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check cache first for ID lookup
        if id:
            cached = self.users.get_by_id(id)
            if cached:
                return cached

        if self._client is None:
            return None

        # ID-based lookup
        if id:
            try:
                user_id = int(id)
                discord_user = await self._client.fetch_user(user_id)
                if discord_user:
                    user = DiscordUser(
                        id=str(discord_user.id),
                        name=discord_user.display_name,
                        handle=discord_user.name,
                        avatar_url=str(discord_user.display_avatar.url) if discord_user.display_avatar else "",
                        discriminator=discord_user.discriminator or "0",
                        global_name=discord_user.global_name,
                        is_bot=discord_user.bot,
                        is_system=discord_user.system,
                    )
                    self.users.add(user)
                    return user
            except (discord.NotFound, discord.HTTPException, ValueError):
                pass

        # Name/handle search - check cache only (Discord API doesn't support user search)
        if name or handle:
            for cached_user in self.users.all():
                if isinstance(cached_user, DiscordUser):
                    if name and cached_user.name.lower() == name.lower():
                        return cached_user
                    if handle and cached_user.handle.lower() == handle.lower():
                        return cached_user

        return None

    async def fetch_channel(
        self,
        identifier: Optional[Union[str, Channel]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel from Discord.

        Accepts flexible inputs:
        - Channel ID as positional arg or id=
        - Channel object (returns as-is or refreshes)
        - name= to search by channel name (requires guild context)

        Note: Discord requires channel ID for direct lookup.
        Name-based search checks cache only.

        Args:
            identifier: A Channel object or channel ID string.
            id: Channel ID.
            name: Channel name to search for (cache only).

        Returns:
            The channel if found, None otherwise.
        """
        # Handle Channel object input
        if isinstance(identifier, DiscordChannel):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        # Check cache first for ID lookup
        if id:
            cached = self.channels.get_by_id(id)
            if cached:
                return cached

        if self._client is None:
            return None

        # ID-based lookup
        if id:
            try:
                channel_id = int(id)
                discord_channel = await self._client.fetch_channel(channel_id)
                if discord_channel:
                    channel = DiscordChannel(
                        id=str(discord_channel.id),
                        name=getattr(discord_channel, "name", "DM"),
                        topic=getattr(discord_channel, "topic", "") or "",
                        guild_id=str(discord_channel.guild.id) if hasattr(discord_channel, "guild") and discord_channel.guild else "",
                        position=getattr(discord_channel, "position", 0),
                        nsfw=getattr(discord_channel, "nsfw", False),
                        slowmode_delay=getattr(discord_channel, "slowmode_delay", 0),
                        discord_type=_discord_channel_type_to_enum(discord_channel.type.value),
                    )
                    self.channels.add(channel)
                    return channel
            except (discord.NotFound, discord.HTTPException, ValueError):
                pass

        # Name search - check cache only
        if name:
            for cached_channel in self.channels.all():
                if isinstance(cached_channel, DiscordChannel):
                    if cached_channel.name.lower() == name.lower():
                        return cached_channel

        return None

    async def fetch_messages(
        self,
        channel: Union[str, Channel],
        limit: int = 100,
        before: Optional[Union[str, Message]] = None,
        after: Optional[Union[str, Message]] = None,
    ) -> List[Message]:
        """Fetch messages from a Discord channel.

        Args:
            channel: The channel to fetch messages from (ID string or Channel object).
            limit: Maximum number of messages (1-100).
            before: Fetch messages before this message (ID string or Message object).
            after: Fetch messages after this message (ID string or Message object).

        Returns:
            List of messages.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        # Resolve channel ID
        channel_id = await self._resolve_channel_id(channel)

        # Resolve before/after message IDs
        before_id = None
        if before:
            if isinstance(before, Message):
                before_id = before.id
            else:
                before_id = before

        after_id = None
        if after:
            if isinstance(after, Message):
                after_id = after.id
            else:
                after_id = after

        try:
            discord_channel = await self._client.fetch_channel(int(channel_id))
            if discord_channel is None:
                return []

            # Build kwargs for history()
            kwargs: dict[str, Any] = {"limit": min(limit, 100)}
            if before_id:
                kwargs["before"] = discord.Object(id=int(before_id))
            if after_id:
                kwargs["after"] = discord.Object(id=int(after_id))

            messages: List[Message] = []
            async for msg in discord_channel.history(**kwargs):
                message = DiscordMessage(
                    id=str(msg.id),
                    content=msg.content,
                    timestamp=msg.created_at.replace(tzinfo=timezone.utc) if msg.created_at else datetime.now(timezone.utc),
                    user_id=str(msg.author.id),
                    channel_id=str(msg.channel.id),
                    guild_id=str(msg.guild.id) if msg.guild else "",
                    edited=msg.edited_at is not None,
                )
                messages.append(message)

            return messages
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to fetch messages: {e}") from e

    async def search_messages(
        self,
        query: str,
        channel: Optional[Union[str, Channel]] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Message]:
        """Search for messages matching a query.

        Note: Discord's API doesn't have a direct message search endpoint for bots.
        This implementation fetches recent messages and filters locally.
        For production use with large channels, consider using Discord's
        user account search or a database-backed solution.

        Args:
            query: The search query string (case-insensitive substring match).
            channel: Channel to search in (required for Discord).
            limit: Maximum number of results.
            **kwargs: Additional options:
                      - from_user: Filter by author ID

        Returns:
            List of messages containing the query.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        if channel is None:
            raise ValueError("Discord search requires a channel parameter")

        # Resolve channel ID
        channel_id = await self._resolve_channel_id(channel)
        from_user = kwargs.get("from_user")
        query_lower = query.lower()

        try:
            discord_channel = await self._client.fetch_channel(int(channel_id))
            if discord_channel is None:
                return []

            messages: List[Message] = []
            # Fetch more messages than limit to account for filtering
            fetch_limit = min(limit * 5, 500)

            async for msg in discord_channel.history(limit=fetch_limit):
                # Check if message matches query
                if query_lower not in msg.content.lower():
                    continue

                # Check user filter
                if from_user and str(msg.author.id) != from_user:
                    continue

                message = DiscordMessage(
                    id=str(msg.id),
                    content=msg.content,
                    timestamp=msg.created_at.replace(tzinfo=timezone.utc) if msg.created_at else datetime.now(timezone.utc),
                    user_id=str(msg.author.id),
                    channel_id=str(msg.channel.id),
                    guild_id=str(msg.guild.id) if msg.guild else "",
                    edited=msg.edited_at is not None,
                )
                messages.append(message)

                if len(messages) >= limit:
                    break

            return messages
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to search messages: {e}") from e

    async def send_message(
        self,
        channel: Union[str, Channel],
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a message to a Discord channel.

        Args:
            channel: The channel to send to (ID string or Channel object).
            content: The message content.
            **kwargs: Additional options (embed, file, tts, etc.).

        Returns:
            The sent message.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        # Resolve channel ID
        channel_id = await self._resolve_channel_id(channel)

        try:
            discord_channel = await self._client.fetch_channel(int(channel_id))
            if discord_channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            # Extract common kwargs
            embed = kwargs.get("embed")
            embeds = kwargs.get("embeds")
            file = kwargs.get("file")
            files = kwargs.get("files")
            tts = kwargs.get("tts", False)

            send_kwargs: dict[str, Any] = {"content": content, "tts": tts}
            if embed:
                send_kwargs["embed"] = embed
            if embeds:
                send_kwargs["embeds"] = embeds
            if file:
                send_kwargs["file"] = file
            if files:
                send_kwargs["files"] = files

            msg = await discord_channel.send(**send_kwargs)

            return DiscordMessage(
                id=str(msg.id),
                content=msg.content,
                timestamp=msg.created_at.replace(tzinfo=timezone.utc) if msg.created_at else datetime.now(timezone.utc),
                user_id=str(msg.author.id),
                channel_id=str(msg.channel.id),
                guild_id=str(msg.guild.id) if msg.guild else "",
            )
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to send message: {e}") from e

    async def edit_message(
        self,
        message: Union[str, Message],
        content: str,
        channel: Optional[Union[str, Channel]] = None,
        **kwargs: Any,
    ) -> Message:
        """Edit a Discord message.

        Args:
            message: The message to edit (ID string or Message object).
            content: The new content.
            channel: The channel containing the message (required if message is a string).
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        # Resolve message and channel IDs
        message_id, channel_id = await self._resolve_message_id(message, channel)

        try:
            discord_channel = await self._client.fetch_channel(int(channel_id))
            if discord_channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await discord_channel.fetch_message(int(message_id))
            edited_msg = await msg.edit(content=content, **kwargs)

            return DiscordMessage(
                id=str(edited_msg.id),
                content=edited_msg.content,
                timestamp=edited_msg.created_at.replace(tzinfo=timezone.utc) if edited_msg.created_at else datetime.now(timezone.utc),
                user_id=str(edited_msg.author.id),
                channel_id=str(edited_msg.channel.id),
                guild_id=str(edited_msg.guild.id) if edited_msg.guild else "",
                edited=True,
            )
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to edit message: {e}") from e

    async def delete_message(
        self,
        message: Union[str, Message],
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Delete a Discord message.

        Args:
            message: The message to delete (ID string or Message object).
            channel: The channel containing the message (required if message is a string).
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        # Resolve message and channel IDs
        message_id, channel_id = await self._resolve_message_id(message, channel)

        try:
            discord_channel = await self._client.fetch_channel(int(channel_id))
            if discord_channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await discord_channel.fetch_message(int(message_id))
            await msg.delete()
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to delete message: {e}") from e

    async def set_presence(
        self,
        status: str,
        status_text: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set the bot's presence on Discord.

        Args:
            status: Presence status ('online', 'idle', 'dnd', 'invisible').
            status_text: Activity text (game name).
            **kwargs: Additional options:
                - activity_type: Type of activity ('playing', 'streaming', 'listening', 'watching', 'competing').
                - url: Streaming URL (for streaming activity).
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        if not HAS_DISCORD:
            raise RuntimeError("discord.py is not installed")

        discord_status = _status_to_discord(status)
        activity = None

        if status_text:
            activity_type = kwargs.get("activity_type", "playing")
            if activity_type == "streaming":
                url = kwargs.get("url", "https://twitch.tv/")
                activity = Activity(type=ActivityType.streaming, name=status_text, url=url)
            elif activity_type == "listening":
                activity = Activity(type=ActivityType.listening, name=status_text)
            elif activity_type == "watching":
                activity = Activity(type=ActivityType.watching, name=status_text)
            elif activity_type == "competing":
                activity = Activity(type=ActivityType.competing, name=status_text)
            else:  # playing
                activity = Game(name=status_text)

        await self._client.change_presence(status=discord_status, activity=activity)

    async def get_presence(self, user_id: str) -> Optional[Presence]:
        """Get a user's presence on Discord.

        Note: This requires the GUILD_PRESENCES intent and caching.
        The user must share a guild with the bot.

        Args:
            user_id: The user ID.

        Returns:
            The user's presence or None if not available.
        """
        if self._client is None:
            return None

        try:
            # Try to find the member in cached guilds
            user_id_int = int(user_id)
            for guild in self._client.guilds:
                member = guild.get_member(user_id_int)
                if member is not None:
                    activities = []
                    for activity in member.activities:
                        activities.append(
                            {
                                "name": getattr(activity, "name", ""),
                                "type": str(getattr(activity, "type", "unknown")),
                            }
                        )

                    return DiscordPresence(
                        user_id=user_id,
                        status=_discord_status_to_presence(member.status),
                        activities=activities,
                        desktop_status=_discord_status_to_presence(member.desktop_status)
                        if hasattr(member, "desktop_status")
                        else PresenceStatus.OFFLINE,
                        mobile_status=_discord_status_to_presence(member.mobile_status)
                        if hasattr(member, "mobile_status")
                        else PresenceStatus.OFFLINE,
                        web_status=_discord_status_to_presence(member.web_status) if hasattr(member, "web_status") else PresenceStatus.OFFLINE,
                    )
            return None
        except (ValueError, AttributeError):
            return None

    async def add_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Add a reaction to a message.

        Args:
            message: The message to react to (ID string or Message object).
            emoji: The emoji (unicode or custom format <:name:id>).
            channel: The channel containing the message (required if message is a string).
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        # Resolve message and channel IDs
        message_id, channel_id = await self._resolve_message_id(message, channel)

        try:
            discord_channel = await self._client.fetch_channel(int(channel_id))
            if discord_channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await discord_channel.fetch_message(int(message_id))
            await msg.add_reaction(emoji)
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to add reaction: {e}") from e

    async def remove_reaction(
        self,
        message: Union[str, Message],
        emoji: str,
        channel: Optional[Union[str, Channel]] = None,
    ) -> None:
        """Remove a reaction from a message.

        Args:
            message: The message to remove reaction from (ID string or Message object).
            emoji: The emoji to remove.
            channel: The channel containing the message (required if message is a string).
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        # Resolve message and channel IDs
        message_id, channel_id = await self._resolve_message_id(message, channel)

        try:
            discord_channel = await self._client.fetch_channel(int(channel_id))
            if discord_channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await discord_channel.fetch_message(int(message_id))
            # Remove the bot's own reaction
            await msg.remove_reaction(emoji, self._client.user)
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to remove reaction: {e}") from e

    def mention_user(self, user: User) -> str:
        """Format a user mention for Discord.

        Args:
            user: The user to mention.

        Returns:
            Discord user mention format (<@user_id>).
        """
        if isinstance(user, DiscordUser):
            return _mention_user(user)
        return f"<@{user.id}>"

    def mention_channel(self, channel: Channel) -> str:
        """Format a channel mention for Discord.

        Args:
            channel: The channel to mention.

        Returns:
            Discord channel mention format (<#channel_id>).
        """
        if isinstance(channel, DiscordChannel):
            return _mention_channel(channel)
        return f"<#{channel.id}>"

    def mention_here(self) -> str:
        """Format an @here mention for Discord.

        Returns:
            Discord @here mention format.
        """
        return "@here"

    def mention_everyone(self) -> str:
        """Format an @everyone mention for Discord.

        Returns:
            Discord @everyone mention format.
        """
        return "@everyone"

    async def get_bot_info(self) -> Optional[User]:
        """Get information about the connected bot user.

        Returns:
            The bot's User object, or None if not available.
        """
        if self._client is None:
            return None

        try:
            bot_user = self._client.user
            if bot_user:
                user = DiscordUser(
                    id=str(bot_user.id),
                    name=bot_user.display_name,
                    handle=bot_user.name,
                    avatar_url=str(bot_user.display_avatar.url) if bot_user.display_avatar else "",
                    discriminator=bot_user.discriminator or "0",
                    global_name=bot_user.global_name,
                    is_bot=bot_user.bot,
                    is_system=bot_user.system,
                )
                # Cache bot info
                self._bot_user_id = user.id
                self._bot_user_name = user.name or user.handle
                return user
        except Exception:
            pass

        return None

    async def create_dm(self, user_id: str) -> Optional[str]:
        """Create a DM channel with a user.

        Args:
            user_id: The user ID to create a DM with.

        Returns:
            The DM channel ID, or None if creation failed.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        try:
            discord_user = await self._client.fetch_user(int(user_id))
            if discord_user:
                dm_channel = await discord_user.create_dm()
                return str(dm_channel.id)
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to create DM: {e}") from e

        return None

    async def create_channel(
        self,
        name: str,
        description: str = "",
        public: bool = True,
        guild_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """Create a new guild text channel.

        Note: This requires the bot to have MANAGE_CHANNELS permission
        in the target guild.

        Args:
            name: The channel name.
            description: Optional channel topic/description.
            public: If False, creates a private channel (not implemented yet).
            guild_id: The guild ID to create the channel in.
                     If not provided, uses config.guild_id.
            **kwargs: Additional options:
                - category_id: Category ID to put the channel under.

        Returns:
            The channel ID of the created channel, or None if failed.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        # Resolve guild ID
        target_guild_id = guild_id or self.config.guild_id
        if not target_guild_id:
            raise RuntimeError("Guild ID required for channel creation. Set guild_id in config or pass as argument.")

        try:
            guild = await self._client.fetch_guild(int(target_guild_id))
            if guild is None:
                raise RuntimeError(f"Guild {target_guild_id} not found")

            # Create the channel
            category_id = kwargs.get("category_id")
            category = None
            if category_id:
                category = await self._client.fetch_channel(int(category_id))

            channel = await guild.create_text_channel(
                name=name,
                topic=description if description else None,
                category=category,
            )

            return str(channel.id)
        except (discord.NotFound, discord.HTTPException, discord.Forbidden, ValueError) as e:
            raise RuntimeError(f"Failed to create channel: {e}") from e

    async def fetch_channel_by_name(
        self,
        name: str,
        guild_id: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel by name from a guild.

        This method searches through the guild's channels to find one
        matching the given name.

        Args:
            name: The channel name to search for (case-insensitive).
            guild_id: The guild ID to search in.
                     If not provided, uses config.guild_id.

        Returns:
            The channel if found, None otherwise.
        """
        if self._client is None:
            return None

        # Check cache first
        for cached_channel in self.channels.all():
            if isinstance(cached_channel, DiscordChannel):
                if cached_channel.name.lower() == name.lower():
                    return cached_channel

        # Resolve guild ID
        target_guild_id = guild_id or self.config.guild_id
        if not target_guild_id:
            return None

        try:
            guild = await self._client.fetch_guild(int(target_guild_id))
            if guild is None:
                return None

            # Fetch all channels from the guild
            channels = await guild.fetch_channels()
            for discord_channel in channels:
                if hasattr(discord_channel, "name") and discord_channel.name.lower() == name.lower():
                    channel = DiscordChannel(
                        id=str(discord_channel.id),
                        name=getattr(discord_channel, "name", ""),
                        topic=getattr(discord_channel, "topic", "") or "",
                        guild_id=str(guild.id),
                        position=getattr(discord_channel, "position", 0),
                        nsfw=getattr(discord_channel, "nsfw", False),
                        slowmode_delay=getattr(discord_channel, "slowmode_delay", 0),
                        discord_type=_discord_channel_type_to_enum(discord_channel.type.value),
                    )
                    self.channels.add(channel)
                    return channel
        except (discord.NotFound, discord.HTTPException, ValueError):
            pass

        return None

    async def fetch_user_by_name(
        self,
        name: str,
        guild_id: Optional[str] = None,
    ) -> Optional[User]:
        """Fetch a user by username from a guild.

        This method searches through the guild's members to find one
        matching the given username or display name.

        Args:
            name: The username or display name to search for (case-insensitive).
            guild_id: The guild ID to search in.
                     If not provided, uses config.guild_id.

        Returns:
            The user if found, None otherwise.
        """
        if self._client is None:
            return None

        # Check cache first
        for cached_user in self.users.all():
            if isinstance(cached_user, DiscordUser):
                if cached_user.name.lower() == name.lower():
                    return cached_user
                if cached_user.handle.lower() == name.lower():
                    return cached_user
                # Handle username#discriminator format
                if "#" in name and cached_user.full_username.lower() == name.lower():
                    return cached_user

        # Resolve guild ID
        target_guild_id = guild_id or self.config.guild_id
        if not target_guild_id:
            return None

        try:
            guild = await self._client.fetch_guild(int(target_guild_id))
            if guild is None:
                return None

            # Search for member - need to search through members
            # For now, check the name without discriminator
            search_name = name.split("#")[0] if "#" in name else name

            # Try to use query_members first (works via gateway, may not need GUILD_MEMBERS intent)
            try:
                members = await guild.query_members(query=search_name, limit=10)
                for member in members:
                    member_name = member.name.lower()
                    member_display = member.display_name.lower()
                    search_lower = search_name.lower()

                    if member_name == search_lower or member_display == search_lower:
                        user = DiscordUser(
                            id=str(member.id),
                            name=member.display_name,
                            handle=member.name,
                            avatar_url=str(member.display_avatar.url) if member.display_avatar else "",
                            discriminator=member.discriminator or "0",
                            global_name=member.global_name,
                            is_bot=member.bot,
                            is_system=member.system,
                        )
                        self.users.add(user)
                        return user
            except (discord.HTTPException, discord.Forbidden):
                pass

            # Fall back to fetch_members if query didn't work
            # This requires GUILD_MEMBERS intent
            try:
                async for member in guild.fetch_members(limit=1000):
                    member_name = member.name.lower()
                    member_display = member.display_name.lower()
                    search_lower = search_name.lower()

                    if member_name == search_lower or member_display == search_lower:
                        user = DiscordUser(
                            id=str(member.id),
                            name=member.display_name,
                            handle=member.name,
                            avatar_url=str(member.display_avatar.url) if member.display_avatar else "",
                            discriminator=member.discriminator or "0",
                            global_name=member.global_name,
                            is_bot=member.bot,
                            is_system=member.system,
                        )
                        self.users.add(user)
                        return user
            except (discord.HTTPException, discord.Forbidden):
                # fetch_members requires GUILD_MEMBERS privileged intent
                pass

        except (discord.NotFound, discord.HTTPException, ValueError):
            pass

        return None

    # =========================================================================
    # Organization/Guild methods
    # =========================================================================

    async def fetch_organization(
        self,
        identifier: Optional[Union[str, Organization]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Organization]:
        """Fetch a guild (organization) from Discord.

        Args:
            identifier: A DiscordGuild object or guild ID string.
            id: Guild ID (alternative to positional identifier).
            name: Guild name to search for (case-insensitive).

        Returns:
            The guild if found, None otherwise.
        """
        # Handle Organization object input
        if isinstance(identifier, DiscordGuild):
            return identifier
        if hasattr(identifier, "id") and identifier is not None:
            id = identifier.id

        # Resolve identifier to id
        if identifier and not id:
            id = str(identifier)

        if self._client is None:
            return None

        # ID-based lookup
        if id:
            try:
                guild_id = int(id)
                discord_guild = await self._client.fetch_guild(guild_id)
                if discord_guild:
                    return DiscordGuild.from_discord_guild(discord_guild)
            except (discord.NotFound, discord.HTTPException, ValueError):
                pass

        # Name-based lookup
        if name:
            return await self.fetch_organization_by_name(name)

        return None

    async def fetch_organization_by_name(
        self,
        name: str,
    ) -> Optional[Organization]:
        """Fetch a guild by name.

        This searches through guilds the bot is a member of.

        Args:
            name: The guild name to search for (case-insensitive).

        Returns:
            The guild if found, None otherwise.
        """
        if self._client is None:
            return None

        # Need to be connected to the gateway to access guilds
        if not self._client.is_ready():
            # Start the client connection in the background
            connect_task = asyncio.create_task(self._client.connect())
            # Wait for the client to be ready
            for _ in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                if self._client.is_ready():
                    break
            else:
                # Clean up if we didn't connect
                connect_task.cancel()
                try:
                    await connect_task
                except asyncio.CancelledError:
                    pass
                return None

        # Search through guilds
        for guild in self._client.guilds:
            if guild.name.lower() == name.lower():
                return DiscordGuild.from_discord_guild(guild)

        return None

    async def list_organizations(self) -> List[Organization]:
        """List all guilds the bot has access to.

        Returns:
            List of guilds.
        """
        if self._client is None:
            return []

        # Need to be connected to the gateway to access guilds
        if not self._client.is_ready():
            # Start the client connection in the background
            connect_task = asyncio.create_task(self._client.connect())
            # Wait for the client to be ready
            for _ in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                if self._client.is_ready():
                    break
            else:
                # Clean up if we didn't connect
                connect_task.cancel()
                try:
                    await connect_task
                except asyncio.CancelledError:
                    pass
                return []

        return [DiscordGuild.from_discord_guild(guild) for guild in self._client.guilds]

    # Aliases for Discord terminology
    async def fetch_guild(
        self,
        identifier: Optional[Union[str, Organization]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Organization]:
        """Fetch a guild from Discord.

        This is an alias for fetch_organization using Discord terminology.
        """
        return await self.fetch_organization(identifier, id=id, name=name)

    async def fetch_guild_by_name(
        self,
        name: str,
    ) -> Optional[Organization]:
        """Fetch a guild by name.

        This is an alias for fetch_organization_by_name using Discord terminology.
        """
        return await self.fetch_organization_by_name(name)

    async def list_guilds(self) -> List[Organization]:
        """List all guilds the bot has access to.

        This is an alias for list_organizations using Discord terminology.
        """
        return await self.list_organizations()

    async def stream_messages(
        self,
        channel: Optional[Union[str, Channel]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> AsyncIterator[DiscordMessage]:
        """Stream incoming messages in real-time using Discord gateway.

        This creates a connection to the Discord gateway and yields
        messages as they arrive. Requires the bot to be in a guild
        and have MESSAGE_CONTENT intent enabled.

        Args:
            channel: Optional channel to filter messages (ID string or Channel object).
            skip_own: If True (default), skip messages sent by the bot itself.
            skip_history: If True (default), skip messages that existed before
                         the stream started. Only yields new messages.

        Yields:
            DiscordMessage: Each message as it arrives.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        if not HAS_DISCORD:
            raise RuntimeError("discord.py is not installed")

        # Resolve channel ID if provided
        channel_id: Optional[str] = None
        if channel is not None:
            channel_id = await self._resolve_channel_id(channel)

        # Get bot info for filtering
        bot_user_id = str(self._client.user.id) if self._client.user else None

        # Track when the stream started for skip_history
        stream_start_time = datetime.now(timezone.utc)

        # Create a queue for messages
        message_queue: asyncio.Queue[DiscordMessage] = asyncio.Queue()
        stop_event = asyncio.Event()

        # Store the original on_message handler if any
        original_handler = getattr(self._client, "_original_on_message", None)

        async def on_message(msg: Any) -> None:
            """Handle incoming messages."""
            try:
                # Skip bot's own messages
                if skip_own and bot_user_id and str(msg.author.id) == bot_user_id:
                    return

                # Filter by channel if specified
                if channel_id and str(msg.channel.id) != channel_id:
                    return

                # Skip messages from before the stream started
                if skip_history:
                    msg_time = msg.created_at.replace(tzinfo=timezone.utc) if msg.created_at else datetime.now(timezone.utc)
                    if msg_time < stream_start_time:
                        return

                # Create DiscordMessage
                discord_msg = DiscordMessage(
                    id=str(msg.id),
                    content=msg.content,
                    timestamp=msg.created_at.replace(tzinfo=timezone.utc) if msg.created_at else datetime.now(timezone.utc),
                    author_id=str(msg.author.id),
                    user_id=str(msg.author.id),
                    channel_id=str(msg.channel.id),
                    guild_id=str(msg.guild.id) if msg.guild else "",
                    mentions=[str(u.id) for u in msg.mentions],
                    mention_everyone=msg.mention_everyone,
                    mention_roles=[str(r.id) for r in msg.role_mentions] if msg.role_mentions else [],
                )

                await message_queue.put(discord_msg)

            except Exception:
                # Silently handle errors to keep stream running
                pass

        # Register the message handler
        self._client.event(on_message)
        self._client._original_on_message = original_handler

        # Start the client's event loop if not already running
        # The client needs to be connected to the gateway to receive events
        client_task = None
        if not self._client.is_ready():
            # Start the client in the background to connect to gateway
            client_task = asyncio.create_task(self._client.connect())
            # Wait for the client to be ready
            for _ in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                if self._client.is_ready():
                    break
            else:
                raise RuntimeError("Discord client failed to connect to gateway")

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
            if client_task:
                client_task.cancel()
                try:
                    await client_task
                except asyncio.CancelledError:
                    pass
