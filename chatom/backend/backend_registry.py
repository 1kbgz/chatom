"""Backend registry for chatom.

This module provides the central registry for backend implementations.
"""

from collections.abc import Callable, Iterator
from importlib.metadata import entry_points
from threading import Lock
from typing import (
    Any,
    ClassVar,
)

from ..base import (
    Channel,
    Presence,
    User,
)
from ..format.variant import Format
from .backend import BackendBase

__all__ = (
    "BackendRegistry",
    "get_backend",
    "get_backend_format",
    "list_backends",
    "register_backend",
)


class BackendRegistry:
    """Central registry for all backend implementations.

    This registry allows discovering and instantiating backends by name.
    Backends can be registered via entry points or programmatically.

    Example:
        >>> # Get a registered backend class
        >>> SlackBackend = BackendRegistry.get("slack")
        >>> backend = SlackBackend()
        >>>
        >>> # List all available backends
        >>> for name in BackendRegistry.list():
        ...     print(name)
    """

    _backends: ClassVar[dict[str, type[BackendBase]]] = {}
    _format_map: ClassVar[dict[str, Format]] = {}
    _instances: ClassVar[dict[str, BackendBase]] = {}
    _loaded: ClassVar[bool] = False
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def register(
        cls,
        backend_class: type[BackendBase],
        name: str | None = None,
    ) -> type[BackendBase]:
        """Register a backend class.

        Args:
            backend_class: The backend class to register.
            name: Optional name override. If not provided, uses
                  backend_class.name.

        Returns:
            The registered backend class (for use as decorator).

        Example:
            >>> @BackendRegistry.register
            ... class MyBackend(BackendBase):
            ...     name = "my_backend"
            ...     ...
        """
        backend_name = name or backend_class.name
        if not backend_name:
            raise ValueError(f"Backend class {backend_class.__name__} must have a name")
        cls._backends[backend_name.lower()] = backend_class
        cls._format_map[backend_name.lower()] = backend_class.format
        return backend_class

    @classmethod
    def get(cls, name: str) -> type[BackendBase]:
        """Get a backend class by name.

        Args:
            name: The backend name.

        Returns:
            The backend class.

        Raises:
            KeyError: If the backend is not registered.
        """
        cls._ensure_loaded()
        name_lower = name.lower()
        if name_lower not in cls._backends:
            raise KeyError(f"Backend '{name}' not found. Available: {list(cls._backends.keys())}")
        return cls._backends[name_lower]

    @classmethod
    def get_instance(cls, name: str, **kwargs: Any) -> BackendBase:
        """Get or create a backend instance.

        If an instance already exists for this name, returns it.
        Otherwise creates a new instance.

        Args:
            name: The backend name.
            **kwargs: Arguments passed to the backend constructor.

        Returns:
            The backend instance.
        """
        cls._ensure_loaded()
        name_lower = name.lower()
        if name_lower not in cls._instances:
            backend_class = cls.get(name)
            cls._instances[name_lower] = backend_class(**kwargs)
        return cls._instances[name_lower]

    @classmethod
    def get_format(cls, name: str) -> Format:
        """Get the preferred format for a backend.

        Args:
            name: The backend name.

        Returns:
            The Format enum value.
        """
        cls._ensure_loaded()
        return cls._format_map.get(name.lower(), Format.MARKDOWN)

    @classmethod
    def list(cls) -> list[str]:
        """List all registered backend names.

        Returns:
            List of backend names.
        """
        cls._ensure_loaded()
        return list(cls._backends.keys())

    @classmethod
    def items(cls) -> Iterator[tuple[str, type[BackendBase]]]:
        """Iterate over all registered backends.

        Yields:
            Tuples of (name, backend_class).
        """
        cls._ensure_loaded()
        yield from cls._backends.items()

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached backend instances."""
        cls._instances.clear()

    @classmethod
    def _ensure_loaded(cls) -> None:
        """Ensure entry points have been loaded."""
        if not cls._loaded:
            with cls._lock:
                if not cls._loaded:
                    cls._load_entry_points()
                    cls._loaded = True

    @classmethod
    def _load_entry_points(cls) -> None:
        """Load backends from entry points."""
        try:
            eps = entry_points(group="chatom.backends")
            for ep in eps:
                try:
                    backend_class = ep.load()
                    if isinstance(backend_class, type) and issubclass(backend_class, BackendBase):
                        cls.register(backend_class, name=ep.name)
                except Exception:  # noqa: BLE001, S110
                    # Log but don't fail on individual entry point errors
                    pass
        except Exception:  # noqa: BLE001, S110
            # Entry points may not be available in all environments
            pass

    @classmethod
    def register_all_types(cls) -> None:
        """Register all backend types for type conversion.

        This iterates over all registered backends and registers their
        user_class, channel_class, and presence_class with the conversion
        module. Each backend class should define these ClassVar attributes.

        This is called lazily when conversion functions are first used.
        """
        # Import here to avoid circular imports
        from ..base.conversion import register_backend_type

        cls._ensure_loaded()

        for backend_name, backend_class in cls._backends.items():
            try:
                # Check if the backend class has the type class attributes
                user_class = getattr(backend_class, "user_class", None)
                channel_class = getattr(backend_class, "channel_class", None)
                presence_class = getattr(backend_class, "presence_class", None)

                # Register types if they exist
                if user_class is not None:
                    register_backend_type(backend_name, User, user_class)
                if channel_class is not None:
                    register_backend_type(backend_name, Channel, channel_class)
                if presence_class is not None:
                    register_backend_type(backend_name, Presence, presence_class)
            except Exception:  # noqa: BLE001, S110
                # Skip backends that fail to register
                pass


# Convenience functions
def register_backend(
    backend_class: type[BackendBase] | None = None,
    *,
    name: str | None = None,
) -> type[BackendBase] | Callable[[type[BackendBase]], type[BackendBase]]:
    """Register a backend class with the registry.

    Can be used as a decorator with or without arguments.

    Args:
        backend_class: The backend class to register.
        name: Optional name override.

    Returns:
        The registered class or a decorator.

    Example:
        >>> @register_backend
        ... class MyBackend(BackendBase):
        ...     name = "my_backend"
        ...
        >>> @register_backend(name="custom_name")
        ... class AnotherBackend(BackendBase):
        ...     ...
    """
    if backend_class is None:
        # Called with arguments: @register_backend(name="...")
        def decorator(cls: type[BackendBase]) -> type[BackendBase]:
            return BackendRegistry.register(cls, name=name)

        return decorator
    else:
        # Called without arguments: @register_backend
        return BackendRegistry.register(backend_class, name=name)


def get_backend(name: str) -> type[BackendBase]:
    """Get a backend class by name.

    Args:
        name: The backend name.

    Returns:
        The backend class.
    """
    return BackendRegistry.get(name)


def get_backend_format(name: str) -> Format:
    """Get the preferred format for a backend.

    This function replaces get_format_for_backend and uses the
    backend registry.

    Args:
        name: The backend name.

    Returns:
        The Format enum value.
    """
    return BackendRegistry.get_format(name)


def list_backends() -> list[str]:
    """List all available backend names.

    Returns:
        List of registered backend names.
    """
    return BackendRegistry.list()
