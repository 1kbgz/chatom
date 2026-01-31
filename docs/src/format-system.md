# Format System

The format system provides a unified way to create rich text that renders correctly on each platform.

## Overview

Each platform has its own markup syntax:
- **Slack** uses `mrkdwn` (similar to Markdown with some differences)
- **Discord** uses Discord-flavored Markdown
- **Symphony** uses MessageML (XML-based)

The format system lets you write once and render for any platform.

## FormattedMessage

The primary way to create formatted content:

```python
from chatom.format import FormattedMessage, Format

msg = FormattedMessage()
msg.bold("Important!")
msg.text(" This is a message with ")
msg.italic("formatting")
msg.text(".")

# Render for different platforms
slack_content = msg.render(Format.SLACK_MARKDOWN)
discord_content = msg.render(Format.DISCORD_MARKDOWN)
symphony_content = msg.render(Format.SYMPHONY_MESSAGEML)

# Or use the backend's format
content = msg.render(backend.get_format())
```

## Available Formats

| Format | Constant | Used By |
|--------|----------|---------|
| Plain Text | `Format.PLAINTEXT` | Fallback |
| Markdown | `Format.MARKDOWN` | Generic |
| Slack mrkdwn | `Format.SLACK_MARKDOWN` | Slack |
| Discord Markdown | `Format.DISCORD_MARKDOWN` | Discord |
| Symphony MessageML | `Format.SYMPHONY_MESSAGEML` | Symphony |
| HTML | `Format.HTML` | Web views |

## Text Formatting

### Basic Styles

```python
msg = FormattedMessage()

# Bold
msg.bold("Bold text")

# Italic
msg.italic("Italic text")

# Strikethrough
msg.strikethrough("Deleted text")

# Underline (where supported)
msg.underline("Underlined")

# Combine styles
msg.bold("Bold and ")
msg.bold_italic("bold italic")
```

### Code

```python
msg = FormattedMessage()

# Inline code
msg.code("inline_code")

# Code block
msg.code_block("""
def hello():
    print("Hello, World!")
""", language="python")
```

### Links

```python
msg = FormattedMessage()

# Simple link
msg.link("https://example.com", "Click here")

# Auto-link (URL as text)
msg.link("https://example.com")
```

## Structure

### Headings

```python
msg = FormattedMessage()

msg.heading("Main Title", level=1)
msg.heading("Section", level=2)
msg.heading("Subsection", level=3)
```

### Paragraphs and Line Breaks

```python
msg = FormattedMessage()

msg.paragraph("First paragraph.")
msg.paragraph("Second paragraph.")

# Or use explicit newlines
msg.text("Line 1")
msg.newline()
msg.text("Line 2")
```

### Blockquotes

```python
msg = FormattedMessage()

msg.quote("This is quoted text.")
msg.quote("Multi-line quotes\nwork too.")
```

### Horizontal Rules

```python
msg = FormattedMessage()

msg.text("Above the line")
msg.horizontal_rule()
msg.text("Below the line")
```

## Lists

### Unordered Lists

```python
msg = FormattedMessage()

msg.unordered_list([
    "First item",
    "Second item",
    "Third item",
])
```

### Ordered Lists

```python
msg = FormattedMessage()

msg.ordered_list([
    "Step one",
    "Step two",
    "Step three",
])
```

### Nested Lists

```python
msg = FormattedMessage()

msg.text("Features:")
msg.unordered_list([
    "Platform support",
    "Rich formatting",
    "Easy to use",
])
```

## Tables

Tables render appropriately for each platform:

```python
from chatom.format import FormattedMessage, Table

msg = FormattedMessage()

# Create a table
table = Table.from_data(
    headers=["Name", "Status", "Count"],
    data=[
        ["Server 1", "Online", "42"],
        ["Server 2", "Offline", "0"],
        ["Server 3", "Online", "128"],
    ],
    caption="Server Status",
)

msg.table(table)
```

### Table Alignment

