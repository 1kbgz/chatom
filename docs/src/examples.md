# Examples

This page references the example applications in the `chatom/examples/` directory.

## Example Applications

All examples are designed to be runnable as integration tests when the appropriate environment variables are set.

### Basic Connection
[chatom/examples/basic_connection.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/basic_connection.py)

Demonstrates connecting to different backends:

```bash
# Slack
export SLACK_BOT_TOKEN="xoxb-your-token"
python -m chatom.examples.basic_connection --backend slack

# Discord
export DISCORD_TOKEN="your-token"
python -m chatom.examples.basic_connection --backend discord

# Symphony
export SYMPHONY_HOST="mycompany.symphony.com"
export SYMPHONY_BOT_USERNAME="my-bot"
export SYMPHONY_BOT_PRIVATE_KEY_PATH="/path/to/key.pem"
python -m chatom.examples.basic_connection --backend symphony
```

### Send Message
[chatom/examples/send_message.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/send_message.py)

Send messages to channels:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_TEST_CHANNEL_NAME="general"
python -m chatom.examples.send_message --backend slack --message "Hello!"
```

### Formatted Messages
[chatom/examples/formatted_messages.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/formatted_messages.py)

Send rich formatted messages with tables:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_TEST_CHANNEL_NAME="general"
python -m chatom.examples.formatted_messages --backend slack
```

### Mentions and Reactions
[chatom/examples/mentions_and_reactions.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/mentions_and_reactions.py)

Mention users and add reactions:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_TEST_CHANNEL_NAME="general"
export SLACK_TEST_USER_NAME="alice"
python -m chatom.examples.mentions_and_reactions --backend slack
```

### Threads and Replies
[chatom/examples/threads_and_replies.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/threads_and_replies.py)

Create threads and reply to messages:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_TEST_CHANNEL_NAME="general"
python -m chatom.examples.threads_and_replies --backend slack
```

### Direct Messages
[chatom/examples/direct_messages.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/direct_messages.py)

Send direct messages to users:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_TEST_USER_NAME="alice"
python -m chatom.examples.direct_messages --backend slack
```

### Message History
[chatom/examples/message_history.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/message_history.py)

Read message history from channels:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_TEST_CHANNEL_NAME="general"
python -m chatom.examples.message_history --backend slack --limit 10
```

### Listen for Messages
[chatom/examples/listen_for_messages.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/listen_for_messages.py)

Listen for real-time messages:

```bash
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_APP_TOKEN="xapp-your-app-token"
export SLACK_TEST_CHANNEL_NAME="general"
python -m chatom.examples.listen_for_messages --backend slack --timeout 60
```

### Cross-Platform Bot
[chatom/examples/cross_platform_bot.py](https://github.com/1kbgz/chatom/blob/main/chatom/examples/cross_platform_bot.py)

Run a bot on multiple platforms simultaneously:

```bash
# Set credentials for any/all platforms
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_TEST_CHANNEL_NAME="general"

export DISCORD_TOKEN="your-token"
export DISCORD_GUILD_NAME="My Server"
export DISCORD_TEST_CHANNEL_NAME="general"

python -m chatom.examples.cross_platform_bot
```

## Environment Variables Reference

### Slack

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Bot OAuth token (xoxb-...) |
| `SLACK_APP_TOKEN` | For events | App-level token (xapp-...) |
| `SLACK_TEST_CHANNEL_NAME` | For tests | Channel name for testing |
| `SLACK_TEST_USER_NAME` | For mention tests | User to mention |

### Discord

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Bot token |
| `DISCORD_GUILD_NAME` | Yes | Server/guild name |
| `DISCORD_TEST_CHANNEL_NAME` | For tests | Channel name for testing |
| `DISCORD_TEST_USER_NAME` | For mention tests | User to mention |

### Symphony

| Variable | Required | Description |
|----------|----------|-------------|
| `SYMPHONY_HOST` | Yes | Pod hostname |
| `SYMPHONY_BOT_USERNAME` | Yes | Bot service account |
| `SYMPHONY_BOT_PRIVATE_KEY_PATH` | * | Path to RSA key |
| `SYMPHONY_BOT_PRIVATE_KEY_CONTENT` | * | RSA key content |
| `SYMPHONY_TEST_ROOM_NAME` | For tests | Room for testing |
| `SYMPHONY_TEST_USER_NAME` | For mention tests | User to mention |

*One authentication method required

## Running Integration Tests

The integration tests in `chatom/tests/integration/` run automatically when credentials are present:

```bash
# Run all tests (skips backends without credentials)
pytest chatom/tests/integration/ -v

# Run only Slack tests
pytest chatom/tests/integration/test_slack_integration.py -v

# Run only Discord tests
pytest chatom/tests/integration/test_discord_integration.py -v

# Run only Symphony tests
pytest chatom/tests/integration/test_symphony_integration.py -v
```

## Code Patterns

### Async Context Manager Pattern

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_backend():
    config = SlackConfig(bot_token=os.environ["SLACK_BOT_TOKEN"])
    backend = SlackBackend(config=config)
    await backend.connect()
    try:
        yield backend
    finally:
        await backend.disconnect()

# Usage
async with get_backend() as backend:
    await backend.send_message(channel_id, "Hello!")
```

### Error Handling Pattern

```python
async def safe_send(backend, channel_id, content):
    try:
        return await backend.send_message(channel_id, content)
    except Exception as e:
        print(f"Failed to send: {e}")
        return None
```

### Retry Pattern

```python
async def send_with_retry(backend, channel_id, content, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await backend.send_message(channel_id, content)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

## Next Steps

- [Quickstart](quickstart.md) - Getting started guide
- [Backend Configuration](backend-config.md) - Detailed configuration
- [API Reference](api.md) - Full API documentation
