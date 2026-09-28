"""Pydantic models for jobs and settings."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    canceled = "canceled"


class Job(BaseModel):
    id: str
    created_at: str
    updated_at: str
    filename: str
    status: JobStatus = JobStatus.queued
    stage: str = "queued"
    progress: float = 0.0
    pages_total: int | None = None
    pages_done: int | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    error_detail: str | None = None
    output_mono: str | None = None


class SettingsResponse(BaseModel):
    base_url: str
    model: str
    lang_in: str
    lang_out: str
    service: str
    threads: int
    prompt_file: str
    job_timeout_minutes: int
    api_key_set: bool
    default_prompt: str | None = None


class SettingsUpdate(BaseModel):
    base_url: str | None = None
    model: str | None = None
    lang_in: str | None = None
    lang_out: str | None = None
    service: str | None = None
    threads: int | None = None
    prompt_file: str | None = None
    job_timeout_minutes: int | None = None
    api_key: str | None = None


class JobCreateOptions(BaseModel):
    lang_in: str = "en"
    lang_out: str = "tr"
    pages: str | None = None
    threads: int = 4
    model: str | None = None
    prompt_override: str | None = None
    ignore_cache: bool = False
