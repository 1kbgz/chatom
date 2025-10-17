from pydantic import BaseModel, Field

from .enums import BACKEND


class BackendConfig(BaseModel): ...


class Backend(BaseModel):
    backend: BACKEND
    config: BackendConfig = Field(default_factory=BackendConfig)

    def connect(self): ...
