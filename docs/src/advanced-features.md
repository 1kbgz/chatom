# Advanced Features

This guide covers advanced chatom features including reactions, attachments,
embeds, threads, and presence management.

## Reactions

Reactions are emoji responses to messages. Support varies by platform.

### Adding Reactions

```python
# Add a Unicode emoji reaction
await backend.add_reaction(
    channel_id="C123456",
    message_id="msg_id",
    emoji="👍",
)

# Add a custom emoji (Discord, Slack)
await backend.add_reaction(
    channel_id="C123456",
    message_id="msg_id",
    emoji="custom_emoji_name",
)
```

### Removing Reactions

```python
await backend.remove_reaction(
    channel_id="C123456",
    message_id="msg_id",
    emoji="👍",
)
```

### Reading Reactions from Messages

```python
messages = await backend.fetch_messages(channel_id)

for message in messages:
    for reaction in message.reactions:
        print(f"Emoji: {reaction.emoji.name}")
        print(f"Unicode: {reaction.emoji.unicode}")
        print(f"Count: {reaction.count}")
        print(f"Custom: {reaction.emoji.is_custom}")
```

### Reaction Models

```python
from chatom import Emoji, Reaction

# Create an emoji
emoji = Emoji(
    name="thumbsup",
    unicode="👍",
    is_custom=False,
)

# Create a reaction
reaction = Reaction(
    emoji=emoji,
    count=5,
    me=True,  # Did the current user react?
)
```

### Platform Support

| Backend | Unicode | Custom | Add | Remove |
|---------|---------|--------|-----|--------|
| Discord | ✅ | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ✅ | ✅ |
| Symphony | ❌ | ❌ | ❌ | ❌ |
| Matrix | ✅ | ✅ | ✅ | ✅ |
| IRC | ❌ | ❌ | ❌ | ❌ |
| Email | ❌ | ❌ | ❌ | ❌ |

### Reaction Events

Handle reaction events (backend-specific):

```python
# Example event handler pattern
async def on_reaction_add(event):
    print(f"User {event.user_id} added {event.emoji}")
    print(f"Message: {event.message_id}")
    print(f"Channel: {event.channel_id}")

# Reaction event model
from chatom import ReactionEvent, ReactionEventType

event = ReactionEvent(
    type=ReactionEventType.ADD,  # or REMOVE
    message_id="msg_123",
    channel_id="C123456",
    user_id="U789",
    emoji=Emoji(name="thumbsup", unicode="👍"),
)
```

---

## Attachments

Attachments are files sent with messages.

### Attachment Model

```python
from chatom import Attachment, AttachmentType, File, Image

# Generic attachment
attachment = Attachment(
    id="att_123",
    filename="document.pdf",
    url="https://example.com/files/document.pdf",
    content_type="application/pdf",
    size=1024000,  # bytes
    attachment_type=AttachmentType.FILE,
)

# File attachment (with additional metadata)
file = File(
    id="file_123",
    filename="report.xlsx",
    url="https://example.com/files/report.xlsx",
    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    size=512000,
)

# Image attachment
image = Image(
    id="img_123",
    filename="photo.png",
    url="https://example.com/images/photo.png",
    content_type="image/png",
    size=256000,
    width=800,
    height=600,
    thumbnail_url="https://example.com/images/photo_thumb.png",
)
```

### Reading Attachments from Messages

```python
messages = await backend.fetch_messages(channel_id)

for message in messages:
    for attachment in message.attachments:
        print(f"Filename: {attachment.filename}")
        print(f"Type: {attachment.content_type}")
        print(f"Size: {attachment.size} bytes")
        print(f"URL: {attachment.url}")

        # Check attachment type
        if attachment.attachment_type == AttachmentType.IMAGE:
            print(f"Dimensions: {attachment.width}x{attachment.height}")
```

### Attachment Types

```python
from chatom import AttachmentType

AttachmentType.FILE      # Generic file
AttachmentType.IMAGE     # Image (png, jpg, gif, etc.)
AttachmentType.VIDEO     # Video file
AttachmentType.AUDIO     # Audio file
AttachmentType.ARCHIVE   # Zip, tar, etc.
AttachmentType.DOCUMENT  # PDF, Word, etc.
```

### Sending Attachments

Attachment sending is backend-specific:

```python
# Discord
await backend.send_message(
    channel_id,
    "Check out this file!",
    files=["/path/to/file.pdf"],
)

# Slack
await backend.send_message(
    channel_id,
    "Here's the document",
    files=[{"file": "/path/to/file.pdf", "title": "Report"}],
)

# Symphony
await backend.send_message(
    stream_id,
    "<messageML>See attachment</messageML>",
    attachments=["/path/to/file.pdf"],
)
```

