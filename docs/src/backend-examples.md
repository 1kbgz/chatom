# Backend Examples

This guide provides practical examples for each backend, including configuration,
a simple bot that responds to "hi" messages, and platform-specific features.

## Discord

Discord is a popular chat platform for gaming and communities.

### Configuration

```python
from chatom.discord import DiscordBackend, DiscordConfig

config = DiscordConfig(
    bot_token="your-discord-bot-token",  # Required: Your bot token from Discord Developer Portal
    application_id="123456789",           # Optional: Application ID for slash commands
    guild_id="987654321",                  # Optional: Default guild for operations
    intents=["guilds", "guild_messages", "message_content"],  # Required intents
)

backend = DiscordBackend(config=config)
```

### Configuration Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot_token` | `SecretStr` | Yes | Discord bot token from Developer Portal |
| `application_id` | `str` | No | Application ID for commands |
| `guild_id` | `str` | No | Default guild ID for operations |
| `intents` | `List[str]` | No | Gateway intents to enable |
| `shard_id` | `int` | No | Shard ID for large bots |
| `shard_count` | `int` | No | Total number of shards |

### Simple Bot Example

```python
import asyncio
from chatom.discord import DiscordBackend, DiscordConfig

async def run_bot():
    config = DiscordConfig(
        bot_token="your-bot-token",
        intents=["guilds", "guild_messages", "message_content"],
    )
    backend = DiscordBackend(config=config)

    await backend.connect()
    print(f"Connected to Discord as {backend.display_name}")

    # In a real bot, you'd use discord.py's event system
    # This is a simplified example showing the chatom API

    # Fetch recent messages from a channel
    messages = await backend.fetch_messages("channel_id", limit=10)

    for message in messages:
        # Check if someone said "hi mybot"
        if message.content and "hi mybot" in message.content.lower():
            # Get the user who sent the message
            author = await backend.fetch_user(message.user_id)
            if author:
                # Reply with a greeting
                reply = f"Hello {backend.mention_user(author)}!"
                await backend.send_message(message.channel_id, reply)

    await backend.disconnect()

# Run with sync helper
backend = DiscordBackend(config=DiscordConfig(bot_token="token"))
backend.sync.connect()
messages = backend.sync.fetch_messages("channel_id", limit=10)
backend.sync.disconnect()
```

### Discord-Specific Features

#### Mentions

```python
from chatom.discord import mention_user, mention_channel, mention_role, mention_everyone

# User mention: <@123456789>
user_mention = backend.mention_user(user)

# Channel mention: <#987654321>
channel_mention = backend.mention_channel(channel)

# Role mention: <@&111222333>
from chatom.discord import mention_role
role_mention = mention_role("role_id")

# Special mentions
from chatom.discord import mention_everyone, mention_here
everyone = mention_everyone()  # @everyone
here = mention_here()          # @here
```

#### Reactions

```python
# Add a reaction (emoji name or unicode)
await backend.add_reaction("channel_id", "message_id", "👍")
await backend.add_reaction("channel_id", "message_id", "custom_emoji_name")

# Remove a reaction
await backend.remove_reaction("channel_id", "message_id", "👍")
```

#### Presence

```python
# Get user presence
presence = await backend.get_presence("user_id")
if presence:
    print(f"Status: {presence.status}")
    print(f"Activity: {presence.activity}")

# Set bot presence
await backend.set_presence(
    status="online",  # online, idle, dnd, invisible
    status_text="Playing chatom",
)
```

#### Create Channels and DMs

```python
# Create a DM with a user
dm_channel_id = await backend.create_dm(["user_id"])

# Create a new text channel
channel_id = await backend.create_channel(
    name="new-channel",
    description="A new text channel",
    public=True,
)
```

---

## Slack

Slack is a business communication platform.

### Configuration

