import pytest

from chatom import User, mention_user
from chatom.discord import DiscordUser
from chatom.email import EmailUser
from chatom.irc import IRCUser
from chatom.matrix import MatrixUser
from chatom.slack import SlackUser
from chatom.symphony import SymphonyUser


class TestMention:
    @pytest.mark.parametrize(
        "msg,expected",
        [
            (DiscordUser(handle="jane_doe", id="456", name="Jane Doe"), "<@!456>"),
            (EmailUser(handle="", id="789", name="Alice"), "Alice"),
            (EmailUser(handle="", id="101", name="Bob", email="bob@example.com"), "<a href='mailto:bob@example.com'>Bob</a>"),
            (IRCUser(handle="charlie", id="112", name="Charlie"), "charlie"),
            (IRCUser(handle="", id="131", name="David"), "David"),
            (MatrixUser(handle="eve", id="415", name="Eve"), "@eve:matrix.org"),
            # (User(handle="charlie", id="112", name="Charlie"), "@charlie"),
            # (User(handle="", id="131", name="David"), "David"),
            # (User(handle="eve", id="415", name="Eve"), "@Eve"),
            (SlackUser(handle="john_doe", id="123", name="John Doe"), "<@123>"),
            (SymphonyUser(handle="frank", id="161", name="Frank"), "@Frank"),
            # (User(handle="eve", id="415", name="Eve"), "<at>Eve</at>"),
            # (User(handle="alice", id="789", name="Alice"), "@alice"),
            # (User(handle="", id="101", name="Bob"), "Bob"),
            # (User(handle="grace", id="718", name="Grace"), "@Grace"),
            # (User(handle="heidi", id="192", name="Heidi"), "@**Heidi**"),
            (User(handle="ivan", id="202", name="Ivan"), "Ivan"),
        ],
    )
    def test_mention(self, msg, expected):
        result = mention_user(msg)
        assert result == expected
