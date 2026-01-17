# API Reference

This page provides links to the automatically generated API documentation.

## Modules

The full API documentation is auto-generated from the source code docstrings.

### Core Modules

- **chatom** - Main module with all exports
- **chatom.base** - Base models (User, Channel, Message, etc.)
- **chatom.format** - Format system (TextNode, Table, FormattedMessage)
- **chatom.backend** - Backend base class and configuration
- **chatom.enums** - Backend type constants

### Backend Modules

- **chatom.discord** - Discord-specific models and utilities
- **chatom.slack** - Slack-specific models and utilities
- **chatom.symphony** - Symphony-specific models and utilities
- **chatom.email** - Email-specific models and utilities
- **chatom.irc** - IRC-specific models and utilities
- **chatom.matrix** - Matrix-specific models and utilities

## Quick Reference

### Base Models

| Class | Description |
|-------|-------------|
| `User` | Represents a chat user |
| `Channel` | Represents a chat channel |
| `Thread` | Represents a thread in a channel |
| `Message` | Represents a chat message |
| `Attachment` | Represents a file attachment |
| `Embed` | Represents a rich embed |
| `Emoji` | Represents an emoji |
| `Reaction` | Represents a message reaction |
| `Presence` | Represents user presence/status |
| `Capabilities` | Represents backend capabilities |

### Format System

| Class | Description |
|-------|-------------|
| `Format` | Enum of output formats |
| `TextNode` | Base class for text formatting |
| `Text` | Plain text content |
| `Bold` | Bold formatted text |
| `Italic` | Italic formatted text |
| `Code` | Inline code |
| `CodeBlock` | Code block with syntax highlighting |
| `Link` | Hyperlink |
| `Quote` | Block quote |
| `Heading` | Heading (h1-h6) |
| `Paragraph` | Paragraph of text |
| `Table` | Data table |
| `FormattedMessage` | Container for formatted content |
| `MessageBuilder` | Fluent API for building messages |

### Backend-Specific Models

| Backend | User | Channel | Presence |
|---------|------|---------|----------|
| Discord | `DiscordUser` | `DiscordChannel` | `DiscordPresence` |
| Slack | `SlackUser` | `SlackChannel` | `SlackPresence` |
| Symphony | `SymphonyUser` | `SymphonyChannel` | `SymphonyPresence` |
| Email | `EmailUser` | - | - |
| IRC | `IRCUser` | `IRCChannel` | - |
| Matrix | `MatrixUser` | - | - |

### Mention Functions

| Backend | Functions |
|---------|-----------|
| Discord | `mention_user`, `mention_channel`, `mention_role`, `mention_everyone`, `mention_here` |
| Slack | `mention_user`, `mention_channel`, `mention_user_group`, `mention_here`, `mention_channel_all`, `mention_everyone` |
| Symphony | `mention_user`, `mention_user_by_email`, `format_hashtag`, `format_cashtag` |
| Email | `mention_user` |
| IRC | `mention_user`, `highlight_user` |
| Matrix | `mention_user`, `mention_room`, `create_pill` |

### Backend Methods

All backends inherit from `BackendBase` and provide these core methods:

| Method | Description |
|--------|-------------|
| `connect()` | Establish connection to the backend |
| `disconnect()` | Disconnect from the backend |
| `fetch_user(id)` | Fetch a user by ID |
| `fetch_channel(id)` | Fetch a channel by ID |
| `fetch_messages(channel_id, limit, before, after)` | Fetch message history from a channel |
| `send_message(channel_id, content, **kwargs)` | Send a message to a channel |
| `lookup_user(id, name, email, handle)` | Look up a user by any identifier |
| `lookup_channel(id, name)` | Look up a channel by any identifier |
| `get_presence(user_id)` | Get a user's presence/online status |
| `set_presence(status, status_text, **kwargs)` | Set the current user's presence status |

#### Presence Support by Backend

| Backend | `get_presence` | `set_presence` |
|---------|----------------|----------------|
| Discord | ✅ Returns user presence with activity | ✅ Set bot presence/status |
| Slack | ✅ Returns active/away status | ✅ Set presence and status text |
| Symphony | ✅ Returns Symphony presence category | ✅ Set availability status |
| Matrix | ✅ Returns online/offline/unavailable | ✅ Set presence and status message |
| Email | ❌ Returns `None` | ❌ Not supported |
| IRC | ❌ Returns `None` | ⚠️ Maps to AWAY command |

#### Sync Helper

All async methods are available synchronously via the `sync` property:

```python
backend = DiscordBackend()
backend.sync.connect()
messages = backend.sync.fetch_messages("channel_id", limit=50)
presence = backend.sync.get_presence("user_id")
backend.sync.set_presence("online", "Available")
backend.sync.disconnect()
```
