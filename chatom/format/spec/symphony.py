"""Symphony MessageML specification reference.

This module encodes the authoritative nesting/content-model rules from
the finos/messageml-utils Java validator (v2.0). It is used by the test
suite to validate that convert_format() output conforms to what the
Symphony API will actually accept.

Source: https://github.com/finos/messageml-utils
Package: org.finos.symphony.messageml.messagemlutils.elements

Key rules come from Element.java's PHRASING_TYPES list and each
element's validate() method calling assertPhrasingContent() or
assertPreformattedOrPhrasingContent().
"""

from __future__ import annotations

import re

# Phrasing content (inline elements allowed inside <b>, <i>, <h1>-<h6>, <pre>)
# Corresponds to Element.java PHRASING_TYPES:
#   TextNode, Link, Chime, Bold, Italic, Image, LineBreak, Span,
#   Emoji, HashTag, CashTag, Mention, Subscript, Superscript
PHRASING_TAGS: frozenset[str] = frozenset(
    {
        "a",  # Link
        "b",  # Bold
        "i",  # Italic
        "img",  # Image (self-closing)
        "br",  # LineBreak (self-closing)
        "span",  # Span
        "sub",  # Subscript
        "sup",  # Superscript
        # Special Symphony elements (not relevant to markdown conversion):
        # "chime", "emoji", "hash", "cash", "mention"
    }
)

# Elements that call assertPhrasingContent() — only allow PHRASING_TAGS children
PHRASING_CONTENT_PARENTS: frozenset[str] = frozenset(
    {
        "b",  # Bold.validate()
        "i",  # Italic.validate()
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",  # Header.validate()
        "pre",  # Preformatted.validate()
    }
)

# Elements that call assertPreformattedOrPhrasingContent()
# Allows PHRASING_TAGS + "pre" as children
PREFORMATTED_OR_PHRASING_PARENTS: frozenset[str] = frozenset(
    {
        "code",  # Code.validate()
    }
)

# Tags that are NOT phrasing (forbidden inside bold/italic/headings/pre)
NON_PHRASING_TAGS: frozenset[str] = frozenset(
    {
        "code",  # Code
        "pre",  # Preformatted
        "p",  # Paragraph
        "div",  # Div
        "table",  # Table
        "thead",  # TableHeader
        "tbody",  # TableBody
        "tfoot",  # TableFooter
        "tr",  # TableRow
        "td",  # TableCell
        "th",  # TableHeaderCell
        "ul",  # BulletList
        "ol",  # OrderedList
        "li",  # ListItem
        "hr",  # HorizontalRule (self-closing)
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",  # Headers
    }
)

# Tags that are NOT valid MessageML elements at all (will cause parse error)
INVALID_MESSAGEML_TAGS: frozenset[str] = frozenset(
    {
        "blockquote",  # Not in MessageMLParser.createElement() switch
        "s",  # Not in MessageMLParser.createElement() switch
        "u",  # Not in MessageMLParser.createElement() switch
    }
)

# Elements with no child content restriction (accept any child)
# These elements either don't override validate() or only check parent/attrs
FLOW_CONTENT_PARENTS: frozenset[str] = frozenset(
    {
        "td",  # TableCell — no content model assertion
        "th",  # TableHeaderCell — no content model assertion
        "li",  # ListItem — only assertParent(ul/ol)
        "p",  # Paragraph — no content model assertion
        "div",  # Root PresentationML wrapper
        "messageML",  # Root element
    }
)

# Table structure rules
TABLE_CHILDREN: frozenset[str] = frozenset({"thead", "tbody", "tfoot"})
TABLE_ROW_PARENTS: frozenset[str] = frozenset({"thead", "tbody", "tfoot"})
TABLE_CELL_PARENTS: frozenset[str] = frozenset({"tr"})

# Standard XML escaping required in MessageML
XML_ESCAPE_MAP = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
}

# Symphony template syntax that must be escaped
TEMPLATE_ESCAPE_MAP = {
    "${": "&#36;{",
    "#{": "&#35;{",
}

# Regex to find opening tags in MessageML
_TAG_RE = re.compile(r"<(/?)(\w+)([^>]*)(/?)>")


def _get_child_tags(html: str, parent_tag: str) -> list[tuple[str, str]]:
    """Find direct child element tags inside a parent tag.

    Returns list of (tag_name, 'open'|'close'|'self-closing') tuples.
    This is a simplified parser for validation purposes only.
    """
    children = []
    depth = 0
    inside_parent = False
    parent_depth = 0

    for m in _TAG_RE.finditer(html):
        is_close = bool(m.group(1))
        tag = m.group(2)
        is_self_closing = bool(m.group(4)) or tag in ("br", "img", "hr")

        if not inside_parent:
            if not is_close and tag == parent_tag:
                inside_parent = True
                parent_depth = depth
                depth += 1
                continue
        else:
            if is_self_closing:
                if depth == parent_depth + 1:
                    children.append((tag, "self-closing"))
            elif is_close:
                depth -= 1
                if depth == parent_depth:
                    inside_parent = False
                elif depth == parent_depth + 1:
                    children.append((tag, "close"))
            else:
                if depth == parent_depth + 1:
                    children.append((tag, "open"))
                depth += 1

    return children


def validate_messageml(html: str) -> list[str]:
    """Validate MessageML content against Symphony nesting rules.

    Returns a list of violation messages. Empty list means valid.

    This implements the core validation logic from the Java validator:
    - Elements with assertPhrasingContent() only allow PHRASING_TAGS children
    - Elements with assertPreformattedOrPhrasingContent() allow PHRASING_TAGS + "pre"

    Args:
        html: MessageML content (without the outer <messageML> wrapper).

    Returns:
        List of violation descriptions. Empty = valid.
    """
    violations = []
    _validate_recursive(html, violations)
    return violations


def _validate_recursive(html: str, violations: list[str]) -> None:
    """Recursively validate nesting rules."""
    stack: list[str] = []

    for m in _TAG_RE.finditer(html):
        is_close = bool(m.group(1))
        tag = m.group(2)
        is_self_closing = bool(m.group(4)) or tag in ("br", "img", "hr")

        if is_self_closing:
            if stack:
                parent = stack[-1]
                _check_allowed(parent, tag, violations)
            if tag in INVALID_MESSAGEML_TAGS:
                violations.append(f'Element "{tag}" is not a valid MessageML element')
        elif is_close:
            if stack and stack[-1] == tag:
                stack.pop()
        else:
            if tag in INVALID_MESSAGEML_TAGS:
                violations.append(f'Element "{tag}" is not a valid MessageML element')
            if stack:
                parent = stack[-1]
                _check_allowed(parent, tag, violations)
            stack.append(tag)


def _check_allowed(parent: str, child: str, violations: list[str]) -> None:
    """Check if child tag is allowed inside parent tag."""
    if parent in PHRASING_CONTENT_PARENTS:
        if child not in PHRASING_TAGS and child != parent:
            violations.append(f'Element "{child}" is not allowed in "{parent}"')
    elif parent in PREFORMATTED_OR_PHRASING_PARENTS and child not in PHRASING_TAGS and child != "pre":
        violations.append(f'Element "{child}" is not allowed in "{parent}"')
