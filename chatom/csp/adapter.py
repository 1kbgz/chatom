"""High-level CSP adapter for chatom backends.

This module provides the BackendAdapter class which wraps a chatom
backend and provides convenient CSP graph/node methods for reading
and writing messages.
"""

import asyncio
import logging
import threading
from queue import Queue
from typing import Optional, Set

import csp
from csp import ts

from ..backend_registry import BackendBase
from ..base import Message
from .nodes import MessageReaderPushAdapter, _send_messages_thread

__all__ = ("BackendAdapter",)

log = logging.getLogger(__name__)


class BackendAdapter:
    """High-level CSP adapter that wraps a chatom backend.

    This provides a convenient interface for using a chatom backend
    with CSP, including message subscription, publishing, and presence.

    Attributes:
        backend: The underlying chatom backend.

    Example:
        >>> from chatom.symphony import SymphonyBackend, SymphonyConfig
        >>> from chatom.csp import BackendAdapter
        >>>
        >>> config = SymphonyConfig(host="company.symphony.com", ...)
        >>> backend = SymphonyBackend(config=config)
        >>> adapter = BackendAdapter(backend)
        >>>
        >>> @csp.graph
        ... def my_graph():
        ...     messages = adapter.subscribe()
        ...     # Process messages
        ...     responses = process(messages)
        ...     adapter.publish(responses)
        >>>
        >>> csp.run(my_graph, starttime=datetime.now(), endtime=timedelta(hours=1))
    """

    def __init__(self, backend: BackendBase):
        """Initialize the adapter.

        Args:
            backend: The chatom backend to wrap.
        """
        self._backend = backend

    @property
    def backend(self) -> BackendBase:
        """Get the underlying backend."""
        return self._backend

    @csp.graph
    def subscribe(
        self,
        channels: Optional[Set[str]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> ts[[Message]]:
        """Subscribe to messages from the backend.

        Args:
            channels: Optional set of channels to filter. Can be IDs or names;
                names will be resolved to IDs at connection time.
            skip_own: If True, skip messages from the bot itself.
            skip_history: If True, skip messages before stream started.

        Returns:
            Time series of Message lists.

        Example:
            >>> @csp.graph
            ... def my_graph():
            ...     # Subscribe to specific channels by ID or name
            ...     messages = adapter.subscribe(channels={"general", "C12345"})
            ...     csp.print("Received", messages)
        """
        return MessageReaderPushAdapter(
            backend=self._backend,
            channels=channels or set(),
            skip_own=skip_own,
            skip_history=skip_history,
        )

    @csp.node
    def _write_message(self, msg: ts[Message]):
        """Internal node for writing messages."""
        with csp.state():
            s_queue: Queue = None
            s_thread: threading.Thread = None

        with csp.start():
            s_queue = Queue(maxsize=0)
            s_thread = threading.Thread(
                target=_send_messages_thread,
                args=(s_queue, self._backend),
                daemon=True,
            )
            s_thread.start()

        with csp.stop():
            if s_thread:
                s_queue.put(None)
                s_queue.join()
                s_thread.join(timeout=5.0)

        if csp.ticked(msg):
            s_queue.put(msg)

    @csp.graph
    def publish(self, msg: ts[Message]):
        """Publish messages to the backend.

        Args:
            msg: Time series of messages to send.

        Example:
            >>> @csp.graph
            ... def my_graph():
            ...     response = csp.const(Message(
            ...         channel_id="stream123",
            ...         content="Hello, World!",
            ...     ))
            ...     adapter.publish(response)
        """
        self._write_message(msg=msg)

    @csp.node
    def _set_presence(self, presence: ts[str], timeout: float = 5.0):
        """Internal node for setting presence."""
        if csp.ticked(presence):
            try:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            self._backend.set_presence(presence),
                            timeout=timeout,
                        )
                    )
                except asyncio.TimeoutError:
                    log.error("Timeout setting presence")
                except Exception:
                    log.exception("Failed setting presence")
                finally:
                    loop.close()
            except Exception:
                log.exception("Error in presence update")

    @csp.graph
    def publish_presence(self, presence: ts[str], timeout: float = 5.0):
        """Publish presence status updates.

        Args:
            presence: Time series of presence status strings
                     (e.g., "available", "busy", "away").
            timeout: Timeout for presence API calls.

        Example:
            >>> @csp.graph
            ... def my_graph():
            ...     presence = csp.const("available")
            ...     adapter.publish_presence(presence)
        """
        self._set_presence(presence=presence, timeout=timeout)
