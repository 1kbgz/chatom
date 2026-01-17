# Messaging Guide

This guide covers reading and writing messages across different backends,
including parsing incoming messages and formatting outgoing messages.

## Reading Messages

### Fetching Message History

All backends support fetching historical messages from channels:

```python
from chatom.slack import SlackBackend, SlackConfig

backend = SlackBackend(config=SlackConfig(bot_token="xoxb-..."))
await backend.connect()

# Fetch the last 50 messages
messages = await backend.fetch_messages("C123456", limit=50)

for message in messages:
    print(f"[{message.timestamp}] {message.author.name}: {message.content}")
```

### Message Properties

Each message has standard properties:

```python
message.id           # Unique message identifier
message.content      # Raw message content/text
message.timestamp    # When the message was sent (datetime)
message.user_id      # ID of the user who sent it
message.channel_id   # ID of the channel/room
message.author       # User object (if available)
message.channel      # Channel object (if available)
message.reactions    # List of reactions
message.attachments  # List of attachments
message.embeds       # List of embeds (Discord, Slack)
message.thread_id    # Thread ID (if in a thread)
message.reply_to     # Message this replies to
```

### Pagination

For large channels, use pagination to fetch older messages:

```python
# Fetch initial messages
messages = await backend.fetch_messages("C123456", limit=100)

# Fetch older messages (before the oldest message we have)
if messages:
    older = await backend.fetch_messages(
        "C123456",
        limit=100,
        before=messages[0].id  # ID of oldest message
    )

# Fetch newer messages (after a specific message)
newer = await backend.fetch_messages(
    "C123456",
    limit=100,
    after=some_message_id
)
```

### Backend-Specific Notes

| Backend | History Support | Pagination | Notes |
|---------|-----------------|------------|-------|
| Discord | ✅ | By message ID | Limit 1-100 per request |
| Slack | ✅ | By timestamp | Uses `conversations.history` API |
| Symphony | ✅ | By message ID | Uses stream ID |
| Matrix | ✅ | By event token | Uses sync tokens |
| Email | ✅ | By date/ID | Via IMAP |
| IRC | ❌ | N/A | No history without a bouncer |

---

## Writing Messages

### Basic Message Sending

```python
# Send a simple text message
await backend.send_message("channel_id", "Hello, world!")

# Sync version
backend.sync.send_message("channel_id", "Hello, world!")
```

### Message Return Value

`send_message` returns the sent message:

```python
sent = await backend.send_message("C123456", "Hello!")
print(f"Message sent with ID: {sent.id}")
print(f"Sent at: {sent.timestamp}")
```

### Editing Messages

```python
# Edit an existing message
edited = await backend.edit_message(
    channel_id="C123456",
    message_id="msg_id",
    content="Updated content",
)
```

### Deleting Messages

```python
# Delete a message
await backend.delete_message(
    channel_id="C123456",
    message_id="msg_id",
)
```

---

## Formatting Messages

### Using the Format System

chatom provides a rich text formatting system that renders to platform-specific formats:

```python
from chatom import (
    Format,
    FormattedMessage,
    Paragraph,
    Text,
    Bold,
    Italic,
    Strikethrough,
    Code,
    CodeBlock,
    Link,
)

# Build a formatted message
msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Text(content="Hello, "),
            Bold(child=Text(content="world")),
            Text(content="! This is "),
            Italic(child=Text(content="important")),
            Text(content="."),
        ]),
    ]
)

# Render for different platforms
plaintext = msg.render(Format.PLAINTEXT)    # "Hello, world! This is important.\n"
markdown = msg.render(Format.MARKDOWN)       # "Hello, **world**! This is *important*.\n"
slack = msg.render(Format.SLACK_MARKDOWN)   # "Hello, *world*! This is _important_.\n"
discord = msg.render(Format.DISCORD_MARKDOWN)
html = msg.render(Format.HTML)              # "<p>Hello, <strong>world</strong>!..."
symphony = msg.render(Format.SYMPHONY_MESSAGEML)

# Send with appropriate format
await backend.send_message("channel_id", msg.render(backend.format))
```

