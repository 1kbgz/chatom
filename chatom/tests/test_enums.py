"""Tests for chatom enums."""


class TestEnums:
    """Tests for backend enums."""

    def test_all_backends_listed(self):
        """Ensure that ALL_BACKENDS contains all backend types."""
        from chatom.enums import ALL_BACKENDS

        # ALL_BACKENDS should have expected members
        for backend in ALL_BACKENDS:
            assert isinstance(backend, str)

    def test_backend_values(self):
        """Test that backend constants have expected values."""
        from chatom.enums import DISCORD, SLACK, SYMPHONY

        assert DISCORD == "discord"
        # assert EMAIL == "email"
        # assert IRC == "irc"
        # assert MATRIX == "matrix"
        assert SLACK == "slack"
        assert SYMPHONY == "symphony"

    def test_all_backends_count(self):
        """Test that ALL_BACKENDS has expected count."""
        from chatom.enums import ALL_BACKENDS

        # At least 3 backends (could be more)
        assert len(ALL_BACKENDS) >= 3

    def test_backend_type_annotation(self):
        """Test BACKEND type annotation."""
        from chatom.enums import BACKEND

        # BACKEND is a Literal type - just verify it exists
        assert BACKEND is not None


class TestCapabilityImplementationAgreement:
    """Every declared capability must have a method that does not refuse."""

    def test_no_backend_declares_a_capability_it_refuses(self):
        """Regression: Symphony declared EMOJI_REACTIONS while add_reaction raised.

        A capability that lies makes capability-gated callers offer a tool that
        always fails, which is what the gating exists to prevent.
        """
        import importlib
        import inspect

        import chatom
        from chatom.backend.backend import BackendBase
        from chatom.base.capabilities import Capability

        backends = {
            "discord": "DiscordBackend",
            "slack": "SlackBackend",
            "symphony": "SymphonyBackend",
            "telegram": "TelegramBackend",
        }
        gates = {
            Capability.EMOJI_REACTIONS: ("add_reaction", "remove_reaction"),
            Capability.EDITING: ("edit_message",),
            Capability.DELETING: ("delete_message",),
            Capability.FILES: ("upload_file",),
            Capability.MESSAGE_SEARCH: ("search_messages",),
            Capability.FORWARDING: ("forward_message",),
        }

        offenders = []
        for name, class_name in backends.items():
            capabilities = getattr(chatom, f"{name.upper()}_CAPABILITIES")
            backend_class = getattr(importlib.import_module(f"chatom.{name}.backend"), class_name)
            for capability, methods in gates.items():
                if not capabilities.supports(capability):
                    continue
                for method in methods:
                    own = getattr(backend_class, method, None)
                    if own is None or own is getattr(BackendBase, method, None):
                        continue
                    try:
                        source = inspect.getsource(own)
                    except OSError:  # pragma: no cover - source always available here
                        continue
                    if "raise NotImplementedError" in source:
                        offenders.append(f"{name}.{method} refuses but {capability.name} is declared")

        assert not offenders, offenders
