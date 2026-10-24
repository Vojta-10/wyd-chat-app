# wyd-backend

FastAPI backend for WYD. The project-wide rules in `../CLAUDE.md` apply here too: **Claude teaches and reviews, it does not build**, and the user does all git operations.

## Commands

```bash
uv sync                                            # install deps from uv.lock
uv run fastapi dev                                 # dev server with reload (entrypoint: app/main.py)
uv run alembic revision --autogenerate -m "msg"    # create a migration (always review it!)
uv run alembic upgrade head                        # apply migrations
uv run pytest                                      # tests (needs `docker compose up -d`)
uv run ruff check --fix && uv run ruff format      # lint + format
uv run mypy app                                    # type check (strict)
uv run pip-audit                                   # known-vulnerable dependencies
uv run bandit -r app                               # static security analysis
docker compose up -d                               # local Postgres for tests
```

Entrypoint: once the code moves to `app/main.py`, point the FastAPI CLI at it with `[tool.fastapi] entrypoint = "app.main:app"` in `pyproject.toml` (check the current FastAPI CLI docs), or pass the path explicitly: `uv run fastapi dev app/main.py`.

Add dependencies with `uv add <pkg>` / `uv add --dev <pkg>`. Never edit `uv.lock` by hand.

## Stack and versions

Latest on PyPI as of 2026-10-24. Before adding a package, check the current version and changelog. Claude must verify the current docs for these libraries instead of relying on memory.

| Purpose | Package | Version |
|---|---|---|
| Runtime | Python | 3.14 |
| Web framework | `fastapi[standard]` (starlette 1.10, uvicorn 0.54, websockets 17.3) | 0.162.0 |
| Validation / settings | `pydantic` / `pydantic-settings` / `email-validator` | 2.14.1 / 2.16.1 / 2.3.0 |
| ORM / migrations | `sqlalchemy[asyncio]` / `alembic` | 2.1.6 / 1.20.1 |
| DB driver | `asyncpg` | 0.32.0 |
| Password hashing | `argon2-cffi` (Argon2id) | 25.1.0 |
| JWT | `pyjwt[crypto]` | 2.15.1 |
| Encryption at rest (TOTP secrets) | `cryptography` | 50.0.2 |
| 2FA | `pyotp` | 2.10.0 |
| OAuth | `authlib` | 1.9.1 |
| Object storage (Cloudflare R2, S3 API) | `aioboto3` | 15.5.0 |
| Image processing | `pillow` | 13.0.0 |
| Rate limiting | `limits` (in-memory now, Redis later) | 5.8.0 |
| Logging / tracing (phase 9) | `structlog` / `opentelemetry-sdk` | 26.1.0 / 1.45.1 |
| Dev: tests | `pytest` / `pytest-asyncio` / `httpx` / `testcontainers[postgres]` | 9.1.1 / 1.4.0 / 0.28.1 / 4.15.0 |
| Dev: quality | `ruff` / `mypy` | 0.17.2 / 2.4.0 |
| Dev: security | `bandit` / `pip-audit` (+ `pre-commit` with gitleaks) | 1.9.4 / 2.10.1 |

Database: **PostgreSQL on Neon.** Redis is intentionally **not** used yet. WebSocket connections and rate-limit counters live in memory, which only works with a single process. Introducing Redis is a planned lesson in phase 10.

## Architecture: organized by technical layer

```
wyd-backend/
├── app/
│   ├── main.py            # app factory, lifespan, middleware, router registration
│   ├── core/              # config.py (pydantic-settings, SecretStr), security.py (hashing, JWT, CSRF),
│   │                      # exceptions.py, logging.py, constants.py
│   ├── db/                # engine.py, session.py (async_sessionmaker), base.py (DeclarativeBase + naming convention)
│   ├── models/            # SQLAlchemy ORM models, one file per aggregate (user.py, post.py, conversation.py…)
│   ├── schemas/           # Pydantic request/response models (Create / Update / Read split)
│   ├── repositories/      # DB queries only, no business rules
│   ├── services/          # business logic + authorization checks; calls repositories
│   ├── routes/v1/         # thin HTTP routers: parse → call service → return schema
│   ├── websockets/        # connection manager, event envelope schemas, WS router, event handlers
│   ├── dependencies/      # get_db, get_current_user, require_csrf, pagination, rate-limit deps
│   ├── middleware/        # security headers, request ID, body size limit
│   └── utils/
├── alembic/ + alembic.ini
├── tests/                 # unit/, integration/, conftest.py
├── docker-compose.yml     # Postgres for tests
├── .env.example           # every setting with dummy values, committed
├── .env                   # real secrets, NEVER committed
└── pyproject.toml
```

