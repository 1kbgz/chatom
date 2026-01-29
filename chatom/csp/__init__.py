"""CSP (Complex Event Processing) integration for chatom.

This module provides optional CSP integration for chatom backends,
allowing real-time message streaming and processing using the csp library.

CSP is an optional dependency. Install with: pip install csp

Example:
    >>> from chatom.symphony import SymphonyBackend, SymphonyConfig
    >>> from chatom.csp import BackendAdapter
    >>>
    >>> config = SymphonyConfig(host="company.symphony.com", ...)
    >>> backend = SymphonyBackend(config=config)
    >>> adapter = BackendAdapter(backend)
    >>>
    >>> @csp.graph
    >>> def my_graph():
    ...     messages = adapter.subscribe()
    ...     # Process messages...
    ...     adapter.publish(responses)
"""

# Check if csp is available
try:
    import csp  # noqa: F401

    HAS_CSP = True
except ImportError:
    HAS_CSP = False

if HAS_CSP:
    from .adapter import BackendAdapter
    from .nodes import message_reader, message_writer

    __all__ = (
        "BackendAdapter",
        "HAS_CSP",
        "message_reader",
        "message_writer",
    )
else:
    __all__ = ("HAS_CSP",)

    def BackendAdapter(*args, **kwargs):
        """Placeholder when csp is not installed."""
        raise ImportError("csp is not installed. Install with: pip install csp")

    def message_reader(*args, **kwargs):
        """Placeholder when csp is not installed."""
        raise ImportError("csp is not installed. Install with: pip install csp")

    def message_writer(*args, **kwargs):
        """Placeholder when csp is not installed."""
        raise ImportError("csp is not installed. Install with: pip install csp")
