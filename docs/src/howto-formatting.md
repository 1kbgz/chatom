# Format rich messages

Use {class}`chatom.MessageBuilder` for fluent construction and formatting nodes when you need exact tree structure.

## Build common text structures

```python
from chatom import MessageBuilder

message = (
    MessageBuilder()
    .heading("Incident update", level=2)
    .paragraph("Database latency has returned to normal.")
    .bold("Status: ")
    .text("resolved")
    .line_break()
    .link("Runbook", "https://example.com/runbook")
    .build()
)

content = message.render_for("slack")
```

The builder supports text, bold, italic, strikethrough, inline code, code blocks, links, quotes, headings, paragraphs, line breaks, lists, tables, images, attachments, embeds, and arbitrary nodes.

## Add a table

```python
message = (
    MessageBuilder()
    .table(
        [["api", "healthy"], ["workers", "degraded"]],
        headers=["service", "state"],
        caption="Service health",
    )
    .build()
)
```

{class}`chatom.Table` also provides {meth}`chatom.Table.from_data` and {meth}`chatom.Table.from_dict_list` when a table is built separately.

## Compose nodes directly

```python
from chatom import Bold, Document, Paragraph, Text

content = Document(
    children=[
        Paragraph(
            children=[
                Text(content="Hello "),
                Bold(child=Text(content="team")),
            ]
        )
    ]
)

print(content.render("markdown"))
```

Direct nodes support nested styles, spans, lists, headings, quotes, code, user and channel mentions, emoji, and raw platform markup.

## Mention a user or channel

```python
from chatom import Channel, FormattedMessage, User

alice = User(id="U123", name="Alice")
operations = Channel(id="C123", name="operations")

message = (
    FormattedMessage()
    .mention(alice)
    .add_text(" posted an update in ")
    .channel_mention(operations)
)
```

## Convert existing Markdown

```python
from chatom.format import convert_format, parse_markdown

parsed = parse_markdown("**Ready** for [release](https://example.com)")
message_ml = parsed.render("symphony_messageml")
plain_text = convert_format("**Ready**", "markdown", "plaintext")
```

## Add embeds and interactive components

```python
from chatom import FormattedMessage
from chatom.format import ButtonStyle, SelectOption

message = FormattedMessage().add_text("Deploy this release?")
message.add_button("Deploy", action_id="deploy", style=ButtonStyle.SUCCESS)
message.add_select(
    "environment",
    [
        SelectOption(label="Staging", value="staging"),
        SelectOption(label="Production", value="production"),
    ],
)
message.add_embed(title="Release 2.4", description="All checks passed", color=0x2E7D32)

components = message.get_components("slack_markdown")
embeds = message.get_embeds_for("discord")
```

Send rendered text and structured payloads using the keyword arguments expected by the selected backend.
