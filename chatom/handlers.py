"""Interaction handler registry.

Provides a small, dependency-free pub/sub for dispatching
:class:`~chatom.base.Interaction` events to registered callbacks,
keyed on ``action_id``. Usable with or without CSP.

Example::

    registry = InteractionRegistry()

    @registry.on("confirm_button")
    async def handle_confirm(event):
        await backend.send_message(event.channel_id, "Confirmed!")

    # Drive the registry from a backend stream
    async for event in backend.stream_interactions():
        await registry.dispatch(event)
"""

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from chatom.base import Interaction

__all__ = ("InteractionHandler", "InteractionRegistry")

log = logging.getLogger(__name__)

#: Handlers can be sync or async callables accepting a single
#: :class:`Interaction` argument. Async handlers are awaited; sync
#: handlers are called directly.
InteractionHandler = Callable[[Interaction], Union[Any, Awaitable[Any]]]


class InteractionRegistry:
    """Dispatch interactions to handlers keyed by ``action_id``.

    Handlers are called in registration order. A single handler can be
    registered for multiple action IDs by calling :meth:`register`
    repeatedly. Use ``action_id=""`` (or :meth:`register_default`) to
    register a catch-all handler that fires when no specific handler
    matches.
    """

    WILDCARD = ""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[InteractionHandler]] = {}

    # ----- registration -------------------------------------------------

    def register(self, action_id: str, handler: InteractionHandler) -> None:
        """Register ``handler`` for ``action_id``."""
        self._handlers.setdefault(action_id, []).append(handler)

    def register_default(self, handler: InteractionHandler) -> None:
        """Register a catch-all handler."""
        self.register(self.WILDCARD, handler)

    def unregister(self, action_id: str, handler: InteractionHandler) -> bool:
        """Remove a previously registered handler. Returns ``True`` if removed."""
        handlers = self._handlers.get(action_id)
        if not handlers:
            return False
        try:
            handlers.remove(handler)
        except ValueError:
            return False
        if not handlers:
            del self._handlers[action_id]
        return True

    def clear(self, action_id: Optional[str] = None) -> None:
        """Remove all handlers, or just those for ``action_id``."""
        if action_id is None:
            self._handlers.clear()
        else:
            self._handlers.pop(action_id, None)

    def on(self, action_id: str) -> Callable[[InteractionHandler], InteractionHandler]:
        """Decorator form of :meth:`register`.

        Example::

            @registry.on("my_button")
            def handle(event): ...
        """

        def decorator(fn: InteractionHandler) -> InteractionHandler:
            self.register(action_id, fn)
            return fn

        return decorator

    # ----- introspection ------------------------------------------------

    @property
    def action_ids(self) -> List[str]:
        """Return all registered action IDs (excluding the wildcard)."""
        return [aid for aid in self._handlers if aid != self.WILDCARD]

    def handlers_for(self, action_id: str) -> List[InteractionHandler]:
        """Return the handler list that :meth:`dispatch` would call."""
        specific = self._handlers.get(action_id, [])
        if specific:
            return list(specific)
        return list(self._handlers.get(self.WILDCARD, []))

    # ----- dispatch -----------------------------------------------------

    async def dispatch(self, event: Interaction) -> List[Any]:
        """Dispatch ``event`` to all matching handlers.

        Returns the list of handler results, in registration order.
        Exceptions from individual handlers are logged and do not
        prevent subsequent handlers from running.
        """
        results: List[Any] = []
        for handler in self.handlers_for(event.action_id):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    result = await result
                results.append(result)
            except Exception:
                log.exception(
                    "Interaction handler for action_id=%r raised",
                    event.action_id,
                )
        return results

    def dispatch_sync(self, event: Interaction) -> List[Any]:
        """Sync wrapper around :meth:`dispatch`.

        Runs the async dispatcher on the current event loop if one is
        running, otherwise in a short-lived loop. Useful for CSP nodes
        and other sync call sites.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Caller is already inside a running loop; schedule and
                # block on the result via a dedicated loop.
                return asyncio.run_coroutine_threadsafe(self.dispatch(event), loop).result()
        except RuntimeError:
            pass
        return asyncio.run(self.dispatch(event))
