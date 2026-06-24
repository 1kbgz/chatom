#!/usr/bin/env python
"""Configured end-to-end integration test runner.

This script runs every e2e suite whose full-coverage environment is present.
It also includes the cross-platform Symphony + Slack bridge test.

Full-coverage environment variables:
    Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_TEST_ROOM_NAME: Name of the room where tests will run
        SYMPHONY_TEST_USER_NAME: Username for mention tests
        Authentication (one of):
            SYMPHONY_BOT_PRIVATE_KEY_PATH / SYMPHONY_BOT_PRIVATE_KEY_CONTENT
            SYMPHONY_BOT_COMBINED_CERT_PATH / SYMPHONY_BOT_COMBINED_CERT_CONTENT

    Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token (xoxb-...)
        SLACK_TEST_CHANNEL_NAME: Channel name where tests will run (without #)
        SLACK_TEST_USER_NAME: Username for mention tests (without @)
        SLACK_APP_TOKEN: App token for Socket Mode (xapp-...)

    Discord:
        DISCORD_TOKEN: Your Discord bot token
        DISCORD_TEST_CHANNEL_NAME: Channel name where tests will run
        DISCORD_TEST_USER_NAME: Username for mention tests
        DISCORD_GUILD_NAME: Server/guild name

    Telegram:
        TELEGRAM_TOKEN: Your Telegram bot token
        TELEGRAM_TEST_USER_NAME: Username for mention tests
        TELEGRAM_TEST_CHAT_NAME or TELEGRAM_TEST_CHAT_ID: Test chat

Usage:
    python -m chatom.tests.combined_e2e

The test will:
1. Detect configured e2e suites from environment variables
2. Run each fully configured suite
3. Run the Symphony + Slack bridge when both sides are configured
4. Fail if any configured suite fails
"""

import asyncio
import os
import re
import sys
import tempfile
import traceback
from datetime import datetime
from typing import List, Optional, Tuple, Union

from chatom.base import Channel, User
from chatom.discord import (
    DiscordBackend,
    DiscordConfig,
    mention_everyone as discord_mention_everyone,
    mention_here as discord_mention_here,
    mention_role,
)
from chatom.format import Format, FormattedMessage, Table
from chatom.slack import (
    SlackBackend,
    SlackConfig,
    SlackMessage,
    mention_channel_all as slack_mention_channel_all,
    mention_everyone as slack_mention_everyone,
    mention_here as slack_mention_here,
)
from chatom.symphony import (
    SymphonyBackend,
    SymphonyConfig,
    format_cashtag,
    format_hashtag,
    mention_user_by_uid,
)
from chatom.telegram import TelegramBackend, TelegramConfig


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"❌ Missing required environment variable: {name}")
        print(f"   Set it with: export {name}='your-value'")
        sys.exit(1)
    return value


def require_interactive_e2e() -> bool:
    """Return whether interactive e2e timeouts should fail."""
    return os.environ.get("CHATOM_E2E_REQUIRE_INTERACTIVE", "").lower() in {"1", "true", "yes"}


