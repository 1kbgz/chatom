# Handle buttons and menus

Create components with stable action IDs, send their backend payloads, then dispatch incoming interactions with {class}`chatom.InteractionRegistry`.

## Build components

```python
from chatom import FormattedMessage
from chatom.format import ButtonStyle, SelectOption

message = FormattedMessage().add_text("Deploy release 2.4?")
message.add_button(
    "Deploy",
    action_id="deploy_release",
    style=ButtonStyle.SUCCESS,
    value="2.4",
)
message.add_select(
    "target_environment",
    [
        SelectOption(label="Staging", value="staging"),
        SelectOption(label="Production", value="production"),
    ],
)

text = message.render_for(backend.name)
components = message.get_components(backend.get_format())
await backend.send_message(channel, text, components=components)
```

Backend SDKs use different payload keyword names. Consult the concrete backend's send method when passing structured components.

## Register handlers

```python
from chatom import InteractionRegistry

registry = InteractionRegistry()

@registry.on("deploy_release")
async def deploy(event):
    release = event.value
    await backend.send_message(event.channel, f"Deploying {release}")

@registry.on("target_environment")
def select_environment(event):
    return event.value
```

Handlers may be synchronous or asynchronous. Multiple handlers for an action run in registration order.

## Consume interactions

```python
async for event in backend.stream_interactions():
    await registry.dispatch(event)
```

Use {meth}`chatom.InteractionRegistry.register_default` for unmatched action IDs and {meth}`chatom.InteractionRegistry.unregister` when a handler is no longer active.
