# Mentions Guide

This guide covers how to mention users and channels in outgoing messages,
and how to parse mentions from incoming messages.

## Mentioning Users in Outbound Messages

### Using the Backend Method

The simplest way to mention a user is using the backend's `mention_user` method:

```python
# Get a user
user = await backend.fetch_user("U123456")

# Create a mention string in the backend's format
mention = backend.mention_user(user)

# Use in a message
await backend.send_message(
    channel_id,
    f"Hello {mention}! Welcome to the channel.",
)
```

### Platform-Specific Mention Formats

| Backend | Format | Example |
|---------|--------|---------|
| Discord | `<@user_id>` | `<@123456789>` |
| Slack | `<@user_id>` | `<@U123456>` |
| Symphony | `<mention uid="user_id"/>` | `<mention uid="12345"/>` |
| Matrix | `@user:server` | `@alice:matrix.org` |
| IRC | Just the nick | `alice` |
| Email | HTML mailto link | `<a href='mailto:alice@example.com'>Alice</a>` |

### Polymorphic Mentions

The base `mention_user` function automatically dispatches to the correct
backend based on the user type:

```python
from chatom import mention_user
from chatom.discord import DiscordUser
from chatom.slack import SlackUser

# Automatically uses the right format
discord_user = DiscordUser(id="123", name="alice")
slack_user = SlackUser(id="U123", name="alice")

print(mention_user(discord_user))  # "<@123>"
print(mention_user(slack_user))    # "<@U123>"
```

### Backend-Specific Mention Functions

#### Discord

```python
from chatom.discord import (
    mention_user,
    mention_channel,
    mention_role,
    mention_everyone,
    mention_here,
)

# User: <@123456789>
user_mention = mention_user(user)

# Channel: <#987654321>
channel_mention = mention_channel(channel)

# Role: <@&111222333>
role_mention = mention_role("role_id")

# Everyone: @everyone
everyone = mention_everyone()

# Here: @here
here = mention_here()
```

#### Slack

```python
from chatom.slack import (
    mention_user,
    mention_channel,
    mention_user_group,
    mention_here,
    mention_channel_all,
    mention_everyone,
)

# User: <@U123456>
user_mention = mention_user(user)

# Channel: <#C123456>
channel_mention = mention_channel(channel)

# User group: <!subteam^S123456>
group_mention = mention_user_group("S123456")

# Here: <!here>
here = mention_here()

# Channel: <!channel>
channel_all = mention_channel_all()

# Everyone: <!everyone>
everyone = mention_everyone()
```

#### Symphony

```python
from chatom.symphony import (
    mention_user,
    mention_user_by_email,
    format_hashtag,
    format_cashtag,
)

# User by ID: <mention uid="12345"/>
user_mention = mention_user(user)

# User by email: <mention email="alice@company.com"/>
email_mention = mention_user_by_email("alice@company.com")

# Hashtag: <hash tag="python"/>
hashtag = format_hashtag("python")

# Cashtag: <cash tag="AAPL"/>
cashtag = format_cashtag("AAPL")
```

#### Matrix

```python
from chatom.matrix import mention_user, mention_room, create_pill

# User MXID: @alice:matrix.org
user_mention = mention_user(user)

# Room: #general:matrix.org
room_mention = mention_room("#general:matrix.org")

# HTML "pill" (clickable mention):
# <a href="https://matrix.to/#/@alice:matrix.org">Alice</a>
pill = create_pill("@alice:matrix.org", "Alice")
```

#### IRC

```python
from chatom.irc import mention_user, highlight_user

# Simple mention (just the nick): alice
user_mention = mention_user(user)

# Highlight (nick: message): alice: Hello!
highlighted = highlight_user("alice", "Hello!")
```

#### Email

```python
from chatom.email import mention_user

# HTML mailto link:
# <a href='mailto:alice@example.com'>Alice</a>
user_mention = mention_user(user)
```

---

## Mentioning Channels

### Using the Backend Method

```python
# Get a channel
channel = await backend.fetch_channel("C123456")

# Create a mention string
mention = backend.mention_channel(channel)

# Use in a message
await backend.send_message(
    other_channel_id,
    f"Please continue this discussion in {mention}.",
)
```

### Platform-Specific Channel Mention Formats

| Backend | Format | Example |
|---------|--------|---------|
| Discord | `<#channel_id>` | `<#987654321>` |
| Slack | `<#channel_id>` | `<#C123456>` |
| Symphony | Channel name | `Project Chat` |
| Matrix | Room alias | `#general:matrix.org` |
| IRC | Channel name | `#general` |
| Email | N/A | N/A |

---

## Reading Mentions from Inbound Messages

### Parsing Mentions

Use `parse_mentions` to extract mentions from incoming messages:

```python
from chatom import parse_mentions

# Parse mentions for a specific backend
mentions = parse_mentions(message.content, backend.name)

for mention in mentions:
    print(f"Type: {mention.type}")      # "user", "channel", "role", etc.
    print(f"ID: {mention.id}")          # The extracted ID
    print(f"Raw: {mention.raw}")        # The raw mention string
    print(f"Start: {mention.start}")    # Position in text
    print(f"End: {mention.end}")        # End position
```

### MentionMatch Properties

```python
class MentionMatch:
    type: str       # "user", "channel", "role", "everyone", "here"
    id: str         # Extracted ID
    raw: str        # Original mention text
    start: int      # Start position in text
    end: int        # End position in text
```

### Platform-Specific Parsing

