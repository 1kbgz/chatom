# Backend Configuration

Each backend requires specific configuration. This guide covers all configuration options for each supported platform.

## Slack Configuration

### Required Settings

```python
from chatom.slack import SlackConfig

config = SlackConfig(
    bot_token="xoxb-your-bot-token",  # Required
)
```

### All Options

```python
from chatom.slack import SlackConfig

config = SlackConfig(
    # Authentication (required)
    bot_token="xoxb-your-bot-token",

    # Socket Mode (for real-time events)
    app_token="xapp-your-app-token",
    socket_mode=True,

    # Request verification
    signing_secret="your-signing-secret",

    # Workspace settings
    team_id="T123456",
    default_channel="C123456",
)
```

### Configuration Reference

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `bot_token` | `str` | Yes | Bot OAuth token (xoxb-...) |
| `app_token` | `str` | No | App token for Socket Mode (xapp-...) |
| `socket_mode` | `bool` | No | Enable Socket Mode for events |
| `signing_secret` | `str` | No | For request verification |
| `team_id` | `str` | No | Workspace/team ID |
| `default_channel` | `str` | No | Default channel for messages |

### Environment Variables

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_APP_TOKEN="xapp-your-app-token"
export SLACK_SIGNING_SECRET="your-secret"
```

```python
import os
from chatom.slack import SlackConfig

config = SlackConfig(
    bot_token=os.environ["SLACK_BOT_TOKEN"],
    app_token=os.environ.get("SLACK_APP_TOKEN", ""),
)
```

### Getting Slack Credentials

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create a new app or select existing
3. Navigate to **OAuth & Permissions**
4. Add required scopes:
   - `channels:read` - Read channel info
   - `channels:history` - Read messages
   - `chat:write` - Send messages
   - `reactions:read` - Read reactions
   - `reactions:write` - Add reactions
   - `users:read` - Read user info
5. Install to workspace
6. Copy the **Bot User OAuth Token**

For Socket Mode:
1. Navigate to **Socket Mode**
2. Enable Socket Mode
3. Copy the **App-Level Token**

---

## Discord Configuration

### Required Settings

```python
from chatom.discord import DiscordConfig

config = DiscordConfig(
    bot_token="your-bot-token",  # Required
)
```

### All Options

```python
from chatom.discord import DiscordConfig

config = DiscordConfig(
    # Authentication (required)
    bot_token="your-bot-token",

    # Application settings
    application_id="123456789",

    # Default guild
    guild_id="987654321",

    # Gateway intents
    intents=["guilds", "guild_messages", "message_content"],

    # Command prefix (for bot commands)
    command_prefix="!",

    # Sharding (for large bots)
    shard_id=0,
    shard_count=1,
)
```

### Configuration Reference

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `bot_token` | `str` | Yes | Bot token from Developer Portal |
| `application_id` | `str` | No | Discord application ID |
| `guild_id` | `str` | No | Default guild/server ID |
| `intents` | `list` | No | Gateway intents to request |
| `command_prefix` | `str` | No | Prefix for bot commands |
| `shard_id` | `int` | No | Shard ID for sharding |
| `shard_count` | `int` | No | Total shard count |

### Available Intents

| Intent | Description |
|--------|-------------|
| `guilds` | Guild create/update/delete events |
| `guild_members` | Member join/leave/update (privileged) |
| `guild_messages` | Message events in guilds |
| `message_content` | Access message content (privileged) |
| `dm_messages` | Direct message events |
| `guild_reactions` | Reaction events in guilds |

### Environment Variables

```bash
export DISCORD_TOKEN="your-bot-token"
export DISCORD_GUILD_ID="your-guild-id"
```

```python
import os
from chatom.discord import DiscordConfig

config = DiscordConfig(
    bot_token=os.environ["DISCORD_TOKEN"],
    guild_id=os.environ.get("DISCORD_GUILD_ID", ""),
)
```

### Getting Discord Credentials

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to **Bot**
4. Click **Add Bot**
5. Enable required intents:
   - **Server Members Intent** (for member lookups)
   - **Message Content Intent** (for reading message content)
6. Copy the **Token**
7. Navigate to **OAuth2 > URL Generator**
8. Select scopes: `bot`, `applications.commands`
9. Select permissions as needed
10. Use the generated URL to invite bot to your server

---

## Symphony Configuration

### Required Settings

```python
from chatom.symphony import SymphonyConfig

