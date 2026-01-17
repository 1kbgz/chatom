# Format System

chatom provides a powerful format system for building rich text messages that can be rendered to multiple output formats.

## Output Formats

The `Format` enum defines the available output formats:

```python
from chatom import Format

# Available formats
Format.PLAINTEXT          # Plain text with no formatting
Format.MARKDOWN           # Standard Markdown
Format.SLACK_MARKDOWN     # Slack's mrkdwn format
Format.DISCORD_MARKDOWN   # Discord-flavored Markdown
Format.HTML               # Standard HTML
Format.SYMPHONY_MESSAGEML # Symphony's XML-based format
```

## Text Nodes

Text nodes are the building blocks for formatted messages. Each node has a `render()` method that outputs the appropriate format.

### Basic Text

```python
from chatom import Text, Format

text = Text(content="Hello, world!")
print(text.render(Format.PLAINTEXT))  # "Hello, world!"
print(text.render(Format.HTML))       # "Hello, world!" (escaped)
```

### Bold

```python
from chatom import Bold, Text, Format

bold = Bold(child=Text(content="important"))
print(bold.render(Format.MARKDOWN))       # "**important**"
print(bold.render(Format.SLACK_MARKDOWN)) # "*important*"
print(bold.render(Format.HTML))           # "<strong>important</strong>"
```

### Italic

```python
from chatom import Italic, Text, Format

italic = Italic(child=Text(content="emphasized"))
print(italic.render(Format.MARKDOWN))       # "*emphasized*"
print(italic.render(Format.SLACK_MARKDOWN)) # "_emphasized_"
print(italic.render(Format.HTML))           # "<em>emphasized</em>"
```

### Strikethrough

```python
from chatom import Strikethrough, Text, Format

strike = Strikethrough(child=Text(content="deleted"))
print(strike.render(Format.MARKDOWN))       # "~~deleted~~"
print(strike.render(Format.SLACK_MARKDOWN)) # "~deleted~"
print(strike.render(Format.HTML))           # "<del>deleted</del>"
```

### Code

Inline code:

```python
from chatom import Code, Format

code = Code(content="print('hello')")
print(code.render(Format.MARKDOWN))  # "`print('hello')`"
print(code.render(Format.HTML))      # "<code>print('hello')</code>"
```

Code blocks:

```python
from chatom import CodeBlock, Format

block = CodeBlock(
    content="def hello():\n    print('Hello!')",
    language="python",
)
print(block.render(Format.MARKDOWN))
# ```python
# def hello():
#     print('Hello!')
# ```
```

### Links

```python
from chatom import Link, Format

link = Link(url="https://example.com", text="Example")
print(link.render(Format.MARKDOWN))  # "[Example](https://example.com)"
print(link.render(Format.HTML))      # '<a href="https://example.com">Example</a>'
```

### Quotes

```python
from chatom import Quote, Text, Format

quote = Quote(child=Text(content="Famous quote here"))
print(quote.render(Format.MARKDOWN))  # "> Famous quote here"
print(quote.render(Format.HTML))      # "<blockquote>Famous quote here</blockquote>"
```

### Headings

```python
from chatom import Heading, Text, Format

h1 = Heading(level=1, child=Text(content="Title"))
h2 = Heading(level=2, child=Text(content="Subtitle"))

print(h1.render(Format.MARKDOWN))  # "# Title"
print(h2.render(Format.MARKDOWN))  # "## Subtitle"
print(h1.render(Format.HTML))      # "<h1>Title</h1>"
```

### Lists

Unordered lists:

```python
from chatom import UnorderedList, ListItem, Text, Format

ul = UnorderedList(items=[
    ListItem(child=Text(content="First item")),
    ListItem(child=Text(content="Second item")),
    ListItem(child=Text(content="Third item")),
])
print(ul.render(Format.MARKDOWN))
# - First item
# - Second item
# - Third item
```

Ordered lists:

```python
from chatom import OrderedList, ListItem, Text, Format

ol = OrderedList(items=[
    ListItem(child=Text(content="Step one")),
    ListItem(child=Text(content="Step two")),
    ListItem(child=Text(content="Step three")),
])
print(ol.render(Format.MARKDOWN))
# 1. Step one
# 2. Step two
# 3. Step three
```

### Paragraphs and Documents

```python
from chatom import Paragraph, Document, Text, Bold, Format

doc = Document(children=[
    Paragraph(children=[
        Text(content="First paragraph with "),
        Bold(child=Text(content="bold")),
        Text(content=" text."),
    ]),
    Paragraph(children=[
        Text(content="Second paragraph."),
    ]),
])

print(doc.render(Format.MARKDOWN))
print(doc.render(Format.HTML))
```

## Tables

Tables are a powerful feature for displaying structured data:

```python
from chatom import Table, TableRow, TableCell, Format

# Create manually
headers = TableRow(cells=[
    TableCell(content="Name"),
    TableCell(content="Score"),
])
rows = [
    TableRow(cells=[TableCell(content="Alice"), TableCell(content="100")]),
    TableRow(cells=[TableCell(content="Bob"), TableCell(content="85")]),
]
table = Table(headers=headers, rows=rows)

# Or create from data
data = [
    ["Alice", "100"],
    ["Bob", "85"],
]
table = Table.from_data(data, headers=["Name", "Score"])

# Render
print(table.render(Format.MARKDOWN))
# | Name | Score |
# |---|---|
# | Alice | 100 |
# | Bob | 85 |

print(table.render(Format.HTML))
# <table>
#   <thead><tr><th>Name</th><th>Score</th></tr></thead>
#   <tbody>
#     <tr><td>Alice</td><td>100</td></tr>
#     <tr><td>Bob</td><td>85</td></tr>
#   </tbody>
# </table>
```

## Mentions

### User Mentions

```python
from chatom import UserMention, Format

