#!/usr/bin/env python
"""Mentions and Reactions Example.

This example demonstrates mentioning users and channels, and adding
and removing reactions, using different backends.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.mentions_and_reactions --backend slack
    python -m chatom.examples.mentions_and_reactions --backend zulip

Note:
    Reactions are capability-gated. IRC and LINE have no reaction concept, so
    the reaction steps are skipped there.
"""

import argparse
import asyncio
import sys

from chatom import Capability, FormattedMessage
from chatom.base import Channel, Message, User

from ._backends import BACKENDS, build_backend, resolve_channel, test_channel, test_user


async def main(backend_name: str) -> bool:
    """Exercise mentions and reactions using any configured backend."""
    backend = build_backend(backend_name)
    channel_name = test_channel(backend_name) if backend else None
    user_name = test_user(backend_name) if backend else None
    if not backend or not channel_name or not user_name:
        return False

    await backend.connect()
    try:
        channel = await resolve_channel(backend, channel_name)
        if not channel:
            print(f"❌ Channel '{channel_name}' not found")
            return False

        user = await backend.fetch_user(name=user_name)
        if not user:
            user = await backend.fetch_user(handle=user_name)
        if not user:
            print(f"❌ User '{user_name}' not found")
            return False

        # Build the message from nodes and render it for this backend only at
        # the boundary. No platform markup appears in this code.
        msg = FormattedMessage()
        msg.add_text("Hello ")
        msg.mention(user)
        msg.add_text("! Check out ")
        msg.channel_mention(channel)

        content = msg.render(backend.get_format())
        sent = await backend.send_message(channel=channel.id, content=content)
        print(f"✅ Sent message with mentions: {sent.id}")

        if backend.capabilities.supports(Capability.EMOJI_REACTIONS):
            await backend.add_reaction(message=sent, emoji="thumbsup")
            print("✅ Added 👍 reaction")

            await backend.add_reaction(message=sent, emoji="rocket")
            print("✅ Added 🚀 reaction")

            await asyncio.sleep(1)

            await backend.remove_reaction(message=sent, emoji="thumbsup")
            print("✅ Removed 👍 reaction")
        else:
            print(f"⏭️  {backend.display_name} does not support reactions")

        # Mention detection works on the common Message model.
        test_msg = Message(
            id="test",
            content=f"Hey {msg.render(backend.get_format())} check this out!",
            channel=Channel(id=channel.id),
            author=User(id=user.id),
        )

        mentioned_ids = test_msg.get_mentioned_user_ids()
        print(f"✅ Detected mentions in test message: {mentioned_ids}")

        if test_msg.mentions_user(user):
            print(f"✅ Confirmed user {user.id} is mentioned")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mentions and reactions example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        default="slack",
        help="Backend to use",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
