from typing import Literal


class TestBackend:
    def test_all_backends_listed(self):
        from chatom.backend import ALL_BACKENDS, BACKEND

        # Ensure that ALL_BACKENDS actually has all backends
        for backend in ALL_BACKENDS:
            assert Literal[backend] in BACKEND.__args__
