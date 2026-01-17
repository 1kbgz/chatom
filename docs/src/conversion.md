# Type Conversion System

The chatom conversion system provides utilities for converting between base types and backend-specific types. This enables you to work with framework-agnostic types and seamlessly convert them for specific platforms.

## Overview

The conversion system provides three core operations:

1. **Validation**: Check if a base type instance can be promoted to a backend type
2. **Promotion**: Convert a base type (e.g., `User`) to a backend type (e.g., `DiscordUser`)
3. **Demotion**: Convert a backend type back to a base type

## Quick Start

```python
from chatom import User, promote, demote, can_promote, DISCORD, SLACK

# Create a base user
user = User(id="123", name="John Doe", handle="johndoe")

# Check if it can be promoted to Discord
if can_promote(user, DISCORD):
    # Promote to DiscordUser with additional Discord-specific fields
    discord_user = promote(user, DISCORD, discriminator="1234")
    print(discord_user.discriminator)  # "1234"

# Demote back to base User
base_user = demote(discord_user)
print(type(base_user))  # <class 'chatom.base.user.User'>
```

## Functions

### `can_promote(instance, backend) -> bool`

Check if a base type instance can be promoted to a backend type.

```python
from chatom import User, Channel, can_promote, DISCORD, SLACK

user = User(id="123", name="Test")
print(can_promote(user, DISCORD))  # True
print(can_promote(user, SLACK))    # True
print(can_promote(user, "unknown")) # Raises BackendNotFoundError
```

### `validate_for_backend(instance, backend) -> ValidationResult`

Perform detailed validation of a base type for a backend.

```python
from chatom import User, validate_for_backend, DISCORD

user = User(id="123", name="Test")
result = validate_for_backend(user, DISCORD)

if result.valid:
    print("User is valid for Discord")
else:
    print(f"Missing fields: {result.missing_required}")
    print(f"Invalid fields: {result.invalid_fields}")
```

### `promote(instance, backend, **extra_fields) -> BackendType`

Promote a base type to a backend-specific type.

```python
from chatom import User, Channel, promote, DISCORD, SLACK, SYMPHONY

# Promote user to Discord with extra fields
user = User(id="123", name="Test User")
discord_user = promote(user, DISCORD,
    discriminator="1234",
    global_name="Display Name"
)

# Promote user to Slack with extra fields
slack_user = promote(user, SLACK,
    team_id="T123ABC",
    is_admin=True,
    real_name="Real Name"
)

# Promote user to Symphony with extra fields
symphony_user = promote(user, SYMPHONY,
    first_name="Test",
    last_name="User",
    company="ACME Corp"
)
```

### `demote(instance) -> BaseType`

Demote a backend-specific type back to its base type.

```python
from chatom import demote
from chatom.discord import DiscordUser

# Create a DiscordUser
discord_user = DiscordUser(
    id="123",
    name="Test User",
    discriminator="1234",
    global_name="Display Name"
)

# Demote to base User
user = demote(discord_user)
print(type(user))  # <class 'chatom.base.user.User'>
print(user.id)     # "123"
print(user.name)   # "Test User"
# Discord-specific fields are stripped
```

## Registry Functions

### `get_backend_type(base_type, backend) -> Type | None`

Get the backend-specific type class for a base type.

```python
from chatom import User, get_backend_type, DISCORD
from chatom.discord import DiscordUser

backend_type = get_backend_type(User, DISCORD)
print(backend_type)  # <class 'chatom.discord.user.DiscordUser'>
print(backend_type is DiscordUser)  # True
```

### `get_base_type(backend_type) -> Type | None`

Get the base type class for a backend-specific type.

```python
from chatom import User, get_base_type
from chatom.discord import DiscordUser

base_type = get_base_type(DiscordUser)
print(base_type)  # <class 'chatom.base.user.User'>
print(base_type is User)  # True
```

### `list_backends_for_type(base_type) -> List[str]`

List all backends that have a registered type for the given base type.

