import pytest

from chatom.mention import mention_user
from chatom.user import User


class TestMention:
    @pytest.mark.parametrize(
        "user,backend,expected",
        [
            (User(handle="jane_doe", id="456", name="Jane Doe"), "discord", "<@!456>"),
            (User(handle="", id="789", name="Alice"), "email", "Alice"),
            (User(handle="", id="101", name="Bob", email="bob@example.com"), "email", "<a href='mailto:bob@example.com'>Bob</a>"),
            (User(handle="charlie", id="112", name="Charlie"), "irc", "charlie"),
            (User(handle="", id="131", name="David"), "irc", "David"),
            (User(handle="eve", id="415", name="Eve"), "matrix", "@eve:matrix.org"),
            (User(handle="charlie", id="112", name="Charlie"), "mattermost", "@charlie"),
            (User(handle="", id="131", name="David"), "mattermost", "David"),
            (User(handle="eve", id="415", name="Eve"), "messenger", "@Eve"),
            (User(handle="john_doe", id="123", name="John Doe"), "slack", "<@123>"),
            (User(handle="frank", id="161", name="Frank"), "symphony", "@Frank"),
            (User(handle="eve", id="415", name="Eve"), "teams", "<at>Eve</at>"),
            (User(handle="alice", id="789", name="Alice"), "telegram", "@alice"),
            (User(handle="", id="101", name="Bob"), "telegram", "Bob"),
            (User(handle="grace", id="718", name="Grace"), "whatsapp", "@Grace"),
            (User(handle="heidi", id="192", name="Heidi"), "zulip", "@**Heidi**"),
            (User(handle="ivan", id="202", name="Ivan"), "unknown", "Ivan"),
        ],
    )
    def test_mention(self, user, backend, expected):
        result = mention_user(user, backend)
        assert result == expected
