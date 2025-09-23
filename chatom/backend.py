from typing import Literal, Union

DISCORD = "discord"
EMAIL = "email"
IRC = "irc"
MATRIX = "matrix"
MATTERMOST = "mattermost"
MESSENGER = "messenger"
SLACK = "slack"
SYMPHONY = "symphony"
TEAMS = "teams"
TELEGRAM = "telegram"
WHATSAPP = "whatsapp"
ZULIP = "zulip"

BACKEND = Union[
    Literal[DISCORD],
    Literal[EMAIL],
    Literal[IRC],
    Literal[MATRIX],
    Literal[MATTERMOST],
    Literal[MESSENGER],
    Literal[SLACK],
    Literal[SYMPHONY],
    Literal[TEAMS],
    Literal[TELEGRAM],
    Literal[WHATSAPP],
    Literal[ZULIP],
    str,
]
ALL_BACKENDS = [
    DISCORD,
    EMAIL,
    IRC,
    MATRIX,
    MATTERMOST,
    MESSENGER,
    SLACK,
    SYMPHONY,
    TEAMS,
    TELEGRAM,
    WHATSAPP,
    ZULIP,
]

__all__ = ("BACKEND", "DISCORD", "MATTERMOST", "MESSENGER", "SLACK", "SYMPHONY", "TEAMS", "TELEGRAM", "WHATSAPP", "ZULIP")
