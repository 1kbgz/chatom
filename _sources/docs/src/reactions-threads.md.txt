# Reactions and Threads

This guide covers working with emoji reactions and message threads.

## Reactions

Reactions let users respond to messages with emoji.

### Adding Reactions

```python
# By emoji name (Slack style)
await backend.add_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="thumbsup",
)

# Unicode emoji (Discord)
await backend.add_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="👍",
)
```

### Multiple Reactions

```python
# Add several reactions
reactions = ["white_check_mark", "eyes", "rocket"]

for emoji in reactions:
    await backend.add_reaction(
        channel_id=channel.id,
        message_id=message.id,
        emoji=emoji,
    )
```

### Removing Reactions

```python
await backend.remove_reaction(
    channel_id="C123456",
    message_id="M789",
    emoji="thumbsup",
)
```

### Reaction Objects

Messages include reaction information:

```python
from chatom import Emoji, Reaction

# Check reactions on a message
for reaction in message.reactions:
    print(f"{reaction.emoji.name}: {reaction.count} reactions")
    print(f"Users: {reaction.users}")
```

### Common Emoji Names

| Slack Name | Unicode | Description |
|------------|---------|-------------|
| `thumbsup` | 👍 | Approve |
| `thumbsdown` | 👎 | Disapprove |
| `heart` | ❤️ | Love |
| `white_check_mark` | ✅ | Done |
| `x` | ❌ | Cancel |
| `eyes` | 👀 | Looking |
| `rocket` | 🚀 | Launch |
| `tada` | 🎉 | Celebrate |
| `thinking_face` | 🤔 | Thinking |
| `fire` | 🔥 | Hot/Great |

## Threads

Threads organize conversations within a channel.

### Creating Threads

```python
# 1. Send parent message
parent = await backend.send_message(
    channel_id=channel.id,
    content="📋 Discussion: Q1 Planning",
)

# 2. Reply to create thread
reply = await backend.reply_to_message(
    channel_id=channel.id,
    message_id=parent.id,
    content="I have some ideas to share...",
)
```

### Thread Replies

```python
# Add multiple replies to a thread
topics = [
    "First, we should prioritize...",
    "Second, let's consider...",
    "Finally, don't forget...",
]

for topic in topics:
    await backend.reply_to_message(
        channel_id=channel.id,
        message_id=parent.id,
        content=topic,
    )
```

### Reading Thread Messages

```python
# Get all messages in a thread
async for message in backend.read_thread(
    channel_id=channel.id,
    thread_id=parent.id,
    limit=50,
):
    author = message.author.name if message.author else "Unknown"
    print(f"{author}: {message.content}")
```

### Thread Properties

```python
# Check if message is in a thread
if message.thread_id:
    print(f"Part of thread: {message.thread_id}")

# Check if message is a reply
if message.reply_to_id:
    print(f"Reply to: {message.reply_to_id}")
```

## Discord Threads

Discord has first-class thread support:

```python
# Create a thread from a message
thread = await backend.create_thread(
    channel_id=channel.id,
    message_id=message.id,
    name="Detailed Discussion",
)

# Send messages in the thread
await backend.send_message(
    channel_id=thread.id,  # Thread ID is used as channel
    content="First message in thread!",
)
```

## Reaction Voting

Use reactions to collect votes:

```python
async def create_poll(backend, channel_id, question, options):
    # Send poll question
    content = f"📊 **Poll**: {question}\n\n"
    for i, option in enumerate(options):
        emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][i]
        content += f"{emoji} {option}\n"

    message = await backend.send_message(
        channel_id=channel_id,
        content=content,
    )

    # Add reaction options
    emojis = ["one", "two", "three", "four", "five"][:len(options)]
    for emoji in emojis:
        await backend.add_reaction(
            channel_id=channel_id,
            message_id=message.id,
            emoji=emoji,
        )

    return message

# Usage
poll = await create_poll(
    backend,
    channel.id,
    "What should we work on next?",
    ["Feature A", "Feature B", "Bug fixes"],
)
```

## Threaded Conversations

Build a threaded conversation handler:

```python
async def handle_support_request(backend, channel_id, user, question):
    from chatom.format import FormattedMessage

    # Create thread parent
    msg = FormattedMessage()
    msg.bold("🎫 Support Request")
    msg.newline()
    msg.text("From: ")
    msg.mention(user)
    msg.newline()
    msg.quote(question)

    content = msg.render(backend.get_format())
    parent = await backend.send_message(
        channel_id=channel_id,
        content=content,
    )

    # Add status reactions
    await backend.add_reaction(
        channel_id=channel_id,
        message_id=parent.id,
        emoji="hourglass",  # Pending
    )

    # First reply with auto-message
    await backend.reply_to_message(
        channel_id=channel_id,
        message_id=parent.id,
        content="Thanks for reaching out! A team member will respond shortly.",
    )

    return parent.id  # Return thread ID for tracking
```

## Reaction Events

Listen for reaction events:

```python
async for event in backend.listen_reactions():
    if event.event_type == "reaction_added":
        print(f"{event.user_id} added {event.emoji.name}")

        # Auto-respond to specific reactions
        if event.emoji.name == "question":
            await backend.reply_to_message(
                channel_id=event.channel_id,
                message_id=event.message_id,
                content="Did you have a question about this?",
            )
```

## Best Practices

### Reactions
- Use consistent emoji across your bot
- Don't add too many reactions (3-5 max)
- Remove reactions when state changes

### Threads
- Use threads for detailed discussions
- Keep parent message concise
- Summarize conclusions in parent

## Next Steps

- [Messaging](messaging.md) - Sending messages
- [Format System](format-system.md) - Rich text formatting
- [Examples](examples.md) - Complete examples
