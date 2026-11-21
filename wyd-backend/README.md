# wyd-backend

FastAPI backend for **WYD**, a live chat and social app (accounts, posts and likes, 1:1 and group chats, image sharing).

This is a learning and portfolio project, built milestone by milestone with a strong focus on security. Every milestone ends deployed and tagged.

**Live:** https://wyd-chat.up.railway.app · [Swagger UI (`/docs`)](https://wyd-chat.up.railway.app/docs)

> The database (Neon) scales to zero when idle, so the first request after a quiet period can take about a second longer.

## Status: M2, social ✅ (`v0.2.0`)

Posts, likes, a paginated feed, blocking and a posts visibility setting, on top of M1's accounts (Argon2id, JWT access token in an httpOnly cookie, customizable profiles). Deployed on Railway. Previous releases: `v0.1.0` (M1, accounts), `v0.0.1` (M0, walking skeleton). Next: H1, hardening (tests, CI, refresh tokens, CSRF, rate limits).

"Optional" auth means the endpoint works logged out, and a valid cookie personalizes the answer (`is_liked`, blocks, posts visibility).

| Endpoint | Auth | What it does |
|---|---|---|
| `POST /v1/auth/register` | – | Create an account (email, username, password). Returns a summary: id, username, join date |
| `POST /v1/auth/login` | – | Check email + password, set the access token cookie. Returns your public profile |
| `POST /v1/auth/logout` | – | Delete the access token cookie |
| `GET /v1/users/me` | cookie | Your own account (including email) with your full profile (including theme) |
| `PATCH /v1/users/me` | cookie | Change your username |
| `PATCH /v1/users/me/profile` | cookie | Change display name, bio, pronouns, accent color or theme. Send only the fields you want to change |
| `GET /v1/users/{username}` | optional | Public account (id, username, join date) with its public profile (no theme). Case-insensitive lookup. `404` if either of you has blocked the other |
| `GET /v1/users/{username}/posts` | optional | One user's posts, newest first, paginated like the feed |
| `PUT /v1/users/{username}/block` | cookie | Block a user (idempotent) |
| `DELETE /v1/users/{username}/block` | cookie | Remove *your* block on a user (idempotent) |
| `GET /v1/posts/` | optional | The feed: everyone's visible posts, newest first. `page_size` 1–100 (default 20), `cursor` = the previous page's `next_cursor` |
| `GET /v1/posts/{post_id}` | optional | One post, same shape as a feed item |
| `POST /v1/posts/` | cookie | Create a post (`description`, 1–256 characters) |
| `PATCH /v1/posts/{post_id}` | cookie | Edit your own post's description |
| `DELETE /v1/posts/{post_id}` | cookie | Delete your own post (its likes go with it) |
| `PUT /v1/posts/{post_id}/like` | cookie | Like a post (idempotent). Returns the post with the new `like_count` |
| `DELETE /v1/posts/{post_id}/like` | cookie | Remove your like (idempotent) |
| `GET /health` | – | Runs `SELECT 1` against Postgres |
| `GET /docs` | – | Interactive API docs (intentionally public until the frontend exists) |

**Try it in Swagger UI:** `register` → `login` (the browser stores the cookie) → `POST /v1/posts/` with `{"description": "hello WYD"}` → `PUT /v1/posts/{post_id}/like` → `GET /v1/posts/?page_size=5`, then pass the returned `next_cursor` as `cursor` for the next page.

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
- **Railway** for hosting

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
│   ├── utils/             # DB error → domain error translation, shared validators
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
| `ENVIRONMENT` | `dev` or `prod` | Required, no default. `dev` enables SQL echo logging (statements only, parameters hidden) |
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
- **No SQL parameters in logs.** The engine uses `hide_parameters=True`, so bound values (emails, password hashes) appear neither in the dev echo log nor in database error messages, which would otherwise end up in the production logs whenever an error isn't handled.
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

### Posts, likes and feed (M2)

