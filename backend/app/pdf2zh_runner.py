"""Build and run pdf2zh CLI as a subprocess."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import ROOT, get_api_key, load_settings, normalize_base_url


def find_pdf2zh() -> list[str]:
    """Return the command prefix to invoke pdf2zh."""
    # Prefer the venv binary next to the current Python
    venv_pdf2zh = Path(sys.executable).parent / "pdf2zh.exe"
    if venv_pdf2zh.exists():
        return [str(venv_pdf2zh)]
    venv_pdf2zh_sh = Path(sys.executable).parent / "pdf2zh"
    if venv_pdf2zh_sh.exists():
        return [str(venv_pdf2zh_sh)]
    # Fall back to PATH
    which = shutil.which("pdf2zh")
    if which:
        return [which]
    # Last resort: python -m
    return [sys.executable, "-m", "pdf2zh"]


def build_env(
    settings: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Environment for the pdf2zh subprocess."""
    settings = settings or load_settings()
    overrides = overrides or {}

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # Windows / corporate SSL: truststore + certifi fallback via sitecustomize
    ssl_boot = Path(__file__).resolve().parent / "ssl_boot"
    prev_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ssl_boot) + (os.pathsep + prev_pp if prev_pp else "")
    try:
        import certifi

        ca = certifi.where()
        env.setdefault("SSL_CERT_FILE", ca)
        env.setdefault("REQUESTS_CA_BUNDLE", ca)
        env.setdefault("CURL_CA_BUNDLE", ca)
    except Exception:
        pass

    api_key = get_api_key() or ""
    base_url = normalize_base_url(str(overrides.get("base_url") or settings.get("base_url") or ""))
    model = str(overrides.get("model") or settings.get("model") or "claude-sonnet-4-6")

    env["OPENAI_BASE_URL"] = base_url
    env["OPENAI_API_KEY"] = api_key
    env["OPENAI_MODEL"] = model
    env["OPENAI_MAX_TOKENS"] = "4096"

    return env


def build_command(
    input_pdf: Path,
    output_dir: Path,
    prompt_path: Path,
    lang_in: str = "en",
    lang_out: str = "tr",
    service: str = "openai",
    threads: int = 4,
    pages: str | None = None,
    ignore_cache: bool = False,
) -> list[str]:
    cmd = find_pdf2zh()
    cmd.append(str(input_pdf))
    cmd += ["-li", lang_in, "-lo", lang_out, "-s", service]
    cmd += ["-o", str(output_dir)]
    cmd += ["-t", str(max(1, min(8, threads)))]
    cmd += ["--prompt", str(prompt_path)]
    if pages:
        cmd += ["-p", pages]
    if ignore_cache:
        cmd.append("--ignore-cache")
    return cmd


_ERROR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b401\b|Unauthorized|invalid.?api.?key", re.I), "API anahtarı reddedildi (401)"),
    (re.compile(r"\b404\b|Not Found", re.I), "API uç noktası bulunamadı (404) — Base URL /v1 ile bitmeli"),
    (re.compile(r"\b429\b|Rate.?limit|Too Many Requests", re.I), "Hız sınırı (429) — biraz bekleyip tekrar deneyin"),
    (re.compile(r"\b5\d{2}\b|Internal Server Error|Bad Gateway", re.I), "Sunucu hatası — tekrar deneyin"),
    (re.compile(r"timeout|timed out", re.I), "Zaman aşımı"),
    (
        re.compile(r"CERTIFICATE_VERIFY_FAILED|SSL|certificate verify failed|unable to get local issuer", re.I),
        "SSL sertifika hatası — sistem güven deposu devreye alınmalı",
    ),
    (
        re.compile(r"model.*download|assets\.py|onnx.*None|from_pretrained", re.I),
        "Model/font indirilemedi — ağ hatası",
    ),
]


def classify_error(log_tail: str) -> str:
    for pattern, message in _ERROR_PATTERNS:
        if pattern.search(log_tail):
            return message
    return "Çeviri motoru başarısız — günlüğü kontrol edin"