### Platform Support

| Backend | Upload | Download URL | Max Size |
|---------|--------|--------------|----------|
| Discord | ✅ | ✅ | 25MB (100MB Nitro) |
| Slack | ✅ | ✅ | Workspace dependent |
| Symphony | ✅ | ✅ | 100MB |
| Matrix | ✅ | ✅ | Homeserver dependent |
| IRC | Limited | Via DCC/URL | N/A |
| Email | ✅ | ✅ | ~25MB typical |

---

## Embeds

Embeds are rich content blocks (cards) attached to messages.

### Embed Model

```python
from chatom import Embed, EmbedAuthor, EmbedField, EmbedFooter, EmbedMedia

# Create a rich embed
embed = Embed(
    title="Project Update",
    description="Here's the latest status on our project.",
    url="https://example.com/project",
    color="#3498db",  # Hex color
    timestamp=datetime.now(timezone.utc),
    author=EmbedAuthor(
        name="Alice",
        url="https://example.com/alice",
        icon_url="https://example.com/alice/avatar.png",
    ),
    thumbnail=EmbedMedia(
        url="https://example.com/project/logo.png",
        width=100,
        height=100,
    ),
    image=EmbedMedia(
        url="https://example.com/project/banner.png",
        width=800,
        height=400,
    ),
    fields=[
        EmbedField(name="Status", value="In Progress", inline=True),
        EmbedField(name="Priority", value="High", inline=True),
        EmbedField(name="Due Date", value="2024-12-31", inline=True),
        EmbedField(name="Description", value="Long description here...", inline=False),
    ],
    footer=EmbedFooter(
        text="Posted by Project Bot",
        icon_url="https://example.com/bot/icon.png",
    ),
)
```

### Embed Components

#### EmbedAuthor

```python
author = EmbedAuthor(
    name="Author Name",
    url="https://example.com/author",      # Optional link
    icon_url="https://example.com/icon.png",  # Optional icon
)
```

#### EmbedField

```python
# Inline fields (displayed side by side)
field1 = EmbedField(name="Column 1", value="Value 1", inline=True)
field2 = EmbedField(name="Column 2", value="Value 2", inline=True)

# Full-width field
field3 = EmbedField(name="Full Width", value="This spans the full width", inline=False)
```

#### EmbedMedia

```python
# Thumbnail (small, shown on right)
thumbnail = EmbedMedia(
    url="https://example.com/thumb.png",
    width=100,
    height=100,
)

# Main image (large, shown at bottom)
image = EmbedMedia(
    url="https://example.com/image.png",
    width=800,
    height=400,
)
```

#### EmbedFooter

```python
footer = EmbedFooter(
    text="Footer text here",
    icon_url="https://example.com/footer-icon.png",
)
```

### Reading Embeds from Messages

```python
for message in messages:
    for embed in message.embeds:
        print(f"Title: {embed.title}")
        print(f"Description: {embed.description}")
        print(f"URL: {embed.url}")

        if embed.author:
            print(f"Author: {embed.author.name}")

        for field in embed.fields:
            print(f"  {field.name}: {field.value}")
```

### Sending Embeds

```python
# Discord - supports rich embeds
await backend.send_message(
    channel_id,
    "Check this out!",
    embeds=[embed.to_dict()],  # Convert to dict for API
)

# Slack - uses "attachments" format
slack_attachment = {
    "fallback": embed.title,
    "color": embed.color,
    "title": embed.title,
    "title_link": embed.url,
    "text": embed.description,
    "fields": [
        {"title": f.name, "value": f.value, "short": f.inline}
        for f in embed.fields
    ],
}
await backend.send_message(
    channel_id,
    "Check this out!",
    attachments=[slack_attachment],
)
```

### Platform Support

| Backend | Rich Embeds | Link Previews | Custom Colors |
|---------|-------------|---------------|---------------|
| Discord | ✅ Full | ✅ | ✅ |
| Slack | ✅ (attachments) | ✅ | ✅ |
| Symphony | ✅ (cards) | ✅ | ❌ |
| Matrix | ❌ | ✅ | ❌ |
| IRC | ❌ | ❌ | ❌ |
| Email | ✅ (HTML) | Varies | ✅ |

---

## Threads

Threads are sub-conversations attached to a message.

### Thread Model

```python
from chatom import Thread

thread = Thread(
    id="thread_123",
    parent_message_id="msg_456",
    channel_id="C123456",
    name="Discussion about feature X",
    message_count=15,
    participant_count=3,
    locked=False,
    archived=False,
)
```

