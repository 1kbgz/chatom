# CSP Integration

chatom provides optional CSP (Complex Event Processing) integration for real-time
message streaming and processing using the [csp](https://github.com/Point72/csp) library.

## Installation

CSP is an optional dependency. Install it separately:

```bash
pip install csp
```

## Overview

The `chatom.csp` module provides:

- **`BackendAdapter`** - High-level adapter that wraps any chatom backend
- **`message_reader`** - Function to create a message time series
- **`message_writer`** - Node to write messages to a backend

## Quick Start

```python
from datetime import datetime, timedelta

import csp
from csp import ts

from chatom import Message
from chatom.csp import BackendAdapter
from chatom.symphony import SymphonyBackend, SymphonyConfig


# Create backend (using Symphony as an example)
config = SymphonyConfig(
    host="company.symphony.com",
    bot_username="my-bot",
    bot_private_key_path="/path/to/key.pem",
)
backend = SymphonyBackend(config=config)

# Create CSP adapter
adapter = BackendAdapter(backend)


@csp.node
def echo(messages: ts[[Message]]) -> ts[Message]:
    """Echo incoming messages."""
    if csp.ticked(messages):
        for msg in messages:
            if "hello" in msg.content.lower():
                return Message(
                    channel_id=msg.channel_id,  # Generic field for any backend
                    content=f"Hello back, {msg.author_id}!",
                )


@csp.graph
def my_bot():
    # Subscribe to messages
    messages = adapter.subscribe()

    # Process and respond
    responses = echo(messages)

    # Publish responses
    adapter.publish(responses)


if __name__ == "__main__":
    csp.run(
        my_bot,
        starttime=datetime.now(),
        endtime=timedelta(hours=8),
        realtime=True,
    )
```

## BackendAdapter

The `BackendAdapter` class wraps any chatom backend and provides CSP graph/node methods.

### Creating an Adapter

```python
from chatom.csp import BackendAdapter
from chatom.symphony import SymphonyBackend, SymphonyConfig

config = SymphonyConfig(host="company.symphony.com", ...)
backend = SymphonyBackend(config=config)
adapter = BackendAdapter(backend)
```

### Subscribing to Messages

```python
@csp.graph
def my_graph():
    # Subscribe to all messages
    messages = adapter.subscribe()

    # Subscribe to specific channels by ID or name
    messages = adapter.subscribe(channels={"general", "C12345"})

    # Skip bot's own messages (default: True)
    messages = adapter.subscribe(skip_own=True)

    # Skip messages from before stream started (default: True)
    messages = adapter.subscribe(skip_history=True)
```

The `subscribe()` method returns a `ts[[Message]]` - a time series of message lists.
Messages are batched because multiple messages may arrive at the same time.

### Publishing Messages

```python
from chatom import Message

@csp.graph
def my_graph():
    response = csp.const(Message(
        channel_id="channel123",
        content="Hello!",
    ))
    adapter.publish(response)
```

### Publishing Presence

```python
@csp.graph
def my_graph():
    presence = csp.const("available")
    adapter.publish_presence(presence)
```

## Low-Level Functions

For more control, use the low-level functions directly.

### message_reader

Creates a time series of messages from a backend:

```python
from chatom.csp import message_reader

@csp.graph
def my_graph():
    # Filter by channel ID or name
    messages = message_reader(
        backend,
        channels={"general", "support"},
        skip_own=True,
        skip_history=True,
    )
```

### message_writer

Writes messages to a backend:

```python
from chatom.csp import message_writer

@csp.graph
def my_graph():
    message_writer(backend, messages=response_ts)
```

## Working with Different Backends

The CSP layer works with any chatom backend:

### Symphony

```python
from chatom.symphony import SymphonyBackend, SymphonyConfig

config = SymphonyConfig(
    host="company.symphony.com",
    bot_username="my-bot",
    bot_private_key_path="/path/to/key.pem",
)
backend = SymphonyBackend(config=config)
adapter = BackendAdapter(backend)
```

### Slack

```python
from chatom.slack import SlackBackend, SlackConfig

config = SlackConfig(
    bot_token="xoxb-...",
    app_token="xapp-...",
)
backend = SlackBackend(config=config)
adapter = BackendAdapter(backend)
```

### Discord

```python
from chatom.discord import DiscordBackend, DiscordConfig

config = DiscordConfig(
    token="...",
)
backend = DiscordBackend(config=config)
adapter = BackendAdapter(backend)
```

## Processing Patterns

### Unrolling Message Batches

Messages arrive as lists. To process individually:

```python
@csp.graph
def my_graph():
    message_batches = adapter.subscribe()
    individual_messages = csp.unroll(message_batches)
    # Now individual_messages is ts[Message]
```

### Filtering Messages

```python
@csp.node
def filter_mentions(messages: ts[[Message]], user_id: str) -> ts[[Message]]:
    """Filter to only messages that mention a user."""
    if csp.ticked(messages):
        filtered = [m for m in messages if m.mentions_user(user_id)]
        if filtered:
            return filtered
```

### Transforming Messages

```python
@csp.node
def transform_to_response(msg: ts[Message]) -> ts[Message]:
    """Transform incoming message to a response."""
    if csp.ticked(msg):
        return Message(
            channel_id=msg.channel_id,
            content=f"You said: {msg.content}",
        )
```

## Error Handling

The adapter handles connection errors gracefully:

```python
@csp.graph
def my_graph():
    adapter = BackendAdapter(backend)

    # If connection fails, the graph will log errors but continue
    messages = adapter.subscribe()

    # Handle errors in your processing
    @csp.node
    def safe_process(msgs: ts[[Message]]) -> ts[Message]:
        if csp.ticked(msgs):
            try:
                # Process...
                pass
            except Exception as e:
                log.error(f"Error processing: {e}")
```

## Platform-Specific Adapters

For platform-specific features, use the dedicated adapter packages:

- **[csp-adapter-symphony](https://github.com/Point72/csp-adapter-symphony)** - Symphony-specific features
- **[csp-adapter-slack](https://github.com/Point72/csp-adapter-slack)** - Slack-specific features
- **[csp-adapter-discord](https://github.com/Point72/csp-adapter-discord)** - Discord-specific features

These packages extend the generic `BackendAdapter` with platform-specific methods.

## API Reference

### BackendAdapter

```python
class BackendAdapter:
    def __init__(self, backend: BackendBase): ...

    @property
    def backend(self) -> BackendBase: ...

    @csp.graph
    def subscribe(
        self,
        channels: Optional[Set[str]] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ) -> ts[[Message]]: ...

    @csp.graph
    def publish(self, msg: ts[Message]): ...

    @csp.graph
    def publish_presence(self, presence: ts[str], timeout: float = 5.0): ...
```

### message_reader

```python
def message_reader(
    backend: BackendBase,
    channels: Optional[Set[str]] = None,
    skip_own: bool = True,
    skip_history: bool = True,
) -> ts[[Message]]: ...
```

### message_writer

```python
@csp.node
def message_writer(
    backend: object,
    messages: ts[Message],
): ...
```

### HAS_CSP

Flag indicating whether CSP is installed:

```python
from chatom.csp import HAS_CSP

if HAS_CSP:
    from chatom.csp import BackendAdapter
    # Use CSP features
else:
    # Fall back to non-CSP approach
```
