# Model a conversation

In this tutorial you will represent a platform-independent conversation, create a reply, and render it for a destination backend.

## Create participants and a channel

```python
from chatom import Channel, Message, User

alice = User(id="user-1", name="Alice", email="alice@example.com")
operations = Channel(id="channel-1", name="operations")
message = Message(
    id="message-1",
    author=alice,
    channel=operations,
    content="Is the deployment complete?",
)
```

These models carry stable chat concepts. Backend packages extend them with fields specific to Discord, Slack, Symphony, or Telegram.

## Create a reply

```python
reply = message.as_reply("Yes, all checks passed.")

assert reply.reply_to == message
assert reply.channel == operations
```

The reply retains its relationship to the incoming message without committing to a platform payload.

## Format the reply

```python
formatted = reply.to_formatted()
print(formatted.render_for("slack"))
print(formatted.render_for("symphony"))
```

The same conversation model can now move through a backend, a {class}`chatom.MessageBridge`, an agent toolset, or an MCP server. Those integrations share the model rather than defining separate message types for application code.
