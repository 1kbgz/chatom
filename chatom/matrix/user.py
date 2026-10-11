"""Matrix-specific user model."""

from chatom.base import Field, User
from chatom.base.conversion import register_backend_type

__all__ = ("MatrixUser",)


class MatrixUser(User):
    """A Matrix user identified by an MXID."""

    avatar_mxc: str = Field(default="", description="Matrix content URI for the avatar.")
    membership: str = Field(default="", description="Room membership state when known.")
    power_level: int = Field(default=0, description="Room power level when known.")

    @property
    def homeserver(self) -> str:
        """Return homeserver portion of the MXID."""
        return self.id.partition(":")[2]

    @property
    def mention_name(self) -> str:
        """Return display name or MXID."""
        return self.display_name or self.name or self.id


register_backend_type("matrix", User, MatrixUser)
