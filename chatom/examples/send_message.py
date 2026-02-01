#!/usr/bin/env python
"""Send Message Example.

This example demonstrates how to send messages to channels
using different backends.

Environment Variables:
    For Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token
        SLACK_TEST_CHANNEL_NAME: Channel to send messages to

    For Discord:
        DISCORD_TOKEN: Your Discord bot token
        DISCORD_GUILD_NAME: The Discord server name
        DISCORD_TEST_CHANNEL_NAME: Channel to send messages to

    For Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key
        SYMPHONY_TEST_ROOM_NAME: Room to send messages to

Usage:
    python -m chatom.examples.send_message --backend slack --message "Hello World!"
"""

import argparse
import asyncio
import os
import sys
from typing import Optional


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Missing required environment variable: {name}")
        return None
    return value


async def send_slack_message(message: str) -> bool:
    """Send a message to Slack."""
    from chatom.slack import SlackBackend, SlackConfig

    bot_token = get_env("SLACK_BOT_TOKEN")
    channel_name = get_env("SLACK_TEST_CHANNEL_NAME")
    if not bot_token or not channel_name:
        return False

    config = SlackConfig(bot_token=bot_token)
    backend = SlackBackend(config=config)

    await backend.connect()

    # Look up the channel by name
    channel = await backend.fetch_channel(name=channel_name)
    if not channel:
        print(f"❌ Channel '{channel_name}' not found")
        await backend.disconnect()
        return False

    # Send the message
    sent_message = await backend.send_message(
        channel=channel.id,
        content=message,
    )

    print(f"✅ Message sent to #{channel_name}")
    print(f"   Message ID: {sent_message.id}")
    print(f"   Timestamp: {sent_message.created_at}")

    await backend.disconnect()
    return True


async def send_discord_message(message: str) -> bool:
    """Send a message to Discord."""
    from chatom.discord import DiscordBackend, DiscordConfig

    bot_token = get_env("DISCORD_TOKEN")
    guild_name = get_env("DISCORD_GUILD_NAME")
    channel_name = get_env("DISCORD_TEST_CHANNEL_NAME")
    if not bot_token or not guild_name or not channel_name:
        return False

    config = DiscordConfig(
        token=bot_token,
        intents=["guilds", "guild_messages"],
    )
    backend = DiscordBackend(config=config)

    await backend.connect()

    # Find the guild
    guild = await backend.fetch_organization(name=guild_name)
    if not guild:
        print(f"❌ Guild '{guild_name}' not found")
        await backend.disconnect()
        return False

    backend.config.guild_id = guild.id

    # Look up the channel by name
    channel = await backend.fetch_channel(name=channel_name)
    if not channel:
        print(f"❌ Channel '{channel_name}' not found")
        await backend.disconnect()
        return False

    # Send the message
    sent_message = await backend.send_message(
        channel=channel.id,
        content=message,
    )

    print(f"✅ Message sent to #{channel_name}")
    print(f"   Message ID: {sent_message.id}")

    await backend.disconnect()
    return True


async def send_symphony_message(message: str) -> bool:
    """Send a message to Symphony."""
    from chatom.symphony import SymphonyBackend, SymphonyConfig

    host = get_env("SYMPHONY_HOST")
    bot_username = get_env("SYMPHONY_BOT_USERNAME")
    room_name = get_env("SYMPHONY_TEST_ROOM_NAME")
    private_key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
    private_key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)

    if not host or not bot_username or not room_name:
        return False

    if not private_key_path and not private_key_content:
        print("Missing: SYMPHONY_BOT_PRIVATE_KEY_PATH or SYMPHONY_BOT_PRIVATE_KEY_CONTENT")
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

    # Look up the room by name
    room = await backend.fetch_channel(name=room_name)
    if not room:
        print(f"❌ Room '{room_name}' not found")
        await backend.disconnect()
        return False

    # Send the message
    sent_message = await backend.send_message(
        channel=room.id,
        content=message,
    )

    print(f"✅ Message sent to {room_name}")
    print(f"   Message ID: {sent_message.id}")

    await backend.disconnect()
    return True


async def main(backend_name: str, message: str) -> bool:
    """Run the send message example."""
    backends = {
        "slack": send_slack_message,
        "discord": send_discord_message,
        "symphony": send_symphony_message,
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        return False

    return await backends[backend_name](message)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send message example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to use",
    )
    parser.add_argument(
        "--message",
        default="Hello from chatom! 👋",
        help="Message to send",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend, args.message))
    sys.exit(0 if success else 1)
