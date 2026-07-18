# Connect Chatom to CSP

Install `csp`, wrap a backend with {class}`chatom.csp.BackendAdapter`, and use the adapter inside a graph.

```bash
pip install csp
```

## Subscribe to messages

```python
import csp
from chatom.csp import BackendAdapter

adapter = BackendAdapter(backend)

@csp.graph
def message_graph():
    messages = adapter.subscribe(
        channels={"operations", "C0123"},
        skip_own=True,
        skip_history=True,
    )
    csp.print("messages", messages)
```

`subscribe` produces a time series of message lists. Channel names are resolved when the backend connects.

## Publish messages and presence

```python
@csp.graph
def publish_graph():
    outgoing = csp.const(message)
    adapter.publish(outgoing)

    presence = csp.const("available")
    adapter.publish_presence(presence)
```

The lower-level {func}`chatom.csp.message_reader`, {func}`chatom.csp.message_writer`, and {func}`chatom.csp.interaction_reader` functions are available when graph composition does not need the wrapper.
