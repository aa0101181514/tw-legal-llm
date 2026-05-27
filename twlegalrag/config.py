"""Config loading: env vars first, then ~/.twlegalrag/config.toml.

The config file holds the user's OWN LLM API key. It lives in the user's home
dir, never in the repo, and is git-ignored. Env vars override the file so CI /
one-off runs can avoid writing keys to disk.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

from .llm import LLMConfig

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


def load_llm_config() -> LLMConfig:
    """LLMConfig from env (preferred) merged over the config file."""
    cfg = LLMConfig.from_env()
    data = _load_file().get("llm", {})
    # Env wins; only fill gaps from file.
    if not cfg.api_key and data.get("api_key"):
        cfg.api_key = data["api_key"]
    if not os.environ.get("TWLEGALRAG_LLM_PROVIDER") and data.get("provider"):
        cfg.provider = data["provider"]
    if not os.environ.get("TWLEGALRAG_LLM_MODEL") and data.get("model"):
        cfg.model = data["model"]
    if not os.environ.get("TWLEGALRAG_LLM_BASE_URL") and data.get("base_url"):
        cfg.base_url = data["base_url"]
    return cfg


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
