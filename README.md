# FalkorDB-project

## Exit-interview knowledge transfer (`knowledge_transfer/`)

Captures what a departing employee knows, then builds a different handover plan per receiver.
FalkorDB decides which questions to ask (knowledge only the leaver has), what each receiver
gets (leaver's knowledge minus theirs) and in what order (`PREREQUISITE_OF` edges).

    make api                                        # http://localhost:8000/docs
    curl -X POST localhost:8000/api/v1/ingest/seed  # synthetic company (mode A)

Flow: ingest sources and/or a leaver brain dump -> `GET gaps` / `coverage` -> `POST interviews`
and `.../answer` -> `GET handover/{receiver}`. `OPENROUTER_API_KEY` is optional:
without it questions come from templates, and brain-dump extraction and voice are disabled.
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

### Voice interview

A spoken version of the interview over a WebSocket, using Deepgram Nova-3 (speech to text) and
Aura-2 (text to speech) through OpenRouter, so `OPENROUTER_API_KEY` is the only key needed.

    make api   # then open http://localhost:8000/api/v1/voice-demo (use headphones)

`WS /api/v1/interviews/{id}/voice`: send 16 kHz mono PCM16 microphone frames; receive JSON events
(`state`, `transcript`, `saved`, `clear`, `audio_end`, `error`, `ended`) and audio clips (a JSON
`audio` header, then an MP3 frame). Send `{"type": "playback_done", "id": n}` when speech `n`
has finished playing. Voice activity detection runs on the server because the OpenRouter audio
endpoints are request/response, not live streams.

Interruptions:
- Speaking over the agent stops it at once (`clear` tells the browser to drop queued audio); what
  is said becomes the answer, stored with `interrupted: true`.
- Pausing and resuming within a short grace window (`VOICE_GRACE_S`, default 0.8 s) is one answer.
- Speech while an answer is being saved is stored as an addition to it.
- Short commands are recognised: "skip", "repeat that", "hold on", "stop".

Spoken answers are stored in the graph with source `interview-voice`. Optional settings:
`STT_MODEL`, `TTS_MODEL`, `TTS_VOICE`, `VOICE_GRACE_S`.

### Layout

```
knowledge_transfer/
  core/       config.py (every env var + default), errors.py (domain errors), llm.py
  schemas/    sources.py (mode A input), extraction.py (LLM output)
  graph/      store.py: KnowledgeGraph on FalkorDB
  db/         Postgres: base, models, session, repositories (Alembic in migrations/)
  services/   assistant, gaps, handover, ingest, interview (business logic)
  voice/      spoken interviews: VAD, STT/TTS providers, session
  seed/       synthetic demo company
  api/        FastAPI app, deps, error envelope, v1/routes
tests/        unit/ (no I/O), integration/ (embedded FalkorDB + SQLite/Postgres), api/, fakes/
```

Dependencies point downwards: `api` -> `services`/`voice` -> `graph`/`db`/`schemas` -> `core`.
