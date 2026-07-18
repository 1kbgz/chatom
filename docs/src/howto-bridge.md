# Bridge messages between platforms

Use {class}`chatom.MessageBridge` to forward messages while translating formatting, channel IDs, attachments, attribution, and linked user mentions.

## Link identities

```python
from chatom import IdentityMapper

mapper = IdentityMapper()
mapper.register_backend("slack", slack_backend)
mapper.register_backend("symphony", symphony_backend)

await mapper.link_by_email("alice@example.com")
```

For users without a shared email address, link known user objects manually:

```python
mapper.link(
    slack_user,
    symphony_user,
    backends=["slack", "symphony"],
)
```

## Map channels and forward

```python
from chatom import MessageBridge

bridge = MessageBridge(
    source=slack_backend,
    dest=symphony_backend,
    source_name="slack",
    dest_name="symphony",
    identity_mapper=mapper,
    channels={"C0123": "symphony-stream-id"},
)

forwarded = await bridge.forward(incoming_message)
```

Pass `to_channel` to override the channel map for one call:

```python
forwarded = await bridge.forward(
    incoming_message,
    to_channel="incident-room-id",
    include_attachments=False,
)
```

Use {meth}`chatom.MessageBridge.forward_many` when an ordered batch should use the same destination rules.
