# Test backend-independent code

Each backend package exports an in-memory mock with the same asynchronous frontend as its live backend.

```python
import pytest
from chatom.discord import MockDiscordBackend
from chatom.irc import MockIRCBackend
from chatom.line import MockLineBackend
from chatom.matrix import MockMatrixBackend
from chatom.slack import MockSlackBackend
from chatom.symphony import MockSymphonyBackend
from chatom.telegram import MockTelegramBackend
from chatom.zulip import MockZulipBackend


@pytest.mark.asyncio
async def test_announcement():
    backend = MockSlackBackend()
    backend.add_mock_channel("C123", "operations")

    await backend.connect()
    try:
        channel = await backend.fetch_channel(name="operations")
        sent = await backend.send_message(channel, "Deployment complete")
    finally:
        await backend.disconnect()

    assert sent.content == "Deployment complete"
    assert backend.get_sent_messages() == [sent]
```

Equivalent mocks are exported by every backend package.

Parameterize a common behavior test to verify frontend portability:

```python
@pytest.mark.parametrize(
    "backend_factory",
    [
        MockDiscordBackend,
        MockIRCBackend,
        MockLineBackend,
        MockMatrixBackend,
        MockSlackBackend,
        MockSymphonyBackend,
        MockTelegramBackend,
        MockZulipBackend,
    ],
)
@pytest.mark.asyncio
async def test_message_workflow(backend_factory):
    backend = backend_factory()
    await backend.connect()
    try:
        assert backend.connected
    finally:
        await backend.disconnect()
```
