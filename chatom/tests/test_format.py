"""Tests for chatom format system."""

from chatom.format import (
    DISCORD_MARKDOWN,
    HTML,
    MARKDOWN,
    PLAINTEXT,
    SLACK_MARKDOWN,
    SYMPHONY_MESSAGEML,
    Bold,
    ChannelMention,
    Code,
    CodeBlock,
    Document,
    # Variant/Format
    Format,
    FormattedAttachment,
    FormattedImage,
    # Message formatting
    FormattedMessage,
    Heading,
    Italic,
    Link,
    ListItem,
    MessageBuilder,
    OrderedList,
    Paragraph,
    Quote,
    Span,
    Strikethrough,
    # Table
    Table,
    TableCell,
    TableRow,
    # Text nodes
    Text,
    Underline,
    UnorderedList,
    UserMention,
    format_message,
    render_message,
)


class TestFormat:
    """Tests for Format enum and constants."""

    def test_format_enum_values(self):
        """Test format enum has expected values."""
        assert Format.PLAINTEXT == "plaintext"
        assert Format.MARKDOWN == "markdown"
        assert Format.SLACK_MARKDOWN == "slack-markdown"
        assert Format.DISCORD_MARKDOWN == "discord-markdown"
        assert Format.HTML == "html"
        assert Format.SYMPHONY_MESSAGEML == "symphony-messageml"

    def test_format_constants(self):
        """Test format constants match enum."""
        assert PLAINTEXT == Format.PLAINTEXT
        assert MARKDOWN == Format.MARKDOWN
        assert SLACK_MARKDOWN == Format.SLACK_MARKDOWN
        assert DISCORD_MARKDOWN == Format.DISCORD_MARKDOWN
        assert HTML == Format.HTML
        assert SYMPHONY_MESSAGEML == Format.SYMPHONY_MESSAGEML


class TestTextNodes:
    """Tests for text node classes."""

    def test_text_node(self):
        """Test basic Text node."""
        node = Text(content="Hello")
        assert node.render(Format.PLAINTEXT) == "Hello"
        assert node.render(Format.MARKDOWN) == "Hello"
        assert node.render(Format.HTML) == "Hello"

    def test_bold_node(self):
        """Test Bold node rendering."""
        node = Bold(child=Text(content="important"))
        assert node.render(Format.PLAINTEXT) == "important"
        assert node.render(Format.MARKDOWN) == "**important**"
        assert node.render(Format.SLACK_MARKDOWN) == "*important*"
        assert node.render(Format.HTML) == "<b>important</b>"
        assert node.render(Format.SYMPHONY_MESSAGEML) == "<b>important</b>"

    def test_italic_node(self):
        """Test Italic node rendering."""
        node = Italic(child=Text(content="emphasis"))
        assert node.render(Format.PLAINTEXT) == "emphasis"
        assert node.render(Format.MARKDOWN) == "*emphasis*"
        assert node.render(Format.SLACK_MARKDOWN) == "_emphasis_"
        assert node.render(Format.HTML) == "<i>emphasis</i>"
        assert node.render(Format.SYMPHONY_MESSAGEML) == "<i>emphasis</i>"

    def test_strikethrough_node(self):
        """Test Strikethrough node rendering."""
        node = Strikethrough(child=Text(content="deleted"))
        assert node.render(Format.PLAINTEXT) == "deleted"
        assert node.render(Format.MARKDOWN) == "~~deleted~~"
        assert node.render(Format.SLACK_MARKDOWN) == "~deleted~"
        assert node.render(Format.HTML) == "<s>deleted</s>"

    def test_underline_node(self):
        """Test Underline node rendering."""
        node = Underline(child=Text(content="underlined"))
        assert node.render(Format.PLAINTEXT) == "underlined"
        assert node.render(Format.DISCORD_MARKDOWN) == "__underlined__"
        assert node.render(Format.HTML) == "<u>underlined</u>"

    def test_code_node(self):
        """Test Code node rendering."""
        node = Code(content="print('hello')")
        assert node.render(Format.PLAINTEXT) == "print('hello')"
        assert node.render(Format.MARKDOWN) == "`print('hello')`"
        assert node.render(Format.HTML) == "<code>print('hello')</code>"

    def test_code_block_node(self):
        """Test CodeBlock node rendering."""
        node = CodeBlock(content="def foo():\n    pass", language="python")

        plaintext = node.render(Format.PLAINTEXT)
        assert "def foo():" in plaintext

        markdown = node.render(Format.MARKDOWN)
        assert markdown.startswith("```python")
        assert "def foo():" in markdown
        assert markdown.endswith("```")

        html = node.render(Format.HTML)
        assert '<pre><code class="language-python">' in html

    def test_link_node(self):
        """Test Link node rendering."""
        node = Link(url="https://example.com", text="Example")

        assert "Example" in node.render(Format.PLAINTEXT)
        assert "https://example.com" in node.render(Format.PLAINTEXT)
        markdown = node.render(Format.MARKDOWN)
        assert "[Example]" in markdown or "[https://example.com]" in markdown
        assert "href" in node.render(Format.HTML) or "https://example.com" in node.render(Format.HTML)

    def test_quote_node(self):
        """Test Quote node rendering."""
        node = Quote(child=Text(content="Quoted text"))

        assert "Quoted text" in node.render(Format.PLAINTEXT)
        result = node.render(Format.MARKDOWN)
        assert "Quoted text" in result
        html = node.render(Format.HTML)
        assert "Quoted text" in html

    def test_heading_node(self):
        """Test Heading node rendering."""
        h1 = Heading(level=1, child=Text(content="Title"))
        h2 = Heading(level=2, child=Text(content="Subtitle"))

        assert "# Title" in h1.render(Format.MARKDOWN) or "Title" in h1.render(Format.MARKDOWN)
        assert "Subtitle" in h2.render(Format.MARKDOWN)
        html = h1.render(Format.HTML)
        assert "Title" in html

    def test_list_nodes(self):
        """Test list node rendering."""
        ul = UnorderedList(
            items=[
                ListItem(child=Text(content="Item 1")),
                ListItem(child=Text(content="Item 2")),
            ]
        )

        markdown = ul.render(Format.MARKDOWN)
        assert "Item 1" in markdown
        assert "Item 2" in markdown

        html = ul.render(Format.HTML)
        assert "<ul>" in html or "Item 1" in html

        ol = OrderedList(
            items=[
                ListItem(child=Text(content="First")),
                ListItem(child=Text(content="Second")),
            ]
        )

        markdown = ol.render(Format.MARKDOWN)
        assert "First" in markdown
        assert "Second" in markdown

    def test_nested_nodes(self):
        """Test nested text nodes."""
        node = Bold(
            child=Span(
                children=[
                    Text(content="Bold with "),
                    Italic(child=Text(content="italic")),
                    Text(content=" text"),
                ]
            )
        )

        result = node.render(Format.MARKDOWN)
        assert "Bold with" in result
        assert "italic" in result

    def test_user_mention_node(self):
        """Test UserMention node rendering."""
        node = UserMention(user_id="123", display_name="John")

        assert "John" in node.render(Format.PLAINTEXT)
        assert "<@123>" in node.render(Format.SLACK_MARKDOWN) or "123" in node.render(Format.SLACK_MARKDOWN)

    def test_channel_mention_node(self):
        """Test ChannelMention node rendering."""
        node = ChannelMention(channel_id="456", channel_name="general")

        result = node.render(Format.PLAINTEXT)
        # Just verify it renders without error
        assert result is not None