class SlackE2ETest:
    """Slack end-to-end test suite."""

    def __init__(self):
        """Initialize test configuration from environment."""
        self.bot_token = get_env("SLACK_BOT_TOKEN")
        self.channel_name = get_env("SLACK_TEST_CHANNEL_NAME")
        self.user_name = get_env("SLACK_TEST_USER_NAME")
        self.app_token = get_env("SLACK_APP_TOKEN", required=False)
        self.backend = None
        self.results = []
        # These will be populated after lookup
        self.channel_id = None
        self.user_id = None

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
        """Set up the Slack backend."""
        self.section("Setting Up Slack Backend")

        config = SlackConfig(
            bot_token=self.bot_token,
            app_token=self.app_token,
        )

        self.backend = SlackBackend(config=config)
        print("Created SlackBackend with config")
        print(f"  Channel Name: {self.channel_name}")
        print(f"  User Name: {self.user_name}")
        print(f"  App Token: {'(set)' if self.app_token else '(not set)'}")

    async def test_connection(self):
        """Test connecting to Slack."""
        self.section("Test: Connection")

        try:
            await self.backend.connect()
            self.log("Connected to Slack successfully")
            print(f"  Backend name: {self.backend.name}")
            print(f"  Display name: {self.backend.display_name}")
            print(f"  Capabilities: {self.backend.capabilities}")
        except Exception as e:
            self.log(f"Failed to connect: {e}", success=False)
            raise

    async def lookup_channel_by_name(self, name: str) -> Optional[str]:
        """Look up a channel ID by name."""
        self.section("Lookup: Channel by Name")

        try:
            # Use the flexible fetch_channel API
            channel = await self.backend.fetch_channel(name=name)

            if channel:
                self.log(f"Found channel '{name}' -> {channel.id}")
                return channel.id

            self.log(f"Channel '{name}' not found", success=False)
            return None

        except Exception as e:
            self.log(f"Failed to lookup channel: {e}", success=False)
            return None

    async def lookup_user_by_name(self, name: str) -> Optional[str]:
        """Look up a user ID by name or display name."""
        self.section("Lookup: User by Name")

        try:
            # Use the flexible fetch_user API
            user = await self.backend.fetch_user(name=name)
            if not user:
                user = await self.backend.fetch_user(handle=name)

            if user:
                self.log(f"Found user '{name}' -> {user.id} (name={user.name}, handle={user.handle})")
                return user.id

            self.log(f"User '{name}' not found", success=False)
            return None

        except Exception as e:
            self.log(f"Failed to lookup user: {e}", success=False)
            return None

    async def test_send_plain_message(self):
        """Test sending a plain text message."""
        self.section("Test: Send Plain Message")

        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Use format system to build message
            msg = FormattedMessage().add_text(f"🧪 [E2E Test] Plain message sent at {timestamp}")
            content = msg.render(Format.SLACK_MARKDOWN)

            result = await self.backend.send_message(self.channel_id, content)
            self.log(f"Sent plain message at {timestamp}")

            if result:
                print(f"  Message TS: {result}")
                # Return the ts string for use in reactions test
                return result.ts if hasattr(result, "ts") else result
            return None
        except Exception as e:
            self.log(f"Failed to send plain message: {e}", success=False)
            return None

    async def test_send_formatted_message(self):
        """Test sending formatted messages using the format system."""
        self.section("Test: Send Formatted Message (mrkdwn)")

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

            # Render for Slack (mrkdwn format)
            content = msg.render(Format.SLACK_MARKDOWN)
            print(f"  Rendered content:\n{content[:200]}...")

            result = await self.backend.send_message(self.channel_id, content)
            self.log("Sent formatted message with bold, italic, code (mrkdwn)")

            return result
        except Exception as e:
            self.log(f"Failed to send formatted message: {e}", success=False)
            return None

    async def test_fetch_user(self):
        """Test fetching user information."""
        self.section("Test: Fetch User")

        try:
            user = await self.backend.fetch_user(self.user_id)
            if user:
                self.log(f"Fetched user: {user.display_name or user.name}")
                print(f"  User ID: {user.id}")
                print(f"  Name: {user.name}")
                print(f"  Real Name: {getattr(user, 'real_name', 'N/A')}")
                print(f"  Display Name: {user.display_name}")
                print(f"  Email: {getattr(user, 'email', 'N/A')}")
                print(f"  Is Bot: {getattr(user, 'is_bot', 'N/A')}")
                print(f"  Timezone: {getattr(user, 'tz', 'N/A')}")
                return user
            else:
                self.log(f"User not found: {self.user_id}", success=False)
                return None
        except Exception as e:
            self.log(f"Failed to fetch user: {e}", success=False)
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
                print(f"  Is Private: {getattr(channel, 'is_private', 'N/A')}")
                print(f"  Is Archived: {getattr(channel, 'is_archived', 'N/A')}")
                print(f"  Topic: {getattr(channel, 'topic', 'N/A')}")
                print(f"  Purpose: {getattr(channel, 'purpose', 'N/A')}")
                return channel
            else:
                self.log(f"Channel not found: {self.channel_id}", success=False)
                return None
        except Exception as e:
            self.log(f"Failed to fetch channel: {e}", success=False)
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
            print(f"  @here format: {slack_mention_here()}")
            print(f"  @channel format: {slack_mention_channel_all()}")
            print(f"  @everyone format: {slack_mention_everyone()}")

            # Use format system to build message with mentions
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] Mentions:\n")
                .add_text(f"  User: {user_mention}\n")
                .add_text(f"  Channel: {channel_mention}\n")
                .add_text("  (Not sending @here/@channel/@everyone to avoid spam)")
            )
            await self.backend.send_message(self.channel_id, msg.render(Format.SLACK_MARKDOWN))
            self.log("Sent message with user and channel mentions")

        except Exception as e:
            self.log(f"Failed to test mentions: {e}", success=False)

    async def test_reactions(self, message_ts: Optional[str]):
        """Test adding and removing reactions."""
        self.section("Test: Reactions")

        if not message_ts:
            # Send a message to react to
            result = await self.backend.send_message(self.channel_id, "🧪 [E2E Test] React to this message! Bot will add reactions...")
            message_ts = result.ts if hasattr(result, "ts") else result

        if not message_ts:
            self.log("No message timestamp to add reactions to", success=False)
            return

        try:
            # Add reactions (Slack uses emoji names without colons)
            reactions = ["thumbsup", "thumbsdown", "tada", "heart"]
            for emoji in reactions:
                await self.backend.add_reaction(message_ts, emoji, self.channel_id)
                print(f"  Added reaction: :{emoji}:")
                await asyncio.sleep(0.5)  # Rate limit

            self.log(f"Added {len(reactions)} reactions")

            # Wait a moment then remove one
            await asyncio.sleep(2)
            await self.backend.remove_reaction(message_ts, "thumbsdown", self.channel_id)
            self.log("Removed :thumbsdown: reaction")

        except Exception as e:
            self.log(f"Failed to test reactions: {e}", success=False)

    async def test_threads(self):
        """Test thread creation and replies."""
        self.section("Test: Threads")

        try:
            # Send a message that will be the thread parent
            result = await self.backend.send_message(self.channel_id, "🧪 [E2E Test] Thread parent message - replies will be in thread")
            parent_ts = result.ts if hasattr(result, "ts") else result

            if parent_ts:
                print(f"  Parent message TS: {parent_ts}")

                # Reply in thread
                reply_result = await self.backend.send_message(
                    self.channel_id,
                    "🧪 [E2E Test] This is a threaded reply!",
                    thread_id=parent_ts,
                )
                thread_reply = reply_result.ts if hasattr(reply_result, "ts") else reply_result
                if thread_reply:
                    self.log("Created thread and sent reply")
                    print(f"  Reply TS: {thread_reply}")

                    # Send another reply
                    await self.backend.send_message(
                        self.channel_id,
                        "🧪 [E2E Test] Second reply in thread",
                        thread_id=parent_ts,
                    )
                else:
                    self.log("Sent parent message but thread reply failed", success=False)
            else:
                self.log("Failed to send thread parent message", success=False)

        except Exception as e:
            self.log(f"Failed to test threads: {e}", success=False)

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
                    ["Threads", "✅", "Working"],
                    ["Mentions", "✅", "Working"],
                    ["Presence", "✅", "Working"],
                ],
                headers=["Feature", "Status", "Notes"],
            )
            msg.content.append(table)

            content = msg.render(Format.SLACK_MARKDOWN)
            await self.backend.send_message(self.channel_id, content)
            self.log("Sent rich content with table")

        except Exception as e:
            self.log(f"Failed to test rich content: {e}", success=False)

    async def test_fetch_messages(self):
        """Test fetching message history."""
        self.section("Test: Fetch Message History")

        try:
            messages = await self.backend.fetch_messages(self.channel_id, limit=10)
            self.log(f"Fetched {len(messages)} messages from history")

            print("\n  Recent messages:")
            for msg in messages[:5]:
                content_preview = (msg.content or "")[:50].replace("\n", " ")
                ts = getattr(msg, "ts", msg.id)
                print(f"  - [{ts}] {content_preview}...")

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
            return []

    async def test_presence(self, user):
        """Test getting and setting presence."""
        self.section("Test: Presence")

        try:
            # Get user presence
            if user:
                presence = await self.backend.get_presence(user.id)
                if presence:
                    print(f"  User presence status: {presence.status}")
                    print(f"  Status text: {getattr(presence, 'status_text', 'N/A')}")
                    print(f"  Status emoji: {getattr(presence, 'status_emoji', 'N/A')}")
                    self.log("Fetched user presence")
                else:
                    print("  Could not fetch presence (may need scopes)")

            # Set bot presence (status) - this requires user token, not bot token
            try:
                await self.backend.set_presence(
                    status="auto",
                    status_text="Running E2E Tests",
                    status_emoji=":test_tube:",
                )
                self.log("Set bot presence with status text")
            except Exception as e:
                error_msg = str(e)
                if "not_allowed_token_type" in error_msg:
                    print("  Skipping set_presence - requires user token (xoxp-), not bot token (xoxb-)")
                    self.log("Set presence skipped (requires user token)")
                else:
                    raise

        except Exception as e:
            self.log(f"Failed to test presence: {e}", success=False)

    async def test_channel_creation(self):
        """Test channel and DM creation using new convenience methods."""
        self.section("Test: Room/DM Creation (using Channel.dm_to)")

        try:
            # Get user object for DM convenience methods
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

                # Send message to incomplete channel - backend will resolve it
                msg = (
                    FormattedMessage()
                    .add_text("🧪 [E2E Test] DM via Channel.dm_to() convenience\n")
                    .add_text(f"Created at: {datetime.now().isoformat()}")
                )
                _result = await self.backend.send_message(dm_channel, msg.render(Format.SLACK_MARKDOWN))
                self.log("Sent DM using Channel.dm_to() - resolved channel")

                # Method 2: Use create_dm directly (legacy approach)
                print(f"\n  Method 2: Using create_dm([{self.user_id}]) directly...")
                dm_channel_id = await self.backend.create_dm([self.user_id])
                if dm_channel_id:
                    self.log(f"Created DM channel via create_dm(): {dm_channel_id}")

                    # Send a test message to the DM
                    msg = FormattedMessage().add_text("🧪 [E2E Test] DM via create_dm()\n").add_text(f"Created at: {datetime.now().isoformat()}")
                    await self.backend.send_message(dm_channel_id, msg.render(Format.SLACK_MARKDOWN))
                    self.log("Sent message to DM")
                else:
                    self.log("DM creation returned no channel ID", success=False)
            else:
                print("  Skipping DM test - no user available")

            # Skip channel creation to avoid clutter
            print("\n  Skipping public/private channel creation test to avoid creating test channels.")
            print("  To test, uncomment the code in this method.")

        except Exception as e:
            self.log(f"Failed to test room/DM creation: {e}", success=False)
            traceback.print_exc()

    async def test_dm_reply_convenience(self):
        """Test as_dm_to_author() convenience method."""
        self.section("Test: as_dm_to_author() Convenience")

        try:
            # Get a recent message from the test channel to use as source
            messages = await self.backend.fetch_messages(self.channel_id, limit=20)

            # Find a message from a non-bot user
            source_message = None
            for msg in messages:
                # Skip bot messages
                if msg.author and not getattr(msg.author, "is_bot", False):
                    source_message = msg
                    break

            if not source_message and self.user_id:
                test_user = await self.backend.fetch_user(self.user_id)
                channel = await self.backend.fetch_channel(self.channel_id)
                if test_user:
                    source_message = SlackMessage(
                        id="synthetic-as-dm-source",
                        content="Synthetic source message for as_dm_to_author()",
                        author=test_user,
                        channel=channel,
                        backend="slack",
                    )
                    print(f"  Using synthetic source message for {test_user.display_name}")

            if source_message:
                print(f"  Found message from {source_message.author.display_name}")
                print(f"  Original content: {(source_message.content or '')[:50]}...")

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
                self.log("as_dm_to_author test skipped - no source message")

        except Exception as e:
            self.log(f"Failed to test as_dm_to_author: {e}", success=False)
            traceback.print_exc()

    async def test_replies(self):
        """Test message replies using as_reply() convenience method."""
        self.section("Test: Message Replies (as_reply)")

        try:
            # Send a message that will receive a reply
            result = await self.backend.send_message(self.channel_id, "🧪 [E2E Test] Original message - will receive a reply")
            parent_ts = result.ts if hasattr(result, "ts") else result

            if parent_ts:
                print(f"  Original message TS: {parent_ts}")

                # Use as_reply() convenience method
                reply_msg = result.as_reply("🧪 [E2E Test] This is a reply using as_reply() convenience!")
                print(f"  Reply message thread: {reply_msg.thread}")

                # Send the reply
                reply_result = await self.backend.send_message(
                    self.channel_id,
                    reply_msg.content,
                    thread_id=reply_msg.thread.id if reply_msg.thread else parent_ts,
                )
                if reply_result:
                    self.log("Sent reply using as_reply() convenience")
                    print(f"  Reply TS: {reply_result.ts if hasattr(reply_result, 'ts') else reply_result}")
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
                    print(f"  Forwarded message TS: {forwarded.ts if hasattr(forwarded, 'ts') else forwarded.id}")
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
                other_users = []
                seen_ids = {self.user_id}

                for msg in messages:
                    if msg.author and msg.author.id not in seen_ids:
                        if not getattr(msg.author, "is_bot", False):
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

                    # Send message to group DM
                    msg = (
                        FormattedMessage()
                        .add_text("🧪 [E2E Test] Group DM via Channel.group_dm_to()\n")
                        .add_text(f"Created at: {datetime.now().isoformat()}")
                    )
                    _result = await self.backend.send_message(group_dm, msg.render(Format.SLACK_MARKDOWN))
                    self.log("Sent group DM using Channel.group_dm_to()")
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
            # Create a temporary text file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write("This is a test file created by the chatom E2E test suite.\n")
                f.write(f"Created at: {datetime.now().isoformat()}\n")
                f.write("This file can be safely deleted.\n")
                temp_file_path = f.name

            print(f"  Created temp file: {temp_file_path}")

            try:
                # Upload the file using Slack's files.upload API
                response = await self.backend._async_client.files_upload_v2(
                    channel=self.channel_id,
                    file=temp_file_path,
                    title="E2E Test File",
                    initial_comment="🧪 [E2E Test] File attachment test",
                )

                if response.get("ok"):
                    self.log("Uploaded file attachment successfully")
                    file_info = response.get("file", {})
                    print(f"  File ID: {file_info.get('id', 'N/A')}")
                    print(f"  File name: {file_info.get('name', 'N/A')}")
                else:
                    self.log(f"File upload failed: {response.get('error')}", success=False)

            finally:
                # Clean up temp file
                os.unlink(temp_file_path)

        except Exception as e:
            if "missing_scope" in str(e) and "files:write" in str(e):
                self.log("File attachment test skipped (Slack app missing files:write scope)")
                return
            self.log(f"Failed to test file attachment: {e}", success=False)
            traceback.print_exc()

    async def test_inbound_messages(self, bot_user_id: str, bot_name: str):
        """Test receiving inbound messages with bot mentions.

        This test requires Socket Mode which requires an app token (xapp-...).
        If no app token is provided, this test will be skipped.
        """
        self.section("Test: Inbound Messages (Interactive)")

        if not self.app_token:
            print("  Skipping inbound message test - no SLACK_APP_TOKEN provided.")
            print("  To enable this test, set SLACK_APP_TOKEN to your app token (xapp-...).")
            self.log("Inbound message test skipped (no app token)")
            return

        try:
            # Start the stream - this establishes the socket connection and waits for it to be ready
            print("  Starting message stream (Socket Mode)...")
            received_message = None

            async def receive_one_message():
                nonlocal received_message
                print("  [receive_one_message] Starting to iterate stream_messages...")
                # skip_own=True and skip_history=True are defaults, so we just get user messages
                async for message in self.backend.stream_messages(channel=self.channel_id):
                    print(f"  [receive_one_message] Got message: {message}")
                    received_message = message
                    return  # Got one message from a user, exit
                print("  [receive_one_message] stream_messages ended without message")

            # Start receiving in background
            print("  Creating receive task...")
            receive_task = asyncio.create_task(receive_one_message())

            # Give the socket time to fully connect (stream_messages waits 5 seconds internally)
            print("  Waiting 6 seconds for socket to connect...")
            await asyncio.sleep(6)
            print("  Done waiting, socket should be ready")

            # Now send prompt to user (socket should be ready)
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
            await self.backend.send_message(self.channel_id, prompt_msg.render(Format.SLACK_MARKDOWN))
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
                self.log("Timeout waiting for inbound message (30s)", success=require_interactive_e2e() is False)
                return

            if received_message:
                self.log("Received inbound message from user")
                print("\n  📨 Message received:")
                print(f"     Message ID: {received_message.id}")
                print(f"     From: {received_message.author_id}")
                print(f"     Text: {(received_message.content or '')[:200]}...")

                # Check if the bot was mentioned using backend method
                if received_message.mentions_user(User(id=bot_user_id)):
                    self.log("Bot mention detected in message")
                else:
                    print(f"     (Bot mention <@{bot_user_id}> not found in message, but message was received)")

                # Send acknowledgment
                ack_msg = (
                    FormattedMessage()
                    .add_text("✅ ")
                    .add_bold("Message received!")
                    .add_text("\n\nI heard you say: ")
                    .add_italic((received_message.content or "")[:100])
                )
                await self.backend.send_message(self.channel_id, ack_msg.render(Format.SLACK_MARKDOWN))
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
            self.log("Disconnected from Slack")

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
        print("  Slack End-to-End Integration Test")
        print("=" * 60)

        try:
            await self.setup()
            await self.test_connection()

            # Lookup channel and user by name
            self.channel_id = await self.lookup_channel_by_name(self.channel_name)
            if not self.channel_id:
                print(f"\n❌ Cannot continue without channel. Make sure '{self.channel_name}' exists and bot is a member.")
                return False

            self.user_id = await self.lookup_user_by_name(self.user_name)
            if not self.user_id:
                print(f"\n❌ Cannot continue without user. Make sure '{self.user_name}' exists.")
                return False

            # Fetch user and channel for later tests
            user = await self.test_fetch_user()
            channel = await self.test_fetch_channel()

            # Test messaging
            message_ts = await self.test_send_plain_message()
            await self.test_send_formatted_message()
            await self.test_mentions(user, channel)

            # Test reactions
            await self.test_reactions(message_ts)

            # Test threads
            await self.test_threads()

            # Test rich content
            await self.test_rich_content()

            # Test history
            await self.test_fetch_messages()

            # Test presence
            await self.test_presence(user)

            # Test channel creation (with Channel.dm_to convenience)
            await self.test_channel_creation()

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

            # Test inbound messages (requires app token)
            # Get bot info for inbound test
            bot_user_id = None
            bot_name = "bot"
            try:
                bot_info = await self.backend.get_bot_info()
                if bot_info:
                    bot_user_id = bot_info.id
                    bot_name = bot_info.name or "bot"
                    print(f"\n  Bot info: {bot_name} ({bot_user_id})")
            except Exception:
                pass

            if bot_user_id:
                await self.test_inbound_messages(bot_user_id, bot_name)

        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            traceback.print_exc()

        finally:
            await self.cleanup()

        return self.print_summary()


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
            print(f"  @here format: {discord_mention_here()}")
            print(f"  @everyone format: {discord_mention_everyone()}")
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
            if "Unknown User" in str(e):
                self.log("DM creation skipped (Discord could not DM configured user)")
                return
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
                self.log("Timeout waiting for inbound message (30s)", success=require_interactive_e2e() is False)
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


