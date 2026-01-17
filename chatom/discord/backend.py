"""Discord backend implementation for chatom.

This module provides the Discord backend using the discord.py library.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, List, Optional, Union

from pydantic import Field

from ..backend_registry import BackendBase
from ..base import (
    DISCORD_CAPABILITIES,
    BackendCapabilities,
    Channel,
    Message,
    Presence,
    PresenceStatus,
    User,
)
from ..format.variant import Format
from .channel import DiscordChannel, DiscordChannelType
from .config import DiscordConfig
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

    capabilities: Optional[BackendCapabilities] = DISCORD_CAPABILITIES
    config: DiscordConfig = Field(default_factory=DiscordConfig)

    # Discord.py client instance
    _client: Any = None

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
            for cached_user in self.users._by_id.values():
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
            for cached_channel in self.channels._by_id.values():
                if isinstance(cached_channel, DiscordChannel):
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
        """Fetch messages from a Discord channel.

        Args:
            channel_id: The channel to fetch messages from.
            limit: Maximum number of messages (1-100).
            before: Fetch messages before this message ID.
            after: Fetch messages after this message ID.

        Returns:
            List of messages.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        try:
            channel = await self._client.fetch_channel(int(channel_id))
            if channel is None:
                return []

            # Build kwargs for history()
            kwargs: dict[str, Any] = {"limit": min(limit, 100)}
            if before:
                kwargs["before"] = discord.Object(id=int(before))
            if after:
                kwargs["after"] = discord.Object(id=int(after))

            messages: List[Message] = []
            async for msg in channel.history(**kwargs):
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

    async def send_message(
        self,
        channel_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Send a message to a Discord channel.

        Args:
            channel_id: The channel to send to.
            content: The message content.
            **kwargs: Additional options (embed, file, tts, etc.).

        Returns:
            The sent message.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        try:
            channel = await self._client.fetch_channel(int(channel_id))
            if channel is None:
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

            msg = await channel.send(**send_kwargs)

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
        channel_id: str,
        message_id: str,
        content: str,
        **kwargs: Any,
    ) -> Message:
        """Edit a Discord message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message ID.
            content: The new content.
            **kwargs: Additional options.

        Returns:
            The edited message.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        try:
            channel = await self._client.fetch_channel(int(channel_id))
            if channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await channel.fetch_message(int(message_id))
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
        channel_id: str,
        message_id: str,
    ) -> None:
        """Delete a Discord message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message ID.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        try:
            channel = await self._client.fetch_channel(int(channel_id))
            if channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await channel.fetch_message(int(message_id))
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
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Add a reaction to a message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message ID.
            emoji: The emoji (unicode or custom format <:name:id>).
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        try:
            channel = await self._client.fetch_channel(int(channel_id))
            if channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await channel.fetch_message(int(message_id))
            await msg.add_reaction(emoji)
        except (discord.NotFound, discord.HTTPException, ValueError) as e:
            raise RuntimeError(f"Failed to add reaction: {e}") from e

    async def remove_reaction(
        self,
        channel_id: str,
        message_id: str,
        emoji: str,
    ) -> None:
        """Remove a reaction from a message.

        Args:
            channel_id: The channel containing the message.
            message_id: The message ID.
            emoji: The emoji to remove.
        """
        if self._client is None:
            raise RuntimeError("Not connected to Discord")

        try:
            channel = await self._client.fetch_channel(int(channel_id))
            if channel is None:
                raise RuntimeError(f"Channel {channel_id} not found")

            msg = await channel.fetch_message(int(message_id))
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
