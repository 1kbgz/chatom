# Quickstart

This guide will help you get started with chatom in just a few minutes.

## Basic Models

### Creating Users and Channels

```python
from chatom import User, Channel

# Create a user
user = User(
    id="u123",
    name="Alice",
    handle="alice",
    email="alice@example.com",
)

# Access properties
print(user.display_name)  # "Alice"
print(user.mention_name)  # "alice"

# Create a channel
channel = Channel(
    id="c456",
    name="general",
    topic="General discussion",
)
```

### Creating Messages

```python
from chatom import User, Channel, Message, Emoji, Reaction

user = User(id="u1", name="Alice")
channel = Channel(id="c1", name="general")

# Create an emoji and reaction
emoji = Emoji(name="thumbsup", unicode="👍")
reaction = Reaction(emoji=emoji, count=5)

# Create a message with reactions
message = Message(
    id="m789",
    content="Hello, world!",
    author=user,
    channel=channel,
    reactions=[reaction],
)

print(message.author.name)  # "Alice"
print(len(message.reactions))  # 1
```

## Rich Text Formatting

### Building Formatted Messages

```python
from chatom import (
    Format,
    Text,
    Bold,
    Italic,
    Paragraph,
    FormattedMessage,
)

# Create a formatted message
msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Text(content="Hello, "),
            Bold(child=Text(content="world")),
            Text(content="! This is "),
            Italic(child=Text(content="chatom")),
            Text(content="."),
        ]),
    ]
)

# Render to different formats
print(msg.render(Format.PLAINTEXT))      # "Hello, world! This is chatom.\n"
print(msg.render(Format.MARKDOWN))       # "Hello, **world**! This is *chatom*.\n"
print(msg.render(Format.HTML))           # "<p>Hello, <strong>world</strong>!..."
```

### Creating Tables

```python
from chatom import Table, Format

# Create a table from data
data = [
    ["Alice", "100", "Gold"],
    ["Bob", "85", "Silver"],
]
table = Table.from_data(data, headers=["Name", "Score", "Rank"])

# Render as markdown
print(table.render(Format.MARKDOWN))
# | Name | Score | Rank |
# |---|---|---|
# | Alice | 100 | Gold |
# | Bob | 85 | Silver |
```

## Backend-Specific Models

### Discord

```python
from chatom.discord import (
    DiscordUser,
    DiscordChannel,
    mention_user,
    mention_channel,
    mention_role,
)

user = DiscordUser(id="123456789", name="Alice")
print(mention_user(user))  # "<@123456789>"

channel = DiscordChannel(id="987654321", name="general")
print(mention_channel(channel))  # "<#987654321>"

print(mention_role("111222333"))  # "<@&111222333>"
```

### Slack

```python
from chatom.slack import (
    SlackUser,
    SlackChannel,
    mention_user,
    mention_channel,
    mention_here,
)

user = SlackUser(id="U123456", name="alice")
print(mention_user(user))  # "<@U123456>"

channel = SlackChannel(id="C123456", name="general")
print(mention_channel(channel))  # "<#C123456>"

print(mention_here())  # "<!here>"
```

### Symphony

```python
from chatom.symphony import (
    SymphonyUser,
    mention_user,
    format_hashtag,
    format_cashtag,
)

user = SymphonyUser(id="123", name="alice", user_id=12345)
print(mention_user(user))  # '<mention uid="12345"/>'

print(format_hashtag("python"))  # '<hash tag="python"/>'
print(format_cashtag("AAPL"))    # '<cash tag="AAPL"/>'
```

## Polymorphic Mentions

The `mention_user` function automatically dispatches to the correct backend:

```python
from chatom import mention_user
from chatom.discord import DiscordUser
from chatom.slack import SlackUser

discord_user = DiscordUser(id="123", name="alice")
slack_user = SlackUser(id="U123", name="alice")

print(mention_user(discord_user))  # "<@123>"
print(mention_user(slack_user))    # "<@U123>"
```

## Checking Capabilities

```python
from chatom import Capability, DISCORD_CAPABILITIES

# Check what Discord supports
print(DISCORD_CAPABILITIES.supports(Capability.THREADS))        # True
print(DISCORD_CAPABILITIES.supports(Capability.VOICE_CHAT))     # True
print(DISCORD_CAPABILITIES.supports(Capability.EMOJI_REACTIONS)) # True
```

## Next Steps

- Learn about all the [Base Models](base-models.md)
- Explore the [Format System](format-system.md)
- Dive into specific [Backends](backends.md)
- Check the full [API Reference](api.md)
