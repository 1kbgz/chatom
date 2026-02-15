"""Backend type conversion and validation for chatom.

This module provides functionality for validating and converting between
base chatom types and backend-specific types. It enables:

1. Validation: Check if a base type instance can be promoted to a backend type
2. Promotion: Convert a base type (e.g., User) to a backend type (e.g., DiscordUser)
3. Demotion: Convert a backend type back to a base type

Example usage:
    >>> from chatom import User
    >>> from chatom.base.conversion import can_promote, promote, demote
    >>>
    >>> user = User(id="123", name="Test")
    >>> if can_promote(user, "discord"):
    ...     discord_user = promote(user, "discord")
    >>>
    >>> base_user = demote(discord_user)
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, cast

from pydantic import ValidationError

from .base import BaseModel

__all__ = (
    # Core functions
    "can_promote",
    "promote",
    "demote",
    "validate_for_backend",
    # Registry functions
    "register_backend_type",
    "get_backend_type",
    "get_base_type",
    "list_backends_for_type",
    # Validation result
    "ValidationResult",
    # Exceptions
    "ConversionError",
    "BackendNotFoundError",
)


T = TypeVar("T", bound=BaseModel)


class ConversionError(Exception):
    """Raised when a type conversion fails."""

    pass


class BackendNotFoundError(ConversionError):
    """Raised when a backend or backend type is not found."""

    pass


class ValidationResult:
    """Result of validating a base type for a backend.

    Attributes:
        valid: Whether the instance is valid for the backend.
        missing_required: List of required fields that are missing values.
        invalid_fields: Dict of field names to validation error messages.
        warnings: List of warning messages (non-fatal issues).
    """

    def __init__(
        self,
        valid: bool = True,
        missing_required: Optional[List[str]] = None,
        invalid_fields: Optional[Dict[str, str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.valid = valid
        self.missing_required = missing_required or []
        self.invalid_fields = invalid_fields or {}
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean context."""
        return self.valid

    def __repr__(self) -> str:
        return (
            f"ValidationResult(valid={self.valid}, "
            f"missing_required={self.missing_required}, "
            f"invalid_fields={self.invalid_fields}, "
            f"warnings={self.warnings})"
        )


# Registry mapping: base_type_name -> backend -> backend_type_class
_TYPE_REGISTRY: Dict[str, Dict[str, Type[BaseModel]]] = {}

# Mapping from backend type class to its base type class
_BASE_TYPE_MAP: Dict[Type[BaseModel], Type[BaseModel]] = {}

# Flag to track if types have been registered
_TYPES_REGISTERED: bool = False


def _ensure_types_registered() -> None:
    """Ensure backend types are registered.

    This is called lazily when conversion functions are first used,
    avoiding circular import issues during module initialization.
    """
    global _TYPES_REGISTERED
    if _TYPES_REGISTERED:
        return
    _TYPES_REGISTERED = True
    _register_all_types()


def register_backend_type(
    backend: str,
    base_type: Type[BaseModel],
    backend_type: Type[BaseModel],
) -> None:
    """Register a backend-specific type for a base type.

    This function registers the relationship between a base chatom type
    and its backend-specific variant. Called during module initialization.

    Args:
        backend: The backend identifier (e.g., "discord", "slack").
        base_type: The base chatom type (e.g., User).
        backend_type: The backend-specific type (e.g., DiscordUser).
    """
    base_name = base_type.__name__
    if base_name not in _TYPE_REGISTRY:
        _TYPE_REGISTRY[base_name] = {}
    _TYPE_REGISTRY[base_name][backend] = backend_type
    _BASE_TYPE_MAP[backend_type] = base_type


def get_backend_type(
    base_type: Type[T],
    backend: str,
) -> Optional[Type[BaseModel]]:
    """Get the backend-specific type for a base type.

    Args:
        base_type: The base type class.
        backend: The backend identifier.

    Returns:
        The backend-specific type class, or None if not registered.
    """
    _ensure_types_registered()
    base_name = base_type.__name__
    return _TYPE_REGISTRY.get(base_name, {}).get(backend)


def get_base_type(backend_type: Type[BaseModel]) -> Optional[Type[BaseModel]]:
    """Get the base type for a backend-specific type.

    Args:
        backend_type: The backend-specific type class.

    Returns:
        The base type class, or None if not registered.
    """
    _ensure_types_registered()
    return _BASE_TYPE_MAP.get(backend_type)


def list_backends_for_type(base_type: Type[BaseModel]) -> List[str]:
    """List all backends that have a registered type for the given base type.

    Args:
        base_type: The base type class.

    Returns:
        List of backend identifiers.
    """
    _ensure_types_registered()
    base_name = base_type.__name__
    return list(_TYPE_REGISTRY.get(base_name, {}).keys())


