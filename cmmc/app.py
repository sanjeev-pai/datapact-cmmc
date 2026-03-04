"""CMMC Tracker — FastAPI application."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cmmc import config

logger = logging.getLogger(__name__)

# ── Ensure models are registered with Base.metadata ─────────────────────────
import cmmc.models  # noqa: F401, E402


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
            seed_all(db, seed_demo=config.SEED_DEMO)
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
from cmmc.routers.dashboard import router as dashboard_router  # noqa: E402
from cmmc.routers.datapact import router as datapact_router  # noqa: E402
from cmmc.routers.evidence import router as evidence_router  # noqa: E402
from cmmc.routers.findings import router as findings_router  # noqa: E402
from cmmc.routers.organizations import router as org_router  # noqa: E402
from cmmc.routers.poams import router as poams_router  # noqa: E402
from cmmc.routers.reports import router as reports_router  # noqa: E402
from cmmc.routers.users import router as users_router  # noqa: E402

app.include_router(assessment_practices_router)
app.include_router(assessments_router)
app.include_router(auth_router)
app.include_router(cmmc_router)
app.include_router(dashboard_router)
app.include_router(datapact_router)
app.include_router(evidence_router)
app.include_router(findings_router)
app.include_router(org_router)
app.include_router(poams_router)
app.include_router(reports_router)
app.include_router(users_router)

# ── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Exception handlers ──────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 with consistent error format for validation errors."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = " -> ".join(str(loc) for loc in first.get("loc", []))
    msg = first.get("msg", "Validation error")
    detail = f"{field}: {msg}" if field else msg
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "error_code": "VALIDATION_ERROR", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled exceptions — return 500 with safe message."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred.",
            "error_code": "INTERNAL_ERROR",
        },
    )


# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "product": "cmmc-tracker",
        "version": config.APP_VERSION,
    }
