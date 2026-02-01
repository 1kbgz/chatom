#!/usr/bin/env python
"""Symphony End-to-End Integration Test.

This script tests all Symphony backend functionality with a real Symphony pod.
It requires human interaction to verify the bot's behavior.

Environment Variables Required:
    SYMPHONY_HOST: Your Symphony pod hostname (e.g., mycompany.symphony.com)
    SYMPHONY_BOT_USERNAME: Bot's service account username
    SYMPHONY_TEST_ROOM_NAME: Name of the room where tests will run
    SYMPHONY_TEST_USER_NAME: Username (e.g., "jsmith") for mention tests

    Authentication (one of the following):
    SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key file
    SYMPHONY_BOT_PRIVATE_KEY_CONTENT: RSA private key content (PEM format)
    SYMPHONY_BOT_COMBINED_CERT_PATH: Path to combined cert file (key+cert in PEM)
    SYMPHONY_BOT_COMBINED_CERT_CONTENT: Combined cert content (key+cert in PEM)

Optional Environment Variables:
    SYMPHONY_AGENT_HOST: Separate agent hostname (if different from pod)
    SYMPHONY_SESSION_AUTH_HOST: Separate session auth hostname
    SYMPHONY_KEY_MANAGER_HOST: Separate key manager hostname

Usage:
    export SYMPHONY_HOST="mycompany.symphony.com"
    export SYMPHONY_BOT_USERNAME="my-bot"
    export SYMPHONY_BOT_COMBINED_CERT_PATH="/path/to/combined.pem"
    export SYMPHONY_TEST_ROOM_NAME="E2E Test Room"
    export SYMPHONY_TEST_USER_NAME="jsmith"
    python -m chatom.tests.integration.e2e.symphony

The bot will:
1. Connect and display bot info
2. Test sending plain messages
3. Test MessageML formatted messages
4. Test mentions (<mention uid="..."/>)
5. Test hashtags (<hash tag="..."/>)
6. Test cashtags (<cash tag="..."/>)
7. Test reading message history
8. Test presence (get/set status)
9. Test user lookup
10. Test creating rooms/IMs
11. Test inbound messages (prompts you to @mention the bot)

Watch the test stream and interact when prompted.
The inbound message test will ask you to send a message mentioning the bot.
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime
from typing import Optional

from chatom.base import Channel
from chatom.format import Format, FormattedMessage, Table
from chatom.symphony import SymphonyBackend, SymphonyConfig, format_cashtag, format_hashtag, mention_user_by_uid


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"❌ Missing required environment variable: {name}")
        print(f"   Set it with: export {name}='your-value'")
        sys.exit(1)
    return value


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
                session = await self.backend._get_session_info()
                bot_user_id = str(session.get("userId", ""))
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
                    session = await self.backend._get_session_info()
                    bot_user_id = str(session.get("userId", ""))
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
            import os as temp_os
            import tempfile

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
                temp_os.unlink(temp_file_path)

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
                self.log("Timeout waiting for inbound message (30s)", success=False)
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
                    received_message.mentions_user(bot_user_id)
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
            import traceback

            traceback.print_exc()

        finally:
            await self.cleanup()

        return self.print_summary()


async def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  Symphony E2E Integration Test")
    print("=" * 60)
    print("\nThis test requires:")
    print("  - SYMPHONY_HOST: Your Symphony pod hostname")
    print("  - SYMPHONY_BOT_USERNAME: Bot's service account username")
    print("  - SYMPHONY_TEST_ROOM_NAME: Name of room to run tests in")
    print("  - SYMPHONY_TEST_USER_NAME: Username for mention tests")
    print("\nAuthentication (one of):")
    print("  - SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key")
    print("  - SYMPHONY_BOT_PRIVATE_KEY_CONTENT: RSA key content (PEM)")
    print("  - SYMPHONY_BOT_COMBINED_CERT_PATH: Path to combined cert (key+cert)")
    print("  - SYMPHONY_BOT_COMBINED_CERT_CONTENT: Combined cert content")
    print("\nOptional (for separate endpoints):")
    print("  - SYMPHONY_AGENT_HOST: Separate agent hostname")
    print("  - SYMPHONY_SESSION_AUTH_HOST: Separate session auth hostname")
    print("  - SYMPHONY_KEY_MANAGER_HOST: Separate key manager hostname")
    print("\nThe bot needs these permissions:")
    print("  - Search rooms (to look up room by name)")
    print("  - Look up users (to resolve username)")
    print("  - Send messages to the test room")
    print("  - Read messages from the test room")
    print("  - Set presence")
    print("\nThe bot will send messages to the test room.")
    print("Please watch the stream and interact when prompted.\n")

    test = SymphonyE2ETest()
    success = await test.run_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
