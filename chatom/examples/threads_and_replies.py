#!/usr/bin/env python
"""Threads and Replies Example.

This example demonstrates how to create threads and reply to messages.

Environment Variables:
    For Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token
        SLACK_TEST_CHANNEL_NAME: Channel to use

    For Discord:
        DISCORD_TOKEN: Your Discord bot token
        DISCORD_GUILD_NAME: The Discord server name
        DISCORD_TEST_CHANNEL_NAME: Channel to use

    For Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key
        SYMPHONY_TEST_ROOM_NAME: Room to use

Usage:
    python -m chatom.examples.threads_and_replies --backend slack
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


async def test_slack_threads() -> bool:
    """Test threads on Slack."""
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

    # Send initial message
    parent = await backend.send_message(
        channel=channel.id,
        content="📋 Thread Demo - Parent Message\n\nThis is the start of a thread.",
    )
    print(f"✅ Sent parent message: {parent.id}")

    # Method 1: Reply in thread using reply_in_thread()
    reply1 = await backend.reply_in_thread(
        message=parent,
        content="Reply #1 using reply_in_thread().",
    )
    print(f"✅ Sent first reply: {reply1.id}")

    await asyncio.sleep(0.5)

    # Method 2: Reply using the as_reply() convenience method
    reply2 = await backend.send_message(**parent.as_reply("Reply #2 using parent.as_reply() convenience method!"))
    print(f"✅ Sent second reply using as_reply(): {reply2.id}")

    await asyncio.sleep(0.5)

    # Method 3: Continue the thread using as_thread_reply()
    reply3 = await backend.send_message(**reply2.as_thread_reply("Reply #3 using as_thread_reply() to continue the thread."))
    print(f"✅ Sent third reply using as_thread_reply(): {reply3.id}")

    await asyncio.sleep(0.5)

    # Method 4: Quote reply using as_quote_reply()
    reply4 = await backend.send_message(**parent.as_quote_reply("✅ Thread complete! This is a quoted reply."))
    print(f"✅ Sent quoted reply using as_quote_reply(): {reply4.id}")

    # Read thread messages
    print("\n📖 Reading thread messages:")
    async for msg in backend.read_thread(
        channel=channel.id,
        thread_id=parent.id,
        limit=10,
    ):
        preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
        print(f"   - {msg.id}: {preview}")

    await backend.disconnect()
    return True


async def test_discord_threads() -> bool:
    """Test threads on Discord."""
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

    # Send initial message
    parent = await backend.send_message(
        channel=channel.id,
        content="📋 Thread Demo - Parent Message",
    )
    print(f"✅ Sent parent message: {parent.id}")

    # Create a thread from the message
    try:
        thread = await backend.create_thread(
            channel=channel.id,
            message_id=parent.id,
            name="Demo Thread",
        )
        print(f"✅ Created thread: {thread.id}")

        # Send messages in the thread
        await backend.send_message(
            channel=thread.id,
            content="First message in the thread!",
        )
        print("✅ Sent first thread message")

        await backend.send_message(
            channel=thread.id,
            content="Second message with more info.",
        )
        print("✅ Sent second thread message")

    except NotImplementedError:
        print("⚠️ Thread creation not fully supported - using replies")

        # Fall back to replies
        await backend.reply_to_message(
            channel=channel.id,
            message_id=parent.id,
            content="This is a reply to the parent message.",
        )
        print("✅ Sent reply")

    await backend.disconnect()
    return True


async def test_symphony_threads() -> bool:
    """Test threads on Symphony."""
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

    # Send initial message
    parent = await backend.send_message(
        channel=room.id,
        content="📋 Thread Demo - Parent Message",
    )
    print(f"✅ Sent parent message: {parent.id}")

    # Reply to the message
    reply1 = await backend.reply_to_message(
        channel=room.id,
        message_id=parent.id,
        content="This is a reply to the parent message.",
    )
    print(f"✅ Sent reply: {reply1.id}")

    reply2 = await backend.reply_to_message(
        channel=room.id,
        message_id=parent.id,
        content="This is another reply in the same thread.",
    )
    print(f"✅ Sent second reply: {reply2.id}")

    await backend.disconnect()
    return True


async def main(backend_name: str) -> bool:
    """Run the threads example."""
    backends = {
        "slack": test_slack_threads,
        "discord": test_discord_threads,
        "symphony": test_symphony_threads,
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        return False

    return await backends[backend_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Threads and replies example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
