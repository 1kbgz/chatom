# Backends

A **backend** is chatom's abstraction for a chat platform. Each backend implements the same interface, allowing you to write platform-agnostic code.

## What is a Backend?

A backend provides:
- **Connection management** - Connect/disconnect from the platform
- **User operations** - Look up and manage users
- **Channel operations** - Look up and manage channels
- **Messaging** - Send, receive, and manage messages
- **Reactions** - Add and remove emoji reactions
- **Presence** - Get and set online status

## Supported Backends

| Backend | Class | Import |
|---------|-------|--------|
| Slack | `SlackBackend` | `from chatom.slack import SlackBackend` |
| Discord | `DiscordBackend` | `from chatom.discord import DiscordBackend` |
| Symphony | `SymphonyBackend` | `from chatom.symphony import SymphonyBackend` |

## Backend Lifecycle

```python
from chatom.slack import SlackBackend, SlackConfig

# 1. Create configuration
config = SlackConfig(bot_token="xoxb-your-token")

# 2. Create backend
backend = SlackBackend(config=config)

# 3. Connect
await backend.connect()

# 4. Use the backend
channel = await backend.fetch_channel(name="general")
await backend.send_message(channel_id=channel.id, content="Hello!")

# 5. Disconnect
await backend.disconnect()
```

## Backend API Reference

### Connection Methods

```python
# Connect to the platform
await backend.connect()

# Check connection status
if backend.connected:
    print("Connected!")

# Disconnect
await backend.disconnect()
```

### User Lookup

```python
# Look up by ID
user = await backend.fetch_user(id="U123456")

# Look up by name
user = await backend.fetch_user(name="Alice Smith")

# Look up by handle/username
user = await backend.fetch_user(handle="alice.smith")

# Look up by email
user = await backend.fetch_user(email="alice@example.com")

# Resolve incomplete user
full_user = await backend.resolve_user(incomplete_user)
```

### Channel Lookup

```python
# Look up by ID
channel = await backend.fetch_channel(id="C123456")

# Look up by name
channel = await backend.fetch_channel(name="general")

# Resolve incomplete channel
full_channel = await backend.resolve_channel(incomplete_channel)

# Get channel members (flexible input)
members = await backend.fetch_channel_members("C123456")
members = await backend.fetch_channel_members(id="C123456")
members = await backend.fetch_channel_members(name="general")
members = await backend.fetch_channel_members(channel)
```

### Messaging

```python
# Send a message
message = await backend.send_message(
    channel_id="C123456",
    content="Hello, world!",
)

# Reply to a message (create thread)
reply = await backend.reply_to_message(
    channel_id="C123456",
    message_id="M789",
    content="This is a reply!",
)

# Forward a message
await backend.forward_message(
    message=original_message,
    target_channel_id="C789",
)

# Edit a message
await backend.edit_message(
    channel_id="C123456",
    message_id="M789",
    content="Updated content",
)

# Delete a message
await backend.delete_message(
    channel_id="C123456",
    message_id="M789",
)
```

### Reading Messages

```python
# Read message history
async for message in backend.read_messages(channel_id="C123456", limit=50):
    print(f"{message.author.name}: {message.content}")

# Read thread messages
async for message in backend.read_thread(
    channel_id="C123456",
    thread_id="M789",
    limit=20,
):
    print(message.content)
```

### Reactions

```python
# Add a reaction
await backend.add_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="thumbsup",  # Slack: use name without colons
)

# Remove a reaction
await backend.remove_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="thumbsup",
)
```

### Direct Messages

```python
# Create/open a DM channel
dm_channel_id = await backend.create_dm(["U123456"])

# Send message in DM
await backend.send_message(
    channel_id=dm_channel.id,
    content="Hello via DM!",
)

# Convenience method: send DM directly
message = await backend.send_dm(
    user=user,
    content="Quick DM!",
)
```

### Presence

```python
# Get user presence
presence = await backend.get_presence(user_id="U123456")
print(f"Status: {presence.status}")  # online, away, dnd, etc.

# Set own presence (if supported)
await backend.set_presence(status="away")
```

### Organizations

```python
# List organizations (guilds/workspaces)
orgs = await backend.list_organizations()
for org in orgs:
    print(f"{org.name} ({org.id})")

# Fetch organization by name
org = await backend.fetch_organization(name="My Workspace")
```

### Real-time Events

```python
# Listen for incoming messages
async for message in backend.listen():
    print(f"New message: {message.content}")

    # Check if bot was mentioned
    if message.mentions_user(backend.bot_user_id):
        await backend.reply_to_message(
            channel_id=message.channel_id,
            message_id=message.id,
            content="You mentioned me!",
        )
```

## Backend Properties

```python
# Backend identifier
backend.name  # "slack", "discord", "symphony"

# Human-readable name
backend.display_name  # "Slack", "Discord", "Symphony"

# Preferred format
backend.get_format()  # Format.SLACK_MARKDOWN, etc.

# Capabilities
backend.capabilities  # BackendCapabilities object
```

## Capabilities

Each backend reports its capabilities:

```python
caps = backend.capabilities

caps.threads           # Supports threading
caps.reactions         # Supports reactions
caps.editing           # Supports message editing
caps.deleting          # Supports message deletion
caps.direct_messages   # Supports DMs
caps.presence          # Supports presence
caps.typing            # Supports typing indicators
caps.attachments       # Supports file attachments
caps.embeds            # Supports rich embeds
```

## Sync API

For synchronous code, use the `.sync` helper:

```python
# All async methods are available synchronously
backend.sync.connect()
channel = backend.sync.fetch_channel(name="general")
backend.sync.send_message(channel_id=channel.id, content="Hello!")
backend.sync.disconnect()
```

## Error Handling

```python
from chatom.base import LookupError

try:
    channel = await backend.fetch_channel(name="nonexistent")
    if channel is None:
        print("Channel not found")
except Exception as e:
    print(f"Error: {e}")
```

## Next Steps

- [Backend Configuration](backend-config.md) - Set up credentials for each platform
- [Messaging](messaging.md) - Detailed messaging guide
- [Format System](format-system.md) - Rich text formatting


