"""Tests for chatom.csp module.

These tests verify the CSP integration layer for chatom backends,
including BackendAdapter, message_reader, message_writer, and
channel name resolution.
"""

import asyncio
import threading
from datetime import datetime, timedelta
from queue import Queue
from typing import List, Optional

import pytest

# Skip all tests if csp is not installed
pytest.importorskip("csp")

import csp
from csp import ts

from chatom.base import Channel, Message
from chatom.csp import HAS_CSP, BackendAdapter, message_reader, message_writer
from chatom.csp.nodes import MessageReaderPushAdapterImpl, _send_messages_thread


class MockBackendForCSP:
    """Mock backend for testing CSP integration."""

    def __init__(self):
        self.connected = False
        self.sent_messages: List[Message] = []
        self.presence_updates: List[str] = []
        self._channels = {}
        self._messages_to_stream: List[Message] = []
        self._stream_delay = 0.01
        self._bot_user_id = "bot123"

    async def connect(self):
        """Connect to backend."""
        self.connected = True

    async def disconnect(self):
        """Disconnect from backend."""
        self.connected = False

    async def send_message(self, channel_id: str, content: str) -> Message:
        """Send a message."""
        msg = Message(
            id=f"msg_{len(self.sent_messages)}",
            channel_id=channel_id,
            content=content,
            author_id=self._bot_user_id,
        )
        self.sent_messages.append(msg)
        return msg

    async def set_presence(self, status: str):
        """Set presence."""
        self.presence_updates.append(status)

    async def fetch_channel(
        self,
        identifier: Optional[str] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Channel]:
        """Fetch a channel by ID or name."""
        channel_id = id or identifier
        if channel_id and channel_id in self._channels:
            return self._channels[channel_id]
        if name:
            for ch in self._channels.values():
                if ch.name == name:
                    return ch
        return None

    def add_channel(self, id: str, name: str):
        """Add a mock channel."""
        self._channels[id] = Channel(id=id, name=name)

    def add_messages_to_stream(self, messages: List[Message]):
        """Add messages that will be returned by stream_messages."""
        self._messages_to_stream.extend(messages)

    async def stream_messages(
        self,
        channel_id: Optional[str] = None,
        skip_own: bool = True,
        skip_history: bool = True,
    ):
        """Stream messages from the backend."""
        for msg in self._messages_to_stream:
            if channel_id and msg.channel_id != channel_id:
                continue
            if skip_own and msg.author_id == self._bot_user_id:
                continue
            await asyncio.sleep(self._stream_delay)
            yield msg


class TestHasCSP:
    """Tests for HAS_CSP flag."""

    def test_has_csp_is_true(self):
        """Test that HAS_CSP is True when csp is installed."""
        assert HAS_CSP is True

    def test_imports_work(self):
        """Test that all exports can be imported."""
        from chatom.csp import HAS_CSP, BackendAdapter, message_reader, message_writer

        assert BackendAdapter is not None
        assert message_reader is not None
        assert message_writer is not None
        assert HAS_CSP is True


