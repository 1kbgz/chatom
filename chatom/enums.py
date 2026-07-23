from typing import Literal, Union

DISCORD = "discord"
# EMAIL = "email"
# IRC = "irc"
# MATRIX = "matrix"
# MATTERMOST = "mattermost"
# MESSENGER = "messenger"
SLACK = "slack"
SYMPHONY = "symphony"
# TEAMS = "teams"
TELEGRAM = "telegram"
# WHATSAPP = "whatsapp"
# ZULIP = "zulip"

BACKEND = Union[Literal["discord", "slack", "symphony", "telegram"], str]  # noqa: UP007
ALL_BACKENDS = [
    DISCORD,
    # EMAIL,
    # IRC,
    # MATRIX,
    # MATTERMOST,
    # MESSENGER,
    SLACK,
    SYMPHONY,
    # TEAMS,
    TELEGRAM,
    # WHATSAPP,
    # ZULIP,
]

__all__ = (
    "BACKEND",
    "DISCORD",
    # "EMAIL",
    # "IRC",
    # "MATRIX",
    # "MATTERMOST",
    # "MESSENGER",
    "SLACK",
    "SYMPHONY",
    # "TEAMS",
    "TELEGRAM",
    # "WHATSAPP",
    # "ZULIP",
)
