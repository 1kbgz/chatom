"""Attachment model for chatom.

This module provides classes for file attachments and media.
"""

from enum import Enum
from typing import Optional

from .base import BaseModel, Field

__all__ = ("Attachment", "AttachmentType", "Image", "File")


class AttachmentType(str, Enum):
    """Types of attachments."""

    FILE = "file"
    """Generic file attachment."""

    IMAGE = "image"
    """Image attachment."""

    VIDEO = "video"
    """Video attachment."""

    AUDIO = "audio"
    """Audio attachment."""

    DOCUMENT = "document"
    """Document attachment (PDF, DOC, etc.)."""

    ARCHIVE = "archive"
    """Archive file (ZIP, TAR, etc.)."""

    CODE = "code"
    """Code snippet or file."""

    UNKNOWN = "unknown"
    """Unknown attachment type."""


class Attachment(BaseModel):
    """Base class for file attachments.

    Attributes:
        id: Platform-specific unique identifier.
        filename: Name of the file.
        url: URL to download the attachment.
        content_type: MIME type of the attachment.
        size: File size in bytes.
        attachment_type: Type of attachment.
    """

    id: str = Field(
        default="",
        description="Platform-specific unique identifier.",
    )
    filename: str = Field(
        default="",
        description="Name of the file.",
    )
    url: str = Field(
        default="",
        description="URL to download the attachment.",
    )
    content_type: str = Field(
        default="",
        description="MIME type of the attachment.",
    )
    size: Optional[int] = Field(
        default=None,
        description="File size in bytes.",
    )
    attachment_type: AttachmentType = Field(
        default=AttachmentType.UNKNOWN,
        description="Type of attachment.",
    )

    @classmethod
    def from_content_type(cls, content_type: str) -> AttachmentType:
        """Determine attachment type from MIME type.

        Args:
            content_type: MIME type string.

        Returns:
            AttachmentType: The determined attachment type.
        """
        if content_type.startswith("image/"):
            return AttachmentType.IMAGE
        elif content_type.startswith("video/"):
            return AttachmentType.VIDEO
        elif content_type.startswith("audio/"):
            return AttachmentType.AUDIO
        elif content_type in (
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            return AttachmentType.DOCUMENT
        elif content_type in (
            "application/zip",
            "application/x-tar",
            "application/gzip",
        ):
            return AttachmentType.ARCHIVE
        elif content_type.startswith("text/"):
            return AttachmentType.CODE
        return AttachmentType.FILE


class Image(Attachment):
    """Image attachment with additional image-specific metadata.

    Attributes:
        width: Image width in pixels.
        height: Image height in pixels.
        alt_text: Alternative text description.
        thumbnail_url: URL to a thumbnail version.
    """

    attachment_type: AttachmentType = Field(
        default=AttachmentType.IMAGE,
        description="Type of attachment.",
    )
    width: Optional[int] = Field(
        default=None,
        description="Image width in pixels.",
    )
    height: Optional[int] = Field(
        default=None,
        description="Image height in pixels.",
    )
    alt_text: str = Field(
        default="",
        description="Alternative text description.",
    )
    thumbnail_url: str = Field(
        default="",
        description="URL to a thumbnail version.",
    )


class File(Attachment):
    """Generic file attachment.

    Attributes:
        preview: Preview text or snippet of the file content.
    """

    attachment_type: AttachmentType = Field(
        default=AttachmentType.FILE,
        description="Type of attachment.",
    )
    preview: str = Field(
        default="",
        description="Preview text or snippet of the file content.",
    )
