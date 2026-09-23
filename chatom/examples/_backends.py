"""Shared backend construction for the runnable examples.

Every example demonstrates one Chatom operation against any configured backend.
Construction and credentials are the only things that vary by platform, so they
live here instead of being repeated in each example.

Environment Variables:
    Slack:
        SLACK_BOT_TOKEN, SLACK_TEST_CHANNEL_NAME, SLACK_TEST_USER_NAME, and
        SLACK_APP_TOKEN when streaming (Socket Mode)

    Discord:
        DISCORD_TOKEN, DISCORD_GUILD_NAME, DISCORD_TEST_CHANNEL_NAME,
        DISCORD_TEST_USER_NAME

    Symphony:
        SYMPHONY_HOST, SYMPHONY_BOT_USERNAME, SYMPHONY_TEST_ROOM_NAME,
        SYMPHONY_TEST_USER_NAME, and one of SYMPHONY_BOT_PRIVATE_KEY_PATH or
        SYMPHONY_BOT_PRIVATE_KEY_CONTENT

    Telegram:
        TELEGRAM_TOKEN, TELEGRAM_TEST_CHAT_NAME, TELEGRAM_TEST_USER_NAME

    Matrix:
        MATRIX_HOMESERVER, MATRIX_USER_ID, MATRIX_ACCESS_TOKEN,
        MATRIX_TEST_ROOM_ALIAS, MATRIX_TEST_USER_ID

    Zulip:
        ZULIP_SITE, ZULIP_EMAIL, ZULIP_API_KEY, ZULIP_TEST_CHANNEL_NAME,
        ZULIP_TEST_USER_EMAIL

    IRC:
        IRC_SERVER, IRC_TEST_CHANNEL, IRC_TEST_USER_NICK, and optionally
        IRC_NICKNAME and IRC_PASSWORD

    LINE:
        LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, LINE_TEST_CHANNEL_ID,
        LINE_TEST_USER_ID
"""

import os

__all__ = (
    "BACKENDS",
    "build_backend",
    "channel_env",
    "get_env",
    "resolve_channel",
    "test_channel",
    "test_user",
)

# Set while probing optional backends so missing variables are not reported.
_quiet = False

BACKENDS = (
    "slack",
    "discord",
    "symphony",
    "telegram",
    "matrix",
    "zulip",
    "irc",
    "line",
)

_CHANNEL_ENV = {
    "slack": "SLACK_TEST_CHANNEL_NAME",
    "discord": "DISCORD_TEST_CHANNEL_NAME",
    "symphony": "SYMPHONY_TEST_ROOM_NAME",
    "telegram": "TELEGRAM_TEST_CHAT_NAME",
    "matrix": "MATRIX_TEST_ROOM_ALIAS",
    "zulip": "ZULIP_TEST_CHANNEL_NAME",
    "irc": "IRC_TEST_CHANNEL",
    "line": "LINE_TEST_CHANNEL_ID",
}

_USER_ENV = {
    "slack": "SLACK_TEST_USER_NAME",
    "discord": "DISCORD_TEST_USER_NAME",
    "symphony": "SYMPHONY_TEST_USER_NAME",
    "telegram": "TELEGRAM_TEST_USER_NAME",
    "matrix": "MATRIX_TEST_USER_ID",
    "zulip": "ZULIP_TEST_USER_EMAIL",
    "irc": "IRC_TEST_USER_NICK",
    "line": "LINE_TEST_USER_ID",
}

# Backends that address channels by opaque id rather than by human-readable name.
_ID_ADDRESSED = frozenset({"line"})


def get_env(name: str, required: bool = True) -> str | None:
    """Get environment variable with validation."""
    value = os.environ.get(name)
    if required and not value:
        if not _quiet:
            print(f"Missing required environment variable: {name}")
        return None
    return value


def channel_env(backend_name: str) -> str:
    """Get the environment variable naming a backend's test channel."""
    return _CHANNEL_ENV[backend_name]


def test_channel(backend_name: str) -> str | None:
    """Get the configured test channel for a backend."""
    return get_env(_CHANNEL_ENV[backend_name])


def test_user(backend_name: str) -> str | None:
    """Get the configured test user for a backend."""
    return get_env(_USER_ENV[backend_name])


def _build_slack(streaming: bool = False):
    from chatom.slack import SlackBackend, SlackConfig

    token = get_env("SLACK_BOT_TOKEN")
    if not token:
        return None
    if not streaming:
        return SlackBackend(config=SlackConfig(bot_token=token))

    # Inbound events require Socket Mode and a separate app-level token.
    app_token = get_env("SLACK_APP_TOKEN")
    if not app_token:
        return None
    return SlackBackend(config=SlackConfig(bot_token=token, app_token=app_token, socket_mode=True))