def validate_for_backend(
    instance: BaseModel,
    backend: str,
) -> ValidationResult:
    """Validate if a base type instance can be promoted to a backend type.

    This performs validation to check if the instance has all required
    fields and if the values are compatible with the backend type.

    Args:
        instance: The base type instance to validate.
        backend: The backend identifier.

    Returns:
        ValidationResult with details about validity and any issues.

    Raises:
        BackendNotFoundError: If the backend type is not registered.
    """
    _ensure_types_registered()

    # Get the backend type
    base_type: Type[BaseModel] = type(instance)

    # Walk up the inheritance chain to find the base type
    while base_type.__name__ not in _TYPE_REGISTRY:
        if base_type.__bases__:
            for parent in base_type.__bases__:
                if issubclass(parent, BaseModel) and parent.__name__ in _TYPE_REGISTRY:
                    base_type = parent
                    break
            else:
                # No registered parent found, use the original type name
                base_type = type(instance)
                break
        else:
            break

    backend_type = get_backend_type(base_type, backend)
    if backend_type is None:
        raise BackendNotFoundError(f"No {backend} type registered for {base_type.__name__}")

    missing_required = []
    invalid_fields = {}
    warnings = []

    # Get the current data from the instance
    data = instance.model_dump()

    # Try to construct the backend type to check validation
    try:
        backend_type.model_validate(data)
    except ValidationError as e:
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            error_type = error["type"]
            error_msg = error["msg"]

            if error_type == "missing":
                missing_required.append(field_path)
            else:
                invalid_fields[field_path] = error_msg

    valid = len(missing_required) == 0 and len(invalid_fields) == 0

    return ValidationResult(
        valid=valid,
        missing_required=missing_required,
        invalid_fields=invalid_fields,
        warnings=warnings,
    )


def can_promote(
    instance: BaseModel,
    backend: str,
) -> bool:
    """Check if a base type instance can be promoted to a backend type.

    This is a convenience wrapper around validate_for_backend that
    returns a simple boolean.

    Args:
        instance: The base type instance to check.
        backend: The backend identifier.

    Returns:
        True if the instance can be promoted, False otherwise.

    Raises:
        BackendNotFoundError: If the backend type is not registered.
    """
    result = validate_for_backend(instance, backend)
    return result.valid


def promote(
    instance: T,
    backend: str,
    **extra_fields: Any,
) -> BaseModel:
    """Promote a base type instance to a backend-specific type.

    Creates a new instance of the backend-specific type using the
    data from the base instance, plus any additional backend-specific
    fields provided.

    Args:
        instance: The base type instance to promote.
        backend: The backend identifier.
        **extra_fields: Additional fields for the backend type.

    Returns:
        A new instance of the backend-specific type.

    Raises:
        BackendNotFoundError: If the backend type is not registered.
        ConversionError: If the promotion fails validation.
    """
    _ensure_types_registered()

    # Get the backend type
    base_type: Type[BaseModel] = type(instance)

    # If the instance is already a backend type, get its base type
    registered_base = _BASE_TYPE_MAP.get(base_type)
    if registered_base is not None:
        base_type = registered_base

    # Walk up the inheritance chain to find the base type
    original_type = base_type
    while base_type.__name__ not in _TYPE_REGISTRY:
        if base_type.__bases__:
            for parent in base_type.__bases__:
                if issubclass(parent, BaseModel) and parent.__name__ in _TYPE_REGISTRY:
                    base_type = parent
                    break
            else:
                base_type = original_type
                break
        else:
            break

    backend_type = get_backend_type(base_type, backend)
    if backend_type is None:
        raise BackendNotFoundError(f"No {backend} type registered for {base_type.__name__}")

    # Get data from the instance
    data = instance.model_dump()

    # Merge with extra fields
    data.update(extra_fields)

    # Create the backend type instance
    try:
        return backend_type.model_validate(data)
    except ValidationError as e:
        raise ConversionError(f"Failed to promote {type(instance).__name__} to {backend_type.__name__}: {e}")


def demote(instance: BaseModel) -> BaseModel:
    """Demote a backend-specific type instance to its base type.

    Creates a new instance of the base type using only the base
    type's fields, stripping away backend-specific fields.

    Args:
        instance: The backend-specific type instance to demote.

    Returns:
        A new instance of the base type.

    Raises:
        ConversionError: If the instance is not a registered backend type.
    """
    _ensure_types_registered()

    instance_type = type(instance)
    base_type = _BASE_TYPE_MAP.get(instance_type)

    if base_type is None:
        # Check if it's already a base type (has entries in registry)
        if instance_type.__name__ in _TYPE_REGISTRY:
            # Already a base type, return a copy
            return instance.model_copy()

        # Check parent classes
        for parent in instance_type.__mro__:
            if parent in _BASE_TYPE_MAP:
                base_type = _BASE_TYPE_MAP[cast(Type[BaseModel], parent)]
                break
            if parent.__name__ in _TYPE_REGISTRY:
                # It's a base type
                return instance.model_copy()

        if base_type is None:
            raise ConversionError(f"{instance_type.__name__} is not a registered backend type")

    # Get data and filter to base type fields only
    # base_type is guaranteed to be non-None here due to the check above
    assert base_type is not None
    data = instance.model_dump()
    base_fields = set(base_type.model_fields.keys())
    filtered_data = {k: v for k, v in data.items() if k in base_fields}

    try:
        return base_type.model_validate(filtered_data)
    except ValidationError as e:
        raise ConversionError(f"Failed to demote {instance_type.__name__} to {base_type.__name__}: {e}")


# =============================================================================
# Backend type registration
# =============================================================================


def _register_all_types() -> None:
    """Register all known backend types from the backend registry.

    This delegates to BackendRegistry.register_all_types() which uses
    entry points to discover backends and their type classes.

    This is called lazily when conversion functions are first used.
    """
    try:
        from ..backend import BackendRegistry

        BackendRegistry.register_all_types()
    except ImportError:
        # Fallback if backend_registry not available
        pass
