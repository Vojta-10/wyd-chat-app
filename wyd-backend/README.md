# wyd-backend

FastAPI backend for **WYD**, a live chat and social app (accounts, posts and likes, 1:1 and group chats, image sharing).

This is a learning and portfolio project, built milestone by milestone with a strong focus on security. Every milestone ends deployed and tagged.

**Live:** https://wyd-chat-app.onrender.com · [Swagger UI (`/docs`)](https://wyd-chat-app.onrender.com/docs)

> Hosted on Render's free tier: after ~15 minutes of inactivity the service spins down, so the first request can take up to a minute.

## Status: M1, accounts (in progress → `v0.1.0`)

Accounts with Argon2id password hashing, a JWT access token in an httpOnly cookie, and customizable profiles. Previous release: `v0.0.1` (M0, walking skeleton).

| Endpoint | Auth | What it does |
|---|---|---|
| `POST /v1/auth/register` | – | Create an account (email, username, password). Returns a summary: id, username, join date |
| `POST /v1/auth/login` | – | Check email + password, set the access token cookie. Returns your public profile |
| `POST /v1/auth/logout` | – | Delete the access token cookie |
| `GET /v1/users/me` | cookie | Your own account (including email) with your full profile (including theme) |
| `PATCH /v1/users/me` | cookie | Change your username |
| `PATCH /v1/users/me/profile` | cookie | Change display name, bio, pronouns, accent color or theme. Send only the fields you want to change |
| `GET /v1/users/{username}` | – | Public account (id, username, join date) with its public profile (no theme). Case-insensitive lookup |
| `GET /health` | – | Runs `SELECT 1` against Postgres |
| `GET /docs` | – | Interactive API docs (intentionally public until the frontend exists) |

**Try it in Swagger UI:** `register` → `login` (the browser stores the cookie) → `GET /v1/users/me` → `PATCH /v1/users/me/profile` with e.g. `{"bio": "hi", "accent_color": "#ff8800"}`.

Profile fields:

| Field | Rules | Visible to |
|---|---|---|
| `display_name` | 1–64 characters after trimming, no control or format characters. Starts as your username. Can't be `null` | everyone |
| `bio` | Up to 128 characters, line breaks allowed. `null` clears it | everyone |
| `pronouns` | Up to 16 characters. `null` clears it | everyone |
| `accent_color` | Hex color `#RRGGBB`, stored uppercase. `null` means the app default | everyone |
| `theme` | `light`, `dark` or `system` (default). `null` resets it to `system` | only you |

## Stack

