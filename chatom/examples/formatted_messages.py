#!/usr/bin/env python
"""Formatted Messages Example.

This example demonstrates how to send rich formatted messages
using the chatom format system.

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
    python -m chatom.examples.formatted_messages --backend slack
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

from chatom.format import Format, FormattedMessage, MessageBuilder


def get_env(name: str, required: bool = True) -> Optional[str]:
    """Get environment variable."""
    value = os.environ.get(name)
    if required and not value:
        print(f"Missing required environment variable: {name}")
        return None
    return value


def create_demo_message() -> FormattedMessage:
    """Create a demo formatted message."""
    msg = MessageBuilder()

    # Add various formatting
    msg.heading("Chatom Format Demo", level=2)
    msg.paragraph("This message demonstrates rich text formatting.")
    msg.line_break()

    # Text styling
    msg.bold("Bold text")
    msg.text(", ")
    msg.italic("italic text")
    msg.text(", ")
    msg.code("inline code")
    msg.line_break()

    # Code block
    msg.code_block('def hello():\n    print("Hello, World!")', language="python")

    # Quote
    msg.quote("This is a blockquote - great for callouts!")

    # Lists
    msg.paragraph("Features:")
    msg.bullet_list(
        [
            "Cross-platform messaging",
            "Rich formatting support",
            "Type-safe models",
        ]
    )

    msg.paragraph("Steps:")
    msg.numbered_list(
        [
            "Connect to backend",
            "Send formatted message",
            "Receive responses",
        ]
    )

    return msg.build()


def create_table_message() -> FormattedMessage:
    """Create a message with a table."""
    msg = MessageBuilder()
    msg.heading("Status Report", level=3)

    # Create a table
    msg.table(
        headers=["Backend", "Status", "Messages"],
        data=[
            ["Slack", "✅ Online", "1,234"],
            ["Discord", "✅ Online", "5,678"],
            ["Symphony", "⚠️ Degraded", "901"],
        ],
        caption="Backend Status Overview",
    )

    msg.line_break()
    msg.paragraph("Last updated: just now")

    return msg.build()


async def send_formatted_slack() -> bool:
    """Send formatted messages to Slack."""
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

    # Send formatted demo message
    demo_msg = create_demo_message()
    content = demo_msg.render(Format.SLACK_MARKDOWN)

    await backend.send_message(channel=channel.id, content=content)
    print("✅ Sent formatted demo message")

    # Send table message
    table_msg = create_table_message()
    content = table_msg.render(Format.SLACK_MARKDOWN)

    await backend.send_message(channel=channel.id, content=content)
    print("✅ Sent table message")

    await backend.disconnect()
    return True


async def send_formatted_discord() -> bool:
    """Send formatted messages to Discord."""
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

    # Send formatted demo message
    demo_msg = create_demo_message()
    content = demo_msg.render(Format.DISCORD_MARKDOWN)

    await backend.send_message(channel=channel.id, content=content)
    print("✅ Sent formatted demo message")

    # Send table message
    table_msg = create_table_message()
    content = table_msg.render(Format.DISCORD_MARKDOWN)

    await backend.send_message(channel=channel.id, content=content)
    print("✅ Sent table message")

    await backend.disconnect()
    return True


async def send_formatted_symphony() -> bool:
    """Send formatted messages to Symphony."""
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

    # Send formatted demo message
    demo_msg = create_demo_message()
    content = demo_msg.render(Format.SYMPHONY_MESSAGEML)

    await backend.send_message(channel=room.id, content=content)
    print("✅ Sent formatted demo message")

    # Send table message
    table_msg = create_table_message()
    content = table_msg.render(Format.SYMPHONY_MESSAGEML)

    await backend.send_message(channel=room.id, content=content)
    print("✅ Sent table message")

    await backend.disconnect()
    return True


async def main(backend_name: str) -> bool:
    """Run the formatted messages example."""
    backends = {
        "slack": send_formatted_slack,
        "discord": send_formatted_discord,
        "symphony": send_formatted_symphony,
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        return False

    return await backends[backend_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Formatted messages example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
