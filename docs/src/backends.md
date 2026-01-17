# Backends

chatom provides specialized implementations for each supported chat platform.

## Configuration

Each backend has a corresponding configuration class that holds platform-specific settings. All configuration classes inherit from `BackendConfig` and use Pydantic for validation.

### SlackConfig

```python
from chatom.slack import SlackBackend, SlackConfig

config = SlackConfig(
    bot_token="xoxb-your-bot-token",      # Bot OAuth token (required)
    app_token="xapp-your-app-token",       # App token for Socket Mode
    signing_secret="your-signing-secret",  # Request signing secret
    team_id="T123456789",                  # Workspace ID
    socket_mode=True,                      # Enable Socket Mode
)

backend = SlackBackend(config=config)
await backend.connect()
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot_token` | `SecretStr` | Yes | Bot OAuth token (xoxb-...) |
| `app_token` | `SecretStr` | No | App token for Socket Mode (xapp-...) |
| `signing_secret` | `SecretStr` | No | Request signing secret |
| `team_id` | `str` | No | Workspace ID |
| `socket_mode` | `bool` | No | Enable Socket Mode (default: False) |

### DiscordConfig

```python
from chatom.discord import DiscordBackend, DiscordConfig

config = DiscordConfig(
    bot_token="your-discord-bot-token",   # Bot token (required)
    application_id="123456789",            # Application ID
    guild_id="987654321",                  # Default guild ID
    intents=["guilds", "messages", "presences"],  # Gateway intents
)

backend = DiscordBackend(config=config)
await backend.connect()
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `bot_token` | `SecretStr` | Yes | Discord bot token |
| `application_id` | `str` | No | Application ID |
| `guild_id` | `str` | No | Default guild ID for operations |
| `intents` | `List[str]` | No | Gateway intents to enable |
| `shard_id` | `int` | No | Shard ID for sharding |
| `shard_count` | `int` | No | Total shard count |

### MatrixConfig

```python
from chatom.matrix import MatrixBackend, MatrixConfig

config = MatrixConfig(
    homeserver_url="https://matrix.example.com",  # Homeserver URL (required)
    access_token="your-access-token",              # Access token (required)
    user_id="@bot:example.com",                    # Bot's user ID
    device_id="BOTDEVICE",                         # Device ID
)

backend = MatrixBackend(config=config)
await backend.connect()
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `homeserver_url` | `str` | Yes | Matrix homeserver URL |
| `access_token` | `SecretStr` | Yes | Access token for authentication |
| `user_id` | `str` | No | Bot's Matrix user ID |
| `device_id` | `str` | No | Device ID for E2EE |
| `sync_filter_limit` | `int` | No | Limit for sync filter (default: 100) |

### IRCConfig

```python
from chatom.irc import IRCBackend, IRCConfig

config = IRCConfig(
    server="irc.libera.chat",           # IRC server (required)
    port=6697,                           # Port (default: 6667)
    nickname="mybot",                    # Bot nickname (required)
    username="mybot",                    # Username (default: nickname)
    password="server-password",          # Server password
    nickserv_password="ns-password",     # NickServ password
    use_ssl=True,                        # Use SSL/TLS
    auto_join_channels=["#general"],     # Channels to auto-join
)

backend = IRCBackend(config=config)
await backend.connect()
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server` | `str` | Yes | IRC server hostname |
| `port` | `int` | No | Server port (default: 6667) |
| `nickname` | `str` | Yes | Bot's nickname |
| `username` | `str` | No | Username (defaults to nickname) |
| `realname` | `str` | No | Real name field |
| `password` | `SecretStr` | No | Server password |
| `nickserv_password` | `SecretStr` | No | NickServ identification password |
| `use_ssl` | `bool` | No | Enable SSL/TLS (default: False) |
| `auto_join_channels` | `List[str]` | No | Channels to join on connect |

### EmailConfig

