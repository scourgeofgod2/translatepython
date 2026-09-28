"""Single-worker asyncio job queue."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from . import job_store
from .config import resolve_prompt_path
from .models import JobStatus
from .pdf2zh_runner import parse_progress, run_pdf2zh

logger = logging.getLogger("mirapdf.queue")

_queue: asyncio.Queue[str] | None = None
_worker_task: asyncio.Task | None = None
_current_job_id: str | None = None
_cancel_requested: set[str] = set()


def get_queue() -> asyncio.Queue[str]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def start_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_worker_loop())
    logger.info("Job worker started")


async def stop_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    _worker_task = None


def enqueue(job_id: str) -> None:
    q = get_queue()
    q.put_nowait(job_id)


def request_cancel(job_id: str) -> None:
    _cancel_requested.add(job_id)


def is_canceled(job_id: str) -> bool:
    return job_id in _cancel_requested


async def _worker_loop() -> None:
    q = get_queue()
    while True:
        job_id = await q.get()
        try:
            if is_canceled(job_id):
                job_store.update_job(
                    job_id,
                    status=JobStatus.canceled,
                    stage="canceled",
                    error="İptal edildi",
                )
                continue
            await _run_job(job_id)
        except Exception as e:
            logger.exception("Job %s crashed", job_id)
            job_store.update_job(
                job_id,
                status=JobStatus.failed,
                error=f"İş beklenmeyen hata: {e}",
            )
        finally:
            q.task_done()


async def _run_job(job_id: str) -> None:
    global _current_job_id
    job = job_store.load_job(job_id)
    if not job:
        return

    job_dir = job_store.job_dir(job_id)
    input_pdf = job_dir / "input.pdf"
    output_dir = job_dir / "output"
    log_path = job_dir / "engine.log"
    prompt_path = job_dir / "prompt.txt"

    if not input_pdf.exists():
        job_store.update_job(
            job_id, status=JobStatus.failed, error="Girdi PDF bulunamadı"
        )
        return

    if not prompt_path.exists():
        default = resolve_prompt_path()
        prompt_path.write_text(default.read_text(encoding="utf-8"), encoding="utf-8")

    opts = job.options or {}
    _current_job_id = job_id
    job_store.update_job(
        job_id,
        status=JobStatus.running,
        stage="loading_model",
        progress=0.0,
        error=None,
        error_detail=None,
    )

    def on_progress(log_file: Path) -> None:
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
            progress, stage, pages_done, pages_total = parse_progress(text)
            job_store.update_job(
                job_id,
                stage=stage,
                progress=progress,
                pages_done=pages_done,
                pages_total=pages_total,
            )
        except Exception:
            pass

    # Run blocking subprocess in a thread
    timeout_min = int(opts.get("timeout_minutes") or 180)
    rc, mono, error = await asyncio.to_thread(
        run_pdf2zh,
        input_pdf,
        output_dir,
        prompt_path,
        log_path,
        lang_in=str(opts.get("lang_in") or "en"),
        lang_out=str(opts.get("lang_out") or "tr"),
        service=str(opts.get("service") or "openai"),
        threads=int(opts.get("threads") or 4),
        pages=opts.get("pages") or None,
        ignore_cache=bool(opts.get("ignore_cache")),
        model=opts.get("model") or None,
        timeout_minutes=timeout_min,
        cwd=job_dir,
        on_progress=on_progress,
    )

    _current_job_id = None

    if is_canceled(job_id):
        job_store.update_job(
            job_id, status=JobStatus.canceled, stage="canceled", error="İptal edildi"
        )
        _cancel_requested.discard(job_id)
        return

    if error or mono is None:
        detail = None
        try:
            if log_path.exists():
                detail = "\n".join(
                    log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-50:]
                )
        except OSError:
            pass
        job_store.update_job(
            job_id,
            status=JobStatus.failed,
            stage="failed",
            error=error or "Çeviri başarısız",
            error_detail=detail,
        )
        return

    job_store.update_job(
        job_id,
        status=JobStatus.done,
        stage="finished",
        progress=1.0,
        output_mono=f"output/{mono.name}",
        error=None,
        error_detail=None,
    )