class TestBackendAdapter:
    """Tests for BackendAdapter class."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        return MockBackendForCSP()

    @pytest.fixture
    def adapter(self, mock_backend):
        """Create a BackendAdapter with mock backend."""
        return BackendAdapter(mock_backend)

    def test_adapter_creation(self, adapter, mock_backend):
        """Test adapter creation."""
        assert adapter.backend is mock_backend

    def test_backend_property(self, adapter, mock_backend):
        """Test backend property returns the wrapped backend."""
        assert adapter.backend is mock_backend
        assert adapter._backend is mock_backend


class TestMessageReaderPushAdapterImpl:
    """Tests for MessageReaderPushAdapterImpl class."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        return MockBackendForCSP()

    def test_init_defaults(self, mock_backend):
        """Test default initialization."""
        impl = MessageReaderPushAdapterImpl(mock_backend)
        assert impl._backend is mock_backend
        assert impl._channels == set()
        assert impl._skip_own is True
        assert impl._skip_history is True
        assert impl._running is False

    def test_init_with_channels(self, mock_backend):
        """Test initialization with channels."""
        channels = {"general", "support"}
        impl = MessageReaderPushAdapterImpl(
            mock_backend,
            channels=channels,
            skip_own=False,
            skip_history=False,
        )
        assert impl._channels == channels
        assert impl._skip_own is False
        assert impl._skip_history is False

    def test_start_creates_thread(self, mock_backend):
        """Test that start creates and starts a thread."""
        impl = MessageReaderPushAdapterImpl(mock_backend)
        impl.start(datetime.now(), datetime.now() + timedelta(hours=1))

        assert impl._running is True
        assert impl._thread is not None
        assert impl._thread.is_alive()

        # Cleanup
        impl.stop()

    def test_stop_stops_thread(self, mock_backend):
        """Test that stop stops the thread."""
        impl = MessageReaderPushAdapterImpl(mock_backend)
        impl.start(datetime.now(), datetime.now() + timedelta(hours=1))
        impl.stop()

        assert impl._running is False


class TestChannelResolution:
    """Tests for channel name resolution."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend with channels."""
        backend = MockBackendForCSP()
        backend.add_channel("C123", "general")
        backend.add_channel("C456", "support")
        return backend

    @pytest.mark.asyncio
    async def test_resolve_channel_by_id(self, mock_backend):
        """Test resolving channel by ID."""
        impl = MessageReaderPushAdapterImpl(mock_backend, channels={"C123"})

        # Simulate connection
        await mock_backend.connect()
        await impl._resolve_channels()

        assert "C123" in impl._resolved_channel_ids

    @pytest.mark.asyncio
    async def test_resolve_channel_by_name(self, mock_backend):
        """Test resolving channel by name."""
        impl = MessageReaderPushAdapterImpl(mock_backend, channels={"general"})

        await mock_backend.connect()
        await impl._resolve_channels()

        # Should resolve "general" to "C123"
        assert "C123" in impl._resolved_channel_ids

    @pytest.mark.asyncio
    async def test_resolve_mixed_channels(self, mock_backend):
        """Test resolving mix of IDs and names."""
        impl = MessageReaderPushAdapterImpl(
            mock_backend,
            channels={"C123", "support"},  # ID  # Name
        )

        await mock_backend.connect()
        await impl._resolve_channels()

        assert "C123" in impl._resolved_channel_ids
        assert "C456" in impl._resolved_channel_ids

    @pytest.mark.asyncio
    async def test_resolve_unknown_channel_not_found(self, mock_backend):
        """Test that unknown channels are not added to resolved set."""
        impl = MessageReaderPushAdapterImpl(mock_backend, channels={"unknown_channel"})

        await mock_backend.connect()
        await impl._resolve_channels()

        # The channel was not found by ID or name
        # Current implementation logs warning and doesn't add it
        assert "unknown_channel" not in impl._resolved_channel_ids

    @pytest.mark.asyncio
    async def test_resolve_empty_channels(self, mock_backend):
        """Test resolving with no channels specified."""
        impl = MessageReaderPushAdapterImpl(mock_backend, channels=set())

        await mock_backend.connect()
        await impl._resolve_channels()

        assert impl._resolved_channel_ids == set()


