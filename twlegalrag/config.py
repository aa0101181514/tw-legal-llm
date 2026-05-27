"""Config loading: env vars first, then ~/.twlegalrag/config.toml.

Holds only the TLR endpoint settings (base URL and an optional API key). The
config file lives in the user's home dir, never in the repo, and is git-ignored.
Env vars override the file.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

CONFIG_DIR = Path(os.environ.get("TWLEGALRAG_HOME", Path.home() / ".twlegalrag"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


def _load_file() -> dict:
    if not CONFIG_FILE.exists() or tomllib is None:
        return {}
    try:
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def get_tlr_base_url() -> str:
    env = os.environ.get("TWLEGALRAG_TLR_BASE_URL")
    if env:
        return env
    return _load_file().get("tlr", {}).get("base_url", "https://tlr.dr-lawbot.com")


def get_tlr_api_key() -> str | None:
    env = os.environ.get("TWLEGALRAG_TLR_API_KEY")
    if env:
        return env
    return _load_file().get("tlr", {}).get("api_key")