**Layer rules** (Claude points out violations in reviews):
- Dependency direction: `routes → services → repositories → models`. Never the other way round.
- Routes contain no DB queries and no business logic.
- Services know nothing about HTTP (no `Request`, no `HTTPException`). They raise domain exceptions, which handlers in `core/exceptions.py` map to HTTP responses.
- ORM models never leave the API. Responses are always Pydantic schemas (`response_model`), so fields like `password_hash` can't leak.
- Async all the way: async engine and sessions, and no blocking I/O in request handlers. CPU-heavy work (Argon2 hashing, Pillow) runs in a thread pool (`anyio.to_thread.run_sync`).

## Data model sketch

The user designs the models; Claude reviews them.

- `users`: email (unique, case-insensitive), username (unique), password_hash (nullable for OAuth-only users), email_verified, is_active, timestamps
- `refresh_tokens`: user_id, family_id, token_hash, expires_at, revoked_at, replaced_by_id, user_agent, ip, created_at
- `oauth_accounts`: user_id, provider, provider_user_id (unique together)
- `user_totp`: encrypted secret, enabled_at, hashed single-use backup codes
- `user_profiles` / settings: display name, bio, pronouns, avatar, banner, accent color, theme, status text, privacy (who can DM me / see my posts)
- `user_blocks`
- `posts`, `post_likes` (composite PK `(user_id, post_id)` makes a like idempotent)
- `media`: owner, object key, mime, size, width/height, status (`pending` / `ready` / `rejected`)
- `conversations`: type (`direct` | `group`), name, icon, theme/emoji/wallpaper
- `conversation_members`: role (`owner` | `admin` | `member`), nickname, muted_until, last_read_message_id
- `messages`: conversation_id, sender_id, type (`text` | `image`), body, media_id, edited_at, deleted_at (soft delete)
- `audit_log`: security events (login, failed login, token reuse, 2FA changes, password change…)

Conventions: choose UUIDv7 or bigint IDs (Claude explains the tradeoffs), `timestamptz` everywhere (`created_at`/`updated_at`), a constraint naming convention on `MetaData` (so Alembic migrations are stable), **keyset (cursor) pagination** for feeds and message history (no `OFFSET`), and indexes for every foreign key and every common query.

## Neon notes

- Use the **pooled** connection string for the app and the **direct** (non-pooled) one for Alembic migrations.
- asyncpg doesn't understand `?sslmode=require`. Pass TLS via `connect_args={"ssl": "require"}` (a common gotcha).
- Check Neon's PgBouncer prepared-statement support and configure asyncpg's statement cache if needed.
- Consider a least-privilege **app role** (DML only) that is separate from the **migration role** (DDL).
- Use Neon branches for experimenting with risky migrations.

## Security requirements

Security is the core lesson of this project. Claude checks these in **every** review.

**Passwords**
- Argon2id with OWASP-recommended parameters; rehash on login when the parameters change.
- Length 12–128, no composition rules, and a breached-password check via the HIBP k-anonymity API.
- No user enumeration: unknown user and wrong password get the same response and similar timing (hash against a dummy hash).

**Tokens and sessions**
- Access token: JWT that expires in 5–15 minutes. Pin the algorithm on decode, and validate `iss`, `aud`, `exp`, `iat`, `sub`, `jti`.
- Refresh token: opaque random value (`secrets.token_urlsafe`), stored **hashed** (SHA-256), **rotated on every use**. Reusing an already-rotated token revokes the **whole family** and is logged to the audit log.
- Logout, "log out all devices", and a sessions list endpoint (list and revoke individual devices).
- Revoke all sessions on password change.

**Cookies, CSRF, CORS**
- Cookies: `__Host-` prefix, `Secure`, `HttpOnly`, `SameSite=Lax`/`Strict`. Scope the refresh cookie path to the refresh endpoint.
- CSRF: signed double-submit token plus a required custom header on all state-changing requests.
- CORS: explicit origin allowlist (the Vite dev origin), `allow_credentials=True`, **never** `*`.

**HTTP hardening**
- Security-headers middleware: CSP, HSTS, `X-Content-Type-Options: nosniff`, Referrer-Policy, Permissions-Policy, `frame-ancestors 'none'`.
- `TrustedHostMiddleware`, a request body size limit, and docs (`/docs`) disabled in production.
- Errors: never send stack traces or internal details to the client. Use consistent error response shapes.

**Input and authorization**
- Pydantic with `extra="forbid"`, a length limit on every string, and strict types where it makes sense.
- Only the ORM or bound parameters. **Never** build SQL with f-strings.
- **AuthZ in services.** Every resource access checks ownership, membership, or role (IDOR prevention). Blocked users can't DM or see each other's content.
- Tests are required for negative cases like "user B cannot read user A's conversation".

**Rate limiting and abuse**
- Login, register, refresh and 2FA: limit per IP **and** per account, with progressive backoff or temporary lockout.
- Message send rate per WebSocket connection; post and like rate per user.

