<a class="logo-light" href="https://github.com/1kbgz/chatom#gh-light-mode-only">
  <img src="https://github.com/1kbgz/chatom/raw/main/docs/img/logo-light.png?raw=true#gh-light-mode-only" alt="chatom" width="150"></a>
</a>
<a class="logo-dark" href="https://github.com/1kbgz/chatom#gh-dark-mode-only">
  <img src="https://github.com/1kbgz/chatom/raw/main/docs/img/logo-dark.png?raw=true#gh-dark-mode-only" alt="chatom" width="150"></a>
</a>
<h1>chatom</h1>

Framework-agnostic chat application models and utilities

[![Build Status](https://github.com/1kbgz/chatom/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/1kbgz/chatom/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/1kbgz/chatom/branch/main/graph/badge.svg)](https://codecov.io/gh/1kbgz/chatom)
[![License](https://img.shields.io/github/license/1kbgz/chatom)](https://github.com/1kbgz/chatom)
[![PyPI](https://img.shields.io/pypi/v/chatom.svg)](https://pypi.python.org/pypi/chatom)

## Overview

`chatom` provides a unified, framework-agnostic representation of chat applications. It offers:

- **Base models** for users, channels, messages, attachments, embeds, reactions, and more
- **Backend-specific implementations** for Discord, Slack, Symphony, Email, IRC, and Matrix
- **Rich text formatting** with nodes for bold, italic, code, tables, lists, and more
- **Format converters** to render messages as plaintext, markdown, HTML, Slack mrkdwn, Discord markdown, or Symphony MessageML

## Installation

```bash
pip install chatom
```

## Quick Start

### Basic Models

```python
from chatom import User, Channel, Message, Emoji, Reaction

# Create a user
user = User(id="u123", name="Alice", email="alice@example.com")

# Create a channel
channel = Channel(id="c456", name="general", topic="General discussion")

# Create a message with reactions
emoji = Emoji(name="thumbsup", unicode="👍")
reaction = Reaction(emoji=emoji, count=5)

message = Message(
    id="m789",
    content="Hello, world!",
    author=user,
    channel=channel,
    reactions=[reaction],
)
```

### Rich Text Formatting

```python
from chatom import (
    Format,
    Text,
    Bold,
    Italic,
    Paragraph,
    Span,
    Table,
    FormattedMessage,
    MessageBuilder,
)

# Build a formatted message using nodes
msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Text(content="Welcome to "),
            Bold(child=Text(content="chatom")),
            Text(content="!"),
        ]),
    ]
)

# Render to different formats
print(msg.render(Format.MARKDOWN))      # "Welcome to **chatom**!\n"
print(msg.render(Format.HTML))          # "<p>Welcome to <strong>chatom</strong>!</p>"
print(msg.render(Format.SLACK_MARKDOWN)) # "Welcome to *chatom*!\n"
```

### Tables

```python
from chatom import Table, Format

# Create a table from data
data = [
    ["Alice", "100", "Gold"],
    ["Bob", "85", "Silver"],
    ["Carol", "70", "Bronze"],
]
table = Table.from_data(data, headers=["Name", "Score", "Rank"])

# Render as markdown
print(table.render(Format.MARKDOWN))
# | Name | Score | Rank |
# |---|---|---|
# | Alice | 100 | Gold |
# | Bob | 85 | Silver |
# | Carol | 70 | Bronze |

# Render as HTML
print(table.render(Format.HTML))
# <table><thead>...</thead><tbody>...</tbody></table>
```

### Backend-Specific Models

Each backend provides specialized models with platform-specific fields:

```python
# Discord
from chatom.discord import (
    DiscordUser,
    DiscordChannel,
    DiscordChannelType,
    DiscordPresence,
    mention_user,
    mention_channel,
    mention_role,
    mention_everyone,
    mention_here,
)

user = DiscordUser(
    id="123456789",
    name="Alice",
    discriminator="1234",
    is_bot=False,
)
print(mention_user(user))  # "<@123456789>"

channel = DiscordChannel(
    id="987654321",
    name="general",
    channel_type=DiscordChannelType.GUILD_TEXT,
)
print(mention_channel(channel))  # "<#987654321>"

# Slack
from chatom.slack import (
    SlackUser,
    SlackChannel,
    SlackPresence,
    mention_user,
    mention_channel,
    mention_user_group,
    mention_here,
    mention_channel_all,
    mention_everyone,
)

user = SlackUser(
    id="U123456",
    name="alice",
    real_name="Alice Smith",
    team_id="T123",
)
print(mention_user(user))  # "<@U123456>"

# Symphony
from chatom.symphony import (
    SymphonyUser,
    SymphonyChannel,
    SymphonyStreamType,
    mention_user,
    format_hashtag,
    format_cashtag,
)

user = SymphonyUser(id="123", name="alice", user_id=12345)
print(mention_user(user))  # '<mention uid="12345"/>'
print(format_hashtag("python"))  # '<hash tag="python"/>'
print(format_cashtag("AAPL"))  # '<cash tag="AAPL"/>'

# Matrix
from chatom.matrix import (
    MatrixUser,
    mention_user,
    mention_room,
    create_pill,
)

user = MatrixUser(
    id="alice",
    name="Alice",
    user_id="@alice:matrix.org",
    homeserver="matrix.org",
)
print(mention_user(user))  # "@alice:matrix.org"
print(create_pill(user))   # '<a href="https://matrix.to/#/@alice:matrix.org">Alice</a>'

# IRC
from chatom.irc import IRCUser, mention_user, highlight_user

user = IRCUser(id="alice", name="alice", nick="alice")
print(mention_user(user))  # "alice"
print(highlight_user("alice", "Hello there!"))  # "alice: Hello there!"

# Email
from chatom.email import EmailUser, mention_user

user = EmailUser(
    id="alice@example.com",
    name="Alice",
    email="alice@example.com",
)
print(mention_user(user))  # "<a href='mailto:alice@example.com'>Alice</a>"
```

### Polymorphic Mentions

The `mention_user` and `mention_channel` functions use `singledispatch` to automatically route to the correct backend implementation:

```python
from chatom import mention_user
from chatom.discord import DiscordUser
from chatom.slack import SlackUser

discord_user = DiscordUser(id="123", name="alice")
slack_user = SlackUser(id="U123", name="alice")

print(mention_user(discord_user))  # "<@123>"
print(mention_user(slack_user))    # "<@U123>"
```

### Backend-Agnostic Mentions

Use `mention_user_for_backend` and `mention_channel_for_backend` when you have a base User or Channel object and want to format it for a specific backend:

```python
from chatom import User, Channel, mention_user_for_backend, mention_channel_for_backend

user = User(id="123", name="Alice", email="alice@example.com")
channel = Channel(id="C456", name="general")

# Mention for different backends
print(mention_user_for_backend(user, "discord"))   # "<@123>"
print(mention_user_for_backend(user, "slack"))     # "<@123>"
print(mention_user_for_backend(user, "matrix"))    # "@123"
print(mention_user_for_backend(user, "email"))     # "<a href='mailto:alice@example.com'>Alice</a>"

print(mention_channel_for_backend(channel, "discord"))  # "<#C456>"
print(mention_channel_for_backend(channel, "slack"))    # "<#C456>"
```

### Rendering Messages for a Backend

Use `render_for` to render a formatted message using the appropriate format for a backend:

```python
from chatom import FormattedMessage, Paragraph, Text, Bold, get_format_for_backend

msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Text(content="Hello, "),
            Bold(child=Text(content="world")),
            Text(content="!"),
        ]),
    ]
)

# Render for different backends
print(msg.render_for("slack"))     # "Hello, *world*!\n" (Slack mrkdwn)
print(msg.render_for("discord"))   # "Hello, **world**!\n" (Discord markdown)
print(msg.render_for("symphony"))  # "<p>Hello, <b>world</b>!</p>" (MessageML)
print(msg.render_for("email"))     # "<p>Hello, <strong>world</strong>!</p>" (HTML)

# Get the format for a backend
from chatom import BACKEND_FORMAT_MAP
print(BACKEND_FORMAT_MAP["slack"])  # Format.SLACK_MARKDOWN
```

### Type Conversion

Convert between base types and backend-specific types with validation:

```python
from chatom import (
    User,
    promote,
    demote,
    can_promote,
    validate_for_backend,
    DISCORD,
    SLACK,
)
from chatom.discord import DiscordUser

# Create a base user
user = User(id="123", name="Alice", handle="alice")

# Check if it can be promoted
if can_promote(user, DISCORD):
    # Promote to DiscordUser with extra fields
    discord_user = promote(user, DISCORD, discriminator="1234")
    print(discord_user.discriminator)  # "1234"
    print(type(discord_user))  # <class 'chatom.discord.user.DiscordUser'>

# Demote back to base User
base_user = demote(discord_user)
print(type(base_user))  # <class 'chatom.base.user.User'>

# Cross-backend conversion: Discord -> Slack
slack_user = promote(demote(discord_user), SLACK, team_id="T123")
print(slack_user.team_id)  # "T123"
```

### Backend Capabilities

```python
from chatom import (
    Capability,
    DISCORD_CAPABILITIES,
    SLACK_CAPABILITIES,
    SYMPHONY_CAPABILITIES,
)

# Check what a backend supports
print(DISCORD_CAPABILITIES.supports(Capability.THREADS))        # True
print(DISCORD_CAPABILITIES.supports(Capability.VOICE_CHAT))     # True
print(DISCORD_CAPABILITIES.supports(Capability.EMOJI_REACTIONS)) # True
```

### Presence and Status

```python
from chatom import Presence, PresenceStatus

presence = Presence(
    status=PresenceStatus.ONLINE,
    status_text="Working on chatom",
    activity="Coding",
)

print(presence.is_available)  # True
print(presence.is_online)     # True
```

### Connections and Registries

The `Connection` base class provides a foundation for backend connections, along with `UserRegistry` and `ChannelRegistry` for managing and looking up users and channels:

```python
from chatom import Connection, UserRegistry, ChannelRegistry, User, Channel, LookupError

# Create registries for managing users and channels
users = [
    User(id="u1", name="Alice", email="alice@example.com", handle="alice"),
    User(id="u2", name="Bob", email="bob@example.com", handle="bob"),
]
user_registry = UserRegistry(users=users)

# Look up users by different fields
print(user_registry.id_to_user("u1").name)         # "Alice"
print(user_registry.email_to_user("bob@example.com").name)  # "Bob"
print(user_registry.name_to_user("Alice").id)      # "u1"
print(user_registry.handle_to_user("alice").email) # "alice@example.com"

# Reverse lookups
print(user_registry.user_to_id(users[0]))          # "u1"
print(user_registry.user_to_email(users[0]))       # "alice@example.com"

# Generic lookup - searches all fields
print(user_registry.lookup("alice").id)            # "u1" (matches handle)
print(user_registry.lookup("bob@example.com").id)  # "u2" (matches email)

# Check if a user exists
print(user_registry.get_user("u1") is not None)    # True
print(user_registry.get_user("unknown"))           # None (no exception)

# Same pattern for channels
channels = [
    Channel(id="c1", name="general", topic="General discussion"),
    Channel(id="c2", name="random"),
]
channel_registry = ChannelRegistry(channels=channels)

print(channel_registry.id_to_channel("c1").name)   # "general"
print(channel_registry.name_to_channel("random").id) # "c2"
print(channel_registry.lookup("general").topic)    # "General discussion"
```

Subclass `Connection` to implement backend-specific connection logic:

```python
from chatom import Connection, UserRegistry, ChannelRegistry

class MyBackendConnection(Connection):
    """Custom connection implementation."""

    async def connect(self):
        # Establish connection to your backend
        pass

    async def disconnect(self):
        # Clean up connection
        pass

    async def fetch_users(self) -> UserRegistry:
        # Fetch and return users from the backend
        users = await self._fetch_users_from_api()
        return UserRegistry(users=users)

    async def fetch_channels(self) -> ChannelRegistry:
        # Fetch and return channels from the backend
        channels = await self._fetch_channels_from_api()
        return ChannelRegistry(channels=channels)
```

## Supported Backends

| Backend  | User Model     | Channel Model     | Mention Support | Presence           |
| -------- | -------------- | ----------------- | --------------- | ------------------ |
| Discord  | `DiscordUser`  | `DiscordChannel`  | ✅              | `DiscordPresence`  |
| Slack    | `SlackUser`    | `SlackChannel`    | ✅              | `SlackPresence`    |
| Symphony | `SymphonyUser` | `SymphonyChannel` | ✅              | `SymphonyPresence` |
| Email    | `EmailUser`    | -                 | ✅              | -                  |
| IRC      | `IRCUser`      | `IRCChannel`      | ✅              | -                  |
| Matrix   | `MatrixUser`   | -                 | ✅              | -                  |

## Output Formats

| Format             | Enum Value                  | Description                   |
| ------------------ | --------------------------- | ----------------------------- |
| Plaintext          | `Format.PLAINTEXT`          | Plain text with no formatting |
| Markdown           | `Format.MARKDOWN`           | Standard Markdown             |
| Slack mrkdwn       | `Format.SLACK_MARKDOWN`     | Slack's mrkdwn format         |
| Discord Markdown   | `Format.DISCORD_MARKDOWN`   | Discord-flavored Markdown     |
| HTML               | `Format.HTML`               | Standard HTML                 |
| Symphony MessageML | `Format.SYMPHONY_MESSAGEML` | Symphony's XML-based format   |

## Text Node Types

| Node             | Description     | Example Output (Markdown)      |
| ---------------- | --------------- | ------------------------------ |
| `Text`           | Plain text      | `Hello`                        |
| `Bold`           | Bold text       | `**Hello**`                    |
| `Italic`         | Italic text     | `*Hello*`                      |
| `Strikethrough`  | Strikethrough   | `~~Hello~~`                    |
| `Underline`      | Underlined text | `<u>Hello</u>` (HTML only)     |
| `Code`           | Inline code     | `` `code` ``                   |
| `CodeBlock`      | Code block      | ```` ```python\ncode\n``` ```` |
| `Link`           | Hyperlink       | `[text](url)`                  |
| `Quote`          | Block quote     | `> quoted text`                |
| `Heading`        | Heading (h1-h6) | `# Heading`                    |
| `Paragraph`      | Paragraph       | Content with newline           |
| `UnorderedList`  | Bullet list     | `- item`                       |
| `OrderedList`    | Numbered list   | `1. item`                      |
| `Table`          | Data table      | Markdown/HTML table            |
| `UserMention`    | User mention    | `@user` or `<@id>`             |
| `ChannelMention` | Channel mention | `#channel`                     |

## Development

```bash
# Clone the repository
git clone https://github.com/1kbgz/chatom.git
cd chatom

# Install development dependencies
make develop

# Run tests
make test

# Run linting
make lint
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
