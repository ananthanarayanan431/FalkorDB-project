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