```python
from chatom.slack import SlackBackend, SlackConfig

config = SlackConfig(
    bot_token="xoxb-your-bot-token",      # Required: Bot OAuth token
    app_token="xapp-your-app-token",       # Required for Socket Mode
    signing_secret="your-signing-secret",  # For request verification
    team_id="T123456789",                  # Workspace ID
    socket_mode=True,                      # Enable Socket Mode for events
)

backend = SlackBackend(config=config)
```

### Configuration Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot_token` | `SecretStr` | Yes | Bot OAuth token (xoxb-...) |
| `app_token` | `SecretStr` | No | App token for Socket Mode (xapp-...) |
| `signing_secret` | `SecretStr` | No | Request signing secret |
| `team_id` | `str` | No | Workspace ID |
| `socket_mode` | `bool` | No | Enable Socket Mode (default: False) |

### Simple Bot Example

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig

async def run_bot():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)

    await backend.connect()
    print("Connected to Slack")

    # Fetch recent messages from a channel
    messages = await backend.fetch_messages("C123456789", limit=10)

    for message in messages:
        # Check if someone said "hi slackbot"
        if message.content and "hi slackbot" in message.content.lower():
            # Get the user who sent the message
            author = await backend.fetch_user(message.user_id)
            if author:
                # Reply with a greeting using Slack mention format
                reply = f"Hello {backend.mention_user(author)}!"
                await backend.send_message(message.channel_id, reply)

    await backend.disconnect()

asyncio.run(run_bot())
```

### Slack-Specific Features

#### Mentions

```python
from chatom.slack import (
    mention_user,
    mention_channel,
    mention_user_group,
    mention_here,
    mention_channel_all,
    mention_everyone,
)

# User mention: <@U123456789>
user_mention = backend.mention_user(user)

# Channel mention: <#C123456789>
channel_mention = backend.mention_channel(channel)

# User group mention: <!subteam^S123>
group_mention = mention_user_group("S123456")

# Special mentions
here = mention_here()          # <!here>
channel = mention_channel_all() # <!channel>
everyone = mention_everyone()   # <!everyone>
```

#### Message Formatting (mrkdwn)

```python
from chatom import FormattedMessage, Bold, Italic, Text, Paragraph, Format

msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Bold(child=Text(content="Important")),
            Text(content=": Please review the "),
            Italic(child=Text(content="updated")),
            Text(content=" documentation."),
        ]),
    ]
)

# Render for Slack (uses *bold* and _italic_)
slack_content = msg.render(Format.SLACK_MARKDOWN)
await backend.send_message("C123", slack_content)
```

#### Presence

```python
# Get user presence
presence = await backend.get_presence("U123456789")
if presence:
    print(f"Status: {presence.status}")  # auto or away

# Set bot presence with status emoji
await backend.set_presence(
    status="auto",
    status_text="Working on chatom",
    status_emoji=":computer:",
)
```

#### Create Channels

```python
# Create a new public channel
channel_id = await backend.create_channel(
    name="project-updates",
    description="Updates for the project",
    public=True,
)

# Create a private channel
channel_id = await backend.create_channel(
    name="team-private",
    description="Private team discussions",
    public=False,
)
```

---

## Symphony

Symphony is an enterprise communication platform for financial services.

### Configuration

```python
from chatom.symphony import SymphonyBackend, SymphonyConfig

# RSA key authentication (recommended)
config = SymphonyConfig(
    host="mycompany.symphony.com",           # Required: Pod hostname
    bot_username="mybot",                     # Required: Bot service account
    bot_private_key_path="/path/to/key.pem", # Path to RSA private key
)

# Or with key content directly
config = SymphonyConfig(
    host="mycompany.symphony.com",
    bot_username="mybot",
    bot_private_key_content="-----BEGIN RSA PRIVATE KEY-----\n...",
)

