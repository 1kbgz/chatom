#!/usr/bin/env python
"""Combined Symphony + Slack End-to-End Integration Test.

This script tests cross-platform messaging between Symphony and Slack.
It connects to both platforms simultaneously and forwards messages between them.

Environment Variables Required:
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
        SLACK_APP_TOKEN: App token for Socket Mode (xapp-...) - REQUIRED for this test

Usage:
    python -m chatom.tests.integration.e2e.combined

The test will:
1. Connect to both Symphony and Slack
2. Prompt you to send a message mentioning the bot in Symphony
3. Forward the Symphony message to Slack
4. Prompt you to send a message mentioning the bot in Slack
5. Forward the Slack message to Symphony
"""

import asyncio
import os
import sys
import traceback
from typing import Optional

# Chatom imports
from chatom.format import Format, FormattedMessage
from chatom.slack import SlackBackend, SlackConfig
from chatom.symphony import SymphonyBackend, SymphonyConfig


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"❌ Missing required environment variable: {name}")
        print(f"   Set it with: export {name}='your-value'")
        sys.exit(1)
    return value


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
            response = await self.slack_backend._async_client.users_lookupByEmail(email=email)
            if response.get("ok"):
                return response.get("user", {}).get("id")
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

                    # Forward to Slack with @mention if found
                    if slack_user_id:
                        forward_msg = (
                            FormattedMessage()
                            .add_text("📨 ")
                            .add_bold("Message forwarded from Symphony")
                            .add_text(f"\n\n<@{slack_user_id}> said:\n")
                            .add_text(f"{plain_text}")
                        )
                    else:
                        forward_msg = (
                            FormattedMessage()
                            .add_text("📨 ")
                            .add_bold("Message forwarded from Symphony")
                            .add_text(f"\n\n*{sender_name}* said:\n")
                            .add_text(f"{plain_text}")
                        )
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
                        # Get sender's email from Slack
                        try:
                            user_info = await self.slack_backend._async_client.users_info(user=received_message.author_id)
                            if user_info.get("ok"):
                                sender_email = user_info.get("user", {}).get("profile", {}).get("email")
                                if sender_email:
                                    symphony_user_id = await self._find_symphony_user_by_email(sender_email)
                                    if symphony_user_id:
                                        print(f"     Found in Symphony: {symphony_user_id}")
                        except Exception:
                            pass

                    # Forward to Symphony with @mention if found
                    if symphony_user_id:
                        forward_msg = (
                            FormattedMessage()
                            .add_text("📨 ")
                            .add_bold("Message forwarded from Slack")
                            .add_text("\n\n")
                            .add_mention(symphony_user_id, sender_name)
                            .add_text(" said:\n")
                            .add_text(f"{text}")
                        )
                    else:
                        forward_msg = (
                            FormattedMessage()
                            .add_text("📨 ")
                            .add_bold("Message forwarded from Slack")
                            .add_text(f"\n\n*{sender_name}* said:\n")
                            .add_text(f"{text}")
                        )
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


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  Combined Symphony + Slack E2E Integration Test")
    print("=" * 60)
    print("\nThis test requires credentials for BOTH Symphony and Slack.")
    print("\nSymphony environment variables:")
    print("  - SYMPHONY_HOST, SYMPHONY_BOT_USERNAME")
    print("  - SYMPHONY_BOT_PRIVATE_KEY_PATH or SYMPHONY_BOT_COMBINED_CERT_PATH")
    print("  - SYMPHONY_TEST_ROOM_NAME, SYMPHONY_TEST_USER_NAME")
    print("\nSlack environment variables:")
    print("  - SLACK_BOT_TOKEN (xoxb-...)")
    print("  - SLACK_APP_TOKEN (xapp-...) - REQUIRED for Socket Mode")
    print("  - SLACK_TEST_CHANNEL_NAME, SLACK_TEST_USER_NAME")
    print("\nThe test will:")
    print("  1. Connect to both Symphony and Slack")
    print("  2. Ask you to send a message in Slack → forward to Symphony")
    print("  3. Ask you to send a message in Symphony → forward to Slack")
    print("\nWatch both platforms and interact when prompted.\n")

    test = CombinedE2ETest()
    success = await test.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
