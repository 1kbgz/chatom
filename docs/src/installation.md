# Installation

## Requirements

- Python 3.10 or higher
- pydantic >= 2.0

## Installing from PyPI

```bash
pip install chatom
```

## Installing from Source

```bash
git clone https://github.com/1kbgz/chatom.git
cd chatom
pip install -e .
```

## Development Installation

For development, install with the `develop` extras:

```bash
pip install -e ".[develop]"
```

This includes:
- Testing tools (pytest, pytest-cov)
- Linting tools (ruff, codespell)
- Build tools (hatchling, build, wheel)
- Documentation tools

## Verifying Installation

```python
import chatom
print(chatom.__version__)
```

## Dependencies

chatom has minimal dependencies:

| Package | Purpose |
|---------|---------|
| `pydantic>=2` | Data validation and serialization |
| `singledispatch` | Polymorphic function dispatch |

## Optional Dependencies

### CSP Integration

For streaming event processing with CSP, install csp:

```bash
pip install csp
```

This enables the `chatom.csp` module for real-time message streaming:

```python
from chatom.csp import BackendAdapter, HAS_CSP

if HAS_CSP:
    # CSP integration available
    from chatom.csp import message_reader, message_writer
```

See the [CSP Integration](csp-integration) guide for more details.
