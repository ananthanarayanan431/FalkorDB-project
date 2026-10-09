# FalkorDB-project

## Exit-interview knowledge transfer (`knowledge_transfer/`)

Captures what a departing employee knows, then builds a different handover plan per receiver.
FalkorDB decides which questions to ask (knowledge only the leaver has), what each receiver
gets (leaver's knowledge minus theirs) and in what order (`PREREQUISITE_OF` edges).

    make api                                        # http://localhost:8000/docs
    curl -X POST localhost:8000/api/v1/ingest/seed  # synthetic company (mode A)

Flow: ingest sources and/or a leaver brain dump -> `GET gaps` / `coverage` -> `POST interviews`
and `.../answer` -> `GET handover/{receiver}`. LLM keys (`OPENROUTER_API_KEY` or `OPENAI_API_KEY`)
are optional: without them questions come from templates and brain-dump extraction is disabled.
Tests run against an embedded FalkorDB: `make test`.

Every response is `{"success": true, "message", "data"}` or
`{"success": false, "message", "error": {"code", "details"}}`.
`POST /api/v1/reset` wipes the graph and stored results. The API has no authentication.

### Storage

- **FalkorDB**: the knowledge graph (people, items, documents, interview answers).
- **Postgres** (`knowledge_transfer/db/`, SQLAlchemy async + asyncpg): interview sessions and their
  turn-by-turn transcripts (`GET /interviews/{id}`), and saved handover plans
  (`POST/GET /handover-plans`). `GET /handover/{receiver}` previews a plan without saving it.

`DATABASE_URL` defaults to the compose database
(`postgresql+asyncpg://kt:kt@localhost:5432/knowledge_transfer`). Schema changes go through Alembic:
edit `knowledge_transfer/db/models.py`, run `make revision m="what changed"`, review the file in
`migrations/versions/`, then `make migrate`. Tests use SQLite unless `TEST_DATABASE_URL` points at a
Postgres database (its tables are dropped and recreated).