- **Keyset (cursor) pagination, not `OFFSET`.** The feed is ordered by post id (UUIDv7, so newest first) and each page asks for `id < cursor`. A new post arriving between two page loads can't shift the pages, so there are no duplicates and no skipped posts, and Postgres doesn't have to read past all the earlier rows. The query fetches `page_size + 1` rows: the extra row only tells whether another page exists. A user's posts use an index on `(user_id, id)` (checked with `EXPLAIN`).
- **One query builder for every post read.** The feed, a user's posts, a single post and the response after a write all use the same select, so a post looks the same everywhere and the block and visibility rules can't be forgotten in one place. Columns are selected explicitly with real joins (no `joinedload` aliases), and the author's display name falls back to the username with `COALESCE`.
- **Idempotent likes.** A like is a row in `post_likes` with the composite primary key `(user_id, post_id)`, inserted with `ON CONFLICT DO NOTHING`: liking twice is harmless and can't fail with a race. Like/unlike use `PUT`/`DELETE`, the idempotent HTTP methods.
- **`like_count` is kept by the database.** `AFTER INSERT` / `AFTER DELETE` triggers on `post_likes` update the counter, so every way of adding or removing a like (including cascades when a user or post is deleted) keeps it right, and a `CHECK (like_count >= 0)` guards it. Reading a viral post's count stays a single column read instead of a `COUNT(*)`.
- **`is_liked`** is a correlated `EXISTS` per post for the current viewer (always `false` when logged out), served by the primary key index.
- **Ownership checks in the service.** Editing or deleting someone else's post is a `403` if you can see it, and a `404` if it's hidden from you (blocked either way, visibility, or an inactive author), so the status code doesn't reveal that the post exists. Post schemas use `extra="forbid"` and the repository has a column allowlist, so `user_id` or `like_count` can't be changed through `PATCH` (mass assignment).
- **Descriptions** follow the same text rules as profiles: trimmed, 1–256 characters, line breaks allowed (`\r\n` stored as `\n`), control and format characters rejected.
- **Reserved usernames** (route words like `settings` or `block`, and impersonation names like `admin` or `support`) are rejected case-insensitively on register *and* on username change.

### Blocking and visibility (M2)

- **A block hides both directions.** If either user has blocked the other, they can't see each other's profile, posts or likes, and get the same `404` as for something that doesn't exist. The rule is a `NOT EXISTS` against `user_blocks` inside the SQL query, not a filter in Python after `LIMIT`: filtering afterwards would return short or empty pages and end pagination early.
- **Can't see it → `404`; can see it but can't change it → `403`.** Editing or deleting a post you can't see is a `404` too, so the response doesn't confirm that a hidden post exists.
- **Silent blocks.** Blocking someone who has already blocked you still returns `204`. A `404` or `409` would tell them "this person blocked you". Each block row belongs to its blocker, so unblocking only removes your own block.
- **Blocking removes likes** between the two users in both directions, in one set-based `DELETE` (the counter triggers adjust `like_count`). The block and the delete run in one transaction.
- **Self-blocks** are rejected in the service (`400`) and by a `CHECK (blocker_id <> blocked_id)` constraint in the database.
- **Posts visibility** (`everybody` (default) / `logged-in` / `nobody`) is a profile setting that applies to all of a user's posts. Logged-out viewers only see `everybody`. Authors always see their own posts. The profile itself stays public.

## Deployment