### Sending Messages to Threads

```python
# Reply in a thread
await backend.send_message(
    channel_id="C123456",
    content="This is a thread reply",
    thread_id="thread_123",  # or parent message ID
)
```

### Fetching Thread Messages

```python
# Fetch messages from a thread
thread_messages = await backend.fetch_messages(
    channel_id="C123456",
    thread_id="thread_123",
    limit=50,
)
```

### Creating a Thread

```python
# Start a new thread from a message (Discord)
await backend.send_message(
    channel_id="C123456",
    content="Let's discuss this further",
    thread_id=parent_message_id,  # Reply to start thread
)
```

### Platform-Specific Thread Behavior

#### Discord

```python
# Discord threads are first-class channels
# Thread ID is the channel ID of the thread
await backend.send_message(
    thread_id,  # Use thread ID as channel
    "Reply in Discord thread",
)
```

#### Slack

```python
# Slack threads use thread_ts (parent message timestamp)
await backend.send_message(
    channel_id="C123456",
    content="Reply in Slack thread",
    thread_ts="1234567890.123456",  # Parent message ts
)
```

#### Matrix

```python
# Matrix uses relations for threads
await backend.send_message(
    room_id,
    "Reply in Matrix thread",
    reply_to=parent_event_id,  # Creates a threaded reply
)
```

### Platform Support

| Backend | Native Threads | Reply-to | Thread Names |
|---------|---------------|----------|--------------|
| Discord | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ❌ |
| Symphony | ✅ | ✅ | ❌ |
| Matrix | ✅ | ✅ | ❌ |
| IRC | ❌ | ❌ | ❌ |
| Email | ✅ (threading) | ✅ | ✅ (subject) |

---

## Presence

Presence indicates a user's online status and activity.

### Presence Model

```python
from chatom import Presence, PresenceStatus, Activity, ActivityType

# Basic presence
presence = Presence(
    user_id="U123456",
    status=PresenceStatus.ONLINE,
    status_text="Working on chatom",
)

# With activity
presence = Presence(
    user_id="U123456",
    status=PresenceStatus.ONLINE,
    activity=Activity(
        type=ActivityType.PLAYING,
        name="Visual Studio Code",
    ),
)
```

### Presence Status Values

```python
from chatom import PresenceStatus

PresenceStatus.ONLINE      # Available, active
PresenceStatus.IDLE        # Away, inactive
PresenceStatus.DND         # Do Not Disturb
PresenceStatus.OFFLINE     # Not connected
PresenceStatus.INVISIBLE   # Hidden (appears offline)
PresenceStatus.AWAY        # Explicitly away
PresenceStatus.BUSY        # Busy (Symphony)
PresenceStatus.UNKNOWN     # Status not available
```

### Getting User Presence

```python
# Get a user's presence
presence = await backend.get_presence("U123456")

if presence:
    print(f"Status: {presence.status}")
    print(f"Status text: {presence.status_text}")

    if presence.activity:
        print(f"Activity: {presence.activity.type} {presence.activity.name}")

    # Check convenience properties
    if presence.is_online:
        print("User is online!")
    elif presence.is_idle:
        print("User is idle")
    elif presence.is_offline:
        print("User is offline")
```

### Setting Your Presence

```python
# Set simple status
await backend.set_presence(
    status="online",
    status_text="Available for questions",
)

# Platform-specific options
await backend.set_presence(
    status="dnd",
    status_text="In a meeting",
    status_emoji=":calendar:",  # Slack
)
```

### Platform-Specific Status Values

| Backend | Online | Away/Idle | DND | Invisible |
|---------|--------|-----------|-----|-----------|
| Discord | `online` | `idle` | `dnd` | `invisible` |
| Slack | `auto` | `away` | N/A | N/A |
| Symphony | `AVAILABLE` | `AWAY` | `BUSY` | `OFF_WORK` |
| Matrix | `online` | `unavailable` | N/A | `offline` |
| IRC | N/A | AWAY msg | N/A | N/A |
| Email | N/A | N/A | N/A | N/A |

### Presence Heartbeat

For long-running bots, use the presence heartbeat:

```python
# Start automatic presence updates
backend.start_presence_heartbeat(
    interval_seconds=60,  # Update every 60 seconds
    status="online",
    status_text="Bot is running",
)

# ... bot runs ...

# Stop when done
backend.stop_presence_heartbeat()
```

### Activity Types

```python
from chatom import ActivityType

ActivityType.PLAYING     # Playing a game
ActivityType.STREAMING   # Streaming content
ActivityType.LISTENING   # Listening to music
ActivityType.WATCHING    # Watching something
ActivityType.CUSTOM      # Custom status
ActivityType.COMPETING   # Competing in something
```

