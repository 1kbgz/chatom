"""One connected backend per process, shared by every CSP reader and writer."""

import asyncio
import concurrent.futures
import contextlib
import logging
import threading
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, TypeVar

from ..backend import BackendBase

__all__ = ("BackendRunner",)

log = logging.getLogger(__name__)

T = TypeVar("T")


class BackendRunner:
    """Run one connected copy of a backend on a dedicated event loop thread.

    Readers, writers, and other callers that acquire a runner for the same
    backend object share it, so a platform gets a single connection per process:
    one IRC nick, one Discord gateway session, one Symphony login. The copy is
    made from the backend's config so the caller's object is never bound to this
    thread's loop.

    Example:
        >>> runner = BackendRunner.acquire(backend)
        >>> bot = runner.call(lambda b: b.get_bot_info()).result(timeout=10)
        >>> runner.release()
    """

    _registry: ClassVar[dict[int, "BackendRunner"]] = {}
    _registry_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, backend: BackendBase):
        self._source = backend
        self.backend: BackendBase = type(backend)(config=backend.config)
        self.loop = asyncio.new_event_loop()
        self._refs = 0
        self._connect_task: asyncio.Task[None] | None = None
        self._thread = threading.Thread(target=self.loop.run_forever, name=f"chatom-{type(backend).__name__}", daemon=True)
        self._thread.start()

    @classmethod
    def acquire(cls, backend: BackendBase) -> "BackendRunner":
        """Return the runner for ``backend``, starting one if none is running."""
        with cls._registry_lock:
            runner = cls._registry.get(id(backend))
            if runner is None:
                runner = cls(backend)
                cls._registry[id(backend)] = runner
            runner._refs += 1
            return runner

    def release(self, timeout: float = 5.0) -> None:
        """Drop one reference; the last one disconnects and stops the loop."""
        with self._registry_lock:
            self._refs -= 1
            if self._refs > 0:
                return
            self._registry.pop(id(self._source), None)
        try:
            asyncio.run_coroutine_threadsafe(self._disconnect(), self.loop).result(timeout)
        except Exception:
            log.exception("Failed disconnecting %s", type(self.backend).__name__)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(timeout)
        if not self._thread.is_alive():
            self.loop.close()

    def call(self, fn: Callable[[BackendBase], Awaitable[T]]) -> concurrent.futures.Future[T]:
        """Run ``fn(backend)`` on the runner's loop once the backend is connected."""
        return asyncio.run_coroutine_threadsafe(self._invoke(fn), self.loop)

    def ready(self, timeout: float | None = None) -> BackendBase:
        """Block until the backend is connected and return it."""
        return self.call(_connected).result(timeout)

    async def _invoke(self, fn: Callable[[BackendBase], Awaitable[Any]]) -> Any:
        # Everything here runs on the one loop thread, so the check and the
        # assignment cannot interleave with another caller.
        if self._connect_task is None:
            self._connect_task = asyncio.ensure_future(self.backend.connect())
        # A cancelled caller must not cancel the connection everyone shares.
        await asyncio.shield(self._connect_task)
        return await fn(self.backend)

    async def _disconnect(self) -> None:
        task = self._connect_task
        if task is None:
            return
        if not task.done():
            task.cancel()
        with contextlib.suppress(BaseException):
            await task
        if not task.cancelled() and task.exception() is None:
            await self.backend.disconnect()


async def _connected(backend: BackendBase) -> BackendBase:
    return backend