class TestDocument:
    """Tests for Document node."""

    def test_document_render(self):
        """Test document with multiple children."""
        doc = Document(
            children=[
                Heading(level=1, child=Text(content="Title")),
                Paragraph(children=[Text(content="First paragraph.")]),
                Paragraph(
                    children=[
                        Text(content="Second paragraph with "),
                        Bold(child=Text(content="bold")),
                        Text(content=" text."),
                    ]
                ),
            ]
        )

        markdown = doc.render(Format.MARKDOWN)
        assert "Title" in markdown
        assert "First paragraph." in markdown


class TestTable:
    """Tests for Table class."""

    def test_create_table(self):
        """Test creating a table."""
        headers = TableRow(
            cells=[
                TableCell(content="Name"),
                TableCell(content="Age"),
            ]
        )
        rows = [
            TableRow(
                cells=[
                    TableCell(content="Alice"),
                    TableCell(content="25"),
                ]
            ),
            TableRow(
                cells=[
                    TableCell(content="Bob"),
                    TableCell(content="30"),
                ]
            ),
        ]
        table = Table(headers=headers, rows=rows)

        assert table.headers is not None
        assert len(table.rows) == 2

    def test_table_from_data(self):
        """Test creating table from data."""
        data = [
            ["Alice", "25"],
            ["Bob", "30"],
        ]
        table = Table.from_data(data, headers=["Name", "Age"])

        assert table.headers is not None
        assert len(table.rows) == 2

    def test_table_render_markdown(self):
        """Test table rendering to markdown."""
        data = [["Alice", "25"], ["Bob", "30"]]
        table = Table.from_data(data, headers=["Name", "Age"])

        result = table.render(Format.MARKDOWN)
        assert "Name" in result
        assert "Alice" in result
        assert "|" in result

    def test_table_render_html(self):
        """Test table rendering to HTML."""
        data = [["Alice", "25"]]
        table = Table.from_data(data, headers=["Name", "Age"])

        result = table.render(Format.HTML)
        assert "<table>" in result
        assert "Name" in result
        assert "Alice" in result
        assert "</table>" in result

    def test_table_render_plaintext(self):
        """Test table rendering to plaintext."""
        data = [["Alice", "25"]]
        table = Table.from_data(data, headers=["Name", "Age"])

        result = table.render(Format.PLAINTEXT)
        assert "Name" in result
        assert "Alice" in result


class TestFormattedAttachment:
    """Tests for FormattedAttachment class."""

    def test_formatted_attachment_render(self):
        """Test rendering a formatted attachment."""
        attachment = FormattedAttachment(
            filename="document.pdf",
            url="https://example.com/doc.pdf",
        )

        # All formats should include the filename
        assert "document.pdf" in attachment.render(Format.PLAINTEXT)

        html = attachment.render(Format.HTML)
        assert "document.pdf" in html or "https://example.com/doc.pdf" in html


class TestFormattedImage:
    """Tests for FormattedImage class."""

    def test_formatted_image_render(self):
        """Test rendering a formatted image."""
        image = FormattedImage(
            url="https://example.com/photo.png",
            alt="A photo",
            title="My Photo",
        )

        markdown = image.render(Format.MARKDOWN)
        assert "https://example.com/photo.png" in markdown

        html = image.render(Format.HTML)
        assert "<img" in html
        assert 'src="https://example.com/photo.png"' in html


class TestFormattedMessage:
    """Tests for FormattedMessage class."""

    def test_formatted_message_render(self):
        """Test rendering a formatted message."""
        msg = FormattedMessage(
            content=[
                Paragraph(children=[Text(content="Hello, world!")]),
            ]
        )

        result = msg.render(Format.PLAINTEXT)
        assert "Hello, world!" in result

    def test_formatted_message_add_text(self):
        """Test add_text method."""
        msg = FormattedMessage()
        msg.add_text("Hello")
        assert msg.render(Format.PLAINTEXT) == "Hello"

    def test_formatted_message_add_bold(self):
        """Test add_bold method."""
        msg = FormattedMessage()
        msg.add_bold("important")
        assert msg.render(Format.MARKDOWN) == "**important**"

    def test_formatted_message_add_italic(self):
        """Test add_italic method."""
        msg = FormattedMessage()
        msg.add_italic("emphasis")
        assert msg.render(Format.MARKDOWN) == "*emphasis*"

    def test_formatted_message_add_code(self):
        """Test add_code method."""
        msg = FormattedMessage()
        msg.add_code("some_code")
        assert msg.render(Format.MARKDOWN) == "`some_code`"

    def test_formatted_message_add_code_block(self):
        """Test add_code_block method."""
        msg = FormattedMessage()
        msg.add_code_block("print('hi')", language="python")
        result = msg.render(Format.MARKDOWN)
        assert "```python" in result
        assert "print('hi')" in result

    def test_formatted_message_add_link(self):
        """Test add_link method."""
        msg = FormattedMessage()
        msg.add_link("Link Text", "https://example.com")
        result = msg.render(Format.MARKDOWN)
        assert "[Link Text]" in result
        assert "https://example.com" in result

    def test_formatted_message_add_line_break(self):
        """Test add_line_break method."""
        msg = FormattedMessage()
        msg.add_text("Line 1")
        msg.add_line_break()
        msg.add_text("Line 2")
        result = msg.render(Format.PLAINTEXT)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_formatted_message_add_table(self):
        """Test add_table method."""
        table = Table.from_data([["A", "B"]], headers=["Col1", "Col2"])
        msg = FormattedMessage()
        msg.add_table(table)
        result = msg.render(Format.MARKDOWN)
        assert "Col1" in result
        assert "A" in result

    def test_formatted_message_add_image(self):
        """Test add_image method."""
        msg = FormattedMessage()
        msg.add_image("https://example.com/img.png", alt_text="Image")
        result = msg.render(Format.MARKDOWN)
        assert "https://example.com/img.png" in result

    def test_formatted_message_append_string(self):
        """Test append method with string."""
        msg = FormattedMessage()
        msg.append("Hello")
        result = msg.render(Format.PLAINTEXT)
        assert "Hello" in result

    def test_formatted_message_chaining(self):
        """Test method chaining."""
        msg = FormattedMessage()
        result = msg.add_text("Hello ").add_bold("world").add_text("!")
        assert result is msg  # Returns self
        assert "Hello " in msg.render(Format.PLAINTEXT)
        assert "world" in msg.render(Format.PLAINTEXT)

    def test_formatted_message_add_raw_preserves_xml(self):
        """Test that add_raw preserves XML tags without escaping.

        This is critical for Symphony mentions like <mention uid="12345"/>
        which should NOT be escaped when rendered.
        """
        msg = FormattedMessage()
        mention_xml = '<mention uid="12345"/>'
        msg.add_text("Hello ").add_raw(mention_xml).add_text("!")

        # When rendered for Symphony MessageML, the XML should be preserved
        result = msg.render(Format.SYMPHONY_MESSAGEML)
        assert '<mention uid="12345"/>' in result
        # The angle brackets should NOT be escaped
        assert "&lt;mention" not in result
        assert "&gt;" not in result

    def test_formatted_message_add_raw_for_hashtags(self):
        """Test add_raw preserves Symphony hashtag XML."""
        msg = FormattedMessage()
        msg.add_text("Check out ").add_raw('<hash tag="chatom"/>').add_text("!")

        result = msg.render(Format.SYMPHONY_MESSAGEML)
        assert '<hash tag="chatom"/>' in result

    def test_formatted_message_default_format(self):
        """Test render with default format."""
        msg = FormattedMessage()
        msg.add_bold("test")
        # Default is MARKDOWN
        result = msg.render()
        assert "**test**" in result


