"""CSP push adapter for chatom interaction streams.

This module mirrors ``chatom.csp.nodes.message_reader`` but for
:class:`~chatom.base.Interaction` events. CSP itself remains optional;
the public surface in ``chatom.csp.__init__`` guards the import.
"""

import asyncio
import contextlib
import logging
import threading
from queue import Queue
from typing import List, Optional

from csp import ts
from csp.impl.pushadapter import PushInputAdapter
from csp.impl.wiring import py_push_adapter_def

from ..backend import BackendBase
from ..base import Interaction

__all__ = (
    "InteractionReaderPushAdapter",
    "interaction_reader",
)

log = logging.getLogger(__name__)


class InteractionReaderPushAdapterImpl(PushInputAdapter):
    """Read interactions from a chatom backend and push them into CSP."""

    def __init__(
        self,
        backend: BackendBase,
        channel: Optional[str] = None,
    ):
        self._backend = backend
        self._channel = channel
        self._thread: Optional[threading.Thread] = None
        self._running_event = threading.Event()
        self._queue: Queue = Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._error: Optional[Exception] = None
        self._shutdown_event: Optional[asyncio.Event] = None

    def start(self, starttime, endtime):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._running_event.set()
        self._thread.start()
        # Initial empty tick so CSP doesn't exit before any interaction arrives
        self.push_tick([])

    def stop(self):
        if self._running_event.is_set():
            self._running_event.clear()
            self._queue.put(None)
            shutdown_event = self._shutdown_event
            loop = self._loop
            if shutdown_event and loop:
                loop.call_soon_threadsafe(shutdown_event.set)
            if self._thread:
                self._thread.join(timeout=2.0)
        if self._error:
            raise self._error

    def _run(self):
        try:
            asyncio.run(self._async_run_with_setup())
        except Exception as e:
            log.exception("Error in interaction reader: %s", e)
            self._error = e
            self._running_event.clear()
        finally:
            self._queue.put(None)

    async def _async_run_with_setup(self):
        self._loop = asyncio.get_running_loop()
        self._shutdown_event = asyncio.Event()
        try:
            await self._async_run()
        finally:
            self._loop = None
            self._shutdown_event = None

    async def _async_run(self):
        # Separate backend instance for this thread's loop, same as message_reader
        backend_class = type(self._backend)
        thread_backend = backend_class(config=self._backend.config)
        await thread_backend.connect()

        drain_task = asyncio.create_task(self._drain())
        try:
            try:
                stream = thread_backend.stream_interactions(channel=self._channel)
            except NotImplementedError:
                log.warning(
                    "Backend %s does not support stream_interactions(); interaction reader will stay idle.",
                    type(thread_backend).__name__,
                )
                await self._shutdown_event.wait()
                return

            consumer = asyncio.create_task(self._consume(stream))
            shutdown = asyncio.create_task(self._shutdown_event.wait())
            try:
                done, _ = await asyncio.wait(
                    [consumer, shutdown],
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                if not consumer.done():
                    consumer.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await consumer
                if not shutdown.done():
                    shutdown.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await shutdown
            if consumer.done() and not consumer.cancelled():
                consumer.result()
        finally:
            drain_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await drain_task
            with contextlib.suppress(Exception):
                await thread_backend.disconnect()

    async def _consume(self, stream):
        async for event in stream:
            if not self._running_event.is_set():
                break
            self._queue.put(event)

    async def _drain(self):
        """Push queued interactions to CSP."""
        while self._running_event.is_set():
            try:
                await asyncio.sleep(0.01)
                batch: List[Interaction] = []
                while not self._queue.empty():
                    item = self._queue.get_nowait()
                    if item is None:
                        return
                    batch.append(item)
                if batch:
                    self.push_tick(batch)
            except asyncio.CancelledError:
                break
            except Exception:
                log.exception("Error draining interaction queue")


InteractionReaderPushAdapter = py_push_adapter_def(
    "InteractionReaderPushAdapter",
    InteractionReaderPushAdapterImpl,
    ts[List[Interaction]],
    backend=object,
    channel=(str, None),
    memoize=False,
)


def interaction_reader(
    backend: BackendBase,
    channel: Optional[str] = None,
) -> "ts[List[Interaction]]":
    """Create a CSP time series of interactions from a chatom backend.

    Args:
        backend: The chatom backend to read from.
        channel: Optional channel filter.

    Returns:
        A CSP time series of :class:`~chatom.base.Interaction` lists.

    Example:
        >>> @csp.graph
        ... def g():
        ...     events = interaction_reader(backend)
        ...     csp.print("interaction", events)
    """
    return InteractionReaderPushAdapter(backend=backend, channel=channel)
