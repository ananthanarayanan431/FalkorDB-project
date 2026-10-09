.PHONY: help install up down logs ui run api test

help:
	@echo "make install  install dependencies"
	@echo "make up       start FalkorDB (docker compose)"
	@echo "make down     stop FalkorDB"
	@echo "make logs     follow FalkorDB logs"
	@echo "make ui       open the FalkorDB browser UI"
	@echo "make run      start FalkorDB and run the chatbot (sample/main.py)"
	@echo "make api      start FalkorDB and the knowledge-transfer API (port 8000)"
	@echo "make test     run the tests (embedded FalkorDB, no docker needed)"

install:
	uv sync

up:
	docker compose up -d --wait

down:
	docker compose down

logs:
	docker compose logs -f falkordb

ui: up
	open http://localhost:3000

run: up
	uv run python -m sample.main

api: up
	uv run uvicorn knowledge_transfer.api:app --reload

test:
	uv run pytest
