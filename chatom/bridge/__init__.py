"""Cross-backend bridging utilities for chatom.

This module provides tools for linking user identities across
chat platforms and forwarding messages between backends with
automatic format conversion and mention translation.
"""

from .identity import IdentityMapper
from .relay import MessageBridge

__all__ = ("IdentityMapper", "MessageBridge")
