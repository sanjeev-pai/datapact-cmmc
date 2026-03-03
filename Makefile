APP_MODULE := cmmc.app:app
HOST := 127.0.0.1
PORT := 8081
FRONTEND_DIR := ui

.PHONY: help install dev dev-backend dev-frontend dev-all dev-stop dev-restart test test-backend test-frontend build clean
.PHONY: db-migrate db-upgrade db-seed db-reset

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Install ──────────────────────────────────────────────────────────────────
install:  ## Install backend + frontend dependencies
	uv sync --all-extras
	cd $(FRONTEND_DIR) && npm install

# ── Database (local PostgreSQL, schema: datapact-cmmc) ───────────────────────
db-migrate:  ## Create a new Alembic migration (usage: make db-migrate msg="description")
	uv run alembic revision --autogenerate -m "$(msg)"

db-upgrade:  ## Run pending Alembic migrations
	uv run alembic upgrade head

db-seed:  ## Seed reference data from YAML
	uv run python -m cmmc.services.seed_service

db-reset:  ## Drop and recreate schema (destructive!)
	psql -U sanjeevpai -d datapact -c 'DROP SCHEMA IF EXISTS "datapact-cmmc" CASCADE; CREATE SCHEMA "datapact-cmmc";'
	uv run alembic upgrade head
	$(MAKE) db-seed

# ── Development ──────────────────────────────────────────────────────────────
dev-backend:  ## Run backend with hot-reload
	uv run uvicorn $(APP_MODULE) --reload --host $(HOST) --port $(PORT)

dev-frontend:  ## Run frontend dev server
	cd $(FRONTEND_DIR) && npm run dev

dev-all:  ## Run backend + frontend concurrently
	@echo "Starting backend on port $(PORT) and frontend..."
	$(MAKE) dev-backend &
	$(MAKE) dev-frontend &
	wait

dev-stop:  ## Stop running backend + frontend dev servers
	@./scripts/dev-stop.sh

dev-restart: dev-stop dev-all  ## Restart backend + frontend dev servers

# ── Testing ──────────────────────────────────────────────────────────────────
test: test-backend test-frontend  ## Run all tests

test-backend:  ## Run backend tests
	uv run pytest tests/ -v --tb=short

test-frontend:  ## Run frontend tests
	cd $(FRONTEND_DIR) && npm test

# ── Build ────────────────────────────────────────────────────────────────────
build:  ## Build backend wheel + frontend
	uv build
	cd $(FRONTEND_DIR) && npm run build

clean:  ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info .pytest_cache __pycache__
	cd $(FRONTEND_DIR) && rm -rf dist node_modules/.cache
