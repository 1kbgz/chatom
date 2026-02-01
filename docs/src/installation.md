# Installation

## Requirements

- Python 3.10 or higher
- pip or uv package manager

## Basic Installation

Install chatom with all backends:

```bash
pip install chatom
```

Or with uv:

```bash
uv pip install chatom
```

## Platform-Specific Installation

Install only the backends you need:

```bash
# Slack only
pip install chatom[slack]

# Discord only
pip install chatom[discord]

# Symphony only
pip install chatom[symphony]

# Multiple backends
pip install chatom[slack,discord]
```

## Development Installation

For development with testing tools:

```bash
pip install chatom[develop]
```

Or clone the repository:

```bash
git clone https://github.com/1kbgz/chatom.git
cd chatom
pip install -e .[develop]
```

## Verify Installation

```python
import chatom
print(chatom.__version__)

# Check available backends
from chatom.backend import list_backends
print(list_backends())
```

## Dependencies

Core dependencies:
- `pydantic` - Data validation and models
- `aiohttp` - Async HTTP client

Backend-specific dependencies are installed automatically:
- **Slack**: `slack-sdk`
- **Discord**: `discord.py`
- **Symphony**: `symphony-bdk-python`

## Next Steps

- [Quickstart Guide](quickstart.md) - Build your first bot
- [Backend Configuration](backend-config.md) - Set up your credentials
