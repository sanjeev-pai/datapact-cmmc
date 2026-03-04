"""Application configuration via environment variables."""

import os

# ── Server ───────────────────────────────────────────────────────────────────
APP_NAME = "CMMC Tracker"
APP_VERSION = "0.1.0"
HOST = os.environ.get("CMMC_HOST", "127.0.0.1")
PORT = int(os.environ.get("CMMC_PORT", "8081"))

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://sanjeevpai@localhost:5432/datapact",
)
DATABASE_SCHEMA = os.environ.get("DATABASE_SCHEMA", "datapact-cmmc")

# ── Auth ─────────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "cmmc-dev-secret-change-in-prod!!")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", "60"))
JWT_REFRESH_EXPIRY_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRY_DAYS", "7"))

# ── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOW_ORIGINS = os.environ.get(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:9091,http://192.168.1.10:9091,http://mrisan.tplinkdns.com:9091",
).split(",")

# ── DataPact Integration ────────────────────────────────────────────────────
DATAPACT_API_URL = os.environ.get("DATAPACT_API_URL", "http://localhost:8180")
DATAPACT_TIMEOUT = int(os.environ.get("DATAPACT_TIMEOUT", "30"))

# ── Uploads ──────────────────────────────────────────────────────────────────
UPLOAD_DIR = os.environ.get("CMMC_UPLOAD_DIR", "uploads")
MAX_UPLOAD_SIZE = int(os.environ.get("CMMC_MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))  # 50MB

# ── Seed ─────────────────────────────────────────────────────────────────────
AUTO_SEED = os.environ.get("CMMC_AUTO_SEED", "true").lower() == "true"
SEED_DEMO = os.environ.get("CMMC_SEED_DEMO", "true").lower() == "true"