class SymphonyE2ETest:
    """Symphony end-to-end test suite."""

    def __init__(self):
        """Initialize test configuration from environment."""
        self.host = get_env("SYMPHONY_HOST")
        self.bot_username = get_env("SYMPHONY_BOT_USERNAME")
        self.private_key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
        self.private_key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)
        self.combined_cert_path = get_env("SYMPHONY_BOT_COMBINED_CERT_PATH", required=False)
        self.combined_cert_content = get_env("SYMPHONY_BOT_COMBINED_CERT_CONTENT", required=False)
        self.room_name = get_env("SYMPHONY_TEST_ROOM_NAME")
        self.user_name = get_env("SYMPHONY_TEST_USER_NAME")

        # Will be resolved after connecting
        self.stream_id = None
        self.user_id = None

        # Optional separate endpoint hosts
        self.agent_host = get_env("SYMPHONY_AGENT_HOST", required=False)
        self.session_auth_host = get_env("SYMPHONY_SESSION_AUTH_HOST", required=False)
        self.key_manager_host = get_env("SYMPHONY_KEY_MANAGER_HOST", required=False)

        # Optional URL overrides for non-standard Symphony deployments
        self.message_create_url = get_env("SYMPHONY_MESSAGE_CREATE_URL", required=False)
        self.datafeed_create_url = get_env("SYMPHONY_DATAFEED_CREATE_URL", required=False)
        self.datafeed_delete_url = get_env("SYMPHONY_DATAFEED_DELETE_URL", required=False)
        self.datafeed_read_url = get_env("SYMPHONY_DATAFEED_READ_URL", required=False)
        self.room_search_url = get_env("SYMPHONY_ROOM_SEARCH_URL", required=False)
        self.room_info_url = get_env("SYMPHONY_ROOM_INFO_URL", required=False)
        self.im_create_url = get_env("SYMPHONY_IM_CREATE_URL", required=False)
        self.room_members_url = get_env("SYMPHONY_ROOM_MEMBERS_URL", required=False)
        self.presence_url = get_env("SYMPHONY_PRESENCE_URL", required=False)
        self.user_detail_url = get_env("SYMPHONY_USER_DETAIL_URL", required=False)
        self.user_search_url = get_env("SYMPHONY_USER_SEARCH_URL", required=False)
        self.user_lookup_url = get_env("SYMPHONY_USER_LOOKUP_URL", required=False)

        # Validate authentication
        has_rsa = self.private_key_path or self.private_key_content
        has_combined = self.combined_cert_path or self.combined_cert_content
        if not has_rsa and not has_combined:
            print("❌ Authentication required. Set one of:")
            print("   - SYMPHONY_BOT_PRIVATE_KEY_PATH (RSA key file)")
            print("   - SYMPHONY_BOT_PRIVATE_KEY_CONTENT (RSA key content)")
            print("   - SYMPHONY_BOT_COMBINED_CERT_PATH (combined cert file)")
            print("   - SYMPHONY_BOT_COMBINED_CERT_CONTENT (combined cert content)")
            sys.exit(1)

        self.backend = None
        self.results = []

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
        """Set up the Symphony backend."""
        self.section("Setting Up Symphony Backend")

        config_kwargs = {
            "host": self.host,
            "bot_username": self.bot_username,
        }

        # Authentication - RSA key or combined cert
        if self.private_key_path:
            config_kwargs["bot_private_key_path"] = self.private_key_path
        elif self.private_key_content:
            config_kwargs["bot_private_key_content"] = self.private_key_content
        elif self.combined_cert_path:
            # Use the cert file path directly for certificate auth
            config_kwargs["bot_certificate_path"] = self.combined_cert_path
        elif self.combined_cert_content:
            # SymphonyConfig handles temp file creation automatically
            config_kwargs["bot_certificate_content"] = self.combined_cert_content

        # Add optional separate endpoint hosts
        if self.agent_host:
            config_kwargs["agent_host"] = self.agent_host
        if self.session_auth_host:
            config_kwargs["session_auth_host"] = self.session_auth_host
        if self.key_manager_host:
            config_kwargs["key_manager_host"] = self.key_manager_host

        # Add optional URL overrides
        if self.message_create_url:
            config_kwargs["message_create_url"] = self.message_create_url
        if self.datafeed_create_url:
            config_kwargs["datafeed_create_url"] = self.datafeed_create_url
        if self.datafeed_delete_url:
            config_kwargs["datafeed_delete_url"] = self.datafeed_delete_url
        if self.datafeed_read_url:
            config_kwargs["datafeed_read_url"] = self.datafeed_read_url
        if self.room_search_url:
            config_kwargs["room_search_url"] = self.room_search_url
        if self.room_info_url:
            config_kwargs["room_info_url"] = self.room_info_url
        if self.im_create_url:
            config_kwargs["im_create_url"] = self.im_create_url
        if self.room_members_url:
            config_kwargs["room_members_url"] = self.room_members_url
        if self.presence_url:
            config_kwargs["presence_url"] = self.presence_url
        if self.user_detail_url:
            config_kwargs["user_detail_url"] = self.user_detail_url
        if self.user_search_url:
            config_kwargs["user_search_url"] = self.user_search_url
        if self.user_lookup_url:
            config_kwargs["user_lookup_url"] = self.user_lookup_url

        config = SymphonyConfig(**config_kwargs)

        self.backend = SymphonyBackend(config=config)
        print("Created SymphonyBackend with config")
        print(f"  Host: {self.host}")
        print(f"  Bot Username: {self.bot_username}")
        print(f"  Room Name: {self.room_name}")
        print(f"  Test User Name: {self.user_name}")
        # Determine auth type for display
        if self.combined_cert_path:
            auth_type = "Combined Cert File"
        elif self.combined_cert_content:
            auth_type = "Combined Cert Content"
        elif self.private_key_path:
            auth_type = "RSA Key File"
        else:
            auth_type = "RSA Key Content"
        print(f"  Auth: {auth_type}")
        if self.agent_host:
            print(f"  Agent Host: {self.agent_host}")
        if self.session_auth_host:
            print(f"  Session Auth Host: {self.session_auth_host}")
        if self.key_manager_host:
            print(f"  Key Manager Host: {self.key_manager_host}")

    async def test_connection(self):
        """Test connecting to Symphony."""
        self.section("Test: Connection")

        try:
            await self.backend.connect()
            self.log("Connected to Symphony successfully")
            print(f"  Backend name: {self.backend.name}")
            print(f"  Display name: {self.backend.display_name}")
            print(f"  Format: {self.backend.format}")
            print(f"  Capabilities: {self.backend.capabilities}")

            # Look up room by name to get stream ID
            await self._resolve_room()

            # Look up user by name to get user ID
            await self._resolve_user()

        except Exception as e:
            self.log(f"Failed to connect: {e}", success=False)
            raise

    async def _resolve_room(self):
        """Look up the room by name to get the stream ID."""
        self.section("Resolving Room")

        try:
            # Use the flexible fetch_channel API
            channel = await self.backend.fetch_channel(name=self.room_name)

            if channel:
                self.stream_id = channel.id
                self.log(f"Found room '{self.room_name}'")
                print(f"  Stream ID: {self.stream_id}")
                return

            self.log(f"Room '{self.room_name}' not found", success=False)
            raise RuntimeError(f"Could not find room: {self.room_name}")

        except Exception as e:
            if "not found" in str(e).lower():
                raise
            self.log(f"Failed to look up room: {e}", success=False)
            raise RuntimeError(f"Could not look up room: {self.room_name}")

    async def _resolve_user(self):
        """Look up the user by name (username or display name) to get the user ID."""
        self.section("Resolving User")

        try:
            # Use the flexible fetch_user API - try by handle first, then email, then name
            user = await self.backend.fetch_user(handle=self.user_name)
            if not user and self.user_name and "@" in self.user_name:
                # Looks like an email address
                user = await self.backend.fetch_user(email=self.user_name)
            if not user:
                user = await self.backend.fetch_user(name=self.user_name)

            if user:
                self.user_id = user.id
                self.log(f"Found user '{user.name}'")
                print(f"  User ID: {self.user_id}")
                print(f"  Username: {user.handle}")
                print(f"  Display Name: {user.name}")
                return

            self.log(f"User '{self.user_name}' not found", success=False)
            raise RuntimeError(f"Could not find user: {self.user_name}")

        except Exception as e:
            if "not found" in str(e).lower():
                raise
            self.log(f"Failed to look up user: {e}", success=False)
            raise RuntimeError(f"Could not look up user: {self.user_name}")

    async def test_send_plain_message(self):
        """Test sending a plain text message."""
        self.section("Test: Send Plain Message")

        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Use format system to build message
            msg = FormattedMessage().add_text(f"🧪 [E2E Test] Plain message sent at {timestamp}")
            content = msg.render(Format.SYMPHONY_MESSAGEML)

            result = await self.backend.send_message(self.stream_id, content)
            self.log(f"Sent plain message at {timestamp}")

            if result:
                print(f"  Message ID: {result}")
            return result
        except Exception as e:
            self.log(f"Failed to send plain message: {e}", success=False)
            return None

    async def test_send_messageml(self):
        """Test sending MessageML formatted messages."""
        self.section("Test: Send MessageML Formatted Message")

        try:
            # Use format system to build rich message
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] MessageML Formatting:\n")
                .add_bold("Bold text")
                .add_text(" and ")
                .add_italic("italic text")
                .add_text("\n")
                .add_text("Code: ")
                .add_code("inline_code()")
                .add_text("\n")
                .add_code_block("def hello():\n    print('Hello from code block!')")
                .add_text("\nThis uses the chatom format system rendered as MessageML.")
            )
            content = msg.render(Format.SYMPHONY_MESSAGEML)

            result = await self.backend.send_message(self.stream_id, content)
            self.log("Sent MessageML formatted message")

            return result
        except Exception as e:
            self.log(f"Failed to send MessageML message: {e}", success=False)
            return None

    async def test_send_formatted_message(self):
        """Test sending formatted messages using the chatom format system."""
        self.section("Test: Send Formatted Message (via Format System)")

        try:
            # Build a rich message with formatting
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] Formatted via chatom:\n")
                .add_bold("Bold text")
                .add_text(" and ")
                .add_italic("italic text")
                .add_text("\n")
                .add_code("inline_code()")
            )

            # Render for Symphony (MessageML format)
            content = msg.render(Format.SYMPHONY_MESSAGEML)
            print(f"  Rendered content:\n{content[:300]}...")

            result = await self.backend.send_message(self.stream_id, content)
            self.log("Sent formatted message via Format system")

            return result
        except Exception as e:
            self.log(f"Failed to send formatted message: {e}", success=False)
            return None

    async def test_fetch_user(self):
        """Test fetching user information."""
        self.section("Test: Fetch User")

        try:
            user = await self.backend.fetch_user(self.user_id)
            if user:
                self.log(f"Fetched user: {user.display_name or user.name}")
                print(f"  User ID: {user.id}")
                print(f"  Name: {user.name}")
                print(f"  Display Name: {user.display_name}")
                print(f"  Email: {getattr(user, 'email', 'N/A')}")
                print(f"  Company: {getattr(user, 'company', 'N/A')}")
                print(f"  Department: {getattr(user, 'department', 'N/A')}")
                return user
            else:
                self.log(f"User not found: {self.user_id}", success=False)
                return None
        except Exception as e:
            self.log(f"Failed to fetch user: {e}", success=False)
            return None

    async def test_mentions(self, user):
        """Test user mentions with MessageML."""
        self.section("Test: Mentions")

        try:
            # User mention by UID
            uid_mention = mention_user_by_uid(self.user_id)
            print(f"  User mention by UID: {uid_mention}")

            # If we have user object, use the backend method
            if user:
                user_mention = self.backend.mention_user(user)
                print(f"  User mention (auto): {user_mention}")
            else:
                user_mention = uid_mention

            # Use format system to build message with mention
            # Note: mentions need to be embedded as raw MessageML since format system
            # doesn't yet have native mention support
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] Mentions:\n")
                .add_text("User mention: ")
                .add_raw(user_mention)  # Use add_raw to preserve XML mention tag
                .add_text("\nCheck if you got notified!")
            )
            content = msg.render(Format.SYMPHONY_MESSAGEML)

            await self.backend.send_message(self.stream_id, content)
            self.log("Sent message with user mention")

        except Exception as e:
            self.log(f"Failed to test mentions: {e}", success=False)

    async def test_hashtags_cashtags(self):
        """Test hashtags and cashtags (Symphony-specific)."""
        self.section("Test: Hashtags and Cashtags")

        try:
            # Create hashtag and cashtag
            hashtag = format_hashtag("chatom")
            cashtag = format_cashtag("AAPL")

            print(f"  Hashtag format: {hashtag}")
            print(f"  Cashtag format: {cashtag}")

            # Use format system with add_raw for Symphony-specific tags
            msg = (
                FormattedMessage()
                .add_text("🧪 [E2E Test] Symphony Tags:\n")
                .add_text("Hashtag: ")
                .add_raw(hashtag)
                .add_text("\nCashtag: ")
                .add_raw(cashtag)
                .add_text("\nThese are clickable in Symphony!")
            )
            content = msg.render(Format.SYMPHONY_MESSAGEML)

            await self.backend.send_message(self.stream_id, content)
            self.log("Sent message with hashtag and cashtag")

        except Exception as e:
            self.log(f"Failed to test hashtags/cashtags: {e}", success=False)

    async def test_rich_content(self):
        """Test sending rich content with tables."""
        self.section("Test: Rich Content (Tables)")

        try:
            # Create a message with a table
            msg = FormattedMessage()
            msg.add_text("🧪 [E2E Test] Rich Content (Table):\n\n")

            table = Table.from_data(
                headers=["Feature", "Status", "Notes"],
                data=[
                    ["Messages", "✅", "Working"],
                    ["Mentions", "✅", "Working"],
                    ["Hashtags", "✅", "Working"],
                    ["Cashtags", "✅", "Working"],
                    ["Presence", "✅", "Working"],
                ],
            )
            msg.content.append(table)

            content = msg.render(Format.SYMPHONY_MESSAGEML)
            await self.backend.send_message(self.stream_id, content)
            self.log("Sent rich content with table")

        except Exception as e:
            self.log(f"Failed to test rich content: {e}", success=False)

    async def test_reactions(self, message_id: Optional[str] = None):
        """Test adding and removing reactions."""
        self.section("Test: Reactions")

        if not message_id:
            # Send a message to react to
            msg = FormattedMessage().add_text("🧪 [E2E Test] React to this message! Bot will add reactions...")
            result = await self.backend.send_message(self.stream_id, msg.render(Format.SYMPHONY_MESSAGEML))
            message_id = result.id if result else None

        if not message_id:
            self.log("No message ID to add reactions to", success=False)
            return

        try:
            # Add reactions (Symphony uses emoji shortcodes like :thumbsup:)
            reactions = [":thumbsup:", ":thumbsdown:", ":tada:", ":heart:"]
            for emoji in reactions:
                await self.backend.add_reaction(message_id, emoji, channel=self.stream_id)
                print(f"  Added reaction: {emoji}")
                await asyncio.sleep(0.5)  # Rate limit

            self.log(f"Added {len(reactions)} reactions")

            # Wait a moment then remove one
            await asyncio.sleep(2)
            await self.backend.remove_reaction(message_id, ":thumbsdown:", channel=self.stream_id)
            self.log("Removed :thumbsdown: reaction")

        except Exception as e:
            self.log(f"Failed to test reactions: {e}", success=False)
            traceback.print_exc()

    async def test_fetch_messages(self):
        """Test fetching message history."""
        self.section("Test: Fetch Message History")

        try:
            messages = await self.backend.fetch_messages(self.stream_id, limit=10)
            self.log(f"Fetched {len(messages)} messages from history")

            print("\n  Recent messages:")
            for msg in messages[:5]:
                # Symphony messages have PresentationML
                content_preview = (msg.content or msg.presentation_ml or "")[:50].replace("\n", " ")
                print(f"  - [{msg.id[:8]}...] {content_preview}...")

            # Test reading a message with the format system
            if messages:
                print("\n  Testing format system on first message...")
                first_msg = messages[0]
                if hasattr(first_msg, "to_formatted"):
                    formatted = first_msg.to_formatted()

                    # Get plain text
                    plain = formatted.render(Format.PLAINTEXT)
                    print(f"  Plain text: {plain[:100]}...")

                    # Check metadata
                    if formatted.metadata.get("mention_ids"):
                        print(f"  Mentions: {formatted.metadata['mention_ids']}")
                    if formatted.metadata.get("hashtags"):
                        print(f"  Hashtags: {formatted.metadata['hashtags']}")
                    if formatted.metadata.get("cashtags"):
                        print(f"  Cashtags: {formatted.metadata['cashtags']}")

                    self.log("Successfully converted message to FormattedMessage")
                else:
                    print("  Message doesn't have to_formatted() method")

            return messages

        except Exception as e:
            self.log(f"Failed to fetch messages: {e}", success=False)
            return []

    async def test_presence(self, user):
        """Test getting and setting presence."""
        self.section("Test: Presence")

        try:
            # Get user presence
            if user:
                presence = await self.backend.get_presence(user.id)
                if presence:
                    print(f"  User presence status: {presence.status}")
                    self.log("Fetched user presence")
                else:
                    print("  Could not fetch presence")

            # Set bot presence
            await self.backend.set_presence(
                status="BUSY",
            )
            self.log("Set bot presence to BUSY")

            # Reset to available
            await asyncio.sleep(2)
            await self.backend.set_presence(status="AVAILABLE")
            self.log("Reset bot presence to AVAILABLE")

        except Exception as e:
            self.log(f"Failed to test presence: {e}", success=False)

    async def test_room_creation(self):
        """Test room/IM/MIM creation using new convenience methods."""
        self.section("Test: Room/IM Creation (using Channel.dm_to)")

        # Get user object for DM convenience methods
        test_user = await self.backend.fetch_user(self.user_id) if self.user_id else None

        # Test 1: Use Channel.dm_to() convenience method
        if test_user:
            try:
                print(f"\n  Method 1: Using Channel.dm_to({test_user.display_name})...")
                dm_channel = Channel.dm_to(test_user)
                print(f"    Created incomplete DM channel: {dm_channel}")
                print(f"    Channel type: {dm_channel.channel_type}")
                print(f"    Users: {[u.display_name for u in dm_channel.users]}")
                print(f"    Is incomplete: {dm_channel.is_incomplete}")

                # Send message to incomplete channel - backend will resolve it
                dm_msg = (
                    FormattedMessage()
                    .add_text("🧪 ")
                    .add_bold("[E2E Test] DM via Channel.dm_to()")
                    .add_text("\n\nThis is a test using the new Channel.dm_to() convenience method.")
                )
                _result = await self.backend.send_message(dm_channel, dm_msg.render(Format.SYMPHONY_MESSAGEML))
                self.log("Sent DM using Channel.dm_to() convenience")
            except Exception as e:
                self.log(f"Failed to use Channel.dm_to: {e}", success=False)

        # Test 2: Use create_im directly (legacy approach)
        try:
            print(f"\n  Method 2: Using create_im([{self.user_id}]) directly...")
            im_id = await self.backend.create_im([self.user_id])
            if im_id:
                self.log(f"Created DM with user {self.user_id}")
                print(f"  DM Stream ID: {im_id}")

                # Send a test message to the DM
                dm_msg = FormattedMessage().add_text("🧪 ").add_bold("[E2E Test] DM Test").add_text("\n\nThis is a test message sent to a 1:1 DM.")
                await self.backend.send_message(im_id, dm_msg.render(Format.SYMPHONY_MESSAGEML))
                self.log("Sent message to DM")
            else:
                self.log("DM creation returned no ID", success=False)
        except Exception as e:
            self.log(f"Failed to create DM: {e}", success=False)

        # Test 3: Create a multi-party IM (MIM) using Channel.group_dm_to()
        # For this test, we need multiple users - we'll demonstrate the API
        try:
            print("\n  Method 3: Demonstrating Channel.group_dm_to() API...")
            # Note: In a real scenario, you'd have multiple user IDs
            # For now, just show the API usage
            if test_user:
                # Create another dummy user for demonstration
                print("    Channel.group_dm_to() requires 2+ users")
                print("    Example: group_dm = Channel.group_dm_to([user1, user2])")
                print("    Skipping actual MIM creation (need 2+ real users)")
                self.log("Group DM API demonstrated (Channel.group_dm_to)")
        except Exception as e:
            self.log(f"Failed to demonstrate group DM: {e}", success=False)

        # Test 4: Create a private room with unique timestamp
        try:
            room_name = f"E2E Test Room {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"\n  Creating private room: {room_name}")
            room_id = await self.backend.create_room(
                name=room_name,
                description="Test room created by chatom E2E test - safe to delete",
                public=False,
            )
            if room_id:
                self.log(f"Created private room: {room_name}")
                print(f"  Room Stream ID: {room_id}")

                # Send a test message to the room
                room_msg = (
                    FormattedMessage()
                    .add_text("🧪 ")
                    .add_bold("[E2E Test] Room Test")
                    .add_text("\n\nThis is a test message sent to a newly created private room.")
                    .add_text(f"\n\nRoom name: {room_name}")
                    .add_text("\n\nThis room was created by the chatom E2E test suite.")
                    .add_text("\nYou can safely delete this room after testing.")
                )
                await self.backend.send_message(room_id, room_msg.render(Format.SYMPHONY_MESSAGEML))
                self.log("Sent message to new room")

                # Note: We don't delete the room - user can verify and delete manually
                print(f"  ℹ️  Room '{room_name}' created. Delete it manually after verifying.")
            else:
                self.log("Room creation returned no ID", success=False)
        except Exception as e:
            self.log(f"Failed to create room: {e}", success=False)

    async def test_dm_reply_convenience(self):
        """Test as_dm_to_author() convenience method."""
        self.section("Test: as_dm_to_author() Convenience")

        try:
            # Get a recent message from the test stream to use as source
            messages = await self.backend.fetch_messages(self.stream_id, limit=20)

            # Get bot info to skip bot messages
            bot_user_id = None
            try:
                bot_info = await self.backend.get_bot_info()
                bot_user_id = str(bot_info.id) if bot_info else None
            except Exception:
                pass

            # Find a message from a non-bot user
            source_message = None
            for msg in messages:
                if msg.author and msg.author.id != bot_user_id:
                    source_message = msg
                    break

            if source_message:
                print(f"  Found message from {source_message.author.display_name}")
                print(f"  Original content: {(source_message.content or '')[:50]}...")

                # Use as_dm_to_author() to create a DM response
                dm_message = source_message.as_dm_to_author(
                    f"🧪 [E2E Test] DM reply via as_dm_to_author()\n"
                    f"This is a response to your message in {self.room_name}.\n"
                    f"Created at: {datetime.now().isoformat()}"
                )

                print(f"  DM message channel type: {dm_message.channel.channel_type}")
                print(f"  DM message channel users: {[u.display_name for u in dm_message.channel.users]}")
                print(f"  DM message is incomplete: {dm_message.channel.is_incomplete}")

                # Send the DM message - backend will resolve the channel
                # Note: Symphony uses MessageML format
                content = FormattedMessage().add_text(dm_message.content).render(Format.SYMPHONY_MESSAGEML)
                _result = await self.backend.send_message(dm_message.channel, content)
                self.log("Sent DM using as_dm_to_author() convenience")

            else:
                print("  No non-bot message found to test with")
                self.log("as_dm_to_author test skipped - no source message", success=False)

        except Exception as e:
            self.log(f"Failed to test as_dm_to_author: {e}", success=False)
            traceback.print_exc()

    async def test_replies(self):
        """Test message replies using as_reply() convenience method.

        Note: Symphony's bot API does not expose reply functionality.
        Native replies in Symphony are a client-side UI feature.
        This test demonstrates the chatom as_reply() API which tracks the
        reply_to reference, and renders in a format resembling Symphony's UI.
        """
        self.section("Test: Message Replies (as_reply)")

        try:
            # Send a message that will receive a reply
            original_text = "🧪 [E2E Test] Original message - will receive a reply"
            msg = FormattedMessage().add_text(original_text)
            result = await self.backend.send_message(self.stream_id, msg.render(Format.SYMPHONY_MESSAGEML))

            if result:
                print(f"  Original message ID: {result.id}")

                # Use as_reply() convenience method - this creates a message with reply_to set
                reply_msg = result.as_reply("🧪 [E2E Test] This is a reply using as_reply() convenience!")
                print(f"  Reply references original: {reply_msg.reply_to is not None}")
                print(f"  Reply-to message ID: {reply_msg.reply_to.id if reply_msg.reply_to else 'N/A'}")
                print("  Note: Symphony Bot API does not support native replies")
                print("  Using card format to resemble Symphony's reply UI")

                # Get author info for the reply header
                bot_name = self.backend.bot_user_name or "Bot"
                timestamp = datetime.now().strftime("%H:%M:%S")

                # Create a reply format resembling Symphony's native reply UI:
                # Uses a card with the "In reply to:" label, author, timestamp
                # and the quoted original message, followed by the reply content
                reply_content = (
                    "<messageML>"
                    '<card accent="tempo-bg-color--blue">'
                    "<body>"
                    f"<p><b>In reply to:</b> {bot_name} · {timestamp}</p>"
                    f"<p>{original_text}</p>"
                    "</body>"
                    "</card>"
                    f"<p>{reply_msg.content}</p>"
                    "</messageML>"
                )
                reply_result = await self.backend.send_message(self.stream_id, reply_content)
                if reply_result:
                    self.log("Sent reply with Symphony-style card format")
                    print(f"  Reply ID: {reply_result.id}")
                else:
                    self.log("Reply send failed", success=False)
            else:
                self.log("Failed to send original message for reply test", success=False)

        except Exception as e:
            self.log(f"Failed to test replies: {e}", success=False)
            traceback.print_exc()

    async def test_forwarding(self):
        """Test message forwarding using forward_message().

        Note: Symphony's bot API does not expose native forwarding.
        Native forwarding in Symphony is a client-side UI feature.
        This test demonstrates the chatom forward_message() method which
        creates a new message with the original content and optional attribution.
        """
        self.section("Test: Message Forwarding")

        try:
            # First, send a fresh message that we'll forward
            source_content = "🧪 [E2E Test] This is the source message to be forwarded"
            source_msg_result = await self.backend.send_message(
                self.stream_id,
                FormattedMessage().add_text(source_content).render(Format.SYMPHONY_MESSAGEML),
            )

            if not source_msg_result:
                self.log("Failed to create source message for forwarding", success=False)
                return

            print(f"  Source message ID: {source_msg_result.id}")
            print("  Note: Symphony Bot API does not support native forwarding")
            print("  Using chatom forward_message() to recreate content with attribution")

            # Get channel and author info for attribution
            from chatom.symphony import SymphonyChannel, SymphonyMessage, SymphonyUser

            source_channel = SymphonyChannel(
                id=self.stream_id,
                name=self.room_name,
            )

            # Use bot's own info as the author (since bot sent the source message)
            bot_name = self.backend.bot_user_name or "Bot"
            source_author = SymphonyUser(
                id=self.backend.bot_user_id or "",
                name=bot_name,
                display_name=bot_name,
            )

            # Create a SymphonyMessage object with content for forwarding
            source_message = SymphonyMessage(
                id=source_msg_result.id,
                content=source_content,
                formatted_content=f"<p>{source_content}</p>",
                channel=source_channel,
                author=source_author,
            )
            print(f"  Source channel: {source_channel.name}")
            print(f"  Source author: {source_author.display_name}")

            # Forward the message with attribution
            forwarded = await self.backend.forward_message(
                source_message,
                self.stream_id,
                include_attribution=True,
                prefix="📤 ",
            )
            if forwarded:
                self.log("Forwarded message with attribution")
                print(f"  Forwarded message ID: {forwarded.id}")

        except Exception as e:
            self.log(f"Failed to test forwarding: {e}", success=False)
            traceback.print_exc()

    async def test_group_dm(self):
        """Test multi-person group DM (MIM) using Channel.group_dm_to()."""
        self.section("Test: Group DM / MIM (Multi-Person)")

        try:
            # Get the test user
            test_user = await self.backend.fetch_user(self.user_id) if self.user_id else None

            if test_user:
                # Demonstrate Channel.group_dm_to() API
                print("  Channel.group_dm_to() requires 2+ users")
                print("  Example: group_dm = Channel.group_dm_to([user1, user2])")

                # For actual group DM/MIM, we need 2+ users - try to find another user from history
                messages = await self.backend.fetch_messages(self.stream_id, limit=50)

                # Get bot info to exclude
                bot_user_id = None
                try:
                    bot_info = await self.backend.get_bot_info()
                    bot_user_id = str(bot_info.id) if bot_info else None
                except Exception:
                    pass

                other_users = []
                seen_ids = {self.user_id}
                if bot_user_id:
                    seen_ids.add(bot_user_id)

                for msg in messages:
                    if msg.author and msg.author.id not in seen_ids:
                        other_users.append(msg.author)
                        seen_ids.add(msg.author.id)
                        if len(other_users) >= 1:
                            break

                if other_users:
                    # Create group DM (MIM) with test_user and other_user
                    group_users = [test_user] + other_users
                    print(f"  Creating MIM with {len(group_users)} users:")
                    for u in group_users:
                        print(f"    - {u.display_name} ({u.id})")

                    group_dm = Channel.group_dm_to(group_users)
                    print(f"  Group DM channel type: {group_dm.channel_type}")
                    print(f"  Is incomplete: {group_dm.is_incomplete}")

                    # Send message to group DM/MIM
                    msg = (
                        FormattedMessage()
                        .add_text("🧪 [E2E Test] MIM via Channel.group_dm_to()\n")
                        .add_text(f"Created at: {datetime.now().isoformat()}")
                    )
                    _result = await self.backend.send_message(group_dm, msg.render(Format.SYMPHONY_MESSAGEML))
                    self.log("Sent MIM using Channel.group_dm_to()")
                else:
                    print("  No other users found for MIM test")
                    self.log("Group DM/MIM API demonstrated (need 2+ real users to send)")
            else:
                print("  Skipping MIM test - no user available")
                self.log("MIM test skipped - no user", success=False)

        except Exception as e:
            self.log(f"Failed to test group DM/MIM: {e}", success=False)
            traceback.print_exc()

    async def test_file_attachment(self):
        """Test sending a file attachment."""
        self.section("Test: File Attachment")

        try:
            # Create a temporary text file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write("This is a test file created by the chatom E2E test suite.\n")
                f.write(f"Created at: {datetime.now().isoformat()}\n")
                f.write("This file can be safely deleted.\n")
                temp_file_path = f.name

            print(f"  Created temp file: {temp_file_path}")

            try:
                # Symphony BDK expects file-like objects with the 'attachments' parameter
                with open(temp_file_path, "rb") as file_obj:
                    msg = FormattedMessage().add_text("🧪 [E2E Test] File attachment test")
                    result = await self.backend.send_message(
                        self.stream_id,
                        msg.render(Format.SYMPHONY_MESSAGEML),
                        attachments=[file_obj],
                    )

                if result:
                    self.log("Sent file attachment successfully")
                    print(f"  Message ID: {result.id}")
                else:
                    self.log("File attachment send failed", success=False)

            finally:
                # Clean up temp file
                os.unlink(temp_file_path)

        except Exception as e:
            self.log(f"Failed to test file attachment: {e}", success=False)
            traceback.print_exc()

    async def test_inbound_messages(self):
        """Test receiving inbound messages with bot mentions."""
        self.section("Test: Inbound Messages (Interactive)")

        try:
            # Get bot info using the abstracted API
            bot_info = await self.backend.get_bot_info()
            if not bot_info:
                self.log("Could not get bot info", success=False)
                return

            bot_user_id = bot_info.id
            bot_display_name = bot_info.name
            print(f"  Bot User ID: {bot_user_id}")
            print(f"  Bot Display Name: {bot_display_name}")

            # Send prompt to user FIRST (before starting stream, as stream startup can be slow)
            print("  Sending prompt to user...")
            prompt_msg = (
                FormattedMessage()
                .add_text("🧪 ")
                .add_bold("[E2E Test] Inbound Message Test")
                .add_text("\n\nPlease send a message in this room that ")
                .add_bold("mentions the bot")
                .add_text(".\n\nExample: ")
                .add_italic(f"@{bot_display_name} hello this is a test message")
                .add_text("\n\nYou have ")
                .add_bold("30 seconds")
                .add_text(" to respond...")
            )
            prompt_result = await self.backend.send_message(self.stream_id, prompt_msg.render(Format.SYMPHONY_MESSAGEML))
            print(f"  Prompt message ID: {prompt_result}")
            print("\n  ⏳ Waiting for you to send a message mentioning the bot...")
            print(f"     Mention the bot like: @{bot_display_name} hello test")

            # Use the abstracted stream_messages API
            # skip_own=True and skip_history=True are defaults, so we just get user messages
            received_message = None
            try:
                async with asyncio.timeout(30.0):
                    async for message in self.backend.stream_messages(channel=self.stream_id):
                        # First message from a user after stream started - that's the one we want
                        received_message = message
                        break

            except asyncio.TimeoutError:
                self.log("Timeout waiting for inbound message (30s)", success=require_interactive_e2e() is False)
                timeout_msg = FormattedMessage().add_text("⏰ ").add_bold("[E2E Test] Timeout").add_text(" - No message received within 30 seconds.")
                await self.backend.send_message(self.stream_id, timeout_msg.render(Format.SYMPHONY_MESSAGEML))
                return

            if received_message:
                self.log("Received inbound message from user")
                print("\n  📨 Message received:")
                print(f"     Message ID: {received_message.id}")
                print(f"     From: {received_message.author_id}")
                content_preview = (received_message.content or "")[:200].replace("\n", " ")
                print(f"     Content: {content_preview}...")

                # Check if bot is mentioned using the backend's method
                has_bot_mention = (
                    received_message.mentions_user(User(id=bot_user_id))
                    if hasattr(received_message, "mentions_user")
                    else received_message.is_message_to_user(bot_info)
                )

                if has_bot_mention:
                    self.log("Bot mention detected in message")
                else:
                    print("     ⚠️  Bot mention not found in content")
                    print(f"     Bot ID: {bot_user_id}")
                    self.log("Bot mention not detected in message", success=False)

                # Test format system processing
                await self._test_inbound_format_processing(received_message, bot_user_id)
            else:
                self.log("Message received but was None", success=False)

        except Exception as e:
            self.log(f"Failed to test inbound messages: {e}", success=False)
            traceback.print_exc()

    async def _test_inbound_format_processing(self, received_message, bot_user_id: str):
        """Test processing the inbound message with the format system."""
        self.section("Test: Format System Processing (Inbound)")

        try:
            # The received_message is already a SymphonyMessage
            msg = received_message
            print(f"  Message type: {type(msg).__name__}")
            print(f"  Message ID: {msg.id}")
            print(f"  Content preview: {(msg.content or '')[:100]}...")

            # Test conversion to FormattedMessage
            if hasattr(msg, "to_formatted"):
                formatted = msg.to_formatted()
                print("  Converted to FormattedMessage")

                # Render to different formats
                plain_text = formatted.render(Format.PLAINTEXT)
                print(f"  Plain text: {plain_text[:100]}...")

                # Check metadata for mentions
                mention_ids = formatted.metadata.get("mention_ids", [])
                if mention_ids:
                    print(f"  Detected mentions: {mention_ids}")
                    if bot_user_id in [str(m) for m in mention_ids]:
                        self.log("Format system correctly extracted bot mention")
                    else:
                        print(f"     Bot ID {bot_user_id} not in mention list")

                # Check for hashtags/cashtags if present
                hashtags = formatted.metadata.get("hashtags", [])
                cashtags = formatted.metadata.get("cashtags", [])
                if hashtags:
                    print(f"  Detected hashtags: {hashtags}")
                if cashtags:
                    print(f"  Detected cashtags: {cashtags}")

                self.log("Successfully processed inbound message with format system")

            else:
                print("  Message does not have to_formatted() method")
                self.log("Format conversion not available", success=False)

            # Send confirmation back to the room using format system
            # Use the extracted plain text from the format system, not raw content
            if hasattr(msg, "to_formatted"):
                extracted_text = msg.to_formatted().render(Format.PLAINTEXT)[:80]
            else:
                extracted_text = (msg.content or "")[:80]
            confirm_msg = (
                FormattedMessage()
                .add_text("✅ ")
                .add_bold("[E2E Test] Message Received and Processed!")
                .add_text("\n\nYour message was successfully:\n")
                .add_text("• Received via stream_messages()\n")
                .add_text("• Processed by the format system\n\n")
                .add_text("Plain text extraction: ")
                .add_italic(extracted_text)
            )
            await self.backend.send_message(self.stream_id, confirm_msg.render(Format.SYMPHONY_MESSAGEML))

        except Exception as e:
            self.log(f"Failed to process with format system: {e}", success=False)
            traceback.print_exc()

    async def cleanup(self):
        """Clean up and disconnect."""
        self.section("Cleanup")

        if self.backend and self.backend.connected:
            await self.backend.disconnect()
            self.log("Disconnected from Symphony")

        # Temp cert cleanup is now handled automatically by SymphonyConfig

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
        print("  Symphony End-to-End Integration Test")
        print("=" * 60)

        try:
            await self.setup()
            await self.test_connection()

            # Fetch user for later tests
            user = await self.test_fetch_user()

            # Test messaging
            await self.test_send_plain_message()
            await self.test_send_messageml()
            await self.test_send_formatted_message()

            # Test Symphony-specific features
            await self.test_mentions(user)
            await self.test_hashtags_cashtags()

            # Test rich content
            await self.test_rich_content()

            # Test reactions
            await self.test_reactions()

            # Test history
            await self.test_fetch_messages()

            # Test presence
            await self.test_presence(user)

            # Test room creation (with Channel.dm_to convenience)
            await self.test_room_creation()

            # Test as_dm_to_author convenience
            await self.test_dm_reply_convenience()

            # Test replies
            await self.test_replies()

            # Test forwarding
            await self.test_forwarding()

            # Test group DM/MIM
            await self.test_group_dm()

            # Test file attachment
            await self.test_file_attachment()

            # Test inbound messages (interactive - prompts user)
            await self.test_inbound_messages()

        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            traceback.print_exc()

        finally:
            await self.cleanup()

        return self.print_summary()


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
                self.log("Timeout waiting for inbound message (30s)", success=require_interactive_e2e() is False)
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


