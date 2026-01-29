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
    python -m chatom.tests.integration.discord_e2e

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
            bot_token=self.bot_token,
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
            # We need to start the client to access guilds
            # First, let's connect to the gateway
            client = self.backend._client

            # Start the client connection in the background
            # We use get_running_loop().create_task to avoid the unused variable warning
            asyncio.get_running_loop().create_task(client.connect())

            # Wait for the client to be ready
            for _ in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                if client.is_ready():
                    break
            else:
                raise RuntimeError("Discord client failed to connect to gateway")

            # Now search for the guild
            for guild in client.guilds:
                if guild.name.lower() == self.guild_name.lower():
                    self.guild_id = str(guild.id)
                    self.backend.config.guild_id = self.guild_id
                    self.log(f"Found guild '{self.guild_name}' -> {self.guild_id}")
                    return self.guild_id

            # List available guilds for debugging
            print("  Available guilds:")
            for guild in client.guilds:
                print(f"    - {guild.name} ({guild.id})")

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
                self.log(f"Found channel '{name}' -> {channel.id}")
                return channel.id

            # List available channels for debugging
            if self.backend._client and self.guild_id:
                guild = await self.backend._client.fetch_guild(int(self.guild_id))
                if guild:
                    channels = await guild.fetch_channels()
                    print("  Available text channels:")
                    for ch in channels:
                        if hasattr(ch, "name") and hasattr(ch, "type"):
                            try:
                                if ch.type.value == 0:  # GUILD_TEXT
                                    print(f"    - {ch.name} ({ch.id})")
                            except Exception:
                                pass

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
                self.log(f"Found user '{name}' -> {user.id} (name={user.name}, handle={user.handle})")
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
                await self.backend.add_reaction(self.channel_id, message_id, emoji)
                print(f"  Added reaction: {emoji}")
                await asyncio.sleep(0.5)  # Rate limit

            self.log(f"Added {len(reactions)} reactions")

            # Wait a moment then remove one
            await asyncio.sleep(2)
            await self.backend.remove_reaction(self.channel_id, message_id, "👎")
            self.log("Removed 👎 reaction")

        except Exception as e:
            self.log(f"Failed to test reactions: {e}", success=False)
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
        """Test DM creation."""
        self.section("Test: DM Creation")

        try:
            # Try to get a user ID - if we don't have one from lookup,
            # we can try to create a DM with an arbitrary user or skip
            test_user_id = self.user_id

            # If no user_id from lookup, try getting one from message history
            if not test_user_id:
                print("  No user_id from lookup, trying to get from message history...")
                try:
                    messages = await self.backend.fetch_messages(self.channel_id, limit=20)
                    for msg in messages:
                        author_id = getattr(msg, "author_id", None) or getattr(msg, "user_id", None)
                        # Skip bot's own messages
                        bot_info = await self.backend.get_bot_info()
                        if author_id and (not bot_info or author_id != bot_info.id):
                            test_user_id = author_id
                            print(f"    Found user ID from message history: {test_user_id}")
                            break
                except Exception as e:
                    print(f"    Failed to get user from history: {e}")

            if test_user_id:
                print(f"  Creating DM with user {test_user_id}...")
                dm_channel_id = await self.backend.create_dm(test_user_id)
                if dm_channel_id:
                    self.log(f"Created DM channel: {dm_channel_id}")

                    # Send a test message to the DM
                    msg = (
                        FormattedMessage().add_text("🧪 [E2E Test] DM creation test message\n").add_text(f"Created at: {datetime.now().isoformat()}")
                    )
                    await self.backend.send_message(dm_channel_id, msg.render(Format.DISCORD_MARKDOWN))
                    self.log("Sent message to DM")
                else:
                    self.log("DM creation returned no channel ID", success=False)
            else:
                print("  Skipping DM test - no user ID available")
                print("  (Enable Server Members Intent to allow user lookup by name)")

        except Exception as e:
            self.log(f"Failed to test DM creation: {e}", success=False)
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
                async for message in self.backend.stream_messages(channel_id=self.channel_id):
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
                .add_bold("60 seconds")
                .add_text(" to respond...")
            )
            await self.backend.send_message(self.channel_id, prompt_msg.render(Format.DISCORD_MARKDOWN))
            print("\n  ⏳ Waiting for you to send a message mentioning the bot...")
            print(f"     Mention the bot like: @{bot_name} hello test")

            # Wait for message with timeout
            try:
                await asyncio.wait_for(receive_task, timeout=60.0)
            except asyncio.TimeoutError:
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
                self.log("Timeout waiting for inbound message (60s)", success=False)
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

            # Test rich content
            await self.test_rich_content()

            # Test history
            await self.test_fetch_messages()

            # Test presence
            await self.test_presence(user)

            # Test DM creation
            await self.test_dm_creation()

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