```python
from chatom.email import EmailBackend, EmailConfig

config = EmailConfig(
    smtp_host="smtp.example.com",        # SMTP server
    smtp_port=587,                        # SMTP port
    smtp_use_tls=True,                    # Use STARTTLS
    imap_host="imap.example.com",        # IMAP server
    imap_port=993,                        # IMAP port
    imap_use_ssl=True,                    # Use SSL for IMAP
    username="bot@example.com",          # Login username
    password="your-password",            # Login password
    from_address="bot@example.com",      # From address
    from_name="Bot",                     # From display name
)

backend = EmailBackend(config=config)
await backend.connect()
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `smtp_host` | `str` | No* | SMTP server hostname |
| `smtp_port` | `int` | No | SMTP port (default: 587) |
| `smtp_use_ssl` | `bool` | No | Use SSL for SMTP (default: False) |
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

### SymphonyConfig

```python
from chatom.symphony import SymphonyBackend, SymphonyConfig

config = SymphonyConfig(
    host="mycompany.symphony.com",             # Pod hostname (required)
    bot_username="mybot",                       # Bot username (required)
    bot_private_key_path="/path/to/key.pem",   # RSA private key path
)

backend = SymphonyBackend(config=config)
await backend.connect()
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | `str` | Yes | Symphony pod hostname |
| `port` | `int` | No | Pod port (default: 443) |
| `scheme` | `str` | No | URL scheme (default: "https") |
| `bot_username` | `str` | Yes | Bot's service account username |
| `bot_private_key_path` | `str` | No* | Path to RSA private key file |
| `bot_private_key_content` | `SecretStr` | No* | RSA private key content |
| `bot_certificate_path` | `str` | No* | Path to certificate (for cert auth) |
| `bot_certificate_content` | `SecretStr` | No* | Certificate content (PEM); temp file created automatically |
| `bot_certificate_password` | `SecretStr` | No | Certificate password |
| `app_id` | `str` | No | Extension app ID |
| `agent_host` | `str` | No | Separate agent hostname |
| `agent_port` | `int` | No | Separate agent port |
| `session_auth_host` | `str` | No | Separate session auth hostname |
| `session_auth_port` | `int` | No | Separate session auth port |
| `key_manager_host` | `str` | No | Separate key manager hostname |
| `key_manager_port` | `int` | No | Separate key manager port |
| `proxy_host` | `str` | No | Proxy hostname |
| `proxy_port` | `int` | No | Proxy port |

*One of `bot_private_key_path`, `bot_private_key_content`, `bot_certificate_path`, or `bot_certificate_content` is required.

**Note:** When using `bot_certificate_content`, the config will automatically create a temporary file (Symphony BDK requires a file path). The temp file is cleaned up automatically on process exit, or you can call `config.cleanup_temp_cert()` for explicit cleanup.

---

## Mock Backends for Testing

Each backend has a corresponding mock implementation for testing without real API connections:

```python
from chatom.slack import MockSlackBackend, SlackConfig
from chatom.discord import MockDiscordBackend, DiscordConfig
from chatom.matrix import MockMatrixBackend, MatrixConfig
from chatom.irc import MockIRCBackend, IRCConfig
from chatom.email import MockEmailBackend, EmailConfig
from chatom.symphony import MockSymphonyBackend, SymphonyConfig

# Create a mock backend
backend = MockSlackBackend()

# Add mock data
backend.add_mock_user("U123", "Test User", "testuser")
backend.add_mock_channel("C123", "general")
backend.add_mock_message("C123", "U123", "Hello!")

# Use like a real backend
await backend.connect()
messages = await backend.fetch_messages("C123")

# Verify operations
await backend.send_message("C123", "Response")
assert len(backend.sent_messages) == 1

# Reset for next test
backend.reset()
```

### Mock Backend Features

| Feature | Description |
|---------|-------------|
| `add_mock_user()` | Add a user to mock data |
| `add_mock_channel()` | Add a channel/room to mock data |
| `add_mock_message()` | Add a message to mock data |
| `set_mock_presence()` | Set presence for a mock user |
| `sent_messages` | List of sent messages for verification |
| `edited_messages` | List of edited message records |
| `deleted_messages` | List of deleted message IDs |
| `presence_changes` | List of presence change records |
| `reset()` | Clear all mock data and tracking |

---

## Discord

### Models

```python
from chatom.discord import (
    DiscordUser,
    DiscordChannel,
    DiscordChannelType,
    DiscordPresence,
    DiscordPresenceStatus,
)
```