- **Railway** (Hobby plan) web service in the **EU West (Amsterdam)** region, auto-deploys from `main`. Moved from Render's free tier in M1 because its cold starts (up to a minute after idling) made the live demo unusable.
- Root directory: `wyd-backend` · Builder: Railpack (dependencies from `uv.lock`, Python version from `.python-version`) · Pre-deploy: `uv run alembic upgrade head` · Start: `uv run fastapi run --forwarded-allow-ips="*"` · Healthcheck: `/health`
- **Build, release, run are separate stages** ([12-factor](https://12factor.net/build-release-run)). The build only installs dependencies and has no side effects. Migrations run in Railway's **pre-deploy command**, which starts only after a successful build. If the migration fails, the deploy stops and the previous version keeps serving. A failed deploy does not roll back the database.
- **Zero-downtime switchover.** Railway sends traffic to the new version only after `/health` returns `200`, and `/health` checks the database. Until then the old version keeps serving, *after* the migration has already run, so every migration must stay compatible with the code that's currently live (expand/contract).
- **Trusting the proxy's forwarded headers.** Railway terminates HTTPS at its edge and forwards the request to the app over plain HTTP, adding `X-Forwarded-Proto: https` and `X-Forwarded-For: <client IP>`. By default uvicorn only believes these headers from `127.0.0.1`, so the app thought every request was HTTP. Redirects (e.g. the trailing-slash `307`) pointed to `http://…`, and a `307` makes the client resend the same body, so a login sent to `/v1/auth/login/` would have resent the password in plain text. `--forwarded-allow-ips="*"` fixes this. Trusting every sender is only acceptable because the container has no public address: the only way in from the internet is through Railway's edge (Railway doesn't publish its proxy IPs, so they can't be listed explicitly).
  - **Side effect, verified 2026-11-14:** with `*`, uvicorn takes the client IP from the *leftmost* `X-Forwarded-For` entry, and a `curl` request with a fake `X-Forwarded-For` header reached the app with the fake IP. So the client IP the app sees is **client-controlled**. Nothing relies on it yet (see Known security gaps).
- **Port:** Railway injects `PORT` and the FastAPI CLI reads it (`--port` defaults to the `PORT` env var). `PORT=8080` is also set explicitly, so the app and Railway's healthcheck agree on the port.
- **Single replica, single worker**, on purpose: later milestones keep WebSocket connections and rate-limit counters in process memory. Scaling out with Redis is a planned lesson (M7).
- Settings are configured in the Railway dashboard, not with a `railway.toml` file: Railway deprecated config-as-code (it stops being read on 2026-12-01) in favour of a TypeScript-based infrastructure-as-code setup, which is more than this single service needs.
- Environment variables are set in the Railway dashboard only. Production uses Neon's `main` branch with its own role password, separate from the `dev` branch used locally.

## Known security gaps

Being explicit about what is *not* done yet. Each item is scheduled for a milestone.

| Gap | Risk today | Planned |
|---|---|---|
| Logout only deletes the cookie. The access JWT is stateless and stays valid until `exp` (`JWT_ACCESS_TOKEN_LIFETIME`, 10–60 min) | A token copied before logout (e.g. from a shared or compromised device) still works: the holder can read and change the account until it expires, and the server can't tell | H1: short-lived access token (5–15 min) + rotating, revocable refresh token |
| No CSRF token | State-changing requests rely on the cookie's `SameSite=Strict`, which stops cross-site requests in modern browsers but not attacks from a same-site origin | H1: signed double-submit token + required custom header |
| No rate limiting | Register and login allow unlimited attempts (password guessing, email enumeration), and every attempt costs an Argon2 hash. Public profiles and the feed can be scraped. Posts and likes can be spammed. `/health` hits the database on every call | H1 |
| Public profiles are readable without logging in | Anyone can check whether a username exists and see its join date and public profile fields (usernames are public by design). Only posts have a visibility setting | H1: rate limiting; a profile privacy setting is not scheduled |
| Blocks and visibility only apply to the logged-in account | A blocked user who logs out, or registers a second account, can see `everybody` posts again. `logged-in` means "anyone with an account", and registration is open, so it is not private. Only `nobody` hides posts from everyone | Accepted: inherent to public content. To be explained in the UI (F1) |
| Display names can impersonate | Reserved names only cover usernames, and only exact matches (`wyd_support` is allowed). A display name like "WYD Support" is allowed | F1: always show `@username` next to the display name |
| Like vs. block race | If a block lands between a like's visibility check and its insert, that like survives the block (very narrow window) | Later: make the insert itself conditional (`INSERT … SELECT … WHERE NOT EXISTS`) |
| Blocking a deactivated account returns `204`, while its profile returns `404` | Reveals that a deactivated account with that username exists | Small fix, not scheduled |
| No security headers (CSP, HSTS, nosniff…), no `TrustedHostMiddleware`, no request body size limit | Low: the API serves only JSON, no HTML pages. Oversized bodies are parsed before field limits reject them | H1 |
| `/docs` is public | Intentional: the live docs are the demo until the frontend exists | F1 |
| One Neon role per branch with full privileges (no separate least-privilege app role vs. migration role) | A SQL injection or leaked app credential could run DDL | later |
| The client IP is spoofable: behind Railway the app trusts `X-Forwarded-For` from everyone (`--forwarded-allow-ips="*"`) and uses its leftmost entry, which the client controls | None today: no logic uses the client IP, only the access logs record whatever IP a client claims. Per-IP rate limiting built on it would be trivially bypassed (a new fake IP per request) | H1, before per-IP rate limiting: take the IP from an entry or header the client can't control |
| CORS settings don't reject a wildcard origin (`CORS_ORIGINS=["*"]`) | None today (credentials aren't allowed). Once F1 enables `allow_credentials`, Starlette answers a wildcard by reflecting *any* origin, so a config mistake would let every website read logged-in responses | F1: reject `*` at startup (fail closed) |
| Unhandled errors return plain-text `Internal Server Error` instead of the JSON `{"detail": …}` shape | No leak (no stack traces), but clients must handle two error formats | H1 / M6 |
| No automated tests, type checking in CI, dependency audit, or secret scanning | Regressions and leaked secrets are caught only by manual review (`git diff --staged` before every commit). Test cases are tracked as `TODO(test)` comments | H1 |
| Register reveals whether an email is already registered (`409`), so emails can be enumerated. Login itself is enumeration-safe | Anyone can check whether an email has an account. Rate limiting (H1) only slows this down | Fix: a generic register response plus an activation email. Needs email sending (not scheduled yet) |
| No email verification | Someone can register with another person's email before they do (account pre-hijacking) | Together with email sending (not scheduled yet) |
| Unhandled errors (e.g. a corrupt password hash → `500`) are only visible in the platform logs | Nobody is alerted, so a bug can go unnoticed | M6 (error tracking, structured logs) |

## Roadmap

| Milestone | Tag | Demo |
|---|---|---|
| **M0 Walking skeleton** ✅ | v0.0.1 | live `/health` |
| **M1 Accounts** ✅ | v0.1.0 | live Swagger `/docs` |
| **M2 Social: posts, likes, feed, blocking** ✅ | v0.2.0 | live Swagger `/docs` |
| H1 Hardening: tests, CI, refresh rotation, CSRF, rate limits | v0.3.0 | green CI, security write-up |
| F1 Frontend (React + Vite + TS) | v0.4.0 | real UI |
| M3 Realtime DMs over WebSockets | v0.5.0 | two browsers chatting |
| M4 Group chats + image uploads | v1.0.0 | MVP |
