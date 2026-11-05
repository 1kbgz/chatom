"""Checks that every MCP gateway preset can build a working backend.

These presets are plain YAML, so a missing required field is only caught at
connect() time. Verifying the declared fields here keeps a preset from
shipping in a state where ``chatom-mcp +gateway=<name>`` cannot connect.
"""

from pathlib import Path

import pytest
import yaml

PRESET_DIR = Path(__file__).resolve().parent.parent / "mcp" / "config" / "gateway"

# Fields each backend's connect() requires, beyond what the config defaults.
REQUIRED_FIELDS = {
    "discord": {"token"},
    "irc": {"server"},
    "line": {"channel_access_token", "channel_secret"},
    "matrix": {"homeserver", "user_id", "access_token", "device_id"},
    "slack": {"bot_token"},
    "telegram": {"bot_token"},
    "zulip": {"site", "email", "api_key"},
}


def _presets():
    return sorted(path for path in PRESET_DIR.glob("*.yaml"))


def test_every_backend_has_a_preset():
    names = {path.stem for path in _presets()}
    assert REQUIRED_FIELDS.keys() <= names


@pytest.mark.parametrize("path", _presets(), ids=lambda path: path.stem)
def test_preset_declares_required_config_fields(path):
    preset = yaml.safe_load(path.read_text())
    backends = preset["backends"]
    assert len(backends) == 1

    name, entry = next(iter(backends.items()))
    required = REQUIRED_FIELDS.get(name)
    if required is None:
        pytest.skip(f"no required-field expectations for {name}")

    declared = set(entry["config"]) - {"_target_"}
    missing = required - declared
    assert not missing, f"{path.name} omits required config: {sorted(missing)}"
