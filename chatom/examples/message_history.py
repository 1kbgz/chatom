#!/usr/bin/env python
"""Message History Example.

This example demonstrates how to read message history from a channel
using different backends.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.message_history --backend slack --limit 20
    python -m chatom.examples.message_history --backend zulip --limit 20

Note:
    History availability varies by platform. Telegram bots cannot fetch
    history at all, and IRC only replays history when the server offers the
    IRCv3 `chathistory` capability.
"""

import argparse
import asyncio
import sys

from ._backends import BACKENDS, build_backend, resolve_channel, test_channel


async def main(backend_name: str, limit: int) -> bool:
    """Read message history using any configured backend."""
    backend = build_backend(backend_name)
    channel_name = test_channel(backend_name) if backend else None
    if not backend or not channel_name:
        return False

    await backend.connect()
    try:
        channel = await resolve_channel(backend, channel_name)
        if not channel:
            print(f"❌ Channel '{channel_name}' not found")
            return False

        print(f"📖 Reading last {limit} messages from {channel_name}:\n")

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
        if count == 0:
            print("   (this platform may not expose history to bots)")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Message history example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
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
