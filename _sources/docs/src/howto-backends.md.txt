# Connect and send through a backend

Install Chatom and the SDKs for the platforms you use:

```bash
pip install chatom
pip install slack-sdk discord.py symphony-bdk-python python-telegram-bot
```

## Create a backend

Each adapter accepts its own configuration model:

```python
from chatom.discord import DiscordBackend, DiscordConfig
from chatom.slack import SlackBackend, SlackConfig
from chatom.symphony import SymphonyBackend, SymphonyConfig
from chatom.telegram import TelegramBackend, TelegramConfig

slack = SlackBackend(config=SlackConfig(bot_token="xoxb-..."))
discord = DiscordBackend(config=DiscordConfig(token="..."))
symphony = SymphonyBackend(
    config=SymphonyConfig(
        host="company.symphony.com",
        bot_username="chatom-bot",
        bot_private_key_path="bot-private-key.pem",
    )
)
telegram = TelegramBackend(config=TelegramConfig(bot_token="..."))
```

Pass secrets from environment variables or a secret manager in production.

## Use the common lifecycle

The rest of the workflow is backend-independent:

```python
async def announce(backend, channel_name: str, content: str):
    await backend.connect()
    try:
        channel = await backend.fetch_channel(name=channel_name)
        return await backend.send_message(channel, content)
    finally:
        await backend.disconnect()
```

{meth}`chatom.BackendBase.fetch_channel` accepts an identifier or named keyword. Methods that accept a channel generally accept either a channel ID or a {class}`chatom.Channel`.

## Use the synchronous facade

For a synchronous caller, use {attr}`chatom.BackendBase.sync` and close it when finished:

```python
backend.sync.connect()
try:
    channel = backend.sync.fetch_channel(name="operations")
    backend.sync.send_message(channel, "Deployment complete")
finally:
    backend.sync.disconnect()
    backend.sync.close()
```

## Check an optional operation

```python
from chatom import Capability

if backend.capabilities.supports(Capability.EMOJI_REACTIONS):
    await backend.add_reaction(channel, message, "thumbsup")
```

Consult the backend's {class}`chatom.BackendCapabilities` before relying on reactions, presence, editing, files, threads, or interactions.

## Read and search messages

```python
from datetime import datetime, timedelta, timezone

since = datetime.now(timezone.utc) - timedelta(hours=1)
messages = await backend.fetch_messages(channel, limit=100, after=since)

async for message in backend.read_messages(channel, limit=20):
    print(message.author_name, message.content)

if backend.capabilities.supports(Capability.MESSAGE_SEARCH):
    matches = await backend.search_messages("deployment", channel=channel)
```

History is returned newest-first. Bounds accept message IDs, {class}`chatom.Message` objects, or timezone-aware datetimes.

## Reply and work with threads

```python
parent = await backend.send_message(channel, "Deployment discussion")
reply = await backend.send_message(channel, "All checks passed", reply_to=parent)
thread_reply = await backend.reply_in_thread(parent, "Following up in the thread")
```

Use {meth}`chatom.BackendBase.create_thread` for platforms where a thread is a named object and {meth}`chatom.BackendBase.read_thread` to iterate its messages.

## Edit, delete, and react

```python
if backend.capabilities.supports(Capability.EDITING):
    message = await backend.edit_message(message, "Corrected content")

if backend.capabilities.supports(Capability.EMOJI_REACTIONS):
    await backend.add_reaction(message, "thumbsup")
    await backend.remove_reaction(message, "thumbsup")

if backend.capabilities.supports(Capability.DELETING):
    await backend.delete_message(message)
```

## Upload and download files

```python
uploaded = await backend.upload_file(
    channel,
    report_bytes,
    filename="report.csv",
    content_type="text/csv",
    content="Latest report",
)

for attachment in incoming_message.attachments:
    data = await backend.download_attachment(attachment, message=incoming_message)
```

## Send a direct message

```python
user = await backend.fetch_user(email="alice@example.com")
message = await backend.send_dm(user, "The report is ready")
```

## Listen for events

```python
async for message in backend.listen(channel=channel):
    if message.content == "ping":
        await backend.reply_in_thread(message, "pong")
```

Use {meth}`chatom.BackendBase.stream_interactions` for button, menu, and modal events. Streaming support depends on the selected backend and its connection mode.

## Manage presence

```python
if backend.capabilities.supports(Capability.PRESENCE):
    await backend.set_presence("online", "Ready")
    presence = await backend.get_presence(user)
```
