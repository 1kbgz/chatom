#!/usr/bin/env python
"""Direct Messages Example.

This example demonstrates how to send direct messages to users
using different backends.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.direct_messages --backend slack
    python -m chatom.examples.direct_messages --backend matrix

Note:
    Discord only allows DMs to users who share a guild with the bot, and IRC
    private messages require the target nick to be online.
"""

import argparse
import asyncio
import sys

from ._backends import BACKENDS, build_backend, test_user


async def main(backend_name: str) -> bool:
    """Send direct messages using any configured backend."""
    backend = build_backend(backend_name)
    user_name = test_user(backend_name) if backend else None
    if not backend or not user_name:
        return False

    await backend.connect()
    try:
        user = await backend.fetch_user(name=user_name)
        if not user:
            user = await backend.fetch_user(handle=user_name)
        if not user:
            print(f"❌ User '{user_name}' not found")
            return False

        print(f"Found user: {user.name} ({user.id})")

        # Method 1: open a DM channel and send to it directly
        dm_channel_id = await backend.create_dm([user.id])
        print(f"✅ Created/opened DM channel: {dm_channel_id}")

        sent = await backend.send_message(
            channel=dm_channel_id,
            content="Hello! This is a direct message sent via chatom. 👋",
        )
        print(f"✅ Sent DM: {sent.id}")

        # Method 2: the send_dm() convenience method
        sent2 = await backend.send_dm(
            user=user,
            content="This is another DM using the send_dm() convenience method!",
        )
        print(f"✅ Sent DM via send_dm(): {sent2.id}")

        # Method 3: as_dm_to_author() for replying privately to a message
        print("\n📝 Demonstrating as_dm_to_author() pattern:")
        print("   In a real bot, you would use this to respond privately:")
        print("   await backend.send_dm(**message.as_dm_to_author('Private response'))")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct messages example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
