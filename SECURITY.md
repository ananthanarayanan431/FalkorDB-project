# Security

## Reporting a vulnerability

Please do not open a public issue. Email the maintainer (see the repository owner's
GitHub profile) with a description, the affected version or commit, and steps to
reproduce. You will get an answer within five working days.

## Threat model

The service stores what a departing employee knows: names, roles, work history and their
own words from interviews. It is built to run **inside an organisation's network**, behind
a reverse proxy that terminates TLS.

**The API has no authentication.** Anyone who can reach it can read and change all data.
Authentication was removed on purpose (see the git history); put the service behind a
network boundary, a VPN, or an authenticating proxy (for example an SSO gateway) before
exposing it to anyone who should not have full access.

## Safeguards in the code

| Risk | Safeguard | Where |
| --- | --- | --- |
| Cypher injection | All values are query parameters. Labels and relationship types (which Cypher cannot parameterise) come only from fixed allowlists, checked with real exceptions rather than `assert` | `graph/store.py` |
| Oversized requests | Body limit (`MAX_REQUEST_BYTES`, default 5 MiB) checked on `Content-Length` and while streaming; per-field length limits on every string and list | `api/middleware.py`, `schemas/` |
| Cross-site WebSocket hijacking | The voice socket checks `Origin` against `ALLOWED_ORIGINS` before accepting; audio and control frames have size caps | `api/v1/routes/voice.py` |
| Host header attacks | `ALLOWED_HOSTS` enables Starlette's TrustedHostMiddleware | `api/app.py` |
| Information leakage | Unhandled errors return a generic message; provider and LLM errors are logged, not sent to clients; `/docs` and the voice demo are off in production | `api/errors.py`, `services/assistant.py`, `voice/session.py` |
| Browser attacks on the UI | Content-Security-Policy, `frame-ancestors 'none'`, `nosniff`, a strict referrer policy, and a Permissions-Policy that allows the microphone for this site only. React escapes all rendered data; no HTML from data is ever injected | `frontend/next.config.ts` |
| Caching of personal data | API responses carry `Cache-Control: no-store` | `api/middleware.py` |
| Destructive reset | `POST /reset` returns 404 unless `ENABLE_RESET=true` | `api/v1/routes/reset.py` |
| Containers | Images run as a non-root user, with pinned base images and a lockfile install | `Dockerfile`, `frontend/Dockerfile` |

## Production checklist

- [ ] Run behind a reverse proxy with TLS. Set `HTTPS_ONLY=true` when building the UI image (adds HSTS).
- [ ] `APP_ENV=production` on the API.
- [ ] `ALLOWED_HOSTS` and `ALLOWED_ORIGINS` set to your real host names and UI origin.
- [ ] `NEXT_PUBLIC_VOICE_WS_URL` set to the `wss://` address of the API when building the UI.
- [ ] Uvicorn's `--forwarded-allow-ips` (env `FORWARDED_ALLOW_IPS`) set to the proxy's address only.
- [ ] Real Postgres credentials (not `kt:kt`), from a secret store, not committed files.
- [ ] FalkorDB and Postgres reachable only from the API, never from the internet.
- [ ] A body size limit and rate limits at the proxy, especially for the endpoints that call the
      language model (`/ingest/braindump`, `/interviews`, `/interviews/{id}/answer`, `/handover*`) and
      for the voice WebSocket. The app enforces size limits but not request rates.
- [ ] `ENABLE_RESET` left off.
- [ ] Backups for both stores.
- [ ] The privacy policy and terms filled in (`NEXT_PUBLIC_OPERATOR_NAME`, `NEXT_PUBLIC_CONTACT_EMAIL`,
      `NEXT_PUBLIC_POLICY_DATE`) and reviewed.

## Dependency scanning

CI runs `pip-audit` on the locked Python runtime dependencies and `npm audit --omit=dev` on
the UI's runtime dependencies, plus ruff's bandit (`S`) security rules on every push.

Known and accepted: `braces` (CVE-2026-93687, stack exhaustion on deeply nested patterns)
has no fixed release yet. It is only pulled in by ESLint's file matching, a development tool
that runs on this repository's own files, and is not part of the built application.