```python
from chatom import User, Channel, list_backends_for_type

backends = list_backends_for_type(User)
print(backends)  # ['discord', 'slack', 'symphony', 'email', 'irc', 'matrix']
```

## Supported Type Conversions

The following base types have backend-specific variants:

| Base Type | Discord | Slack | Symphony | Email | IRC | Matrix |
|-----------|---------|-------|----------|-------|-----|--------|
| User | DiscordUser | SlackUser | SymphonyUser | EmailUser | IRCUser | MatrixUser |
| Channel | DiscordChannel | SlackChannel | SymphonyChannel | EmailChannel | IRCChannel | MatrixChannel |
| Presence | DiscordPresence | SlackPresence | SymphonyPresence | EmailPresence | IRCPresence | MatrixPresence |

## Cross-Backend Conversion

You can convert between different backends by demoting to base and then promoting to a new backend:

```python
from chatom import demote, promote, DISCORD, SLACK
from chatom.discord import DiscordUser

# Start with a Discord user
discord_user = DiscordUser(
    id="123",
    name="Test User",
    email="test@example.com",
    discriminator="1234"
)

# Convert to base User
base_user = demote(discord_user)

# Promote to Slack user
slack_user = promote(base_user, SLACK, team_id="T123")
print(slack_user.id)        # "123" (preserved)
print(slack_user.name)      # "Test User" (preserved)
print(slack_user.team_id)   # "T123" (added)
```

## ValidationResult Class

The `ValidationResult` class provides detailed information about validation:

```python
from chatom import ValidationResult

result = ValidationResult(
    valid=False,
    missing_required=["required_field"],
    invalid_fields={"email": "Invalid email format"},
    warnings=["Consider adding display_name"]
)

if result:  # Can use as boolean
    print("Valid!")
else:
    print(f"Missing: {result.missing_required}")
    print(f"Invalid: {result.invalid_fields}")
    print(f"Warnings: {result.warnings}")
```

## Exceptions

### `ConversionError`

Raised when a type conversion fails due to validation errors.

```python
from chatom import User, promote, ConversionError, DISCORD

try:
    # This would fail if Discord required fields that User doesn't have
    discord_user = promote(User(), DISCORD)
except ConversionError as e:
    print(f"Conversion failed: {e}")
```

### `BackendNotFoundError`

Raised when trying to use an unknown backend or unregistered type.

```python
from chatom import User, promote, BackendNotFoundError

try:
    user = promote(User(id="123"), "unknown_backend")
except BackendNotFoundError as e:
    print(f"Backend not found: {e}")
```

## Custom Type Registration

You can register your own backend types using `register_backend_type`:

```python
from chatom import User, register_backend_type
from chatom.base import BaseModel, Field

class CustomUser(User):
    """Custom backend user type."""
    custom_field: str = Field(default="")

# Register the custom type
register_backend_type("custom", User, CustomUser)

# Now you can use it with the conversion functions
from chatom import promote, demote

user = User(id="123", name="Test")
custom_user = promote(user, "custom", custom_field="value")
print(custom_user.custom_field)  # "value"
```

## Best Practices

1. **Use base types for cross-platform logic**: Write business logic using base types (`User`, `Channel`, etc.) and only promote to backend types when interfacing with specific platforms.

2. **Check before promoting**: Use `can_promote()` or `validate_for_backend()` before promoting to handle edge cases gracefully.

3. **Preserve data through demotion**: When demoting, backend-specific fields are stripped. If you need to preserve them, store the original backend instance.

4. **Add backend fields during promotion**: Use the `**extra_fields` parameter of `promote()` to add backend-specific data.

```python
# Good: Add backend-specific fields during promotion
discord_user = promote(user, DISCORD,
    discriminator="1234",
    global_name="Display Name"
)

# Good: Check validity before conversion
if can_promote(user, DISCORD):
    discord_user = promote(user, DISCORD)
else:
    # Handle the case where promotion isn't possible
    pass
```
