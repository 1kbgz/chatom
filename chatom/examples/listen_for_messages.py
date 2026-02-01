#!/usr/bin/env python
"""Listen for Messages Example.

This example demonstrates how to listen for incoming messages
using real-time event streams.

Environment Variables:
    For Slack:
        SLACK_BOT_TOKEN: Your Slack bot OAuth token
        SLACK_APP_TOKEN: Your Slack app token (xapp-...) for Socket Mode
        SLACK_TEST_CHANNEL_NAME: Channel to listen in

    For Symphony:
        SYMPHONY_HOST: Your Symphony pod hostname
        SYMPHONY_BOT_USERNAME: Bot's service account username
        SYMPHONY_BOT_PRIVATE_KEY_PATH: Path to RSA private key
        SYMPHONY_TEST_ROOM_NAME: Room to listen in

Usage:
    python -m chatom.examples.listen_for_messages --backend slack --timeout 60
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


async def listen_slack(timeout: int) -> bool:
    """Listen for messages on Slack using Socket Mode."""
    from chatom.slack import SlackBackend, SlackConfig

    bot_token = get_env("SLACK_BOT_TOKEN")
    app_token = get_env("SLACK_APP_TOKEN")
    channel_name = get_env("SLACK_TEST_CHANNEL_NAME")

    if not bot_token or not app_token or not channel_name:
        return False

    config = SlackConfig(
        bot_token=bot_token,
        app_token=app_token,
        socket_mode=True,
    )
    backend = SlackBackend(config=config)

    await backend.connect()

    channel = await backend.fetch_channel(name=channel_name)
    if not channel:
        print(f"❌ Channel '{channel_name}' not found")
        await backend.disconnect()
        return False

    print(f"👂 Listening for messages in #{channel_name}...")
    print(f"   (Will stop after {timeout} seconds or Ctrl+C)")
    print("   Try sending '!help', '!ping', or '!dm' to test responses")
    print()

    # Create a task that will cancel after timeout
    async def listen_with_timeout():
        try:
            async for message in backend.listen():
                # Filter to our test channel
                if message.channel_id != channel.id:
                    continue

                author = "Unknown"
                if message.author:
                    author = message.author.name or message.author_id

                content = message.content or ""
                print(f"📨 [{author}]: {content}")

                # Check if we're mentioned
                mentioned_ids = message.get_mentioned_user_ids()
                if mentioned_ids:
                    print(f"   (Mentioned: {mentioned_ids})")

                # Demo: Use convenience methods to respond to commands
                if content.startswith("!help"):
                    # Reply in thread using as_reply()
                    await backend.send_message(**message.as_reply("Available commands: !help, !ping, !dm, !quote"))
                    print("   → Sent help reply in thread")

                elif content.startswith("!ping"):
                    # Reply with quote using as_quote_reply()
                    await backend.send_message(**message.as_quote_reply("🏓 Pong!"))
                    print("   → Sent quoted pong reply")

                elif content.startswith("!dm") and message.author:
                    # DM the author using as_dm_to_author()
                    await backend.send_dm(**message.as_dm_to_author("👋 You asked me to DM you!"))
                    print(f"   → Sent DM to {author}")

        except asyncio.CancelledError:
            print("\n⏱️ Timeout reached")

    try:
        await asyncio.wait_for(listen_with_timeout(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    except KeyboardInterrupt:
        print("\n⛔ Interrupted by user")

    await backend.disconnect()
    return True


async def listen_symphony(timeout: int) -> bool:
    """Listen for messages on Symphony using datafeed."""
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

    print(f"👂 Listening for messages in {room_name}...")
    print(f"   (Will stop after {timeout} seconds or Ctrl+C)")
    print()

    async def listen_with_timeout():
        try:
            async for message in backend.listen():
                if message.channel_id != room.id:
                    continue

                author = "Unknown"
                if message.author:
                    author = message.author.name or message.author_id

                content = message.content or ""
                print(f"📨 [{author}]: {content}")
        except asyncio.CancelledError:
            print("\n⏱️ Timeout reached")

    try:
        await asyncio.wait_for(listen_with_timeout(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    except KeyboardInterrupt:
        print("\n⛔ Interrupted by user")

    await backend.disconnect()
    return True


async def main(backend_name: str, timeout: int) -> bool:
    """Run the listen example."""
    if backend_name == "discord":
        print("⚠️ Discord listen example requires additional setup - see discord_e2e.py")
        return False

    backends = {
        "slack": lambda: listen_slack(timeout),
        "symphony": lambda: listen_symphony(timeout),
    }

    if backend_name not in backends:
        print(f"Unknown backend: {backend_name}")
        return False

    return await backends[backend_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen for messages example")
    parser.add_argument(
        "--backend",
        choices=["slack", "discord", "symphony"],
        default="slack",
        help="Backend to use",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend, args.timeout))
    sys.exit(0 if success else 1)
