#!/usr/bin/env python
"""Threads and Replies Example.

This example demonstrates threading and reply patterns
using different backends.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.threads_and_replies --backend slack
    python -m chatom.examples.threads_and_replies --backend zulip

Note:
    Threading models differ. Slack and Matrix have native threads, Zulip uses
    topics, and IRC and LINE have neither, so they fall back to plain replies.
"""

import argparse
import asyncio
import sys

from chatom import Capability

from ._backends import BACKENDS, build_backend, resolve_channel, test_channel


async def main(backend_name: str) -> bool:
    """Exercise threads and replies using any configured backend."""
    backend = build_backend(backend_name)
    channel_name = test_channel(backend_name) if backend else None
    if not backend or not channel_name:
        return False

    supports_threads = backend.capabilities.supports(Capability.THREADS)

    await backend.connect()
    try:
        channel = await resolve_channel(backend, channel_name)
        if not channel:
            print(f"❌ Channel '{channel_name}' not found")
            return False

        parent = await backend.send_message(
            channel=channel.id,
            content="📋 Thread Demo - Parent Message\n\nThis is the start of a thread.",
        )
        print(f"✅ Sent parent message: {parent.id}")

        # Method 1: reply_in_thread() on backends with native threads
        if supports_threads:
            reply1 = await backend.reply_in_thread(
                message=parent,
                content="Reply #1 using reply_in_thread().",
            )
            print(f"✅ Sent first reply: {reply1.id}")
            await asyncio.sleep(0.5)

        # Method 2: the as_reply() convenience method
        reply2 = await backend.send_message(**parent.as_reply("Reply #2 using parent.as_reply() convenience method!"))
        print(f"✅ Sent second reply using as_reply(): {reply2.id}")

        await asyncio.sleep(0.5)

        # Method 3: continue the thread using as_thread_reply()
        reply3 = await backend.send_message(**reply2.as_thread_reply("Reply #3 using as_thread_reply() to continue the thread."))
        print(f"✅ Sent third reply using as_thread_reply(): {reply3.id}")

        await asyncio.sleep(0.5)

        # Method 4: quote reply using as_quote_reply()
        reply4 = await backend.send_message(**parent.as_quote_reply("✅ Thread complete! This is a quoted reply."))
        print(f"✅ Sent quoted reply using as_quote_reply(): {reply4.id}")

        if not supports_threads:
            print(f"\n⏭️  {backend.display_name} has no native threads; replies were sent inline")
            return True

        print("\n📖 Reading thread messages:")
        async for msg in backend.read_thread(
            channel=channel.id,
            thread_id=parent.id,
            limit=10,
        ):
            preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            print(f"   - {msg.id}: {preview}")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Threads and replies example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
