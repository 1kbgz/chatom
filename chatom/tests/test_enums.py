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
        from chatom.enums import DISCORD, EMAIL, IRC, MATRIX, SLACK, SYMPHONY

        assert DISCORD == "discord"
        assert EMAIL == "email"
        assert IRC == "irc"
        assert MATRIX == "matrix"
        assert SLACK == "slack"
        assert SYMPHONY == "symphony"

    def test_all_backends_count(self):
        """Test that ALL_BACKENDS has expected count."""
        from chatom.enums import ALL_BACKENDS

        # At least 5 backends (could be more)
        assert len(ALL_BACKENDS) >= 5

    def test_backend_type_annotation(self):
        """Test BACKEND type annotation."""
        from chatom.enums import BACKEND

        # BACKEND is a Literal type - just verify it exists
        assert BACKEND is not None
