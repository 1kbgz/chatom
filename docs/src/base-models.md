# Base Models

chatom provides a set of base models that represent common concepts across all chat platforms.

## Core Entities

### User

The `User` class represents a user on a chat platform.

```python
from chatom import User

user = User(
    id="u123",
    name="Alice Smith",
    handle="alice",
    email="alice@example.com",
    avatar_url="https://example.com/avatar.png",
    is_bot=False,
)

# Properties
user.display_name  # Returns name, handle, or id (in order of preference)
user.mention_name  # Returns handle or name
```

**Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | `str` | required | Platform-specific unique identifier |
| `name` | `str` | `""` | Display name of the user |
| `handle` | `str` | `""` | Username or handle (e.g., @username) |
| `email` | `str` | `""` | Email address, if available |
| `avatar_url` | `str` | `""` | URL to avatar image |
| `is_bot` | `bool` | `False` | Whether the user is a bot |

### Channel

The `Channel` class represents a chat channel or room.

```python
from chatom import Channel

channel = Channel(
    id="c456",
    name="general",
    topic="General discussion",
    description="A place for general chat",
    is_private=False,
)
```

**Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | `str` | required | Platform-specific unique identifier |
| `name` | `str` | `""` | Channel name |
| `topic` | `str` | `""` | Channel topic |
| `description` | `str` | `""` | Channel description |
| `channel_type` | `str` | `""` | Platform-specific channel type |
| `is_private` | `bool` | `False` | Whether the channel is private |

### Thread

The `Thread` class represents a thread within a channel.

```python
from chatom import Thread, Channel

parent_channel = Channel(id="c1", name="general")

thread = Thread(
    id="t789",
    name="Discussion about X",
    parent_channel=parent_channel,
    parent_message_id="m123",
)
```

### Message

The `Message` class represents a chat message.

```python
from chatom import Message, User, Channel

message = Message(
    id="m123",
    content="Hello, world!",
    author=User(id="u1", name="Alice"),
    author_id="u1",
    channel=Channel(id="c1", name="general"),
    channel_id="c1",
    created_at=datetime.now(),
    is_edited=False,
    backend="slack",
)
```

**Core Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | `str` | required | Unique message identifier |
| `content` | `str` | `""` | Message text content |
| `formatted_content` | `str` | `""` | Rich/formatted content (HTML, MessageML, etc.) |
| `author` | `User` | `None` | Message author |
| `author_id` | `str` | `""` | ID of the message author |
| `channel` | `Channel` | `None` | Channel the message was sent in |
| `channel_id` | `str` | `""` | ID of the channel |
| `thread` | `Thread` | `None` | Thread, if in a thread |
| `thread_id` | `str` | `""` | ID of the thread |
| `created_at` | `datetime` | `None` | When the message was created |
| `edited_at` | `datetime` | `None` | When the message was edited |
| `is_edited` | `bool` | `False` | Whether the message was edited |
| `is_pinned` | `bool` | `False` | Whether the message is pinned |
| `is_bot` | `bool` | `False` | Whether sent by a bot |
| `is_system` | `bool` | `False` | Whether it's a system message |
| `message_type` | `MessageType` | `DEFAULT` | Message type enum |
| `backend` | `str` | `""` | The backend this message originated from |
| `raw` | `Any` | `None` | Raw message data from the backend |

**Mention and Reply Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `mentions` | `list[User]` | `[]` | Users mentioned in the message |
| `mention_ids` | `list[str]` | `[]` | IDs of mentioned users |
| `reference` | `MessageReference` | `None` | Reference to replied message |
| `reply_to` | `Message` | `None` | Parent message if a reply |
| `reply_to_id` | `str` | `""` | ID of the replied-to message |

**Content Attributes:**

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `attachments` | `list[Attachment]` | `[]` | File attachments |
| `embeds` | `list[Embed]` | `[]` | Rich embeds |
| `reactions` | `list[Reaction]` | `[]` | Message reactions |
| `metadata` | `dict` | `{}` | Platform-specific metadata |

#### Message Conversion

Messages can be converted to and from `FormattedMessage` for cross-platform rendering:

```python
from chatom import Message
from chatom.format import FormattedMessage, MessageBuilder, Format

# Create a message and convert to FormattedMessage
msg = Message(
    id="m1",
    content="Hello **world**",
    author_id="u1",
    channel_id="c1",
    backend="discord",
)
formatted = msg.to_formatted()

# Render for different backends
print(formatted.render(Format.SLACK_MARKDOWN))  # For Slack
print(formatted.render(Format.HTML))            # For Matrix/Email

# Create a message from a FormattedMessage
fm = MessageBuilder().bold("Alert").text(": Check this out!").build()
slack_msg = Message.from_formatted(fm, backend="slack")
print(slack_msg.content)  # "*Alert*: Check this out!"

# Render a message directly for another backend
discord_msg = Message(content="Hello *everyone*", backend="slack")
print(discord_msg.render_for("discord"))  # Renders for Discord format
```