backend = SymphonyBackend(config=config)
```

### Configuration Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | `str` | Yes | Symphony pod hostname |
| `port` | `int` | No | Pod port (default: 443) |
| `bot_username` | `str` | Yes | Bot's service account username |
| `bot_private_key_path` | `str` | No* | Path to RSA private key file |
| `bot_private_key_content` | `SecretStr` | No* | RSA private key content |
| `bot_certificate_path` | `str` | No* | Path to certificate (cert auth) |
| `agent_host` | `str` | No | Separate agent hostname |
| `key_manager_host` | `str` | No | Separate key manager hostname |

*One authentication method is required.

### Simple Bot Example

```python
import asyncio
from chatom.symphony import SymphonyBackend, SymphonyConfig

async def run_bot():
    config = SymphonyConfig(
        host="mycompany.symphony.com",
        bot_username="mybot",
        bot_private_key_path="/path/to/key.pem",
    )
    backend = SymphonyBackend(config=config)

    await backend.connect()
    print("Connected to Symphony")

    # Fetch recent messages from a stream
    stream_id = "abc123xyz"
    messages = await backend.fetch_messages(stream_id, limit=10)

    for message in messages:
        # Symphony messages arrive in PresentationML (HTML-like format)
        # A message with a mention looks like:
        # <p>hi <span class="entity" data-entity-id="0">@symphonybot</span></p>
        #
        # Use the format system to extract plain text:
        from chatom.format import Format

        formatted = message.to_formatted()
        plain_text = formatted.render(Format.PLAINTEXT)
        # Result: "hi @symphonybot"

        # You can also access mentions from metadata:
        mention_ids = formatted.metadata.get("mention_ids", [])

        # Check if someone mentioned symphonybot
        if "symphonybot" in plain_text.lower():
            # Get the user who sent the message
            author = await backend.fetch_user(message.user_id)
            if author:
                # Reply with a greeting using Symphony MessageML
                reply = f"<messageML>Hello {backend.mention_user(author)}!</messageML>"
                await backend.send_message(message.channel_id, reply)

    await backend.disconnect()

asyncio.run(run_bot())
```

### Symphony-Specific Features

#### MessageML Format

Symphony uses MessageML, an XML-based format for rich messages:

```python
from chatom import FormattedMessage, Bold, Italic, Text, Paragraph, Format

msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Bold(child=Text(content="Alert")),
            Text(content=": System maintenance scheduled."),
        ]),
    ]
)

# Render as MessageML
messageml = msg.render(Format.SYMPHONY_MESSAGEML)
# Result: <messageML><p><b>Alert</b>: System maintenance scheduled.</p></messageML>

await backend.send_message(stream_id, messageml)
```

#### Mentions

```python
from chatom.symphony import mention_user, mention_user_by_email, format_hashtag, format_cashtag

# User mention: <mention uid="12345"/>
user_mention = backend.mention_user(user)

# Mention by email: <mention email="alice@company.com"/>
email_mention = mention_user_by_email("alice@company.com")

# Hashtags: <hash tag="python"/>
hashtag = format_hashtag("python")

# Cashtags: <cash tag="AAPL"/>
cashtag = format_cashtag("AAPL")
```

#### Presence

```python
# Get user presence
presence = await backend.get_presence("12345")
if presence:
    print(f"Status: {presence.status}")
    # AVAILABLE, BUSY, AWAY, ON_THE_PHONE, BE_RIGHT_BACK,
    # IN_A_MEETING, OUT_OF_OFFICE, OFF_WORK

# Set presence
await backend.set_presence(
    status="BUSY",
    soft=True,  # Respect current activity state
)
```

#### Create Rooms and IMs

```python
# Create a direct message (IM) with users
im_stream_id = await backend.create_im(["user_id_1", "user_id_2"])

# Create a room
room_stream_id = await backend.create_room(
    name="Project Discussion",
    description="Room for project discussions",
    public=False,
    read_only=False,
)
```

---

## Matrix

Matrix is an open standard for decentralized communication.

### Configuration

```python
from chatom.matrix import MatrixBackend, MatrixConfig

