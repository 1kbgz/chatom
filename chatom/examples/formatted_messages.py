#!/usr/bin/env python
"""Formatted Messages Example.

This example demonstrates how to send rich formatted messages
using the chatom format system.

The message is built once from formatting nodes and rendered with the
backend's own format at send time, so no platform markup appears here.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.formatted_messages --backend slack
    python -m chatom.examples.formatted_messages --backend matrix
"""

import argparse
import asyncio
import sys

from chatom.format import FormattedMessage, MessageBuilder

from ._backends import BACKENDS, build_backend, resolve_channel, test_channel


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
            ["Matrix", "✅ Online", "2,345"],
            ["Zulip", "✅ Online", "3,456"],
            ["Symphony", "⚠️ Degraded", "901"],
        ],
        caption="Backend Status Overview",
    )

    msg.line_break()
    msg.paragraph("Last updated: just now")

    return msg.build()


async def main(backend_name: str) -> bool:
    """Send formatted messages using any configured backend."""
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

        # One render call per message, using whatever format this backend wants.
        target_format = backend.get_format()
        print(f"Rendering for {backend.display_name} as {target_format}")

        demo_msg = create_demo_message()
        await backend.send_message(channel=channel.id, content=demo_msg.render(target_format))
        print("✅ Sent formatted demo message")

        table_msg = create_table_message()
        await backend.send_message(channel=channel.id, content=table_msg.render(target_format))
        print("✅ Sent table message")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Formatted messages example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
