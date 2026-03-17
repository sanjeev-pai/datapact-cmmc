# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CMMC 2.0 compliance tracking platform — standalone app integrating with DataPact via REST API.

## Commands

### Setup
- `make install` — install backend (uv) + frontend (npm) dependencies
- `make db-upgrade` — run Alembic migrations
- `make db-seed` — seed CMMC reference data from YAML

### Development
- `make dev-all` — backend (port 8081) + frontend (port 9091) concurrently
- `make dev-backend` — uvicorn with hot-reload on port 8081
- `make dev-frontend` — Vite dev server on port 9091 (bound to 0.0.0.0)

### Testing
- `make test` — run all tests (backend + frontend)
- `make test-backend` — `uv run pytest tests/ -v --tb=short`
- `make test-frontend` — `cd ui && npm test`
- Single backend test: `uv run pytest tests/test_health.py -v`
- Single frontend test: `cd ui && npx vitest run src/App.test.tsx`

### Database
- `make db-migrate msg="description"` — create new Alembic migration
- `make db-reset` — drop and recreate schema, migrate, seed (destructive)

### Build & Lint
- `make build` — uv wheel + Vite bundle
- `uv run ruff check cmmc/` — lint backend
- `cd ui && npm run lint` — lint frontend

## Architecture

### Backend (`cmmc/`)
FastAPI + SQLAlchemy + Alembic + PostgreSQL (psycopg3)

- `app.py` — FastAPI app, CORS middleware, lifespan, health endpoint
- `config.py` — env-var-based settings (DATABASE_URL, JWT_*, CORS, DataPact)
- `database.py` — engine, SessionLocal factory, `get_db()` dependency
- `errors.py` — custom exceptions: NotFoundError(404), ConflictError(409), ForbiddenError(403), UnauthorizedError(401)
- `models/base.py` — BaseModel with mixins (TimestampMixin, CreatorMixin, VersionMixin)
- `routers/` — API route handlers, prefix `/api/`
- `schemas/` — Pydantic request/response models
- `services/` — business logic, seed_service
- `dependencies/` — reusable FastAPI Depends functions

### Frontend (`ui/`)
Vite + React 19 + TypeScript + TailwindCSS + DaisyUI

- `src/App.tsx` — BrowserRouter, routes nested under AppLayout
- `src/components/` — shared UI components (AppLayout with sidebar)
- `src/modules/` — feature modules: admin, assessments, auth, cmmc, dashboard, datapact, evidence, findings, poam, reports
- `src/services/` — API client layer
- `src/contexts/` — React context providers
- `src/hooks/` — custom hooks
- `src/types/` — shared TypeScript types

### DataPact Integration (Deep Delegation)
- DataPact is the source of truth for tenants (organizations), contracts, and compliance scoring
- CMMC stores only CMMC-specific data locally (practices, assessments, evidence, findings)
- `datapact_client.py` — full HTTP client: GET/POST/PUT/DELETE for contracts, tenants, compliance, certifications, audit
- `org_sync_service.py` — bidirectional org↔tenant sync (create, update, link)
- `sync_service.py` — syncs assessment practices with DataPact compliance + scoring APIs
- Organization model has `datapact_tenant_id` linking to DataPact tenant
- Response normalization: DataPact `results` → CMMC `items`
- Per-org DataPact credentials: `datapact_api_url`, `datapact_api_key` on Organization

### Frontend Integration
- Frontend proxies `/api/*` to backend via Vite dev server config

## Conventions

### Backend
- All models extend `BaseModel`: 16-char hex UUID `id`, `created_at`/`updated_at` (UTC), `creator_id`, `row_version` (optimistic locking, auto-incremented on flush)
- Router prefix: `/api/`
- DB dependency injection: `db: Session = Depends(get_db)`
- Tests use SQLite in-memory via conftest.py fixtures (`setup_db`, `db`, `client`)

### Frontend
- Path alias: `@/` maps to `src/`
- Styling: TailwindCSS + DaisyUI with custom `cmmc` theme (light) and `cmmc-dark` theme
- Testing: Vitest + @testing-library/react, setup in `src/test/setup.ts`
- TypeScript strict mode enabled

### Seed Data
- YAML files in `data/cmmc/` (domains, level1/2/3 practices, demo assessment)
- Seed service uses natural keys (domain_id, practice_id) for idempotent upserts
- Auto-seeds on startup when `CMMC_AUTO_SEED=true` (default)

## Testing Policy
- Test-first development — write tests before production code
- Do NOT run tests directly — tell the user which command to run

## Environment Variables
Key config in `cmmc/config.py`:
- `DATABASE_URL` — default: `postgresql+psycopg://sanjeevpai@localhost:5432/datapact`
- `DATABASE_SCHEMA` — default: `datapact-cmmc`
- `CMMC_PORT` — default: 8081
- `CMMC_AUTO_SEED` — default: true
- `DATAPACT_API_URL` — default: `http://localhost:8180`
- `JWT_SECRET` — must change in production

## Database
- Local PostgreSQL 14 on port 5432 (Homebrew)
- Database: `datapact`, Schema: `datapact-cmmc`
- All tables live in the `datapact-cmmc` schema (set via Base metadata + search_path)

## Documentation
- PRDs in `docs/PRD/`, plans in `docs/plans/`
- Templates in `docs/templates/` — use for new PRDs, plans, work items

## Git Workflow
- Direct pushes to `main` do not need a PR
- Feature branches and PRs are optional — use when collaboration or review is needed
- Check if user has admin rights and use admin to merge PRs when used

## TODOs
TODOs and work policy live in **MEMORY.md** (auto-loaded every session) under the "CMMC TODOs" section. Do not store TODOs here — manage them in MEMORY.md so they are always in context.
