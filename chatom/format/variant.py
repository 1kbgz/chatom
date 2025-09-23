from typing import Literal, Union

PLAINTEXT = "plaintext"
MARKDOWN = "markdown"
SLACK_MARKDOWN = "slack-markdown"
DISCORD_MARKDOWN = "discord-markdown"
HTML = "html"
SYMPHONY_HTML = "symphony-html"

FORMAT = Union[
    Literal[PLAINTEXT],
    Literal[MARKDOWN],
    Literal[SLACK_MARKDOWN],
    Literal[DISCORD_MARKDOWN],
    Literal[HTML],
    Literal[SYMPHONY_HTML],
    str,
]

__all__ = ("FORMAT", "PLAINTEXT", "MARKDOWN", "SLACK_MARKDOWN", "DISCORD_MARKDOWN", "HTML", "SYMPHONY_HTML")
