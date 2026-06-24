"""Comprehensive Symphony MessageML compliance tests.

Tests that convert_format() output conforms to the Symphony MessageML
nesting rules as defined in finos/messageml-utils.

These tests validate the actual output that would be sent to the
Symphony API, catching violations BEFORE they hit production.

Key rules tested:
- <code> is NOT allowed inside <b>, <i>, <h1>-<h6>, <pre>
- <pre> is NOT allowed inside <b>, <i>, <h1>-<h6>, <pre>
- <b>, <i> only allow phrasing content (text, a, b, i, img, br, span, sub, sup)
- <h1>-<h6> only allow phrasing content
- <code> allows phrasing content + <pre>
- <td>, <th>, <li> accept any content (no restriction)

Source: https://github.com/finos/messageml-utils
"""

import pytest

from chatom.format import Format, convert_format
from chatom.format.spec.symphony import (
    validate_messageml,
)


def md_to_symphony(md: str) -> str:
    """Convert markdown to Symphony MessageML via convert_format."""
    return convert_format(md, Format.MARKDOWN, Format.SYMPHONY_MESSAGEML)


def assert_valid_messageml(html: str, context: str = "") -> None:
    """Assert that the given MessageML passes validation."""
    violations = validate_messageml(html)
    assert violations == [], f"MessageML violations{' (' + context + ')' if context else ''}:\n" + "\n".join(f"  - {v}" for v in violations)


class TestCodeNesting:
    """Test that <code> is never inside <b>, <i>, or <h1>-<h6>."""

    def test_code_inside_bold(self):
        """**`code`** → code must not be wrapped in <code> inside <b>."""
        result = md_to_symphony("**`hello`**")
        assert "<code>" not in result or "<b>" not in result or "<code>" not in _extract_between(result, "<b>", "</b>")
        assert_valid_messageml(result, "bold with inline code")

    def test_code_inside_italic(self):
        """*`code`* → code must not be wrapped in <code> inside <i>."""
        result = md_to_symphony("*`hello`*")
        assert_valid_messageml(result, "italic with inline code")

    def test_code_inside_heading_h1(self):
        """# `code` → code must not be in <code> inside <h1>."""
        result = md_to_symphony("# `hello`")
        assert_valid_messageml(result, "h1 with inline code")

    def test_code_inside_heading_h2(self):
        result = md_to_symphony("## `hello`")
        assert_valid_messageml(result, "h2 with inline code")

    def test_code_inside_heading_h3(self):
        result = md_to_symphony("### `hello`")
        assert_valid_messageml(result, "h3 with inline code")

    def test_code_inside_heading_h4(self):
        result = md_to_symphony("#### `hello`")
        assert_valid_messageml(result, "h4 with inline code")

    def test_code_inside_heading_h5(self):
        result = md_to_symphony("##### `hello`")
        assert_valid_messageml(result, "h5 with inline code")

    def test_code_inside_heading_h6(self):
        result = md_to_symphony("###### `hello`")
        assert_valid_messageml(result, "h6 with inline code")

    def test_code_inside_bold_italic(self):
        """***`code`*** → nested bold+italic with code."""
        result = md_to_symphony("***`hello`***")
        assert_valid_messageml(result, "bold+italic with inline code")

    def test_multiple_codes_in_bold(self):
        """**`a` and `b`** → multiple code spans in bold."""
        result = md_to_symphony("**`a` and `b`**")
        assert_valid_messageml(result, "multiple code spans in bold")

    def test_code_mixed_with_text_in_heading(self):
        """## Hello `world` today → code mixed with text in heading."""
        result = md_to_symphony("## Hello `world` today")
        assert_valid_messageml(result, "heading with code and text")

    def test_code_preserved_standalone(self):
        """Standalone `code` should still render as <code>."""
        result = md_to_symphony("Use `pip install` to install.")
        assert "<code>" in result
        assert_valid_messageml(result, "standalone code")

    def test_code_in_paragraph(self):
        """Code in a paragraph is fine — <p> has no restriction."""
        result = md_to_symphony("Run `python main.py` to start.")
        assert "<code>" in result
        assert_valid_messageml(result, "code in paragraph")

    def test_code_inside_bold_heading(self):
        """### **`code`** → bold inside heading with code."""
        result = md_to_symphony("### **`code`**")
        assert_valid_messageml(result, "bold inside heading with code")


