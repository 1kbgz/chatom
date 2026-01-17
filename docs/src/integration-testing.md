# Integration Testing

This guide explains how to run end-to-end integration tests for each backend.
These tests verify that your credentials and permissions are set up correctly
and that all backend functionality works as expected.

## Overview

Integration tests are located in `chatom/tests/integration/` and are designed
to be run as standalone scripts. They require:

1. Real credentials for the target platform
2. A test channel/room where the bot can send messages
3. Human interaction to verify the bot's behavior

Each test will:
- Connect to the platform
- Test all available functionality
- Send messages to the test channel
- Report which tests passed/failed

## Running Tests

Tests are run as standalone Python scripts:

```bash
python -m chatom.tests.integration.<backend>_e2e
```

For example:
```bash
python -m chatom.tests.integration.discord_e2e
python -m chatom.tests.integration.slack_e2e
python -m chatom.tests.integration.symphony_e2e
python -m chatom.tests.integration.matrix_e2e
python -m chatom.tests.integration.irc_e2e
python -m chatom.tests.integration.email_e2e
```

---

## Discord Integration Test

### Prerequisites

1. **Create a Discord Application** at [Discord Developer Portal](https://discord.com/developers/applications)
2. **Create a Bot** under the application
3. **Copy the Bot Token**
4. **Enable Required Intents**:
   - Presence Intent (optional, for presence tests)
   - Server Members Intent (optional, for member tests)
   - Message Content Intent (required for reading message content)
5. **Invite the bot** to your test server with appropriate permissions

### Required Scopes and Permissions

When creating the invite URL, include:

**Scopes:**
- `bot`
- `applications.commands` (if using slash commands)

**Bot Permissions:**
- Send Messages
- Read Message History
- Add Reactions
- Manage Messages (for reaction removal)
- Create Public Threads (for thread tests)

### Environment Variables

```bash
export DISCORD_BOT_TOKEN="your-bot-token"
export DISCORD_TEST_CHANNEL_ID="123456789012345678"
export DISCORD_TEST_USER_ID="987654321098765432"
export DISCORD_TEST_GUILD_ID="111222333444555666"  # Optional
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Bot token from Developer Portal |
| `DISCORD_TEST_CHANNEL_ID` | Yes | Text channel ID for tests |
| `DISCORD_TEST_USER_ID` | Yes | Your user ID for mention tests |
| `DISCORD_TEST_GUILD_ID` | No | Guild ID for guild-specific tests |

### Getting IDs

Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode),
then right-click on channels/users/servers to copy their IDs.

### Run

```bash
python -m chatom.tests.integration.discord_e2e
```

### What's Tested

| Feature | Test Description |
|---------|-----------------|
| Connection | Connect to Discord gateway |
| Plain Messages | Send simple text messages |
| Formatted Messages | Bold, italic, code blocks |
| Fetch User | Look up user by ID |
| Fetch Channel | Look up channel by ID |
| Mentions | User and channel mentions |
| Reactions | Add and remove emoji reactions |
| Threads | Create threads and reply |
| Rich Content | Tables rendered in Discord markdown |
| Message History | Fetch recent messages |
| Presence | Set bot status |

---

## Slack Integration Test

### Prerequisites

1. **Create a Slack App** at [Slack API](https://api.slack.com/apps)
2. **Install to Workspace**
3. **Copy the Bot Token** (starts with `xoxb-`)
4. **Add Required Scopes**

### Required OAuth Scopes

Add these under **OAuth & Permissions**:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages |
| `channels:read` | Read channel info |
| `channels:history` | Read message history (public channels) |
| `groups:history` | Read message history (private channels) |
| `users:read` | Read user info |
| `reactions:write` | Add reactions |
| `reactions:read` | Read reactions |
| `im:write` | Create DMs |
| `users.profile:write` | Set status (optional, requires user token) |
| `connections:write` | Socket Mode (optional, for inbound messages) |

### Environment Variables

```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_TEST_CHANNEL_NAME="test-channel"  # Channel name without #
export SLACK_TEST_USER_NAME="john.doe"  # Username without @
export SLACK_APP_TOKEN="xapp-your-app-token"  # Optional, for Socket Mode
```

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Bot OAuth token (xoxb-...) |
| `SLACK_TEST_CHANNEL_NAME` | Yes | Channel name for tests (without #) |
| `SLACK_TEST_USER_NAME` | Yes | Username for mention tests (without @) |
| `SLACK_APP_TOKEN` | No | App token for Socket Mode (enables inbound message test) |

### Finding Channel/User Names

- **Channel Name**: The channel name as shown in Slack (without the #)
- **User Name**: The username or display name as shown in user profiles

### Run

```bash
python -m chatom.tests.integration.slack_e2e
```

### What's Tested

| Feature | Test Description |
|---------|-----------------|
| Connection | Connect and authenticate |
| Channel/User Lookup | Look up by name to get IDs |
| Plain Messages | Send simple text messages |
| Formatted Messages | mrkdwn formatting (bold, italic, code) |
| Fetch User | Look up user by ID |
| Fetch Channel | Look up channel by ID |
| Mentions | User, channel, @here, @channel, @everyone |
| Reactions | Add and remove emoji reactions |
| Threads | Create threads and reply |
| Rich Content | Tables in mrkdwn format |
| Message History | Fetch recent messages |
| Presence | Get user status |
| DM Creation | Create direct messages |
| Inbound Messages | Receive and parse bot mentions (requires Socket Mode) |

---

## Symphony Integration Test

### Prerequisites

1. **Symphony Bot Account** configured by your Symphony administrator
2. **RSA Key Pair** for authentication
3. **Bot Service Account** with appropriate entitlements

### Required Entitlements

Your bot needs:
- Send messages to streams
- Read messages from streams
- Look up users
- Set presence

### Environment Variables

```bash
export SYMPHONY_HOST="mycompany.symphony.com"
export SYMPHONY_BOT_USERNAME="my-bot"
export SYMPHONY_BOT_PRIVATE_KEY_PATH="/path/to/private-key.pem"
export SYMPHONY_TEST_ROOM_NAME="E2E Test Room"
export SYMPHONY_TEST_USER_NAME="jsmith"
```

Or use key content directly:
```bash
export SYMPHONY_BOT_PRIVATE_KEY_CONTENT="-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----"
```

Or use a combined certificate (key+cert in one PEM file):
```bash
export SYMPHONY_BOT_COMBINED_CERT_PATH="/path/to/combined.pem"
# or
export SYMPHONY_BOT_COMBINED_CERT_CONTENT="-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----"
```

| Variable | Required | Description |
|----------|----------|-------------|
| `SYMPHONY_HOST` | Yes | Pod hostname |
| `SYMPHONY_BOT_USERNAME` | Yes | Bot service account name |
| `SYMPHONY_BOT_PRIVATE_KEY_PATH` | Yes* | Path to RSA private key |
| `SYMPHONY_BOT_PRIVATE_KEY_CONTENT` | Yes* | RSA key content (alternative) |
| `SYMPHONY_BOT_COMBINED_CERT_PATH` | Yes* | Path to combined cert file (key+cert in PEM) |
| `SYMPHONY_BOT_COMBINED_CERT_CONTENT` | Yes* | Combined cert content (key+cert in PEM) |
| `SYMPHONY_TEST_ROOM_NAME` | Yes | Room name for tests (looked up automatically) |
| `SYMPHONY_TEST_USER_NAME` | Yes | Username for mention tests (looked up automatically) |
| `SYMPHONY_AGENT_HOST` | No | Separate agent hostname |
| `SYMPHONY_SESSION_AUTH_HOST` | No | Separate session auth hostname |
| `SYMPHONY_KEY_MANAGER_HOST` | No | Separate key manager hostname |

*One of private key (`_PATH` or `_CONTENT`) or combined cert (`_PATH` or `_CONTENT`) is required.

### Getting Room Name

In Symphony, the room name is the display name shown in the room header.
The test will automatically look up the room by name to get its stream ID.

### Run

```bash
python -m chatom.tests.integration.symphony_e2e
```

### What's Tested

| Feature | Test Description |
|---------|-----------------|
| Connection | Authenticate with RSA key or combined cert |
| Room Lookup | Search room by name to get stream ID |
| User Lookup | Search user by username to get user ID |
| Plain Messages | Send MessageML messages |
| MessageML Formatting | Native Symphony formatting |
| Format System | Convert FormattedMessage to MessageML |
| Fetch User | Look up user by ID |
| Mentions | `<mention uid="..."/>` tags |
| Hashtags | `<hash tag="..."/>` tags |
| Cashtags | `<cash tag="..."/>` (stock tickers) |
| Rich Content | Tables in MessageML |
| Message History | Fetch and parse PresentationML |
| Presence | Get/set presence status |
| DM/IM Creation | Create 1:1 DMs and multi-party IMs |
| Room Creation | Create private rooms |
| Inbound Messages | Receive messages via datafeed, detect bot mentions |

---

## Matrix Integration Test

### Prerequisites

1. **Matrix Homeserver** account
2. **Access Token** for your bot user
3. **Bot joined to test room**

### Getting an Access Token

```bash
# Using the Matrix API
curl -X POST "https://matrix.example.com/_matrix/client/r0/login" \
  -H "Content-Type: application/json" \
  -d '{"type":"m.login.password","user":"@bot:example.com","password":"yourpassword"}'
```

### Environment Variables

```bash
export MATRIX_HOMESERVER_URL="https://matrix.example.com"
export MATRIX_ACCESS_TOKEN="syt_your_access_token"
export MATRIX_USER_ID="@mybot:example.com"
export MATRIX_TEST_ROOM_ID="!abc123:example.com"
export MATRIX_TEST_USER_ID="@testuser:example.com"
export MATRIX_DEVICE_ID="MYDEVICE"  # Optional
```

| Variable | Required | Description |
|----------|----------|-------------|
| `MATRIX_HOMESERVER_URL` | Yes | Homeserver URL |
| `MATRIX_ACCESS_TOKEN` | Yes | Bot's access token |
| `MATRIX_USER_ID` | Yes | Bot's Matrix ID (@user:server) |
| `MATRIX_TEST_ROOM_ID` | Yes | Room ID for tests (!room:server) |
| `MATRIX_TEST_USER_ID` | Yes | User ID for mention tests |
| `MATRIX_DEVICE_ID` | No | Device ID for E2EE |

### Run

```bash
python -m chatom.tests.integration.matrix_e2e
```

### What's Tested

| Feature | Test Description |
|---------|-----------------|
| Connection | Connect to homeserver |
| Plain Messages | Send simple text |
| HTML Messages | Native HTML formatting |
| Format System | Convert FormattedMessage to HTML |
| Fetch User | Look up user profile |
| Mentions | Matrix user pills |
| Reactions | Add/remove emoji annotations |
| Rich Content | HTML tables |
| Message History | Fetch room messages |
| Presence | Get/set presence |

---

## IRC Integration Test

### Prerequisites

1. **IRC Server** to connect to (e.g., Libera.Chat)
2. **Registered Nickname** (optional but recommended)
3. **Test Channel** where bot can join

### Environment Variables

```bash
export IRC_SERVER="irc.libera.chat"
export IRC_PORT="6697"
export IRC_NICKNAME="chatom-test-bot"
export IRC_TEST_CHANNEL="#chatom-test"
export IRC_USE_SSL="true"
export IRC_NICKSERV_PASSWORD="your-nickserv-password"  # Optional
```

| Variable | Required | Description |
|----------|----------|-------------|
| `IRC_SERVER` | Yes | IRC server hostname |
| `IRC_PORT` | No | Server port (default: 6667) |
| `IRC_NICKNAME` | Yes | Bot's nickname |
| `IRC_TEST_CHANNEL` | Yes | Channel for tests (with #) |
| `IRC_USE_SSL` | No | Use SSL (default: false) |
| `IRC_PASSWORD` | No | Server password |
| `IRC_NICKSERV_PASSWORD` | No | NickServ password |

### Run

```bash
python -m chatom.tests.integration.irc_e2e
```

### What's Tested

| Feature | Test Description |
|---------|-----------------|
| Connection | Connect to IRC server |
| Plain Messages | Send PRIVMSG |
| Formatted Messages | Rendered as plain text |
| Actions | /me messages (CTCP ACTION) |
| Notices | NOTICE messages |
| User Highlights | "nick: message" format |
| Channel Operations | JOIN and PART |
| Rich Content | Tables as plain text |
| Presence | AWAY status |

### IRC Limitations

| Feature | Supported |
|---------|-----------|
| Message History | ❌ (requires bouncer) |
| Reactions | ❌ |
| Threads | ❌ |
| Read Receipts | ❌ |
| Presence | ⚠️ (AWAY only) |
| Attachments | ⚠️ (URLs or DCC) |

---

## Email Integration Test

### Prerequisites

1. **SMTP Server** for sending
2. **IMAP Server** for receiving
3. **Email Account** with credentials

### Gmail Setup

For Gmail, you need an **App Password**:

1. Enable 2-Factor Authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Create a new App Password for "Mail"
4. Use this password for `EMAIL_PASSWORD`

### Environment Variables

```bash
# Gmail example
export EMAIL_SMTP_HOST="smtp.gmail.com"
export EMAIL_SMTP_PORT="587"
export EMAIL_IMAP_HOST="imap.gmail.com"
export EMAIL_IMAP_PORT="993"
export EMAIL_USERNAME="yourbot@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export EMAIL_FROM_ADDRESS="yourbot@gmail.com"
export EMAIL_FROM_NAME="Test Bot"
export EMAIL_TEST_RECIPIENT="you@example.com"
```

| Variable | Required | Description |
|----------|----------|-------------|
| `EMAIL_SMTP_HOST` | Yes | SMTP server hostname |
| `EMAIL_SMTP_PORT` | No | SMTP port (default: 587) |
| `EMAIL_IMAP_HOST` | Yes | IMAP server hostname |
| `EMAIL_IMAP_PORT` | No | IMAP port (default: 993) |
| `EMAIL_USERNAME` | Yes | Login username |
| `EMAIL_PASSWORD` | Yes | Login password |
| `EMAIL_FROM_ADDRESS` | Yes | From email address |
| `EMAIL_FROM_NAME` | No | From display name |
| `EMAIL_TEST_RECIPIENT` | Yes | Recipient for tests |
| `EMAIL_SMTP_USE_TLS` | No | Use STARTTLS (default: true) |
| `EMAIL_SMTP_USE_SSL` | No | Use SSL for SMTP (default: false) |
| `EMAIL_IMAP_USE_SSL` | No | Use SSL for IMAP (default: true) |

### Run

```bash
python -m chatom.tests.integration.email_e2e
```

### What's Tested

| Feature | Test Description |
|---------|-----------------|
| Connection | Connect to SMTP and IMAP |
| Plain Text Email | Send simple text email |
| HTML Email | Send formatted HTML email |
| Format System | Convert FormattedMessage to HTML |
| Mentions | mailto: links in HTML |
| Threading | In-Reply-To headers |
| Fetch Emails | Read from INBOX via IMAP |
| Rich Content | HTML tables |

### Email Limitations

| Feature | Supported |
|---------|-----------|
| Message History | ✅ (via IMAP) |
| Threads | ✅ (via headers) |
| Attachments | ✅ |
| HTML Formatting | ✅ |
| Reactions | ❌ |
| Presence | ❌ |
| Real-time | ❌ (polling) |

---

## Troubleshooting

### Common Issues

#### "Module not found" errors
Ensure chatom is installed:
```bash
pip install -e .
# or
uv pip install -e .
```

#### Authentication failures
- Verify your credentials are correct
- Check that tokens haven't expired
- Ensure the bot has been invited/added to the test channel

#### Permission errors
- Verify the bot has required permissions/scopes
- Check that the bot has access to the test channel
- Review the platform's permission documentation

#### Rate limiting
- The tests include delays between operations
- If you see rate limit errors, wait and try again
- Consider using a less busy test channel

### Debug Mode

Add verbose output by setting:
```bash
export CHATOM_DEBUG=1
python -m chatom.tests.integration.slack_e2e
```

### Reporting Issues

If a test fails unexpectedly:

1. Check the error message for details
2. Verify environment variables are set correctly
3. Ensure the backend library is installed (e.g., `discord.py`, `slack_sdk`)
4. Check platform-specific documentation for changes

---

## Writing Custom Integration Tests

You can use the existing tests as templates for your own integration tests.
Key patterns:

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig

async def my_custom_test():
    # Read config from environment
    config = SlackConfig(bot_token=os.environ["SLACK_BOT_TOKEN"])
    backend = SlackBackend(config=config)

    # Connect
    await backend.connect()

    try:
        # Your test code here
        await backend.send_message("C123", "Test message")
        messages = await backend.fetch_messages("C123", limit=5)

        for msg in messages:
            formatted = msg.to_formatted()
            print(formatted.render(Format.PLAINTEXT))
    finally:
        # Always disconnect
        await backend.disconnect()

if __name__ == "__main__":
    asyncio.run(my_custom_test())
```

---

## Feature Comparison

| Feature | Discord | Slack | Symphony | Matrix | IRC | Email |
|---------|---------|-------|----------|--------|-----|-------|
| Messages | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Formatting | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Reactions | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Threads | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Mentions | ✅ | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| History | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Presence | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ |
| Attachments | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Real-time | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

**Legend:**
- ✅ Fully supported
- ⚠️ Limited support
- ❌ Not supported
