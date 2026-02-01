# Base Models

Chatom provides type-safe models for all chat concepts. These models are platform-agnostic and can be converted to/from backend-specific formats.

## User

The `User` model represents a chat platform user.

```python
from chatom import User

# Create a user with various identifiers
user = User(
    id="U123456",
    name="Alice Smith",
    handle="alice.smith",
    email="alice@example.com",
    avatar_url="https://example.com/avatar.png",
)

# Access computed properties
print(user.display_name)  # "Alice Smith"
print(user.mention_name)  # "alice.smith"
```

### User Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Display name |
| `handle` | `str` | Username/handle |
| `email` | `str` | Email address |
| `avatar_url` | `str` | Profile picture URL |
| `is_bot` | `bool` | Whether user is a bot |
| `metadata` | `dict` | Platform-specific data |

### Incomplete Users

Users from message events may be incomplete (only have ID):

```python
# User from a message event - only has ID
incomplete_user = User(id="U123456", is_incomplete=True)

# Resolve to get full details
full_user = await backend.resolve_user(incomplete_user)
print(full_user.name)  # Now populated
```

## Channel

The `Channel` model represents a channel, room, or conversation.

```python
from chatom import Channel, ChannelType

# Public channel
channel = Channel(
    id="C123456",
    name="general",
    topic="General discussion",
    channel_type=ChannelType.PUBLIC,
)

# Direct message
dm = Channel(
    id="D789",
    channel_type=ChannelType.DM,
    members=["U123", "U456"],
)

# Group DM
group_dm = Channel(
    id="G789",
    name="Project Team",
    channel_type=ChannelType.GROUP_DM,
    members=["U123", "U456", "U789"],
)
```

### Channel Types

| Type | Description |
|------|-------------|
| `ChannelType.PUBLIC` | Public channel visible to all |
| `ChannelType.PRIVATE` | Private channel (invite only) |
| `ChannelType.DM` | Direct message between two users |
| `ChannelType.GROUP_DM` | Group direct message |

### Channel Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Channel name |
| `topic` | `str` | Channel topic/description |
| `channel_type` | `ChannelType` | Type of channel |
| `members` | `List[str]` | Member user IDs |
| `organization_id` | `str` | Parent org/guild ID |
| `metadata` | `dict` | Platform-specific data |

## Message

The `Message` model represents a chat message.

```python
from chatom import Message, MessageType, User, Channel
from datetime import datetime

# Create a message
message = Message(
    id="M123456",
    content="Hello, world!",
    author=User(id="U123", name="Alice"),
    channel=Channel(id="C456", name="general"),
    created_at=datetime.now(),
    message_type=MessageType.DEFAULT,
)

# Message with thread
reply = Message(
    id="M789",
    content="Great message!",
    author=User(id="U456", name="Bob"),
    channel_id="C456",
    thread_id="M123456",  # Parent message ID
    reply_to_id="M123456",
)
```

### Message Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique identifier |
| `content` | `str` | Message text content |
| `author` | `User` | Message author |
| `author_id` | `str` | Author user ID |
| `channel` | `Channel` | Channel/room |
| `channel_id` | `str` | Channel ID |
| `created_at` | `datetime` | When created |
| `edited_at` | `datetime` | When last edited |
| `thread_id` | `str` | Parent thread ID |
| `reply_to_id` | `str` | Message being replied to |
| `reactions` | `List[Reaction]` | Emoji reactions |
| `attachments` | `List[Attachment]` | File attachments |
| `embeds` | `List[Embed]` | Rich embeds |
| `metadata` | `dict` | Platform-specific data |

### Message Types

```python
from chatom import MessageType

# Standard message
MessageType.DEFAULT

# System/notification messages
MessageType.SYSTEM

# Join/leave notifications
MessageType.JOIN
MessageType.LEAVE

# Pin notifications
MessageType.PIN
```

### Detecting Mentions

```python
# Check who is mentioned in a message
mentioned_user_ids = message.get_mentioned_user_ids()
mentioned_channel_ids = message.get_mentioned_channel_ids()

# Check if specific user is mentioned
if message.mentions_user("U123456"):
    print("User U123456 was mentioned!")
```

### Response Convenience Methods

Messages have methods that construct new Message instances for responses:

| Method | Description |
|--------|-------------|
| `as_reply(content)` | Create a reply message |
| `as_thread_reply(content)` | Create a reply in the same thread |
| `as_forward(channel)` | Create a forwarded message |
| `as_quote_reply(content)` | Create a reply that quotes the original |
| `reply_context()` | Get context dict for custom handling |

```python
# Create a reply message
reply = message.as_reply("Thanks!")
print(reply.reply_to is message)  # True
print(reply.message_type)  # MessageType.REPLY

# Create a forward to another channel
forward = message.as_forward(log_channel)
print(forward.forwarded_from is message)  # True
```

See [Messaging](messaging.md#response-convenience-methods) for full documentation.
```

## Reaction

The `Reaction` model represents emoji reactions on messages.

```python
from chatom import Emoji, Reaction

# Create an emoji
emoji = Emoji(
    name="thumbsup",
    unicode="👍",
    custom=False,
)

# Create a reaction
reaction = Reaction(
    emoji=emoji,
    count=5,
    users=["U123", "U456", "U789"],
)
```

### Emoji Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Emoji name (e.g., "thumbsup") |
| `unicode` | `str` | Unicode character |
| `custom` | `bool` | Whether custom emoji |
| `id` | `str` | Custom emoji ID |

## Organization

The `Organization` model represents a workspace, guild, or pod.

```python
from chatom import Organization

org = Organization(
    id="T123456",
    name="My Company",
    domain="mycompany.slack.com",
)
```

### Organization Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `str` | Unique identifier |
| `name` | `str` | Organization name |
| `domain` | `str` | Domain/URL |
| `icon_url` | `str` | Organization icon |
| `metadata` | `dict` | Platform-specific data |

## Attachment

The `Attachment` model represents file attachments.

```python
from chatom import Attachment, AttachmentType

attachment = Attachment(
    id="F123",
    filename="report.pdf",
    url="https://example.com/files/report.pdf",
    attachment_type=AttachmentType.FILE,
    size=1024000,
    mime_type="application/pdf",
)
```

### Attachment Types

| Type | Description |
|------|-------------|
| `AttachmentType.FILE` | Generic file |
| `AttachmentType.IMAGE` | Image file |
| `AttachmentType.VIDEO` | Video file |
| `AttachmentType.AUDIO` | Audio file |

## Embed

The `Embed` model represents rich embeds (cards, previews).

```python
from chatom import Embed, EmbedField, EmbedAuthor, EmbedFooter

embed = Embed(
    title="News Article",
    description="This is the article summary...",
    url="https://example.com/article",
    color=0x3498db,
    author=EmbedAuthor(name="John Doe"),
    fields=[
        EmbedField(name="Category", value="Technology", inline=True),
        EmbedField(name="Date", value="2024-01-15", inline=True),
    ],
    footer=EmbedFooter(text="Published by Example News"),
)
```

## Model Conversion

Convert between base models and backend-specific models:

```python
from chatom.base import promote, demote
from chatom import User

# Create a base user
base_user = User(id="U123", name="Alice")

# Promote to Slack-specific user
from chatom.slack import SlackUser
slack_user = promote(base_user, SlackUser)

# Demote back to base user
base_user_again = demote(slack_user)
```

## Next Steps

- [Backends](backends.md) - Working with chat platforms
- [Backend Configuration](backend-config.md) - Platform credentials
- [Messaging](messaging.md) - Sending and receiving messages