class TestPhrasingNesting:
    """Test that phrasing elements can nest inside each other."""

    def test_bold_inside_italic(self):
        """*text **bold** text* → <b> inside <i> is allowed."""
        result = md_to_symphony("*text **bold** text*")
        assert_valid_messageml(result, "bold inside italic")

    def test_italic_inside_bold(self):
        """**text *italic* text** → <i> inside <b> is allowed."""
        result = md_to_symphony("**text *italic* text**")
        assert_valid_messageml(result, "italic inside bold")

    def test_bold_italic_combined(self):
        """***bold italic*** → nested <b><i> or <i><b>."""
        result = md_to_symphony("***bold italic***")
        assert_valid_messageml(result, "combined bold italic")

    def test_link_inside_bold(self):
        """**[text](url)** → <a> inside <b> is allowed."""
        result = md_to_symphony("**[click here](https://example.com)**")
        assert "<a " in result
        assert_valid_messageml(result, "link inside bold")

    def test_link_inside_italic(self):
        """*[text](url)* → <a> inside <i> is allowed."""
        result = md_to_symphony("*[click here](https://example.com)*")
        assert_valid_messageml(result, "link inside italic")

    def test_link_inside_heading(self):
        """## [text](url) → <a> inside <h2> is allowed."""
        result = md_to_symphony("## [Click](https://example.com)")
        assert_valid_messageml(result, "link inside heading")

    def test_bold_inside_heading(self):
        """## **Important** → <b> inside <h2> is allowed."""
        result = md_to_symphony("## **Important**")
        assert "<b>" in result
        assert_valid_messageml(result, "bold inside heading")

    def test_italic_inside_heading(self):
        """## *Emphasis* → <i> inside <h2> is allowed."""
        result = md_to_symphony("## *Emphasis*")
        assert "<i>" in result
        assert_valid_messageml(result, "italic inside heading")


class TestBlockElements:
    """Test block-level elements render valid MessageML."""

    def test_simple_paragraph(self):
        result = md_to_symphony("Hello world")
        assert_valid_messageml(result, "simple paragraph")

    def test_multiple_paragraphs(self):
        result = md_to_symphony("First paragraph.\n\nSecond paragraph.")
        assert_valid_messageml(result, "multiple paragraphs")

    def test_heading_levels(self):
        """All heading levels produce valid MessageML."""
        for level in range(1, 7):
            md = f"{'#' * level} Heading {level}"
            result = md_to_symphony(md)
            assert f"<h{level}>" in result
            assert_valid_messageml(result, f"h{level}")

    def test_blockquote(self):
        result = md_to_symphony("> This is a quote")
        # Symphony doesn't support <blockquote>; rendered with visual prefix
        assert "<blockquote>" not in result
        assert "\u258e" in result
        assert_valid_messageml(result, "blockquote")

    def test_nested_blockquote(self):
        result = md_to_symphony("> Line 1\n> Line 2")
        assert_valid_messageml(result, "multi-line blockquote")

    def test_horizontal_rule(self):
        result = md_to_symphony("---")
        assert "<hr/>" in result
        assert_valid_messageml(result, "horizontal rule")

    def test_code_block(self):
        """Code blocks render as <pre> without inner <code>."""
        result = md_to_symphony("```python\nprint('hello')\n```")
        assert "<pre>" in result
        # Symphony MessageML: <pre> without <code> inside
        assert "<code>" not in result
        assert_valid_messageml(result, "code block")

    def test_code_block_plain(self):
        """Code block without language."""
        result = md_to_symphony("```\nsome code\n```")
        assert "<pre>" in result
        assert_valid_messageml(result, "plain code block")