- **Python 3.14**, managed with [uv](https://docs.astral.sh/uv/)
- **FastAPI** (ASGI, served by uvicorn via the FastAPI CLI) + **Pydantic 2**
- **SQLAlchemy 2.1** (async) + **asyncpg**, **Alembic** for migrations
- **PostgreSQL on Neon** (serverless, scales to zero)
- **argon2-cffi** (Argon2id password hashing), **PyJWT** (access tokens)
- **pydantic-settings** for 12-factor configuration
- **Render** for hosting

## Project structure

Organized by technical layer. Dependencies point one way only: `routes → services → repositories → models`.

```
wyd-backend/
├── app/
│   ├── main.py            # FastAPI app, lifespan, CORS, exception handlers, routers
│   ├── dependencies.py    # get_db_session, get_current_user, typed Annotated deps
│   ├── core/              # config (settings), constants (cookie options),
│   │                      # exceptions (domain errors + HTTP handlers), security (Argon2, JWT)
│   ├── db/                # base (DeclarativeBase + naming convention), engine (lifecycle)
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic request/response models (Create / Login / Patch / Public / Self)
│   ├── repositories/      # DB queries only
│   ├── services/          # business rules; raise domain exceptions, know nothing about HTTP
│   ├── routes/v1/         # thin HTTP routers: parse → call service → return a schema
│   ├── utils/             # DB error → domain error translation
│   └── scripts/           # dev tools (print_ddl: show the DDL the models generate)
├── alembic/               # migrations (async env.py)
├── example.env            # every setting with dummy values (committed)
├── .env                   # real values (gitignored, never committed)
├── pyproject.toml
└── uv.lock
```

## Running locally

Prerequisites: Python 3.14, uv, and a Neon project with a **`dev` branch** (local development never touches the production branch).

```bash
cd wyd-backend
uv sync                      # install exact versions from uv.lock
cp example.env .env          # then fill in real values (see below)
uv run alembic upgrade head  # create/upgrade the tables on your dev branch
uv run fastapi dev           # dev server with auto-reload on http://127.0.0.1:8000
```

The entrypoint (`app.main:app`) is configured in `pyproject.toml` under `[tool.fastapi]`.

New migration: `uv run alembic revision --autogenerate -m "describe the change"`, then **read the generated file** before applying it.

### Configuration

All settings come from environment variables (or `.env` locally). Missing or invalid values make the app **fail at startup** instead of misbehaving later.

| Variable | Example | Purpose |
|---|---|---|
| `DATABASE_URL_POOLING` | `postgresql+asyncpg://user:pass@ep-xxx-pooler.region.aws.neon.tech/db` | Neon **pooled** connection string, used by the app |
| `DATABASE_URL_NO_POOLING` | `postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/db` | Neon **direct** connection string, used by Alembic (PgBouncer's transaction mode breaks migrations) |
| `ENVIRONMENT` | `dev` or `prod` | Required, no default. `dev` enables SQL echo logging |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | JSON list of allowed browser origins (the frontend), never `*` |
| `JWT_SECRET` | output of `python -c "import secrets; print(secrets.token_urlsafe(32))"` | HS256 signing key, at least 43 characters. Different per environment |
| `JWT_ACCESS_TOKEN_LIFETIME` | `30` | Access token lifetime in **minutes** (10–60) |

Do not put `?sslmode=...` in the URLs: asyncpg doesn't understand libpq query parameters. TLS is configured in code (see below).

## Design notes

### Database and lifecycle (M0)

- **Engine lifecycle in the lifespan.** The engine and session factory are created when the app starts and disposed when it shuts down (closing pooled connections cleanly). They live on `app.state`, owned by the app instance rather than a module global, and requests reach them through the `get_db_session` dependency.
- **Fail fast.** On startup the app opens a connection and runs `SELECT 1`. A wrong URL or password crashes the boot, so a broken deploy fails its health check and the platform keeps the previous version running.
- **TLS with full verification.** Connections to Neon use `ssl.create_default_context()`, which checks the certificate chain *and* the hostname (equivalent to `sslmode=verify-full`), protecting against man-in-the-middle attacks. Alembic's `env.py` uses the same TLS setup.
- **`pool_pre_ping`.** Neon scales to zero and closes idle connections. Pre-ping tests each pooled connection on checkout (one extra round trip) instead of failing the first request after an idle period with `connection is closed`.
- **Session per request.** `get_db_session` commits on success, rolls back on any exception (and re-raises), and always returns the connection to the pool.
- **CORS allowlist from config.** Only listed frontend origins may read responses in a browser. CORS is a browser-enforced read protection, not server-side access control; CSRF protection is a separate layer (planned for H1).

### Accounts (M1)

- **UUIDv7 primary keys**, generated by Postgres. Unlike auto-increment IDs, they don't reveal how many accounts exist (they do contain a creation timestamp, which is accepted).
- **Case-insensitive uniqueness** for email and username through unique indexes on `lower(email)` and `lower(username)`. Lookups use `lower()` on both sides so they match the index (verified with `EXPLAIN`). The username is stored as typed.
- **Let the database decide.** Register and username changes don't check "is it taken?" first (a race between two requests would pass both checks). They insert/update and translate the unique-index violation into a `409`. Unknown integrity errors are re-raised, never swallowed.
- **Argon2id** with OWASP parameters (`t=4`, `m=9 MiB`, `p=1`). Hashing runs in a thread pool capped at 8 concurrent hashes, so a burst of logins can't exhaust the instance's memory. Hashes made with old parameters are upgraded on the next successful login.
- **Enumeration-safe login.** Unknown email and wrong password return the same `401`, and the unknown-email path still does Argon2 work so response times are similar.
- **JWT access token** (HS256) in a `__Host-` cookie: `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`. Decoding pins the algorithm and requires `exp`, `iat`, `iss`, `aud`, `sub` and `jti`. `sub` is parsed into a UUID at that boundary, so a malformed token is a `401`, never a `500`. The cookie attributes live in one shared constant, so setting and deleting the cookie can't drift apart.
- **Mass-assignment protection** on `PATCH /users/me`: the schema rejects unknown fields (`extra="forbid"` → `422`), only fields the client actually sent are applied (`exclude_unset`), and the repository enforces its own allowlist of updatable columns. Email and password changes are deliberately not part of this endpoint (they will need re-authentication).
- **Public profiles hide inactive accounts.** A deactivated user gets the same `404` as a username that doesn't exist. The public schema exposes only `id`, `username`, `created_at` and the public profile fields.
- **Layering.** Services raise domain exceptions (`UsernameTaken`, `InvalidCredentials`, `UserNotFound`, …); handlers in `core/exceptions.py` map them to HTTP responses. ORM models never leave the API: every route has a `response_model`, so fields like `hashed_password` can't leak.

### Profiles (M1)

- **Separate `user_profiles` table, 1:1 with `users`.** `user_id` is both the primary key and a foreign key with `ON DELETE CASCADE`. Account data (credentials, email) and presentation data (bio, theme…) live in different tables, which keeps the `users` table small and makes it clear which data is sensitive.
- **The database creates the profile.** An `AFTER INSERT` trigger on `users` inserts the profile row (display name = username), so every way of creating a user gets a profile, not only the code path through the API. The migration that added the table also backfilled profiles for existing users with `INSERT … WHERE NOT EXISTS`. Note: tests must build their database with Alembic, not `metadata.create_all()`, which doesn't know about the trigger.
- **Self-heal on write, never on read.** If a profile row is ever missing, `PATCH /users/me/profile` recreates it instead of failing with a `500` the user can't fix. The insert runs in a **savepoint**, so if a concurrent request created the row first, only the savepoint rolls back; the unique violation is swallowed and the existing row is re-read. Any other database error is re-raised. `GET` requests never write: a missing profile is returned as `user_profile: null`. Safe methods must not change state (they're also the methods CSRF protection skips).
- **Validation in two layers.** Pydantic validates and normalises the input (trimming, uppercasing the color, `\r\n` → `\n`, `null` → the column's default). The database enforces the same rules with `CHECK` constraints on `theme` and `accent_color`, as the last line of defence. The allowed themes are defined once as a `Literal` type, and the database constraint is generated from it.
- **Unicode-safe text.** Display name, bio and pronouns reject every Unicode control and format character (category `C*`), except a line break in the bio. This blocks invisible characters and **right-to-left overrides** (`U+202E`), which can make a display name look like a different name (impersonation).
- **Mass-assignment protection** works as on `PATCH /users/me`: `extra="forbid"`, `exclude_unset`, and a column allowlist in the repository. The profile has its own endpoint and schema, so a stray `username` in a profile update is a `422`, not a silent change.
- **Eager loading by design.** The `user_profile` relationship is configured with `lazy="raise"`: an accidental lazy load (which would be an implicit, async-unsafe query) fails loudly instead of quietly running extra queries. Every user query loads the profile explicitly with `joinedload` (one query with a `LEFT OUTER JOIN`).
- **Known limitation:** because format characters are rejected, emoji sequences joined with a zero-width joiner (`U+200D`, e.g. 👨‍👩‍👧 or 🏳️‍🌈) are rejected in display names, bios and pronouns. Single emoji like 😀 work. Allowing ZWJ only inside valid emoji sequences would need an emoji-sequence parser, so it's out of scope for now.

## Deployment

- **Render** web service, auto-deploys from `main`.
- Root directory: `wyd-backend` · Build: `uv sync --locked && uv run alembic upgrade head` · Start: `uv run fastapi run`
- **Migrations run in the build step** (Render's pre-deploy command is paid-only). The old version keeps serving while the new one builds, so every migration must stay compatible with the code that's currently live (expand/contract). A failed deploy does not roll back the database.
- **Single worker**, on purpose: later milestones keep WebSocket connections and rate-limit counters in process memory. Scaling out with Redis is a planned lesson (M7).
- Environment variables are set in the Render dashboard only. Production uses Neon's `main` branch with its own role password, separate from the `dev` branch used locally.

## Known security gaps

Being explicit about what is *not* done yet. Each item is scheduled for a milestone.

| Gap | Risk today | Planned |
|---|---|---|
| Logout only deletes the cookie. The access JWT is stateless and stays valid until `exp` (`JWT_ACCESS_TOKEN_LIFETIME`, 10–60 min) | A token copied before logout (e.g. from a shared or compromised device) still works: the holder can read and change the account until it expires, and the server can't tell | H1: short-lived access token (5–15 min) + rotating, revocable refresh token |
| No CSRF token | State-changing requests rely on the cookie's `SameSite=Strict`, which stops cross-site requests in modern browsers but not attacks from a same-site origin | H1: signed double-submit token + required custom header |
| No rate limiting | Register and login allow unlimited attempts (password guessing, email enumeration), and every attempt costs an Argon2 hash. Public profiles can be scraped. `/health` hits the database on every call | H1 |
| Public profiles are readable without logging in | Anyone can check whether a username exists and see its join date (usernames are public by design) | M2: blocking + privacy setting; H1: rate limiting |
| No reserved usernames | Anyone can register names like `admin` or `support` (impersonation). A future `/users/<word>` route would collide with a user of that name | Before M2 adds new `/users/...` routes |
| No security headers (CSP, HSTS, nosniff…), no `TrustedHostMiddleware`, no request body size limit | Low: the API serves only JSON, no HTML pages. Oversized bodies are parsed before field limits reject them | H1 |
| `/docs` is public | Intentional: the live docs are the demo until the frontend exists | F1 |
| One Neon role per branch with full privileges (no separate least-privilege app role vs. migration role) | A SQL injection or leaked app credential could run DDL | later |
| SQL echo logging in `dev` prints bound parameters | The local dev terminal shows emails and Argon2 password hashes (production is not affected: echo is off) | M1 (log redaction) |
| No automated tests, type checking in CI, dependency audit, or secret scanning | Regressions and leaked secrets are caught only by manual review (`git diff --staged` before every commit). Test cases are tracked as `TODO(test)` comments | H1 |
| Register reveals whether an email is already registered (`409`), so emails can be enumerated. Login itself is enumeration-safe | Anyone can check whether an email has an account. Rate limiting (H1) only slows this down | Fix: a generic register response plus an activation email. Needs email sending (not scheduled yet) |
| No email verification | Someone can register with another person's email before they do (account pre-hijacking) | Together with email sending (not scheduled yet) |
| Unhandled errors (e.g. a corrupt password hash → `500`) are only visible in the platform logs | Nobody is alerted, so a bug can go unnoticed | M6 (error tracking, structured logs) |

## Roadmap

| Milestone | Tag | Demo |
|---|---|---|
| **M0 Walking skeleton** ✅ | v0.0.1 | live `/health` |
| **M1 Accounts** (in progress) | v0.1.0 | live Swagger `/docs` |
| M2 Social: posts, likes, feed, blocking | v0.2.0 | live Swagger `/docs` |
| H1 Hardening: tests, CI, refresh rotation, CSRF, rate limits | v0.3.0 | green CI, security write-up |
| F1 Frontend (React + Vite + TS) | v0.4.0 | real UI |
| M3 Realtime DMs over WebSockets | v0.5.0 | two browsers chatting |
| M4 Group chats + image uploads | v1.0.0 | MVP |
