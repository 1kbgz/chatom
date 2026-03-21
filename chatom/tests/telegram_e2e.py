#!/usr/bin/env python
"""Telegram End-to-End Integration Test.

This script tests all Telegram backend functionality with a real Telegram bot.
It requires human interaction to verify the bot's behavior.

Environment Variables Required:
    TELEGRAM_TOKEN: Your Telegram bot token (from @BotFather)
    TELEGRAM_TEST_USER_NAME: A Telegram username for mention tests (without @)

Chat Lookup (at least one recommended):
    TELEGRAM_TEST_CHAT_NAME: Public @username of the chat/group (without @)
    TELEGRAM_TEST_CHAT_ID: Numeric chat ID (works for private groups too)
    If neither is set, the test will try to discover chats from recent bot updates.

Optional Environment Variables:
    TELEGRAM_TEST_USER_ID: User ID for mention tests (if username lookup unavailable)

Usage:
    export TELEGRAM_TOKEN="123456:ABC-DEF..."
    export TELEGRAM_TEST_CHAT_NAME="my_test_group"
    export TELEGRAM_TEST_USER_NAME="johndoe"
    python -m chatom.tests.telegram_e2e

The bot will:
1. Connect and display bot info
2. Test sending plain messages
3. Test formatted messages (bold, italic, code with HTML)
4. Test mentions (@username, tg://user links)
5. Test reactions (add/remove emoji)
6. Test replies (reply_to_message_id)
7. Test rich content (tables)
8. Test fetching message history (limited - Telegram Bot API limitation)
9. Test presence (limited - Telegram Bot API limitation)
10. Test user/channel lookup
11. Test creating DMs
12. Test DM reply convenience (as_dm_to_author)
13. Test message forwarding
14. Test file attachment
15. Test message editing
16. Test message deletion
17. Test inbound messages (prompts you to send a message to the bot)

Watch the test chat and interact when prompted.
The inbound message test will ask you to send a message mentioning the bot.
"""

import asyncio
import os
import sys
import tempfile
import traceback
from datetime import datetime
from typing import Optional

from chatom.base import Channel, User
from chatom.format import Format, FormattedMessage, Table
from chatom.telegram import TelegramBackend, TelegramConfig


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"❌ Missing required environment variable: {name}")
        print(f"   Set it with: export {name}='your-value'")
        sys.exit(1)
    return value