def _build_discord(streaming: bool = False):
    from chatom.discord import DiscordBackend, DiscordConfig

    token = get_env("DISCORD_TOKEN")
    if not token or not get_env("DISCORD_GUILD_NAME"):
        return None
    return DiscordBackend(config=DiscordConfig(token=token, intents=["guilds", "guild_messages"]))


def _build_symphony(streaming: bool = False):
    from chatom.symphony import SymphonyBackend, SymphonyConfig

    host = get_env("SYMPHONY_HOST")
    bot_username = get_env("SYMPHONY_BOT_USERNAME")
    if not host or not bot_username:
        return None

    key_path = get_env("SYMPHONY_BOT_PRIVATE_KEY_PATH", required=False)
    key_content = get_env("SYMPHONY_BOT_PRIVATE_KEY_CONTENT", required=False)
    if not key_path and not key_content:
        print("Missing: SYMPHONY_BOT_PRIVATE_KEY_PATH or SYMPHONY_BOT_PRIVATE_KEY_CONTENT")
        return None

    kwargs = {"host": host, "bot_username": bot_username}
    if key_path:
        kwargs["bot_private_key_path"] = key_path
    else:
        from pydantic import SecretStr

        kwargs["bot_private_key_content"] = SecretStr(key_content)
    return SymphonyBackend(config=SymphonyConfig(**kwargs))


def _build_telegram(streaming: bool = False):
    from chatom.telegram import TelegramBackend, TelegramConfig

    token = get_env("TELEGRAM_TOKEN")
    if not token:
        return None
    return TelegramBackend(config=TelegramConfig(bot_token=token))


def _build_matrix(streaming: bool = False):
    from chatom.matrix import MatrixBackend, MatrixConfig

    homeserver = get_env("MATRIX_HOMESERVER")
    user_id = get_env("MATRIX_USER_ID")
    access_token = get_env("MATRIX_ACCESS_TOKEN")
    if not homeserver or not user_id or not access_token:
        return None
    return MatrixBackend(
        config=MatrixConfig(
            homeserver=homeserver,
            user_id=user_id,
            access_token=access_token,
            device_id=os.environ.get("MATRIX_DEVICE_ID", ""),
        )
    )


def _build_zulip(streaming: bool = False):
    from chatom.zulip import ZulipBackend, ZulipConfig

    site = get_env("ZULIP_SITE")
    email = get_env("ZULIP_EMAIL")
    api_key = get_env("ZULIP_API_KEY")
    if not site or not email or not api_key:
        return None
    return ZulipBackend(config=ZulipConfig(site=site, email=email, api_key=api_key))


def _build_irc(streaming: bool = False):
    from chatom.irc import IRCBackend, IRCConfig

    server = get_env("IRC_SERVER")
    channel = get_env("IRC_TEST_CHANNEL")
    if not server or not channel:
        return None
    return IRCBackend(
        config=IRCConfig(
            server=server,
            nickname=os.environ.get("IRC_NICKNAME", "chatom"),
            password=os.environ.get("IRC_PASSWORD", ""),
            channels=[channel],
        )
    )


def _build_line(streaming: bool = False):
    from chatom.line import LineBackend, LineConfig

    token = get_env("LINE_CHANNEL_ACCESS_TOKEN")
    secret = get_env("LINE_CHANNEL_SECRET")
    if not token or not secret:
        return None
    return LineBackend(config=LineConfig(channel_access_token=token, channel_secret=secret))


_BUILDERS = {
    "slack": _build_slack,
    "discord": _build_discord,
    "symphony": _build_symphony,
    "telegram": _build_telegram,
    "matrix": _build_matrix,
    "zulip": _build_zulip,
    "irc": _build_irc,
    "line": _build_line,
}


def build_backend(name: str, streaming: bool = False, quiet: bool = False):
    """Construct a backend from environment variables.

    Set `streaming` for examples that consume inbound events; Slack needs
    Socket Mode and an app-level token for those. Set `quiet` when probing
    several backends and an unconfigured one is expected rather than an error.

    Returns None, reporting what is missing, when the backend is not configured.
    """
    global _quiet

    builder = _BUILDERS.get(name)
    if builder is None:
        print(f"Unknown backend: {name}")
        print(f"Available: {list(BACKENDS)}")
        return None

    _quiet = quiet
    try:
        return builder(streaming)
    finally:
        _quiet = False


async def resolve_channel(backend, identifier: str):
    """Look up the example channel on a connected backend.

    Most backends resolve a human-readable name. Discord first needs its guild
    selected, and LINE addresses conversations by opaque id only.
    """
    if backend.name == "discord":
        guild_name = get_env("DISCORD_GUILD_NAME")
        guild = await backend.fetch_organization(name=guild_name)
        if not guild:
            print(f"❌ Guild '{guild_name}' not found")
            return None
        backend.config.guild_id = guild.id

    if backend.name in _ID_ADDRESSED:
        return await backend.fetch_channel(id=identifier)
    return await backend.fetch_channel(name=identifier)
