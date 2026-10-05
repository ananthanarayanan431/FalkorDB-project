.PHONY: help install up down logs ui run

help:
	@echo "make install  install dependencies"
	@echo "make up       start FalkorDB (docker compose)"
	@echo "make down     stop FalkorDB"
	@echo "make logs     follow FalkorDB logs"
	@echo "make ui       open the FalkorDB browser UI"
	@echo "make run      start FalkorDB and run the chatbot (sample/main.py)"

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
