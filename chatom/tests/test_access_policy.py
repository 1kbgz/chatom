"""Tests for BackendToolset access policy enforcement.

These tests verify that the access control guardrails cannot be bypassed
by prompt injection or malicious tool calls.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatom.agent.toolset import AccessDeniedError, AccessPolicy, BackendToolset
from chatom.base import Channel, ChannelType, Message, User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_backend(members=None, channel_type=ChannelType.PUBLIC):
    """Create a mock backend with configurable membership and channel info."""
    backend = MagicMock()
    backend.name = "test"
    backend.capabilities = None
    # Mirror BackendBase.normalize_channel_id (identity) so channel-id
    # comparisons in the access policy behave like a real backend.
    backend.normalize_channel_id = lambda channel_id: channel_id

    # fetch_channel_members
    if members is not None:
        backend.fetch_channel_members = AsyncMock(return_value=members)
    else:
        backend.fetch_channel_members = AsyncMock(side_effect=NotImplementedError("not supported"))

    # lookup_channel
    resolved_channel = Channel(id="C123", name="general", channel_type=channel_type)
    backend.lookup_channel = AsyncMock(return_value=resolved_channel)

    # fetch_messages
    backend.fetch_messages = AsyncMock(return_value=[])

    # search_messages
    backend.search_messages = AsyncMock(return_value=[])

    # send_message
    backend.send_message = AsyncMock(return_value=None)

    return backend


def _make_user(user_id="U001", name="alice"):
    return User(id=user_id, name=name)


def _make_toolset(backend, policy):
    return BackendToolset(backend=backend, access_policy=policy)


def _run(coro):
    """Run an async function synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Test: Blocked channels
# ---------------------------------------------------------------------------


class TestBlockedChannels:
    def test_blocked_channel_is_denied(self):
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=_make_user(),
            blocked_channel_ids={"C_SECRET"},
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="blocked by policy"):
            _run(toolset._check_channel_access(Channel(id="C_SECRET", name="secret")))

    def test_non_blocked_channel_passes(self):
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=_make_user(),
            blocked_channel_ids={"C_SECRET"},
            require_membership=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)
        # Should not raise
        _run(toolset._check_channel_access(Channel(id="C_OK", name="general")))


# ---------------------------------------------------------------------------
# Test: Allowed channel whitelist
# ---------------------------------------------------------------------------


class TestAllowedChannels:
    def test_whitelisted_channel_passes_without_membership_check(self):
        """If allowed_channel_ids is set, whitelisted channels bypass membership."""
        backend = _make_backend(members=[])  # user NOT in members
        policy = AccessPolicy(
            requesting_user=_make_user(),
            allowed_channel_ids={"C123"},
            require_membership=True,
        )
        toolset = _make_toolset(backend, policy)
        # Should pass — whitelist takes precedence
        _run(toolset._check_channel_access(Channel(id="C123", name="general")))
        # fetch_channel_members should NOT be called
        backend.fetch_channel_members.assert_not_called()

    def test_non_whitelisted_channel_denied(self):
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=_make_user(),
            allowed_channel_ids={"C123"},
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="not in the allowed channel list"):
            _run(toolset._check_channel_access(Channel(id="C_OTHER", name="other")))


# ---------------------------------------------------------------------------
# Test: Restrict to invoking channel
# ---------------------------------------------------------------------------


class TestRestrictToInvokingChannel:
    def test_same_channel_passes(self):
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=_make_user(),
            invoking_channel_id="C123",
            restrict_to_invoking_channel=True,
            require_membership=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)
        _run(toolset._check_channel_access(Channel(id="C123", name="general")))

    def test_different_channel_denied(self):
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=_make_user(),
            invoking_channel_id="C123",
            restrict_to_invoking_channel=True,
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="restricted to the invoking channel"):
            _run(toolset._check_channel_access(Channel(id="C_OTHER", name="other")))

    def test_cross_channel_allowed_when_disabled(self):
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=_make_user(),
            invoking_channel_id="C123",
            restrict_to_invoking_channel=False,
            require_membership=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)
        _run(toolset._check_channel_access(Channel(id="C_OTHER", name="other")))


# ---------------------------------------------------------------------------
# Test: DM blocking
# ---------------------------------------------------------------------------


class TestBlockDmReads:
    def test_dm_channel_blocked(self):
        backend = _make_backend(members=[_make_user()], channel_type=ChannelType.DIRECT)
        policy = AccessPolicy(
            requesting_user=_make_user(),
            block_dm_reads=True,
            restrict_to_invoking_channel=False,
            require_membership=False,
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="direct messages is blocked"):
            _run(toolset._check_channel_access(Channel(id="D123", name="")))

    def test_group_dm_blocked(self):
        backend = _make_backend(members=[_make_user()], channel_type=ChannelType.GROUP)
        policy = AccessPolicy(
            requesting_user=_make_user(),
            block_dm_reads=True,
            restrict_to_invoking_channel=False,
            require_membership=False,
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="direct messages is blocked"):
            _run(toolset._check_channel_access(Channel(id="G123", name="")))

    def test_dm_allowed_when_disabled(self):
        backend = _make_backend(members=[_make_user()], channel_type=ChannelType.DIRECT)
        policy = AccessPolicy(
            requesting_user=_make_user(),
            block_dm_reads=False,
            restrict_to_invoking_channel=False,
            require_membership=False,
        )
        toolset = _make_toolset(backend, policy)
        _run(toolset._check_channel_access(Channel(id="D123", name="")))


