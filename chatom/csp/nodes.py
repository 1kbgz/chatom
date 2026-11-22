"""CSP nodes and push adapters for chatom backends.

This module provides the low-level CSP nodes for reading and writing
messages using chatom backends.
"""

import asyncio
import contextlib
import logging
import threading
from collections.abc import Callable
from queue import Queue

import csp
from csp import ts
from csp.impl.pushadapter import PushInputAdapter
from csp.impl.wiring import py_push_adapter_def

from ..backend import BackendBase
from ..base import Channel, Message, Presence
from .runner import BackendRunner

__all__ = (
    "MessageReaderPushAdapter",
    "_send_messages_thread",
    "message_reader",
    "message_writer",
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
        channels: set[str] | None = None,
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
        self._resolved_channel_ids: set[str] = set()
        self._skip_own = skip_own
        self._skip_history = skip_history
        self._thread: threading.Thread | None = None
        self._running_event = threading.Event()  # Thread-safe running flag
        self._message_queue: Queue = Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._error: Exception | None = None
        self._shutdown_event: asyncio.Event | None = None

    def start(self, starttime, endtime):
        """Start the adapter."""
        log.debug(f"MessageReaderPushAdapter.start() called, starttime={starttime}, endtime={endtime}")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running_event.set()
        self._thread.start()
        log.debug("MessageReaderPushAdapter thread started")
        # Push an initial empty tick to signal to CSP that this adapter is active
        # This prevents CSP from exiting early before any messages arrive
        self.push_tick([])

    def stop(self):
        """Stop the adapter."""
        log.debug("MessageReaderPushAdapter.stop() called")
        if self._running_event.is_set():
            self._running_event.clear()
            self._message_queue.put(None)
            # Capture local refs to avoid TOCTOU race with _async_run_with_setup's finally
            shutdown_event = self._shutdown_event
            loop = self._loop
            # Signal shutdown via the event rather than stopping the loop
            if shutdown_event and loop:
                loop.call_soon_threadsafe(shutdown_event.set)
            if self._thread:
                self._thread.join(timeout=2.0)  # Shorter timeout for faster Ctrl+C response

        if self._error:
            raise self._error

    def _run(self):
        """Run the message stream on the backend's shared runner.

        The stream runs on the runner's loop, the same connection the writer
        and presence threads use, and this thread waits for it to finish.
        """
        log.debug("MessageReaderPushAdapter._run() thread function starting")
        runner = BackendRunner.acquire(self._backend)
        try:
            runner.call(self._async_run_with_setup).result()
        except Exception as e:
            log.exception(f"Error in message reader: {e}")  # noqa: TRY401
            self._error = e
            self._running_event.clear()
        finally:
            self._message_queue.put(None)
            runner.release()
        log.debug("MessageReaderPushAdapter._run() thread function finished")

    async def _async_run_with_setup(self, backend: BackendBase):
        """Async wrapper that captures the loop for external stop calls."""
        log.debug("_async_run_with_setup starting")
        self._loop = asyncio.get_running_loop()
        self._shutdown_event = asyncio.Event()
        try:
            await self._async_run(backend)
        finally:
            self._loop = None
            self._shutdown_event = None
        log.debug("_async_run_with_setup finished")

    async def _async_run(self, thread_backend: BackendBase):
        """Async main loop for reading messages."""
        log.debug("_async_run starting")

        # Resolve channel names to IDs
        await self._resolve_channels(thread_backend)
        log.debug(f"Resolved channels: {self._resolved_channel_ids}")

        # Start processing queue in parallel with reading
        queue_task = asyncio.create_task(self._process_queue())

        try:
            # If we have specific channels, stream each one
            if self._resolved_channel_ids:
                # For now, stream from first channel
                # TODO: Support multiple channels with asyncio.gather
                for channel_id in self._resolved_channel_ids:
                    log.debug(f"Starting to stream messages from channel {channel_id}")
                    stream = thread_backend.stream_messages(
                        channel=channel_id,
                        skip_own=self._skip_own,
                        skip_history=self._skip_history,
                    )
                    await self._consume_stream(stream)
                    log.debug(f"Stream from channel {channel_id} ended")
                    if not self._running_event.is_set() or self._shutdown_event.is_set():
                        break
            else:
                # Stream all messages
                log.debug("Starting to stream all messages")
                stream = thread_backend.stream_messages(
                    skip_own=self._skip_own,
                    skip_history=self._skip_history,
                )
                await self._consume_stream(stream)
                log.debug("Stream all messages ended")
        finally:
            queue_task.cancel()
            try:
                await queue_task
            except asyncio.CancelledError:
                pass

    async def _consume_stream(self, stream, timeout: float = 30.0):
        """Consume an async stream with shutdown and timeout support.

        Wraps stream consumption in a task and races against shutdown,
        ensuring responsive shutdown even when messages are infrequent.

        Args:
            stream: An async iterable of messages.
            timeout: Seconds to wait before logging a health check (default 30s).
                     Set to None to disable timeout logging.
        """

        async def drain_to_queue():
            async for message in stream:
                if not self._running_event.is_set():
                    break
                log.debug(f"Received message: {message.id}")
                self._message_queue.put(message)

        consumer = asyncio.create_task(drain_to_queue())
        shutdown = asyncio.create_task(self._shutdown_event.wait())

        try:
            while not consumer.done() and not shutdown.done():
                done, _ = await asyncio.wait(
                    [consumer, shutdown],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=timeout,
                )
                if not done:
                    log.debug(f"Stream idle for {timeout}s, still waiting...")
        finally:
            if not consumer.done():
                consumer.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await consumer
            if not shutdown.done():
                shutdown.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await shutdown

        # Propagate any exception from the consumer
        if consumer.done() and not consumer.cancelled():
            consumer.result()

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
            except Exception as e:  # noqa: BLE001
                log.warning(f"Error resolving channel '{channel}': {e}, using as ID")
                self._resolved_channel_ids.add(channel)

    async def _process_queue(self):
        """Process messages from the queue and push to CSP."""
        while self._running_event.is_set():
            try:
                await asyncio.sleep(0.01)
                messages: list[Message] = []
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
                log.exception(f"Error processing message queue: {e}")  # noqa: TRY401


# Create the CSP adapter definition
MessageReaderPushAdapter = py_push_adapter_def(
    "MessageReaderPushAdapter",
    MessageReaderPushAdapterImpl,
    ts[list[Message]],
    backend=object,
    channels=set,
    skip_own=bool,
    skip_history=bool,
    memoize=False,
)


def message_reader(
    backend: BackendBase,
    channels: set[str] | None = None,
    skip_own: bool = True,
    skip_history: bool = True,
) -> ts[list[Message]]:
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


async def _send_one(backend: BackendBase, msg: Message, on_sent: Callable[[Message, Message], None] | None) -> None:
    """Send one message, then upload any attachments that carry binary data."""
    log.debug(f"Sending message to channel_id={msg.channel_id}")
    # Separate attachments with binary data from URL-only ones
    url_attachments = []
    upload_attachments = []
    for att in msg.attachments:
        if getattr(att, "has_data", False) and att.data is not None:
            upload_attachments.append((att, att.data))
        else:
            url_attachments.append(att)

    # Send the main message (text + url attachments + embeds)
    kwargs = {}
    if url_attachments:
        kwargs["attachments"] = url_attachments
    if msg.embeds:
        kwargs["embeds"] = msg.embeds
    if msg.thread is not None:
        kwargs["thread"] = msg.thread
    if msg.reply_to is not None:
        kwargs["reply_to"] = msg.reply_to
    elif msg.reference is not None and msg.reference.message_id:
        kwargs["reply_to"] = msg.reference.message_id
    if msg.components is not None and msg.components.rows:
        from chatom.format import attach_components_for_backend

        kwargs["content"] = msg.content
        attach_components_for_backend(kwargs, msg.components, backend.get_format())
        content_to_send = str(kwargs.pop("content"))
    else:
        content_to_send = msg.content
    sent = await backend.send_message(
        channel=msg.channel_id,
        content=content_to_send,
        **kwargs,
    )
    if on_sent is not None:
        on_sent(msg, sent)

    # Upload any attachments with binary data
    for att, data in upload_attachments:
        try:
            uploaded = await backend.upload_file(
                channel=msg.channel_id,
                data=data,
                filename=att.filename or "file",
                content_type=getattr(att, "content_type", ""),
            )
            if on_sent is not None:
                on_sent(Message(channel=Channel(id=msg.channel_id), attachments=[att]), uploaded)
        except NotImplementedError:
            log.warning(f"Backend {type(backend).__name__} does not support file uploads, skipping {att.filename!r}")
        except Exception:
            log.exception(f"Failed uploading {att.filename!r}")

    log.debug("Message sent successfully")


def _send_messages_thread(msg_queue: Queue, backend: BackendBase, on_sent: Callable[[Message, Message], None] | None = None):
    """Thread function to send messages from queue using the backend.

    Sends go through the backend's shared runner, so the writer reuses the
    reader's connection instead of opening its own. ``on_sent`` observes the
    returned platform message for the text send and each separate binary
    attachment upload.
    """
    log.debug("Message writer thread started")
    runner = BackendRunner.acquire(backend)
    try:
        while True:
            log.debug("Waiting for message from queue...")
            msg = msg_queue.get()
            msg_queue.task_done()

            if msg is None:
                log.debug("Received None, stopping writer thread")
                break

            try:
                runner.call(lambda b, m=msg: _send_one(b, m, on_sent)).result()
            except Exception:
                log.exception("Failed sending message")
    finally:
        runner.release()
    log.debug("Message writer thread finished")


async def _set_one_presence(backend: BackendBase, presence: Presence | str, timeout: float) -> None:
    log.debug(f"Setting presence to status={getattr(presence, 'status', presence)}")
    # Handle both Presence objects and status strings
    status = str(presence.status.value) if isinstance(presence, Presence) else str(presence)
    try:
        await asyncio.wait_for(backend.set_presence(status), timeout=timeout)
        log.debug("Presence set successfully")
    except TimeoutError:
        log.error("Timeout setting presence")


def _set_presence_thread(presence_queue: Queue, backend: BackendBase):
    """Thread function to set presence from queue using the backend's shared runner."""
    log.debug("Presence writer thread started")
    runner = BackendRunner.acquire(backend)
    try:
        while True:
            log.debug("Waiting for presence from queue...")
            item = presence_queue.get()
            presence_queue.task_done()

            if item is None:
                log.debug("Received None, stopping presence thread")
                break

            presence, timeout = item
            try:
                runner.call(lambda b, p=presence, t=timeout: _set_one_presence(b, p, t)).result()
            except Exception:
                log.exception("Failed setting presence")
    finally:
        runner.release()
    log.debug("Presence writer thread finished")


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
        s_queue: Queue | None = None
        s_thread: threading.Thread | None = None

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
            # Use threading.Thread to join queue with timeout to avoid potential deadlock
            joiner = threading.Thread(target=s_queue.join, daemon=True)
            joiner.start()
            joiner.join(timeout=5.0)
            s_thread.join(timeout=5.0)

    if csp.ticked(messages):
        s_queue.put(messages)
