"""Base model classes for chatom.

This module provides the foundational model classes that all chatom
data structures inherit from. It uses Pydantic for data validation
and serialization.
"""

from typing import Any, Dict, TypeVar

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field

__all__ = ("BaseModel", "Field", "Identifiable")

T = TypeVar("T", bound="BaseModel")


class BaseModel(PydanticBaseModel):
    """Base model class for all chatom data structures.

    Provides common configuration and utilities for all models.
    Inherits from Pydantic's BaseModel for validation and serialization.
    """

    model_config = ConfigDict(
        frozen=False,
        extra="allow",
        populate_by_name=True,
        validate_assignment=True,
    )

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
    """

    id: str = Field(
        default="",
        description="Platform-specific unique identifier.",
    )
    name: str = Field(
        default="",
        description="Human-readable name or display name.",
    )