mention = UserMention(user_id="123", display_name="Alice")
print(mention.render(Format.PLAINTEXT))      # "@Alice"
print(mention.render(Format.SLACK_MARKDOWN)) # "<@123>"
print(mention.render(Format.DISCORD_MARKDOWN)) # "<@123>"
```

### Channel Mentions

```python
from chatom import ChannelMention, Format

mention = ChannelMention(channel_id="456", channel_name="general")
print(mention.render(Format.PLAINTEXT))      # "#general"
print(mention.render(Format.SLACK_MARKDOWN)) # "<#456>"
```

## FormattedMessage

The `FormattedMessage` class wraps content nodes for easy rendering:

```python
from chatom import FormattedMessage, Paragraph, Text, Bold, Format

msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Text(content="Welcome to "),
            Bold(child=Text(content="chatom")),
            Text(content="!"),
        ]),
    ]
)

# Render to any format
markdown = msg.render(Format.MARKDOWN)
html = msg.render(Format.HTML)
plaintext = msg.render(Format.PLAINTEXT)
slack = msg.render(Format.SLACK_MARKDOWN)
symphony = msg.render(Format.SYMPHONY_MESSAGEML)

# Render for a specific backend
slack_output = msg.render_for("slack")
discord_output = msg.render_for("discord")
```

## Message Conversion

Messages from any backend can be converted to and from `FormattedMessage`, enabling cross-platform message rendering.

### Converting Messages to FormattedMessage

All backend-specific message classes have a `to_formatted()` method:

```python
from chatom.slack import SlackMessage
from chatom.discord import DiscordMessage
from chatom.format import Format

# Slack message
slack_msg = SlackMessage(
    ts="1234567890.123456",
    channel="C12345",
    text="Hello *bold* and _italic_",
)
formatted = slack_msg.to_formatted()

# Now render for any other backend
discord_output = formatted.render(Format.DISCORD_MARKDOWN)
html_output = formatted.render(Format.HTML)
symphony_output = formatted.render(Format.SYMPHONY_MESSAGEML)
```

### Creating Messages from FormattedMessage

Use `from_formatted()` to create backend-specific messages:

```python
from chatom.format import MessageBuilder
from chatom.slack import SlackMessage
from chatom.discord import DiscordMessage
from chatom.symphony import SymphonyMessage

# Build a formatted message
fm = (
    MessageBuilder()
    .bold("Alert")
    .text(": Check out this ")
    .link("link", "https://example.com")
    .text("!")
    .build()
)

# Create backend-specific messages
slack_msg = SlackMessage.from_formatted(fm, channel="C12345")
discord_msg = DiscordMessage.from_formatted(fm, channel_id="D12345")
symphony_msg = SymphonyMessage.from_formatted(fm, stream_id="stream_xyz")

print(slack_msg.text)       # "*Alert*: Check out this <https://example.com|link>!"
print(discord_msg.content)  # "**Alert**: Check out this [link](https://example.com)!"
print(symphony_msg.message_ml)  # MessageML formatted
```

### Cross-Platform Message Conversion

Convert a message from one platform to another:

```python
from chatom.slack import SlackMessage
from chatom.discord import DiscordMessage

# Incoming Slack message
slack_msg = SlackMessage.from_api_response(slack_api_data)

# Convert to FormattedMessage
formatted = slack_msg.to_formatted()

# Create Discord message
discord_msg = DiscordMessage.from_formatted(
    formatted,
    channel_id="target_channel",
)

# The Discord message now has proper Discord formatting
await discord_channel.send(discord_msg.content)
```

### Metadata Preservation

When converting messages, metadata is preserved:

```python
from chatom.slack import SlackMessage

slack_msg = SlackMessage(
    ts="1234567890.123456",
    channel="C12345",
    user="U12345",
    text="Hello!",
    thread_ts="1234567890.000000",
)

formatted = slack_msg.to_formatted()

# Metadata includes source information
print(formatted.metadata["source_backend"])  # "slack"
print(formatted.metadata["ts"])              # "1234567890.123456"
print(formatted.metadata["author_id"])       # "U12345"
print(formatted.metadata["thread_ts"])       # "1234567890.000000"
```

## MessageBuilder

For a fluent API, use `MessageBuilder`:

```python
from chatom import MessageBuilder, Format

msg = (
    MessageBuilder()
    .add_text("Hello, ")
    .add_bold("world")
    .add_text("!")
    .build()
)

print(msg.render(Format.MARKDOWN))  # "Hello, **world**!"
```

## Utility Functions

### render_message

```python
from chatom import render_message, FormattedMessage, Text, Format

msg = FormattedMessage(content=[Text(content="Hello")])
result = render_message(msg, Format.MARKDOWN)
```

### format_message

For simple text escaping:

```python
from chatom import format_message, Format

# Escape for HTML
text = format_message("<script>alert('xss')</script>", Format.HTML)
# "&lt;script&gt;alert('xss')&lt;/script&gt;"
```

## Format Comparison

| Node | Plaintext | Markdown | Slack | Discord | HTML | Symphony |
|------|-----------|----------|-------|---------|------|----------|
| Bold | text | `**text**` | `*text*` | `**text**` | `<strong>` | `<b>` |
| Italic | text | `*text*` | `_text_` | `*text*` | `<em>` | `<i>` |
| Strike | text | `~~text~~` | `~text~` | `~~text~~` | `<del>` | `<s>` |
| Code | text | `` `text` `` | `` `text` `` | `` `text` `` | `<code>` | `<code>` |
| Link | url | `[t](url)` | `<url\|t>` | `[t](url)` | `<a>` | `<a>` |
| Quote | text | `> text` | `> text` | `> text` | `<blockquote>` | `<quote>` |
