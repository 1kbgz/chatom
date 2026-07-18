# One message for four backends

In this tutorial you will build one rich message and render it for Slack, Discord, Symphony, and Telegram. No credentials or network connection are required.

## Build the message

Chatom's frontend consists of backend-independent models and formatting nodes. Build a status message with the fluent {class}`chatom.MessageBuilder`:

```{literalinclude} ../../chatom/examples/unified_frontend.py
:language: python
:pyobject: build_status_message
```

The object contains structure, not platform markup. The heading, list, and table remain typed nodes until rendering.

## Render for each backend

Render the same object with each backend name:

```{literalinclude} ../../chatom/examples/unified_frontend.py
:language: python
:pyobject: main
```

Run the complete example:

```bash
python -m chatom.examples.unified_frontend
```

Notice how the outputs differ:

- Slack uses mrkdwn and a fixed-width table.
- Discord uses Discord-flavored Markdown and a Markdown table.
- Symphony uses MessageML elements.
- Telegram uses its supported HTML subset and a preformatted table.

No conditional rendering logic appears in the application. {meth}`chatom.FormattedMessage.render_for` selects the platform format at the boundary.

## Send the rendered result

A connected backend accepts the same channel-and-content call shape:

```python
channel = await backend.fetch_channel(name="operations")
content = message.render_for(backend.name)
await backend.send_message(channel, content)
```

Only backend construction and credentials vary. Message construction, channel lookup, and sending use the common frontend.