#### DiscordUser

```python
user = DiscordUser(
    id="123456789012345678",
    name="Alice",
    discriminator="1234",
    global_name="Alice Smith",
    is_bot=False,
    avatar="abc123",
    banner="def456",
)
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `discriminator` | `str` | User's discriminator (legacy) |
| `global_name` | `str` | User's global display name |
| `avatar` | `str` | Avatar hash |
| `banner` | `str` | Banner hash |

#### DiscordChannel

```python
channel = DiscordChannel(
    id="987654321098765432",
    name="general",
    channel_type=DiscordChannelType.GUILD_TEXT,
    guild_id="111222333444555666",
    position=0,
    nsfw=False,
)
```

**Channel Types:**

| Type | Description |
|------|-------------|
| `GUILD_TEXT` | Text channel in a server |
| `DM` | Direct message |
| `GUILD_VOICE` | Voice channel |
| `GROUP_DM` | Group DM |
| `GUILD_CATEGORY` | Category |
| `GUILD_ANNOUNCEMENT` | Announcement channel |
| `GUILD_STAGE_VOICE` | Stage channel |
| `GUILD_FORUM` | Forum channel |

### Mentions

```python
from chatom.discord import (
    mention_user,
    mention_channel,
    mention_role,
    mention_everyone,
    mention_here,
)

# User mention
user = DiscordUser(id="123", name="alice")
print(mention_user(user))  # "<@123>"

# Channel mention
channel = DiscordChannel(id="456", name="general")
print(mention_channel(channel))  # "<#456>"

# Role mention
print(mention_role("789"))  # "<@&789>"

# Special mentions
print(mention_everyone())  # "@everyone"
print(mention_here())      # "@here"
```

---

## Slack

### Models

```python
from chatom.slack import (
    SlackUser,
    SlackChannel,
    SlackPresence,
    SlackPresenceStatus,
)
```

#### SlackUser

```python
user = SlackUser(
    id="U123456789",
    name="alice",
    real_name="Alice Smith",
    display_name="Alice",
    team_id="T123456789",
    is_admin=False,
    is_owner=False,
    tz="America/New_York",
    status_text="Working",
    status_emoji=":computer:",
)
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `real_name` | `str` | User's real name |
| `display_name` | `str` | Display name in workspace |
| `team_id` | `str` | Workspace ID |
| `is_admin` | `bool` | Workspace admin |
| `is_owner` | `bool` | Workspace owner |
| `tz` | `str` | Timezone identifier |
| `status_text` | `str` | Status message |
| `status_emoji` | `str` | Status emoji |

#### SlackChannel

```python
channel = SlackChannel(
    id="C123456789",
    name="general",
    is_channel=True,
    is_private=False,
    is_archived=False,
    creator="U111111",
    purpose="General discussion",
    topic="Welcome!",
    num_members=50,
)
```

### Mentions

```python
from chatom.slack import (
    mention_user,
    mention_channel,
    mention_user_group,
    mention_here,
    mention_channel_all,
    mention_everyone,
)

# User mention
print(mention_user(user))  # "<@U123456789>"

# Channel mention
print(mention_channel(channel))  # "<#C123456789>"

# User group
print(mention_user_group("S123"))  # "<!subteam^S123>"

# Special mentions
print(mention_here())        # "<!here>"
print(mention_channel_all()) # "<!channel>"
print(mention_everyone())    # "<!everyone>"
```

---

## Symphony

### Models

```python
from chatom.symphony import (
    SymphonyUser,
    SymphonyChannel,
    SymphonyStreamType,
    SymphonyPresence,
    SymphonyPresenceStatus,
)
```

#### SymphonyUser

```python
user = SymphonyUser(
    id="123",
    name="alice",
    user_id=123456789,
    email="alice@company.com",
    first_name="Alice",
    last_name="Smith",
    company="ACME Corp",
    department="Engineering",
    title="Software Engineer",
)
```

#### SymphonyChannel

```python
channel = SymphonyChannel(
    id="abc123",
    name="Project Chat",
    stream_id="xyz789",
    stream_type=SymphonyStreamType.ROOM,
    external=False,
    cross_pod=False,
)
```

**Stream Types:**