class TestLists:
    """Test list rendering produces valid MessageML."""

    def test_unordered_list(self):
        md = "- Item 1\n- Item 2\n- Item 3"
        result = md_to_symphony(md)
        assert "<ul>" in result
        assert "<li>" in result
        assert_valid_messageml(result, "unordered list")

    def test_ordered_list(self):
        md = "1. First\n2. Second\n3. Third"
        result = md_to_symphony(md)
        assert "<ol>" in result
        assert "<li>" in result
        assert_valid_messageml(result, "ordered list")

    def test_list_with_code(self):
        """Code inside list items is allowed (<li> has no restriction)."""
        md = "- Use `pip install`\n- Run `python main.py`"
        result = md_to_symphony(md)
        assert "<code>" in result
        assert_valid_messageml(result, "list with code")

    def test_list_with_bold(self):
        md = "- **Important** item\n- Normal item"
        result = md_to_symphony(md)
        assert "<b>" in result
        assert_valid_messageml(result, "list with bold")

    def test_list_with_links(self):
        md = "- [Link](https://example.com)\n- Other"
        result = md_to_symphony(md)
        assert "<a " in result
        assert_valid_messageml(result, "list with links")


class TestTables:
    """Test table rendering produces valid MessageML."""

    def test_simple_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = md_to_symphony(md)
        assert "<table>" in result
        assert_valid_messageml(result, "simple table")

    def test_table_with_code_in_cells(self):
        """Table cells can contain code — <td> has no restriction."""
        md = "| Command | Description |\n|---|---|\n| `ls` | List files |"
        result = md_to_symphony(md)
        assert "<table>" in result
        assert_valid_messageml(result, "table with code cells")

    def test_table_with_header(self):
        md = "| Header 1 | Header 2 |\n|---|---|\n| Cell 1 | Cell 2 |"
        result = md_to_symphony(md)
        assert "<th>" in result or "<td>" in result
        assert_valid_messageml(result, "table with header")


class TestEscaping:
    """Test proper character escaping in MessageML output."""

    def test_ampersand_escaped(self):
        result = md_to_symphony("A & B")
        assert "&amp;" in result
        assert "& " not in result or "&amp;" in result

    def test_less_than_escaped(self):
        result = md_to_symphony("a < b")
        assert "&lt;" in result

    def test_greater_than_escaped(self):
        result = md_to_symphony("a > b")
        # Note: > in markdown starts a blockquote, so test with inline
        result = md_to_symphony("Use `a > b` for comparison")
        assert "&gt;" in result

    def test_html_in_code(self):
        """HTML chars inside code should be escaped."""
        result = md_to_symphony("`<div>hello</div>`")
        assert "&lt;" in result
        assert "&gt;" in result

    def test_html_in_code_block(self):
        """HTML chars inside code blocks should be escaped."""
        result = md_to_symphony("```\n<script>alert('xss')</script>\n```")
        assert "&lt;" in result
        assert "&gt;" in result
        assert "<script>" not in result


class TestRealWorldScenarios:
    """Test complex markdown patterns that agents typically produce."""

    def test_agent_response_with_code_heading(self):
        """Agent output: heading with code (caused production error)."""
        md = "### Using `pip install`\n\nRun this command to install."
        result = md_to_symphony(md)
        assert_valid_messageml(result, "agent heading with code")

    def test_agent_response_bold_code(self):
        """Agent output: bold text with code reference."""
        md = "**Command:** `pip install chatom`"
        result = md_to_symphony(md)
        assert_valid_messageml(result, "agent bold with code")

    def test_agent_response_mixed_formatting(self):
        """Complex agent response with mixed formatting."""
        md = """## Summary

Here's what I found:

- **Package**: `chatom`
- **Version**: `1.0.0`
- **Status**: *active*

### Installation

```bash
pip install chatom
```

Use `chatom --help` for more info."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, "complex agent response")

    def test_agent_response_all_heading_levels_with_code(self):
        """Agent uses various heading levels with code spans."""
        md = """# Main `title`

## Section `two`

### Sub `three`

#### Deep `four`

##### Level `five`

###### Level `six`"""
        result = md_to_symphony(md)
        assert_valid_messageml(result, "all heading levels with code")

    def test_agent_response_nested_bold_italic_code(self):
        """***`code`*** → deeply nested formatting."""
        md = "***`important code`***"
        result = md_to_symphony(md)
        assert_valid_messageml(result, "deeply nested bold/italic/code")

    def test_agent_response_list_with_bold_code(self):
        """- **`command`**: description — bold wrapping code in list."""
        md = "- **`pip install`**: Install the package\n- **`pip uninstall`**: Remove it"
        result = md_to_symphony(md)
        assert_valid_messageml(result, "list with bold-wrapped code")

    def test_agent_error_output(self):
        """Agent error with backtrace-like output."""
        md = """### Error: `FileNotFoundError`

The file `config.yaml` was not found at path `/etc/app/config.yaml`.

**Fix:** Create the file or set `CONFIG_PATH` environment variable."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, "agent error output")

    def test_api_response_with_json(self):
        """Agent shows API response with code block."""
        md = """### Response from `/api/v1/status`

