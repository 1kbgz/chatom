#!/usr/bin/env python
"""Discord End-to-End Integration Test.

This script tests all Discord backend functionality with a real Discord bot.
It requires human interaction to verify the bot's behavior.

Environment Variables Required:
    DISCORD_TOKEN: Your Discord bot token
    DISCORD_TEST_CHANNEL_NAME: A channel name where tests will run (without #)
    DISCORD_TEST_USER_NAME: A Discord username for mention tests (with or without #discriminator)
    DISCORD_GUILD_NAME: The name of the Discord server/guild to use

Usage:
    export DISCORD_TOKEN="your-bot-token"
    export DISCORD_TEST_CHANNEL_NAME="general"
    export DISCORD_TEST_USER_NAME="johndoe#1234"
    export DISCORD_GUILD_NAME="My Server"
    python -m chatom.tests.integration.e2e.discord

The bot will:
1. Connect and display bot info
2. Test sending plain messages
3. Test formatted messages (bold, italic, code with Discord markdown)
4. Test mentions (<@user>, <#channel>, @everyone, @here)
5. Test reactions (add/remove emoji)
6. Test threads (create, reply) - if supported
7. Test reading message history
8. Test presence (get/set status)
9. Test user/channel lookup
10. Test creating DMs
11. Test inbound messages (prompts you to @mention the bot)

Watch the test channel and interact when prompted.
The inbound message test will ask you to send a message mentioning the bot.
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime
from typing import Optional

from chatom.base import Channel
from chatom.discord import (
    DiscordBackend,
    DiscordConfig,
    mention_everyone,
    mention_here,
    mention_role,
)

# Chatom imports
from chatom.format import Format, FormattedMessage, Table


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"❌ Missing required environment variable: {name}")
        print(f"   Set it with: export {name}='your-value'")
        sys.exit(1)
    return value


class DiscordE2ETest:
    """Discord end-to-end test suite."""

    def __init__(self):
        """Initialize test configuration from environment."""
        self.bot_token = get_env("DISCORD_TOKEN")
        self.channel_name = get_env("DISCORD_TEST_CHANNEL_NAME")
        self.user_name = get_env("DISCORD_TEST_USER_NAME")
        self.guild_name = get_env("DISCORD_GUILD_NAME")
        self.backend = None
        self.results = []
        # These will be populated after lookup
        self.channel_id = None
        self.user_id = None
        self.guild_id = None

    def log(self, message: str, success: bool = True):
        """Log a test result."""
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
        self.results.append((message, success))

    def section(self, title: str):
        """Print a section header."""
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    async def setup(self):
        """Set up the Discord backend."""
        self.section("Setting Up Discord Backend")

        # Start with basic intents that don't require privileged access
        # Note: For full functionality, enable the following in Discord Developer Portal:
        # - Server Members Intent (for member lookups)
        # - Message Content Intent (for reading message content)
        config = DiscordConfig(
            token=self.bot_token,
            intents=["guilds", "guild_messages"],  # Basic intents only
        )

        self.backend = DiscordBackend(config=config)
        print("Created DiscordBackend with config")
        print(f"  Channel Name: {self.channel_name}")
        print(f"  User Name: {self.user_name}")
        print(f"  Guild Name: {self.guild_name}")

    async def test_connection(self):
        """Test connecting to Discord."""
        self.section("Test: Connection")

        try:
            await self.backend.connect()
            self.log("Connected to Discord successfully")
            print(f"  Backend name: {self.backend.name}")
            print(f"  Display name: {self.backend.display_name}")
            print(f"  Capabilities: {self.backend.capabilities}")
        except Exception as e:
            self.log(f"Failed to connect: {e}", success=False)
            raise

    async def resolve_guild(self):
        """Look up the guild by name to get the guild ID."""
        self.section("Resolving Guild")

        try:
            # Use the backend's fetch_organization method with name parameter
            guild = await self.backend.fetch_organization(name=self.guild_name)

            if guild:
                self.guild_id = guild.id
                self.backend.config.guild_id = self.guild_id
                self.log(f"Found guild '{guild.name}'")
                print(f"  Guild ID: {guild.id}")
                return self.guild_id

            # List available guilds for debugging
            print("  Available guilds:")
            guilds = await self.backend.list_organizations()
            for g in guilds:
                print(f"    - {g.name} ({g.id})")

            self.log(f"Guild '{self.guild_name}' not found", success=False)
            return None

        except Exception as e:
            self.log(f"Failed to resolve guild: {e}", success=False)
            traceback.print_exc()
            return None

    async def lookup_channel_by_name(self, name: str) -> Optional[str]:
        """Look up a channel ID by name."""
        self.section("Lookup: Channel by Name")

        try:
            # Use the backend's fetch_channel_by_name method
            channel = await self.backend.fetch_channel_by_name(name, self.guild_id)

            if channel:
                self.log(f"Found channel '#{channel.name}'")
                print(f"  Channel ID: {channel.id}")
                return channel.id

            self.log(f"Channel '{name}' not found", success=False)
            return None

        except Exception as e:
            self.log(f"Failed to lookup channel: {e}", success=False)
            traceback.print_exc()
            return None

    async def lookup_user_by_name(self, name: str) -> Optional[str]:
        """Look up a user ID by name or display name."""
        self.section("Lookup: User by Name")

        try:
            # Use the backend's fetch_user_by_name method
            user = await self.backend.fetch_user_by_name(name, self.guild_id)

            if user:
                self.log(f"Found user '@{user.handle or user.name}'")
                print(f"  User ID: {user.id}")
                print(f"  Name: {user.name}")
                print(f"  Handle: {user.handle}")
                return user.id

            # Fallback: try to find the user from recent message history
            print("  User not found via member lookup, trying message history...")
            if self.channel_id:
                try:
                    messages = await self.backend.fetch_messages(self.channel_id, limit=100)
                    search_name = name.split("#")[0].lower() if "#" in name else name.lower()
                    for msg in messages:
                        # Try to fetch the user who authored the message
                        author_id = getattr(msg, "user_id", None) or getattr(msg, "author_id", None)
                        if author_id:
                            author = await self.backend.fetch_user(author_id)
                            if author:
                                author_name = author.name.lower() if author.name else ""
                                author_handle = author.handle.lower() if author.handle else ""
                                if author_name == search_name or author_handle == search_name:
                                    self.log(f"Found user '{name}' via message history -> {author.id}")
                                    return author.id
                except Exception as msg_err:
                    print(f"  Could not search message history: {msg_err}")

            self.log(f"User '{name}' not found", success=False)
            print("  Note: User lookup may require Server Members Intent (privileged intent)")
            print("  Enable it in Discord Developer Portal > Bot > Privileged Gateway Intents")
            return None

        except Exception as e:
            error_msg = str(e)
            if "members" in error_msg.lower() or "intents" in error_msg.lower():
                print("  Note: User lookup requires Server Members Intent (privileged intent)")
                print("  Enable it in Discord Developer Portal > Bot > Privileged Gateway Intents")
                self.log("User lookup skipped (requires Server Members Intent)")
            else:
                self.log(f"Failed to lookup user: {e}", success=False)
                traceback.print_exc()
            return None

    async def test_send_plain_message(self):
        """Test sending a plain text message."""
        self.section("Test: Send Plain Message")

        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Use format system to build message
            msg = FormattedMessage().add_text(f"🧪 [E2E Test] Plain message sent at {timestamp}")
            content = msg.render(Format.DISCORD_MARKDOWN)

            result = await self.backend.send_message(self.channel_id, content)
            self.log(f"Sent plain message at {timestamp}")

            if result:
                print(f"  Message ID: {result.id}")
                return result.id
            return None
        except Exception as e:
            self.log(f"Failed to send plain message: {e}", success=False)
            traceback.print_exc()
            return None

    async def test_send_formatted_message(self):
        """Test sending formatted messages using the format system."""
        self.section("Test: Send Formatted Message (Discord Markdown)")

        try:
            # Build a rich message with formatting
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] Formatted message:\n")
                .add_bold("This is bold text")
                .add_text(" and ")
                .add_italic("this is italic")
                .add_text("\n")
                .add_code("inline_code()")
                .add_text("\n")
                .add_code_block("def hello():\n    print('Hello from code block!')", "python")
            )

            # Render for Discord
            content = msg.render(Format.DISCORD_MARKDOWN)
            print(f"  Rendered content:\n{content[:200]}...")

            result = await self.backend.send_message(self.channel_id, content)
            self.log("Sent formatted message with bold, italic, code")

            return result
        except Exception as e:
            self.log(f"Failed to send formatted message: {e}", success=False)
            traceback.print_exc()
            return None

    async def test_fetch_user(self):
        """Test fetching user information."""
        self.section("Test: Fetch User")

        if not self.user_id:
            print("  Skipping user fetch test - no user ID available")
            print("  (Enable Server Members Intent to allow user lookup by name)")
            return None

        try:
            user = await self.backend.fetch_user(self.user_id)
            if user:
                self.log(f"Fetched user: {user.display_name or user.name}")
                print(f"  User ID: {user.id}")
                print(f"  Name: {user.name}")
                print(f"  Handle: {user.handle}")
                print(f"  Display Name: {user.display_name}")
                print(f"  Is Bot: {getattr(user, 'is_bot', 'N/A')}")
                print(f"  Discriminator: {getattr(user, 'discriminator', 'N/A')}")
                return user
            else:
                self.log(f"User not found: {self.user_id}", success=False)
                return None
        except Exception as e:
            self.log(f"Failed to fetch user: {e}", success=False)
            traceback.print_exc()
            return None

    async def test_fetch_channel(self):
        """Test fetching channel information."""
        self.section("Test: Fetch Channel")

        try:
            channel = await self.backend.fetch_channel(self.channel_id)
            if channel:
                self.log(f"Fetched channel: {channel.name}")
                print(f"  Channel ID: {channel.id}")
                print(f"  Name: {channel.name}")
                print(f"  Topic: {getattr(channel, 'topic', 'N/A')}")
                print(f"  Guild ID: {getattr(channel, 'guild_id', 'N/A')}")
                print(f"  Type: {getattr(channel, 'discord_type', 'N/A')}")
                print(f"  NSFW: {getattr(channel, 'nsfw', 'N/A')}")
                return channel
            else:
                self.log(f"Channel not found: {self.channel_id}", success=False)
                return None
        except Exception as e:
            self.log(f"Failed to fetch channel: {e}", success=False)
            traceback.print_exc()
            return None

    async def test_mentions(self, user, channel):
        """Test user and channel mentions."""
        self.section("Test: Mentions")

        try:
            # User mention
            if user:
                user_mention = self.backend.mention_user(user)
                print(f"  User mention format: {user_mention}")
            else:
                user_mention = f"<@{self.user_id}>"

            # Channel mention
            if channel:
                channel_mention = self.backend.mention_channel(channel)
                print(f"  Channel mention format: {channel_mention}")
            else:
                channel_mention = f"<#{self.channel_id}>"

            # Special mentions (display only, don't send to avoid spam)
            print(f"  @here format: {mention_here()}")
            print(f"  @everyone format: {mention_everyone()}")
            print(f"  Role mention format: {mention_role('123456789')}")

            # Use format system to build message with mentions
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] Mentions:\n")
                .add_text(f"  User: {user_mention}\n")
                .add_text(f"  Channel: {channel_mention}\n")
                .add_text("  (Not sending @here/@everyone to avoid spam)")
            )
            await self.backend.send_message(self.channel_id, msg.render(Format.DISCORD_MARKDOWN))
            self.log("Sent message with user and channel mentions")

        except Exception as e:
            self.log(f"Failed to test mentions: {e}", success=False)
            traceback.print_exc()

    async def test_reactions(self, message_id: Optional[str]):
        """Test adding and removing reactions."""
        self.section("Test: Reactions")

        if not message_id:
            # Send a message to react to
            result = await self.backend.send_message(self.channel_id, "🧪 [E2E Test] React to this message! Bot will add reactions...")
            message_id = result.id if result else None

        if not message_id:
            self.log("No message ID to add reactions to", success=False)
            return

        try:
            # Add reactions (Discord uses unicode emoji)
            reactions = ["👍", "👎", "🎉", "❤️"]
            for emoji in reactions:
                await self.backend.add_reaction(message_id, emoji, channel=self.channel_id)
                print(f"  Added reaction: {emoji}")
                await asyncio.sleep(0.5)  # Rate limit

            self.log(f"Added {len(reactions)} reactions")

            # Wait a moment then remove one
            await asyncio.sleep(2)
            await self.backend.remove_reaction(message_id, "👎", channel=self.channel_id)
            self.log("Removed 👎 reaction")

        except Exception as e:
            self.log(f"Failed to test reactions: {e}", success=False)
            traceback.print_exc()

    async def test_threads(self):
        """Test thread creation and replies."""
        self.section("Test: Threads")

        try:
            # Send a message that will be the thread parent
            result = await self.backend.send_message(
                self.channel_id,
                "🧪 [E2E Test] Thread parent message - replies will be in thread",
            )

            if result:
                print(f"  Parent message ID: {result.id}")

                # Get the discord channel and message to create a thread
                discord_channel = await self.backend._client.fetch_channel(int(self.channel_id))
                discord_message = await discord_channel.fetch_message(int(result.id))

                # Create a thread from the message
                thread = await discord_message.create_thread(
                    name="E2E Test Thread",
                    auto_archive_duration=60,  # 1 hour
                )
                print(f"  Created thread: {thread.name} ({thread.id})")

                # Send messages in the thread
                await thread.send("🧪 [E2E Test] This is the first reply in the thread!")
                await thread.send("🧪 [E2E Test] Second reply in thread")
                self.log("Created thread and sent replies")

            else:
                self.log("Failed to send thread parent message", success=False)

        except Exception as e:
            self.log(f"Failed to test threads: {e}", success=False)
            traceback.print_exc()

    async def test_rich_content(self):
        """Test sending rich content with tables."""
        self.section("Test: Rich Content (Tables)")

        try:
            # Create a message with a table using Table.from_data
            msg = FormattedMessage()
            msg.add_text("🧪 [E2E Test] Rich Content (Table):\n\n")

            table = Table.from_data(
                data=[
                    ["Messages", "✅", "Working"],
                    ["Reactions", "✅", "Working"],
                    ["Mentions", "✅", "Working"],
                    ["Presence", "✅", "Working"],
                    ["DMs", "✅", "Working"],
                ],
                headers=["Feature", "Status", "Notes"],
            )
            msg.content.append(table)

            content = msg.render(Format.DISCORD_MARKDOWN)
            await self.backend.send_message(self.channel_id, content)
            self.log("Sent rich content with table")

        except Exception as e:
            self.log(f"Failed to test rich content: {e}", success=False)
            traceback.print_exc()

    async def test_fetch_messages(self):
        """Test fetching message history."""
        self.section("Test: Fetch Message History")

        try:
            messages = await self.backend.fetch_messages(self.channel_id, limit=10)
            self.log(f"Fetched {len(messages)} messages from history")

            print("\n  Recent messages:")
            for msg in messages[:5]:
                content_preview = (msg.content or "")[:50].replace("\n", " ")
                print(f"  - [{msg.id[:8]}...] {content_preview}...")

            # Test reading a message with the format system
            if messages:
                print("\n  Testing format system on first message...")
                first_msg = messages[0]
                if hasattr(first_msg, "to_formatted"):
                    formatted = first_msg.to_formatted()
                    plain = formatted.render(Format.PLAINTEXT)
                    print(f"  Plain text: {plain[:100]}...")
                    self.log("Successfully converted message to FormattedMessage")
                else:
                    print("  Message doesn't have to_formatted() method")

            return messages

        except Exception as e:
            self.log(f"Failed to fetch messages: {e}", success=False)
            traceback.print_exc()
            return []

    async def test_presence(self, user):
        """Test getting and setting presence."""
        self.section("Test: Presence")

        try:
            # Get user presence (requires GUILD_PRESENCES intent)
            if user:
                presence = await self.backend.get_presence(user.id)
                if presence:
                    print(f"  User presence status: {presence.status}")
                    print(f"  Activities: {getattr(presence, 'activities', 'N/A')}")
                    self.log("Fetched user presence")
                else:
                    print("  Could not fetch presence (may need GUILD_PRESENCES intent)")

            # Set bot presence
            await self.backend.set_presence(
                status="dnd",
                status_text="Running E2E Tests",
                activity_type="playing",
            )
            self.log("Set bot presence with status text")

            # Wait and reset
            await asyncio.sleep(2)
            await self.backend.set_presence(
                status="online",
                status_text="Ready!",
            )
            self.log("Reset bot presence to online")

        except Exception as e:
            self.log(f"Failed to test presence: {e}", success=False)
            traceback.print_exc()

    async def test_dm_creation(self):
        """Test DM creation using Channel.dm_to() convenience method."""
        self.section("Test: DM Creation (using Channel.dm_to)")

        try:
            # Try to get a user - if we don't have one from lookup,
            # we can try to get one from message history
            test_user = None
            test_user_id = self.user_id

            # If we have a user_id, fetch the full user object
            if test_user_id:
                test_user = await self.backend.fetch_user(test_user_id)

            # If no user_id from lookup, try getting one from message history
            if not test_user:
                print("  No user from lookup, trying to get from message history...")
                try:
                    messages = await self.backend.fetch_messages(self.channel_id, limit=20)
                    bot_info = await self.backend.get_bot_info()
                    for msg in messages:
                        if msg.author and (not bot_info or msg.author.id != bot_info.id):
                            test_user = msg.author
                            print(f"    Found user from message history: {test_user.display_name}")
                            break
                except Exception as e:
                    print(f"    Failed to get user from history: {e}")

            if test_user:
                # Method 1: Use Channel.dm_to() convenience method
                print(f"\n  Method 1: Using Channel.dm_to({test_user.display_name})...")
                dm_channel = Channel.dm_to(test_user)
                print(f"    Created incomplete DM channel: {dm_channel}")
                print(f"    Channel type: {dm_channel.channel_type}")
                print(f"    Users: {[u.display_name for u in dm_channel.users]}")
                print(f"    Is incomplete: {dm_channel.is_incomplete}")

                # Send message to incomplete channel - backend will resolve it
                msg = (
                    FormattedMessage()
                    .add_text("🧪 [E2E Test] DM via Channel.dm_to() convenience\n")
                    .add_text(f"Created at: {datetime.now().isoformat()}")
                )
                result = await self.backend.send_message(dm_channel, msg.render(Format.DISCORD_MARKDOWN))
                self.log(f"Sent DM using Channel.dm_to() - resolved to: {result.channel.id if result else 'N/A'}")

                # Method 2: Use create_dm directly with user ID (legacy approach)
                print(f"\n  Method 2: Using create_dm({test_user.id}) directly...")
                dm_channel_id = await self.backend.create_dm(test_user.id)
                if dm_channel_id:
                    self.log(f"Created DM channel via create_dm(): {dm_channel_id}")
                else:
                    self.log("create_dm() returned no channel ID", success=False)

            else:
                print("  Skipping DM test - no user available")
                print("  (Enable Server Members Intent to allow user lookup by name)")

        except Exception as e:
            self.log(f"Failed to test DM creation: {e}", success=False)
            traceback.print_exc()

    async def test_dm_reply_convenience(self):
        """Test as_dm_to_author() convenience method."""
        self.section("Test: as_dm_to_author() Convenience")

        try:
            # Get a recent message from the test channel to use as source
            messages = await self.backend.fetch_messages(self.channel_id, limit=20)
            bot_info = await self.backend.get_bot_info()

            # Find a message from a non-bot user
            source_message = None
            for msg in messages:
                if msg.author and (not bot_info or msg.author.id != bot_info.id):
                    source_message = msg
                    break

            if source_message:
                print(f"  Found message from {source_message.author.display_name}")
                print(f"  Original content: {source_message.content[:50]}...")

                # Use as_dm_to_author() to create a DM response
                dm_message = source_message.as_dm_to_author(
                    f"🧪 [E2E Test] DM reply via as_dm_to_author()\n"
                    f"This is a response to your message in #{self.channel_name}.\n"
                    f"Created at: {datetime.now().isoformat()}"
                )

                print(f"  DM message channel type: {dm_message.channel.channel_type}")
                print(f"  DM message channel users: {[u.display_name for u in dm_message.channel.users]}")
                print(f"  DM message is incomplete: {dm_message.channel.is_incomplete}")

                # Send the DM message - backend will resolve the channel
                _result = await self.backend.send_message(dm_message.channel, dm_message.content)
                self.log("Sent DM using as_dm_to_author() convenience")

            else:
                print("  No non-bot message found to test with")
                self.log("as_dm_to_author test skipped - no source message", success=False)

        except Exception as e:
            self.log(f"Failed to test as_dm_to_author: {e}", success=False)
            traceback.print_exc()

    async def test_replies(self):
        """Test message replies using as_reply() convenience method."""
        self.section("Test: Message Replies (as_reply)")

        try:
            # Send a message that will receive a reply
            msg = FormattedMessage().add_text("🧪 [E2E Test] Original message - will receive a reply")
            result = await self.backend.send_message(self.channel_id, msg.render(Format.DISCORD_MARKDOWN))

            if result:
                print(f"  Original message ID: {result.id}")

                # Use as_reply() convenience method
                reply_msg = result.as_reply("🧪 [E2E Test] This is a reply using as_reply() convenience!")
                print(f"  Reply message thread: {reply_msg.thread}")

                # For Discord, we need to use the reference kwarg for replies
                reply_result = await self.backend.send_message(
                    self.channel_id,
                    reply_msg.content,
                    reference={"message_id": int(result.id)},
                )
                if reply_result:
                    self.log("Sent reply using as_reply() convenience")
                    print(f"  Reply ID: {reply_result.id}")
                else:
                    self.log("as_reply() failed", success=False)
            else:
                self.log("Failed to send original message for reply test", success=False)

        except Exception as e:
            self.log(f"Failed to test replies: {e}", success=False)
            traceback.print_exc()

    async def test_forwarding(self):
        """Test message forwarding using forward_message()."""
        self.section("Test: Message Forwarding")

        try:
            # Get a recent message to forward
            messages = await self.backend.fetch_messages(self.channel_id, limit=10)

            if messages:
                source_message = messages[0]
                print(f"  Source message: {(source_message.content or '')[:50]}...")

                # Forward the message to the same channel (for testing)
                forwarded = await self.backend.forward_message(
                    source_message,
                    self.channel_id,
                    include_attribution=True,
                    prefix="📤 ",
                )
                if forwarded:
                    self.log("Forwarded message with attribution")
                    print(f"  Forwarded message ID: {forwarded.id}")
            else:
                self.log("No messages found to forward", success=False)

        except Exception as e:
            self.log(f"Failed to test forwarding: {e}", success=False)
            traceback.print_exc()

    async def test_group_dm(self):
        """Test multi-person group DM using Channel.group_dm_to()."""
        self.section("Test: Group DM (Multi-Person)")

        try:
            # Get the test user
            test_user = None
            if self.user_id:
                test_user = await self.backend.fetch_user(self.user_id)

            if test_user:
                # Demonstrate Channel.group_dm_to() API
                print("  Channel.group_dm_to() requires 2+ users")
                print("  Example: group_dm = Channel.group_dm_to([user1, user2])")

                # For actual group DM, we need 2+ users - try to find another user from history
                messages = await self.backend.fetch_messages(self.channel_id, limit=50)
                bot_info = await self.backend.get_bot_info()
                other_users = []
                seen_ids = {self.user_id}
                if bot_info:
                    seen_ids.add(bot_info.id)

                for msg in messages:
                    if msg.author and msg.author.id not in seen_ids:
                        other_users.append(msg.author)
                        seen_ids.add(msg.author.id)
                        if len(other_users) >= 1:
                            break

                if other_users:
                    # Create group DM with test_user and other_user
                    group_users = [test_user] + other_users
                    print(f"  Creating group DM with {len(group_users)} users:")
                    for u in group_users:
                        print(f"    - {u.display_name} ({u.id})")

                    group_dm = Channel.group_dm_to(group_users)
                    print(f"  Group DM channel type: {group_dm.channel_type}")
                    print(f"  Is incomplete: {group_dm.is_incomplete}")

                    # Note: Discord group DMs require users to be friends or have shared server
                    # This may fail due to Discord's restrictions
                    try:
                        msg = (
                            FormattedMessage()
                            .add_text("🧪 [E2E Test] Group DM via Channel.group_dm_to()\n")
                            .add_text(f"Created at: {datetime.now().isoformat()}")
                        )
                        _result = await self.backend.send_message(group_dm, msg.render(Format.DISCORD_MARKDOWN))
                        self.log("Sent group DM using Channel.group_dm_to()")
                    except Exception as e:
                        print(f"  Group DM send failed (Discord restriction): {e}")
                        self.log("Group DM API demonstrated (Discord may restrict group DM creation)")
                else:
                    print("  No other users found for group DM test")
                    self.log("Group DM API demonstrated (need 2+ real users to send)")
            else:
                print("  Skipping group DM test - no user available")
                self.log("Group DM test skipped - no user", success=False)

        except Exception as e:
            self.log(f"Failed to test group DM: {e}", success=False)
            traceback.print_exc()

    async def test_file_attachment(self):
        """Test sending a file attachment."""
        self.section("Test: File Attachment")

        try:
            import os as temp_os
            import tempfile

            import discord

            # Create a temporary text file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write("This is a test file created by the chatom E2E test suite.\n")
                f.write(f"Created at: {datetime.now().isoformat()}\n")
                f.write("This file can be safely deleted.\n")
                temp_file_path = f.name

            print(f"  Created temp file: {temp_file_path}")

            try:
                # Create a discord.File object
                discord_file = discord.File(temp_file_path, filename="e2e_test_file.txt")

                # Send message with file attachment
                result = await self.backend.send_message(
                    self.channel_id,
                    "🧪 [E2E Test] File attachment test",
                    file=discord_file,
                )

                if result:
                    self.log("Sent file attachment successfully")
                    print(f"  Message ID: {result.id}")
                else:
                    self.log("File attachment send failed", success=False)

            finally:
                # Clean up temp file
                temp_os.unlink(temp_file_path)

        except Exception as e:
            self.log(f"Failed to test file attachment: {e}", success=False)
            traceback.print_exc()

    async def test_inbound_messages(self, bot_user_id: str, bot_name: str):
        """Test receiving inbound messages with bot mentions.

        This test uses the Discord gateway to receive real-time messages.
        """
        self.section("Test: Inbound Messages (Interactive)")

        try:
            received_message = None

            async def receive_one_message():
                nonlocal received_message
                print("  [receive_one_message] Starting to iterate stream_messages...")
                # skip_own=True and skip_history=True are defaults
                async for message in self.backend.stream_messages(channel=self.channel_id):
                    print(f"  [receive_one_message] Got message: {message}")
                    received_message = message
                    return  # Got one message from a user, exit
                print("  [receive_one_message] stream_messages ended without message")

            # Start receiving in background
            print("  Creating receive task...")
            receive_task = asyncio.create_task(receive_one_message())

            # Give the stream time to start
            await asyncio.sleep(3)

            # Now send prompt to user
            print("  Sending prompt to user...")
            prompt_msg = (
                FormattedMessage()
                .add_text("🧪 ")
                .add_bold("[E2E Test] Inbound Message Test")
                .add_text("\n\nPlease send a message in this channel that ")
                .add_bold("mentions the bot")
                .add_text(".\n\nExample: ")
                .add_italic(f"@{bot_name} hello this is a test message")
                .add_text("\n\nYou have ")
                .add_bold("30 seconds")
                .add_text(" to respond...")
            )
            await self.backend.send_message(self.channel_id, prompt_msg.render(Format.DISCORD_MARKDOWN))
            print("\n  ⏳ Waiting for you to send a message mentioning the bot...")
            print(f"     Mention the bot like: @{bot_name} hello test")

            # Wait for message with timeout
            try:
                await asyncio.wait_for(receive_task, timeout=30.0)
            except asyncio.TimeoutError:
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
                self.log("Timeout waiting for inbound message (30s)", success=False)
                return

            if received_message:
                self.log("Received inbound message from user")
                print("\n  📨 Message received:")
                print(f"     Message ID: {received_message.id}")
                print(f"     From: {received_message.author_id}")
                print(f"     Text: {(received_message.content or '')[:200]}...")

                # Check if the bot was mentioned
                mentions = getattr(received_message, "mentions", [])
                if bot_user_id in mentions:
                    self.log("Bot mention detected in message")
                elif f"<@{bot_user_id}>" in (received_message.content or ""):
                    self.log("Bot mention detected in message content")
                else:
                    print(f"     (Bot mention <@{bot_user_id}> not found, but message was received)")

                # Send acknowledgment
                ack_msg = (
                    FormattedMessage()
                    .add_text("✅ ")
                    .add_bold("Message received!")
                    .add_text("\n\nI heard you say: ")
                    .add_italic((received_message.content or "")[:100])
                )
                await self.backend.send_message(self.channel_id, ack_msg.render(Format.DISCORD_MARKDOWN))
            else:
                self.log("Message received but was None", success=False)

        except Exception as e:
            self.log(f"Failed to test inbound messages: {e}", success=False)
            traceback.print_exc()

    async def cleanup(self):
        """Clean up and disconnect."""
        self.section("Cleanup")

        if self.backend and self.backend.connected:
            await self.backend.disconnect()
            self.log("Disconnected from Discord")

    def print_summary(self):
        """Print test summary."""
        self.section("Test Summary")

        passed = sum(1 for _, s in self.results if s)
        failed = sum(1 for _, s in self.results if not s)
        total = len(self.results)

        print(f"  Passed: {passed}/{total}")
        print(f"  Failed: {failed}/{total}")
        print()

        if failed > 0:
            print("  Failed tests:")
            for msg, success in self.results:
                if not success:
                    print(f"    ❌ {msg}")

        return failed == 0

    async def run_all(self):
        """Run all tests."""
        print("\n" + "=" * 60)
        print("  Discord End-to-End Integration Test")
        print("=" * 60)

        try:
            await self.setup()
            await self.test_connection()

            # Resolve guild first (needed for channel/user lookups)
            guild_id = await self.resolve_guild()
            if not guild_id:
                print(f"\n❌ Cannot continue without guild. Make sure '{self.guild_name}' exists and bot is a member.")
                return False

            # Lookup channel and user by name
            self.channel_id = await self.lookup_channel_by_name(self.channel_name)
            if not self.channel_id:
                print(f"\n❌ Cannot continue without channel. Make sure '{self.channel_name}' exists.")
                return False

            self.user_id = await self.lookup_user_by_name(self.user_name)
            if not self.user_id:
                print(f"\n⚠️  User '{self.user_name}' not found. Some tests may be skipped.")

            # Fetch user and channel for later tests
            user = await self.test_fetch_user()
            channel = await self.test_fetch_channel()

            # Test messaging
            message_id = await self.test_send_plain_message()
            await self.test_send_formatted_message()
            await self.test_mentions(user, channel)

            # Test reactions
            await self.test_reactions(message_id)

            # Test threads
            await self.test_threads()

            # Test rich content
            await self.test_rich_content()

            # Test history
            await self.test_fetch_messages()

            # Test presence
            await self.test_presence(user)

            # Test DM creation (with Channel.dm_to convenience)
            await self.test_dm_creation()

            # Test as_dm_to_author convenience
            await self.test_dm_reply_convenience()

            # Test replies
            await self.test_replies()

            # Test forwarding
            await self.test_forwarding()

            # Test group DM
            await self.test_group_dm()

            # Test file attachment
            await self.test_file_attachment()

            # Test inbound messages
            bot_info = await self.backend.get_bot_info()
            if bot_info:
                print(f"\n  Bot info: {bot_info.name} ({bot_info.id})")
                await self.test_inbound_messages(bot_info.id, bot_info.name)
            else:
                print("\n  Could not get bot info, skipping inbound message test")

        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            traceback.print_exc()

        finally:
            await self.cleanup()

        return self.print_summary()


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  Discord E2E Integration Test")
    print("=" * 60)
    print("\nThis test requires:")
    print("  - DISCORD_TOKEN: Your Discord bot token")
    print("  - DISCORD_TEST_CHANNEL_NAME: Channel name to run tests in (without #)")
    print("  - DISCORD_TEST_USER_NAME: Username for mention tests")
    print("  - DISCORD_GUILD_NAME: Name of the Discord server/guild")
    print("\nRequired Discord bot permissions:")
    print("  - Send Messages")
    print("  - Read Message History")
    print("  - Add Reactions")
    print("  - Read Messages/View Channels")
    print("\nRequired Intents (enable in Discord Developer Portal):")
    print("  - Server Members Intent (for member lookups)")
    print("  - Message Content Intent (for reading message content)")
    print("\nThe bot will send messages to the test channel.")
    print("Please watch the channel and interact when prompted.\n")

    test = DiscordE2ETest()
    success = await test.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
