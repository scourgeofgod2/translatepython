"""Tests for job store."""
from backend.app import job_store
from backend.app.models import JobStatus


def test_create_and_load_job(tmp_path, monkeypatch):
    monkeypatch.setattr(job_store, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(job_store, "ensure_dirs", lambda: (tmp_path / "jobs").mkdir(parents=True, exist_ok=True))

    job = job_store.create_job("test.pdf", {"lang_in": "en", "lang_out": "tr"})
    assert job.filename == "test.pdf"
    assert job.status == JobStatus.queued

    loaded = job_store.load_job(job.id)
    assert loaded is not None
    assert loaded.id == job.id
    assert loaded.options["lang_out"] == "tr"


def test_update_job(tmp_path, monkeypatch):
    monkeypatch.setattr(job_store, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(job_store, "ensure_dirs", lambda: (tmp_path / "jobs").mkdir(parents=True, exist_ok=True))

    job = job_store.create_job("a.pdf", {})
    updated = job_store.update_job(job.id, status=JobStatus.done, progress=1.0)
    assert updated is not None
    assert updated.status == JobStatus.done
    assert updated.progress == 1.0


def test_recover_stale_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(job_store, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(job_store, "ensure_dirs", lambda: (tmp_path / "jobs").mkdir(parents=True, exist_ok=True))

    job_store.create_job("stale.pdf", {})
    n = job_store.recover_stale_jobs()
    assert n == 1
    jobs = job_store.list_jobs()
    assert all(j.status == JobStatus.failed for j in jobs)