| Type | Description |
|------|-------------|
| `IM` | Instant message (1:1) |
| `MIM` | Multi-party IM |
| `ROOM` | Chat room |
| `POST` | Wall post |

### Mentions

```python
from chatom.symphony import (
    mention_user,
    mention_user_by_email,
    format_hashtag,
    format_cashtag,
)

# User mention
print(mention_user(user))  # '<mention uid="123456789"/>'

# Mention by email
print(mention_user_by_email("alice@company.com"))
# '<mention email="alice@company.com"/>'

# Hashtags and cashtags
print(format_hashtag("python"))  # '<hash tag="python"/>'
print(format_cashtag("AAPL"))    # '<cash tag="AAPL"/>'
```

---

## Email

### Models

```python
from chatom.email import EmailUser
```

#### EmailUser

```python
user = EmailUser(
    id="alice@example.com",
    name="Alice Smith",
    email="alice@example.com",
    display_name="Alice",
)

# Get formatted email address
print(user.formatted_address)  # "Alice Smith <alice@example.com>"
```

### Mentions

```python
from chatom.email import mention_user

print(mention_user(user))
# "<a href='mailto:alice@example.com'>Alice Smith</a>"
```

---

## IRC

### Models

```python
from chatom.irc import IRCUser, IRCChannel
```

#### IRCUser

```python
user = IRCUser(
    id="alice",
    name="alice",
    nick="alice",
    ident="alice",
    host="user.irc.example.com",
    modes="o",  # operator mode
    realname="Alice Smith",
)

# Properties
print(user.hostmask)     # "alice!alice@user.irc.example.com"
print(user.is_operator)  # True (has 'o' in modes)
```

#### IRCChannel

```python
channel = IRCChannel(
    id="#general",
    name="#general",
    modes="nt",
    topic="General discussion",
    user_count=25,
)
```

### Mentions

```python
from chatom.irc import mention_user, highlight_user

# Simple mention (just the nick)
print(mention_user(user))  # "alice"

# Highlight (nick: message)
print(highlight_user("alice", "Hello there!"))  # "alice: Hello there!"
```

---

## Matrix

### Models

```python
from chatom.matrix import (
    # User
    MatrixUser,
    # Channel/Room
    MatrixChannel,
    MatrixRoom,  # Alias for MatrixChannel
    MatrixRoomType,
    MatrixJoinRule,
    MatrixGuestAccess,
    MatrixRoomVisibility,
    # Message
    MatrixMessage,
    MatrixMessageType,
    MatrixMessageFormat,
    MatrixRelationType,
    MatrixEventType,
    # Presence
    MatrixPresence,
    MatrixPresenceStatus,
)
```

#### MatrixUser

```python
user = MatrixUser(
    id="alice",
    name="Alice Smith",  # Display name
    user_id="@alice:matrix.org",
    homeserver="matrix.org",
    avatar_mxc="mxc://matrix.org/abc123",
    is_guest=False,
    deactivated=False,
    currently_active=True,
    last_active_ago=5000,  # ms since last active
)

# Properties
print(user.localpart)      # "alice"
print(user.full_user_id)   # "@alice:matrix.org"
print(user.mxid)           # "@alice:matrix.org" (alias)
print(user.server_name)    # "matrix.org"
print(user.display_name)   # "Alice Smith"

# Convert MXC avatar URL to HTTP
print(user.get_avatar_http_url("https://matrix.org"))
# "https://matrix.org/_matrix/media/r0/download/matrix.org/abc123"
```

#### MatrixChannel (MatrixRoom)

```python
channel = MatrixChannel(
    id="!abc123:matrix.org",
    name="General Chat",
    room_id="!abc123:matrix.org",
    canonical_alias="#general:matrix.org",
    aliases=["#general:matrix.org", "#chat:matrix.org"],
    room_type=MatrixRoomType.DEFAULT,  # or SPACE
    join_rule=MatrixJoinRule.INVITE,  # or PUBLIC, KNOCK, RESTRICTED
    guest_access=MatrixGuestAccess.FORBIDDEN,
    visibility=MatrixRoomVisibility.PRIVATE,
    encrypted=True,
    federated=True,
    direct=False,
    members={"@alice:matrix.org": "Alice", "@bob:matrix.org": "Bob"},
    power_levels={"users": {"@admin:matrix.org": 100}},
    unread_count=5,
    highlight_count=2,
)

# Properties
print(channel.display_name)          # "General Chat"
print(channel.homeserver)            # "matrix.org"
print(channel.is_public)             # False
print(channel.is_invite_only)        # True
print(channel.is_encrypted)          # True
print(channel.is_space)              # False
print(channel.generic_channel_type)  # ChannelType.PRIVATE
```