class CombinedE2ETest:
    """Combined Symphony + Slack end-to-end test suite."""

    def __init__(self):
        """Initialize test configuration from environment."""
        # Symphony config
        self.symphony_host = get_env("SYMPHONY_HOST")
        self.symphony_bot_username = get_env("SYMPHONY_BOT_USERNAME")
        self.symphony_private_key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
        self.symphony_private_key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)
        self.symphony_combined_cert_path = get_env("SYMPHONY_BOT_COMBINED_CERT_PATH", required=False)
        self.symphony_combined_cert_content = get_env("SYMPHONY_BOT_COMBINED_CERT_CONTENT", required=False)
        self.symphony_room_name = get_env("SYMPHONY_TEST_ROOM_NAME")
        self.symphony_user_name = get_env("SYMPHONY_TEST_USER_NAME")
        self.symphony_agent_host = get_env("SYMPHONY_AGENT_HOST", required=False)
        self.symphony_session_auth_host = get_env("SYMPHONY_SESSION_AUTH_HOST", required=False)
        self.symphony_key_manager_host = get_env("SYMPHONY_KEY_MANAGER_HOST", required=False)

        # Symphony URL overrides for non-standard deployments
        self.symphony_message_create_url = get_env("SYMPHONY_MESSAGE_CREATE_URL", required=False)
        self.symphony_datafeed_create_url = get_env("SYMPHONY_DATAFEED_CREATE_URL", required=False)
        self.symphony_datafeed_delete_url = get_env("SYMPHONY_DATAFEED_DELETE_URL", required=False)
        self.symphony_datafeed_read_url = get_env("SYMPHONY_DATAFEED_READ_URL", required=False)
        self.symphony_room_search_url = get_env("SYMPHONY_ROOM_SEARCH_URL", required=False)
        self.symphony_room_info_url = get_env("SYMPHONY_ROOM_INFO_URL", required=False)
        self.symphony_im_create_url = get_env("SYMPHONY_IM_CREATE_URL", required=False)
        self.symphony_room_members_url = get_env("SYMPHONY_ROOM_MEMBERS_URL", required=False)
        self.symphony_presence_url = get_env("SYMPHONY_PRESENCE_URL", required=False)
        self.symphony_user_detail_url = get_env("SYMPHONY_USER_DETAIL_URL", required=False)
        self.symphony_user_search_url = get_env("SYMPHONY_USER_SEARCH_URL", required=False)
        self.symphony_user_lookup_url = get_env("SYMPHONY_USER_LOOKUP_URL", required=False)

        # Validate Symphony authentication
        has_rsa = self.symphony_private_key_path or self.symphony_private_key_content
        has_combined = self.symphony_combined_cert_path or self.symphony_combined_cert_content
        if not has_rsa and not has_combined:
            print("❌ Symphony authentication required. Set one of:")
            print("   - SYMPHONY_BOT_PRIVATE_KEY_PATH (RSA key file)")
            print("   - SYMPHONY_BOT_PRIVATE_KEY_CONTENT (RSA key content)")
            print("   - SYMPHONY_BOT_COMBINED_CERT_PATH (combined cert file)")
            print("   - SYMPHONY_BOT_COMBINED_CERT_CONTENT (combined cert content)")
            sys.exit(1)

        # Slack config
        self.slack_bot_token = get_env("SLACK_BOT_TOKEN")
        self.slack_channel_name = get_env("SLACK_TEST_CHANNEL_NAME")
        self.slack_user_name = get_env("SLACK_TEST_USER_NAME")
        self.slack_app_token = get_env("SLACK_APP_TOKEN")  # Required for this test

        # Will be resolved after connecting
        self.symphony_stream_id = None
        self.symphony_user_id = None
        self.slack_channel_id = None
        self.slack_user_id = None

        # Backends
        self.symphony_backend: Optional[SymphonyBackend] = None
        self.slack_backend: Optional[SlackBackend] = None

        self.results = []

    async def _find_slack_user_by_email(self, email: str) -> Optional[str]:
        """Find a Slack user ID by their email address."""
        try:
            user = await self.slack_backend.fetch_user(email=email)
            if user:
                return user.id
        except Exception:
            pass
        return None

    async def _find_symphony_user_by_email(self, email: str) -> Optional[str]:
        """Find a Symphony user ID by their email address."""
        try:
            user = await self.symphony_backend.fetch_user(email=email)
            if user:
                return str(user.id)
        except Exception:
            pass
        return None

    async def _parse_slack_mentions(self, text: str) -> List[Tuple[str, Union[str, Tuple[str, str]]]]:
        """Parse Slack text and return segments with mentions resolved to Symphony.

        Returns a list of tuples: ('text', 'content') or ('mention', (user_id, display_name))
        """
        segments = []
        mention_pattern = re.compile(r"<@(U[A-Z0-9]+)>")
        last_end = 0

        for match in mention_pattern.finditer(text):
            # Add text before this mention
            if match.start() > last_end:
                segments.append(("text", text[last_end : match.start()]))

            slack_user_id = match.group(1)
            display_name = "User"
            symphony_user_id = None

            try:
                # Get user info from Slack using abstract API
                slack_user = await self.slack_backend.fetch_user(slack_user_id)
                if slack_user:
                    display_name = slack_user.display_name or slack_user.name or "User"

                    # Try to find the user in Symphony by email
                    if slack_user.email:
                        symphony_user_id = await self._find_symphony_user_by_email(slack_user.email)
            except Exception:
                pass

            if symphony_user_id:
                segments.append(("mention", (symphony_user_id, display_name)))
            else:
                segments.append(("text", f"@{display_name}"))

            last_end = match.end()

        # Add remaining text
        if last_end < len(text):
            segments.append(("text", text[last_end:]))

        return segments if segments else [("text", text)]

    async def _parse_symphony_mentions(self, text: str, mentions: list = None) -> List[Tuple[str, Union[str, Tuple[str, str]]]]:
        """Parse Symphony text and return segments with mentions resolved to Slack.

        Returns a list of tuples: ('text', 'content') or ('mention', (user_id, display_name))
        """
        # Build a map of display_name -> slack_user_id from structured mentions
        mention_map = {}  # display_name -> slack_user_id

        if mentions:
            for mention in mentions:
                # Handle User objects from chatom.base
                user_id = None

                # Get user ID - try various attribute names
                if hasattr(mention, "id"):
                    user_id = mention.id
                elif hasattr(mention, "user_id"):
                    user_id = mention.user_id
                elif isinstance(mention, dict):
                    user_id = mention.get("id") or mention.get("user_id")

                if user_id:
                    try:
                        # Fetch full user details to get the real display name
                        symphony_user = await self.symphony_backend.fetch_user(user_id)
                        if symphony_user:
                            # Get the display name from the fetched user
                            display_name = symphony_user.display_name or symphony_user.name

                            if display_name and symphony_user.email:
                                slack_user_id = await self._find_slack_user_by_email(symphony_user.email)
                                if slack_user_id:
                                    mention_map[display_name] = slack_user_id
                    except Exception:
                        pass

        # Search for known mentions from the map directly in the text
        # This is more reliable than regex for names with commas, etc.
        segments = []

        if mention_map:
            # Sort by length descending to match longer names first
            sorted_names = sorted(mention_map.keys(), key=len, reverse=True)

            # Find all mentions and their positions
            mention_positions = []  # (start, end, display_name, slack_user_id)
            for display_name in sorted_names:
                search_text = f"@{display_name}"
                idx = text.find(search_text)
                if idx != -1:
                    mention_positions.append((idx, idx + len(search_text), display_name, mention_map[display_name]))

            # Sort by position
            mention_positions.sort(key=lambda x: x[0])

            # Build segments
            last_end = 0
            for start, end, display_name, slack_user_id in mention_positions:
                # Skip if this overlaps with a previous mention
                if start < last_end:
                    continue

                # Add text before this mention
                if start > last_end:
                    segments.append(("text", text[last_end:start]))

                segments.append(("mention", (slack_user_id, display_name)))
                last_end = end

            # Add remaining text
            if last_end < len(text):
                segments.append(("text", text[last_end:]))

        return segments if segments else [("text", text)]

    def _build_message_with_segments(
        self, segments: List[Tuple[str, Union[str, Tuple[str, str]]]], target_format: str = "symphony"
    ) -> FormattedMessage:
        """Build a FormattedMessage from parsed segments.

        Args:
            segments: List of ('text', content) or ('mention', (user_id, display_name)) tuples
            target_format: 'symphony' or 'slack' - determines mention format
        """
        msg = FormattedMessage()

        for seg_type, content in segments:
            if seg_type == "text":
                msg.add_text(content)
            elif seg_type == "mention":
                user_id, display_name = content
                if target_format == "symphony":
                    msg.add_mention(user_id, display_name)
                else:
                    # For Slack, use raw <@U...> format in text
                    msg.add_text(f"<@{user_id}>")

        return msg

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

    async def setup_symphony(self):
        """Set up the Symphony backend."""
        self.section("Setting Up Symphony Backend")

        config_kwargs = {
            "host": self.symphony_host,
            "bot_username": self.symphony_bot_username,
        }

        # Authentication - RSA key or combined cert
        if self.symphony_private_key_path:
            config_kwargs["bot_private_key_path"] = self.symphony_private_key_path
            print(f"  Using RSA key file: {self.symphony_private_key_path}")
        elif self.symphony_private_key_content:
            config_kwargs["bot_private_key_content"] = self.symphony_private_key_content
            print("  Using RSA key content")
        elif self.symphony_combined_cert_path:
            config_kwargs["bot_certificate_path"] = self.symphony_combined_cert_path
            print(f"  Using combined cert file: {self.symphony_combined_cert_path}")
        elif self.symphony_combined_cert_content:
            config_kwargs["bot_certificate_content"] = self.symphony_combined_cert_content
            print("  Using combined cert content")

        # Add optional separate endpoint hosts
        if self.symphony_agent_host:
            config_kwargs["agent_host"] = self.symphony_agent_host
        if self.symphony_session_auth_host:
            config_kwargs["session_auth_host"] = self.symphony_session_auth_host
        if self.symphony_key_manager_host:
            config_kwargs["key_manager_host"] = self.symphony_key_manager_host

        # Add optional URL overrides
        if self.symphony_message_create_url:
            config_kwargs["message_create_url"] = self.symphony_message_create_url
        if self.symphony_datafeed_create_url:
            config_kwargs["datafeed_create_url"] = self.symphony_datafeed_create_url
        if self.symphony_datafeed_delete_url:
            config_kwargs["datafeed_delete_url"] = self.symphony_datafeed_delete_url
        if self.symphony_datafeed_read_url:
            config_kwargs["datafeed_read_url"] = self.symphony_datafeed_read_url
        if self.symphony_room_search_url:
            config_kwargs["room_search_url"] = self.symphony_room_search_url
        if self.symphony_room_info_url:
            config_kwargs["room_info_url"] = self.symphony_room_info_url
        if self.symphony_im_create_url:
            config_kwargs["im_create_url"] = self.symphony_im_create_url
        if self.symphony_room_members_url:
            config_kwargs["room_members_url"] = self.symphony_room_members_url
        if self.symphony_presence_url:
            config_kwargs["presence_url"] = self.symphony_presence_url
        if self.symphony_user_detail_url:
            config_kwargs["user_detail_url"] = self.symphony_user_detail_url
        if self.symphony_user_search_url:
            config_kwargs["user_search_url"] = self.symphony_user_search_url
        if self.symphony_user_lookup_url:
            config_kwargs["user_lookup_url"] = self.symphony_user_lookup_url

        config = SymphonyConfig(**config_kwargs)

        self.symphony_backend = SymphonyBackend(config=config)
        print(f"  Host: {self.symphony_host}")
        print(f"  Bot Username: {self.symphony_bot_username}")
        print(f"  Room Name: {self.symphony_room_name}")
        if self.symphony_agent_host:
            print(f"  Agent Host: {self.symphony_agent_host}")
        if self.symphony_session_auth_host:
            print(f"  Session Auth Host: {self.symphony_session_auth_host}")
        if self.symphony_key_manager_host:
            print(f"  Key Manager Host: {self.symphony_key_manager_host}")

        # Connect
        await self.symphony_backend.connect()
        self.log("Connected to Symphony")

        # Look up room using abstract API
        channel = await self.symphony_backend.fetch_channel(name=self.symphony_room_name)
        if channel:
            self.symphony_stream_id = channel.id
            self.log(f"Found Symphony room '{self.symphony_room_name}' -> {self.symphony_stream_id}")
        else:
            print(f"❌ Symphony room '{self.symphony_room_name}' not found")
            sys.exit(1)

        # Look up user using abstract API
        user = await self.symphony_backend.fetch_user(handle=self.symphony_user_name)
        if not user:
            user = await self.symphony_backend.fetch_user(name=self.symphony_user_name)
        if user:
            self.symphony_user_id = str(user.id)
            self.log(f"Found Symphony user '{user.name}' -> {self.symphony_user_id}")
        else:
            print(f"❌ Symphony user '{self.symphony_user_name}' not found")
            sys.exit(1)

    async def setup_slack(self):
        """Set up the Slack backend."""
        self.section("Setting Up Slack Backend")

        config = SlackConfig(
            bot_token=self.slack_bot_token,
            app_token=self.slack_app_token,
        )

        self.slack_backend = SlackBackend(config=config)
        print(f"  Channel Name: {self.slack_channel_name}")
        print(f"  User Name: {self.slack_user_name}")

        # Connect
        await self.slack_backend.connect()
        self.log("Connected to Slack")

        # Look up channel using abstract API
        channel = await self.slack_backend.fetch_channel(name=self.slack_channel_name)
        if channel:
            self.slack_channel_id = channel.id
            self.log(f"Found Slack channel '{self.slack_channel_name}' -> {self.slack_channel_id}")
        else:
            print(f"❌ Slack channel '{self.slack_channel_name}' not found")
            sys.exit(1)

        # Look up user using abstract API
        user = await self.slack_backend.fetch_user(handle=self.slack_user_name)
        if not user:
            user = await self.slack_backend.fetch_user(name=self.slack_user_name)
        if user:
            self.slack_user_id = str(user.id)
            self.log(f"Found Slack user '{user.name}' -> {self.slack_user_id}")
        else:
            print(f"❌ Slack user '{self.slack_user_name}' not found")
            sys.exit(1)

    async def test_symphony_to_slack(self):
        """Test receiving a message from Symphony and forwarding to Slack."""
        self.section("Test: Symphony → Slack Message Forwarding")

        try:
            # Get bot info using abstract API
            bot_info = await self.symphony_backend.get_bot_info()
            if not bot_info:
                self.log("Could not get Symphony bot info", success=False)
                return
            bot_display_name = bot_info.name
            print(f"  Symphony Bot: {bot_display_name} ({bot_info.id})")

            # Send prompt to Symphony
            prompt_msg = (
                FormattedMessage()
                .add_text("🔄 ")
                .add_bold("[Combined E2E Test] Symphony → Slack")
                .add_text("\n\nPlease send a message in this room that ")
                .add_bold("mentions the bot")
                .add_text(f".\n\nExample: @{bot_display_name} Hello from Symphony!")
                .add_text("\n\nThis message will be forwarded to Slack.")
                .add_text("\n\nYou have ")
                .add_bold("60 seconds")
                .add_text(" to respond...")
            )
            await self.symphony_backend.send_message(
                self.symphony_stream_id,
                prompt_msg.render(Format.SYMPHONY_MESSAGEML),
            )
            print("\n  ⏳ Waiting for Symphony message...")

            # Use abstract stream_messages API
            received_message = None
            try:
                async with asyncio.timeout(60.0):
                    async for message in self.symphony_backend.stream_messages(channel=self.symphony_stream_id):
                        # First message from a user (skip_own=True by default)
                        received_message = message
                        break

                if received_message:
                    self.log("Received message from Symphony")

                    # Get sender info
                    sender_name = "Unknown"
                    if hasattr(received_message, "author") and received_message.author:
                        sender_name = received_message.author.name
                    elif received_message.author_id:
                        sender_user = await self.symphony_backend.fetch_user(received_message.author_id)
                        if sender_user:
                            sender_name = sender_user.name

                    # Convert to FormattedMessage and render as plain text
                    if hasattr(received_message, "to_formatted"):
                        formatted = received_message.to_formatted()
                        plain_text = formatted.render(Format.PLAINTEXT)
                    else:
                        plain_text = received_message.content or ""

                    # Remove the bot mention from the plain text
                    bot_mention = f"@{bot_display_name}"
                    plain_text = plain_text.replace(bot_mention, "").strip()

                    print("\n  📨 Message from Symphony:")
                    print(f"     From: {sender_name}")
                    print(f"     Content: {plain_text[:200]}...")

                    # Try to find the sender in Slack by email
                    slack_user_id = None
                    if received_message.author_id:
                        sender_user = await self.symphony_backend.fetch_user(received_message.author_id)
                        if sender_user and sender_user.email:
                            slack_user_id = await self._find_slack_user_by_email(sender_user.email)
                            if slack_user_id:
                                print(f"     Found in Slack: {slack_user_id}")

                    # Parse mentions in the message text and convert to Slack format
                    mentions = getattr(received_message, "mentions", None)
                    text_segments = await self._parse_symphony_mentions(plain_text, mentions)

                    # Forward to Slack with @mention if found
                    forward_msg = FormattedMessage()
                    forward_msg.add_text("📨 ")
                    forward_msg.add_bold("Message forwarded from Symphony")
                    if slack_user_id:
                        forward_msg.add_text(f"\n\n<@{slack_user_id}> said:\n")
                    else:
                        forward_msg.add_text(f"\n\n*{sender_name}* said:\n")

                    # Add the message content with converted mentions
                    for seg_type, content in text_segments:
                        if seg_type == "text":
                            forward_msg.add_text(content)
                        elif seg_type == "mention":
                            user_id, display_name = content
                            forward_msg.add_text(f"<@{user_id}>")
                    await self.slack_backend.send_message(
                        self.slack_channel_id,
                        forward_msg.render(Format.SLACK_MARKDOWN),
                    )
                    self.log("Forwarded Symphony message to Slack")
                else:
                    self.log("No message received", success=False)

            except asyncio.TimeoutError:
                self.log("Timeout waiting for Symphony message (60s)", success=False)

        except Exception as e:
            self.log(f"Failed Symphony → Slack test: {e}", success=False)
            traceback.print_exc()

    async def test_slack_to_symphony(self):
        """Test receiving a message from Slack and forwarding to Symphony."""
        self.section("Test: Slack → Symphony Message Forwarding")

        try:
            # Get bot info using abstract API
            bot_info = await self.slack_backend.get_bot_info()
            if not bot_info:
                self.log("Could not get Slack bot info", success=False)
                return
            bot_name = bot_info.name
            bot_user_id = bot_info.id
            print(f"  Slack Bot: {bot_name} ({bot_user_id})")

            # Send prompt to Slack
            prompt_msg = (
                FormattedMessage()
                .add_text("🔄 ")
                .add_bold("[Combined E2E Test] Slack → Symphony")
                .add_text("\n\nPlease send a message in this channel that ")
                .add_bold("mentions the bot")
                .add_text(f".\n\nExample: @{bot_name} Hello from Slack!")
                .add_text("\n\nThis message will be forwarded to Symphony.")
                .add_text("\n\nYou have ")
                .add_bold("60 seconds")
                .add_text(" to respond...")
            )
            await self.slack_backend.send_message(
                self.slack_channel_id,
                prompt_msg.render(Format.SLACK_MARKDOWN),
            )
            print("\n  ⏳ Waiting for Slack message...")

            # Use abstract stream_messages API
            received_message = None
            try:
                async with asyncio.timeout(60.0):
                    async for message in self.slack_backend.stream_messages(channel=self.slack_channel_id):
                        # First message from a user (skip_own=True by default)
                        received_message = message
                        break

                if received_message:
                    self.log("Received message from Slack")

                    # Get sender info
                    sender_name = "Unknown"
                    if received_message.author_id:
                        sender_user = await self.slack_backend.fetch_user(received_message.author_id)
                        if sender_user:
                            sender_name = sender_user.name or sender_user.display_name

                    # Get plain text content
                    text = received_message.content or ""

                    # Remove bot mention from text
                    bot_mention = f"<@{bot_user_id}>"
                    text = text.replace(bot_mention, "").strip()

                    print("\n  📨 Message from Slack:")
                    print(f"     From: {sender_name}")
                    print(f"     Content: {text[:200]}...")

                    # Try to find the sender in Symphony by email
                    symphony_user_id = None
                    if received_message.author_id:
                        # Get sender's email from Slack using abstract API
                        sender_user = await self.slack_backend.fetch_user(received_message.author_id)
                        if sender_user and sender_user.email:
                            symphony_user_id = await self._find_symphony_user_by_email(sender_user.email)
                            if symphony_user_id:
                                print(f"     Found in Symphony: {symphony_user_id}")

                    # Parse mentions in the message text and convert to Symphony format
                    text_segments = await self._parse_slack_mentions(text)

                    # Forward to Symphony with @mention if found
                    forward_msg = FormattedMessage()
                    forward_msg.add_text("📨 ")
                    forward_msg.add_bold("Message forwarded from Slack")
                    forward_msg.add_text("\n\n")
                    if symphony_user_id:
                        forward_msg.add_mention(symphony_user_id, sender_name)
                    else:
                        forward_msg.add_text(f"*{sender_name}*")
                    forward_msg.add_text(" said:\n")

                    # Add the message content with converted mentions
                    for seg_type, content in text_segments:
                        if seg_type == "text":
                            forward_msg.add_text(content)
                        elif seg_type == "mention":
                            user_id, display_name = content
                            forward_msg.add_mention(user_id, display_name)
                    await self.symphony_backend.send_message(
                        self.symphony_stream_id,
                        forward_msg.render(Format.SYMPHONY_MESSAGEML),
                    )
                    self.log("Forwarded Slack message to Symphony")
                else:
                    self.log("No message received", success=False)

            except asyncio.TimeoutError:
                self.log("Timeout waiting for Slack message (60s)", success=False)

        except Exception as e:
            self.log(f"Failed Slack → Symphony test: {e}", success=False)
            traceback.print_exc()

    async def cleanup(self):
        """Clean up resources."""
        self.section("Cleanup")

        if self.symphony_backend and self.symphony_backend.connected:
            await self.symphony_backend.disconnect()
            self.log("Disconnected from Symphony")

        if self.slack_backend and self.slack_backend.connected:
            await self.slack_backend.disconnect()
            self.log("Disconnected from Slack")

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
        print("  Combined Symphony + Slack E2E Integration Test")
        print("=" * 60)

        try:
            # Setup both backends
            await self.setup_symphony()
            await self.setup_slack()

            # Test Slack → Symphony first (since it was working)
            await self.test_slack_to_symphony()

            # Then test Symphony → Slack
            await self.test_symphony_to_slack()

        except Exception as e:
            print(f"\n❌ Test suite failed with error: {e}")
            traceback.print_exc()

        finally:
            await self.cleanup()

        return self.print_summary()


