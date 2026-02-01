# Messaging

This guide covers all aspects of sending, receiving, and managing messages.

## Sending Messages

### Basic Message

```python
message = await backend.send_message(
    channel_id="C123456",
    content="Hello, world!",
)

print(f"Sent: {message.id}")
```

### Formatted Message

```python
from chatom.format import FormattedMessage

msg = FormattedMessage()
msg.bold("Important:")
msg.text(" Please read this.")

content = msg.render(backend.get_format())
message = await backend.send_message(
    channel_id=channel.id,
    content=content,
)
```

### Send to Channel by Name

```python
# Look up channel first
channel = await backend.fetch_channel(name="general")

# Then send
message = await backend.send_message(
    channel_id=channel.id,
    content="Hello!",
)
```

## Reading Messages

### Message History

```python
# Read last 50 messages
async for message in backend.read_messages(channel_id="C123456", limit=50):
    author = message.author.name if message.author else "Unknown"
    print(f"{author}: {message.content}")
```

### With Pagination

```python
# Read in batches
messages = []
async for message in backend.read_messages(channel_id="C123456", limit=100):
    messages.append(message)

    # Process in batches of 20
    if len(messages) >= 20:
        process_batch(messages)
        messages = []

# Process remaining
if messages:
    process_batch(messages)
```

### Since a Specific Time

```python
from datetime import datetime, timedelta

# Read messages from last hour
since = datetime.now() - timedelta(hours=1)

async for message in backend.read_messages(
    channel_id="C123456",
    after=since,
    limit=100,
):
    print(message.content)
```

## Threads

### Create a Thread

```python
# Send parent message
parent = await backend.send_message(
    channel_id="C123456",
    content="📋 Discussion Topic: New Feature",
)

# Reply in thread
reply = await backend.reply_to_message(
    channel_id="C123456",
    message_id=parent.id,
    content="I think we should...",
)
```

### Multiple Replies

```python
# Send several replies
for i, point in enumerate(discussion_points):
    await backend.reply_to_message(
        channel_id="C123456",
        message_id=parent.id,
        content=f"{i+1}. {point}",
    )
```

### Read Thread Messages

```python
# Read all messages in a thread
async for message in backend.read_thread(
    channel=channel,
    thread=parent_message,
    limit=50,
):
    print(f"{message.author.name}: {message.content}")
```

## Direct Messages

### Create DM Channel

```python
# Find user
user = await backend.fetch_user(name="Alice")

# Create/open DM channel
dm_channel_id = await backend.create_dm([user.id])

# Send message
await backend.send_message(
    channel=dm_channel_id,
    content="Hello! This is a private message.",
)
```

### Convenience Method

```python
# Send DM directly
message = await backend.send_dm(
    user=user,
    content="Quick question for you!",
)
```

## Reactions

### Add Reaction

```python
await backend.add_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="thumbsup",  # emoji name without colons
)
```

### Multiple Reactions

```python
emojis = ["thumbsup", "rocket", "heart"]

for emoji in emojis:
    await backend.add_reaction(
        channel_id="C123456",
        message_id="M789",
        emoji=emoji,
    )
```

### Remove Reaction

```python
await backend.remove_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="thumbsup",
)
```

### Unicode Emojis (Discord)

```python
# Discord accepts unicode directly
await backend.add_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="👍",
)
```

## Editing Messages

```python
# Send initial message
message = await backend.send_message(
    channel_id="C123456",
    content="Processing...",
)

# Do some work...
await asyncio.sleep(2)

# Update the message
await backend.edit_message(
    channel_id="C123456",
    message_id=message.id,
    content="Processing... Done! ✅",
)
```

## Deleting Messages

```python
await backend.delete_message(
    channel_id="C123456",
    message_id="M789",
)
```

## Forwarding Messages

```python
# Forward a message to another channel
await backend.forward_message(
    message=original_message,
    target_channel_id="C789",
)
```

## Listening for Messages

### Real-time Events

```python
async for message in backend.listen():
    print(f"New message: {message.content}")

    # Respond to mentions
    if message.mentions_user(backend.bot_user_id):
        await backend.reply_to_message(
            channel_id=message.channel_id,
            message_id=message.id,
            content="You mentioned me!",
        )
```

### With Timeout

```python
import asyncio

async def listen_with_timeout(backend, timeout=60):
    try:
        async with asyncio.timeout(timeout):
            async for message in backend.listen():
                yield message
    except asyncio.TimeoutError:
        print("Listener timed out")
```

## Message Objects