**Room Types:**

| Type | Description |
|------|-------------|
| `DEFAULT` | Standard room |
| `SPACE` | Matrix Space (similar to Discord server categories) |

**Join Rules:**

| Rule | Description |
|------|-------------|
| `PUBLIC` | Anyone can join |
| `INVITE` | Invite required |
| `KNOCK` | Can request to join |
| `RESTRICTED` | Space membership required |
| `PRIVATE` | Alias for invite |

#### MatrixMessage

```python
from chatom.matrix import MatrixMessage, MatrixMessageType

# Create from an event dict (e.g., from sync response)
event = {
    "event_id": "$abc123",
    "room_id": "!room:matrix.org",
    "sender": "@alice:matrix.org",
    "type": "m.room.message",
    "origin_server_ts": 1699999999999,
    "content": {
        "msgtype": "m.text",
        "body": "Hello, world!",
        "format": "org.matrix.custom.html",
        "formatted_body": "<b>Hello</b>, world!",
    },
}
msg = MatrixMessage.from_event(event)

# Or create directly
msg = MatrixMessage(
    event_id="$abc123",
    room_id="!room:matrix.org",
    sender="@alice:matrix.org",
    text="Hello, world!",
    msgtype="m.text",
    format="org.matrix.custom.html",
    formatted_body="<b>Hello</b>, world!",
)

# Properties
print(msg.is_text)              # True
print(msg.is_notice)            # False
print(msg.is_media)             # False
print(msg.is_reply)             # False
print(msg.is_edit)              # False
print(msg.has_html)             # True
print(msg.sender_localpart)     # "alice"

# Convert to content for sending
content = msg.to_content()
# {"msgtype": "m.text", "body": "Hello, world!", ...}
```

**Message Types:**

| Type | Description |
|------|-------------|
| `m.text` | Text message |
| `m.notice` | Bot/system notice |
| `m.emote` | /me action |
| `m.image` | Image |
| `m.file` | File attachment |
| `m.audio` | Audio |
| `m.video` | Video |
| `m.location` | Location |

#### MatrixPresence

```python
presence = MatrixPresence(
    user_id="@alice:matrix.org",
    matrix_presence=MatrixPresenceStatus.ONLINE,
    status_msg="Working on chatom",
    currently_active=True,
    last_active_ago=1000,
)

print(presence.generic_status)  # PresenceStatus.ONLINE
```

### Mentions

```python
from chatom.matrix import mention_user, mention_room, create_pill

# User mention
print(mention_user(user))  # "@alice:matrix.org"

# Room mention
print(mention_room("#general:matrix.org"))  # "#general:matrix.org"

# Create a "pill" (clickable mention in HTML)
print(create_pill("@alice:matrix.org", "Alice"))
# '<a href="https://matrix.to/#/@alice:matrix.org">Alice</a>'
```

---

## Polymorphic Dispatch

The base `mention_user` and `mention_channel` functions use `singledispatch` to automatically call the correct backend implementation:

```python
from chatom import mention_user, mention_channel
from chatom.discord import DiscordUser, DiscordChannel
from chatom.slack import SlackUser, SlackChannel
from chatom.base import User, Channel

# Automatically dispatches to correct implementation
discord_user = DiscordUser(id="123", name="alice")
slack_user = SlackUser(id="U123", name="alice")
base_user = User(id="base", name="alice")

print(mention_user(discord_user))  # "<@123>" (Discord format)
print(mention_user(slack_user))    # "<@U123>" (Slack format)
print(mention_user(base_user))     # "alice" (fallback to name)

# Same for channels
discord_channel = DiscordChannel(id="456", name="general")
slack_channel = SlackChannel(id="C456", name="general")

print(mention_channel(discord_channel))  # "<#456>"
print(mention_channel(slack_channel))    # "<#C456>"
```

