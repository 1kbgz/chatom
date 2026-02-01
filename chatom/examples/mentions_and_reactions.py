#!/usr/bin/env python
"""Mentions and Reactions Example.

This example demonstrates how to mention users/channels and
add/remove reactions to messages.

Environment Variables:
    For Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token
        SLACK_TEST_CHANNEL_NAME: Channel to use
        SLACK_TEST_USER_NAME: User to mention

    For Discord:
        DISCORD_TOKEN: Your Discord bot token
        DISCORD_GUILD_NAME: The Discord server name
        DISCORD_TEST_CHANNEL_NAME: Channel to use
        DISCORD_TEST_USER_NAME: User to mention

    For Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key
        SYMPHONY_TEST_ROOM_NAME: Room to use
        SYMPHONY_TEST_USER_NAME: User to mention

Usage:
    python -m chatom.examples.mentions_and_reactions --backend slack
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

from chatom.format import FormattedMessage


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Missing required environment variable: {name}")
        return None
    return value


async def test_slack_mentions_reactions() -> bool:
    """Test mentions and reactions on Slack."""
    from chatom.slack import SlackBackend, SlackConfig

    bot_token = get_env("SLACK_BOT_TOKEN")
    channel_name = get_env("SLACK_TEST_CHANNEL_NAME")
    user_name = get_env("SLACK_TEST_USER_NAME")
    if not bot_token or not channel_name or not user_name:
        return False

    config = SlackConfig(bot_token=bot_token)
    backend = SlackBackend(config=config)

    await backend.connect()

    # Look up channel and user
    channel = await backend.fetch_channel(name=channel_name)
    if not channel:
        print(f"❌ Channel '{channel_name}' not found")
        await backend.disconnect()
        return False

    user = await backend.fetch_user(name=user_name)
    if not user:
        user = await backend.fetch_user(handle=user_name)
    if not user:
        print(f"❌ User '{user_name}' not found")
        await backend.disconnect()
        return False

    # Create message with mentions
    msg = FormattedMessage()
    msg.add_text("Hello ")
    msg.mention(user)  # User mention
    msg.add_text("! Check out ")
    msg.channel_mention(channel)  # Channel mention

    content = msg.render(backend.get_format())
    sent = await backend.send_message(channel=channel.id, content=content)
    print(f"✅ Sent message with mentions: {sent.id}")

    # Add reactions
    await backend.add_reaction(
        message=sent,
        emoji="thumbsup",
    )
    print("✅ Added 👍 reaction")

    await backend.add_reaction(
        message=sent,
        emoji="rocket",
    )
    print("✅ Added 🚀 reaction")

    # Wait a moment then remove one
    await asyncio.sleep(1)

    await backend.remove_reaction(
        message=sent,
        emoji="thumbsup",
    )
    print("✅ Removed 👍 reaction")

    # Test detecting mentions in a message
    test_content = f"Hey <@{user.id}> check this out!"
    from chatom.base import Channel, Message, User

    test_msg = Message(
        id="test",
        content=test_content,
        channel=Channel(id=channel.id),
        author=User(id=user.id),
    )

    mentioned_ids = test_msg.get_mentioned_user_ids()
    print(f"✅ Detected mentions in test message: {mentioned_ids}")

    if test_msg.mentions_user(user.id):
        print(f"✅ Confirmed user {user.id} is mentioned")

    await backend.disconnect()
    return True


async def test_discord_mentions_reactions() -> bool:
    """Test mentions and reactions on Discord."""
    from chatom.discord import DiscordBackend, DiscordConfig

    bot_token = get_env("DISCORD_TOKEN")
    guild_name = get_env("DISCORD_GUILD_NAME")
    channel_name = get_env("DISCORD_TEST_CHANNEL_NAME")
    user_name = get_env("DISCORD_TEST_USER_NAME")
    if not bot_token or not guild_name or not channel_name or not user_name:
        return False

    config = DiscordConfig(
        token=bot_token,
        intents=["guilds", "guild_messages", "guild_members"],
    )
    backend = DiscordBackend(config=config)

    await backend.connect()

    # Find guild
    guild = await backend.fetch_organization(name=guild_name)
    if not guild:
        print(f"❌ Guild '{guild_name}' not found")
        await backend.disconnect()
        return False

    backend.config.guild_id = guild.id

    # Look up channel and user
    channel = await backend.fetch_channel(name=channel_name)
    if not channel:
        print(f"❌ Channel '{channel_name}' not found")
        await backend.disconnect()
        return False

    user = await backend.fetch_user(name=user_name)
    if not user:
        user = await backend.fetch_user(handle=user_name)
    if not user:
        print(f"⚠️ User '{user_name}' not found - sending without mention")
        # Still continue with the test

    # Create message with mentions
    msg = FormattedMessage()
    msg.add_text("Hello ")
    if user:
        msg.mention(user)
    else:
        msg.add_text(f"@{user_name}")
    msg.add_text("! Testing mentions and reactions.")

    content = msg.render(backend.get_format())
    sent = await backend.send_message(channel=channel.id, content=content)
    print(f"✅ Sent message: {sent.id}")

    # Add reactions
    await backend.add_reaction(
        message=sent,
        emoji="👍",
    )
    print("✅ Added 👍 reaction")

    await backend.add_reaction(
        message=sent,
        emoji="🚀",
    )
    print("✅ Added 🚀 reaction")

    await backend.disconnect()
    return True


async def test_symphony_mentions_reactions() -> bool:
    """Test mentions and reactions on Symphony."""
    from chatom.symphony import SymphonyBackend, SymphonyConfig

    host = get_env("SYMPHONY_HOST")
    bot_username = get_env("SYMPHONY_BOT_USERNAME")
    room_name = get_env("SYMPHONY_TEST_ROOM_NAME")
    user_name = get_env("SYMPHONY_TEST_USER_NAME")
    private_key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
    private_key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)

    if not host or not bot_username or not room_name or not user_name:
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

    # Look up room and user
    room = await backend.fetch_channel(name=room_name)
    if not room:
        print(f"❌ Room '{room_name}' not found")
        await backend.disconnect()
        return False

    user = await backend.fetch_user(name=user_name)
    if not user:
        user = await backend.fetch_user(handle=user_name)
    if not user:
        print(f"❌ User '{user_name}' not found")
        await backend.disconnect()
        return False

    # Create message with mentions
    msg = FormattedMessage()
    msg.add_text("Hello ")
    msg.mention(user)
    msg.add_text("! Testing Symphony mentions.")

    content = msg.render(backend.get_format())
    sent = await backend.send_message(channel=room.id, content=content)
    print(f"✅ Sent message with mention: {sent.id}")

    await backend.disconnect()
    return True


async def main(backend_name: str) -> bool:
    """Run the mentions and reactions example."""
    backends = {
        "slack": test_slack_mentions_reactions,
        "discord": test_discord_mentions_reactions,
        "symphony": test_symphony_mentions_reactions,
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        return False

    return await backends[backend_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mentions and reactions example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
