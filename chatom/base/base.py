"""Base model classes for chatom.

This module provides the foundational model classes that all chatom
data structures inherit from. It uses Pydantic for data validation
and serialization.
"""

from typing import Any, Dict, Self, TypeVar

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, PrivateAttr, model_validator

__all__ = ("BaseModel", "Field", "Identifiable")

T = TypeVar("T", bound="BaseModel")


class BaseModel(PydanticBaseModel):
    """Base model class for all chatom data structures.

    Provides common configuration and utilities for all models.
    Inherits from Pydantic's BaseModel for validation and serialization.

    Models can be marked as "incomplete" when they have partial information
    that needs to be resolved by a backend (e.g., a Channel with only a name
    but no id). Use `is_incomplete` to check, and `mark_incomplete()` /
    `mark_complete()` to change the state.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="allow",
        populate_by_name=True,
        validate_assignment=True,
    )

    # Private attribute to track if this object needs resolution
    _incomplete: bool = PrivateAttr(default=False)

    @property
    def is_incomplete(self) -> bool:
        """Check if this object is marked as incomplete.

        Incomplete objects have partial information and need to be
        resolved by a backend to populate missing fields.

        Returns:
            bool: True if the object is incomplete.
        """
        return self._incomplete

    def mark_incomplete(self) -> None:
        """Mark this object as incomplete.

        Call this when the object has partial information that needs
        to be resolved by a backend.
        """
        self._incomplete = True

    def mark_complete(self) -> None:
        """Mark this object as complete.

        Call this after a backend has resolved all missing fields.
        """
        self._incomplete = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation.

        Returns:
            Dict[str, Any]: Dictionary representation of the model.
        """
        return self.model_dump(exclude_none=True)

    def copy_with(self: T, **kwargs: Any) -> T:
        """Create a copy of the model with updated fields.

        Args:
            **kwargs: Fields to update in the copy.

        Returns:
            A new instance with the updated fields.
        """
        return self.model_copy(update=kwargs)


class Identifiable(BaseModel):
    """Base class for models with an identifier.

    Provides common id and name fields that most chat entities have.

    Objects can be created with partial information (e.g., just a name)
    and later resolved by a backend to populate missing fields like id.
    Use the `is_complete` property to check if an object has all required
    fields populated.
    """

    id: str = Field(
        default="",
        description="Platform-specific unique identifier.",
    )
    name: str = Field(
        default="",
        description="Human-readable name or display name.",
    )

    @property
    def is_complete(self) -> bool:
        """Check if this object has all required fields populated.

        An object is considered complete if it has an id. Subclasses may
        override this to add additional requirements.

        Returns:
            bool: True if the object is complete.
        """
        return bool(self.id)

    @property
    def is_resolvable(self) -> bool:
        """Check if this object has enough info to be resolved by a backend.

        An object is resolvable if it has at least an id OR a name that
        can be used to look it up.

        Returns:
            bool: True if the object can potentially be resolved.
        """
        return bool(self.id or self.name)

    @model_validator(mode="after")
    def _check_completeness(self) -> Self:
        """Auto-mark object as incomplete if it has no id but has other info.

        This allows users to create objects with partial information
        (e.g., Channel(name="general")) that can later be resolved.
        """
        if not self.id and self.is_resolvable:
            self.mark_incomplete()
        return self
