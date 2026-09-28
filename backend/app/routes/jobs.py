"""Job CRUD and download endpoints."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from .. import job_queue, job_store
from ..config import get_api_key
from ..models import Job, JobStatus

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

MAX_UPLOAD_MB = 80


def _job_to_public(job: Job) -> dict[str, Any]:
    return job.model_dump(mode="json")


@router.post("")
async def create_job(
    file: UploadFile = File(...),
    lang_in: str = Form("en"),
    lang_out: str = Form("tr"),
    pages: str = Form(""),
    threads: int = Form(4),
    model: str = Form(""),
    prompt_override: str = Form(""),
    ignore_cache: bool = Form(False),
) -> dict[str, Any]:
    if not get_api_key():
        raise HTTPException(
            status_code=400,
            detail="API anahtarı ayarlanmamış — önce Ayarlar sekmesinden girin",
        )

    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları destekleniyor")

    options: dict[str, Any] = {
        "lang_in": (lang_in or "en").strip(),
        "lang_out": (lang_out or "tr").strip(),
        "pages": pages.strip() or None,
        "threads": max(1, min(8, threads)),
        "model": model.strip() or None,
        "ignore_cache": bool(ignore_cache),
    }

    job = job_store.create_job(filename, options)
    jdir = job_store.job_dir(job.id)

    # Write prompt override
    if prompt_override.strip():
        (jdir / "prompt.txt").write_text(prompt_override, encoding="utf-8")

    # Stream upload to disk with size cap
    dest = jdir / "input.pdf"
    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_MB * 1024 * 1024:
                    out.close()
                    dest.unlink(missing_ok=True)
                    job_store.delete_job(job.id)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Dosya çok büyük (maks {MAX_UPLOAD_MB} MB)",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        job_store.delete_job(job.id)
        raise HTTPException(status_code=500, detail=f"Yükleme hatası: {e}") from e

    job_queue.enqueue(job.id)
    return _job_to_public(job)


@router.get("")
async def list_jobs() -> list[dict[str, Any]]:
    return [_job_to_public(j) for j in job_store.list_jobs()]


@router.get("/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = job_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    return _job_to_public(job)


@router.get("/{job_id}/download")
async def download(job_id: str) -> FileResponse:
    job = job_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    if job.status != JobStatus.done or not job.output_mono:
        raise HTTPException(status_code=400, detail="İş henüz tamamlanmadı")

    path = job_store.job_dir(job_id) / job.output_mono
    if not path.exists():
        raise HTTPException(status_code=404, detail="Çıktı dosyası bulunamadı")

    # Safe download name
    safe = re.sub(r"[^\w\-. ]+", "_", job.filename)
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"
    download_name = safe.replace(".pdf", "-tr.pdf")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=download_name,
    )


@router.get("/{job_id}/log")
async def get_log(job_id: str) -> PlainTextResponse:
    job = job_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")
    log_path = job_store.job_dir(job_id) / "engine.log"
    if not log_path.exists():
        return PlainTextResponse("")
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    return PlainTextResponse("\n".join(lines[-200:]))


@router.delete("/{job_id}")
async def delete_job(job_id: str) -> dict[str, Any]:
    job = job_store.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="İş bulunamadı")

    if job.status in (JobStatus.queued, JobStatus.running):
        job_queue.request_cancel(job_id)

    job_store.delete_job(job_id)
    return {"ok": True}