config = SymphonyConfig(
    host="mycompany.symphony.com",
    bot_username="my-bot",
    bot_private_key_path="/path/to/private-key.pem",
)
```

### All Options

```python
from chatom.symphony import SymphonyConfig
from pydantic import SecretStr

config = SymphonyConfig(
    # Pod configuration (required)
    host="mycompany.symphony.com",
    port=443,
    scheme="https",

    # Bot authentication (one required)
    bot_username="my-bot",
    bot_private_key_path="/path/to/private-key.pem",
    # OR
    bot_private_key_content=SecretStr("-----BEGIN RSA PRIVATE KEY-----..."),
    # OR (certificate auth)
    bot_certificate_path="/path/to/cert.pem",
    bot_certificate_content=SecretStr("-----BEGIN CERTIFICATE-----..."),

    # Separate endpoint hosts (optional)
    agent_host="agent.mycompany.symphony.com",
    session_auth_host="session.mycompany.symphony.com",
    key_manager_host="km.mycompany.symphony.com",

    # Proxy configuration
    proxy_host="proxy.mycompany.com",
    proxy_port=8080,
    proxy_username="user",
    proxy_password=SecretStr("password"),

    # Connection settings
    timeout=30,
    max_attempts=10,

    # Error handling
    error_room="error-room-stream-id",
    inform_client=True,

    # Datafeed version
    datafeed_version="v2",
)
```

### Configuration Reference

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `host` | `str` | Yes | Symphony pod hostname |
| `port` | `int` | No | Pod port (default: 443) |
| `bot_username` | `str` | Yes | Bot service account username |
| `bot_private_key_path` | `str` | * | Path to RSA private key |
| `bot_private_key_content` | `SecretStr` | * | RSA key content |
| `bot_certificate_path` | `str` | * | Path to certificate |
| `bot_certificate_content` | `SecretStr` | * | Certificate content |
| `agent_host` | `str` | No | Separate agent hostname |
| `session_auth_host` | `str` | No | Separate session auth host |
| `key_manager_host` | `str` | No | Separate key manager host |
| `timeout` | `int` | No | Request timeout (seconds) |
| `datafeed_version` | `str` | No | "v1" or "v2" |

*One authentication method required

### Environment Variables

```bash
export SYMPHONY_HOST="mycompany.symphony.com"
export SYMPHONY_BOT_USERNAME="my-bot"
export SYMPHONY_BOT_PRIVATE_KEY_PATH="/path/to/key.pem"
# OR
export SYMPHONY_BOT_PRIVATE_KEY_CONTENT="-----BEGIN RSA PRIVATE KEY-----..."
```

```python
import os
from chatom.symphony import SymphonyConfig

config = SymphonyConfig(
    host=os.environ["SYMPHONY_HOST"],
    bot_username=os.environ["SYMPHONY_BOT_USERNAME"],
    bot_private_key_path=os.environ.get("SYMPHONY_BOT_PRIVATE_KEY_PATH"),
)
```

### Getting Symphony Credentials

1. Contact your Symphony pod administrator
2. Request a bot service account
3. Generate an RSA key pair:
   ```bash
   openssl genrsa -out private-key.pem 4096
   openssl rsa -in private-key.pem -pubout -out public-key.pem
   ```
4. Provide the public key to your administrator
5. Receive your bot username and pod hostname

---

## Configuration from Files

All backends support loading tokens from files:

```python
# Slack - token file
config = SlackConfig(
    bot_token="/path/to/bot-token.txt",  # File path works too
)

# Discord - token file
config = DiscordConfig(
    bot_token="/path/to/discord-token.txt",
)
```

## Configuration Validation

Configurations are validated on creation:

```python
from pydantic import ValidationError
from chatom.slack import SlackConfig

try:
    config = SlackConfig(bot_token="invalid")  # Missing xoxb- prefix
except ValidationError as e:
    print(f"Invalid config: {e}")
```

## Next Steps

- [Backends](backends.md) - Using the backend API
- [Messaging](messaging.md) - Sending messages
- [Examples](examples.md) - Complete examples
