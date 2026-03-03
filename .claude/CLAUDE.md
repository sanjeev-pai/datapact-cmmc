# CMMC Tracker

CMMC 2.0 compliance tracking platform — standalone app integrating with DataPact via REST API.

## Workspace

- **uv** for Python package management
- `uv sync` installs backend dependencies
- `cd ui && npm install` for frontend

## Development

- `make dev-all` — starts backend (port 8001) + frontend (port 5174)
- `make db-start` — starts PostgreSQL on port 5433
- `make db-upgrade` — runs Alembic migrations
- `make db-seed` — seeds CMMC reference data

## Architecture

- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- **Frontend**: Vite + React + TypeScript + TailwindCSS + DaisyUI
- **Integration**: DataPact via REST API (httpx client)

## Testing Policy

- Test-first development — write tests before production code
- Do NOT run tests directly — tell the user which command to run
- Backend: `make test-backend` or `uv run pytest tests/ -v`
- Frontend: `make test-frontend` or `cd ui && npm test`

## Conventions

- BaseModel: 16-char hex UUID id, timestamps, creator, row_version
- Router prefix: `/api/`
- YAML seed files in `data/cmmc/`
