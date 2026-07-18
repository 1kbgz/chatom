# Test backend-independent code

Each backend package exports an in-memory mock with the same asynchronous frontend as its live backend.

```python
import pytest
from chatom.slack import MockSlackBackend


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

Equivalent mocks are exported as {class}`chatom.discord.MockDiscordBackend`, {class}`chatom.symphony.MockSymphonyBackend`, and {class}`chatom.telegram.MockTelegramBackend`.

Parameterize a common behavior test to verify frontend portability:

```python
@pytest.mark.parametrize(
    "backend_factory",
    [MockSlackBackend, MockDiscordBackend, MockSymphonyBackend, MockTelegramBackend],
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
