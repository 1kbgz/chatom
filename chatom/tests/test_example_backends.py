"""Tests for the shared example backend factory.

The examples are the documented path for running a real bot locally, so the
env-var contract and channel resolution are worth pinning down.
"""

import pytest

from chatom.examples import _backends


def test_every_backend_has_channel_and_user_env():
    for name in _backends.BACKENDS:
        assert _backends.channel_env(name)
        assert name in _backends._USER_ENV


@pytest.mark.parametrize(
    ("name", "lookup"),
    [
        ("slack", "name"),
        ("discord", "name"),
        ("symphony", "name"),
        ("telegram", "name"),
        ("zulip", "name"),
        ("matrix", "id"),
        ("irc", "id"),
        ("line", "id"),
    ],
)
@pytest.mark.asyncio
async def test_resolve_channel_uses_the_lookup_each_backend_supports(name, lookup, monkeypatch):
    """Matrix, IRC, and LINE resolve an identifier, not a display name.

    Matrix takes a room id or a #alias it resolves, IRC builds the channel
    from #name, and LINE conversations are opaque ids. Passing name= for
    those returns None instead of the channel.
    """
    calls = {}

    class _Backend:
        def __init__(self, backend_name):
            self.name = backend_name

        async def fetch_channel(self, **kwargs):
            calls.update(kwargs)
            return object()

    monkeypatch.setenv("DISCORD_GUILD_NAME", "guild")
    backend = _Backend(name)
    if name == "discord":

        async def fetch_organization(**kwargs):
            return type("Org", (), {"id": "g1"})()

        backend.fetch_organization = fetch_organization
        backend.config = type("Config", (), {"guild_id": None})()

    await _backends.resolve_channel(backend, "target")

    assert list(calls) == [lookup]
    assert calls[lookup] == "target"
