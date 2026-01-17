"""Embed model for chatom.

This module provides the Embed class for rich message embeds.
"""

from datetime import datetime
from typing import List, Optional

from .base import BaseModel, Field

__all__ = ("Embed", "EmbedField", "EmbedAuthor", "EmbedFooter", "EmbedMedia")


class EmbedMedia(BaseModel):
    """Media (image/video/thumbnail) within an embed.

    Attributes:
        url: URL of the media.
        proxy_url: Proxy URL of the media.
        width: Width in pixels.
        height: Height in pixels.
    """

    url: str = Field(
        default="",
        description="URL of the media.",
    )
    proxy_url: str = Field(
        default="",
        description="Proxy URL of the media.",
    )
    width: Optional[int] = Field(
        default=None,
        description="Width in pixels.",
    )
    height: Optional[int] = Field(
        default=None,
        description="Height in pixels.",
    )


class EmbedAuthor(BaseModel):
    """Author information for an embed.

    Attributes:
        name: Name of the author.
        url: URL for the author link.
        icon_url: URL for the author's icon.
    """

    name: str = Field(
        default="",
        description="Name of the author.",
    )
    url: str = Field(
        default="",
        description="URL for the author link.",
    )
    icon_url: str = Field(
        default="",
        description="URL for the author's icon.",
    )


class EmbedFooter(BaseModel):
    """Footer information for an embed.

    Attributes:
        text: Footer text.
        icon_url: URL for the footer icon.
    """

    text: str = Field(
        default="",
        description="Footer text.",
    )
    icon_url: str = Field(
        default="",
        description="URL for the footer icon.",
    )


class EmbedField(BaseModel):
    """A field within an embed.

    Attributes:
        name: Field name/title.
        value: Field value/content.
        inline: Whether to display inline with other fields.
    """

    name: str = Field(
        default="",
        description="Field name/title.",
    )
    value: str = Field(
        default="",
        description="Field value/content.",
    )
    inline: bool = Field(
        default=False,
        description="Whether to display inline with other fields.",
    )


class Embed(BaseModel):
    """Rich embed for messages.

    Supports images, fields, authors, footers, and more.
    Compatible with Discord embeds and similar rich content systems.

    Attributes:
        title: Title of the embed.
        description: Description text.
        url: URL the title links to.
        color: Color of the embed sidebar (as hex integer).
        timestamp: Timestamp to display.
        author: Author information.
        footer: Footer information.
        thumbnail: Thumbnail image.
        image: Main image.
        video: Video content.
        fields: List of embed fields.
    """

    title: str = Field(
        default="",
        description="Title of the embed.",
    )
    description: str = Field(
        default="",
        description="Description text.",
    )
    url: str = Field(
        default="",
        description="URL the title links to.",
    )
    color: Optional[int] = Field(
        default=None,
        description="Color of the embed sidebar (as hex integer).",
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp to display.",
    )
    author: Optional[EmbedAuthor] = Field(
        default=None,
        description="Author information.",
    )
    footer: Optional[EmbedFooter] = Field(
        default=None,
        description="Footer information.",
    )
    thumbnail: Optional[EmbedMedia] = Field(
        default=None,
        description="Thumbnail image.",
    )
    image: Optional[EmbedMedia] = Field(
        default=None,
        description="Main image.",
    )
    video: Optional[EmbedMedia] = Field(
        default=None,
        description="Video content.",
    )
    fields: List[EmbedField] = Field(
        default_factory=list,
        description="List of embed fields.",
    )

    def add_field(self, name: str, value: str, inline: bool = False) -> "Embed":
        """Add a field to the embed.

        Args:
            name: Field name.
            value: Field value.
            inline: Whether to display inline.

        Returns:
            Self for method chaining.
        """
        self.fields.append(EmbedField(name=name, value=value, inline=inline))
        return self
