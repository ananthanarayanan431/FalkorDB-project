.PHONY: help install up down logs ui run migrate revision api test lint fmt web web-install web-check check app

help:
	@echo "make install      install Python dependencies"
	@echo "make up           start FalkorDB and Postgres (docker compose)"
	@echo "make down         stop FalkorDB and Postgres"
	@echo "make logs         follow FalkorDB and Postgres logs"
	@echo "make ui           open the FalkorDB browser UI"
	@echo "make run          start FalkorDB and run the chatbot (sample/main.py)"
	@echo "make migrate      apply database migrations (alembic upgrade head)"
	@echo "make revision m=\"msg\"  autogenerate a migration from model changes"
	@echo "make api          start the stores, migrate, and run the API with reload (port 8000)"
	@echo "make web          run the web UI in development (port 3001)"
	@echo "make test         run the Python tests (embedded FalkorDB, no docker needed)"
	@echo "make lint         check Python style, imports and security rules (ruff)"
	@echo "make fmt          apply ruff's automatic fixes"
	@echo "make web-check    typecheck, lint and build the web UI"
	@echo "make check        everything CI runs: lint, tests, web-check"
	@echo "make app          build and run the whole app from Docker images (port 3001)"

install:
	uv sync

up:
	docker compose up -d --wait

down:
	docker compose --profile app down

logs:
	docker compose logs -f falkordb postgres

ui: up
	open http://localhost:3000

run: up
	uv run python -m sample.main

migrate: up
	uv run alembic upgrade head

revision: up
	uv run alembic revision --autogenerate -m "$(m)"

api: migrate
	uv run uvicorn knowledge_transfer.api:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run ruff check --fix .

web-install:
	cd frontend && npm ci

web:
	cd frontend && npm run dev

web-check:
	cd frontend && npm run typecheck && npm run lint && npm run build

check: lint test web-check

app:
	docker compose --profile app up -d --build --wait
	@echo "UI on http://localhost:3001, API on http://localhost:8000"