class TelegramE2ETest:
    """Telegram end-to-end test suite."""

    def __init__(self):
        """Initialize test configuration from environment."""
        self.bot_token = get_env("TELEGRAM_TOKEN")
        self.chat_name = get_env("TELEGRAM_TEST_CHAT_NAME", required=False)
        self.chat_id = get_env("TELEGRAM_TEST_CHAT_ID", required=False)
        self.user_name = get_env("TELEGRAM_TEST_USER_NAME")
        self.user_id = get_env("TELEGRAM_TEST_USER_ID", required=False)

        if not self.chat_name and not self.chat_id:
            print("⚠️  Neither TELEGRAM_TEST_CHAT_NAME nor TELEGRAM_TEST_CHAT_ID is set.")
            print("   Will attempt to discover chats from recent bot updates.")
            print("   For reliable results, set one of:")
            print("     TELEGRAM_TEST_CHAT_NAME: public @username of the group (without @)")
            print("     TELEGRAM_TEST_CHAT_ID: numeric chat ID (for private groups)")

        self.backend = None
        self.results = []
        # Will be populated after lookup
        self.bot_user_id = None
        self.bot_user_name = None

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
        """Set up the Telegram backend."""
        self.section("Setting Up Telegram Backend")

        config = TelegramConfig(
            bot_token=self.bot_token,
        )

        self.backend = TelegramBackend(config=config)
        print("Created TelegramBackend with config")
        print(f"  Chat Name: {self.chat_name}")
        print(f"  Chat ID: {self.chat_id}")
        print(f"  User Name: {self.user_name}")

    async def test_connection(self):
        """Test connecting to Telegram."""
        self.section("Test: Connection")

        try:
            await self.backend.connect()
            self.log("Connected to Telegram successfully")
            print(f"  Backend name: {self.backend.name}")
            print(f"  Display name: {self.backend.display_name}")
            print(f"  Format: {self.backend.format}")
            print(f"  Capabilities: {self.backend.capabilities}")
            print(f"  Bot user ID: {self.backend.bot_user_id}")
            print(f"  Bot username: {self.backend.bot_user_name}")

            self.bot_user_id = self.backend.bot_user_id
            self.bot_user_name = self.backend.bot_user_name
        except Exception as e:
            self.log(f"Failed to connect: {e}", success=False)
            raise

    async def lookup_chat(self) -> Optional[str]:
        """Look up the chat by name or ID and return the resolved chat ID."""
        self.section("Lookup: Chat")

        # If we already have a numeric chat ID, verify it works
        if self.chat_id:
            try:
                channel = await self.backend.fetch_channel(self.chat_id)
                if channel:
                    self.log(f"Found chat by ID: {channel.name} ({channel.id})")
                    return channel.id
            except Exception as e:
                self.log(f"Chat ID {self.chat_id} lookup failed: {e}", success=False)

        # Look up by name (tries @username via getChat API)
        if self.chat_name:
            try:
                channel = await self.backend.fetch_channel(name=self.chat_name)
                if channel:
                    self.log(f"Found chat '{self.chat_name}' -> {channel.name} ({channel.id})")
                    return channel.id
                self.log(f"Chat '{self.chat_name}' not found via @username lookup", success=False)
            except Exception as e:
                self.log(f"Chat name lookup failed: {e}", success=False)

        # As a last resort, discover chats from recent updates
        print("\n  Attempting to discover chats from recent bot updates...")
        print("  (Send a message in the target group if the bot hasn't received any yet)\n")
        chats = await self.backend.discover_chats(timeout=5.0)
        if chats:
            print(f"  Found {len(chats)} chat(s) from recent updates:")
            for ch in chats:
                username_str = f" (@{ch.username})" if ch.username else ""
                print(f"    - {ch.name}{username_str}  [id={ch.id}, type={ch.chat_type.value}]")

            # Try matching by title or username
            target = (self.chat_name or "").lower()
            for ch in chats:
                if target and (ch.name.lower() == target or ch.username.lower() == target):
                    self.log(f"Matched discovered chat: {ch.name} ({ch.id})")
                    return ch.id

            # If only one chat found, use it
            if len(chats) == 1:
                ch = chats[0]
                self.log(f"Using only discovered chat: {ch.name} ({ch.id})")
                return ch.id

            print("\n  Could not auto-match a chat. Set TELEGRAM_TEST_CHAT_ID to one of the IDs above.")
        else:
            print("  No chats discovered. Make sure:")
            print("    1. The bot is added to the target group")
            print("    2. Someone has sent a message in the group since the bot was added")
            print("    3. The group has a public @username (for name-based lookup)")

        return None

    async def test_fetch_channel(self):
        """Test fetching channel/chat information."""
        self.section("Test: Fetch Channel (getChat)")

        try:
            channel = await self.backend.fetch_channel(self.chat_id)
            if channel:
                self.log(f"Fetched chat: {channel.name}")
                print(f"  Chat ID: {channel.id}")
                print(f"  Name: {channel.name}")
                print(f"  Topic: {getattr(channel, 'topic', 'N/A')}")
                print(f"  Chat Type: {getattr(channel, 'chat_type', 'N/A')}")
                print(f"  Description: {getattr(channel, 'description', 'N/A')}")
                print(f"  Is Forum: {getattr(channel, 'is_forum', 'N/A')}")
                return channel
            else:
                self.log(f"Chat not found: {self.chat_id}", success=False)
                return None
        except Exception as e:
            self.log(f"Failed to fetch chat: {e}", success=False)
            traceback.print_exc()
            return None

    async def test_fetch_user(self):
        """Test fetching user information."""
        self.section("Test: Fetch User")

        try:
            # Telegram Bot API cannot lookup users arbitrarily -
            # users must have interacted with the bot first.
            # Try by user_id if available (from env or discovered from messages)
            user = None

            if self.user_id:
                user = await self.backend.fetch_user(self.user_id)

            if not user and self.user_name:
                user = await self.backend.fetch_user(handle=self.user_name)

            if user:
                self.log(f"Fetched user: {user.display_name or user.name}")
                print(f"  User ID: {user.id}")
                print(f"  Name: {user.name}")
                print(f"  Handle: {user.handle}")
                print(f"  Display Name: {user.display_name}")
                print(f"  Username: {getattr(user, 'username', 'N/A')}")
                print(f"  First Name: {getattr(user, 'first_name', 'N/A')}")
                print(f"  Last Name: {getattr(user, 'last_name', 'N/A')}")
                print(f"  Is Bot: {getattr(user, 'is_bot', 'N/A')}")
                return user
            else:
                print("  Note: Telegram Bot API cannot lookup users arbitrarily.")
                print("  Users must have interacted with the bot first.")
                print("  User will be discovered from inbound messages later.")
                self.log("User not found in cache (Telegram API limitation)")
                return None
        except Exception as e:
            self.log(f"Failed to fetch user: {e}", success=False)
            traceback.print_exc()
            return None

    async def test_send_plain_message(self):
        """Test sending a plain text message."""
        self.section("Test: Send Plain Message")

        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Send without parse_mode for plain text
            content = f"🧪 [E2E Test] Plain message sent at {timestamp}"

            result = await self.backend.send_message(self.chat_id, content, parse_mode=None)
            self.log(f"Sent plain message at {timestamp}")

            if result:
                print(f"  Message ID: {result.id}")
                print(f"  Chat ID: {result.chat_id}")
                return result
            return None
        except Exception as e:
            self.log(f"Failed to send plain message: {e}", success=False)
            traceback.print_exc()
            return None

    async def test_send_formatted_message(self):
        """Test sending formatted messages using the format system."""
        self.section("Test: Send Formatted Message (HTML)")

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

            # Render for Telegram (HTML format)
            content = msg.render(Format.HTML)
            print(f"  Rendered content:\n{content[:200]}...")

            result = await self.backend.send_message(self.chat_id, content)
            self.log("Sent formatted message with bold, italic, code (HTML)")

            return result
        except Exception as e:
            self.log(f"Failed to send formatted message: {e}", success=False)
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
            elif self.user_name:
                user_mention = f"@{self.user_name}"
            elif self.user_id:
                user_mention = f'<a href="tg://user?id={self.user_id}">User</a>'
            else:
                user_mention = "@unknown"

            # Channel mention
            if channel:
                channel_mention = self.backend.mention_channel(channel)
                print(f"  Channel mention format: {channel_mention}")
            else:
                channel_mention = f"#{self.chat_id}"

            # Build message with mentions
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] Mentions:\n")
                .add_text(f"  User: {user_mention}\n")
                .add_text(f"  Channel: {channel_mention}\n")
                .add_text("  Note: Telegram mentions use @username or HTML links")
            )
            await self.backend.send_message(self.chat_id, msg.render(Format.HTML))
            self.log("Sent message with user and channel mentions")

        except Exception as e:
            self.log(f"Failed to test mentions: {e}", success=False)
            traceback.print_exc()

    async def test_reactions(self, message):
        """Test adding and removing reactions."""
        self.section("Test: Reactions")

        if not message:
            # Send a message to react to
            message = await self.backend.send_message(
                self.chat_id,
                "🧪 [E2E Test] React to this message! Bot will add reactions...",
                parse_mode=None,
            )

        if not message:
            self.log("No message to add reactions to", success=False)
            return

        try:
            # Add reactions (Telegram uses unicode emoji via setMessageReaction)
            # Note: Available reactions depend on the chat settings
            reactions = ["👍", "❤️", "🎉"]
            for emoji in reactions:
                try:
                    await self.backend.add_reaction(message, emoji, self.chat_id)
                    print(f"  Added reaction: {emoji}")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"  Failed to add {emoji}: {e}")

            self.log(f"Attempted {len(reactions)} reactions")

            # Wait a moment then remove reactions
            await asyncio.sleep(2)
            try:
                await self.backend.remove_reaction(message, "👍", self.chat_id)
                self.log("Removed reactions (set empty list)")
            except Exception as e:
                print(f"  Remove reaction failed: {e}")
                self.log("Remove reaction attempted (may not be supported in this chat)")

        except Exception as e:
            self.log(f"Failed to test reactions: {e}", success=False)
            traceback.print_exc()

    async def test_replies(self):
        """Test message replies using reply_to."""
        self.section("Test: Message Replies")

        try:
            # Send a message that will receive a reply
            result = await self.backend.send_message(
                self.chat_id,
                "🧪 [E2E Test] Original message - will receive a reply",
                parse_mode=None,
            )

            if result:
                print(f"  Original message ID: {result.id}")

                # Send reply using reply_to kwarg
                reply_result = await self.backend.send_message(
                    self.chat_id,
                    "🧪 [E2E Test] This is a reply to the above message!",
                    reply_to=result,
                    parse_mode=None,
                )
                if reply_result:
                    self.log("Sent reply to message")
                    print(f"  Reply message ID: {reply_result.id}")

                    # Also test as_reply() convenience method
                    reply_msg = result.as_reply("🧪 [E2E Test] Reply via as_reply() convenience!")
                    print(f"  as_reply() thread: {reply_msg.thread}")
                    reply_result2 = await self.backend.send_message(
                        self.chat_id,
                        reply_msg.content,
                        reply_to=result.id,
                        parse_mode=None,
                    )
                    if reply_result2:
                        self.log("Sent reply using as_reply() convenience")
                    else:
                        self.log("as_reply() convenience failed", success=False)
                else:
                    self.log("Reply failed", success=False)
            else:
                self.log("Failed to send original message for reply test", success=False)

        except Exception as e:
            self.log(f"Failed to test replies: {e}", success=False)
            traceback.print_exc()

    async def test_rich_content(self):
        """Test sending rich content with tables."""
        self.section("Test: Rich Content (Tables)")

        try:
            # Create a message with a table using Table.from_data
            table = Table.from_data(
                data=[
                    ["Messages", "✅", "Working"],
                    ["Reactions", "✅", "Working"],
                    ["Mentions", "✅", "Working"],
                    ["Replies", "✅", "Working"],
                    ["Forwarding", "✅", "Working"],
                ],
                headers=["Feature", "Status", "Notes"],
            )

            # Telegram HTML doesn't support <table> tags, so render
            # the table as plaintext inside a <pre> block.
            content = f"🧪 [E2E Test] Rich Content (Table):\n\n<pre>{table.render(Format.PLAINTEXT)}</pre>"
            await self.backend.send_message(self.chat_id, content)
            self.log("Sent rich content with table")

        except Exception as e:
            self.log(f"Failed to test rich content: {e}", success=False)
            traceback.print_exc()

    async def test_fetch_messages(self):
        """Test fetching message history."""
        self.section("Test: Fetch Message History")

        try:
            messages = await self.backend.fetch_messages(self.chat_id, limit=10)
            print(f"  Fetched {len(messages)} messages")

            if len(messages) == 0:
                print("  Note: Telegram Bot API does not support fetching message history.")
                print("  This is a known limitation - bots can only receive real-time messages.")
                self.log("Fetch messages returned empty (Telegram API limitation - expected)")
            else:
                self.log(f"Fetched {len(messages)} messages")
                for msg in messages[:5]:
                    content_preview = (msg.content or "")[:50].replace("\n", " ")
                    print(f"  - [{msg.id}] {content_preview}...")

        except Exception as e:
            self.log(f"Failed to fetch messages: {e}", success=False)
            traceback.print_exc()

    async def test_presence(self, user):
        """Test presence (limited for Telegram)."""
        self.section("Test: Presence")

        try:
            # Get presence
            if user:
                presence = await self.backend.get_presence(user.id)
                if presence:
                    print(f"  User presence status: {presence.status}")
                    self.log("Fetched user presence")
                else:
                    print("  Presence returned None (expected for Telegram)")
                    self.log("Presence not available (Telegram limitation - expected)")
            else:
                print("  No user to check presence for")
                self.log("Presence check skipped (no user)")

            # Set presence (no-op for Telegram)
            await self.backend.set_presence(
                status="online",
                status_text="Running E2E Tests",
            )
            print("  set_presence() called (no-op for Telegram bots)")
            self.log("Set presence called (no-op for Telegram - expected)")

        except Exception as e:
            self.log(f"Failed to test presence: {e}", success=False)
            traceback.print_exc()

    async def test_dm_creation(self):
        """Test DM creation using Channel.dm_to() convenience method."""
        self.section("Test: DM Creation (using Channel.dm_to)")

        try:
            # In Telegram, DM chat_id = user_id
            # The bot must have been contacted by the user first

            test_user = None
            if self.user_id:
                test_user = await self.backend.fetch_user(self.user_id)

            if test_user:
                # Method 1: Use Channel.dm_to() convenience method
                print(f"\n  Method 1: Using Channel.dm_to({test_user.display_name})...")
                dm_channel = Channel.dm_to(test_user)
                print(f"    Created incomplete DM channel: {dm_channel}")
                print(f"    Channel type: {dm_channel.channel_type}")
                print(f"    Users: {[u.display_name for u in dm_channel.users]}")
                print(f"    Is incomplete: {dm_channel.is_incomplete}")

                # Send message to DM
                msg = (
                    FormattedMessage()
                    .add_text("🧪 [E2E Test] DM via Channel.dm_to() convenience\n")
                    .add_text(f"Created at: {datetime.now().isoformat()}")
                )
                await self.backend.send_message(dm_channel, msg.render(Format.HTML))
                self.log("Sent DM using Channel.dm_to()")

                # Method 2: Use create_dm directly
                print(f"\n  Method 2: Using create_dm([{self.user_id}]) directly...")
                dm_chat_id = await self.backend.create_dm([self.user_id])
                if dm_chat_id:
                    self.log(f"Created DM via create_dm(): {dm_chat_id}")
                    print(f"  Note: In Telegram, DM chat_id = user_id ({dm_chat_id})")

                    # Send a message to the DM
                    msg2 = FormattedMessage().add_text("🧪 [E2E Test] DM via create_dm()\n").add_text(f"Created at: {datetime.now().isoformat()}")
                    await self.backend.send_message(dm_chat_id, msg2.render(Format.HTML))
                    self.log("Sent message to DM")
                else:
                    self.log("create_dm() returned no chat ID", success=False)
            else:
                print("  Skipping DM test - no user available")
                print("  Set TELEGRAM_TEST_USER_ID to a user who has messaged the bot")
                self.log("DM test skipped (no user ID)")

        except Exception as e:
            self.log(f"Failed to test DM creation: {e}", success=False)
            traceback.print_exc()

    async def test_dm_reply_convenience(self):
        """Test as_dm_to_author() convenience method."""
        self.section("Test: as_dm_to_author() Convenience")

        try:
            # We need a message from a known user to test this.
            # Since Telegram doesn't have message history, we'll wait for
            # the inbound message test to populate a user, or use the bot user.

            # For now, create a synthetic message to demonstrate the API
            if self.user_id:
                from chatom.telegram import TelegramMessage, TelegramUser

                test_user = TelegramUser(
                    id=self.user_id,
                    name=self.user_name or "Test User",
                    handle=self.user_name or "",
                    username=self.user_name or "",
                )

                source_message = TelegramMessage(
                    id="1",
                    content="Test message for DM reply",
                    author=test_user,
                    channel=await self.backend.fetch_channel(self.chat_id),
                    chat_id=self.chat_id,
                )

                # Use as_dm_to_author()
                dm_message = source_message.as_dm_to_author(
                    f"🧪 [E2E Test] DM reply via as_dm_to_author()\nThis is a response to your message.\nCreated at: {datetime.now().isoformat()}"
                )

                print(f"  DM message channel type: {dm_message.channel.channel_type}")
                print(f"  DM message users: {[u.display_name for u in dm_message.channel.users]}")
                print(f"  DM message is incomplete: {dm_message.channel.is_incomplete}")

                # Send the DM (user_id is the chat_id for Telegram DMs)
                await self.backend.send_message(self.user_id, dm_message.content)
                self.log("Sent DM using as_dm_to_author() convenience")
            else:
                print("  Skipping as_dm_to_author test - no user ID")
                self.log("as_dm_to_author test skipped (no user ID)")

        except Exception as e:
            self.log(f"Failed to test as_dm_to_author: {e}", success=False)
            traceback.print_exc()

    async def test_forwarding(self):
        """Test message forwarding using forward_message()."""
        self.section("Test: Message Forwarding")

        try:
            # Send a message to forward
            source = await self.backend.send_message(
                self.chat_id,
                "🧪 [E2E Test] This message will be forwarded",
                parse_mode=None,
            )

            if source:
                print(f"  Source message: {source.id}")

                # Forward to the same chat (for testing)
                forwarded = await self.backend.forward_message(
                    source,
                    self.chat_id,
                    include_attribution=True,
                    prefix="📤 ",
                )
                if forwarded:
                    self.log("Forwarded message with attribution")
                    print(f"  Forwarded message ID: {forwarded.id}")
                else:
                    self.log("Forward returned None", success=False)
            else:
                self.log("No source message to forward", success=False)

        except Exception as e:
            self.log(f"Failed to test forwarding: {e}", success=False)
            traceback.print_exc()

    async def test_edit_message(self):
        """Test editing a message."""
        self.section("Test: Edit Message")

        try:
            # Send a message to edit
            original = await self.backend.send_message(
                self.chat_id,
                "🧪 [E2E Test] Original message - will be edited",
                parse_mode=None,
            )

            if original:
                print(f"  Original message ID: {original.id}")
                await asyncio.sleep(1)

                # Edit the message
                edited = await self.backend.edit_message(
                    original,
                    "🧪 [E2E Test] ✏️ This message has been EDITED!",
                    self.chat_id,
                    parse_mode=None,
                )
                if edited:
                    self.log("Edited message successfully")
                    print(f"  Edited content: {edited.content[:50]}...")
                else:
                    self.log("Edit returned None", success=False)
            else:
                self.log("Failed to send original message for edit test", success=False)

        except Exception as e:
            self.log(f"Failed to test edit: {e}", success=False)
            traceback.print_exc()

    async def test_delete_message(self):
        """Test deleting a message."""
        self.section("Test: Delete Message")

        try:
            # Send a message to delete
            msg = await self.backend.send_message(
                self.chat_id,
                "🧪 [E2E Test] This message will be DELETED in 2 seconds...",
                parse_mode=None,
            )

            if msg:
                print(f"  Message ID to delete: {msg.id}")
                await asyncio.sleep(2)

                await self.backend.delete_message(msg, self.chat_id)
                self.log("Deleted message successfully")
            else:
                self.log("Failed to send message for delete test", success=False)

        except Exception as e:
            self.log(f"Failed to test delete: {e}", success=False)
            traceback.print_exc()

    async def test_group_dm(self):
        """Test multi-person group DM concept."""
        self.section("Test: Group DM (Multi-Person)")

        try:
            print("  Note: Telegram group DMs are regular group chats.")
            print("  Bots cannot create groups; they must be added by users.")
            print("  Demonstrating Channel.group_dm_to() API:")

            if self.user_id:
                from chatom.telegram import TelegramUser

                user1 = TelegramUser(
                    id=self.user_id,
                    name=self.user_name or "User 1",
                    handle=self.user_name or "",
                    username=self.user_name or "",
                )
                user2 = TelegramUser(
                    id="999999999",
                    name="User 2",
                    handle="user2",
                    username="user2",
                )

                group_dm = Channel.group_dm_to([user1, user2])
                print(f"  Group DM channel type: {group_dm.channel_type}")
                print(f"  Is incomplete: {group_dm.is_incomplete}")
                print(f"  Users: {[u.display_name for u in group_dm.users]}")
                self.log("Group DM API demonstrated (Telegram bots cannot create groups)")
            else:
                self.log("Group DM test skipped (no user ID)")

        except Exception as e:
            self.log(f"Failed to test group DM: {e}", success=False)
            traceback.print_exc()

    async def test_file_attachment(self):
        """Test sending a file attachment."""
        self.section("Test: File Attachment")

        try:
            # Create a temporary text file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write("This is a test file created by the chatom Telegram E2E test suite.\n")
                f.write(f"Created at: {datetime.now().isoformat()}\n")
                f.write("This file can be safely deleted.\n")
                temp_file_path = f.name

            print(f"  Created temp file: {temp_file_path}")

            try:
                # Use Telegram's sendDocument API
                with open(temp_file_path, "rb") as doc:
                    result = await self.backend._bot.send_document(
                        chat_id=int(self.chat_id),
                        document=doc,
                        caption="🧪 [E2E Test] File attachment test",
                    )

                if result:
                    self.log("Uploaded file attachment successfully")
                    print(f"  Message ID: {result.message_id}")
                    print(f"  Document: {result.document}")
                else:
                    self.log("File upload failed", success=False)

            finally:
                os.unlink(temp_file_path)

        except Exception as e:
            self.log(f"Failed to test file attachment: {e}", success=False)
            traceback.print_exc()

    async def test_inbound_messages(self):
        """Test receiving inbound messages.

        Uses Telegram's getUpdates long-polling to receive real-time messages.
        """
        self.section("Test: Inbound Messages (Interactive)")

        try:
            received_message = None

            async def receive_one_message():
                nonlocal received_message
                print("  [receive_one_message] Starting to iterate stream_messages...")
                async for message in self.backend.stream_messages(channel=self.chat_id):
                    print(f"  [receive_one_message] Got message: {message}")
                    received_message = message
                    return
                print("  [receive_one_message] stream_messages ended without message")

            # Start receiving in background
            print("  Creating receive task...")
            receive_task = asyncio.create_task(receive_one_message())

            # Give the polling a moment to initialize
            await asyncio.sleep(2)

            # Prompt user
            bot_name = self.bot_user_name or "the bot"
            prompt_msg = (
                FormattedMessage()
                .add_text("🧪 ")
                .add_bold("[E2E Test] Inbound Message Test")
                .add_text("\n\nPlease send a message in this chat.\n")
                .add_text(f"Example: @{bot_name} hello this is a test message\n\n")
                .add_text("You have ")
                .add_bold("30 seconds")
                .add_text(" to respond...")
            )
            await self.backend.send_message(self.chat_id, prompt_msg.render(Format.HTML))
            print("\n  ⏳ Waiting for you to send a message...")
            print(f"     Example: @{bot_name} hello test")

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
                if received_message.author:
                    print(f"     From: {received_message.author.display_name} (ID: {received_message.author.id})")

                    # Cache the user for future tests
                    if not self.user_id:
                        self.user_id = received_message.author.id
                        print(f"     (Discovered user ID: {self.user_id})")
                print(f"     Text: {(received_message.content or '')[:200]}...")

                # Check if the bot was mentioned
                if received_message.mentions_user(User(id=self.bot_user_id)):
                    self.log("Bot mention detected in message")
                else:
                    print("     (Bot mention not found, but message was received)")

                # Test to_formatted() on the received message
                if hasattr(received_message, "to_formatted"):
                    formatted = received_message.to_formatted()
                    plain = formatted.render(Format.PLAINTEXT)
                    print(f"     Formatted (plaintext): {plain[:100]}...")
                    self.log("Successfully converted inbound message to FormattedMessage")

                # Send acknowledgment
                ack_msg = (
                    FormattedMessage()
                    .add_text("✅ ")
                    .add_bold("Message received!")
                    .add_text("\n\nI heard you say: ")
                    .add_italic((received_message.content or "")[:100])
                )
                await self.backend.send_message(self.chat_id, ack_msg.render(Format.HTML))
            else:
                self.log("Message received but was None", success=False)

        except Exception as e:
            self.log(f"Failed to test inbound messages: {e}", success=False)
            traceback.print_exc()

    async def test_bot_info(self):
        """Test getting bot info."""
        self.section("Test: Bot Info (getMe)")

        try:
            bot_user = await self.backend.get_bot_info()
            if bot_user:
                self.log(f"Got bot info: {bot_user.display_name}")
                print(f"  Bot ID: {bot_user.id}")
                print(f"  Name: {bot_user.name}")
                print(f"  Username: {getattr(bot_user, 'username', 'N/A')}")
                print(f"  Is Bot: {getattr(bot_user, 'is_bot', 'N/A')}")
                return bot_user
            else:
                self.log("Failed to get bot info", success=False)
                return None
        except Exception as e:
            self.log(f"Failed to get bot info: {e}", success=False)
            traceback.print_exc()
            return None

    async def cleanup(self):
        """Clean up and disconnect."""
        self.section("Cleanup")

        if self.backend and self.backend.connected:
            await self.backend.disconnect()
            self.log("Disconnected from Telegram")

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
        print("  Telegram End-to-End Integration Test")
        print("=" * 60)

        try:
            await self.setup()
            await self.test_connection()

            # Get bot info
            await self.test_bot_info()

            # Look up chat by name or ID
            self.chat_id = await self.lookup_chat()
            if not self.chat_id:
                print("\n❌ Cannot continue without a chat.")
                print("   Options:")
                print("   1. Set TELEGRAM_TEST_CHAT_NAME to the group's public @username")
                print("   2. Set TELEGRAM_TEST_CHAT_ID to the numeric chat ID")
                print("   3. Send a message in the group and re-run (discover_chats will find it)")
                return False

            # Fetch channel details
            channel = await self.test_fetch_channel()

            # Fetch user (may not work without prior interaction)
            user = await self.test_fetch_user()

            # Test messaging
            message = await self.test_send_plain_message()
            await self.test_send_formatted_message()
            await self.test_mentions(user, channel)

            # Test reactions
            await self.test_reactions(message)

            # Test replies
            await self.test_replies()

            # Test rich content
            await self.test_rich_content()

            # Test edit message
            await self.test_edit_message()

            # Test delete message
            await self.test_delete_message()

            # Test history (limited for Telegram)
            await self.test_fetch_messages()

            # Test presence (limited for Telegram)
            await self.test_presence(user)

            # Test forwarding
            await self.test_forwarding()

            # Test file attachment
            await self.test_file_attachment()

            # Test inbound messages (interactive - prompts user)
            # Run before DM tests so user_id can be discovered
            await self.test_inbound_messages()

            # Test DM creation (needs user_id, possibly discovered above)
            await self.test_dm_creation()

            # Test as_dm_to_author convenience
            await self.test_dm_reply_convenience()

            # Test group DM concept
            await self.test_group_dm()

        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            traceback.print_exc()

        finally:
            await self.cleanup()

        return self.print_summary()


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  Telegram E2E Integration Test")
    print("=" * 60)
    print("\nThis test requires:")
    print("  - TELEGRAM_TOKEN: Your Telegram bot token (from @BotFather)")
    print("  - TELEGRAM_TEST_USER_NAME: Username for mention tests (without @)")
    print("\nChat lookup (at least one recommended):")
    print("  - TELEGRAM_TEST_CHAT_NAME: Public @username of the group (without @)")
    print("  - TELEGRAM_TEST_CHAT_ID: Numeric chat ID (works for private groups)")
    print("  - If neither is set, will try to discover chats from recent bot updates")
    print("\nOptional:")
    print("  - TELEGRAM_TEST_USER_ID: User ID for DM and mention tests")
    print("\nRequired Telegram bot setup:")
    print("  1. Create a bot via @BotFather")
    print("  2. Add the bot to a group chat")
    print("  3. Make the group public with a username, or get its numeric chat ID")
    print("  4. Ensure the bot has permission to send messages")
    print("\nTelegram Bot API limitations:")
    print("  - No message history access (fetch_messages returns empty)")
    print("  - No user presence information")
    print("  - Users must message the bot first for DM to work")
    print("  - Reactions depend on chat settings (may be restricted)")
    print("\nThe bot will send messages to the test chat.")
    print("Please watch the chat and interact when prompted.\n")

    test = TelegramE2ETest()
    success = await test.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