class TestSendMessagesThread:
    """Tests for _send_messages_thread function."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        return MockBackendForCSP()

    def test_send_messages(self, mock_backend):
        """Test sending messages through the thread."""
        queue = Queue()
        thread = threading.Thread(
            target=_send_messages_thread,
            args=(queue, mock_backend),
            daemon=True,
        )
        thread.start()

        # Send a message
        msg = Message(channel_id="C123", content="Hello!")
        queue.put(msg)

        # Send stop signal
        queue.put(None)
        queue.join()
        thread.join(timeout=2.0)

        # Verify message was sent
        assert len(mock_backend.sent_messages) == 1
        assert mock_backend.sent_messages[0].content == "Hello!"
        assert mock_backend.sent_messages[0].channel_id == "C123"

    def test_send_multiple_messages(self, mock_backend):
        """Test sending multiple messages."""
        queue = Queue()
        thread = threading.Thread(
            target=_send_messages_thread,
            args=(queue, mock_backend),
            daemon=True,
        )
        thread.start()

        # Send messages
        for i in range(5):
            msg = Message(channel_id="C123", content=f"Message {i}")
            queue.put(msg)

        # Send stop signal
        queue.put(None)
        queue.join()
        thread.join(timeout=2.0)

        assert len(mock_backend.sent_messages) == 5


class TestCSPGraphExecution:
    """Tests for CSP graph execution with the adapter."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        return MockBackendForCSP()

    def test_publish_single_message(self, mock_backend):
        """Test publishing a single message through CSP."""
        adapter = BackendAdapter(mock_backend)

        @csp.graph
        def test_graph():
            msg = csp.const(Message(channel_id="C123", content="Test message"))
            adapter.publish(msg)

        csp.run(
            test_graph,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.5),
            realtime=True,
        )

        # Give thread time to process
        import time

        time.sleep(0.2)

        assert len(mock_backend.sent_messages) >= 1
        assert mock_backend.sent_messages[0].content == "Test message"

    def test_publish_multiple_messages(self, mock_backend):
        """Test publishing multiple messages through CSP."""
        adapter = BackendAdapter(mock_backend)

        @csp.node
        def generate_messages() -> ts[Message]:
            with csp.alarms():
                a_msg = csp.alarm(Message)

            with csp.start():
                csp.schedule_alarm(
                    a_msg,
                    timedelta(milliseconds=10),
                    Message(channel_id="C1", content="First"),
                )
                csp.schedule_alarm(
                    a_msg,
                    timedelta(milliseconds=20),
                    Message(channel_id="C2", content="Second"),
                )

            if csp.ticked(a_msg):
                return a_msg

        @csp.graph
        def test_graph():
            messages = generate_messages()
            adapter.publish(messages)

        csp.run(
            test_graph,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.5),
            realtime=True,
        )

        import time

        time.sleep(0.3)

        assert len(mock_backend.sent_messages) >= 2

    def test_publish_presence(self, mock_backend):
        """Test publishing presence updates."""
        adapter = BackendAdapter(mock_backend)

        @csp.graph
        def test_graph():
            presence = csp.const("available")
            adapter.publish_presence(presence)

        csp.run(
            test_graph,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.5),
            realtime=True,
        )

        import time

        time.sleep(0.2)

        assert "available" in mock_backend.presence_updates


class TestMessageReaderFunction:
    """Tests for message_reader convenience function."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        backend = MockBackendForCSP()
        backend.add_channel("C123", "general")
        return backend

    def test_message_reader_returns_adapter(self, mock_backend):
        """Test that message_reader returns a CSP adapter."""
        # This is a CSP function, so we just verify it's callable
        # Full test requires running in a graph
        result = message_reader(mock_backend, channels={"C123"})
        # Result is a CSP wiring object
        assert result is not None


class TestMessageWriterNode:
    """Tests for message_writer CSP node."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        return MockBackendForCSP()

    def test_message_writer_sends_messages(self, mock_backend):
        """Test that message_writer sends messages."""

        @csp.graph
        def test_graph():
            msg = csp.const(Message(channel_id="C123", content="Writer test"))
            message_writer(mock_backend, msg)

        csp.run(
            test_graph,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.5),
            realtime=True,
        )

        import time

        time.sleep(0.2)

        assert len(mock_backend.sent_messages) >= 1
        assert mock_backend.sent_messages[0].content == "Writer test"


