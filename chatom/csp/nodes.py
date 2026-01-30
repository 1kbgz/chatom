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

from ..backend import BackendBase
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
        self._shutdown_event: Optional[asyncio.Event] = None

    def start(self, starttime, endtime):
        """Start the adapter."""
        log.debug(f"MessageReaderPushAdapter.start() called, starttime={starttime}, endtime={endtime}")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running = True
        self._thread.start()
        log.debug("MessageReaderPushAdapter thread started")
        # Push an initial empty tick to signal to CSP that this adapter is active
        # This prevents CSP from exiting early before any messages arrive
        self.push_tick([])

    def stop(self):
        """Stop the adapter."""
        log.debug("MessageReaderPushAdapter.stop() called")
        if self._running:
            self._running = False
            self._message_queue.put(None)
            # Signal shutdown via the event rather than stopping the loop
            if self._shutdown_event and self._loop:
                self._loop.call_soon_threadsafe(self._shutdown_event.set)
            if self._thread:
                self._thread.join(timeout=2.0)  # Shorter timeout for faster Ctrl+C response

        if self._error:
            raise self._error

    def _run(self):
        """Run the message stream in a background thread.

        Uses asyncio.run() which properly sets up the task context
        that aiohttp requires. This is critical because aiohttp's
        timeout context manager checks asyncio.current_task().
        """
        log.debug("MessageReaderPushAdapter._run() thread function starting")
        try:
            asyncio.run(self._async_run_with_setup())
        except Exception as e:
            log.exception(f"Error in message reader: {e}")
            self._error = e
            self._running = False
        finally:
            self._message_queue.put(None)
        log.debug("MessageReaderPushAdapter._run() thread function finished")

    async def _async_run_with_setup(self):
        """Async wrapper that captures the loop for external stop calls."""
        log.debug("_async_run_with_setup starting")
        self._loop = asyncio.get_running_loop()
        self._shutdown_event = asyncio.Event()
        try:
            await self._async_run()
        finally:
            self._loop = None
            self._shutdown_event = None
        log.debug("_async_run_with_setup finished")

    async def _async_run(self):
        """Async main loop for reading messages."""
        log.debug("_async_run starting")
        # Create a new backend instance for this thread to avoid event loop issues
        # This is necessary because aiohttp sessions are bound to specific event loops
        backend_class = type(self._backend)
        log.debug(f"Creating thread-local backend of type {backend_class.__name__}")
        thread_backend = backend_class(config=self._backend.config)
        log.debug("Connecting thread-local backend...")
        await thread_backend.connect()
        log.debug("Thread-local backend connected")

        # Resolve channel names to IDs
        await self._resolve_channels(thread_backend)
        log.debug(f"Resolved channels: {self._resolved_channel_ids}")

        # Start processing queue in parallel with reading
        queue_task = asyncio.create_task(self._process_queue())

        # Create a shutdown watcher task
        async def shutdown_watcher():
            await self._shutdown_event.wait()

        shutdown_task = asyncio.create_task(shutdown_watcher())

        try:
            # If we have specific channels, stream each one
            if self._resolved_channel_ids:
                # For now, stream from first channel
                # TODO: Support multiple channels with asyncio.gather
                for channel_id in self._resolved_channel_ids:
                    log.debug(f"Starting to stream messages from channel {channel_id}")
                    async for message in thread_backend.stream_messages(
                        channel_id=channel_id,
                        skip_own=self._skip_own,
                        skip_history=self._skip_history,
                    ):
                        log.debug(f"Received message: {message.id}")
                        if not self._running or self._shutdown_event.is_set():
                            log.debug("Stopping stream due to _running=False or shutdown_event")
                            break
                        self._message_queue.put(message)
                    log.debug(f"Stream from channel {channel_id} ended")
                    if not self._running or self._shutdown_event.is_set():
                        break
            else:
                # Stream all messages
                log.debug("Starting to stream all messages")
                async for message in thread_backend.stream_messages(
                    skip_own=self._skip_own,
                    skip_history=self._skip_history,
                ):
                    log.debug(f"Received message: {message.id}")
                    if not self._running or self._shutdown_event.is_set():
                        log.debug("Stopping stream due to _running=False or shutdown_event")
                        break
                    self._message_queue.put(message)
                log.debug("Stream all messages ended")
        finally:
            queue_task.cancel()
            shutdown_task.cancel()
            try:
                await queue_task
            except asyncio.CancelledError:
                pass
            try:
                await shutdown_task
            except asyncio.CancelledError:
                pass
            # Disconnect the thread-local backend
            try:
                await thread_backend.disconnect()
            except Exception:
                pass

    async def _resolve_channels(self, backend):
        """Resolve channel names to IDs.

        For each channel in self._channels, determine if it's an ID or name
        and resolve names to IDs using the backend's fetch_channel method.
        Symphony stream IDs look like 'wi__BW5M9bd910N25XXUP3___nrUDOBKdA'.
        """
        if not self._channels:
            return

        for channel in self._channels:
            try:
                # First try to fetch by ID
                result = await backend.fetch_channel(id=channel)
                if result:
                    self._resolved_channel_ids.add(result.id)
                    continue

                # If not found by ID, try by name
                result = await backend.fetch_channel(name=channel)
                if result:
                    self._resolved_channel_ids.add(result.id)
                    log.info(f"Resolved channel name '{channel}' to ID '{result.id}'")
                else:
                    # Could not find it, but it might still be a valid stream ID
                    # (e.g., the API returned None but the ID is still usable)
                    log.debug(f"Could not resolve channel '{channel}', using as-is")
                    self._resolved_channel_ids.add(channel)
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
    """Thread function to send messages from queue using the backend.

    Uses asyncio.run() which properly sets up the task context
    that aiohttp requires. We create a new backend instance in this thread
    to ensure the aiohttp session is bound to our event loop.
    """
    log.debug("Message writer thread started")

    async def run():
        # Create a new backend instance for this thread to avoid event loop issues
        # This is necessary because aiohttp sessions are bound to specific event loops
        backend_class = type(backend)
        log.debug(f"Creating thread-local backend of type {backend_class.__name__}")
        thread_backend = backend_class(config=backend.config)
        log.debug("Connecting thread-local backend...")
        await thread_backend.connect()
        log.debug("Thread-local backend connected")

        loop = asyncio.get_running_loop()
        try:
            while True:
                log.debug("Waiting for message from queue...")
                msg = await loop.run_in_executor(None, msg_queue.get)
                msg_queue.task_done()

                if msg is None:
                    log.debug("Received None, stopping writer thread")
                    break

                log.debug(f"Sending message to channel_id={msg.channel_id}")
                try:
                    await thread_backend.send_message(
                        channel=msg.channel_id,
                        content=msg.content,
                    )
                    log.debug("Message sent successfully")
                except Exception:
                    log.exception("Failed sending message")
        finally:
            # Disconnect cleanly
            log.debug("Disconnecting thread-local backend")
            try:
                await thread_backend.disconnect()
            except Exception:
                pass

    try:
        asyncio.run(run())
    except Exception:
        log.exception("Error in message writer thread")
    log.debug("Message writer thread finished")


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
