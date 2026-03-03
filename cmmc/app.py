"""CMMC Tracker — FastAPI application."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cmmc import config

# ── Ensure models are registered with Base.metadata ─────────────────────────
import cmmc.models  # noqa: F401


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Startup / shutdown lifecycle."""
    _startup()
    yield
    _cleanup()


def _startup() -> None:
    """Run on application startup."""
    from cmmc.database import engine
    from cmmc.models.base import Base

    # Create tables for non-PostgreSQL backends (dev/test convenience)
    db_url = str(engine.url)
    if not db_url.startswith("postgresql"):
        Base.metadata.create_all(bind=engine)


def _cleanup() -> None:
    """Run on application shutdown."""
    pass


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="CMMC 2.0 compliance tracking and assessment platform",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "product": "cmmc-tracker",
        "version": config.APP_VERSION,
    }