config = MatrixConfig(
    homeserver_url="https://matrix.example.com",  # Required
    access_token="your-access-token",              # Required
    user_id="@bot:example.com",                    # Bot's user ID
    device_id="BOTDEVICE",                         # Device ID for E2EE
)

backend = MatrixBackend(config=config)
```

### Configuration Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `homeserver_url` | `str` | Yes | Matrix homeserver URL |
| `access_token` | `SecretStr` | Yes | Access token for authentication |
| `user_id` | `str` | No | Bot's Matrix user ID |
| `device_id` | `str` | No | Device ID for E2EE |
| `sync_filter_limit` | `int` | No | Limit for sync filter (default: 100) |

### Simple Bot Example

```python
import asyncio
from chatom.matrix import MatrixBackend, MatrixConfig

async def run_bot():
    config = MatrixConfig(
        homeserver_url="https://matrix.example.com",
        access_token="your-access-token",
        user_id="@mybot:example.com",
    )
    backend = MatrixBackend(config=config)

    await backend.connect()
    print("Connected to Matrix")

    # Fetch recent messages from a room
    room_id = "!abc123:example.com"
    messages = await backend.fetch_messages(room_id, limit=10)

    for message in messages:
        # Check if someone said "hi matrixbot"
        if message.content and "hi matrixbot" in message.content.lower():
            # Get the user who sent the message
            author = await backend.fetch_user(message.user_id)
            if author:
                # Reply with a greeting
                reply = f"Hello {backend.mention_user(author)}!"
                await backend.send_message(room_id, reply)

    await backend.disconnect()

asyncio.run(run_bot())
```

### Matrix-Specific Features

#### Mentions

```python
from chatom.matrix import mention_user, mention_room, create_pill

# User mention (just the MXID)
user_mention = backend.mention_user(user)  # @alice:example.com

# Room mention
room_mention = mention_room("#general:example.com")

# Create an HTML "pill" (clickable mention)
pill = create_pill("@alice:example.com", "Alice")
# <a href="https://matrix.to/#/@alice:example.com">Alice</a>
```

#### Message Formats

Matrix supports both plain text and HTML:

```python
from chatom.matrix import MatrixMessage

# Send plain text
await backend.send_message(room_id, "Hello, world!")

# Send HTML formatted message
await backend.send_message(
    room_id,
    "Hello, <b>world</b>!",
    format="org.matrix.custom.html",
)
```

#### Reactions

```python
# Add a reaction
await backend.add_reaction(room_id, event_id, "👍")

# Remove a reaction
await backend.remove_reaction(room_id, event_id, "👍")
```

#### Presence

```python
# Get user presence
presence = await backend.get_presence("@alice:example.com")
if presence:
    print(f"Status: {presence.status}")  # online, offline, unavailable
    print(f"Status message: {presence.status_msg}")

# Set presence
await backend.set_presence(
    status="online",
    status_text="Available for chat",
)
```

#### Room Management

```python
# Join a room
await backend.join_room("#general:example.com")

# Leave a room
await backend.leave_room("!room_id:example.com")

# Create a room
room_id = await backend.create_channel(
    name="New Room",
    description="A new Matrix room",
    public=True,
)
```

---

## IRC

IRC (Internet Relay Chat) is a classic real-time chat protocol.

### Configuration

```python
from chatom.irc import IRCBackend, IRCConfig

config = IRCConfig(
    server="irc.libera.chat",           # Required: IRC server
    port=6697,                           # Port (default: 6667)
    nickname="mybot",                    # Required: Bot nickname
    username="mybot",                    # Username (defaults to nickname)
    password="server-password",          # Server password (if required)
    nickserv_password="ns-password",     # NickServ password
    use_ssl=True,                        # Use SSL/TLS
    auto_join_channels=["#general"],     # Channels to auto-join
)

