"""CLI entry point for chatom-mcp.

Uses Hydra's Compose API for config composition (no cwd change, no
outputs directory, no logging takeover — safe for MCP stdio).

Gateway presets live in ``config/gateway/`` and are selected via the
``+gateway=<name>`` override.

Usage::

    chatom-mcp +gateway=slack
    chatom-mcp +gateway=discord server.transport=http server.port=9090
"""

from __future__ import annotations

import os
import sys
from typing import Any, cast

from hydra import compose, initialize_config_module
from hydra.utils import instantiate

from chatom.mcp.server import build_mcp_server


def main() -> None:
    """CLI entry point — compose config via Hydra, start MCP server."""
    overrides = sys.argv[1:]

    with initialize_config_module(config_module="chatom.mcp.config", version_base=None):
        cfg = compose(config_name="config", overrides=overrides)

    backends: dict = {}
    for name, bcfg in cfg.backends.items():
        backends[name] = instantiate(bcfg, _convert_="all")

    if not backends:
        raise SystemExit("error: no backends configured — use +gateway=<name>")

    mcp = build_mcp_server(backends, read_only=cfg.server.read_only)

    transport: str = cfg.server.transport
    if cfg.server.auth_token_env and transport != "stdio":
        auth_token = os.environ.get(cfg.server.auth_token_env, "")
        if auth_token:
            from fastmcp.server.auth import StaticTokenVerifier

            cast(Any, mcp)._auth = StaticTokenVerifier(tokens={auth_token: {"client_id": "chatom-mcp", "scopes": []}})

    kwargs: dict[str, Any] = {}
    if transport in ("http", "sse"):
        kwargs["host"] = cfg.server.host
        kwargs["port"] = cfg.server.port

    mcp.run(transport=transport, **kwargs)


if __name__ == "__main__":
    main()
