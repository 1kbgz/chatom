"""Markdown parser for chatom format system.

Uses mistune (a proper markdown parser) to produce an AST, then converts
to chatom TextNode trees for multi-format rendering.
"""

import re

import mistune
from pydantic import Field

from .table import Table, TableRow
from .text import (
    Bold,
    Code,
    CodeBlock,
    Document,
    Heading,
    HorizontalRule,
    Italic,
    LineBreak,
    Link,
    ListItem,
    OrderedList,
    Paragraph,
    Quote,
    Span,
    Strikethrough,
    Text,
    TextNode,
    UnorderedList,
)
from .variant import FORMAT, Format

__all__ = ("convert_format", "parse_markdown")

# Singleton mistune parser with table + strikethrough support
_md = mistune.create_markdown(renderer="ast", plugins=["table", "strikethrough"])


class _TableNode(TextNode):
    """Adapter wrapping a Table as a TextNode for Document inclusion."""

    table: Table = Field(description="The wrapped table.")

    def render(self, format: FORMAT = Format.MARKDOWN) -> str:
        return self.table.render(format)


def _convert_inline(nodes: list) -> TextNode:
    """Convert a list of mistune inline AST nodes to a single TextNode."""
    result: list[TextNode] = []
    for node in nodes:
        result.append(_convert_node(node))
    if len(result) == 1:
        return result[0]
    return Span(children=result)


def _convert_node(node: dict) -> TextNode:
    """Convert a single mistune AST node to a TextNode."""
    t = node["type"]

    if t == "text":
        return Text(content=node.get("raw", ""))

    if t == "softbreak":
        return Text(content="\n")

    if t == "linebreak":
        return LineBreak()

    if t == "strong":
        return Bold(child=_convert_inline(node["children"]))

    if t == "emphasis":
        return Italic(child=_convert_inline(node["children"]))

    if t == "strikethrough":
        return Strikethrough(child=_convert_inline(node["children"]))

    if t == "codespan":
        return Code(content=node.get("raw", ""))

    if t == "link":
        children = node.get("children", [])
        link_text = "".join(c.get("raw", "") for c in children) if children else ""
        url = node.get("attrs", {}).get("url", "")
        return Link(text=link_text, url=url)

    if t == "image":
        # Render as a link fallback
        alt = node.get("children", [{}])
        alt_text = alt[0].get("raw", "image") if alt else "image"
        url = node.get("attrs", {}).get("url", "")
        return Link(text=alt_text, url=url)

    # Fallback: render raw content as text
    return Text(content=node.get("raw", ""))


def _convert_block(node: dict) -> TextNode:
    """Convert a block-level mistune AST node to a TextNode."""
    t = node["type"]

    if t == "paragraph":
        return Paragraph(children=[_convert_inline(node["children"])])

    if t == "heading":
        level = node.get("attrs", {}).get("level", 1)
        return Heading(child=_convert_inline(node["children"]), level=level)

    if t == "block_code":
        language = node.get("attrs", {}).get("info", "") or ""
        raw = node.get("raw", "")
        # mistune includes trailing newline in raw; strip it
        raw = raw.removesuffix("\n")
        return CodeBlock(content=raw, language=language)

    if t == "block_quote":
        inner = [_convert_block(child) for child in node.get("children", [])]
        if len(inner) == 1:
            return Quote(child=inner[0])
        return Quote(child=Span(children=inner))

    if t == "thematic_break":
        return HorizontalRule()

    if t == "blank_line":
        return LineBreak()

    if t == "list":
        ordered = node.get("attrs", {}).get("ordered", False)
        items: list[ListItem] = []
        for child in node.get("children", []):
            if child["type"] == "list_item":
                item_children = child.get("children", [])
                if item_children:
                    # list_item contains block_text or paragraphs
                    inner_nodes = []
                    for ic in item_children:
                        if ic["type"] == "block_text" or ic["type"] == "paragraph":
                            inner_nodes.append(_convert_inline(ic["children"]))
                        else:
                            inner_nodes.append(_convert_block(ic))
                    content = inner_nodes[0] if len(inner_nodes) == 1 else Span(children=inner_nodes)
                else:
                    content = Text(content="")
                items.append(ListItem(child=content))
        if ordered:
            return OrderedList(items=items)
        return UnorderedList(items=items)

    if t == "table":
        headers_node = None
        rows: list[TableRow] = []
        for child in node.get("children", []):
            if child["type"] == "table_head":
                cells = [_render_inline_text(cell.get("children", [])) for cell in child.get("children", [])]
                headers_node = TableRow.from_values(cells, is_header=True)
            elif child["type"] == "table_body":
                for row in child.get("children", []):
                    cells = [_render_inline_text(cell.get("children", [])) for cell in row.get("children", [])]
                    rows.append(TableRow.from_values(cells))
        return _TableNode(table=Table(headers=headers_node, rows=rows))

    # Fallback
    return Text(content=node.get("raw", ""))


