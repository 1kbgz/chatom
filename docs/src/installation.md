# Installation

Chatom supports Python 3.11 and newer.

## Install the core package

```bash
pip install chatom
```

The core package contains platform-independent models, formatting, conversion, registries, bridging, and backend interfaces.

## Install backend SDKs

Install only the platform SDKs your application uses:

```bash
pip install slack-sdk
pip install discord.py
pip install symphony-bdk-python
pip install python-telegram-bot
```

Importing common Chatom models and formatting does not require those SDKs. Constructing a concrete backend does.

## Install optional integrations

```bash
pip install 'chatom[agent]'
pip install 'chatom[mcp]'
pip install csp
```

The `agent` extra installs pydantic-ai integration. The `mcp` extra installs FastMCP and Hydra configuration support. CSP remains a separate optional dependency.

## Install for development

```bash
git clone https://github.com/1kbgz/chatom.git
cd chatom
pip install -e '.[develop]'
```

Build the public documentation directly with Yardang:

```bash
yardang build
```