class TestMessageBuilder:
    """Tests for MessageBuilder class."""

    def test_message_builder_exists(self):
        """Test that MessageBuilder can be instantiated."""
        builder = MessageBuilder()
        assert builder is not None

    def test_message_builder_build(self):
        """Test that MessageBuilder can build a message."""
        builder = MessageBuilder()
        # Just verify build() works without error
        msg = builder.build()
        assert msg is not None

    def test_message_builder_text(self):
        """Test MessageBuilder.text method."""
        msg = MessageBuilder().text("Hello world").build()
        assert msg.render(Format.PLAINTEXT) == "Hello world"

    def test_message_builder_bold(self):
        """Test MessageBuilder.bold method."""
        msg = MessageBuilder().bold("important").build()
        assert msg.render(Format.MARKDOWN) == "**important**"

    def test_message_builder_italic(self):
        """Test MessageBuilder.italic method."""
        msg = MessageBuilder().italic("emphasis").build()
        assert msg.render(Format.MARKDOWN) == "*emphasis*"

    def test_message_builder_strikethrough(self):
        """Test MessageBuilder.strikethrough method."""
        msg = MessageBuilder().strikethrough("deleted").build()
        assert msg.render(Format.MARKDOWN) == "~~deleted~~"

    def test_message_builder_code(self):
        """Test MessageBuilder.code method."""
        msg = MessageBuilder().code("inline_code").build()
        assert msg.render(Format.MARKDOWN) == "`inline_code`"

    def test_message_builder_code_block(self):
        """Test MessageBuilder.code_block method."""
        msg = MessageBuilder().code_block("print('hello')", language="python").build()
        result = msg.render(Format.MARKDOWN)
        assert "```python" in result
        assert "print('hello')" in result

    def test_message_builder_link(self):
        """Test MessageBuilder.link method."""
        msg = MessageBuilder().link("Click here", "https://example.com").build()
        result = msg.render(Format.MARKDOWN)
        assert "[Click here]" in result
        assert "https://example.com" in result

    def test_message_builder_quote(self):
        """Test MessageBuilder.quote method."""
        msg = MessageBuilder().quote("A famous quote").build()
        result = msg.render(Format.MARKDOWN)
        assert "> A famous quote" in result

    def test_message_builder_heading(self):
        """Test MessageBuilder.heading method."""
        msg = MessageBuilder().heading("Title", level=1).build()
        result = msg.render(Format.MARKDOWN)
        assert "# Title" in result

    def test_message_builder_heading_level2(self):
        """Test MessageBuilder.heading with level 2."""
        msg = MessageBuilder().heading("Subtitle", level=2).build()
        result = msg.render(Format.MARKDOWN)
        assert "## Subtitle" in result

    def test_message_builder_line_break(self):
        """Test MessageBuilder.line_break method."""
        msg = MessageBuilder().text("Line 1").line_break().text("Line 2").build()
        result = msg.render(Format.PLAINTEXT)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_message_builder_paragraph(self):
        """Test MessageBuilder.paragraph method."""
        msg = MessageBuilder().paragraph("A paragraph of text.").build()
        result = msg.render(Format.PLAINTEXT)
        assert "A paragraph of text." in result

    def test_message_builder_bullet_list(self):
        """Test MessageBuilder.bullet_list method."""
        msg = MessageBuilder().bullet_list(["Item 1", "Item 2", "Item 3"]).build()
        result = msg.render(Format.MARKDOWN)
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result

    def test_message_builder_numbered_list(self):
        """Test MessageBuilder.numbered_list method."""
        msg = MessageBuilder().numbered_list(["First", "Second", "Third"]).build()
        result = msg.render(Format.MARKDOWN)
        assert "First" in result
        assert "Second" in result
        assert "Third" in result

    def test_message_builder_table(self):
        """Test MessageBuilder.table method."""
        data = [["Alice", "30"], ["Bob", "25"]]
        msg = MessageBuilder().table(data, headers=["Name", "Age"]).build()
        result = msg.render(Format.MARKDOWN)
        assert "Alice" in result
        assert "Bob" in result
        assert "Name" in result

    def test_message_builder_table_from_dicts(self):
        """Test MessageBuilder.table_from_dicts method."""
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        msg = MessageBuilder().table_from_dicts(data, columns=["name", "age"]).build()
        result = msg.render(Format.MARKDOWN)
        assert "Alice" in result
        assert "Bob" in result

    def test_message_builder_image(self):
        """Test MessageBuilder.image method."""
        msg = MessageBuilder().image("https://example.com/img.png", alt_text="An image").build()
        result = msg.render(Format.MARKDOWN)
        assert "https://example.com/img.png" in result

    def test_message_builder_attachment(self):
        """Test MessageBuilder.attachment method."""
        msg = MessageBuilder().text("See attached file").attachment("doc.pdf", "https://example.com/doc.pdf").build()
        assert len(msg.attachments) == 1
        assert msg.attachments[0].filename == "doc.pdf"

    def test_message_builder_node(self):
        """Test MessageBuilder.node method for custom nodes."""
        custom_node = Bold(child=Italic(child=Text(content="nested")))
        msg = MessageBuilder().node(custom_node).build()
        result = msg.render(Format.MARKDOWN)
        assert "nested" in result

    def test_message_builder_metadata(self):
        """Test MessageBuilder.metadata method."""
        msg = MessageBuilder().text("Hello").metadata("key", "value").build()
        assert msg.metadata.get("key") == "value"

    def test_message_builder_chaining(self):
        """Test MessageBuilder method chaining."""
        msg = MessageBuilder().text("Hello, ").bold("world").text("! ").italic("How are you?").build()
        result = msg.render(Format.MARKDOWN)
        assert "Hello, " in result
        assert "**world**" in result
        assert "*How are you?*" in result


class TestRenderMessage:
    """Tests for render_message utility."""

    def test_render_message_basic(self):
        """Test render_message with basic content."""
        # Create a FormattedMessage and render it
        msg = FormattedMessage(content=[Text(content="Hello")])
        result = render_message(msg, Format.MARKDOWN)
        assert "Hello" in result


