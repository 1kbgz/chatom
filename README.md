<p>
  <img src="https://github.com/1kbgz/chatom/raw/main/docs/img/logo-light.png?raw=true#gh-light-mode-only" alt="chatom" width="150">
  <img src="https://github.com/1kbgz/chatom/raw/main/docs/img/logo-dark.png?raw=true#gh-dark-mode-only" alt="chatom" width="150">
</p>

# Chatom

A unified Python frontend for Discord, Slack, Symphony, Telegram, and other chat backends.

[![Build Status](https://github.com/1kbgz/chatom/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/1kbgz/chatom/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/1kbgz/chatom/branch/main/graph/badge.svg?token=IubQKhtRoK)](https://codecov.io/gh/1kbgz/chatom)
[![License](https://img.shields.io/github/license/1kbgz/chatom)](https://github.com/1kbgz/chatom)
[![PyPI](https://img.shields.io/pypi/v/chatom.svg)](https://pypi.python.org/pypi/chatom)

Chatom lets application code use one set of users, channels, messages, formatting nodes, interactions, and backend operations. Platform adapters translate that frontend to Discord, Slack, Symphony, or Telegram at the edge. The same models also feed cross-platform bridges, pydantic-ai tools, MCP servers, and CSP graphs.

## Install

Chatom requires Python 3.11 or newer.

```bash
pip install chatom
```

Install the SDKs for the backends you use:

```bash
pip install slack-sdk discord.py symphony-bdk-python python-telegram-bot
```

Optional integrations are available with `chatom[agent]` and `chatom[mcp]`.

## One message, four backends

```python
from chatom import MessageBuilder

message = (
    MessageBuilder()
    .heading("Deployment status", level=2)
    .paragraph("All checks passed.")
    .bold("Environment: ")
    .text("production")
    .table(
        [["API", "healthy"], ["Workers", "healthy"]],
        headers=["Service", "State"],
    )
    .build()
)

slack_content = message.render_for("slack")
discord_content = message.render_for("discord")
symphony_content = message.render_for("symphony")
telegram_content = message.render_for("telegram")
```

Message construction stays unchanged. Only rendering and backend configuration know which platform receives it.

Connected backends share the same lifecycle and operation shape:

```python
await backend.connect()
try:
    channel = await backend.fetch_channel(name="operations")
    await backend.send_message(channel, message.render_for(backend.name))
finally:
    await backend.disconnect()
```

## What the frontend covers

- Platform-independent models for users, channels, organizations, threads, messages, attachments, embeds, reactions, presence, and interactions
- Rich text, tables, mentions, embeds, buttons, select menus, and format conversion
- A common asynchronous backend interface with a synchronous facade
- Backend capabilities for feature-dependent operations such as reactions, editing, files, presence, and threads
- Model promotion and demotion between common and backend-specific types
- Identity mapping and message forwarding between platforms
- Agent, MCP, and CSP integrations built on the same backend contract
- In-memory Discord, Slack, Symphony, and Telegram backends for tests

## Documentation

- [Installation](docs/src/installation.md)
- [Tutorials](docs/src/tutorials.md)
- [How-to guides](docs/src/howtos.md)
- [Why the unified frontend works](docs/src/concepts.md)
- [API reference](docs/src/api.md)

## Development

```bash
git clone https://github.com/1kbgz/chatom.git
cd chatom
pip install -e '.[develop]'
make test
make lint
yardang build
```

## License

Chatom is licensed under the [Apache License 2.0](LICENSE).

> [!NOTE]
> This library was generated using [copier](https://copier.readthedocs.io/en/stable/) from the [Base Python Project Template repository](https://github.com/python-project-templates/base)
