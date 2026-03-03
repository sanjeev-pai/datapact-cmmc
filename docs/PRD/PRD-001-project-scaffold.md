# PRD-001: Project Scaffold

## Overview

Set up the datapact-cmmc repository with a working development environment: FastAPI backend, React frontend, PostgreSQL database, and all tooling (uv, Vite, Alembic, Makefile).

## Goals

- Developers can run `make dev-all` and have backend (8001) + frontend (5174) running
- Health endpoint responds at `/api/health`
- Database connection to PostgreSQL on port 5433
- Alembic migration infrastructure ready
- Frontend renders a shell layout with sidebar navigation
- Test infrastructure passes with basic smoke tests

## Deliverables

### Backend
- `pyproject.toml` — uv project with FastAPI, SQLAlchemy, Alembic, httpx, JWT auth deps
- `docker-compose.yml` — PostgreSQL 16 on port 5433 (db: cmmc, user: cmmc)
- `Makefile` — install, dev-backend, dev-frontend, dev-all, test, build, db-* targets
- `alembic.ini` + `alembic/env.py` — migration infrastructure
- `cmmc/app.py` — FastAPI app with CORS, health endpoint, lifespan
- `cmmc/config.py` — env-var configuration
- `cmmc/database.py` — engine, session, get_db dependency
- `cmmc/models/base.py` — BaseModel (16-char hex UUID, timestamps, creator, row_version)
- `cmmc/errors.py` — shared HTTP exception classes
- Package stubs: `schemas/`, `services/`, `routers/`, `middleware/`, `dependencies/`

### Frontend
- `ui/package.json` — React 19, React Router 7, TailwindCSS 4, DaisyUI 5, Recharts, Vitest
- `ui/vite.config.ts` — Vite + React + Tailwind plugin, API proxy to :8001
- `ui/tsconfig.json` — TypeScript config with `@/` path alias
- `ui/src/App.tsx` — Router shell with placeholder pages (Dashboard, CMMC Library, Assessments)
- `ui/src/components/AppLayout.tsx` — Sidebar + content layout
- `ui/src/index.css` — TailwindCSS + DaisyUI with custom CMMC light/dark themes
- Module directory stubs: auth, dashboard, cmmc, assessments, evidence, findings, poam, datapact, reports, admin

### Data
- `data/cmmc/domains.yaml` — 14 CMMC domains
- `data/cmmc/level1_practices.yaml` — 17 Level 1 practices
- Placeholder files for Level 2, Level 3, and demo assessment

### Testing
- `tests/conftest.py` — SQLite-backed test fixtures
- `tests/test_health.py` — health endpoint smoke test
- `ui/src/App.test.tsx` — basic render test

### Other
- `.gitignore`
- `.claude/CLAUDE.md` — project instructions for Claude Code

## Verification

1. `make db-start` starts PostgreSQL
2. `make dev-all` starts backend on 8001 + frontend on 5174
3. `curl http://localhost:8001/api/health` returns `{"status": "ok"}`
4. Frontend shows sidebar layout with navigation
5. `make test-backend` passes health test
6. `cd ui && npm test` passes render test

## Status

**Complete** — all deliverables created in Phase 1.
