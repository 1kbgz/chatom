#!/usr/bin/env python
"""Basic Connection Example.

This example demonstrates how to connect to different chat backends
and perform basic operations.

Backend construction and credentials live in `chatom.examples._backends`.
See that module for the environment variables each backend reads.

Usage:
    python -m chatom.examples.basic_connection --backend slack
    python -m chatom.examples.basic_connection --backend matrix
    python -m chatom.examples.basic_connection --backend irc
"""

import argparse
import asyncio
import sys

from chatom import Capability

from ._backends import BACKENDS, build_backend


async def main(backend_name: str) -> bool:
    """Connect to any configured backend and display connection info."""
    backend = build_backend(backend_name)
    if not backend:
        return False

    print(f"Connecting to {backend.display_name}...")
    await backend.connect()
    try:
        print("✅ Connected successfully!")
        print(f"   Backend: {backend.display_name}")
        print(f"   Format: {backend.format}")
        print(f"   Capabilities: {backend.capabilities}")

        # Not every platform has a workspace concept.
        if backend.capabilities.supports(Capability.ORGANIZATIONS):
            organizations = await backend.list_organizations()
            print(f"   Organizations: {[o.name for o in organizations]}")
        return True
    finally:
        await backend.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Basic connection example")
    parser.add_argument(
        "--backend",
        choices=BACKENDS,
        default="slack",
        help="Backend to connect to",
    )
    args = parser.parse_args()

    success = asyncio.run(main(args.backend))
    sys.exit(0 if success else 1)
