"""Tests for Symphony backend fetch_messages range + pagination logic."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatom.base import Message
from chatom.symphony.backend import SymphonyBackend


def _make_v4_message(message_id: str, timestamp_ms: int, user_id: int = 1001):
    """Create a mock V4Message-like object."""
    msg = SimpleNamespace()
    msg.message_id = message_id
    msg.message = f"<messageML>Message {message_id}</messageML>"
    msg.timestamp = timestamp_ms
    msg.user = SimpleNamespace(user_id=user_id)
    return msg


def _make_messages_in_range(start_ms: int, end_ms: int, count: int):
    """Create `count` messages evenly spaced between start_ms and end_ms."""
    if count == 0:
        return []
    step = (end_ms - start_ms) // max(count, 1)
    return [_make_v4_message(f"msg_{i}", start_ms + i * step) for i in range(count)]


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


@pytest.fixture
def backend():
    """Create a SymphonyBackend with mocked internals."""
    b = object.__new__(SymphonyBackend)
    b._bdk = MagicMock()
    b._bot_user_id_int = 9999
    b._stream_cache = {}
    b._connected = True
    return b


@pytest.fixture
def mock_list_messages(backend):
    """Set up the mock for message_service.list_messages."""
    msg_service = MagicMock()
    msg_service.list_messages = AsyncMock()
    backend._bdk.messages.return_value = msg_service
    return msg_service.list_messages


def _make_side_effect(all_messages):
    """Simulate the Symphony API: messages with timestamp >= since, oldest-first,
    paginated via skip/limit."""

    async def _side_effect(stream_id, since, skip=0, limit=500):
        matching = [m for m in all_messages if m.timestamp >= since]
        return matching[skip : skip + limit]

    return _side_effect


class TestFetchRange:
    """_fetch_range: newest-first results, range bounds, full pagination."""

    def test_returns_most_recent_limit_newest_first(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        all_messages = _make_messages_in_range(_ms(now - timedelta(minutes=30)), _ms(now - timedelta(minutes=1)), 200)
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        result = asyncio.run(backend._fetch_range("stream123", limit=50, since_ms=None, until_ms=None))

        assert len(result) == 50
        ts = [m.created_at for m in result]
        assert ts == sorted(ts, reverse=True)  # newest-first
        assert {m.id for m in result} == {m.message_id for m in all_messages[-50:]}

    def test_no_lower_bound_widens_window(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        old = _make_messages_in_range(_ms(now - timedelta(days=3, hours=12)), _ms(now - timedelta(days=3)), 20)
        mock_list_messages.side_effect = _make_side_effect(old)

        result = asyncio.run(backend._fetch_range("stream123", limit=20, since_ms=None, until_ms=None))

        assert len(result) == 20
        ts = [m.created_at for m in result]
        assert ts == sorted(ts, reverse=True)

    def test_since_lower_bound(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        all_messages = _make_messages_in_range(_ms(now - timedelta(hours=2)), _ms(now - timedelta(minutes=1)), 120)
        mock_list_messages.side_effect = _make_side_effect(all_messages)
        since = _ms(now - timedelta(minutes=30))

        result = asyncio.run(backend._fetch_range("stream123", limit=500, since_ms=since, until_ms=None))

        assert result
        assert all(_ms(m.created_at) >= since for m in result)

    def test_until_upper_bound(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        all_messages = _make_messages_in_range(_ms(now - timedelta(hours=2)), _ms(now - timedelta(minutes=1)), 120)
        mock_list_messages.side_effect = _make_side_effect(all_messages)
        until = _ms(now - timedelta(minutes=30))

        result = asyncio.run(backend._fetch_range("stream123", limit=500, since_ms=None, until_ms=until))

        assert result
        assert all(_ms(m.created_at) <= until for m in result)

    def test_range_between_bounds(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        all_messages = _make_messages_in_range(_ms(now - timedelta(hours=2)), _ms(now - timedelta(minutes=1)), 120)
        mock_list_messages.side_effect = _make_side_effect(all_messages)
        since = _ms(now - timedelta(minutes=90))
        until = _ms(now - timedelta(minutes=30))

        result = asyncio.run(backend._fetch_range("stream123", limit=500, since_ms=since, until_ms=until))

        assert result
        assert all(since <= _ms(m.created_at) <= until for m in result)

    def test_full_pagination_no_duplicates(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        all_messages = _make_messages_in_range(_ms(now - timedelta(minutes=30)), _ms(now - timedelta(minutes=1)), 800)
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        result = asyncio.run(backend._fetch_range("stream123", limit=800, since_ms=None, until_ms=None))

        ids = [m.id for m in result]
        assert len(ids) == len(set(ids))
        assert mock_list_messages.call_count >= 2  # skip pagination engaged

    def test_empty_channel(self, backend, mock_list_messages):
        mock_list_messages.side_effect = _make_side_effect([])
        result = asyncio.run(backend._fetch_range("stream123", limit=50, since_ms=None, until_ms=None))
        assert result == []

    def test_backstop_prevents_infinite_pagination(self, backend, mock_list_messages):
        mock_list_messages.side_effect = _make_side_effect([])
        result = asyncio.run(backend._fetch_range("stream123", limit=50, since_ms=None, until_ms=None))
        assert result == []
        assert mock_list_messages.call_count <= 15


class TestToEpochMs:
    """_to_epoch_ms coerces the range bounds."""

    def test_none(self):
        assert SymphonyBackend._to_epoch_ms(None) is None

    def test_aware_datetime(self):
        dt = datetime(2026, 7, 17, 18, 51, tzinfo=UTC)
        assert SymphonyBackend._to_epoch_ms(dt) == int(dt.timestamp() * 1000)

    def test_naive_datetime_assumed_utc(self):
        dt = datetime(2026, 7, 17, 18, 51)  # noqa: DTZ001
        assert SymphonyBackend._to_epoch_ms(dt) == int(dt.replace(tzinfo=UTC).timestamp() * 1000)

    def test_message_uses_created_at(self):
        created = datetime(2026, 7, 17, 18, 51, tzinfo=UTC)
        msg = Message(id="x", content="hi", created_at=created)
        assert SymphonyBackend._to_epoch_ms(msg) == int(created.timestamp() * 1000)

    def test_string_epoch(self):
        assert SymphonyBackend._to_epoch_ms("1716850000000") == 1716850000000


class TestFetchMessagesDispatch:
    """The public fetch_messages resolves bounds and returns newest-first."""

    def test_after_datetime_sets_lower_bound(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        all_messages = _make_messages_in_range(_ms(now - timedelta(hours=2)), _ms(now - timedelta(minutes=1)), 60)
        mock_list_messages.side_effect = _make_side_effect(all_messages)
        cutoff = now - timedelta(minutes=30)

        with patch.object(SymphonyBackend, "_resolve_channel_id", new=AsyncMock(return_value="stream123")):
            result = asyncio.run(backend.fetch_messages("stream123", limit=500, after=cutoff))

        assert result
        assert all(_ms(m.created_at) >= _ms(cutoff) for m in result)
        ts = [m.created_at for m in result]
        assert ts == sorted(ts, reverse=True)

    def test_default_returns_recent_newest_first(self, backend, mock_list_messages):
        now = datetime.now(UTC)
        all_messages = _make_messages_in_range(_ms(now - timedelta(minutes=20)), _ms(now - timedelta(minutes=1)), 40)
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        with patch.object(SymphonyBackend, "_resolve_channel_id", new=AsyncMock(return_value="stream123")):
            result = asyncio.run(backend.fetch_messages("stream123", limit=10))

        assert len(result) == 10
        ts = [m.created_at for m in result]
        assert ts == sorted(ts, reverse=True)
        assert {m.id for m in result} == {m.message_id for m in all_messages[-10:]}
