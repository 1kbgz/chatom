#!/usr/bin/env python
"""Send Message Example.

This example demonstrates how to send messages to channels
using different backends.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.send_message --backend slack --message "Hello World!"
    python -m chatom.examples.send_message --backend zulip --message "Hello World!"
"""

import argparse
import asyncio
import sys

from ._backends import BACKENDS, build_backend, resolve_channel, test_channel


async def main(backend_name: str, message: str) -> bool:
    """Send one message using any configured backend."""
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

        sent_message = await backend.send_message(
            channel=channel.id,
            content=message,
        )

        print(f"✅ Message sent to {channel_name}")
        print(f"   Message ID: {sent_message.id}")
        print(f"   Timestamp: {sent_message.created_at}")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send message example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
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
