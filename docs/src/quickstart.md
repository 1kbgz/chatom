# Quickstart

This guide walks you through building your first chatom application.

## Prerequisites

1. Install chatom: `pip install chatom`
2. Have credentials for at least one platform (Slack, Discord, or Symphony)

## Step 1: Connect to a Backend

### Slack

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig

async def main():
    # Create configuration
    config = SlackConfig(
        bot_token="xoxb-your-bot-token",
        app_token="xapp-your-app-token",  # For Socket Mode (optional)
    )

    # Create and connect backend
    backend = SlackBackend(config=config)
    await backend.connect()

    print(f"Connected to {backend.display_name}")
    print(f"Capabilities: {backend.capabilities}")

    await backend.disconnect()

asyncio.run(main())
```

### Discord

```python
import asyncio
from chatom.discord import DiscordBackend, DiscordConfig

async def main():
    config = DiscordConfig(
        bot_token="your-bot-token",
        intents=["guilds", "guild_messages"],
    )

    backend = DiscordBackend(config=config)
    await backend.connect()

    # List available guilds
    guilds = await backend.list_organizations()
    for guild in guilds:
        print(f"Guild: {guild.name} ({guild.id})")

    await backend.disconnect()

asyncio.run(main())
```

### Symphony

```python
import asyncio
from chatom.symphony import SymphonyBackend, SymphonyConfig

async def main():
    config = SymphonyConfig(
        host="mycompany.symphony.com",
        bot_username="my-bot",
        bot_private_key_path="/path/to/private-key.pem",
    )

    backend = SymphonyBackend(config=config)
    await backend.connect()

    print(f"Connected to Symphony pod: {config.host}")

    await backend.disconnect()

asyncio.run(main())
```

## Step 2: Send a Message

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig

async def main():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)
    await backend.connect()

    # Look up channel by name
    channel = await backend.fetch_channel(name="general")

    # Send a message
    message = await backend.send_message(
        channel_id=channel.id,
        content="Hello from chatom! 👋",
    )

    print(f"Sent message: {message.id}")

    await backend.disconnect()

asyncio.run(main())
```

## Step 3: Format Your Message

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig
from chatom.format import FormattedMessage

async def main():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)
    await backend.connect()

    channel = await backend.fetch_channel(name="general")

    # Create a formatted message
    msg = FormattedMessage()
    msg.heading("Welcome!", level=2)
    msg.paragraph("Here's what you can do:")
    msg.unordered_list([
        "Send messages",
        "Add reactions",
        "Create threads",
    ])
    msg.newline()
    msg.bold("Need help?")
    msg.text(" Just ask!")

    # Render for the backend's format
    content = msg.render(backend.get_format())

    await backend.send_message(channel_id=channel.id, content=content)

    await backend.disconnect()

asyncio.run(main())
```

## Step 4: Read Message History

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig

async def main():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)
    await backend.connect()

    channel = await backend.fetch_channel(name="general")

    # Read last 10 messages
    print("Recent messages:")
    async for message in backend.read_messages(channel_id=channel.id, limit=10):
        author = message.author.name if message.author else "Unknown"
        print(f"  [{author}]: {message.content[:50]}...")

    await backend.disconnect()

asyncio.run(main())
```

## Step 5: Add Reactions

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig

async def main():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)
    await backend.connect()

    channel = await backend.fetch_channel(name="general")

    # Send a message
    message = await backend.send_message(
        channel_id=channel.id,
        content="React to this message!",
    )

    # Add reactions
    await backend.add_reaction(
        channel_id=channel.id,
        message_id=message.id,
        emoji="thumbsup",
    )
    await backend.add_reaction(
        channel_id=channel.id,
        message_id=message.id,
        emoji="rocket",
    )

    await backend.disconnect()

asyncio.run(main())
```

## Step 6: Create Threads

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig

async def main():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)
    await backend.connect()

    channel = await backend.fetch_channel(name="general")

    # Send parent message
    parent = await backend.send_message(
        channel_id=channel.id,
        content="📋 Thread topic: Project Updates",
    )

    # Reply in thread
    await backend.reply_to_message(
        channel_id=channel.id,
        message_id=parent.id,
        content="First update: Everything is on track!",
    )

    await backend.reply_to_message(
        channel_id=channel.id,
        message_id=parent.id,
        content="Second update: New features coming soon.",
    )

    await backend.disconnect()

asyncio.run(main())
```

## Using Sync API

If you prefer synchronous code:

```python
from chatom.slack import SlackBackend, SlackConfig

config = SlackConfig(bot_token="xoxb-your-token")
backend = SlackBackend(config=config)

# Use .sync for synchronous calls
backend.sync.connect()

channel = backend.sync.fetch_channel(name="general")
backend.sync.send_message(channel_id=channel.id, content="Hello!")

backend.sync.disconnect()
```

## Next Steps

- [Base Models](base-models.md) - Understanding User, Channel, Message
- [Backend Configuration](backend-config.md) - Detailed configuration options
- [Format System](format-system.md) - Rich text formatting
- [Examples](examples.md) - Complete example applications
