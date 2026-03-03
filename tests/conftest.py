"""Shared test fixtures."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from cmmc.app import app  # noqa: E402
from cmmc.database import get_db  # noqa: E402
from cmmc.models.base import Base  # noqa: E402

_test_engine = create_engine(
    "sqlite:///./test.db", connect_args={"check_same_thread": False}
)
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