### Using Backend's Format

Each backend has a preferred format. Use it automatically:

```python
from chatom.slack import SlackBackend

backend = SlackBackend(...)

# backend.format is Format.SLACK_MARKDOWN
content = msg.render(backend.format)
await backend.send_message("C123456", content)
```

### Available Formats

| Format | Backend | Example Bold | Example Italic |
|--------|---------|--------------|----------------|
| `PLAINTEXT` | All | `word` | `word` |
| `MARKDOWN` | General | `**word**` | `*word*` |
| `SLACK_MARKDOWN` | Slack | `*word*` | `_word_` |
| `DISCORD_MARKDOWN` | Discord | `**word**` | `*word*` |
| `HTML` | Email, Web | `<strong>word</strong>` | `<em>word</em>` |
| `SYMPHONY_MESSAGEML` | Symphony | `<b>word</b>` | `<i>word</i>` |

### Text Formatting Elements

#### Bold, Italic, Strikethrough

```python
from chatom import Bold, Italic, Strikethrough, Text, Format

bold = Bold(child=Text(content="important"))
italic = Italic(child=Text(content="emphasized"))
strike = Strikethrough(child=Text(content="deleted"))

# Combine them
combined = Bold(child=Italic(child=Text(content="both")))
print(combined.render(Format.MARKDOWN))  # "***both***"
```

#### Code

```python
from chatom import Code, CodeBlock, Format

# Inline code
inline = Code(content="print('hello')")
print(inline.render(Format.MARKDOWN))  # "`print('hello')`"

# Code block with syntax highlighting
block = CodeBlock(
    content="def hello():\n    return 'Hello!'",
    language="python",
)
print(block.render(Format.MARKDOWN))
# ```python
# def hello():
#     return 'Hello!'
# ```
```

#### Links

```python
from chatom import Link, Format

link = Link(url="https://example.com", text="Click here")
print(link.render(Format.MARKDOWN))       # "[Click here](https://example.com)"
print(link.render(Format.SLACK_MARKDOWN)) # "<https://example.com|Click here>"
print(link.render(Format.HTML))           # '<a href="https://example.com">Click here</a>'
```

#### Lists

```python
from chatom import UnorderedList, OrderedList, ListItem, Text, Format

# Unordered list
ul = UnorderedList(items=[
    ListItem(content=Text(content="First item")),
    ListItem(content=Text(content="Second item")),
])
print(ul.render(Format.MARKDOWN))
# - First item
# - Second item

# Ordered list
ol = OrderedList(items=[
    ListItem(content=Text(content="Step one")),
    ListItem(content=Text(content="Step two")),
])
print(ol.render(Format.MARKDOWN))
# 1. Step one
# 2. Step two
```

#### Blockquotes

```python
from chatom import Blockquote, Text, Format

quote = Blockquote(child=Text(content="This is a quote"))
print(quote.render(Format.MARKDOWN))       # "> This is a quote"
print(quote.render(Format.SLACK_MARKDOWN)) # "> This is a quote"
print(quote.render(Format.HTML))           # "<blockquote>This is a quote</blockquote>"
```

### Tables

```python
from chatom import Table, Format

# Create from data
data = [
    ["Alice", "100", "Gold"],
    ["Bob", "85", "Silver"],
    ["Carol", "70", "Bronze"],
]
table = Table.from_data(data, headers=["Name", "Score", "Medal"])

print(table.render(Format.MARKDOWN))
# | Name | Score | Medal |
# |------|-------|-------|
# | Alice | 100 | Gold |
# | Bob | 85 | Silver |
# | Carol | 70 | Bronze |

print(table.render(Format.PLAINTEXT))
# Name    Score   Medal
# Alice   100     Gold
# Bob     85      Silver
# Carol   70      Bronze
```

---

## Platform-Specific Formatting

### Discord

Discord uses a Markdown variant:

```python
from chatom import Format

msg = FormattedMessage(content=[...])
content = msg.render(Format.DISCORD_MARKDOWN)

# Discord-specific: spoiler tags
spoiler_text = "||This is a spoiler||"