def redact_secrets(text: str, api_key: str | None = None) -> str:
    if api_key and api_key in text:
        text = text.replace(api_key, "***REDACTED***")
    text = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-***REDACTED***", text)
    return text


def parse_progress(log_text: str) -> tuple[float, str, int | None, int | None]:
    """Best-effort progress parse. Returns (progress, stage, pages_done, pages_total)."""
    stage = "translating"
    progress = 0.0
    pages_done: int | None = None
    pages_total: int | None = None

    lower = log_text.lower()
    if "loading" in lower or "model" in lower and "translat" not in lower[-200:]:
        stage = "loading_model"
    if "writing" in lower or "font" in lower and "subset" in lower:
        stage = "writing_pdf"
    if "finish" in lower or "done" in lower or "complete" in lower:
        stage = "finished"

    # page counters like "1/5" or "page 1 of 5"
    matches = re.findall(r"(\d+)\s*/\s*(\d+)", log_text)
    if matches:
        done, total = matches[-1]
        try:
            pages_done = int(done)
            pages_total = int(total)
            if pages_total > 0:
                progress = min(1.0, pages_done / pages_total)
        except ValueError:
            pass

    return progress, stage, pages_done, pages_total


def find_mono_pdf(output_dir: Path) -> Path | None:
    if not output_dir.exists():
        return None
    monos = sorted(output_dir.glob("*-mono.pdf"))
    if monos:
        return monos[0]
    # fallback: any pdf
    pdfs = sorted(output_dir.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def run_pdf2zh(
    input_pdf: Path,
    output_dir: Path,
    prompt_path: Path,
    log_path: Path,
    *,
    lang_in: str = "en",
    lang_out: str = "tr",
    service: str = "openai",
    threads: int = 4,
    pages: str | None = None,
    ignore_cache: bool = False,
    model: str | None = None,
    timeout_minutes: int = 180,
    cwd: Path | None = None,
    on_progress: Any = None,
) -> tuple[int, Path | None, str | None]:
    """Run pdf2zh. Returns (returncode, mono_pdf_path | None, error_message | None)."""
    settings = load_settings()
    overrides = {"model": model} if model else {}
    env = build_env(settings, overrides)
    cmd = build_command(
        input_pdf,
        output_dir,
        prompt_path,
        lang_in=lang_in,
        lang_out=lang_out,
        service=service,
        threads=threads,
        pages=pages,
        ignore_cache=ignore_cache,
    )

    api_key = env.get("OPENAI_API_KEY") or None
    timeout_s = max(1, timeout_minutes) * 60

    log_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(log_path, "ab") as log_f:
        header = f"$ {' '.join(cmd)}\n".encode("utf-8", errors="replace")
        log_f.write(header)
        log_f.flush()
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd or input_pdf.parent),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
        except OSError as e:
            msg = f"pdf2zh başlatılamadı: {e}"
            log_f.write(msg.encode("utf-8") + b"\n")
            return -1, None, msg

        assert proc.stdout is not None
        try:
            for raw in proc.stdout:
                safe = redact_secrets(raw.decode("utf-8", errors="replace"), api_key)
                log_f.write(safe.encode("utf-8", errors="replace"))
                log_f.flush()
                if on_progress:
                    try:
                        on_progress(log_path)
                    except Exception:
                        pass
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            log_f.write(b"\nTIMEOUT\n")
            return -1, None, f"Zaman aşımı ({timeout_minutes} dk)"
        except Exception as e:
            proc.kill()
            proc.wait()
            msg = f"Motor hatası: {e}"
            log_f.write(msg.encode("utf-8") + b"\n")
            return -1, None, msg

    rc = proc.returncode or 0
    mono = find_mono_pdf(output_dir)

    if rc != 0 or mono is None:
        tail = ""
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
            tail = "\n".join(text.splitlines()[-50:])
        except OSError:
            pass
        error = classify_error(tail)
        return rc, mono, error

    return rc, mono, None