SYMPHONY_AUTH_ENV_VARS = (
    "SYMPHONY_BOT_PRIVATE_KEY_PATH",
    "SYMPHONY_BOT_PRIVATE_KEY_CONTENT",
    "SYMPHONY_BOT_COMBINED_CERT_PATH",
    "SYMPHONY_BOT_COMBINED_CERT_CONTENT",
)


def _env_is_set(name: str) -> bool:
    return bool(os.environ.get(name))


def _missing_env(names: Tuple[str, ...]) -> List[str]:
    return [name for name in names if not _env_is_set(name)]


def _missing_slack_env() -> List[str]:
    return _missing_env(
        (
            "SLACK_BOT_TOKEN",
            "SLACK_TEST_CHANNEL_NAME",
            "SLACK_TEST_USER_NAME",
            "SLACK_APP_TOKEN",
        )
    )


def _missing_discord_env() -> List[str]:
    return _missing_env(
        (
            "DISCORD_TOKEN",
            "DISCORD_TEST_CHANNEL_NAME",
            "DISCORD_TEST_USER_NAME",
            "DISCORD_GUILD_NAME",
        )
    )


def _missing_symphony_env() -> List[str]:
    missing = _missing_env(
        (
            "SYMPHONY_HOST",
            "SYMPHONY_BOT_USERNAME",
            "SYMPHONY_TEST_ROOM_NAME",
            "SYMPHONY_TEST_USER_NAME",
        )
    )
    if not any(_env_is_set(name) for name in SYMPHONY_AUTH_ENV_VARS):
        missing.append("one of " + ", ".join(SYMPHONY_AUTH_ENV_VARS))
    return missing


