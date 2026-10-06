#!/usr/bin/env python
"""Cross-Platform Bot Example.

This example demonstrates how to build a bot that works across
multiple platforms simultaneously.

Every backend that has credentials in the environment joins the bot. The
message is built once and rendered per backend at send time.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.cross_platform_bot
"""

import asyncio
import os
import sys

from chatom.backend import BackendBase
from chatom.base import Message
from chatom.format import FormattedMessage

from ._backends import BACKENDS, build_backend, channel_env, resolve_channel


class CrossPlatformBot:
    """A bot that can run on multiple platforms simultaneously."""

    def __init__(self):
        self.backends: dict[str, BackendBase] = {}
        self.channels: dict[str, str] = {}  # backend_name -> channel_id

    async def add(self, name: str) -> bool:
        """Connect one backend, skipping it when it is not configured."""
        # An unconfigured backend is skipped here rather than treated as an error.
        backend = build_backend(name, quiet=True)
        if not backend:
            print(f"⏭️ Skipping {name} (missing credentials)")
            return False

        channel_name = os.environ.get(channel_env(name))
        if not channel_name:
            print(f"⏭️ Skipping {name} (no test channel configured)")
            return False

        await backend.connect()
        channel = await resolve_channel(backend, channel_name)
        if not channel:
            print(f"❌ {name} channel '{channel_name}' not found")
            await backend.disconnect()
            return False

        self.backends[name] = backend
        self.channels[name] = channel.id
        print(f"✅ Connected to {name} ({channel_name})")
        return True

    async def broadcast(self, content: str) -> list[Message]:
        """Send a message to all connected platforms.

        Uses FormattedMessage to render appropriately for each backend.
        """
        results = []

        msg = FormattedMessage()
        msg.add_bold("📢 Cross-Platform Broadcast")
        msg.add_line_break()
        msg.add_text(content)

        for name, backend in self.backends.items():
            channel_id = self.channels[name]
            rendered = msg.render(backend.get_format())

            sent = await backend.send_message(
                channel=channel_id,
                content=rendered,
            )
            results.append(sent)
            print(f"   → Sent to {name}: {sent.id}")

        return results

    async def disconnect_all(self):
        """Disconnect from all backends."""
        for name, backend in self.backends.items():
            await backend.disconnect()
            print(f"🔌 Disconnected from {name}")


async def main() -> bool:
    """Run the cross-platform bot example."""
    bot = CrossPlatformBot()

    print("🤖 Cross-Platform Bot Starting...\n")

    for name in BACKENDS:
        await bot.add(name)

    if not bot.backends:
        print("\n❌ No backends configured. Set environment variables for at least one platform.")
        return False

    print(f"\n📡 Connected to {len(bot.backends)} platform(s): {list(bot.backends.keys())}")

    # Send a broadcast message
    print("\n📤 Broadcasting message to all platforms...")
    await bot.broadcast("Hello from the cross-platform chatom bot! 🌐")

    # Send platform-specific information
    print("\n📊 Sending status to each platform...")
    for name, backend in bot.backends.items():
        channel_id = bot.channels[name]

        msg = FormattedMessage()
        msg.add_bold("Platform Status")
        msg.add_line_break()
        msg.add_text(f"Backend: {backend.display_name}")
        msg.add_line_break()
        msg.add_text(f"Format: {backend.get_format().name}")
        msg.add_line_break()
        msg.add_text(f"Capabilities: {backend.capabilities}")

        await backend.send_message(
            channel=channel_id,
            content=msg.render(backend.get_format()),
        )
        print(f"   → Sent status to {name}")

    # Cleanup
    print()
    await bot.disconnect_all()

    print("\n✅ Cross-platform bot example complete!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
