"""CSP nodes and push adapters for chatom backends.

This module provides the low-level CSP nodes for reading and writing
messages using chatom backends.
"""

import asyncio
import logging
import threading
from queue import Queue
from typing import List, Optional, Set

import csp
from csp import ts
from csp.impl.pushadapter import PushInputAdapter
from csp.impl.wiring import py_push_adapter_def

from ..backend_registry import BackendBase
from ..base import Message

__all__ = (
    "MessageReaderPushAdapter",
    "message_reader",
    "message_writer",
    "_send_messages_thread",
)

log = logging.getLogger(__name__)


class MessageReaderPushAdapterImpl(PushInputAdapter):
    """Push adapter implementation for reading messages from a chatom backend.

    This adapter runs the backend's message stream in a background thread
    and pushes messages to CSP as they arrive.
    """

    def __init__(
        self,
        backend: BackendBase,
        channels: Optional[Set[str]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ):
        """Initialize the message reader.

        Args:
            backend: The chatom backend to read from.
            channels: Optional set of channels to filter. Can be IDs or names;
                names will be resolved to IDs at connection time.
            skip_own: If True, skip messages from the bot itself.
            skip_history: If True, skip messages before the stream started.
        """
        self._backend = backend
        self._channels = channels or set()
        self._resolved_channel_ids: Set[str] = set()
        self._skip_own = skip_own
        self._skip_history = skip_history
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._message_queue: Queue = Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._error: Optional[Exception] = None

    def start(self, starttime, endtime):
        """Start the adapter."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running = True
        self._thread.start()

    def stop(self):
        """Stop the adapter."""
        if self._running:
            self._running = False
            self._message_queue.put(None)
            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread:
                self._thread.join(timeout=5.0)

        if self._error:
            raise self._error

    def _run(self):
        """Run the message stream in a background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_run())
        except Exception as e:
            log.exception(f"Error in message reader: {e}")
            self._error = e
            self._running = False
        finally:
            if self._loop and not self._loop.is_closed():
                self._loop.close()
            self._message_queue.put(None)

    async def _async_run(self):
        """Async main loop for reading messages."""
        # Connect if not already connected
        if not self._backend.connected:
            await self._backend.connect()

        # Resolve channel names to IDs
        await self._resolve_channels()

        # Start processing queue in parallel with reading
        queue_task = asyncio.create_task(self._process_queue())

        try:
            # If we have specific channels, stream each one
            if self._resolved_channel_ids:
                # For now, stream from first channel
                # TODO: Support multiple channels with asyncio.gather
                for channel_id in self._resolved_channel_ids:
                    async for message in self._backend.stream_messages(
                        channel_id=channel_id,
                        skip_own=self._skip_own,
                        skip_history=self._skip_history,
                    ):
                        if not self._running:
                            break
                        self._message_queue.put(message)
                    if not self._running:
                        break
            else:
                # Stream all messages
                async for message in self._backend.stream_messages(
                    skip_own=self._skip_own,
                    skip_history=self._skip_history,
                ):
                    if not self._running:
                        break
                    self._message_queue.put(message)
        finally:
            queue_task.cancel()

    async def _resolve_channels(self):
        """Resolve channel names to IDs.

        For each channel in self._channels, determine if it's an ID or name
        and resolve names to IDs using the backend's fetch_channel method.
        """
        if not self._channels:
            return

        for channel in self._channels:
            try:
                # First try to fetch by ID
                result = await self._backend.fetch_channel(id=channel)
                if result:
                    self._resolved_channel_ids.add(result.id)
                    continue

                # If not found by ID, try by name
                result = await self._backend.fetch_channel(name=channel)
                if result:
                    self._resolved_channel_ids.add(result.id)
                    log.info(f"Resolved channel name '{channel}' to ID '{result.id}'")
                else:
                    log.warning(f"Could not resolve channel: {channel}")
            except NotImplementedError:
                # Backend doesn't support fetch_channel, assume it's an ID
                self._resolved_channel_ids.add(channel)
                log.debug(f"Backend doesn't support fetch_channel, using '{channel}' as ID")
            except Exception as e:
                log.warning(f"Error resolving channel '{channel}': {e}, using as ID")
                self._resolved_channel_ids.add(channel)

    async def _process_queue(self):
        """Process messages from the queue and push to CSP."""
        while self._running:
            try:
                await asyncio.sleep(0.01)
                messages: List[Message] = []
                while not self._message_queue.empty():
                    msg = self._message_queue.get_nowait()
                    if msg is None:
                        return
                    messages.append(msg)
                if messages:
                    self.push_tick(messages)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.exception(f"Error processing message queue: {e}")


# Create the CSP adapter definition
MessageReaderPushAdapter = py_push_adapter_def(
    "MessageReaderPushAdapter",
    MessageReaderPushAdapterImpl,
    ts[[Message]],
    backend=object,
    channels=set,
    skip_own=bool,
    skip_history=bool,
    memoize=False,
)


def message_reader(
    backend: BackendBase,
    channels: Optional[Set[str]] = None,
    skip_own: bool = True,
    skip_history: bool = True,
) -> ts[[Message]]:
    """Create a CSP time series of messages from a chatom backend.

    This is a convenience function that wraps the MessageReaderPushAdapter.

    Args:
        backend: The chatom backend to read from.
        channels: Optional set of channels to filter. Can be IDs or names;
            names will be resolved to IDs at connection time.
        skip_own: If True, skip messages from the bot itself.
        skip_history: If True, skip messages before the stream started.

    Returns:
        A time series of Message lists.

    Example:
        >>> @csp.graph
        ... def my_graph():
        ...     # Filter by channel ID
        ...     messages = message_reader(backend, channels={"C12345"})
        ...     # Or by channel name
        ...     messages = message_reader(backend, channels={"general", "support"})
        ...     csp.print("Message", messages)
    """
    return MessageReaderPushAdapter(
        backend=backend,
        channels=channels or set(),
        skip_own=skip_own,
        skip_history=skip_history,
    )


def _send_messages_thread(msg_queue: Queue, backend: BackendBase):
    """Thread function to send messages from queue using the backend."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        # Connect if not already connected
        if not backend.connected:
            await backend.connect()

        while True:
            msg = await loop.run_in_executor(None, msg_queue.get)
            msg_queue.task_done()

            if msg is None:
                break

            try:
                await backend.send_message(
                    channel_id=msg.channel_id,
                    content=msg.content,
                )
            except Exception:
                log.exception("Failed sending message")

    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


@csp.node
def message_writer(
    backend: object,  # BackendBase
    messages: ts[Message],
):
    """CSP node that writes messages to a chatom backend.

    This node receives messages on a time series and sends them
    using the backend's send_message method.

    Args:
        backend: The chatom backend to write to.
        messages: Time series of messages to send.

    Example:
        >>> @csp.graph
        ... def my_graph():
        ...     response = csp.const(Message(channel_id="stream123", content="Hello!"))
        ...     message_writer(backend, response)
    """
    with csp.state():
        s_queue: Queue = None
        s_thread: threading.Thread = None

    with csp.start():
        s_queue = Queue(maxsize=0)
        s_thread = threading.Thread(
            target=_send_messages_thread,
            args=(s_queue, backend),
            daemon=True,
        )
        s_thread.start()

    with csp.stop():
        if s_thread:
            s_queue.put(None)
            s_queue.join()
            s_thread.join(timeout=5.0)

    if csp.ticked(messages):
        s_queue.put(messages)