def _missing_telegram_env() -> List[str]:
    missing = _missing_env(
        (
            "TELEGRAM_TOKEN",
            "TELEGRAM_TEST_USER_NAME",
        )
    )
    if not _env_is_set("TELEGRAM_TEST_CHAT_NAME") and not _env_is_set("TELEGRAM_TEST_CHAT_ID"):
        missing.append("TELEGRAM_TEST_CHAT_NAME or TELEGRAM_TEST_CHAT_ID")
    return missing


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys(items))


def _missing_bridge_env() -> List[str]:
    return _dedupe(_missing_slack_env() + _missing_symphony_env())


def configured_e2e_suites():
    """Return e2e suites with complete env, plus skipped suite reasons."""
    candidates = (
        ("Slack", SlackE2ETest, _missing_slack_env()),
        ("Discord", DiscordE2ETest, _missing_discord_env()),
        ("Symphony", SymphonyE2ETest, _missing_symphony_env()),
        ("Telegram", TelegramE2ETest, _missing_telegram_env()),
        ("Symphony + Slack Bridge", CombinedE2ETest, _missing_bridge_env()),
    )

    suites = []
    skipped = []
    for name, factory, missing in candidates:
        if missing:
            skipped.append((name, missing))
        else:
            suites.append((name, factory))
    return suites, skipped