```json
{"status": "ok", "version": "1.2.3"}
```

The **`status`** field indicates health."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, "API response display")

    def test_mixed_links_and_bold(self):
        """Links inside bold and headings."""
        md = """## [Documentation](https://docs.example.com)

See **[the guide](https://guide.example.com)** for details."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, "links in bold and heading")

    def test_empty_code_span(self):
        """Edge case: empty code span."""
        result = md_to_symphony("Use `` for empty.")
        assert_valid_messageml(result, "empty code span")

    def test_code_with_special_chars(self):
        """Code containing HTML special characters."""
        result = md_to_symphony("Run `echo '<hello>' && exit`")
        assert_valid_messageml(result, "code with special chars")
        assert "<hello>" not in result  # Must be escaped

    def test_long_agent_response(self):
        """Simulate a long structured agent response."""
        md = """## Analysis Results

### Overview

The analysis of **`main.py`** reveals the following:

1. **Import issues**: `os` is imported but unused
2. **Type errors**: `calculate()` returns `str` but `int` expected
3. **Style**: Lines exceed 120 chars

### Recommendations

- Remove unused import `os`
- Add return type annotation to `calculate()`
- Run `ruff format` to fix style

### Code Fix

```python
def calculate(x: int, y: int) -> int:
    return x + y
```

Use **`ruff check --fix`** to auto-fix."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, "long agent response")


class TestValidator:
    """Test that the validator correctly catches violations."""

    def test_catches_code_in_bold(self):
        violations = validate_messageml("<b><code>bad</code></b>")
        assert len(violations) == 1
        assert '"code" is not allowed in "b"' in violations[0]

    def test_catches_code_in_italic(self):
        violations = validate_messageml("<i><code>bad</code></i>")
        assert len(violations) == 1
        assert '"code" is not allowed in "i"' in violations[0]

    def test_catches_code_in_h1(self):
        violations = validate_messageml("<h1><code>bad</code></h1>")
        assert len(violations) == 1
        assert '"code" is not allowed in "h1"' in violations[0]

    def test_catches_code_in_h3(self):
        violations = validate_messageml("<h3><code>bad</code></h3>")
        assert len(violations) == 1
        assert '"code" is not allowed in "h3"' in violations[0]

    def test_catches_code_in_h6(self):
        violations = validate_messageml("<h6><code>bad</code></h6>")
        assert len(violations) == 1
        assert '"code" is not allowed in "h6"' in violations[0]

    def test_catches_pre_in_bold(self):
        violations = validate_messageml("<b><pre>bad</pre></b>")
        assert len(violations) == 1
        assert '"pre" is not allowed in "b"' in violations[0]

    def test_catches_pre_in_heading(self):
        violations = validate_messageml("<h2><pre>bad</pre></h2>")
        assert len(violations) == 1
        assert '"pre" is not allowed in "h2"' in violations[0]

    def test_allows_bold_in_italic(self):
        violations = validate_messageml("<i><b>ok</b></i>")
        assert violations == []

    def test_allows_italic_in_bold(self):
        violations = validate_messageml("<b><i>ok</i></b>")
        assert violations == []

    def test_allows_link_in_bold(self):
        violations = validate_messageml('<b><a href="http://x">ok</a></b>')
        assert violations == []

    def test_allows_link_in_heading(self):
        violations = validate_messageml('<h1><a href="http://x">ok</a></h1>')
        assert violations == []

    def test_allows_br_in_bold(self):
        violations = validate_messageml("<b>line1<br/>line2</b>")
        assert violations == []

    def test_allows_span_in_italic(self):
        violations = validate_messageml("<i><span>ok</span></i>")
        assert violations == []

    def test_allows_code_standalone(self):
        violations = validate_messageml("<p><code>ok</code></p>")
        assert violations == []

    def test_allows_code_in_li(self):
        violations = validate_messageml("<ul><li><code>ok</code></li></ul>")
        assert violations == []

    def test_allows_pre_in_code(self):
        """<code> permits <pre> as child."""
        violations = validate_messageml("<code><pre>ok</pre></code>")
        assert violations == []

    def test_catches_table_in_bold(self):
        violations = validate_messageml("<b><table><tr><td>x</td></tr></table></b>")
        assert any('"table" is not allowed in "b"' in v for v in violations)

    def test_catches_ul_in_italic(self):
        violations = validate_messageml("<i><ul><li>x</li></ul></i>")
        assert any('"ul" is not allowed in "i"' in v for v in violations)

    def test_catches_p_in_bold(self):
        violations = validate_messageml("<b><p>bad</p></b>")
        assert any('"p" is not allowed in "b"' in v for v in violations)

    def test_catches_div_in_heading(self):
        violations = validate_messageml("<h1><div>bad</div></h1>")
        assert any('"div" is not allowed in "h1"' in v for v in violations)

    def test_deeply_nested_violation(self):
        """<b><i><code>x</code></i></b> — code in italic (inside bold)."""
        violations = validate_messageml("<b><i><code>bad</code></i></b>")
        assert any('"code" is not allowed in "i"' in v for v in violations)

    def test_valid_complex_structure(self):
        """Complex but valid structure."""
        html = "<p><b>Hello</b> <i>world</i></p><ul><li><code>cmd</code></li></ul><h2><b>Title</b></h2><pre>code block</pre>"
        violations = validate_messageml(html)
        assert violations == []


