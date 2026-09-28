"""Settings and health endpoints."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config
from ..models import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/health")
async def health() -> dict[str, Any]:
    import sys

    return {
        "ok": True,
        "python": sys.version.split()[0],
        "app": "mirapdf",
    }


@router.get("/settings", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    s = config.load_settings()
    prompt_path = config.resolve_prompt_path(s)
    prompt_text = None
    if prompt_path.exists():
        prompt_text = prompt_path.read_text(encoding="utf-8")
    return SettingsResponse(
        base_url=s["base_url"],
        model=s["model"],
        lang_in=s["lang_in"],
        lang_out=s["lang_out"],
        service=s["service"],
        threads=s["threads"],
        prompt_file=s["prompt_file"],
        job_timeout_minutes=s["job_timeout_minutes"],
        hf_endpoint=s["hf_endpoint"],
        api_key_set=config.get_api_key() is not None,
        default_prompt=prompt_text,
    )


@router.put("/settings")
async def put_settings(body: SettingsUpdate) -> dict[str, Any]:
    s = config.load_settings()

    if body.base_url is not None:
        s["base_url"] = config.normalize_base_url(body.base_url)
    if body.model is not None:
        s["model"] = body.model.strip() or s["model"]
    if body.lang_in is not None:
        s["lang_in"] = body.lang_in.strip() or s["lang_in"]
    if body.lang_out is not None:
        s["lang_out"] = body.lang_out.strip() or s["lang_out"]
    if body.service is not None:
        s["service"] = body.service.strip() or s["service"]
    if body.threads is not None:
        s["threads"] = max(1, min(8, body.threads))
    if body.prompt_file is not None:
        s["prompt_file"] = body.prompt_file
    if body.job_timeout_minutes is not None:
        s["job_timeout_minutes"] = max(1, body.job_timeout_minutes)
    if body.hf_endpoint is not None:
        s["hf_endpoint"] = body.hf_endpoint.strip()

    config.save_settings(s)

    if body.api_key is not None and body.api_key.strip():
        config.save_env_value("OPENAI_API_KEY", body.api_key.strip())

    return {
        "ok": True,
        "api_key_set": config.get_api_key() is not None,
        "base_url": s["base_url"],
    }


class TestRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None


@router.post("/settings/test")
async def test_connection(body: TestRequest | None = None) -> dict[str, Any]:
    s = config.load_settings()
    base_url = config.normalize_base_url(
        (body.base_url if body and body.base_url else s.get("base_url") or "")
    )
    api_key = None
    if body and body.api_key and body.api_key.strip():
        api_key = body.api_key.strip()
    else:
        api_key = config.get_api_key()

    if not api_key:
        raise HTTPException(status_code=400, detail="API anahtarı ayarlanmamış")

    url = f"{base_url.rstrip('/')}/models"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {api_key}"}
            )
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"Bağlantı hatası: {e}", "base_url": base_url}

    if resp.status_code == 401:
        return {"ok": False, "error": "API anahtarı reddedildi (401)", "base_url": base_url}
    if resp.status_code == 404:
        return {
            "ok": False,
            "error": "API uç noktası bulunamadı (404) — Base URL /v1 ile bitmeli",
            "base_url": base_url,
        }
    if resp.status_code >= 400:
        return {
            "ok": False,
            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            "base_url": base_url,
        }

    try:
        data = resp.json()
        models = []
        if isinstance(data, dict):
            for m in data.get("data") or []:
                if isinstance(m, dict) and m.get("id"):
                    models.append(m["id"])
        return {"ok": True, "base_url": base_url, "models": models}
    except Exception:
        return {"ok": True, "base_url": base_url, "models": []}