# ---------------------------------------------------------------------------
# Test: Membership checks
# ---------------------------------------------------------------------------


class TestMembershipCheck:
    def test_member_allowed(self):
        user = _make_user("U001")
        backend = _make_backend(members=[user])
        policy = AccessPolicy(
            requesting_user=user,
            require_membership=True,
            restrict_to_invoking_channel=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)
        _run(toolset._check_channel_access(Channel(id="C123", name="general")))

    def test_non_member_denied(self):
        user = _make_user("U001")
        other_user = _make_user("U999", "bob")
        backend = _make_backend(members=[other_user])  # U001 not in list
        policy = AccessPolicy(
            requesting_user=user,
            require_membership=True,
            restrict_to_invoking_channel=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="not a member"):
            _run(toolset._check_channel_access(Channel(id="C123", name="general")))

    def test_membership_not_supported_denies_by_default(self):
        """If backend can't list members, deny access (fail closed)."""
        user = _make_user("U001")
        backend = _make_backend(members=None)  # raises NotImplementedError
        policy = AccessPolicy(
            requesting_user=user,
            require_membership=True,
            restrict_to_invoking_channel=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="not a member"):
            _run(toolset._check_channel_access(Channel(id="C123", name="general")))

    def test_membership_cache(self):
        """Membership result is cached — only one API call per channel."""
        user = _make_user("U001")
        backend = _make_backend(members=[user])
        policy = AccessPolicy(
            requesting_user=user,
            require_membership=True,
            restrict_to_invoking_channel=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        _run(toolset._check_channel_access(Channel(id="C123", name="general")))
        _run(toolset._check_channel_access(Channel(id="C123", name="general")))

        # Should only call the backend once
        assert backend.fetch_channel_members.call_count == 1

    def test_no_user_context_denies(self):
        """If no requesting_user is set, membership check fails closed."""
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=None,
            require_membership=True,
            restrict_to_invoking_channel=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="no requesting user"):
            _run(toolset._check_channel_access(Channel(id="C123", name="general")))


# ---------------------------------------------------------------------------
# Test: History time filtering
# ---------------------------------------------------------------------------


class TestHistoryTimeFiltering:
    def test_filters_old_messages(self):
        """Messages before history_visible_since are excluded."""
        cutoff = datetime(2025, 6, 1, tzinfo=timezone.utc)
        messages = [
            Message(id="m1", content="old", timestamp=datetime(2025, 5, 15, tzinfo=timezone.utc)),
            Message(id="m2", content="new", timestamp=datetime(2025, 6, 15, tzinfo=timezone.utc)),
            Message(id="m3", content="newer", timestamp=datetime(2025, 6, 20, tzinfo=timezone.utc)),
        ]
        policy = AccessPolicy(history_visible_since=cutoff)
        toolset = _make_toolset(_make_backend(), policy)

        filtered = toolset._filter_messages_by_time(messages)
        assert len(filtered) == 2
        assert filtered[0].id == "m2"
        assert filtered[1].id == "m3"

    def test_no_cutoff_returns_all(self):
        """Without history_visible_since, all messages pass through."""
        messages = [
            Message(id="m1", content="old", timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc)),
            Message(id="m2", content="new", timestamp=datetime(2025, 6, 15, tzinfo=timezone.utc)),
        ]
        policy = AccessPolicy(history_visible_since=None)
        toolset = _make_toolset(_make_backend(), policy)

        filtered = toolset._filter_messages_by_time(messages)
        assert len(filtered) == 2

    def test_epoch_millis_timestamps(self):
        """Handles numeric epoch millisecond timestamps."""
        cutoff = datetime(2025, 6, 1, tzinfo=timezone.utc)
        cutoff_ms = int(cutoff.timestamp() * 1000)
        messages = [
            {"id": "m1", "content": "old", "timestamp": cutoff_ms - 1000000},
            {"id": "m2", "content": "new", "timestamp": cutoff_ms + 1000000},
        ]
        policy = AccessPolicy(history_visible_since=cutoff)
        toolset = _make_toolset(_make_backend(), policy)

        filtered = toolset._filter_messages_by_time(messages)
        assert len(filtered) == 1
        assert filtered[0]["id"] == "m2"

    def test_messages_without_timestamp_excluded(self):
        """Messages with no timestamp are excluded for safety."""
        cutoff = datetime(2025, 6, 1, tzinfo=timezone.utc)
        messages = [
            Message(id="m1", content="no-ts"),  # timestamp=None
            Message(id="m2", content="has-ts", timestamp=datetime(2025, 6, 15, tzinfo=timezone.utc)),
        ]
        policy = AccessPolicy(history_visible_since=cutoff)
        toolset = _make_toolset(_make_backend(), policy)

        filtered = toolset._filter_messages_by_time(messages)
        assert len(filtered) == 1
        assert filtered[0].id == "m2"