backend = IRCBackend(config=config)
```

### Configuration Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server` | `str` | Yes | IRC server hostname |
| `port` | `int` | No | Server port (default: 6667) |
| `nickname` | `str` | Yes | Bot's nickname |
| `username` | `str` | No | Username (defaults to nickname) |
| `realname` | `str` | No | Real name field |
| `password` | `SecretStr` | No | Server password |
| `nickserv_password` | `SecretStr` | No | NickServ password |
| `use_ssl` | `bool` | No | Enable SSL/TLS (default: False) |
| `auto_join_channels` | `List[str]` | No | Channels to join on connect |

### Simple Bot Example

```python
import asyncio
from chatom.irc import IRCBackend, IRCConfig

async def run_bot():
    config = IRCConfig(
        server="irc.libera.chat",
        port=6697,
        nickname="myircbot",
        use_ssl=True,
        auto_join_channels=["#mychannel"],
    )
    backend = IRCBackend(config=config)

    await backend.connect()
    print("Connected to IRC")

    # Note: IRC doesn't have message history by default
    # You need to set up event handlers for real-time messages

    # For demonstration, we'll show how to respond
    # In reality, you'd use the irc library's event system

    # When you receive a message "hi ircbot":
    sender_nick = "alice"
    channel = "#mychannel"

    # Reply with a greeting (highlighting the user)
    from chatom.irc import highlight_user
    reply = highlight_user(sender_nick, "Hello!")
    # Result: "alice: Hello!"

    await backend.send_message(channel, reply)

    await backend.disconnect()

asyncio.run(run_bot())
```

### IRC-Specific Features

#### Mentions

IRC doesn't have formal mentions. Instead, users are highlighted by name:

```python
from chatom.irc import mention_user, highlight_user

# Simple mention (just the nick)
mention = backend.mention_user(user)  # "alice"

# Highlight (nick: message)
highlight = highlight_user("alice", "Check this out!")
# Result: "alice: Check this out!"
```

#### Actions (/me)

```python
# Send an action message (like /me waves)
await backend.send_action("#general", "waves hello")
# Appears as: * mybot waves hello
```

#### Notices

```python
# Send a notice (displayed differently from regular messages)
await backend.send_notice("alice", "This is a notice")
```

#### Channel Management

```python
# Join a channel
await backend.join_channel("#newchannel")

# Join with a key (password)
await backend.join_channel("#private", key="secretkey")

# Leave a channel
await backend.leave_channel("#oldchannel", message="Goodbye!")
```

#### Important Limitations

| Feature | Support |
|---------|---------|
| Message history | ❌ (requires a bouncer) |
| Reactions | ❌ |
| Threads | ❌ |
| Read receipts | ❌ |
| Presence | Limited (AWAY only) |
| File attachments | Limited (DCC or URLs) |

---

## Email

Email backend for asynchronous communication.

### Configuration

```python
from chatom.email import EmailBackend, EmailConfig

config = EmailConfig(
    smtp_host="smtp.example.com",        # SMTP server for sending
    smtp_port=587,                        # SMTP port
    smtp_use_tls=True,                    # Use STARTTLS
    imap_host="imap.example.com",        # IMAP server for receiving
    imap_port=993,                        # IMAP port
    imap_use_ssl=True,                    # Use SSL for IMAP
    username="bot@example.com",          # Login username
    password="your-password",            # Login password
    from_address="bot@example.com",      # From address
    from_name="My Bot",                  # From display name
)

backend = EmailBackend(config=config)
```

### Configuration Options

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `smtp_host` | `str` | No* | SMTP server hostname |
| `smtp_port` | `int` | No | SMTP port (default: 587) |
| `smtp_use_ssl` | `bool` | No | Use SSL for SMTP |
| `smtp_use_tls` | `bool` | No | Use STARTTLS (default: True) |
| `imap_host` | `str` | No* | IMAP server hostname |
| `imap_port` | `int` | No | IMAP port (default: 993) |
| `imap_use_ssl` | `bool` | No | Use SSL for IMAP (default: True) |
| `username` | `str` | No | Login username |
| `password` | `SecretStr` | No | Login password |
| `from_address` | `str` | No | From email address |
| `from_name` | `str` | No | From display name |
| `default_mailbox` | `str` | No | Default mailbox (default: "INBOX") |
| `signature` | `str` | No | Email signature to append |