---

## Capabilities Comparison

| Capability | Discord | Slack | Symphony | Email | IRC | Matrix |
|------------|---------|-------|----------|-------|-----|--------|
| Threads | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Emoji Reactions | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Custom Emoji | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| File Attachments | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Embeds | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Voice Chat | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Video Chat | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Typing Indicators | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Read Receipts | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Presence | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Message History | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |

---

## Backend Methods

All backends inherit from `BackendBase` and provide the following core methods:

### Connection Methods

```python
async def connect() -> None
async def disconnect() -> None
```

### User/Channel Lookup

The `fetch_user` and `fetch_channel` methods accept flexible inputs, allowing you to look up users and channels by ID, name, email, or by passing an existing object.

```python
# Flexible fetch_user - accepts multiple input types
async def fetch_user(
    identifier: Optional[Union[str, User]] = None,
    *,
    id: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    handle: Optional[str] = None,
) -> Optional[User]

# Flexible fetch_channel - accepts multiple input types
async def fetch_channel(
    identifier: Optional[Union[str, Channel]] = None,
    *,
    id: Optional[str] = None,
    name: Optional[str] = None,
) -> Optional[Channel]

# Convenience wrappers (same as fetch_*)
async def lookup_user(*, id=None, name=None, email=None, handle=None) -> Optional[User]
async def lookup_channel(*, id=None, name=None) -> Optional[Channel]
```

**Usage Examples:**

```python
# All of these work:
user = await backend.fetch_user("U123")                # By ID string
user = await backend.fetch_user(id="U123")             # By ID keyword
user = await backend.fetch_user(name="Alice")          # By display name
user = await backend.fetch_user(email="alice@ex.com")  # By email
user = await backend.fetch_user(handle="alice")        # By handle/username
user = await backend.fetch_user(existing_user)         # Pass User object

channel = await backend.fetch_channel("C123")          # By ID string
channel = await backend.fetch_channel(id="C123")       # By ID keyword
channel = await backend.fetch_channel(name="general")  # By name
channel = await backend.fetch_channel(existing_chan)   # Pass Channel object
```

**Backend-Specific Notes:**

| Backend | Email Lookup | Name/Handle Search |
|---------|--------------|-------------------|
| Slack | Uses `users.lookupByEmail` API | Searches via `users.list` |
| Symphony | Uses `list_users_by_emails` | Uses `search_users` API |
| Discord | Not available (cache only) | Cache only |
| Matrix | Not available (cache only) | Cache only |
| Email | Primary identifier | Cache only |
| IRC | Not available | Cache only |

### Message Operations

```python
async def fetch_messages(
    channel_id: str,
    limit: int = 100,
    before: Optional[str] = None,
    after: Optional[str] = None,
) -> List[Message]

async def send_message(
    channel_id: str,
    content: str,
    **kwargs,
) -> Message
```

### `fetch_messages`

Retrieves historical messages from a channel with support for pagination.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `channel_id` | `str` | required | The channel/room/stream ID to fetch messages from |
| `limit` | `int` | `100` | Maximum number of messages to return |
| `before` | `str` | `None` | Fetch messages before this message ID (for backwards pagination) |
| `after` | `str` | `None` | Fetch messages after this message ID (for forwards pagination) |

**Returns:** `List[Message]` - Messages ordered from oldest to newest.

**Backend-Specific Notes:**

| Backend | Notes |
|---------|-------|
| Discord | Uses message snowflake IDs for pagination. Limit 1-100. |
| Slack | Uses message timestamps (`ts`) for pagination. Maps to `conversations.history` API. |
| Symphony | Uses Symphony stream IDs. Pagination uses message IDs. |
| Matrix | Uses event tokens for pagination (`before`/`after` are pagination tokens). |
| Email | Uses IMAP to fetch emails. `before`/`after` can be dates or message IDs. |
| IRC | Returns empty list by default (IRC has no message history without a bouncer). |

**Example:**