### Setting Activity (Discord)

```python
# Discord supports rich activity
await backend.set_presence(
    status="online",
    activity_type="playing",
    activity_name="with the chatom API",
)
```

### Platform Support

| Backend | Get | Set | Status Text | Activity |
|---------|-----|-----|-------------|----------|
| Discord | ✅ | ✅ | ❌ | ✅ |
| Slack | ✅ | ✅ | ✅ | ❌ |
| Symphony | ✅ | ✅ | ❌ | ❌ |
| Matrix | ✅ | ✅ | ✅ | ❌ |
| IRC | Limited | ✅ (AWAY) | ✅ | ❌ |
| Email | ❌ | ❌ | ❌ | ❌ |

---

## User and Channel Lookup

### Fetching Users

```python
# Fetch by ID
user = await backend.fetch_user("U123456")

# Lookup with flexible criteria
user = await backend.lookup_user(
    id="U123456",        # By ID
    # or
    name="Alice",        # By name
    # or
    email="alice@example.com",  # By email
    # or
    handle="alice",      # By username/handle
)
```

### Fetching Channels

```python
# Fetch by ID
channel = await backend.fetch_channel("C123456")

# Lookup with flexible criteria
channel = await backend.lookup_channel(
    id="C123456",   # By ID
    # or
    name="general", # By name
)
```

### User Caching

Backends cache fetched users automatically:

```python
# First call fetches from API
user1 = await backend.fetch_user("U123")

# Second call returns cached copy
user2 = await backend.fetch_user("U123")

# Access the cache directly
cached = backend.users.get_by_id("U123")
all_users = list(backend.users)

# Clear cache if needed
backend.users.clear()
```

### Channel Caching

```python
# Channels are also cached
channel = await backend.fetch_channel("C123")

# Access cache
cached = backend.channels.get_by_id("C123")
by_name = backend.channels.get_by_name("general")
all_channels = list(backend.channels)
```

---

## Complete Example: Feature-Rich Bot

A bot demonstrating multiple features:

```python
import asyncio
from datetime import datetime, timezone
from chatom import (
    Embed, EmbedField, EmbedFooter,
    Emoji, Reaction,
    PresenceStatus,
    parse_mentions,
)
from chatom.slack import SlackBackend, SlackConfig

async def run_feature_bot():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)

    await backend.connect()

    # Set bot presence
    await backend.set_presence(
        status="auto",
        status_text="Feature Bot Online",
    )

    # Start presence heartbeat
    backend.start_presence_heartbeat(
        interval_seconds=300,
        status="auto",
        status_text="Feature Bot Running",
    )

    channel_id = "C123456"

    # Fetch recent messages
    messages = await backend.fetch_messages(channel_id, limit=10)

    for message in messages:
        content = message.content or ""

        # Check for commands
        if content.startswith("!status"):
            # Show user presence
            mentions = parse_mentions(content, "slack")
            if mentions:
                user_id = mentions[0].id
                presence = await backend.get_presence(user_id)
                if presence:
                    await backend.send_message(
                        channel_id,
                        f"User status: {presence.status.value}",
                    )

        elif content.startswith("!info"):
            # Send a rich embed (Slack attachment)
            attachment = {
                "fallback": "Bot Information",
                "color": "#36a64f",
                "title": "Feature Bot Info",
                "text": "I'm a demonstration bot for chatom features.",
                "fields": [
                    {"title": "Version", "value": "1.0.0", "short": True},
                    {"title": "Uptime", "value": "2 hours", "short": True},
                    {"title": "Commands", "value": "!status, !info, !react", "short": False},
                ],
                "footer": "chatom Feature Bot",
                "ts": int(datetime.now().timestamp()),
            }
            await backend.send_message(
                channel_id,
                "Here's my info:",
                attachments=[attachment],
            )

        elif content.startswith("!react"):
            # Add a reaction to the command message
            await backend.add_reaction(
                channel_id,
                message.id,
                "thumbsup",
            )

        # Check for attachments
        if message.attachments:
            for att in message.attachments:
                await backend.send_message(
                    channel_id,
                    f"I see you uploaded: {att.filename} ({att.size} bytes)",
                )

    # Cleanup
    backend.stop_presence_heartbeat()
    await backend.disconnect()

asyncio.run(run_feature_bot())
```

---

## Next Steps

- See [Backend Examples](backend-examples.md) for platform-specific code
- Learn about [Message Formatting](messaging.md)
- Explore [Mentions](mentions.md) for tagging users
- Check the [API Reference](api.md) for complete details
