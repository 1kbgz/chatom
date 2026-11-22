"""Tests for chatom.csp.runner.BackendRunner."""

import asyncio
from concurrent.futures import CancelledError
from datetime import UTC, datetime, timedelta
from queue import Queue

import pytest

pytest.importorskip("csp")

import csp

from chatom.base import Channel, Interaction, Message, User
from chatom.csp import BackendAdapter, BackendRunner, interaction_reader
from chatom.csp.nodes import MessageReaderPushAdapterImpl, _send_messages_thread, _set_presence_thread


class CountingConfig:
    """Config shared by every copy a runner makes."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.connects = 0
        self.disconnects = 0
        self.sent: list[str] = []
        self.presence: list[str] = []


class CountingBackend:
    """Backend that records connections on its config, which copies share."""

    def __init__(self, config: CountingConfig):
        self.config = config
        self.connected = False

    async def connect(self):
        if self.config.fail:
            raise ConnectionError("refused")
        self.config.connects += 1
        self.connected = True

    async def disconnect(self):
        self.config.disconnects += 1
        self.connected = False

    async def send_message(self, channel: str, content: str, **kwargs) -> Message:
        self.config.sent.append(content)
        return Message(id=f"m{len(self.config.sent)}", channel=Channel(id=channel), content=content, author=User(id="bot"))

    async def set_presence(self, status: str):
        self.config.presence.append(status)

    async def fetch_channel(self, identifier=None, *, id=None, name=None):
        return None

    async def stream_messages(self, channel=None, skip_own=True, skip_history=True):
        yield Message(id="in1", channel=Channel(id="c"), content="ping", author=User(id="u"))
        await asyncio.Event().wait()


def test_acquire_returns_one_runner_per_backend():
    backend = CountingBackend(CountingConfig())
    other = CountingBackend(CountingConfig())

    first = BackendRunner.acquire(backend)
    second = BackendRunner.acquire(backend)
    third = BackendRunner.acquire(other)
    try:
        assert first is second
        assert first is not third
        assert first.backend is not backend
    finally:
        for runner in (first, second, third):
            runner.release()


def test_call_connects_once_and_release_disconnects_last():
    config = CountingConfig()
    backend = CountingBackend(config)

    first = BackendRunner.acquire(backend)
    second = BackendRunner.acquire(backend)
    assert first.ready(timeout=5) is first.backend
    first.call(lambda b: b.send_message("c", "hello")).result(timeout=5)

    first.release()
    assert config.disconnects == 0
    second.release()

    assert config.connects == 1
    assert config.disconnects == 1
    assert config.sent == ["hello"]
    assert first.loop.is_closed()
    again = BackendRunner.acquire(backend)
    assert again is not first
    again.release()


def test_release_without_any_call_never_connects():
    config = CountingConfig()
    runner = BackendRunner.acquire(CountingBackend(config))

    runner.release()

    assert config.connects == 0
    assert config.disconnects == 0


def test_connect_failure_reaches_every_caller():
    config = CountingConfig(fail=True)
    runner = BackendRunner.acquire(CountingBackend(config))
    try:
        with pytest.raises(ConnectionError):
            runner.ready(timeout=5)
        with pytest.raises(ConnectionError):
            runner.call(lambda b: b.send_message("c", "x")).result(timeout=5)
    finally:
        runner.release()

    assert config.disconnects == 0


def test_cancelled_caller_does_not_cancel_shared_connection():
    config = CountingConfig()
    gate = asyncio.Event()

    class SlowBackend(CountingBackend):
        async def connect(self):
            await gate.wait()
            await super().connect()

    runner = BackendRunner.acquire(SlowBackend(config))
    try:
        pending = runner.call(lambda b: b.send_message("c", "first"))
        pending.cancel()
        with pytest.raises(CancelledError):
            pending.result(timeout=5)
        runner.loop.call_soon_threadsafe(gate.set)
        runner.call(lambda b: b.send_message("c", "second")).result(timeout=5)
    finally:
        runner.release()

    assert config.connects == 1
    assert config.sent == ["second"]


def test_release_cancels_a_connection_still_in_progress():
    config = CountingConfig()

    class HangingBackend(CountingBackend):
        async def connect(self):
            await asyncio.Event().wait()

    runner = BackendRunner.acquire(HangingBackend(config))
    pending = runner.call(lambda b: b.send_message("c", "never"))

    runner.release()

    assert pending.cancelled() or isinstance(pending.exception(timeout=5), asyncio.CancelledError)
    assert config.disconnects == 0


def test_reader_writer_and_presence_share_one_connection():
    config = CountingConfig()
    adapter = BackendAdapter(CountingBackend(config))

    received: list[str] = []

    @csp.node
    def collect(messages: csp.ts[list[Message]]):
        if csp.ticked(messages):
            received.extend(message.content for message in messages)

    @csp.graph
    def graph():
        collect(adapter.subscribe())
        adapter.publish(csp.const(Message(channel=Channel(id="c"), content="hi")))
        adapter.publish_presence(csp.const("available"))

    csp.run(graph, starttime=datetime.now(UTC), endtime=timedelta(seconds=0.5), realtime=True)

    assert received == ["ping"]
    assert config.connects == 1
    assert config.disconnects == 1
    assert config.sent == ["hi"]
    assert config.presence == ["available"]
    assert BackendRunner._registry == {}


def test_reader_streams_a_subscribed_channel():
    adapter = BackendAdapter(CountingBackend(CountingConfig()))

    received: list[str] = []

    @csp.node
    def collect(messages: csp.ts[list[Message]]):
        if csp.ticked(messages):
            received.extend(message.content for message in messages)

    @csp.graph
    def graph():
        collect(adapter.subscribe(channels={"c"}))

    csp.run(graph, starttime=datetime.now(UTC), endtime=timedelta(seconds=0.5), realtime=True)

    assert received == ["ping"]


def test_interaction_reader_uses_the_shared_connection():
    config = CountingConfig()

    class InteractiveBackend(CountingBackend):
        async def stream_interactions(self, channel=None):
            yield Interaction(id="i1", action_id="approve")
            await asyncio.Event().wait()

    backend = InteractiveBackend(config)
    adapter = BackendAdapter(backend)
    seen: list[str] = []

    @csp.node
    def collect(events: csp.ts[list[Interaction]]):
        if csp.ticked(events):
            seen.extend(event.action_id for event in events)

    @csp.graph
    def graph():
        collect(interaction_reader(backend))
        adapter.publish(csp.const(Message(channel=Channel(id="c"), content="hi")))

    csp.run(graph, starttime=datetime.now(UTC), endtime=timedelta(seconds=0.5), realtime=True)

    assert seen == ["approve"]
    assert config.connects == 1
    assert config.sent == ["hi"]


def test_writer_keeps_sending_after_a_failed_message():
    config = CountingConfig()

    class PickyBackend(CountingBackend):
        async def send_message(self, channel: str, content: str, **kwargs) -> Message:
            if content == "bad":
                raise RuntimeError("rejected")
            return await super().send_message(channel, content, **kwargs)

    queue: Queue = Queue()
    for content in ("bad", "good"):
        queue.put(Message(channel=Channel(id="c"), content=content))
    queue.put(None)

    _send_messages_thread(queue, PickyBackend(config))

    assert config.sent == ["good"]
    assert config.connects == 1
    assert config.disconnects == 1


def test_presence_timeout_is_logged_not_raised():
    config = CountingConfig()

    class SlowPresence(CountingBackend):
        async def set_presence(self, status: str):
            await asyncio.sleep(1)

    queue: Queue = Queue()
    queue.put(("available", 0.01))
    queue.put(None)

    _set_presence_thread(queue, SlowPresence(config))

    assert config.presence == []
    assert config.disconnects == 1


def test_reader_records_a_connect_failure():
    reader = MessageReaderPushAdapterImpl(CountingBackend(CountingConfig(fail=True)))
    reader._running_event.set()

    reader._run()

    assert isinstance(reader._error, ConnectionError)
    assert not reader._running_event.is_set()
    assert BackendRunner._registry == {}