```python
from chatom.discord import DiscordBackend

# Subclass and implement for your bot
class MyDiscordBot(DiscordBackend):
    async def fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        before: str = None,
        after: str = None,
    ):
        # Implementation using discord.py
        channel = self.bot.get_channel(int(channel_id))
        messages = []
        async for msg in channel.history(limit=limit, before=before, after=after):
            messages.append(self._convert_message(msg))
        return messages

# Usage
backend = MyDiscordBot()
await backend.connect()

# Fetch latest 50 messages
messages = await backend.fetch_messages("123456789", limit=50)

# Paginate backwards
older_messages = await backend.fetch_messages(
    "123456789",
    limit=50,
    before=messages[0].id  # Before the oldest message we have
)

# Sync usage
messages = backend.sync.fetch_messages("123456789", limit=50)
```

### Presence Operations

```python
async def get_presence(user_id: str) -> Optional[Presence]
async def set_presence(status: str, status_text: Optional[str] = None, **kwargs) -> None
```

### `get_presence`

Retrieves a user's current presence/online status.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | `str` | The user ID to get presence for |

**Returns:** `Optional[Presence]` - The user's presence, or `None` if not available.

**Backend-Specific Notes:**

| Backend | Notes |
|---------|-------|
| Discord | Returns presence with status, activity, and client status (desktop/mobile/web). |
| Slack | Returns presence with `auto`/`away` status. Use `users.getPresence` API. |
| Symphony | Returns Symphony-specific presence categories. |
| Matrix | Returns presence with `online`/`offline`/`unavailable` status and optional status message. |
| Email | Returns `None` (email has no presence concept). |
| IRC | Returns `None` (IRC has no native presence queries). |

### `set_presence`

Sets the current user's presence status.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | `str` | required | The presence status (platform-specific values) |
| `status_text` | `str` | `None` | Optional status message/text |
| `**kwargs` | `Any` | - | Additional platform-specific options |

**Backend-Specific Status Values:**

| Backend | Supported Status Values |
|---------|------------------------|
| Discord | `'online'`, `'idle'`, `'dnd'`, `'invisible'` |
| Slack | `'auto'`, `'away'` (also supports `status_emoji`, `status_expiration`) |
| Symphony | `'AVAILABLE'`, `'BUSY'`, `'AWAY'`, `'ON_THE_PHONE'`, `'BE_RIGHT_BACK'`, `'IN_A_MEETING'`, `'OUT_OF_OFFICE'`, `'OFF_WORK'` |
| Matrix | `'online'`, `'offline'`, `'unavailable'` |
| Email | Not supported (raises `NotImplementedError`) |
| IRC | Maps to AWAY command (any non-empty status sets AWAY with `status_text` as message) |

**Example:**

```python
from chatom.slack import SlackBackend
from chatom.base import Presence, PresenceStatus

# Subclass and implement for your app
class MySlackBot(SlackBackend):
    def __init__(self, client):
        super().__init__()
        self.client = client

    async def get_presence(self, user_id: str):
        response = await self.client.users_getPresence(user=user_id)
        return Presence(
            status=PresenceStatus.ONLINE if response["presence"] == "active" else PresenceStatus.IDLE,
            status_text=response.get("status_text", ""),
        )

    async def set_presence(self, status: str, status_text: str = None, **kwargs):
        await self.client.users_setPresence(presence=status)
        if status_text:
            await self.client.users_profile_set(
                profile={"status_text": status_text, "status_emoji": kwargs.get("status_emoji", "")}
            )

# Usage
backend = MySlackBot(client)
await backend.connect()

# Get a user's presence
presence = await backend.get_presence("U123456")
print(f"User is {'online' if presence.is_online else 'offline'}")

# Set your presence
await backend.set_presence("auto", "Working on chatom", status_emoji=":computer:")

# Sync usage
presence = backend.sync.get_presence("U123456")
backend.sync.set_presence("away", "In a meeting")
```

### Sync Helper

All async methods are available synchronously via the `sync` property:

```python
backend = DiscordBackend()
backend.sync.connect()

# Fetch messages synchronously
messages = backend.sync.fetch_messages("channel_id", limit=50)

# Get/set presence synchronously
presence = backend.sync.get_presence("user_id")
backend.sync.set_presence("online", "Available")

backend.sync.disconnect()
```


