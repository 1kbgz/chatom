#!/usr/bin/env python
"""Listen For Messages Example.

This example demonstrates how to consume inbound messages and respond
with the reply, quote, and DM convenience methods.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.listen_for_messages --backend slack --timeout 60
    python -m chatom.examples.listen_for_messages --backend matrix --timeout 60

Note:
    Slack needs Socket Mode, so SLACK_APP_TOKEN is required here in addition
    to SLACK_BOT_TOKEN.
"""

import argparse
import asyncio
import sys

from ._backends import BACKENDS, build_backend, resolve_channel, test_channel


async def _handle(backend, message, channel_id: str) -> None:
    """Print one inbound message and respond to its command, if any."""
    if message.channel_id != channel_id:
        return

    author = "Unknown"
    if message.author:
        author = message.author.name or message.author_id

    content = message.content or ""
    print(f"📨 [{author}]: {content}")

    mentioned_ids = message.get_mentioned_user_ids()
    if mentioned_ids:
        print(f"   (Mentioned: {mentioned_ids})")

    if content.startswith("!help"):
        await backend.send_message(**message.as_reply("Available commands: !help, !ping, !dm, !quote"))
        print("   → Sent help reply in thread")

    elif content.startswith("!ping"):
        await backend.send_message(**message.as_quote_reply("🏓 Pong!"))
        print("   → Sent quoted pong reply")

    elif content.startswith("!dm") and message.author:
        await backend.send_dm(**message.as_dm_to_author("👋 You asked me to DM you!"))
        print(f"   → Sent DM to {author}")


async def main(backend_name: str, timeout: int) -> bool:
    """Listen for inbound messages using any configured backend."""
    backend = build_backend(backend_name, streaming=True)
    channel_name = test_channel(backend_name) if backend else None
    if not backend or not channel_name:
        return False

    await backend.connect()
    try:
        channel = await resolve_channel(backend, channel_name)
        if not channel:
            print(f"❌ Channel '{channel_name}' not found")
            return False

        print(f"👂 Listening for messages in {channel_name}...")
        print(f"   (Will stop after {timeout} seconds or Ctrl+C)")
        print("   Try sending '!help', '!ping', or '!dm' to test responses")
        print()

        async def listen_with_timeout():
            try:
                async for message in backend.listen():
                    await _handle(backend, message, channel.id)
            except asyncio.CancelledError:
                print("\n⏱️ Timeout reached")

        try:
            await asyncio.wait_for(listen_with_timeout(), timeout=timeout)
        except TimeoutError:
            pass
        except KeyboardInterrupt:
            print("\n⛔ Interrupted by user")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Listen for messages example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        default="slack",
        help="Backend to use",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Seconds to listen before stopping",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend, args.timeout))
    sys.exit(0 if success else 1)
