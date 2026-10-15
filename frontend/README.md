# Knowledge Transfer UI

Web interface for the exit-interview knowledge transfer API in `../knowledge_transfer`.
Next.js 16 (App Router), React 19, TypeScript and Tailwind CSS 4.

## Run it

Start the API first (from the repository root: `make api`, which serves port 8000), then:

    cd frontend
    npm install
    cp .env.example .env.local   # optional; the defaults work locally
    npm run dev                  # http://localhost:3001

Port 3000 is left free for the FalkorDB browser (`make ui`).

The browser only talks to this Next server. Requests to `/api/v1/*`, `/docs` and
`/openapi.json` are proxied to `API_URL`, so the API needs no CORS setup. The voice
interview WebSocket connects to the API directly: `ws(s)://<host>:8000` unless
`NEXT_PUBLIC_VOICE_WS_URL` is set.

## Pages

| Path         | What it does                                                         |
| ------------ | -------------------------------------------------------------------- |
| `/`          | Service status and how much of the leaver's unique knowledge is captured |
| `/import`    | Demo company, JSON source bundle, brain dump (needs a language model) |
| `/gaps`      | Items only the leaver knows about, ranked by risk                    |
| `/interview` | Typed or spoken interview, with the full transcript                  |
| `/handover`  | Preview, save and reopen a plan per receiver                         |
| `/people`    | Add or edit people, set what each person already knows               |
| `/graph`     | The FalkorDB graph drawn as nodes and relationships, with every property; filter by label or type, search, load a node's neighbours. A Table tab lists the same data as text |
| `/settings`  | Clear browser preferences, delete all data (needs `ENABLE_RESET=true` on the API) |
| `/privacy`, `/terms` | Privacy policy and terms                                     |

## Checks

    npm run typecheck
    npm run lint
    npm run build

## Before going live

- Set `NEXT_PUBLIC_OPERATOR_NAME`, `NEXT_PUBLIC_CONTACT_EMAIL` and `NEXT_PUBLIC_POLICY_DATE`
  (they appear on the privacy and terms pages) and have both pages reviewed.
- Serve it on your own domain over HTTPS. The microphone only works on HTTPS or localhost.
- The API has no authentication. Only expose it on a network where everyone may see and
  change the data.