### Properties

```python
message = await backend.send_message(channel_id, content)

# Basic info
message.id          # Unique identifier
message.content     # Text content
message.created_at  # When sent
message.edited_at   # When last edited (if any)

# Author
message.author      # User object
message.author_id   # User ID string

# Channel
message.channel     # Channel object
message.channel_id  # Channel ID string

# Threading
message.thread_id   # Parent thread ID
message.reply_to_id # Message being replied to

# Rich content
message.reactions   # List of Reaction objects
message.attachments # List of Attachment objects
message.embeds      # List of Embed objects
```

### Detecting Mentions

```python
# Get all mentioned user IDs
user_ids = message.get_mentioned_user_ids()

# Get all mentioned channel IDs
channel_ids = message.get_mentioned_channel_ids()

# Check if specific user is mentioned
if message.mentions_user("U123456"):
    print("User was mentioned!")
```

### Response Convenience Methods

Messages have convenience methods that construct new Message instances. This makes it easy to create replies, forwards, or quotes:

#### `as_reply(content, **kwargs)`

Create a new message as a reply to this message:

```python
async for message in backend.listen():
    if "help" in message.content.lower():
        # Create a reply message
        reply = message.as_reply("I can help with that!")
        # reply.reply_to is message
        # reply.message_type is MessageType.REPLY
```

#### `as_thread_reply(content, **kwargs)`

Create a reply within the existing thread (or create one if not in a thread):

```python
# If message is in a thread, new message is in that thread
# Otherwise, a new thread is created from this message
reply = message.as_thread_reply("Following up on this...")
# reply.thread is set appropriately
```

#### `as_forward(target_channel, **kwargs)`

Create a forwarded message to another channel with attribution:

```python
# Forward to moderation channel
forward = message.as_forward(mod_channel)
# forward.forwarded_from is message
# forward.message_type is MessageType.FORWARD
# forward.content includes "[Forwarded from Alice in #general]\nOriginal content..."
```

#### `as_quote_reply(content, **kwargs)`

Create a reply that quotes the original message:

```python
quote = message.as_quote_reply("I agree with this!")
# quote.content is "> Original message\n\nI agree with this!"
```

#### `reply_context()`

Get context information for custom reply handling:

```python
ctx = message.reply_context()
# Returns: {
#   "channel": Channel(...),
#   "message": Message(...),
#   "thread": Thread(...) or None,
#   "author": User(...),
# }

# Use for custom logic
new_msg = Message(
    channel=ctx["channel"],
    content=f"Replying to {ctx['message'].author_name}",
    reply_to=ctx["message"],
)
```

### Complete Response Bot Example

```python
async for message in backend.listen():
    content = message.content.lower()

    if "!help" in content:
        # Create a reply
        reply = message.as_reply("Available commands: !help, !forward")
        # ... send via your preferred method

    elif "!forward" in content:
        # Forward to log channel
        forward = message.as_forward(log_channel)
        # forward.forwarded_from is message

    elif "!quote" in content:
        # Quote and respond
        quote = message.as_quote_reply("Acknowledged! ✅")
```
```

## Error Handling

```python
try:
    message = await backend.send_message(
        channel_id="C123456",
        content="Hello!",
    )
except Exception as e:
    print(f"Failed to send message: {e}")
```

## Complete Example: Notification Bot

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig
from chatom.format import FormattedMessage, Table

async def daily_report():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)
    await backend.connect()

    try:
        # Get channel
        channel = await backend.fetch_channel(name="reports")

        # Create formatted report
        msg = FormattedMessage()
        msg.heading("📊 Daily Report", level=2)
        msg.paragraph(f"Report generated at {datetime.now()}")

        # Add table
        table = Table.from_data(
            headers=["Metric", "Value", "Change"],
            data=[
                ["Users", "1,234", "+5%"],
                ["Revenue", "$45,678", "+12%"],
                ["Errors", "23", "-8%"],
            ],
        )
        msg.table(table)

        # Send report
        content = msg.render(backend.get_format())
        report_msg = await backend.send_message(
            channel_id=channel.id,
            content=content,
        )

        # Add reaction to indicate success
        await backend.add_reaction(
            channel_id=channel.id,
            message_id=report_msg.id,
            emoji="white_check_mark",
        )

    finally:
        await backend.disconnect()

asyncio.run(daily_report())
```

## Next Steps

- [Format System](format-system.md) - Rich text formatting
- [Mentions](mentions.md) - User and channel mentions
- [Examples](examples.md) - Complete example applications