*At least one of `smtp_host` or `imap_host` is required.

### Simple Bot Example

```python
import asyncio
from chatom.email import EmailBackend, EmailConfig

async def run_bot():
    config = EmailConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_use_tls=True,
        imap_host="imap.example.com",
        imap_port=993,
        imap_use_ssl=True,
        username="bot@example.com",
        password="your-password",
        from_address="bot@example.com",
        from_name="My Bot",
    )
    backend = EmailBackend(config=config)

    await backend.connect()
    print("Connected to email server")

    # Fetch recent emails from inbox
    # In email, "channel_id" is the mailbox name
    messages = await backend.fetch_messages("INBOX", limit=10)

    for message in messages:
        # Check if the subject contains "hi emailbot"
        if message.content and "hi emailbot" in message.content.lower():
            # Get the sender
            author = await backend.fetch_user(message.user_id)
            if author:
                # Reply with a greeting
                # For email, channel_id is the recipient email
                reply_content = f"Hello {author.name}!\n\nThank you for your message."
                await backend.send_message(
                    author.email,
                    reply_content,
                    subject=f"Re: {message.subject}",
                )

    await backend.disconnect()

asyncio.run(run_bot())
```

### Email-Specific Features

#### Mentions

Email mentions are formatted as mailto links:

```python
from chatom.email import mention_user

# Creates an HTML mailto link
mention = backend.mention_user(user)
# <a href='mailto:alice@example.com'>Alice Smith</a>
```

#### Sending with HTML

```python
from chatom import FormattedMessage, Bold, Text, Paragraph, Format

msg = FormattedMessage(
    content=[
        Paragraph(children=[
            Bold(child=Text(content="Important Update")),
        ]),
        Paragraph(children=[
            Text(content="Please review the attached document."),
        ]),
    ]
)

# Render as HTML for email
html_content = msg.render(Format.HTML)
await backend.send_message(
    "recipient@example.com",
    html_content,
    subject="Important Update",
    content_type="text/html",
)
```

#### Important Notes

| Feature | Support |
|---------|---------|
| Message history | ✅ (via IMAP) |
| Threads | ✅ (via In-Reply-To headers) |
| Reactions | ❌ |
| Presence | ❌ |
| Real-time | ❌ (polling required) |
| Attachments | ✅ |

---

## Synchronous Usage

All backends support synchronous operations via the `sync` helper:

```python
from chatom.slack import SlackBackend, SlackConfig

backend = SlackBackend(config=SlackConfig(bot_token="xoxb-..."))

# Use sync helper for all operations
backend.sync.connect()

# Fetch messages synchronously
messages = backend.sync.fetch_messages("C123456", limit=10)

# Send a message
backend.sync.send_message("C123456", "Hello!")

# Lookup users and channels
user = backend.sync.fetch_user("U123456")
channel = backend.sync.fetch_channel("C123456")

backend.sync.disconnect()
```

---

## Mock Backends for Testing

Each backend has a mock implementation for testing:

```python
from chatom.slack import MockSlackBackend

# Create mock backend (no real connection needed)
backend = MockSlackBackend()

# Add test data
backend.add_mock_user("U123", "Test User", "testuser")
backend.add_mock_channel("C123", "general")
backend.add_mock_message("C123", "U123", "hi slackbot")

# Use like a real backend
await backend.connect()
messages = await backend.fetch_messages("C123")

# Send a message (tracked for verification)
await backend.send_message("C123", "Hello!")

# Verify what was sent
assert len(backend.sent_messages) == 1
assert backend.sent_messages[0]["content"] == "Hello!"

# Reset for next test
backend.reset()
```

See [Mock Backends](backends.md#mock-backends-for-testing) for more details.
