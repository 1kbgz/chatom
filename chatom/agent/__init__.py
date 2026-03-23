try:
    from pydantic_ai.toolsets.abstract import AbstractToolset  # noqa: F401
except ImportError as e:
    raise ImportError("chatom.agent requires the 'agent' extra. Install it with: pip install chatom[agent]") from e

from chatom.agent.context import ChannelContext, build_channel_context
from chatom.agent.toolset import BackendToolset

__all__ = (
    "BackendToolset",
    "ChannelContext",
    "build_channel_context",
)
