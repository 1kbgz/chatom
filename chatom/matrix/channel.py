"""Matrix-specific channel model."""

from chatom.base import Channel, Field
from chatom.base.conversion import register_backend_type

__all__ = ("MatrixChannel",)


class MatrixChannel(Channel):
    """A Matrix room."""

    canonical_alias: str = Field(default="", description="Canonical room alias.")
    aliases: list[str] = Field(default_factory=list, description="Known room aliases.")
    avatar_mxc: str = Field(default="", description="Matrix content URI for the room avatar.")
    encrypted: bool = Field(default=False, description="Whether room encryption is enabled.")
    join_rule: str = Field(default="", description="Matrix room join rule.")
    room_version: str = Field(default="", description="Matrix room version.")

    @property
    def matrix_identifier(self) -> str:
        """Prefer canonical alias for display and room ID for API calls."""
        return self.canonical_alias or self.id


register_backend_type("matrix", Channel, MatrixChannel)
