"""Shared test fixtures."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Use SQLite for tests, disable auto-seed
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["CMMC_AUTO_SEED"] = "false"

from cmmc.app import app  # noqa: E402
from cmmc.database import get_db  # noqa: E402
from cmmc.models import Base  # noqa: E402

_test_engine = create_engine(
    "sqlite:///./test.db", connect_args={"check_same_thread": False}
)

# Make PostgreSQL JSON columns work on SQLite by compiling them as TEXT
from sqlalchemy.dialects.postgresql import JSON as PG_JSON  # noqa: E402


@event.listens_for(_test_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable FK enforcement in SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(PG_JSON, "sqlite")
def _compile_json_sqlite(type_, compiler, **kw):
    return "TEXT"


TestSession = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
