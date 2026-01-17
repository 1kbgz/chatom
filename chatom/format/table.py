"""Table formatting for chatom.

This module provides table representation that can be rendered
to different output formats.
"""

from typing import Any, List, Optional

from pydantic import Field

from chatom.base import BaseModel

from .variant import FORMAT, Format

__all__ = ("Table", "TableRow", "TableCell", "TableAlignment")


class TableAlignment:
    """Table column alignment constants."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class TableCell(BaseModel):
    """A single cell in a table.

    Attributes:
        content: The cell content.
        is_header: Whether this is a header cell.
        colspan: Number of columns this cell spans.
        rowspan: Number of rows this cell spans.
        alignment: Text alignment within the cell.
    """

    content: str = Field(default="", description="The cell content.")
    is_header: bool = Field(default=False, description="Whether this is a header cell.")
    colspan: int = Field(default=1, ge=1, description="Number of columns to span.")
    rowspan: int = Field(default=1, ge=1, description="Number of rows to span.")
    alignment: str = Field(default=TableAlignment.LEFT, description="Text alignment.")


class TableRow(BaseModel):
    """A row in a table.

    Attributes:
        cells: The cells in this row.
        is_header: Whether this is a header row.
    """

    cells: List[TableCell] = Field(default_factory=list, description="Cells in the row.")
    is_header: bool = Field(default=False, description="Whether this is a header row.")

    @classmethod
    def from_values(cls, values: List[str], is_header: bool = False) -> "TableRow":
        """Create a row from a list of string values.

        Args:
            values: Cell values as strings.
            is_header: Whether this is a header row.

        Returns:
            TableRow: The created row.
        """
        cells = [TableCell(content=str(v), is_header=is_header) for v in values]
        return cls(cells=cells, is_header=is_header)


class Table(BaseModel):
    """A table that can be rendered to different formats.

    Supports Markdown, HTML, Symphony MessageML, and plaintext output.

    Attributes:
        headers: Optional header row.
        rows: Data rows.
        caption: Optional table caption.
        alignments: Column alignments.
    """

    headers: Optional[TableRow] = Field(default=None, description="Header row.")
    rows: List[TableRow] = Field(default_factory=list, description="Data rows.")
    caption: str = Field(default="", description="Table caption.")
    alignments: List[str] = Field(default_factory=list, description="Column alignments.")

    @classmethod
    def from_data(
        cls,
        data: List[List[Any]],
        headers: Optional[List[str]] = None,
        caption: str = "",
        alignments: Optional[List[str]] = None,
    ) -> "Table":
        """Create a table from a 2D list of data.

        Args:
            data: 2D list of cell values.
            headers: Optional list of header values.
            caption: Optional table caption.
            alignments: Optional list of column alignments.

        Returns:
            Table: The created table.
        """
        header_row = None
        if headers:
            header_row = TableRow.from_values(headers, is_header=True)

        rows = [TableRow.from_values([str(cell) for cell in row]) for row in data]

        return cls(
            headers=header_row,
            rows=rows,
            caption=caption,
            alignments=alignments or [],
        )

    @classmethod
    def from_dict_list(
        cls,
        data: List[dict],
        columns: Optional[List[str]] = None,
        caption: str = "",
    ) -> "Table":
        """Create a table from a list of dictionaries.

        Args:
            data: List of dictionaries, each representing a row.
            columns: Optional list of column keys to include. Defaults to all keys.
            caption: Optional table caption.

        Returns:
            Table: The created table.
        """
        if not data:
            return cls(caption=caption)

        # Get columns from first dict if not specified
        if columns is None:
            columns = list(data[0].keys())

        headers = TableRow.from_values(columns, is_header=True)
        rows = [TableRow.from_values([str(row.get(col, "")) for col in columns]) for row in data]

        return cls(headers=headers, rows=rows, caption=caption)

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        """Render the table to the specified format.

        Args:
            format: The output format.

        Returns:
            str: The rendered table.
        """
        fmt = Format(format) if isinstance(format, str) else format

        if fmt in (Format.MARKDOWN, Format.DISCORD_MARKDOWN):
            return self._render_markdown()
        elif fmt == Format.SLACK_MARKDOWN:
            return self._render_slack()
        elif fmt in (Format.HTML,):
            return self._render_html()
        elif fmt == Format.SYMPHONY_MESSAGEML:
            return self._render_symphony()
        else:
            return self._render_plaintext()

    def _get_column_widths(self) -> List[int]:
        """Calculate the width of each column."""
        all_rows = []
        if self.headers:
            all_rows.append(self.headers)
        all_rows.extend(self.rows)

        if not all_rows:
            return []

        max_cols = max(len(row.cells) for row in all_rows)
        widths = [0] * max_cols

        for row in all_rows:
            for i, cell in enumerate(row.cells):
                widths[i] = max(widths[i], len(cell.content))

        return widths

    def _render_markdown(self) -> str:
        """Render as Markdown table."""
        if not self.rows and not self.headers:
            return ""

        lines = []
        widths = self._get_column_widths()

        # Header row
        if self.headers:
            cells = [cell.content.ljust(widths[i]) if i < len(widths) else cell.content for i, cell in enumerate(self.headers.cells)]
            lines.append("| " + " | ".join(cells) + " |")

            # Separator
            separators = []
            for i, width in enumerate(widths):
                align = self.alignments[i] if i < len(self.alignments) else TableAlignment.LEFT
                if align == TableAlignment.CENTER:
                    separators.append(":" + "-" * max(width, 1) + ":")
                elif align == TableAlignment.RIGHT:
                    separators.append("-" * max(width, 1) + ":")
                else:
                    separators.append("-" * max(width + 2, 3))
            lines.append("|" + "|".join(separators) + "|")

        # Data rows
        for row in self.rows:
            cells = [cell.content.ljust(widths[i]) if i < len(widths) else cell.content for i, cell in enumerate(row.cells)]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    def _render_slack(self) -> str:
        """Render as Slack-friendly text table.

        Slack doesn't support Markdown tables, so we use a code block.
        """
        if not self.rows and not self.headers:
            return ""

        widths = self._get_column_widths()
        lines = []

        # Header
        if self.headers:
            cells = [cell.content.ljust(widths[i]) if i < len(widths) else cell.content for i, cell in enumerate(self.headers.cells)]
            lines.append(" | ".join(cells))
            lines.append("-+-".join("-" * w for w in widths))

        # Data
        for row in self.rows:
            cells = [cell.content.ljust(widths[i]) if i < len(widths) else cell.content for i, cell in enumerate(row.cells)]
            lines.append(" | ".join(cells))

        return "```\n" + "\n".join(lines) + "\n```"

    def _render_html(self) -> str:
        """Render as HTML table."""
        parts = ["<table>"]

        if self.caption:
            parts.append(f"<caption>{self.caption}</caption>")

        if self.headers:
            parts.append("<thead><tr>")
            for cell in self.headers.cells:
                parts.append(f"<th>{cell.content}</th>")
            parts.append("</tr></thead>")

        if self.rows:
            parts.append("<tbody>")
            for row in self.rows:
                parts.append("<tr>")
                for cell in row.cells:
                    tag = "th" if cell.is_header else "td"
                    parts.append(f"<{tag}>{cell.content}</{tag}>")
                parts.append("</tr>")
            parts.append("</tbody>")

        parts.append("</table>")
        return "".join(parts)

    def _render_symphony(self) -> str:
        """Render as Symphony MessageML table."""
        parts = ["<table>"]

        if self.headers:
            parts.append("<thead><tr>")
            for cell in self.headers.cells:
                content = self._escape_symphony(cell.content)
                parts.append(f"<th>{content}</th>")
            parts.append("</tr></thead>")

        if self.rows:
            parts.append("<tbody>")
            for row in self.rows:
                parts.append("<tr>")
                for cell in row.cells:
                    content = self._escape_symphony(cell.content)
                    parts.append(f"<td>{content}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")

        parts.append("</table>")
        return "".join(parts)

    def _escape_symphony(self, text: str) -> str:
        """Escape text for Symphony MessageML."""
        return text.replace("&", "&#38;").replace("<", "&lt;").replace("${", "&#36;{").replace("#{", "&#35;{")

    def _render_plaintext(self) -> str:
        """Render as plain text table."""
        if not self.rows and not self.headers:
            return ""

        widths = self._get_column_widths()
        lines = []

        def format_row(cells: List[TableCell]) -> str:
            parts = []
            for i, cell in enumerate(cells):
                width = widths[i] if i < len(widths) else len(cell.content)
                parts.append(cell.content.ljust(width))
            return " | ".join(parts)

        # Header
        if self.headers:
            lines.append(format_row(self.headers.cells))
            lines.append("-+-".join("-" * w for w in widths))

        # Data
        for row in self.rows:
            lines.append(format_row(row.cells))

        return "\n".join(lines)
