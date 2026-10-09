.PHONY: help install up down logs ui run migrate revision api test

help:
	@echo "make install  install dependencies"
	@echo "make up       start FalkorDB and Postgres (docker compose)"
	@echo "make down     stop FalkorDB and Postgres"
	@echo "make logs     follow FalkorDB and Postgres logs"
	@echo "make ui       open the FalkorDB browser UI"
	@echo "make run      start FalkorDB and run the chatbot (sample/main.py)"
	@echo "make migrate  apply database migrations (alembic upgrade head)"
	@echo "make revision m=\"msg\"  autogenerate a migration from model changes"
	@echo "make api      start the stores, migrate, and run the knowledge-transfer API (port 8000)"
	@echo "make test     run the tests (embedded FalkorDB, no docker needed)"

install:
	uv sync

up:
	docker compose up -d --wait

down:
	docker compose down

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