class TestFullPipeline:
    """End-to-end tests: markdown → parse → render → validate."""

    @pytest.mark.parametrize(
        "md,desc",
        [
            ("Hello world", "plain text"),
            ("**bold**", "bold"),
            ("*italic*", "italic"),
            ("~~strike~~", "strikethrough"),
            ("`code`", "inline code"),
            ("```\nblock\n```", "code block"),
            ("[link](https://x.com)", "link"),
            ("> quote", "blockquote"),
            ("---", "horizontal rule"),
            ("- a\n- b", "unordered list"),
            ("1. a\n2. b", "ordered list"),
            ("# H1", "heading 1"),
            ("## H2", "heading 2"),
            ("### H3", "heading 3"),
            ("| A | B |\n|---|---|\n| 1 | 2 |", "table"),
        ],
    )
    def test_basic_elements(self, md: str, desc: str):
        """Each basic markdown element produces valid MessageML."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, desc)

    @pytest.mark.parametrize(
        "md,desc",
        [
            ("**`code in bold`**", "code in bold"),
            ("*`code in italic`*", "code in italic"),
            ("# `code in h1`", "code in h1"),
            ("## `code in h2`", "code in h2"),
            ("### `code in h3`", "code in h3"),
            ("#### `code in h4`", "code in h4"),
            ("##### `code in h5`", "code in h5"),
            ("###### `code in h6`", "code in h6"),
            ("***`code in bold+italic`***", "code in bold+italic"),
            ("**text `code` more**", "code mid-bold"),
            ("## The `function()` method", "code in h2 with text"),
        ],
    )
    def test_forbidden_nesting_handled(self, md: str, desc: str):
        """All forbidden nesting combos produce valid output."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, desc)

    @pytest.mark.parametrize(
        "md,desc",
        [
            ("**[link](https://x.com)**", "link in bold"),
            ("*[link](https://x.com)*", "link in italic"),
            ("## [link](https://x.com)", "link in heading"),
            ("***bold italic***", "bold+italic"),
            ("**text *nested italic* text**", "italic in bold"),
            ("*text **nested bold** text*", "bold in italic"),
            ("## **Bold heading**", "bold in heading"),
        ],
    )
    def test_allowed_nesting(self, md: str, desc: str):
        """All allowed nesting combos produce valid output."""
        result = md_to_symphony(md)
        assert_valid_messageml(result, desc)


def _extract_between(html: str, open_tag: str, close_tag: str) -> str:
    """Extract content between opening and closing tags."""
    start = html.find(open_tag)
    if start == -1:
        return ""
    start += len(open_tag)
    end = html.find(close_tag, start)
    if end == -1:
        return html[start:]
    return html[start:end]