# Discord-specific: timestamps
timestamp = f"<t:{int(datetime.now().timestamp())}:R>"  # Relative time
```

### Slack

Slack uses mrkdwn format:

```python
from chatom import Format

content = msg.render(Format.SLACK_MARKDOWN)

# Slack-specific: emoji shortcodes
emoji = ":wave: :rocket:"

# Slack-specific: date formatting
date_str = f"<!date^{timestamp}^{{date_short}} at {{time}}|fallback>"
```

### Symphony

Symphony uses MessageML (XML-based):

```python
from chatom import Format

content = msg.render(Format.SYMPHONY_MESSAGEML)
# Result: <messageML><p>Hello <b>world</b>!</p></messageML>

# Symphony-specific: structured elements
form = """
<messageML>
    <form id="my-form">
        <text-field name="input" placeholder="Enter text"/>
        <button name="submit" type="action">Submit</button>
    </form>
</messageML>
"""
```

### Email (HTML)

Email typically uses HTML:

```python
from chatom import Format

content = msg.render(Format.HTML)

# Full HTML email with styling
html_email = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    {content}
    <hr>
    <p style="color: gray; font-size: 12px;">
        Sent via My Bot
    </p>
</body>
</html>
"""
```

---

## Parsing Incoming Messages

### Extracting Content

```python
# Get the raw content
content = message.content

# Check for specific patterns
if "help" in content.lower():
    await send_help_message(channel_id)

# Use regex for more complex patterns
import re
match = re.search(r'remind me in (\d+) minutes? to (.+)', content)
if match:
    minutes = int(match.group(1))
    task = match.group(2)
```

### Parsing Mentions in Messages

See the [Mentions Guide](mentions.md) for detailed information on parsing
mentions in incoming messages.

```python
from chatom import parse_mentions, MentionMatch

# Parse all mentions in a message
mentions = parse_mentions(message.content, backend.name)

for mention in mentions:
    if mention.type == "user":
        user = await backend.fetch_user(mention.id)
        print(f"Mentioned user: {user.name}")
    elif mention.type == "channel":
        channel = await backend.fetch_channel(mention.id)
        print(f"Mentioned channel: {channel.name}")
```

### Handling Attachments

```python
for attachment in message.attachments:
    print(f"Attachment: {attachment.filename}")
    print(f"Type: {attachment.content_type}")
    print(f"Size: {attachment.size} bytes")
    print(f"URL: {attachment.url}")
```

### Handling Reactions

```python
for reaction in message.reactions:
    print(f"Emoji: {reaction.emoji.name}")
    print(f"Count: {reaction.count}")
```

---

## Complete Example: Echo Bot

A complete example that reads messages and responds with formatted replies:

```python
import asyncio
from chatom import FormattedMessage, Paragraph, Bold, Italic, Text, Format
from chatom.slack import SlackBackend, SlackConfig

async def run_echo_bot():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)

    await backend.connect()
    print("Echo bot connected!")

    # In a real bot, you'd use event handlers
    # This is a simplified polling example

    channel_id = "C123456"
    last_message_id = None

    while True:
        # Fetch new messages
        messages = await backend.fetch_messages(
            channel_id,
            limit=10,
            after=last_message_id,
        )

        for message in messages:
            last_message_id = message.id

            # Skip our own messages
            if message.author and message.author.is_bot:
                continue

            # Echo the message with formatting
            response = FormattedMessage(
                content=[
                    Paragraph(children=[
                        Text(content="You said: "),
                        Italic(child=Text(content=message.content or "")),
                    ]),
                ]
            )

            # Send in Slack format
            await backend.send_message(
                channel_id,
                response.render(Format.SLACK_MARKDOWN),
            )

        await asyncio.sleep(2)  # Poll every 2 seconds

asyncio.run(run_echo_bot())
```

---

## Next Steps

- Learn about [User and Channel Mentions](mentions.md)
- Explore [Attachments and Embeds](advanced-features.md#attachments)
- See backend-specific examples in [Backend Examples](backend-examples.md)