class TestBackendNotImplementedFetchChannel:
    """Tests for backends that don't implement fetch_channel."""

    @pytest.fixture
    def mock_backend_no_fetch(self):
        """Create a mock backend without fetch_channel."""

        class NoFetchBackend:
            connected = True

            async def fetch_channel(self, *args, **kwargs):
                raise NotImplementedError("Backend doesn't support fetch_channel")

            async def stream_messages(self, **kwargs):
                if False:
                    yield

        return NoFetchBackend()

    @pytest.mark.asyncio
    async def test_uses_channel_as_id_when_not_implemented(self, mock_backend_no_fetch):
        """Test that channels are used as IDs when fetch_channel not implemented."""
        impl = MessageReaderPushAdapterImpl(mock_backend_no_fetch, channels={"some_channel"})

        await impl._resolve_channels()

        # Should just add the channel as-is since fetch_channel raises NotImplementedError
        assert "some_channel" in impl._resolved_channel_ids


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        return MockBackendForCSP()

    def test_adapter_with_none_channels(self, mock_backend):
        """Test adapter with None channels."""
        adapter = BackendAdapter(mock_backend)

        @csp.graph
        def test_graph():
            # Should not raise
            messages = adapter.subscribe(channels=None)
            csp.add_graph_output("messages", messages)

        # Should complete without error (non-realtime to avoid event loop issues)
        csp.run(
            test_graph,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.1),
        )
        # No messages expected since backend has nothing to stream

    def test_adapter_with_empty_channels(self, mock_backend):
        """Test adapter with empty channels set."""
        adapter = BackendAdapter(mock_backend)

        @csp.graph
        def test_graph():
            messages = adapter.subscribe(channels=set())
            csp.add_graph_output("messages", messages)

        # Non-realtime to avoid event loop issues in CI
        csp.run(
            test_graph,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.1),
        )

    @pytest.mark.asyncio
    async def test_resolve_channels_with_exception(self, mock_backend):
        """Test channel resolution when backend raises exception."""

        class FailingBackend:
            connected = True

            async def fetch_channel(self, *args, **kwargs):
                raise RuntimeError("Connection failed")

        backend = FailingBackend()
        impl = MessageReaderPushAdapterImpl(backend, channels={"failing_channel"})

        # Should not raise, should log warning and use channel as ID
        await impl._resolve_channels()

        assert "failing_channel" in impl._resolved_channel_ids


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_publish_only_pattern(self):
        """Test a simple publish-only pattern (no subscription)."""
        backend = MockBackendForCSP()
        adapter = BackendAdapter(backend)

        @csp.graph
        def publish_bot():
            msg = csp.const(Message(channel_id="C123", content="Hello from bot"))
            adapter.publish(msg)

        csp.run(
            publish_bot,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.5),
            realtime=True,
        )

        import time

        time.sleep(0.3)

        # Check that message was published
        assert len(backend.sent_messages) >= 1
        assert backend.sent_messages[0].content == "Hello from bot"

    def test_scheduled_messages_pattern(self):
        """Test scheduling multiple messages over time."""
        backend = MockBackendForCSP()
        adapter = BackendAdapter(backend)

        @csp.node
        def schedule_messages() -> ts[Message]:
            with csp.alarms():
                alarm = csp.alarm(Message)

            with csp.start():
                for i in range(3):
                    csp.schedule_alarm(
                        alarm,
                        timedelta(milliseconds=10 * (i + 1)),
                        Message(channel_id="C123", content=f"Scheduled {i}"),
                    )

            if csp.ticked(alarm):
                return alarm

        @csp.graph
        def scheduled_bot():
            messages = schedule_messages()
            adapter.publish(messages)

        csp.run(
            scheduled_bot,
            starttime=datetime.now(),
            endtime=timedelta(seconds=0.5),
            realtime=True,
        )

        import time

        time.sleep(0.3)

        assert len(backend.sent_messages) >= 3

    def test_adapter_properties(self):
        """Test that adapter exposes backend correctly."""
        backend = MockBackendForCSP()
        adapter = BackendAdapter(backend)

        assert adapter.backend is backend
        assert adapter._backend is backend