# ---------------------------------------------------------------------------
# Test: Max messages cap
# ---------------------------------------------------------------------------


class TestMaxMessagesCap:
    def test_limit_capped(self):
        """The limit passed to backend is capped by max_messages_per_request."""
        user = _make_user("U001")
        backend = _make_backend(members=[user])
        policy = AccessPolicy(
            requesting_user=user,
            max_messages_per_request=25,
            restrict_to_invoking_channel=False,
            require_membership=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        # Call with limit=200 — should be capped to 25
        args = {"channel": {"id": "C123"}, "limit": 200}
        _run(toolset._call_read_channel_history(args))

        # Verify the backend was called with limit=25
        backend.fetch_messages.assert_called_once()
        call_kwargs = backend.fetch_messages.call_args
        assert call_kwargs.kwargs.get("limit") == 25 or call_kwargs[1].get("limit") == 25


# ---------------------------------------------------------------------------
# Test: call_tool returns error dict on denial (not crash)
# ---------------------------------------------------------------------------


class TestCallToolErrorHandling:
    def test_access_denied_returns_error_dict(self):
        """AccessDeniedError results in an error dict, not an exception."""
        user = _make_user("U001")
        backend = _make_backend(members=[_make_user("U999", "bob")])
        policy = AccessPolicy(
            requesting_user=user,
            require_membership=True,
            restrict_to_invoking_channel=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        # Simulate a call_tool invocation
        ctx = MagicMock()
        tool = MagicMock()
        result = _run(
            toolset.call_tool(
                "read_channel_history",
                {"channel": {"id": "C123"}, "limit": 50},
                ctx,
                tool,
            )
        )
        assert result["error"] == "access_denied"
        assert "not a member" in result["message"]


# ---------------------------------------------------------------------------
# Test: Search enforcement
# ---------------------------------------------------------------------------


class TestSearchEnforcement:
    def test_search_restricted_to_invoking_channel(self):
        """When restrict_to_invoking_channel and no channel specified, it's auto-scoped."""
        user = _make_user("U001")
        backend = _make_backend(members=[user])
        policy = AccessPolicy(
            requesting_user=user,
            invoking_channel_id="C123",
            restrict_to_invoking_channel=True,
            require_membership=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        _run(toolset._call_search_messages({"query": "test", "limit": 10}))

        # Should have been called with a channel
        call_args = backend.search_messages.call_args
        ch = call_args.kwargs.get("channel") or call_args[1].get("channel")
        assert ch is not None
        assert ch.id == "C123"

    def test_search_denied_cross_channel(self):
        """Searching a different channel is denied when restricted."""
        user = _make_user("U001")
        backend = _make_backend(members=[user])
        policy = AccessPolicy(
            requesting_user=user,
            invoking_channel_id="C123",
            restrict_to_invoking_channel=True,
            require_membership=False,
            block_dm_reads=False,
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="restricted to the invoking channel"):
            _run(toolset._call_search_messages({"query": "test", "channel": {"id": "C_OTHER"}, "limit": 10}))


# ---------------------------------------------------------------------------
# Test: Combined policy enforcement order
# ---------------------------------------------------------------------------


class TestPolicyOrder:
    def test_blocked_takes_priority_over_whitelist(self):
        """A channel in both blocked and allowed is still blocked."""
        backend = _make_backend(members=[_make_user()])
        policy = AccessPolicy(
            requesting_user=_make_user(),
            blocked_channel_ids={"C123"},
            allowed_channel_ids={"C123"},  # also whitelisted
        )
        toolset = _make_toolset(backend, policy)

        with pytest.raises(AccessDeniedError, match="blocked by policy"):
            _run(toolset._check_channel_access(Channel(id="C123", name="general")))

    def test_default_policy_restricts_to_invoking_channel(self):
        """The default policy from AgentCommand restricts to invoking channel."""
        # Simulating what build_access_policy returns
        policy = AccessPolicy(
            requesting_user=_make_user(),
            invoking_channel_id="C_ORIGIN",
            restrict_to_invoking_channel=True,
            require_membership=True,
            block_dm_reads=True,
        )
        backend = _make_backend(members=[_make_user()])
        toolset = _make_toolset(backend, policy)

        # Trying to access a different channel should be denied
        with pytest.raises(AccessDeniedError):
            _run(toolset._check_channel_access(Channel(id="C_OTHER", name="other")))