**WebSockets**
- Validate the `Origin` header on the handshake (Cross-Site WebSocket Hijacking).
- Authenticate at the handshake (cookie or a single-use short-lived WS ticket from an HTTP endpoint). Never put a JWT in the query string.
- Re-check authorization on every action. When the access token expires, force re-auth.
- Max frame/message size, and a typed Pydantic event envelope (`{"type": ..., "data": ...}`) validated per frame. Unknown event types are rejected.
- Heartbeat (ping/pong) with a timeout, and correct close codes (e.g. 1008 policy violation).

**Uploads (R2)**
- Private bucket, random object keys (never user-supplied filenames).
- Presigned PUT URLs with content-type and size conditions, and a short expiry.
- Post-upload validation: magic bytes, allowed formats, `Image.MAX_IMAGE_PIXELS` (decompression-bomb guard), and **re-encode with Pillow** to strip EXIF/GPS metadata.
- Serve chat images only to conversation members, through short-lived presigned GET URLs.

**2FA and OAuth (phase 7)**
- TOTP secret encrypted at rest (AES-GCM or Fernet, key from env). Backup codes are hashed and single-use. Prevent TOTP code replay.
- Step-up auth (password or TOTP) for sensitive actions: change email or password, disable 2FA, delete account.
- OAuth: authorization code flow with `state` + PKCE. Only link accounts on a **verified** provider email.

**Secrets and operations**
- `.env` is gitignored, and only `.env.example` is committed. Use `SecretStr` for secrets in settings.
- Log redaction: never log passwords, tokens, cookies, or full emails.
- Audit log for security events.
- `pip-audit`, `bandit`, and a gitleaks pre-commit hook. Later these also run in CI.

## Roadmap

The MVP is **phases 0–6**. Every phase is one or more feature branches merged through PRs.

0. **Foundation:** move to the `app/` layered skeleton; settings via pydantic-settings; ruff, mypy strict, pytest, pre-commit; docker-compose Postgres; async SQLAlchemy + async Alembic; `/health`; global error handlers; security-headers middleware; CORS.
1. **Accounts and auth core:** register, login, logout; Argon2id; JWT access + refresh rotation in cookies; CSRF; `/users/me`; rate limiting; sessions list; enumeration-safe responses; audit log basics.
2. **Profiles and customization:** profile fields (display name, bio, pronouns, accent color, theme, status), privacy settings, blocking, public profile view, username change rules.
3. **Posts and likes:** CRUD, keyset-paginated feed, idempotent like/unlike, like counts (lesson: a denormalized counter vs. `COUNT(*)`, and race conditions).
4. **Media:** R2 presigned uploads, validation and re-encode pipeline, avatars and banners, post images, cleanup of orphaned uploads.
5. **Realtime DMs:** WS auth handshake, connection manager, event protocol, persist-then-broadcast, history pagination, reconnect and resync (fetch missed messages since the last ID).
6. **Group chats:** create, invite, kick, leave; roles and permissions; chat customization (name, icon, theme, emoji, per-member nicknames); images in chats; editing and deleting messages.
7. **Advanced auth:** TOTP 2FA + backup codes + step-up auth; OAuth login with GitHub and Google.
8. **Realtime extras:** typing indicators, read receipts, unread counts, online presence, notifications.
9. **Observability:** structlog JSON logs, request IDs, OpenTelemetry tracing, audit-log querying.
10. **CI/CD and deploy:** GitHub Actions (ruff, mypy, pytest, pip-audit, bandit); multi-stage, non-root Dockerfile; deploy to Fly.io or Railway. Lesson: why multiple workers break the in-memory WS manager and rate limiter, followed by introducing Redis pub/sub.

## Testing conventions

- `pytest` + `pytest-asyncio`, with httpx `AsyncClient` over the ASGI transport against Docker Postgres, and a transaction rollback per test.
- Every endpoint gets at least a happy-path test, an **authz-negative** test (wrong user or not logged in), and a **validation-negative** test.
- WebSocket tests use Starlette's `TestClient.websocket_connect`.
- **Security regression tests are mandatory:** refresh token reuse, missing or invalid CSRF, IDOR, bad `Origin` on WS, rate limit triggers, and oversized uploads.
- Never run tests against the Neon database.

## Teaching reminders for Claude

- **At the start of a phase or feature:** name the concepts to learn, link the docs to read, and remind the user to create a branch (suggest a name).
- **During work:** answer with explanations and hints. Ask what the user thinks before revealing the solution.
- **At a checkpoint:** remind the user to commit and suggest a Conventional Commit message.
- **At the end of a phase:** offer a review against the security checklist above, and remind the user to open a PR, self-review the diff, and merge into `main`.
