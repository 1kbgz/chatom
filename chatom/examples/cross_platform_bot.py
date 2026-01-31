#!/usr/bin/env python
"""Cross-Platform Bot Example.

This example demonstrates how to build a bot that works across
multiple platforms simultaneously.

Environment Variables:
    SLACK_BOT_TOKEN: Your Slack bot OAuth token
    SLACK_APP_TOKEN: Your Slack app token for Socket Mode
    SLACK_TEST_CHANNEL_NAME: Channel to use for Slack

    DISCORD_TOKEN: Your Discord bot token
    DISCORD_GUILD_NAME: The Discord server name
    DISCORD_TEST_CHANNEL_NAME: Channel to use for Discord

Usage:
    python -m chatom.examples.cross_platform_bot
"""

import asyncio
import os
import sys
from typing import Dict, List, Optional

from chatom.backend import BackendBase
from chatom.base import Message
from chatom.format import FormattedMessage


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable."""
    value = os.environ.get(name)
    if required and not value:
        return None
    return value


class CrossPlatformBot:
    """A bot that can run on multiple platforms simultaneously."""

    def __init__(self):
        self.backends: Dict[str, BackendBase] = {}
        self.channels: Dict[str, str] = {}  # backend_name -> channel_id

    async def add_slack(self) -> bool:
        """Add Slack backend."""
        from chatom.slack import SlackBackend, SlackConfig

        bot_token = get_env("SLACK_BOT_TOKEN", required=False)
        app_token = get_env("SLACK_APP_TOKEN", required=False)
        channel_name = get_env("SLACK_TEST_CHANNEL_NAME", required=False)

        if not bot_token or not channel_name:
            print("⏭️ Skipping Slack (missing credentials)")
            return False

        config = SlackConfig(
            bot_token=bot_token,
            app_token=app_token or "",
        )
        backend = SlackBackend(config=config)

        await backend.connect()

        channel = await backend.fetch_channel(name=channel_name)
        if not channel:
            print(f"❌ Slack channel '{channel_name}' not found")
            await backend.disconnect()
            return False

        self.backends["slack"] = backend
        self.channels["slack"] = channel.id
        print(f"✅ Connected to Slack (#{channel_name})")
        return True

    async def add_discord(self) -> bool:
        """Add Discord backend."""
        from chatom.discord import DiscordBackend, DiscordConfig

        bot_token = get_env("DISCORD_TOKEN", required=False)
        guild_name = get_env("DISCORD_GUILD_NAME", required=False)
        channel_name = get_env("DISCORD_TEST_CHANNEL_NAME", required=False)

        if not bot_token or not guild_name or not channel_name:
            print("⏭️ Skipping Discord (missing credentials)")
            return False

        config = DiscordConfig(
            bot_token=bot_token,
            intents=["guilds", "guild_messages"],
        )
        backend = DiscordBackend(config=config)

        await backend.connect()

        guild = await backend.fetch_organization(name=guild_name)
        if not guild:
            print(f"❌ Discord guild '{guild_name}' not found")
            await backend.disconnect()
            return False

        backend.config.guild_id = guild.id

        channel = await backend.fetch_channel(name=channel_name)
        if not channel:
            print(f"❌ Discord channel '{channel_name}' not found")
            await backend.disconnect()
            return False

        self.backends["discord"] = backend
        self.channels["discord"] = channel.id
        print(f"✅ Connected to Discord (#{channel_name})")
        return True

    async def add_symphony(self) -> bool:
        """Add Symphony backend."""
        from chatom.symphony import SymphonyBackend, SymphonyConfig

        host = get_env("SYMPHONY_HOST", required=False)
        bot_username = get_env("SYMPHONY_BOT_USERNAME", required=False)
        room_name = get_env("SYMPHONY_TEST_ROOM_NAME", required=False)
        private_key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
        private_key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)

        if not host or not bot_username or not room_name:
            print("⏭️ Skipping Symphony (missing credentials)")
            return False

        if not private_key_path and not private_key_content:
            print("⏭️ Skipping Symphony (missing key)")
            return False

        config_kwargs = {
            "host": host,
            "bot_username": bot_username,
        }

        if private_key_path:
            config_kwargs["bot_private_key_path"] = private_key_path
        elif private_key_content:
            from pydantic import SecretStr

            config_kwargs["bot_private_key_content"] = SecretStr(private_key_content)

        config = SymphonyConfig(**config_kwargs)
        backend = SymphonyBackend(config=config)

        await backend.connect()

        room = await backend.fetch_channel(name=room_name)
        if not room:
            print(f"❌ Symphony room '{room_name}' not found")
            await backend.disconnect()
            return False

        self.backends["symphony"] = backend
        self.channels["symphony"] = room.id
        print(f"✅ Connected to Symphony ({room_name})")
        return True

    async def broadcast(self, content: str) -> List[Message]:
        """Send a message to all connected platforms.

        Uses FormattedMessage to render appropriately for each backend.
        """
        results = []

        msg = FormattedMessage()
        msg.bold("📢 Cross-Platform Broadcast")
        msg.newline()
        msg.text(content)

        for name, backend in self.backends.items():
            channel_id = self.channels[name]
            rendered = msg.render(backend.get_format())

            sent = await backend.send_message(
                channel_id=channel_id,
                content=rendered,
            )
            results.append(sent)
            print(f"   → Sent to {name}: {sent.id}")

        return results

    async def disconnect_all(self):
        """Disconnect from all backends."""
        for name, backend in self.backends.items():
            await backend.disconnect()
            print(f"🔌 Disconnected from {name}")


async def main() -> bool:
    """Run the cross-platform bot example."""
    bot = CrossPlatformBot()

    print("🤖 Cross-Platform Bot Starting...\n")

    # Try to connect to all available backends
    await bot.add_slack()
    await bot.add_discord()
    await bot.add_symphony()

    if not bot.backends:
        print("\n❌ No backends configured. Set environment variables for at least one platform.")
        return False

    print(f"\n📡 Connected to {len(bot.backends)} platform(s): {list(bot.backends.keys())}")

    # Send a broadcast message
    print("\n📤 Broadcasting message to all platforms...")
    await bot.broadcast("Hello from the cross-platform chatom bot! 🌐")

    # Send platform-specific information
    print("\n📊 Sending status to each platform...")
    for name, backend in bot.backends.items():
        channel_id = bot.channels[name]

        msg = FormattedMessage()
        msg.heading("Platform Status", level=3)
        msg.text(f"Backend: {backend.display_name}")
        msg.newline()
        msg.text(f"Format: {backend.get_format().name}")
        msg.newline()
        msg.text(f"Capabilities: {backend.capabilities}")

        await backend.send_message(
            channel_id=channel_id,
            content=msg.render(backend.get_format()),
        )
        print(f"   → Sent status to {name}")

    # Cleanup
    print()
    await bot.disconnect_all()

    print("\n✅ Cross-platform bot example complete!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