#### Discord

```python
# Discord message: "Hey <@123456789>, please check <#987654321>"
mentions = parse_mentions(content, "discord")

# Result:
# [
#     MentionMatch(type="user", id="123456789", raw="<@123456789>"),
#     MentionMatch(type="channel", id="987654321", raw="<#987654321>"),
# ]

# Handle each mention
for mention in mentions:
    if mention.type == "user":
        user = await backend.fetch_user(mention.id)
        print(f"User mentioned: {user.name}")
    elif mention.type == "channel":
        channel = await backend.fetch_channel(mention.id)
        print(f"Channel mentioned: {channel.name}")
```

#### Slack

```python
# Slack message: "Hey <@U123456>, check <#C789012>"
mentions = parse_mentions(content, "slack")

for mention in mentions:
    if mention.type == "user":
        user = await backend.fetch_user(mention.id)
    elif mention.type == "channel":
        channel = await backend.fetch_channel(mention.id)
```

#### Symphony

```python
# Symphony message: '<mention uid="12345"/> Please review'
mentions = parse_mentions(content, "symphony")

for mention in mentions:
    if mention.type == "user":
        user = await backend.fetch_user(mention.id)
```

### Extracting User IDs from Bot Mentions

A common pattern is detecting when your bot is mentioned:

```python
async def handle_message(message, bot_user_id):
    mentions = parse_mentions(message.content, backend.name)

    # Check if the bot was mentioned
    bot_mentioned = any(
        m.type == "user" and m.id == bot_user_id
        for m in mentions
    )

    if bot_mentioned:
        # Respond to the mention
        await backend.send_message(
            message.channel_id,
            "Hi! You mentioned me. How can I help?",
        )
```

### Removing Mentions from Content

To get clean text without mentions:

```python
def remove_mentions(content: str, backend_name: str) -> str:
    """Remove all mentions from a message."""
    mentions = parse_mentions(content, backend_name)

    # Sort by position (reverse) to remove from end first
    for mention in sorted(mentions, key=lambda m: m.start, reverse=True):
        content = content[:mention.start] + content[mention.end:]

    return content.strip()

# Example
message = "Hey <@U123456>, what do you think?"
clean = remove_mentions(message, "slack")
# Result: "Hey , what do you think?"
```

### Replacing Mentions with Names

```python
async def replace_mentions_with_names(content: str, backend) -> str:
    """Replace mention tags with display names."""
    mentions = parse_mentions(content, backend.name)

    # Sort by position (reverse) to replace from end first
    for mention in sorted(mentions, key=lambda m: m.start, reverse=True):
        if mention.type == "user":
            user = await backend.fetch_user(mention.id)
            name = user.display_name if user else "Unknown User"
        elif mention.type == "channel":
            channel = await backend.fetch_channel(mention.id)
            name = f"#{channel.name}" if channel else "#unknown"
        else:
            name = mention.raw

        content = content[:mention.start] + name + content[mention.end:]

    return content

# Example
message = "Hey <@U123456>, check <#C789012>"
readable = await replace_mentions_with_names(message, backend)
# Result: "Hey Alice, check #general"
```

---

## Complete Example: Greeting Bot

A bot that responds when mentioned:

```python
import asyncio
from chatom import parse_mentions
from chatom.slack import SlackBackend, SlackConfig

async def run_greeting_bot():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)

    await backend.connect()

    # Get the bot's own user ID
    # (In a real app, get this from auth.test or stored config)
    bot_user_id = "U_BOT_ID"

    channel_id = "C123456"

    # Fetch recent messages
    messages = await backend.fetch_messages(channel_id, limit=10)

    for message in messages:
        # Skip if no content
        if not message.content:
            continue

        # Parse mentions
        mentions = parse_mentions(message.content, "slack")

        # Check if bot was mentioned
        bot_mentioned = any(
            m.type == "user" and m.id == bot_user_id
            for m in mentions
        )

        if bot_mentioned:
            # Get the sender
            author = await backend.fetch_user(message.user_id)
            if author:
                # Reply with a greeting
                reply = f"Hello {backend.mention_user(author)}! How can I help?"
                await backend.send_message(channel_id, reply)

    await backend.disconnect()

asyncio.run(run_greeting_bot())
```

---

## Best Practices

### 1. Always Use Backend Methods

Use `backend.mention_user()` instead of constructing mention strings manually:

```python
# ✅ Good - uses correct format for the backend
mention = backend.mention_user(user)

# ❌ Avoid - may break on different backends
mention = f"<@{user.id}>"
```

### 2. Handle Missing Users Gracefully

```python
async def safe_mention(backend, user_id: str) -> str:
    user = await backend.fetch_user(user_id)
    if user:
        return backend.mention_user(user)
    return f"User {user_id}"  # Fallback
```

### 3. Be Mindful of Notification Spam

Mentions often trigger notifications. Avoid:
- Mentioning users in automated bulk messages
- Using @everyone/@here unnecessarily
- Mentioning users in edit operations (may re-notify)

### 4. Cache User Lookups

When processing many mentions, cache user lookups:

```python
user_cache = {}

async def get_user_cached(backend, user_id: str):
    if user_id not in user_cache:
        user_cache[user_id] = await backend.fetch_user(user_id)
    return user_cache[user_id]
```

---

## Next Steps

- Learn about [Message Formatting](messaging.md)
- Explore [Advanced Features](advanced-features.md) like reactions and threads
- See [Backend Examples](backend-examples.md) for platform-specific code
