#!/usr/bin/env python
"""Direct Messages Example.

This example demonstrates how to send direct messages to users.

Environment Variables:
    For Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token
        SLACK_TEST_USER_NAME: User to send DM to

    For Discord:
        DISCORD_TOKEN: Your Discord bot token
        DISCORD_GUILD_NAME: The Discord server name
        DISCORD_TEST_USER_NAME: User to send DM to

    For Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key
        SYMPHONY_TEST_USER_NAME: User to send DM to

Usage:
    python -m chatom.examples.direct_messages --backend slack
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


async def send_slack_dm() -> bool:
    """Send a direct message on Slack."""
    from chatom.slack import SlackBackend, SlackConfig

    bot_token = get_env("SLACK_BOT_TOKEN")
    user_name = get_env("SLACK_TEST_USER_NAME")
    if not bot_token or not user_name:
        return False

    config = SlackConfig(bot_token=bot_token)
    backend = SlackBackend(config=config)

    await backend.connect()

    # Look up user
    user = await backend.fetch_user(name=user_name)
    if not user:
        user = await backend.fetch_user(handle=user_name)
    if not user:
        print(f"❌ User '{user_name}' not found")
        await backend.disconnect()
        return False

    print(f"Found user: {user.name} ({user.id})")

    # Method 1: Create DM channel and send message manually
    dm_channel_id = await backend.create_dm([user.id])
    print(f"✅ Created/opened DM channel: {dm_channel_id}")

    sent = await backend.send_message(
        channel=dm_channel_id,
        content="Hello! This is a direct message sent via chatom. 👋",
    )
    print(f"✅ Sent DM: {sent.id}")

    # Method 2: Use the convenience send_dm method
    sent2 = await backend.send_dm(
        user=user,
        content="This is another DM using the send_dm() convenience method!",
    )
    print(f"✅ Sent DM via send_dm(): {sent2.id}")

    # Method 3: Demonstrate as_dm_to_author() for replying to messages
    # In a real scenario, you'd get a message from listening or reading history
    # Here we simulate by creating a mock scenario
    print("\n📝 Demonstrating as_dm_to_author() pattern:")
    print("   In a real bot, you would use this to respond privately:")
    print("   await backend.send_dm(**message.as_dm_to_author('Private response'))")

    await backend.disconnect()
    return True


async def send_discord_dm() -> bool:
    """Send a direct message on Discord."""
    from chatom.discord import DiscordBackend, DiscordConfig

    bot_token = get_env("DISCORD_TOKEN")
    guild_name = get_env("DISCORD_GUILD_NAME")
    user_name = get_env("DISCORD_TEST_USER_NAME")
    if not bot_token or not guild_name or not user_name:
        return False

    config = DiscordConfig(
        token=bot_token,
        intents=["guilds", "guild_messages", "guild_members", "dm_messages"],
    )
    backend = DiscordBackend(config=config)

    await backend.connect()

    guild = await backend.fetch_organization(name=guild_name)
    if not guild:
        print(f"❌ Guild '{guild_name}' not found")
        await backend.disconnect()
        return False

    backend.config.guild_id = guild.id

    # Look up user
    user = await backend.fetch_user(name=user_name)
    if not user:
        user = await backend.fetch_user(handle=user_name)
    if not user:
        print(f"❌ User '{user_name}' not found")
        await backend.disconnect()
        return False

    print(f"Found user: {user.name} ({user.id})")

    # Create DM channel and send
    dm_channel_id = await backend.create_dm([user.id])
    print(f"✅ Created/opened DM channel: {dm_channel_id}")

    sent = await backend.send_message(
        channel=dm_channel_id,
        content="Hello! This is a direct message from chatom. 👋",
    )
    print(f"✅ Sent DM: {sent.id}")

    await backend.disconnect()
    return True


async def send_symphony_dm() -> bool:
    """Send a direct message on Symphony."""
    from chatom.symphony import SymphonyBackend, SymphonyConfig

    host = get_env("SYMPHONY_HOST")
    bot_username = get_env("SYMPHONY_BOT_USERNAME")
    user_name = get_env("SYMPHONY_TEST_USER_NAME")
    private_key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
    private_key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)

    if not host or not bot_username or not user_name:
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

    # Look up user
    user = await backend.fetch_user(name=user_name)
    if not user:
        user = await backend.fetch_user(handle=user_name)
    if not user:
        print(f"❌ User '{user_name}' not found")
        await backend.disconnect()
        return False

    print(f"Found user: {user.name} ({user.id})")

    # Create IM and send
    im_channel_id = await backend.create_im([user.id])
    print(f"✅ Created/opened IM: {im_channel_id}")

    sent = await backend.send_message(
        channel=im_channel_id,
        content="Hello! This is a direct message from chatom.",
    )
    print(f"✅ Sent IM: {sent.id}")

    await backend.disconnect()
    return True


async def main(backend_name: str) -> bool:
    """Run the direct messages example."""
    backends = {
        "slack": send_slack_dm,
        "discord": send_discord_dm,
        "symphony": send_symphony_dm,
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        return False

    return await backends[backend_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct messages example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
