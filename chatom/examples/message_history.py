#!/usr/bin/env python
"""Message History Example.

This example demonstrates how to read message history from channels.

Environment Variables:
    For Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token
        SLACK_TEST_CHANNEL_NAME: Channel to read from

    For Discord:
        DISCORD_TOKEN: Your Discord bot token
        DISCORD_GUILD_NAME: The Discord server name
        DISCORD_TEST_CHANNEL_NAME: Channel to read from

    For Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key
        SYMPHONY_TEST_ROOM_NAME: Room to read from

Usage:
    python -m chatom.examples.message_history --backend slack --limit 10
"""

import argparse
import asyncio
import os
import sys
from typing import Optional


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Missing required environment variable: {name}")
        return None
    return value


async def read_slack_history(limit: int) -> bool:
    """Read message history from Slack."""
    from chatom.slack import SlackBackend, SlackConfig

    bot_token = get_env("SLACK_BOT_TOKEN")
    channel_name = get_env("SLACK_TEST_CHANNEL_NAME")
    if not bot_token or not channel_name:
        return False

    config = SlackConfig(bot_token=bot_token)
    backend = SlackBackend(config=config)

    await backend.connect()

    channel = await backend.fetch_channel(name=channel_name)
    if not channel:
        print(f"❌ Channel '{channel_name}' not found")
        await backend.disconnect()
        return False

    print(f"📖 Reading last {limit} messages from #{channel_name}:\n")

    count = 0
    async for message in backend.read_messages(channel=channel.id, limit=limit):
        count += 1
        # Format author name
        author = message.author_id
        if message.author:
            author = message.author.name or message.author_id

        # Truncate long messages
        content = message.content or ""
        if len(content) > 80:
            content = content[:77] + "..."
        content = content.replace("\n", " ")

        timestamp = ""
        if message.created_at:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M")

        print(f"{count:3}. [{timestamp}] {author}: {content}")

    print(f"\n✅ Read {count} messages")

    await backend.disconnect()
    return True


async def read_discord_history(limit: int) -> bool:
    """Read message history from Discord."""
    from chatom.discord import DiscordBackend, DiscordConfig

    bot_token = get_env("DISCORD_TOKEN")
    guild_name = get_env("DISCORD_GUILD_NAME")
    channel_name = get_env("DISCORD_TEST_CHANNEL_NAME")
    if not bot_token or not guild_name or not channel_name:
        return False

    config = DiscordConfig(
        token=bot_token,
        intents=["guilds", "guild_messages", "message_content"],
    )
    backend = DiscordBackend(config=config)

    await backend.connect()

    guild = await backend.fetch_organization(name=guild_name)
    if not guild:
        print(f"❌ Guild '{guild_name}' not found")
        await backend.disconnect()
        return False

    backend.config.guild_id = guild.id

    channel = await backend.fetch_channel(name=channel_name)
    if not channel:
        print(f"❌ Channel '{channel_name}' not found")
        await backend.disconnect()
        return False

    print(f"📖 Reading last {limit} messages from #{channel_name}:\n")

    count = 0
    async for message in backend.read_messages(channel=channel.id, limit=limit):
        count += 1
        author = message.author_id
        if message.author:
            author = message.author.name or message.author_id

        content = message.content or ""
        if len(content) > 80:
            content = content[:77] + "..."
        content = content.replace("\n", " ")

        timestamp = ""
        if message.created_at:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M")

        print(f"{count:3}. [{timestamp}] {author}: {content}")

    print(f"\n✅ Read {count} messages")

    await backend.disconnect()
    return True


async def read_symphony_history(limit: int) -> bool:
    """Read message history from Symphony."""
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

    room = await backend.fetch_channel(name=room_name)
    if not room:
        print(f"❌ Room '{room_name}' not found")
        await backend.disconnect()
        return False

    print(f"📖 Reading last {limit} messages from {room_name}:\n")

    count = 0
    async for message in backend.read_messages(channel=room.id, limit=limit):
        count += 1
        author = message.author_id
        if message.author:
            author = message.author.name or message.author_id

        content = message.content or ""
        if len(content) > 80:
            content = content[:77] + "..."
        content = content.replace("\n", " ")

        timestamp = ""
        if message.created_at:
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M")

        print(f"{count:3}. [{timestamp}] {author}: {content}")

    print(f"\n✅ Read {count} messages")

    await backend.disconnect()
    return True


async def main(backend_name: str, limit: int) -> bool:
    """Run the message history example."""
    backends = {
        "slack": lambda: read_slack_history(limit),
        "discord": lambda: read_discord_history(limit),
        "symphony": lambda: read_symphony_history(limit),
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        return False

    return await backends[backend_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Message history example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to use",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of messages to read",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend, args.limit))
    sys.exit(0 if success else 1)