#### Backend-Specific Messages

Each backend has its own message class with additional platform-specific attributes:

```python
# Slack
from chatom.slack import SlackMessage
slack_msg = SlackMessage.from_api_response(api_data)
formatted = slack_msg.to_formatted()

# Discord
from chatom.discord import DiscordMessage
discord_msg = DiscordMessage.from_api_response(api_data)
formatted = discord_msg.to_formatted()

# Symphony
from chatom.symphony import SymphonyMessage
symphony_msg = SymphonyMessage.from_api_response(api_data)
formatted = symphony_msg.to_formatted()

# Matrix
from chatom.matrix import MatrixMessage
matrix_msg = MatrixMessage.from_event(event_data)
formatted = matrix_msg.to_formatted()

# IRC
from chatom.irc import IRCMessage
irc_msg = IRCMessage.from_raw(":nick!user@host PRIVMSG #channel :Hello!")
formatted = irc_msg.to_formatted()

# Email
from chatom.email import EmailMessage
email_msg = EmailMessage.from_email_message(email.message.Message())
formatted = email_msg.to_formatted()
```

## Attachments and Media

### Attachment

```python
from chatom import Attachment

attachment = Attachment(
    id="a123",
    filename="document.pdf",
    url="https://example.com/document.pdf",
    size=1024000,
    content_type="application/pdf",
)
```

### Embed

Rich embeds for displaying formatted content:

```python
from chatom import Embed, EmbedField

embed = Embed(
    title="Article Title",
    description="A brief description",
    url="https://example.com/article",
    color=0x5865F2,
    author_name="John Doe",
    author_url="https://example.com/john",
    thumbnail_url="https://example.com/thumb.png",
    image_url="https://example.com/image.png",
    fields=[
        EmbedField(name="Field 1", value="Value 1", inline=True),
        EmbedField(name="Field 2", value="Value 2", inline=True),
    ],
    footer_text="Footer text",
)
```

## Reactions and Emoji

### Emoji

```python
from chatom import Emoji

# Standard Unicode emoji
emoji = Emoji(name="thumbsup", unicode="👍")

# Custom emoji
custom = Emoji(
    id="123456",
    name="custom_emoji",
    animated=True,
)
```

### Reaction

```python
from chatom import Emoji, Reaction, User

emoji = Emoji(name="heart", unicode="❤️")
reaction = Reaction(
    emoji=emoji,
    count=10,
    users=[User(id="u1", name="Alice")],
    me=False,  # Whether the current user reacted
)
```

## Presence and Status

### Presence

```python
from chatom import Presence, PresenceStatus

presence = Presence(
    status=PresenceStatus.ONLINE,
    status_text="Working on chatom",
    activity="Coding",
)

# Check availability
presence.is_available  # True for ONLINE or IDLE
presence.is_online     # True only for ONLINE
```

**Status Values:**

| Status | Description |
|--------|-------------|
| `ONLINE` | User is online and active |
| `IDLE` | User is online but idle |
| `DND` | Do not disturb |
| `OFFLINE` | User is offline |
| `INVISIBLE` | User appears offline |

## Capabilities

Check what features a backend supports:

```python
from chatom import Capability, Capabilities

caps = Capabilities(
    capabilities={
        Capability.THREADS,
        Capability.EMOJI_REACTIONS,
        Capability.FILE_ATTACHMENTS,
    }
)

# Check single capability
caps.supports(Capability.THREADS)  # True

# Check multiple capabilities
caps.supports_all(Capability.THREADS, Capability.EMOJI_REACTIONS)  # True
caps.supports_any(Capability.VOICE_CHAT, Capability.THREADS)  # True
```

**Available Capabilities:**

| Capability | Description |
|------------|-------------|
| `THREADS` | Thread/reply support |
| `EMOJI_REACTIONS` | Emoji reaction support |
| `CUSTOM_EMOJI` | Custom emoji support |
| `FILE_ATTACHMENTS` | File attachment support |
| `EMBEDS` | Rich embed support |
| `VOICE_CHAT` | Voice chat support |
| `VIDEO_CHAT` | Video chat support |
| `SCREEN_SHARE` | Screen sharing support |
| `TYPING_INDICATORS` | Typing indicator support |
| `READ_RECEIPTS` | Read receipt support |
| `PRESENCE` | Presence/status support |
| `DIRECT_MESSAGES` | Direct message support |

### Predefined Capabilities

chatom includes predefined capability sets for each backend:

```python
from chatom import (
    DISCORD_CAPABILITIES,
    SLACK_CAPABILITIES,
    SYMPHONY_CAPABILITIES,
)
```