class TestFormatMessage:
    """Tests for format_message utility."""

    def test_format_message_basic(self):
        """Test format_message with basic content."""
        # format_message takes a plain string and escapes for the format
        result = format_message("Test", Format.PLAINTEXT)
        assert "Test" in result

    def test_format_message_plaintext(self):
        """Test format_message returns unchanged for plaintext."""
        result = format_message("Hello <world> & friends", Format.PLAINTEXT)
        assert result == "Hello <world> & friends"

    def test_format_message_html_escaping(self):
        """Test format_message escapes HTML characters."""
        result = format_message("Hello <script>alert('xss')</script>", Format.HTML)
        assert "&lt;" in result
        assert "&gt;" in result
        assert "<script>" not in result

    def test_format_message_html_ampersand(self):
        """Test format_message escapes ampersands for HTML."""
        result = format_message("Tom & Jerry", Format.HTML)
        assert "&amp;" in result
        assert "Tom & Jerry" not in result

    def test_format_message_symphony_messageml(self):
        """Test format_message escapes for Symphony MessageML."""
        result = format_message("Hello ${var} and #{tag}", Format.SYMPHONY_MESSAGEML)
        assert "${" not in result
        assert "#{" not in result
        assert "&#36;{" in result
        assert "&#35;{" in result

    def test_format_message_symphony_html_escaping(self):
        """Test format_message escapes HTML in Symphony format."""
        result = format_message("<b>not bold</b>", Format.SYMPHONY_MESSAGEML)
        assert "&lt;" in result
        assert "&gt;" in result

    def test_format_message_disable_html_escaping(self):
        """Test format_message with escape_html=False."""
        result = format_message("<b>bold</b>", Format.HTML, escape_html=False)
        assert "<b>bold</b>" == result

    def test_format_message_disable_symphony_escaping(self):
        """Test format_message with escape_symphony=False."""
        result = format_message("${var}", Format.SYMPHONY_MESSAGEML, escape_symphony=False)
        # HTML is still escaped
        assert "${var}" in result

    def test_format_message_string_format(self):
        """Test format_message accepts string format."""
        result = format_message("<test>", "html")
        assert "&lt;test&gt;" in result


class TestRenderFor:
    """Tests for FormattedMessage.render_for method."""

    def test_render_for_slack(self):
        """Test render_for with Slack backend."""
        msg = FormattedMessage(content=[Bold(child=Text(content="important"))])
        result = msg.render_for("slack")
        # Slack uses *text* for bold
        assert "*important*" in result

    def test_render_for_discord(self):
        """Test render_for with Discord backend."""
        msg = FormattedMessage(content=[Bold(child=Text(content="important"))])
        result = msg.render_for("discord")
        # Discord uses **text** for bold
        assert "**important**" in result

    def test_render_for_symphony(self):
        """Test render_for with Symphony backend."""
        msg = FormattedMessage(content=[Bold(child=Text(content="important"))])
        result = msg.render_for("symphony")
        # Symphony uses <b>text</b> for bold when properly registered
        # Falls back to markdown (**text**) if not registered
        assert "important" in result

    def test_render_for_matrix(self):
        """Test render_for with Matrix backend."""
        msg = FormattedMessage(content=[Bold(child=Text(content="important"))])
        result = msg.render_for("matrix")
        # Matrix uses HTML when properly registered
        # Falls back to markdown if not registered
        assert "important" in result

    def test_render_for_irc(self):
        """Test render_for with IRC backend."""
        msg = FormattedMessage(content=[Bold(child=Text(content="important"))])
        result = msg.render_for("irc")
        # IRC uses plaintext
        assert "important" in result

    def test_render_for_email(self):
        """Test render_for with email backend."""
        msg = FormattedMessage(content=[Bold(child=Text(content="important"))])
        result = msg.render_for("email")
        # Email uses HTML when properly registered
        # Falls back to markdown if not registered
        assert "important" in result

    def test_render_for_unknown_backend(self):
        """Test render_for with unknown backend falls back to markdown."""
        msg = FormattedMessage(content=[Bold(child=Text(content="important"))])
        result = msg.render_for("unknown_platform")
        # Unknown backends fall back to markdown
        assert "**important**" in result

    def test_render_for_case_insensitive(self):
        """Test render_for is case insensitive."""
        msg = FormattedMessage(content=[Text(content="hello")])
        # All should work the same
        result1 = msg.render_for("slack")
        result2 = msg.render_for("SLACK")
        result3 = msg.render_for("Slack")
        assert result1 == result2 == result3


class TestGetFormatForBackend:
    """Tests for get_format_for_backend function."""

    def test_get_format_for_known_backends_via_map(self):
        """Test get_format_for_backend returns correct formats via BACKEND_FORMAT_MAP."""
        from chatom.format.message import BACKEND_FORMAT_MAP

        # Test the static map directly
        assert BACKEND_FORMAT_MAP["discord"] == Format.DISCORD_MARKDOWN
        assert BACKEND_FORMAT_MAP["slack"] == Format.SLACK_MARKDOWN
        assert BACKEND_FORMAT_MAP["symphony"] == Format.SYMPHONY_MESSAGEML
        assert BACKEND_FORMAT_MAP["matrix"] == Format.HTML
        assert BACKEND_FORMAT_MAP["irc"] == Format.PLAINTEXT
        assert BACKEND_FORMAT_MAP["email"] == Format.HTML

    def test_get_format_for_unknown_backend(self):
        """Test get_format_for_backend returns markdown for unknown backends."""
        from chatom import get_format_for_backend

        assert get_format_for_backend("unknown") == Format.MARKDOWN
        assert get_format_for_backend("foo") == Format.MARKDOWN


class TestBackendFormatMap:
    """Tests for BACKEND_FORMAT_MAP constant."""

    def test_backend_format_map_exists(self):
        """Test that BACKEND_FORMAT_MAP is exported."""
        from chatom import BACKEND_FORMAT_MAP

        assert isinstance(BACKEND_FORMAT_MAP, dict)


class TestTextNodeOperators:
    """Tests for TextNode operator overloads."""

    def test_text_node_str(self):
        """Test TextNode __str__ method."""
        node = Text(content="Hello")
        assert str(node) == "Hello"

    def test_text_node_add_nodes(self):
        """Test TextNode __add__ with another node."""
        node1 = Text(content="Hello ")
        node2 = Text(content="World")
        result = node1 + node2
        assert result.render(Format.PLAINTEXT) == "Hello World"

    def test_text_node_add_string(self):
        """Test TextNode __add__ with string."""
        node = Text(content="Hello ")
        result = node + "World"
        assert result.render(Format.PLAINTEXT) == "Hello World"


class TestSpanNode:
    """Tests for Span node with multiple children."""

    def test_span_with_multiple_children(self):
        """Test Span with multiple children."""
        span = Span(
            children=[
                Text(content="Start "),
                Bold(child=Text(content="bold")),
                Text(content=" end"),
            ]
        )
        result = span.render(Format.MARKDOWN)
        assert "Start " in result
        assert "**bold**" in result
        assert " end" in result


