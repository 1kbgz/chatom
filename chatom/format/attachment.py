"""Attachment formatting for chatom.

This module provides attachment and media rendering for different formats.
Attachments can reference files by URL or hold in-memory binary data
for direct upload to backend APIs.
"""

from typing import Optional

from pydantic import Field

from chatom.base import BaseModel

from .variant import FORMAT, Format

__all__ = ("FormattedAttachment", "FormattedImage")


class FormattedAttachment(BaseModel):
    """An attachment that can be rendered to different formats.

    Attachments can reference a URL or hold raw bytes for upload.
    When ``data`` is set, the publish path will use the backend's
    file upload API instead of rendering a URL link.

    Attributes:
        filename: Name of the file.
        url: URL to the attachment.
        data: Raw file bytes for direct upload.
        size: File size in bytes.
        content_type: MIME type.
    """

    filename: str = Field(default="", description="Name of the file.")
    url: str = Field(default="", description="URL to the attachment.")
    data: Optional[bytes] = Field(default=None, description="Raw file bytes for direct upload.", exclude=True, repr=False)
    size: Optional[int] = Field(default=None, description="File size in bytes.")
    content_type: str = Field(default="", description="MIME type.")

    @property
    def has_data(self) -> bool:
        """Whether this attachment carries in-memory binary data."""
        return self.data is not None

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render the attachment to the specified format.

        Args:
            format: The output format.

        Returns:
            str: The rendered attachment.
        """
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return f"[{self.filename}]({self.url})"
        elif fmt == Format.SLACK_MARKDOWN:
            return f"<{self.url}|{self.filename}>"
        elif fmt in (Format.HTML, Format.SYMPHONY_MESSAGEML):
            return f'<a href="{self.url}">{self.filename}</a>'
        else:
            return f"{self.filename}: {self.url}"


class FormattedImage(BaseModel):
    """An image that can be rendered to different formats.

    Images can reference a URL or hold raw bytes for upload.
    When ``data`` is set, the publish path will use the backend's
    image/file upload API instead of rendering a URL.

    Attributes:
        url: URL to the image.
        data: Raw image bytes for direct upload.
        alt_text: Alternative text for accessibility.
        title: Image title.
        filename: Filename for the upload (derived from url if empty).
        content_type: MIME type (e.g. ``image/png``).
        width: Width in pixels.
        height: Height in pixels.
    """

    url: str = Field(default="", description="URL to the image.")
    data: Optional[bytes] = Field(default=None, description="Raw image bytes for direct upload.", exclude=True, repr=False)
    alt_text: str = Field(default="", description="Alternative text.")
    title: str = Field(default="", description="Image title.")
    filename: str = Field(default="", description="Filename for the upload.")
    content_type: str = Field(default="", description="MIME type (e.g. image/png).")
    width: Optional[int] = Field(default=None, description="Width in pixels.")
    height: Optional[int] = Field(default=None, description="Height in pixels.")

    @property
    def has_data(self) -> bool:
        """Whether this image carries in-memory binary data."""
        return self.data is not None

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render the image to the specified format.

        Args:
            format: The output format.

        Returns:
            str: The rendered image.
        """
        fmt = Format(format) if isinstance(format, str) else format
        alt = self.alt_text or "image"

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            if self.title:
                return f'![{alt}]({self.url} "{self.title}")'
            return f"![{alt}]({self.url})"
        elif fmt == Format.SLACK_MARKDOWN:
            # Slack auto-unfurls images from URLs
            return self.url
        elif fmt in (Format.HTML,):
            attrs = [f'src="{self.url}"', f'alt="{alt}"']
            if self.title:
                attrs.append(f'title="{self.title}"')
            if self.width:
                attrs.append(f'width="{self.width}"')
            if self.height:
                attrs.append(f'height="{self.height}"')
            return f"<img {' '.join(attrs)}/>"
        elif fmt == Format.SYMPHONY_MESSAGEML:
            # Symphony uses a card format for images
            return f'<card><header>{alt}</header><body><img src="{self.url}"/></body></card>'
        else:
            return f"{alt}: {self.url}"
