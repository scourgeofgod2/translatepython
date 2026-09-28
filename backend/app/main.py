"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import job_queue, job_store
from .config import FRONTEND_DIR, ensure_dirs
from .routes import jobs as jobs_routes
from .routes import settings as settings_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mirapdf")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    recovered = job_store.recover_stale_jobs()
    if recovered:
        logger.warning("Recovered %d stale jobs", recovered)
    await job_queue.start_worker()
    logger.info("mirapdf ready at http://127.0.0.1:8765/")
    yield
    await job_queue.stop_worker()


app = FastAPI(title="mirapdf", version="0.1.0", lifespan=lifespan)

app.include_router(settings_routes.router)
app.include_router(jobs_routes.router)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
