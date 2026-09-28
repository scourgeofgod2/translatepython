"""Paths and settings persistence.

Secrets (API key) live in data/.env. Non-secret prefs live in data/settings.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
ENV_PATH = DATA_DIR / ".env"
SETTINGS_PATH = DATA_DIR / "settings.json"
FRONTEND_DIR = ROOT / "frontend"
PROMPTS_DIR = ROOT / "prompts"
DEFAULT_PROMPT = PROMPTS_DIR / "tr_scientific.txt"

DEFAULT_SETTINGS: dict[str, Any] = {
    "base_url": "https://app.claude.gg/v1",
    "model": "claude-sonnet-4-6",
    "lang_in": "en",
    "lang_out": "tr",
    "service": "openai",
    "threads": 4,
    "prompt_file": "prompts/tr_scientific.txt",
    "job_timeout_minutes": 180,
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    ensure_dirs()
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_PATH.exists():
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                settings.update(raw)
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    ensure_dirs()
    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_env_file() -> dict[str, str]:
    """Parse data/.env into a dict. Lines KEY=VALUE, # comments."""
    result: dict[str, str] = {}
    if not ENV_PATH.exists():
        return result
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def save_env_value(key: str, value: str) -> None:
    ensure_dirs()
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def get_api_key() -> str | None:
    env = load_env_file()
    key = env.get("OPENAI_API_KEY", "").strip()
    if not key or key == "sk-your-key-here":
        return None
    return key


def normalize_base_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        return DEFAULT_SETTINGS["base_url"]
    if not url.endswith("/v1"):
        url = url + "/v1"
    return url


def resolve_prompt_path(settings: dict[str, Any] | None = None) -> Path:
    settings = settings or load_settings()
    rel = settings.get("prompt_file") or str(DEFAULT_PROMPT)
    p = Path(rel)
    if not p.is_absolute():
        p = ROOT / p
    if p.exists():
        return p
    return DEFAULT_PROMPT
