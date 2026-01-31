# Mentions

Mentions allow you to reference users, channels, and special groups in your messages.

## User Mentions

### Using FormattedMessage

```python
from chatom.format import FormattedMessage
from chatom import User

msg = FormattedMessage()

# With User object (recommended)
user = User(id="U123456", name="Alice")
msg.text("Hello ")
msg.mention(user)
msg.text("!")

# Render for platform
content = msg.render(backend.get_format())
# Slack: "Hello <@U123456>!"
# Discord: "Hello <@U123456>!"
# Symphony: "Hello <mention uid="U123456"/>!"
```

### Using User ID

```python
msg = FormattedMessage()
msg.user_mention("U123456")
```

### Platform-Specific Functions

```python
# Slack
from chatom.slack import mention_user
content = mention_user("U123456")  # <@U123456>

# Discord
from chatom.discord import mention_user
content = mention_user("123456789")  # <@123456789>

# Symphony
from chatom.symphony import mention_user_by_uid
content = mention_user_by_uid("123456789")  # <mention uid="123456789"/>
```

## Channel Mentions

### Using FormattedMessage

```python
from chatom.format import FormattedMessage
from chatom import Channel

msg = FormattedMessage()

channel = Channel(id="C123456", name="general")
msg.text("Join us in ")
msg.channel_mention(channel)

content = msg.render(backend.get_format())
# Slack: "Join us in <#C123456>"
# Discord: "Join us in <#C123456>"
```

### Using Channel ID

```python
msg = FormattedMessage()
msg.channel_mention_by_id("C123456")
```

## Special Mentions

### Slack

```python
from chatom.slack import mention_here, mention_channel_all, mention_everyone

# @here - notify active members
here = mention_here()  # <!here>

# @channel - notify all channel members
channel_all = mention_channel_all()  # <!channel>

# @everyone - notify everyone in workspace
everyone = mention_everyone()  # <!everyone>

msg = FormattedMessage()
msg.text(mention_here())
msg.text(" Please review this!")
```

### Discord

```python
from chatom.discord import mention_everyone, mention_here, mention_role

# @everyone
everyone = mention_everyone()  # @everyone

# @here
here = mention_here()  # @here

# @role
role = mention_role("role_id")  # <@&role_id>

msg = FormattedMessage()
msg.text(mention_everyone())
msg.text(" New announcement!")
```

### Symphony

Symphony uses hashtags and cashtags:

```python
from chatom.symphony import format_hashtag, format_cashtag

# Hashtag
hashtag = format_hashtag("project")  # <hash tag="project"/>

# Cashtag (stock symbols)
cashtag = format_cashtag("AAPL")  # <cash tag="AAPL"/>

msg = FormattedMessage()
msg.text("Check out ")
msg.text(format_hashtag("chatom"))
```

## Detecting Mentions

### In Message Content

```python
from chatom import Message

message = Message(
    id="M123",
    content="Hey <@U123456> check out <#C789>",
    channel_id="C456",
)

# Get mentioned user IDs
user_ids = message.get_mentioned_user_ids()
# ['U123456']

# Get mentioned channel IDs
channel_ids = message.get_mentioned_channel_ids()
# ['C789']

# Check if specific user is mentioned
if message.mentions_user("U123456"):
    print("User was mentioned!")
```

### Using Parse Functions

```python
from chatom.base import parse_mentions, parse_channel_mentions, extract_mention_ids

content = "Hello <@U123> and <@U456>!"

# Parse to get match objects
matches = parse_mentions(content, backend_name="slack")
for match in matches:
    print(f"User ID: {match.user_id} at position {match.start}-{match.end}")

# Just get IDs
user_ids = extract_mention_ids(content, backend_name="slack")
# ['U123', 'U456']
```

## Backend-Specific Mention Formats

### Slack Mention Format

```python
# User mention
<@U123456>
<@U123456|displayname>

# Channel mention
<#C123456>
<#C123456|channel-name>

# Special mentions
<!here>
<!channel>
<!everyone>
<!subteam^SXXX|@group>
```

### Discord Mention Format

```python
# User mention
<@123456789>
<@!123456789>  # With nickname

# Channel mention
<#123456789>

# Role mention
<@&123456789>

# Special mentions
@everyone
@here
```

### Symphony Mention Format (MessageML)

```xml
<!-- User mention -->
<mention uid="123456789"/>
<mention email="user@example.com"/>

<!-- Hashtag -->
<hash tag="topic"/>

<!-- Cashtag -->
<cash tag="AAPL"/>
```

## Generating Channel Links

Generate clickable channel references:

```python
# Using backend method
link = backend.channel_link(channel)
# Returns formatted clickable link for the platform

# In a message
msg = FormattedMessage()
msg.text("Check out ")
msg.channel_mention(channel)
```

## Complete Example

```python
import asyncio
from chatom.slack import SlackBackend, SlackConfig, mention_here
from chatom.format import FormattedMessage

async def send_notification():
    config = SlackConfig(bot_token="xoxb-your-token")
    backend = SlackBackend(config=config)
    await backend.connect()

    # Find channel and user
    channel = await backend.fetch_channel(name="announcements")
    user = await backend.fetch_user(name="Project Manager")

    # Create message with mentions
    msg = FormattedMessage()
    msg.text(mention_here())
    msg.text(" ")
    msg.bold("Important Update")
    msg.newline()
    msg.text("Please contact ")
    msg.mention(user)
    msg.text(" if you have questions.")
    msg.newline()
    msg.text("Discussion in ")
    msg.channel_mention(channel)

    # Send
    content = msg.render(backend.get_format())
    await backend.send_message(channel_id=channel.id, content=content)

    await backend.disconnect()

asyncio.run(send_notification())
```

## Next Steps

- [Messaging](messaging.md) - Sending messages
- [Format System](format-system.md) - Rich text formatting
- [Reactions & Threads](reactions-threads.md) - Reactions and threading
