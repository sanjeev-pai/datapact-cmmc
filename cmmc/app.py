"""CMMC Tracker — FastAPI application."""

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
    from cmmc.database import SessionLocal, engine
    from cmmc.models.base import Base

    # Create tables for non-PostgreSQL backends (dev/test convenience)
    db_url = str(engine.url)
    if not db_url.startswith("postgresql"):
        Base.metadata.create_all(bind=engine)

    # Auto-seed reference data
    if config.AUTO_SEED:
        from cmmc.services.seed_service import seed_all

        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()


def _cleanup() -> None:
    """Run on application shutdown."""
    pass


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="CMMC 2.0 compliance tracking and assessment platform",
    lifespan=lifespan,
    redirect_slashes=False,
)

# ── Routers ─────────────────────────────────────────────────────────────────
from cmmc.routers.assessment_practices import router as assessment_practices_router  # noqa: E402
from cmmc.routers.assessments import router as assessments_router  # noqa: E402
from cmmc.routers.auth import router as auth_router  # noqa: E402
from cmmc.routers.cmmc import router as cmmc_router  # noqa: E402
from cmmc.routers.evidence import router as evidence_router  # noqa: E402
from cmmc.routers.organizations import router as org_router  # noqa: E402
from cmmc.routers.users import router as users_router  # noqa: E402

app.include_router(assessment_practices_router)
app.include_router(assessments_router)
app.include_router(auth_router)
app.include_router(cmmc_router)
app.include_router(evidence_router)
app.include_router(org_router)
app.include_router(users_router)

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