def _render_inline_text(nodes: list) -> str:
    """Render inline AST nodes to plain text (for table cells)."""
    parts = []
    for node in nodes:
        if node["type"] == "text" or node["type"] == "codespan":
            parts.append(node.get("raw", ""))
        elif node["type"] == "strong" or node["type"] == "emphasis":
            parts.append(_render_inline_text(node.get("children", [])))
        elif node["type"] == "link":
            children = node.get("children", [])
            parts.append(_render_inline_text(children))
        else:
            parts.append(node.get("raw", ""))
    return "".join(parts)


def parse_markdown(text: str) -> Document:
    """Parse a markdown string into a Document of TextNode objects.

    Uses mistune to parse the markdown into an AST, then converts to
    chatom's TextNode tree for multi-format rendering.

    Args:
        text: Markdown-formatted string.

    Returns:
        Document containing the parsed TextNode tree.
    """
    ast = _md(text)
    nodes = [_convert_block(node) for node in ast if isinstance(node, dict)]
    return Document(children=nodes)


def _fix_symphony_nesting(html: str) -> str:
    """Fix Symphony MessageML nesting violations.

    Symphony forbids <code> inside <b>, <i>, and <h1>-<h6> tags.
    Post-processes rendered output to strip <code> wrappers when nested.
    """

    def _strip_nested_code(m: re.Match) -> str:
        tag = m.group(1)
        inner = m.group(2)
        cleaned = re.sub(r"<code>(.*?)</code>", r"\1", inner)
        return f"<{tag}>{cleaned}</{tag}>"

    html = re.sub(r"<(b)>((?:(?!</b>).)*?<code>.*?</code>(?:(?!</b>).)*?)</b>", _strip_nested_code, html)
    html = re.sub(r"<(i)>((?:(?!</i>).)*?<code>.*?</code>(?:(?!</i>).)*?)</i>", _strip_nested_code, html)
    # Headings: <h1> through <h6>
    for level in range(1, 7):
        tag = f"h{level}"
        html = re.sub(
            rf"<({tag})>((?:(?!</{tag}>).)*?<code>.*?</code>(?:(?!</{tag}>).)*?)</{tag}>",
            _strip_nested_code,
            html,
        )
    return html


def convert_format(text: str, from_format: FORMAT, to_format: FORMAT) -> str:
    """Convert text from one format to another.

    Currently supports converting FROM markdown to any target format.

    Args:
        text: The source text.
        from_format: The format of the input text.
        to_format: The desired output format.

    Returns:
        str: The converted text.

    Raises:
        ValueError: If conversion from the specified format is not supported.
    """
    from_fmt = Format(from_format) if isinstance(from_format, str) else from_format
    to_fmt = Format(to_format) if isinstance(to_format, str) else to_format

    if from_fmt == to_fmt:
        return text

    if from_fmt != Format.MARKDOWN:
        raise ValueError(f"Conversion from {from_fmt.value} is not supported; only MARKDOWN is supported as source format.")

    doc = parse_markdown(text)
    rendered = doc.render(to_fmt)

    # Apply format-specific post-processing
    if to_fmt == Format.SYMPHONY_MESSAGEML:
        rendered = _fix_symphony_nesting(rendered)

    return rendered
