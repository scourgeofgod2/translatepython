"""JSON-file job store under data/jobs/<id>/job.json."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import JOBS_DIR, ensure_dirs
from .models import Job, JobStatus


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def create_job(filename: str, options: dict[str, Any]) -> Job:
    ensure_dirs()
    import uuid

    job_id = uuid.uuid4().hex
    now = _now()
    job = Job(
        id=job_id,
        created_at=now,
        updated_at=now,
        filename=filename,
        options=options,
    )
    d = job_dir(job_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "output").mkdir(exist_ok=True)
    save_job(job)
    return job


def save_job(job: Job) -> None:
    d = job_dir(job.id)
    d.mkdir(parents=True, exist_ok=True)
    job.updated_at = _now()
    (d / "job.json").write_text(
        job.model_dump_json(indent=2), encoding="utf-8"
    )


def load_job(job_id: str) -> Job | None:
    path = job_dir(job_id) / "job.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Job.model_validate(data)
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def list_jobs() -> list[Job]:
    ensure_dirs()
    jobs: list[Job] = []
    if not JOBS_DIR.exists():
        return jobs
    for d in sorted(JOBS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        job = load_job(d.name)
        if job:
            jobs.append(job)
    return jobs


def update_job(job_id: str, **fields: Any) -> Job | None:
    job = load_job(job_id)
    if not job:
        return None
    for k, v in fields.items():
        if hasattr(job, k):
            setattr(job, k, v)
    save_job(job)
    return job


def delete_job(job_id: str) -> bool:
    import shutil

    d = job_dir(job_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


def recover_stale_jobs() -> int:
    """Mark any 'running' jobs as failed after a crash/restart."""
    count = 0
    for job in list_jobs():
        if job.status in (JobStatus.running, JobStatus.queued):
            job.status = JobStatus.failed
            job.error = "Uygulama yeniden başlatıldı — iş yarım kaldı"
            save_job(job)
            count += 1
    return count