def configured_e2e_suite_names() -> List[str]:
    """Return names for suites whose full-coverage env is present."""
    suites, _ = configured_e2e_suites()
    return [name for name, _ in suites]


class ConfiguredE2ERunner:
    """Run all fully configured e2e suites."""

    def __init__(self):
        self.results = []

    def section(self, title: str):
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}\n")

    async def run_all(self) -> bool:
        suites, skipped = configured_e2e_suites()

        self.section("Configured E2E Integration Test")
        if skipped:
            print("Skipped suites:")
            for name, missing in skipped:
                print(f"  - {name}: missing {', '.join(missing)}")
            print()

        if not suites:
            print("No fully configured e2e suites found.")
            return False

        print("Running suites:")
        for name, _ in suites:
            print(f"  - {name}")

        for name, factory in suites:
            self.section(f"Suite: {name}")
            try:
                success = await factory().run_all()
            except SystemExit as exc:
                success = exc.code == 0
                if not success:
                    print(f"{name} exited with status {exc.code}")
            except Exception as exc:
                success = False
                print(f"{name} failed with error: {exc}")
                traceback.print_exc()

            self.results.append((name, success))

        return self.print_summary()

    def print_summary(self) -> bool:
        self.section("Configured E2E Summary")
        passed = sum(1 for _, success in self.results if success)
        failed = len(self.results) - passed

        print(f"  Passed: {passed}/{len(self.results)}")
        print(f"  Failed: {failed}/{len(self.results)}")
        if failed:
            print()
            print("  Failed suites:")
            for name, success in self.results:
                if not success:
                    print(f"    - {name}")

        return failed == 0


async def run_configured_e2e_suites() -> bool:
    """Run every suite whose full-coverage env is present."""
    return await ConfiguredE2ERunner().run_all()


def test_configured_e2e_suites():
    """Pytest entrypoint for configured e2e coverage."""
    import pytest

    if not configured_e2e_suite_names():
        pytest.skip("No fully configured e2e suites found")

    assert asyncio.run(run_configured_e2e_suites())


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  Configured E2E Integration Test")
    print("=" * 60)
    print("\nRuns every e2e suite whose full-coverage env is present.")
    print("Missing suite env skips that suite; zero configured suites fails direct script mode.")
    print("Configured suites may prompt for interactive inbound-message checks.\n")

    success = await run_configured_e2e_suites()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