```python
from chatom.format import Table, TableAlignment

table = Table.from_data(
    headers=["Left", "Center", "Right"],
    data=[
        ["text", "text", "123"],
        ["more", "more", "456"],
    ],
    alignments=[
        TableAlignment.LEFT,
        TableAlignment.CENTER,
        TableAlignment.RIGHT,
    ],
)
```

### Complex Tables

```python
from chatom.format import Table, TableRow, TableCell

# Create with TableRow/TableCell for more control
table = Table(
    headers=TableRow.from_values(["Col A", "Col B"], is_header=True),
    rows=[
        TableRow.from_values(["Value 1", "Value 2"]),
        TableRow(cells=[
            TableCell(content="Spanning cell", colspan=2),
        ]),
    ],
)
```

## Mentions

### User Mentions

```python
from chatom.format import FormattedMessage
from chatom import User

msg = FormattedMessage()

# Mention using User object (recommended)
user = User(id="U123456", name="Alice")
msg.mention(user)

# Mention using ID only
msg.user_mention("U123456")
```

### Channel Mentions

```python
from chatom.format import FormattedMessage
from chatom import Channel

msg = FormattedMessage()

# Mention using Channel object (recommended)
channel = Channel(id="C123456", name="general")
msg.channel_mention(channel)
```

### Platform-Specific Mentions

Some platforms have special mentions:

```python
# Slack
from chatom.slack import mention_here, mention_channel_all, mention_everyone

msg.text(mention_here())  # @here
msg.text(mention_channel_all())  # @channel
msg.text(mention_everyone())  # @everyone

# Discord
from chatom.discord import mention_everyone, mention_here, mention_role

msg.text(mention_everyone())  # @everyone
msg.text(mention_here())  # @here
msg.text(mention_role("role_id"))  # @role
```

## Complete Example

```python
from chatom.format import FormattedMessage, Table, Format
from chatom import User, Channel

def create_status_report(users: list, channel: Channel) -> FormattedMessage:
    msg = FormattedMessage()

    # Header
    msg.heading("📊 Daily Status Report", level=2)
    msg.paragraph("Here's the summary for today:")
    msg.newline()

    # Status table
    table = Table.from_data(
        headers=["User", "Tasks", "Status"],
        data=[
            [u.name, str(u.metadata.get("tasks", 0)), "✅"]
            for u in users
        ],
    )
    msg.table(table)
    msg.newline()

    # Footer
    msg.text("Posted to ")
    msg.channel_mention(channel)
    msg.text(" • ")
    msg.italic("Updated hourly")

    return msg

# Use it
report = create_status_report(users, channel)
content = report.render(backend.get_format())
await backend.send_message(channel_id=channel.id, content=content)
```

## Rendering for Specific Backends

```python
msg = FormattedMessage()
msg.bold("Hello")

# For Slack
# Output: *Hello*
slack = msg.render(Format.SLACK_MARKDOWN)

# For Discord
# Output: **Hello**
discord = msg.render(Format.DISCORD_MARKDOWN)

# For Symphony
# Output: <b>Hello</b>
symphony = msg.render(Format.SYMPHONY_MESSAGEML)

# Using backend
content = msg.render(backend.get_format())
```

## Text Nodes (Advanced)

For complex formatting, use text nodes directly:

```python
from chatom.format import (
    Document, Paragraph, Bold, Italic, Code,
    Link, UnorderedList, ListItem, text, bold, italic
)

# Create a document
doc = Document(children=[
    Paragraph(children=[
        text("This is "),
        bold("bold"),
        text(" and "),
        italic("italic"),
        text("."),
    ]),
    UnorderedList(children=[
        ListItem(children=[text("Item 1")]),
        ListItem(children=[text("Item 2")]),
    ]),
])

# Render
content = doc.render(Format.MARKDOWN)
```

## Next Steps

- [Mentions](mentions.md) - Detailed mention guide
- [Messaging](messaging.md) - Sending formatted messages
- [Examples](examples.md) - Complete examples
