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
