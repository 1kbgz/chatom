#!/usr/bin/env python
"""Slack End-to-End Integration Test.

This script tests all Slack backend functionality with a real Slack app.
It requires human interaction to verify the bot's behavior.

Environment Variables Required:
    SLACK_BOT_TOKEN: Your Slack bot OAuth token (xoxb-...)
    SLACK_TEST_CHANNEL_NAME: A channel name where tests will run (without #)
    SLACK_TEST_USER_NAME: A Slack username for mention tests (without @)
    SLACK_APP_TOKEN: (Optional) App token for Socket Mode (xapp-...)

Usage:
    export SLACK_BOT_TOKEN="xoxb-your-token"
    export SLACK_TEST_CHANNEL_NAME="test-channel"
    export SLACK_TEST_USER_NAME="john.doe"
    python -m chatom.tests.integration.e2e.slack

The bot will:
1. Connect and display bot info
2. Test sending plain messages
3. Test formatted messages (bold, italic, code with mrkdwn)
4. Test mentions (<@user>, <#channel>)
5. Test reactions (add/remove emoji)
6. Test threads (create, reply)
7. Test reading message history
8. Test presence (get/set status)
9. Test user/channel lookup
10. Test creating channels/DMs
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

# Chatom imports
from chatom.format import Format, FormattedMessage, Table
from chatom.slack import SlackBackend, SlackConfig, mention_channel_all, mention_everyone, mention_here


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"❌ Missing required environment variable: {name}")
        print(f"   Set it with: export {name}='your-value'")
        sys.exit(1)
    return value


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
            print(f"  @here format: {mention_here()}")
            print(f"  @channel format: {mention_channel_all()}")
            print(f"  @everyone format: {mention_everyone()}")

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
                await self.backend.add_reaction(self.channel_id, message_ts, emoji)
                print(f"  Added reaction: :{emoji}:")
                await asyncio.sleep(0.5)  # Rate limit

            self.log(f"Added {len(reactions)} reactions")

            # Wait a moment then remove one
            await asyncio.sleep(2)
            await self.backend.remove_reaction(self.channel_id, message_ts, "thumbsdown")
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
        """Test channel and DM creation."""
        self.section("Test: Room/DM Creation")

        try:
            # Test DM creation with the test user
            if self.user_id:
                print(f"  Creating DM with user {self.user_id}...")
                dm_channel = await self.backend.create_dm(self.user_id)
                if dm_channel:
                    self.log(f"Created DM channel: {dm_channel}")

                    # Send a test message to the DM
                    msg = (
                        FormattedMessage().add_text("🧪 [E2E Test] DM creation test message\n").add_text(f"Created at: {datetime.now().isoformat()}")
                    )
                    await self.backend.send_message(dm_channel, msg.render(Format.SLACK_MARKDOWN))
                    self.log("Sent message to DM")
                else:
                    self.log("DM creation returned no channel ID", success=False)
            else:
                print("  Skipping DM test - no user ID available")

            # Skip channel creation to avoid clutter
            print("\n  Skipping public/private channel creation test to avoid creating test channels.")
            print("  To test, uncomment the code in this method.")

            # Uncomment to test channel creation:
            # timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            # channel_name = f"test-e2e-{timestamp}"
            # print(f"\n  Creating private channel: {channel_name}...")
            # channel_id = await self.backend.create_room(
            #     name=channel_name,
            #     description="Test channel created by E2E test",
            #     public=False,
            # )
            # if channel_id:
            #     self.log(f"Created channel: {channel_name} ({channel_id})")
            #
            #     # Send a test message to the new channel
            #     msg = (
            #         FormattedMessage()
            #         .add_text(f"🧪 [E2E Test] Channel creation test\n")
            #         .add_text(f"Channel: {channel_name}\n")
            #         .add_text(f"Created at: {datetime.now().isoformat()}")
            #     )
            #     await self.backend.send_message(channel_id, msg.render(Format.SLACK_MARKDOWN))
            #     self.log("Sent message to new channel")
            # else:
            #     self.log("Channel creation not supported or failed", success=False)

        except Exception as e:
            self.log(f"Failed to test room/DM creation: {e}", success=False)
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
                self.log("Timeout waiting for inbound message (60s)", success=False)
                return

            if received_message:
                self.log("Received inbound message from user")
                print("\n  📨 Message received:")
                print(f"     Message ID: {received_message.id}")
                print(f"     From: {received_message.author_id}")
                print(f"     Text: {(received_message.content or '')[:200]}...")

                # Check if the bot was mentioned using backend method
                if received_message.mentions_user(bot_user_id):
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

            # Test channel creation (optional)
            await self.test_channel_creation()

            # Test inbound messages (requires app token)
            # Get bot info for inbound test
            bot_user_id = None
            bot_name = "bot"
            try:
                auth_response = await self.backend._async_client.auth_test()
                if auth_response.get("ok"):
                    bot_user_id = auth_response.get("user_id")
                    bot_name = auth_response.get("user", "bot")
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


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  Slack E2E Integration Test")
    print("=" * 60)
    print("\nThis test requires:")
    print("  - SLACK_BOT_TOKEN: Your Slack bot token (xoxb-...)")
    print("  - SLACK_TEST_CHANNEL_NAME: Channel name to run tests in (without #)")
    print("  - SLACK_TEST_USER_NAME: Username for mention tests (without @)")
    print("\nOptional:")
    print("  - SLACK_APP_TOKEN: App token for Socket Mode (xapp-...) - enables inbound message test")
    print("\nRequired Slack app scopes:")
    print("  - chat:write (send messages)")
    print("  - channels:read (read channel info)")
    print("  - channels:history (read message history)")
    print("  - users:read (read user info)")
    print("  - reactions:write (add reactions)")
    print("  - users.profile:write (set status, optional)")
    print("  - im:write (create DMs)")
    print("  - connections:write (Socket Mode, for inbound messages)")
    print("\nThe bot will send messages to the test channel.")
    print("Please watch the channel and interact when prompted.\n")

    test = SlackE2ETest()
    success = await test.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
