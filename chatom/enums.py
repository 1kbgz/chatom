from typing import Literal, Union

DISCORD = "discord"
# EMAIL = "email"
IRC = "irc"
LINE = "line"
MATRIX = "matrix"
# MATTERMOST = "mattermost"
# MESSENGER = "messenger"
SLACK = "slack"
SYMPHONY = "symphony"
# TEAMS = "teams"
TELEGRAM = "telegram"
# WHATSAPP = "whatsapp"
ZULIP = "zulip"

BACKEND = Union[Literal["discord", "irc", "line", "matrix", "slack", "symphony", "telegram", "zulip"], str]  # noqa: UP007
ALL_BACKENDS = [
    DISCORD,
    # EMAIL,
    IRC,
    LINE,
    MATRIX,
    # MATTERMOST,
    # MESSENGER,
    SLACK,
    SYMPHONY,
    # TEAMS,
    TELEGRAM,
    # WHATSAPP,
    ZULIP,
]

__all__ = (
    "BACKEND",
    "DISCORD",
    # "EMAIL",
    "IRC",
    "LINE",
    "MATRIX",
    # "MATTERMOST",
    # "MESSENGER",
    "SLACK",
    "SYMPHONY",
    # "TEAMS",
    "TELEGRAM",
    # "WHATSAPP",
    "ZULIP",
)
