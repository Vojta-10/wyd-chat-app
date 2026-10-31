# wyd-backend

FastAPI backend for **WYD**, a live chat and social app (accounts, posts and likes, 1:1 and group chats, image sharing).

This is a learning and portfolio project, built milestone by milestone with a strong focus on security. Every milestone ends deployed and tagged.

**Live:** https://wyd-chat-app.onrender.com · [Swagger UI (`/docs`)](https://wyd-chat-app.onrender.com/docs)

> Hosted on Render's free tier: after ~15 minutes of inactivity the service spins down, so the first request can take up to a minute.

## Status: M0, walking skeleton (`v0.0.1`)

The goal of M0 is a trivial app that is fully wired end to end: config → database → HTTP → deployment.

| Endpoint | What it does |
|---|---|
| `GET /` | Hello world |
| `GET /health` | Runs `SELECT 1` against Postgres; returns `{"message": "DB connection OK"}` |
| `GET /docs` | Interactive API docs (intentionally public until the frontend exists) |

Next up: **M1, accounts** (register/login, Argon2id passwords, JWT in an httpOnly cookie, profiles).

## Stack

- **Python 3.14**, managed with [uv](https://docs.astral.sh/uv/)
- **FastAPI** (ASGI, served by uvicorn via the FastAPI CLI)
- **SQLAlchemy 2.1** (async) + **asyncpg**
- **PostgreSQL on Neon** (serverless, scales to zero)
- **pydantic-settings** for 12-factor configuration
- **Render** for hosting

## Project structure

```
wyd-backend/
├── app/
│   ├── main.py            # FastAPI app, lifespan, CORS middleware, routes
│   ├── dependencies.py    # get_db_session (per-request session), typed Annotated deps
│   ├── core/
│   │   └── config.py      # Settings (pydantic-settings, SecretStr), cached get_settings()
│   └── db/
│       └── engine.py      # async engine + session factory, startup connectivity check
├── example.env            # every setting with dummy values (committed)
├── .env                   # real values (gitignored, never committed)
├── pyproject.toml
└── uv.lock
```

The layered layout (`routes → services → repositories → models`) arrives with the first real feature in M1.

## Running locally

Prerequisites: Python 3.14, uv, and a Neon project with a **`dev` branch** (local development never touches the production branch).

```bash
cd wyd-backend
uv sync                      # install exact versions from uv.lock
cp example.env .env          # then fill in real values (see below)
uv run fastapi dev           # dev server with auto-reload on http://127.0.0.1:8000
```

The entrypoint (`app.main:app`) is configured in `pyproject.toml` under `[tool.fastapi]`.

### Configuration

All settings come from environment variables (or `.env` locally). Missing or invalid values make the app **fail at startup** instead of misbehaving later.

| Variable | Example | Purpose |
|---|---|---|
| `DATABASE_URL_POOLING` | `postgresql+asyncpg://user:pass@ep-xxx-pooler.region.aws.neon.tech/db` | Neon **pooled** connection string, used by the app |
| `DATABASE_URL_NO_POOLING` | `postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/db` | Neon **direct** connection string, reserved for Alembic migrations (M1) |
| `ENVIRONMENT` | `dev` or `prod` | Required, no default. `dev` enables SQL echo logging |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | JSON list of allowed browser origins (the frontend), never `*` |

Do not put `?sslmode=...` in the URLs: asyncpg doesn't understand libpq query parameters. TLS is configured in code (see below).

## Design notes

- **Engine lifecycle in the lifespan.** The engine and session factory are created when the app starts and disposed when it shuts down (closing pooled connections cleanly). They live on `app.state`, owned by the app instance rather than a module global, and requests reach them through the `get_db_session` dependency.
- **Fail fast.** On startup the app opens a connection and runs `SELECT 1`. A wrong URL or password crashes the boot, so a broken deploy fails its health check and the platform keeps the previous version running.
- **TLS with full verification.** Connections to Neon use `ssl.create_default_context()`, which checks the certificate chain *and* the hostname (equivalent to `sslmode=verify-full`), protecting against man-in-the-middle attacks.
- **`pool_pre_ping`.** Neon scales to zero and closes idle connections. Pre-ping tests each pooled connection on checkout (one extra round trip) instead of failing the first request after an idle period with `connection is closed`.
- **Session per request.** `get_db_session` commits on success, rolls back on any exception (and re-raises), and always returns the connection to the pool.
- **CORS allowlist from config.** Only listed frontend origins may read responses in a browser. CORS is a browser-enforced read protection, not server-side access control; CSRF protection is a separate layer (planned for H1).

## Deployment

- **Render** web service, auto-deploys from `main`.
- Root directory: `wyd-backend` · Build: `uv sync --locked` · Start: `uv run fastapi run`
- **Single worker**, on purpose: later milestones keep WebSocket connections and rate-limit counters in process memory. Scaling out with Redis is a planned lesson (M7).
- Environment variables are set in the Render dashboard only. Production uses Neon's `main` branch with its own role password, separate from the `dev` branch used locally.

## Known security gaps

Being explicit about what is *not* done yet. Each item is scheduled for a milestone.

| Gap | Risk today | Planned |
|---|---|---|
| No authentication or users yet | Nothing to protect yet | M1 |
| No rate limiting | `/health` hits the database on every call, so anyone can generate DB load and keep the Neon compute awake (cost) | H1 |
| No security headers (CSP, HSTS, nosniff…), no `TrustedHostMiddleware`, no request body size limit | Low with only two GET endpoints | H1 |
| `/docs` is public | Intentional: the live docs are the demo until the frontend exists | F1 |
| One Neon role per branch with full privileges (no separate least-privilege app role vs. migration role) | A SQL injection or leaked app credential could run DDL | later (M1+) |
| SQL echo logging in `dev` prints bound parameters | Harmless now; would log emails and password hashes once users exist | M1 (log redaction) |
| No automated tests, type checking in CI, dependency audit, or secret scanning | Regressions and leaked secrets are caught only by manual review (`git diff --staged` before every commit) | H1 |
| Register reveals whether an email is already registered (email enumeration). Mitigated by rate limiting in H1

## Roadmap

| Milestone | Tag | Demo |
|---|---|---|
| **M0 Walking skeleton** ✅ | v0.0.1 | live `/health` |
| M1 Accounts | v0.1.0 | live Swagger `/docs` |
| M2 Social: posts, likes, feed, blocking | v0.2.0 | live Swagger `/docs` |
| H1 Hardening: tests, CI, refresh rotation, CSRF, rate limits | v0.3.0 | green CI, security write-up |
| F1 Frontend (React + Vite + TS) | v0.4.0 | real UI |
| M3 Realtime DMs over WebSockets | v0.5.0 | two browsers chatting |
| M4 Group chats + image uploads | v1.0.0 | MVP |
