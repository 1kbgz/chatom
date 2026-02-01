#!/usr/bin/env python
"""Basic Connection Example.

This example demonstrates how to connect to different chat backends
and perform basic operations.

Environment Variables:
    For Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token (xoxb-...)

    For Discord:
        DISCORD_TOKEN: Your Discord bot token
        DISCORD_GUILD_NAME: The Discord server name

    For Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key file

Usage:
    python -m chatom.examples.basic_connection --backend slack
    python -m chatom.examples.basic_connection --backend discord
    python -m chatom.examples.basic_connection --backend symphony
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


async def connect_slack():
    """Connect to Slack and display connection info."""
    from chatom.slack import SlackBackend, SlackConfig

    bot_token = get_env("SLACK_BOT_TOKEN")
    if not bot_token:
        return False

    config = SlackConfig(bot_token=bot_token)
    backend = SlackBackend(config=config)

    print("Connecting to Slack...")
    await backend.connect()

    print("✅ Connected successfully!")
    print(f"   Backend: {backend.display_name}")
    print(f"   Capabilities: {backend.capabilities}")

    await backend.disconnect()
    return True


async def connect_discord():
    """Connect to Discord and display connection info."""
    from chatom.discord import DiscordBackend, DiscordConfig

    bot_token = get_env("DISCORD_TOKEN")
    if not bot_token:
        return False

    config = DiscordConfig(
        token=bot_token,
        intents=["guilds", "guild_messages"],
    )
    backend = DiscordBackend(config=config)

    print("Connecting to Discord...")
    await backend.connect()

    print("✅ Connected successfully!")
    print(f"   Backend: {backend.display_name}")
    print(f"   Capabilities: {backend.capabilities}")

    # List available guilds
    guilds = await backend.list_organizations()
    print(f"   Available guilds: {[g.name for g in guilds]}")

    await backend.disconnect()
    return True


async def connect_symphony():
    """Connect to Symphony and display connection info."""
    from chatom.symphony import SymphonyBackend, SymphonyConfig

    host = get_env("SYMPHONY_HOST")
    bot_username = get_env("SYMPHONY_BOT_USERNAME")
    private_key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
    private_key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)

    if not host or not bot_username:
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

    print("Connecting to Symphony...")
    await backend.connect()

    print("✅ Connected successfully!")
    print(f"   Backend: {backend.display_name}")
    print(f"   Pod: {host}")

    await backend.disconnect()
    return True


async def main(backend_name: str) -> bool:
    """Run the connection example for the specified backend."""
    backends = {
        "slack": connect_slack,
        "discord": connect_discord,
        "symphony": connect_symphony,
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        print(f"Available: {list(backends.keys())}")
        return False

    return await backends[backend_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Basic connection example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to connect to",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
