"""Tests for pdf2zh command/env builder."""
from pathlib import Path

from backend.app.pdf2zh_runner import build_command, build_env, classify_error, redact_secrets


def test_build_env_normalizes_base_url():
    env = build_env({"base_url": "https://app.claude.gg", "model": "claude-sonnet-4-6"})
    assert env["OPENAI_BASE_URL"] == "https://app.claude.gg/v1"
    assert env["OPENAI_MODEL"] == "claude-sonnet-4-6"
    assert env["PYTHONUTF8"] == "1"


def test_build_env_keeps_v1():
    env = build_env({"base_url": "https://app.claude.gg/v1", "model": "m"})
    assert env["OPENAI_BASE_URL"] == "https://app.claude.gg/v1"


def test_build_command_includes_prompt_and_langs(tmp_path: Path):
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(b"%PDF")
    out = tmp_path / "output"
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("hello")
    cmd = build_command(pdf, out, prompt, lang_in="en", lang_out="tr", threads=4)
    assert "input.pdf" in " ".join(cmd) or any("input.pdf" in c for c in cmd)
    assert "-li" in cmd and "en" in cmd
    assert "-lo" in cmd and "tr" in cmd
    assert "--prompt" in cmd
    assert any(str(prompt) == c for c in cmd)


def test_build_command_pages_and_cache(tmp_path: Path):
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(b"%PDF")
    out = tmp_path / "out"
    prompt = tmp_path / "p.txt"
    prompt.write_text("x")
    cmd = build_command(pdf, out, prompt, pages="1-2", ignore_cache=True)
    assert "-p" in cmd and "1-2" in cmd
    assert "--ignore-cache" in cmd


def test_classify_error_401():
    assert "401" in classify_error("HTTP 401 Unauthorized")


def test_classify_error_404():
    assert "404" in classify_error("404 Not Found")


def test_redact_secrets():
    text = "key=sk-abc123456789xyz and more"
    out = redact_secrets(text, "sk-abc123456789xyz")
    assert "sk-abc123456789xyz" not in out
    assert "REDACTED" in out