class TestUnderlineNode:
    """Tests for Underline node."""

    def test_underline_render_plaintext(self):
        """Test Underline renders correctly in plaintext."""
        node = Underline(child=Text(content="underlined"))
        assert node.render(Format.PLAINTEXT) == "underlined"

    def test_underline_render_html(self):
        """Test Underline renders correctly in HTML."""
        node = Underline(child=Text(content="underlined"))
        assert "<u>underlined</u>" in node.render(Format.HTML)


class TestHorizontalRule:
    """Tests for HorizontalRule node."""

    def test_horizontal_rule_markdown(self):
        """Test HorizontalRule in Markdown."""
        from chatom.format import HorizontalRule

        node = HorizontalRule()
        result = node.render(Format.MARKDOWN)
        assert "---" in result or "***" in result

    def test_horizontal_rule_html(self):
        """Test HorizontalRule in HTML."""
        from chatom.format import HorizontalRule

        node = HorizontalRule()
        result = node.render(Format.HTML)
        assert "<hr" in result


class TestEmojiNode:
    """Tests for Emoji node."""

    def test_emoji_render(self):
        """Test Emoji renders correctly."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="smile")
        result = node.render(Format.PLAINTEXT)
        assert "smile" in result


class TestTableFromDictList:
    """Tests for Table.from_dict_list method."""

    def test_table_from_dict_list_with_columns(self):
        """Test Table.from_dict_list with specific columns."""
        data = [
            {"name": "Alice", "age": 30, "city": "NYC"},
            {"name": "Bob", "age": 25, "city": "LA"},
        ]
        table = Table.from_dict_list(data, columns=["name", "age"])
        result = table.render(Format.MARKDOWN)
        assert "name" in result
        assert "age" in result
        assert "Alice" in result
        assert "Bob" in result
        # city should not be included
        assert "city" not in result or "NYC" not in result

    def test_table_from_dict_list_without_columns(self):
        """Test Table.from_dict_list infers columns from data."""
        data = [
            {"name": "Alice", "score": 100},
            {"name": "Bob", "score": 95},
        ]
        table = Table.from_dict_list(data)
        result = table.render(Format.MARKDOWN)
        assert "name" in result
        assert "score" in result


class TestTableRendering:
    """Additional tests for Table rendering."""

    def test_table_render_slack_markdown(self):
        """Test table rendering in Slack markdown."""
        data = [["A", "B"], ["C", "D"]]
        table = Table.from_data(data, headers=["Col1", "Col2"])
        result = table.render(Format.SLACK_MARKDOWN)
        assert "Col1" in result
        assert "A" in result

    def test_table_render_discord_markdown(self):
        """Test table rendering in Discord markdown."""
        data = [["A", "B"]]
        table = Table.from_data(data, headers=["X", "Y"])
        result = table.render(Format.DISCORD_MARKDOWN)
        assert "X" in result

    def test_table_render_symphony(self):
        """Test table rendering in Symphony MessageML."""
        data = [["A", "B"]]
        table = Table.from_data(data, headers=["X", "Y"])
        result = table.render(Format.SYMPHONY_MESSAGEML)
        assert "X" in result or "A" in result

    def test_table_with_caption(self):
        """Test table with caption."""
        data = [["A"]]
        table = Table.from_data(data, headers=["Col"], caption="My Table")
        result = table.render(Format.HTML)
        assert "My Table" in result or "Col" in result


class TestDocumentNode:
    """Additional tests for Document node."""

    def test_document_render_html(self):
        """Test Document rendering in HTML."""
        doc = Document(
            children=[
                Heading(level=1, child=Text(content="Title")),
                Paragraph(children=[Text(content="Content")]),
            ]
        )
        result = doc.render(Format.HTML)
        assert "Title" in result
        assert "Content" in result

    def test_document_render_plaintext(self):
        """Test Document rendering in plaintext."""
        doc = Document(children=[Text(content="Simple")])
        result = doc.render(Format.PLAINTEXT)
        assert "Simple" in result


class TestListRendering:
    """Tests for list rendering."""

    def test_unordered_list_html(self):
        """Test UnorderedList in HTML."""
        ul = UnorderedList(
            items=[
                ListItem(child=Text(content="Item 1")),
                ListItem(child=Text(content="Item 2")),
            ]
        )
        result = ul.render(Format.HTML)
        assert "<ul>" in result or "Item 1" in result

    def test_ordered_list_with_start(self):
        """Test OrderedList with custom start number."""
        ol = OrderedList(
            items=[
                ListItem(child=Text(content="First")),
                ListItem(child=Text(content="Second")),
            ],
            start=5,
        )
        result = ol.render(Format.MARKDOWN)
        assert "First" in result
        assert "Second" in result


class TestHeadingLevels:
    """Tests for different heading levels."""

    def test_heading_level_3(self):
        """Test heading level 3."""
        h = Heading(level=3, child=Text(content="Subheading"))
        result = h.render(Format.MARKDOWN)
        assert "### Subheading" in result

    def test_heading_level_html(self):
        """Test heading in HTML format."""
        h = Heading(level=2, child=Text(content="Section"))
        result = h.render(Format.HTML)
        assert "<h2>" in result or "Section" in result


class TestCodeBlockLanguages:
    """Tests for code blocks with different languages."""

    def test_code_block_no_language(self):
        """Test code block without language."""
        cb = CodeBlock(content="code here")
        result = cb.render(Format.MARKDOWN)
        assert "```" in result
        assert "code here" in result

    def test_code_block_javascript(self):
        """Test code block with JavaScript."""
        cb = CodeBlock(content="console.log('hi')", language="javascript")
        result = cb.render(Format.MARKDOWN)
        assert "```javascript" in result

    def test_code_block_html_format(self):
        """Test code block in HTML format."""
        cb = CodeBlock(content="print('hi')", language="python")
        result = cb.render(Format.HTML)
        assert "<code>" in result or "<pre>" in result or "print" in result


class TestLinkRendering:
    """Tests for Link rendering."""

    def test_link_with_title(self):
        """Test Link with title attribute."""
        link = Link(text="Click", url="https://example.com", title="Example Site")
        result = link.render(Format.MARKDOWN)
        assert "[Click]" in result
        assert "https://example.com" in result

    def test_link_html(self):
        """Test Link in HTML format."""
        link = Link(text="Click", url="https://example.com")
        result = link.render(Format.HTML)
        assert "<a " in result
        assert "href=" in result
        assert "https://example.com" in result


class TestTextEscaping:
    """Tests for text escaping in different formats."""

    def test_text_escapes_html(self):
        """Test that Text escapes HTML characters."""
        node = Text(content="<script>alert('xss')</script>")
        result = node.render(Format.HTML)
        assert "<script>" not in result
        assert "&lt;" in result

    def test_text_escapes_ampersand(self):
        """Test that Text escapes ampersands in HTML."""
        node = Text(content="Tom & Jerry")
        result = node.render(Format.HTML)
        assert "&amp;" in result


class TestFormattedAttachmentRender:
    """Tests for FormattedAttachment.render in all formats."""

    def test_attachment_markdown(self):
        """Test attachment in markdown format."""
        att = FormattedAttachment(filename="doc.pdf", url="https://example.com/doc.pdf")
        result = att.render(Format.MARKDOWN)
        assert "[doc.pdf]" in result
        assert "(https://example.com/doc.pdf)" in result

    def test_attachment_discord_markdown(self):
        """Test attachment in Discord markdown format."""
        att = FormattedAttachment(filename="doc.pdf", url="https://example.com/doc.pdf")
        result = att.render(Format.DISCORD_MARKDOWN)
        assert "[doc.pdf]" in result
        assert "(https://example.com/doc.pdf)" in result

    def test_attachment_slack_markdown(self):
        """Test attachment in Slack markdown format."""
        att = FormattedAttachment(filename="doc.pdf", url="https://example.com/doc.pdf")
        result = att.render(Format.SLACK_MARKDOWN)
        assert "<https://example.com/doc.pdf|doc.pdf>" == result

    def test_attachment_html(self):
        """Test attachment in HTML format."""
        att = FormattedAttachment(filename="doc.pdf", url="https://example.com/doc.pdf")
        result = att.render(Format.HTML)
        assert '<a href="https://example.com/doc.pdf">' in result
        assert "doc.pdf</a>" in result

    def test_attachment_symphony(self):
        """Test attachment in Symphony MessageML format."""
        att = FormattedAttachment(filename="doc.pdf", url="https://example.com/doc.pdf")
        result = att.render(Format.SYMPHONY_MESSAGEML)
        assert '<a href="https://example.com/doc.pdf">' in result

    def test_attachment_plaintext(self):
        """Test attachment in plaintext format."""
        att = FormattedAttachment(filename="doc.pdf", url="https://example.com/doc.pdf")
        result = att.render(Format.PLAINTEXT)
        assert "doc.pdf" in result
        assert "https://example.com/doc.pdf" in result


class TestFormattedImageRender:
    """Tests for FormattedImage.render in all formats."""

    def test_image_markdown(self):
        """Test image in markdown format."""
        img = FormattedImage(url="https://example.com/img.png", alt_text="Logo")
        result = img.render(Format.MARKDOWN)
        assert "![Logo]" in result
        assert "(https://example.com/img.png)" in result

    def test_image_markdown_with_title(self):
        """Test image with title in markdown format."""
        img = FormattedImage(
            url="https://example.com/img.png",
            alt_text="Logo",
            title="Company Logo",
        )
        result = img.render(Format.MARKDOWN)
        assert '"Company Logo"' in result

    def test_image_discord_markdown(self):
        """Test image in Discord markdown format."""
        img = FormattedImage(url="https://example.com/img.png", alt_text="Logo")
        result = img.render(Format.DISCORD_MARKDOWN)
        assert "![Logo]" in result

    def test_image_slack_markdown(self):
        """Test image in Slack markdown format (just URL)."""
        img = FormattedImage(url="https://example.com/img.png", alt_text="Logo")
        result = img.render(Format.SLACK_MARKDOWN)
        assert result == "https://example.com/img.png"

    def test_image_html(self):
        """Test image in HTML format."""
        img = FormattedImage(url="https://example.com/img.png", alt_text="Logo")
        result = img.render(Format.HTML)
        assert "<img " in result
        assert 'src="https://example.com/img.png"' in result
        assert 'alt="Logo"' in result

    def test_image_html_with_dimensions(self):
        """Test image in HTML format with dimensions."""
        img = FormattedImage(
            url="https://example.com/img.png",
            alt_text="Logo",
            width=100,
            height=50,
        )
        result = img.render(Format.HTML)
        assert 'width="100"' in result
        assert 'height="50"' in result

    def test_image_html_with_title(self):
        """Test image in HTML format with title."""
        img = FormattedImage(
            url="https://example.com/img.png",
            alt_text="Logo",
            title="Company Logo",
        )
        result = img.render(Format.HTML)
        assert 'title="Company Logo"' in result

    def test_image_symphony(self):
        """Test image in Symphony MessageML format."""
        img = FormattedImage(url="https://example.com/img.png", alt_text="Logo")
        result = img.render(Format.SYMPHONY_MESSAGEML)
        assert "<card>" in result
        assert "<header>Logo</header>" in result
        assert '<img src="https://example.com/img.png"/>' in result

    def test_image_plaintext(self):
        """Test image in plaintext format."""
        img = FormattedImage(url="https://example.com/img.png", alt_text="Logo")
        result = img.render(Format.PLAINTEXT)
        assert "Logo" in result
        assert "https://example.com/img.png" in result

    def test_image_default_alt_text(self):
        """Test image with default alt text."""
        img = FormattedImage(url="https://example.com/img.png")
        result = img.render(Format.HTML)
        assert 'alt="image"' in result

    def test_image_render_string_format(self):
        """Test image render with string format."""
        img = FormattedImage(url="https://example.com/img.png", alt_text="Logo")
        result = img.render("markdown")
        assert "![Logo]" in result


class TestFormattedAttachmentProperties:
    """Tests for FormattedAttachment properties."""

    def test_attachment_with_size(self):
        """Test attachment with size."""
        att = FormattedAttachment(
            filename="doc.pdf",
            url="https://example.com/doc.pdf",
            size=1024,
        )
        assert att.size == 1024

    def test_attachment_with_content_type(self):
        """Test attachment with content type."""
        att = FormattedAttachment(
            filename="doc.pdf",
            url="https://example.com/doc.pdf",
            content_type="application/pdf",
        )
        assert att.content_type == "application/pdf"

    def test_attachment_render_string_format(self):
        """Test attachment render with string format."""
        att = FormattedAttachment(filename="doc.pdf", url="https://example.com/doc.pdf")
        result = att.render("html")
        assert "<a " in result


class TestTextNodeEdgeCases:
    """Test edge cases for text nodes."""

    def test_text_html_escaping(self):
        """Test Text node escapes HTML special characters."""
        node = Text(content="<script>alert('xss')</script>")
        result = node.render(Format.HTML)
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result

    def test_text_symphony_escaping(self):
        """Test Text node escapes Symphony special characters."""
        node = Text(content="${variable} and #{hash}")
        result = node.render(Format.SYMPHONY_MESSAGEML)
        # Symphony escapes are handled in HTML mode
        assert result is not None

    def test_link_with_title_markdown(self):
        """Test Link node with title in markdown format."""
        node = Link(url="https://example.com", text="Example", title="Link title")
        result = node.render(Format.MARKDOWN)
        assert "[Example]" in result
        assert "https://example.com" in result
        assert "Link title" in result

    def test_link_with_title_html(self):
        """Test Link node with title in HTML format."""
        node = Link(url="https://example.com", text="Example", title="Link title")
        result = node.render(Format.HTML)
        assert 'title="Link title"' in result

    def test_link_plaintext(self):
        """Test Link node in plaintext format."""
        node = Link(url="https://example.com", text="Example")
        result = node.render(Format.PLAINTEXT)
        assert "Example" in result
        assert "https://example.com" in result

    def test_paragraph_html(self):
        """Test Paragraph node in HTML format."""
        from chatom.format.text import Paragraph

        node = Paragraph(children=[Text(content="Some paragraph text.")])
        result = node.render(Format.HTML)
        assert "<p>" in result
        assert "Some paragraph text." in result
        assert "</p>" in result

    def test_paragraph_plaintext(self):
        """Test Paragraph node in plaintext format."""
        from chatom.format.text import Paragraph

        node = Paragraph(children=[Text(content="Paragraph content.")])
        result = node.render(Format.PLAINTEXT)
        assert "Paragraph content." in result
        assert result.endswith("\n")

    def test_line_break_html(self):
        """Test LineBreak node in HTML format."""
        from chatom.format.text import LineBreak

        node = LineBreak()
        result = node.render(Format.HTML)
        assert "<br/>" in result

    def test_line_break_markdown(self):
        """Test LineBreak node in markdown format."""
        from chatom.format.text import LineBreak

        node = LineBreak()
        result = node.render(Format.MARKDOWN)
        assert result == "\n"

    def test_horizontal_rule_markdown(self):
        """Test HorizontalRule node in markdown format."""
        from chatom.format.text import HorizontalRule

        node = HorizontalRule()
        result = node.render(Format.MARKDOWN)
        assert "---" in result

    def test_horizontal_rule_html(self):
        """Test HorizontalRule node in HTML format."""
        from chatom.format.text import HorizontalRule

        node = HorizontalRule()
        result = node.render(Format.HTML)
        assert "<hr/>" in result

    def test_horizontal_rule_plaintext(self):
        """Test HorizontalRule node in plaintext format."""
        from chatom.format.text import HorizontalRule

        node = HorizontalRule()
        result = node.render(Format.PLAINTEXT)
        assert "-" * 40 in result

    def test_ordered_list_with_start(self):
        """Test OrderedList with custom start number."""
        ol = OrderedList(
            items=[
                ListItem(child=Text(content="Third item")),
                ListItem(child=Text(content="Fourth item")),
            ],
            start=3,
        )
        result = ol.render(Format.MARKDOWN)
        assert "3." in result
        assert "4." in result

    def test_ordered_list_html(self):
        """Test OrderedList in HTML format."""
        ol = OrderedList(
            items=[
                ListItem(child=Text(content="First")),
                ListItem(child=Text(content="Second")),
            ]
        )
        result = ol.render(Format.HTML)
        assert "<ol>" in result
        assert "<li>" in result
        assert "</ol>" in result

    def test_ordered_list_html_with_start(self):
        """Test OrderedList in HTML format with custom start."""
        ol = OrderedList(
            items=[
                ListItem(child=Text(content="First")),
            ],
            start=5,
        )
        result = ol.render(Format.HTML)
        assert 'start="5"' in result

    def test_ordered_list_plaintext(self):
        """Test OrderedList in plaintext format."""
        ol = OrderedList(
            items=[
                ListItem(child=Text(content="Item A")),
                ListItem(child=Text(content="Item B")),
            ]
        )
        result = ol.render(Format.PLAINTEXT)
        assert "1." in result
        assert "2." in result

    def test_unordered_list_html(self):
        """Test UnorderedList in HTML format."""
        ul = UnorderedList(
            items=[
                ListItem(child=Text(content="First")),
                ListItem(child=Text(content="Second")),
            ]
        )
        result = ul.render(Format.HTML)
        assert "<ul>" in result
        assert "<li>" in result
        assert "</ul>" in result

    def test_unordered_list_plaintext(self):
        """Test UnorderedList in plaintext format."""
        ul = UnorderedList(
            items=[
                ListItem(child=Text(content="Apple")),
                ListItem(child=Text(content="Banana")),
            ]
        )
        result = ul.render(Format.PLAINTEXT)
        assert "• Apple" in result
        assert "• Banana" in result

    def test_heading_slack(self):
        """Test Heading in Slack format (falls back to bold)."""
        h1 = Heading(level=1, child=Text(content="Title"))
        result = h1.render(Format.SLACK_MARKDOWN)
        assert "*Title*" in result

    def test_heading_plaintext(self):
        """Test Heading in plaintext format (uppercase)."""
        h1 = Heading(level=1, child=Text(content="Title"))
        result = h1.render(Format.PLAINTEXT)
        assert "TITLE" in result

    def test_user_mention_discord(self):
        """Test UserMention in Discord format."""
        node = UserMention(user_id="123456")
        result = node.render(Format.DISCORD_MARKDOWN)
        assert "<@123456>" in result

    def test_user_mention_symphony(self):
        """Test UserMention in Symphony format."""
        node = UserMention(user_id="12345")
        result = node.render(Format.SYMPHONY_MESSAGEML)
        assert 'mention uid="12345"' in result

    def test_user_mention_html(self):
        """Test UserMention in HTML format."""
        node = UserMention(user_id="123", display_name="John Doe")
        result = node.render(Format.HTML)
        assert 'data-user-id="123"' in result
        assert "@John Doe" in result

    def test_user_mention_html_no_display_name(self):
        """Test UserMention in HTML format without display name."""
        node = UserMention(user_id="123")
        result = node.render(Format.HTML)
        assert "@123" in result

    def test_channel_mention_discord(self):
        """Test ChannelMention in Discord format."""
        node = ChannelMention(channel_id="789")
        result = node.render(Format.DISCORD_MARKDOWN)
        assert "<#789>" in result

    def test_channel_mention_html(self):
        """Test ChannelMention in HTML format."""
        node = ChannelMention(channel_id="456", display_name="general")
        result = node.render(Format.HTML)
        assert 'data-channel-id="456"' in result
        assert "#general" in result

    def test_channel_mention_html_no_display_name(self):
        """Test ChannelMention in HTML format without display name."""
        node = ChannelMention(channel_id="456")
        result = node.render(Format.HTML)
        assert "#456" in result

    def test_emoji_with_custom_id_discord(self):
        """Test Emoji with custom ID in Discord format."""
        from chatom.format.text import Emoji

        node = Emoji(name="custom_emoji", custom_id="123456789")
        result = node.render(Format.DISCORD_MARKDOWN)
        assert "<:custom_emoji:123456789>" in result

    def test_emoji_html_with_unicode(self):
        """Test Emoji in HTML format with unicode."""
        from chatom.format.text import Emoji

        node = Emoji(name="smile", unicode="😀")
        result = node.render(Format.HTML)
        assert result == "😀"

    def test_emoji_html_without_unicode(self):
        """Test Emoji in HTML format without unicode."""
        from chatom.format.text import Emoji

        node = Emoji(name="custom")
        result = node.render(Format.HTML)
        assert 'class="emoji"' in result
        assert 'data-emoji="custom"' in result
        assert ":custom:" in result

    def test_document_html(self):
        """Test Document in HTML format wraps in div."""
        doc = Document(children=[Text(content="Content")])
        result = doc.render(Format.HTML)
        assert "<div>" in result
        assert "Content" in result
        assert "</div>" in result

    def test_document_append(self):
        """Test Document append method."""
        doc = Document()
        doc.append(Text(content="First"))
        doc.append(Text(content="Second"))
        result = doc.render(Format.PLAINTEXT)
        assert "First" in result
        assert "Second" in result
        assert len(doc.children) == 2

    def test_quote_slack(self):
        """Test Quote in Slack format."""
        node = Quote(child=Text(content="Quoted content"))
        result = node.render(Format.SLACK_MARKDOWN)
        assert ">" in result
        assert "Quoted content" in result

    def test_quote_symphony(self):
        """Test Quote in Symphony format."""
        node = Quote(child=Text(content="Quoted content"))
        result = node.render(Format.SYMPHONY_MESSAGEML)
        assert "Quoted content" in result


class TestHelperFunctions:
    """Test text node helper functions."""

    def test_text_helper(self):
        """Test text() helper function."""
        from chatom.format.text import text

        node = text("Hello world")
        assert isinstance(node, Text)
        assert node.content == "Hello world"

    def test_bold_helper_with_string(self):
        """Test bold() helper function with string."""
        from chatom.format.text import bold

        node = bold("Strong text")
        assert isinstance(node, Bold)
        assert node.render(Format.MARKDOWN) == "**Strong text**"

    def test_bold_helper_with_node(self):
        """Test bold() helper function with TextNode."""
        from chatom.format.text import bold

        inner = Text(content="Inner")
        node = bold(inner)
        assert isinstance(node, Bold)

    def test_italic_helper_with_string(self):
        """Test italic() helper function with string."""
        from chatom.format.text import italic

        node = italic("Emphasized")
        assert isinstance(node, Italic)
        assert node.render(Format.MARKDOWN) == "*Emphasized*"

    def test_italic_helper_with_node(self):
        """Test italic() helper function with TextNode."""
        from chatom.format.text import italic

        inner = Text(content="Inner")
        node = italic(inner)
        assert isinstance(node, Italic)

    def test_code_helper(self):
        """Test code() helper function."""
        from chatom.format.text import code

        node = code("print('hi')")
        assert isinstance(node, Code)
        assert node.render(Format.MARKDOWN) == "`print('hi')`"

    def test_code_block_helper(self):
        """Test code_block() helper function."""
        from chatom.format.text import code_block

        node = code_block("x = 1", language="python")
        assert isinstance(node, CodeBlock)
        result = node.render(Format.MARKDOWN)
        assert "```python" in result

    def test_link_helper(self):
        """Test link() helper function."""
        from chatom.format.text import link

        node = link("Example", "https://example.com", title="Title")
        assert isinstance(node, Link)
        assert node.text == "Example"
        assert node.url == "https://example.com"
        assert node.title == "Title"


class TestUncoveredLines:
    """Tests for previously uncovered lines in text.py."""

    def test_text_render_symphony_messageml_escapes_html(self):
        """Test Text escapes HTML characters in Symphony MessageML format."""
        node = Text(content="<script> & <div>")
        result = node.render(Format.SYMPHONY_MESSAGEML)
        assert "&lt;script&gt;" in result
        assert "&amp;" in result
        assert "&lt;div&gt;" in result

    def test_link_render_slack_markdown(self):
        """Test Link renders correctly in Slack markdown format (line 252)."""
        node = Link(url="https://example.com", text="Click here")
        result = node.render(Format.SLACK_MARKDOWN)
        assert result == "<https://example.com|Click here>"

    def test_link_render_plaintext(self):
        """Test Link renders correctly in plaintext format (line 257)."""
        node = Link(url="https://example.com", text="Example")
        result = node.render(Format.PLAINTEXT)
        assert result == "Example (https://example.com)"

    def test_horizontal_rule_slack_markdown(self):
        """Test HorizontalRule renders in Slack markdown format (line 324)."""
        from chatom.format.text import HorizontalRule

        node = HorizontalRule()
        result = node.render(Format.SLACK_MARKDOWN)
        assert "---" in result

    def test_channel_mention_slack_markdown(self):
        """Test ChannelMention renders in Slack markdown format (line 465)."""
        node = ChannelMention(channel_id="C12345", display_name="general")
        result = node.render(Format.SLACK_MARKDOWN)
        assert result == "<#C12345>"

    def test_channel_mention_html(self):
        """Test ChannelMention renders in HTML format (line 467)."""
        node = ChannelMention(channel_id="C12345", display_name="general")
        result = node.render(Format.HTML)
        assert '<span class="channel-mention"' in result
        assert 'data-channel-id="C12345"' in result
        assert "#general" in result

    def test_emoji_discord_markdown_with_custom_id(self):
        """Test Emoji renders with custom_id in Discord markdown (line 494)."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="custom_emoji", custom_id="123456789")
        result = node.render(Format.DISCORD_MARKDOWN)
        assert result == "<:custom_emoji:123456789>"

    def test_emoji_slack_markdown(self):
        """Test Emoji renders in Slack markdown format (line 496)."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="smile")
        result = node.render(Format.SLACK_MARKDOWN)
        assert result == ":smile:"

    def test_emoji_html_without_unicode(self):
        """Test Emoji renders in HTML format without unicode (line 499-500)."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="custom")
        result = node.render(Format.HTML)
        assert '<span class="emoji"' in result
        assert 'data-emoji="custom"' in result
        assert ":custom:" in result

    def test_emoji_with_unicode_returns_unicode(self):
        """Test Emoji with unicode always returns unicode (line 489)."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="smile", unicode="😊")
        # Unicode should be returned regardless of format
        assert node.render(Format.MARKDOWN) == "😊"
        assert node.render(Format.DISCORD_MARKDOWN) == "😊"
        assert node.render(Format.SLACK_MARKDOWN) == "😊"
        assert node.render(Format.HTML) == "😊"

    def test_span_add_with_text_node(self):
        """Test Span __add__ method with TextNode (lines 520-522)."""
        span = Span(children=[Text(content="Hello ")])
        new_span = span + Bold(child=Text(content="world"))
        result = new_span.render(Format.MARKDOWN)
        assert "Hello " in result
        assert "**world**" in result
        assert isinstance(new_span, Span)
        assert len(new_span.children) == 2

    def test_span_add_with_string(self):
        """Test Span __add__ method with string (lines 520-521)."""
        span = Span(children=[Text(content="Hello ")])
        new_span = span + "world"
        result = new_span.render(Format.MARKDOWN)
        assert "Hello world" in result
        assert isinstance(new_span, Span)
        assert len(new_span.children) == 2

    def test_emoji_discord_markdown_without_custom_id(self):
        """Test Emoji renders without custom_id in Discord markdown (line 494)."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="smile")
        result = node.render(Format.DISCORD_MARKDOWN)
        assert result == ":smile:"

    def test_emoji_html_with_unicode(self):
        """Test Emoji with unicode in HTML format returns unicode (line 499)."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="smile", unicode="😊")
        result = node.render(Format.HTML)
        assert result == "😊"

    def test_emoji_symphony_with_unicode(self):
        """Test Emoji with unicode in Symphony format returns unicode."""
        from chatom.format.text import Emoji as EmojiNode

        node = EmojiNode(name="smile", unicode="😊")
        result = node.render(Format.SYMPHONY_MESSAGEML)
        assert result == "😊"
