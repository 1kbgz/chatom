from typing import Literal


class TestEnums:
    def test_all_backends_listed(self):
        from chatom.enums import ALL_BACKENDS, BACKEND

        # Ensure that ALL_BACKENDS actually has all backends
        for backend in ALL_BACKENDS:
            assert Literal[backend] in BACKEND.__args__
