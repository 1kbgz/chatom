"""Backend module for chatom.

This module provides the backend base class, configuration, and registry.
"""

from .backend import AttachmentDownloadLimitError, Backend, BackendBase, SyncHelper
from .backend_config import BackendConfig
from .backend_registry import (
    BackendRegistry,
    get_backend,
    get_backend_format,
    list_backends,
    register_backend,
)

__all__ = (
    "AttachmentDownloadLimitError",
    # Backend base class and alias
    "Backend",
    "BackendBase",
    # Configuration
    "BackendConfig",
    # Registry
    "BackendRegistry",
    "SyncHelper",
    "get_backend",
    "get_backend_format",
    "list_backends",
    "register_backend",
)
