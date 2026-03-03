"""Application configuration via environment variables."""

import os

# ── Server ───────────────────────────────────────────────────────────────────
APP_NAME = "CMMC Tracker"
APP_VERSION = "0.1.0"
PORT = int(os.environ.get("CMMC_PORT", "8001"))

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://cmmc:cmmc@localhost:5433/cmmc",
)

# ── Auth ─────────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "cmmc-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", "60"))
JWT_REFRESH_EXPIRY_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRY_DAYS", "7"))

# ── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOW_ORIGINS = os.environ.get(
    "CORS_ALLOW_ORIGINS", "http://localhost:5174"
).split(",")

# ── DataPact Integration ────────────────────────────────────────────────────
DATAPACT_API_URL = os.environ.get("DATAPACT_API_URL", "http://localhost:8000")
DATAPACT_TIMEOUT = int(os.environ.get("DATAPACT_TIMEOUT", "30"))

# ── Seed ─────────────────────────────────────────────────────────────────────
AUTO_SEED = os.environ.get("CMMC_AUTO_SEED", "true").lower() == "true"
