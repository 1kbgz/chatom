from pydantic import BaseModel as PydanticBaseModel, Field

__all__ = ("BaseModel", "Field")


class BaseModel(PydanticBaseModel):
    # In case customization needed
    ...
