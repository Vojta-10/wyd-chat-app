# wyd-backend

FastAPI backend for WYD. The project-wide rules in `../CLAUDE.md` apply here too: **Claude teaches and reviews, it does not build**, and the user does all git operations.

## Commands

```bash
# From M0/M1
uv sync                                            # install deps from uv.lock
uv run fastapi dev                                 # dev server with reload (entrypoint: app/main.py)
uv run alembic revision --autogenerate -m "msg"    # create a migration (always review it!)
uv run alembic upgrade head                        # apply migrations

# From H1 (hardening milestone)
docker compose up -d                               # local Postgres for tests
uv run pytest                                      # tests
uv run ruff check --fix && uv run ruff format      # lint + format (until H1: just the ruff editor extension)
uv run mypy app                                    # type check (strict)
uv run pip-audit                                   # known-vulnerable dependencies
uv run bandit -r app                               # static security analysis
```

Entrypoint: once the code moves to `app/main.py`, point the FastAPI CLI at it with `[tool.fastapi] entrypoint = "app.main:app"` in `pyproject.toml` (check the current FastAPI CLI docs), or pass the path explicitly: `uv run fastapi dev app/main.py`.

Add dependencies with `uv add <pkg>` / `uv add --dev <pkg>`. Never edit `uv.lock` by hand.

## Stack and versions

Latest on PyPI as of 2026-10-24. Before adding a package, check the current version and changelog. Claude must verify the current docs for these libraries instead of relying on memory.

**Just-in-time tooling:** add a package in the milestone where it's first needed (the "Added in" column), not up front. Each tool should solve a problem the user can already feel.

| Purpose | Package | Version | Added in |
|---|---|---|---|
| Runtime | Python | 3.14 | M0 |
| Web framework | `fastapi[standard]` (starlette 1.10, uvicorn 0.54, websockets 17.3) | 0.162.0 | M0 |
| Validation / settings | `pydantic` / `pydantic-settings` / `email-validator` | 2.14.1 / 2.16.1 / 2.3.0 | M0 / M0 / M1 |
| ORM / migrations | `sqlalchemy[asyncio]` / `alembic` | 2.1.6 / 1.20.1 | M0 / M1 |
| DB driver | `asyncpg` | 0.32.0 | M0 |
| Password hashing | `argon2-cffi` (Argon2id) | 25.1.0 | M1 |
| JWT | `pyjwt[crypto]` | 2.15.1 | M1 |
| Rate limiting | `limits` (in-memory now, Redis in M7) | 5.8.0 | H1 |
| Dev: tests | `pytest` / `pytest-asyncio` / `httpx` / `testcontainers[postgres]` | 9.1.1 / 1.4.0 / 0.28.1 / 4.15.0 | H1 |
| Dev: quality | `ruff` / `mypy` | 0.17.2 / 2.4.0 | H1 (ruff editor extension from day 1) |
| Dev: security | `bandit` / `pip-audit` (+ `pre-commit` with gitleaks) | 1.9.4 / 2.10.1 | H1 |
| Object storage (Cloudflare R2, S3 API) | `aioboto3` | 15.5.0 | M4 |
| Image processing | `pillow` | 13.0.0 | M4 |
| Encryption at rest (TOTP secrets) | `cryptography` | 50.0.2 | M5 |
| 2FA / OAuth | `pyotp` / `authlib` | 2.10.0 / 1.9.1 | M5 |
| Logging / tracing | `structlog` / `opentelemetry-sdk` | 26.1.0 / 1.45.1 | M6 |

Database: **PostgreSQL on Neon.** Redis is intentionally **not** used yet. WebSocket connections and rate-limit counters live in memory, which only works with a **single process**, so deploy with one worker. Introducing Redis is a planned lesson in M7.

**Write type hints from day 1**, even though mypy only arrives in H1. Typing as you go makes turning on strict mode later a small cleanup instead of a rewrite.

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
- Branches: Neon `main` = production (the deployed app), and a `dev` branch for local development (`.env`). Make throwaway branches for risky migrations.

## Security requirements

Security is the core lesson of this project. Claude checks these in **every** review, against the milestone tag in brackets after each heading.

Security comes in layers that follow the milestones:
- **Baseline: always, from the first route.** It needs no setup, just correct code: Argon2id, enumeration-safe auth, Pydantic validation with length limits, response schemas, authorization checks in services, ORM-only queries, secrets only in env vars, CORS allowlist, and secure cookie flags.
- **Hardening: in H1 and later milestones.** Refresh rotation, CSRF, rate limiting, headers, tests, scanners.

Until H1, the README keeps a **"Known security gaps"** list. Being honest about what isn't done yet is itself a good portfolio signal. Before H1, Claude flags a missing H1 item only if it's actively dangerous in the current code.

**Passwords [M1; HIBP check in H1]**
- Argon2id with OWASP-recommended parameters; rehash on login when the parameters change.
- Length 12–128, no composition rules, and a breached-password check via the HIBP k-anonymity API.
- No user enumeration: unknown user and wrong password get the same response and similar timing (hash against a dummy hash).

**Tokens and sessions [M1: access JWT only; H1: everything else]**
- Access token: a JWT. Pin the algorithm on decode, and validate `iss`, `aud`, `exp`, `iat`, `sub`, `jti`. In M1, without refresh tokens, a longer lifetime (~60 min) is an accepted known gap. From H1 it drops to 5–15 minutes.
- Refresh token: opaque random value (`secrets.token_urlsafe`), stored **hashed** (SHA-256), **rotated on every use**. Reusing an already-rotated token revokes the **whole family** and is logged to the audit log.
- Logout, "log out all devices", and a sessions list endpoint (list and revoke individual devices).
- Revoke all sessions on password change.

**Cookies, CSRF, CORS [cookies + CORS from M0/M1; CSRF in H1]**
- Cookies: `__Host-` prefix, `Secure`, `HttpOnly`, `SameSite=Lax`/`Strict`. Scope the refresh cookie path to the refresh endpoint.
- CSRF: signed double-submit token plus a required custom header on all state-changing requests.
- CORS: explicit origin allowlist (the Vite dev origin), `allow_credentials=True`, **never** `*`.
- **Same-site gotcha (F1):** `SameSite` cookies are only sent if the frontend and API are on the *same site*. `wyd.pages.dev` → `wyd-api.onrender.com` is cross-site, and login silently breaks. Fix it with a custom domain (`app.example.com` + `api.example.com`) or a reverse proxy. This is a key lesson.

**HTTP hardening [H1]**
- Security-headers middleware: CSP, HSTS, `X-Content-Type-Options: nosniff`, Referrer-Policy, Permissions-Policy, `frame-ancestors 'none'`.
- `TrustedHostMiddleware`, a request body size limit, and correct client IPs behind the platform proxy (uvicorn `--proxy-headers` / `--forwarded-allow-ips`, needed for rate limiting).
- Disable `/docs` in production once the frontend exists (F1). Until then the live docs *are* the demo.
- Errors: never send stack traces or internal details to the client. Use consistent error response shapes (baseline).

**Input and authorization [baseline, always]**
- Pydantic with `extra="forbid"`, a length limit on every string, and strict types where it makes sense.
- Only the ORM or bound parameters. **Never** build SQL with f-strings.
- **AuthZ in services.** Every resource access checks ownership, membership, or role (IDOR prevention). Blocked users can't DM or see each other's content.
- Negative cases like "user B cannot read user A's conversation" need tests. Before H1, check them by hand and leave a `# TODO(test): …` comment so they're easy to find with grep later.

**Rate limiting and abuse [H1; per-connection limits in M3]**
- Login, register, refresh and 2FA: limit per IP **and** per account, with progressive backoff or temporary lockout.
- Message send rate per WebSocket connection; post and like rate per user.

**WebSockets [M3]**
- Validate the `Origin` header on the handshake (Cross-Site WebSocket Hijacking).
- Authenticate at the handshake (cookie or a single-use short-lived WS ticket from an HTTP endpoint). Never put a JWT in the query string.
- Re-check authorization on every action. When the access token expires, force re-auth.
- Max frame/message size, and a typed Pydantic event envelope (`{"type": ..., "data": ...}`) validated per frame. Unknown event types are rejected.
- Heartbeat (ping/pong) with a timeout, and correct close codes (e.g. 1008 policy violation).

**Uploads (R2) [M4]**
- Private bucket, random object keys (never user-supplied filenames).
- Presigned PUT URLs with content-type and size conditions, and a short expiry.
- Post-upload validation: magic bytes, allowed formats, `Image.MAX_IMAGE_PIXELS` (decompression-bomb guard), and **re-encode with Pillow** to strip EXIF/GPS metadata.
- Serve chat images only to conversation members, through short-lived presigned GET URLs.

**2FA and OAuth [M5]**
- TOTP secret encrypted at rest (AES-GCM or Fernet, key from env). Backup codes are hashed and single-use. Prevent TOTP code replay.
- Step-up auth (password or TOTP) for sensitive actions: change email or password, disable 2FA, delete account.
- OAuth: authorization code flow with `state` + PKCE. Only link accounts on a **verified** provider email.

**Secrets and operations [baseline; scanners in H1; audit log in M6]**
- `.env` is gitignored, and only `.env.example` is committed. Use `SecretStr` for secrets in settings. Production secrets live only in the hosting platform's env vars.
- Until gitleaks arrives in H1: check `git diff --staged` before every commit.
- Log redaction: never log passwords, tokens, cookies, or full emails.
- Audit log for security events.
- `pip-audit`, `bandit`, and a gitleaks pre-commit hook, which also run in CI.

## Roadmap: milestones

Principles:
- **Walking skeleton first.** Deploy something trivial on day 1, then keep `main` deployable. Deploying early surfaces the hard problems (env vars, migrations, CORS, cookies across domains) while the app is still small.
- **Features first, then harden.** Write routes right away. Tooling and test setup come in **H1**, after there's enough code that manual testing hurts. That pain is part of the lesson.
- **Each milestone is a shippable demo.** Milestones are made of small feature branches (`feat/posts-crud`, `feat/likes`, …), not one giant branch.

**Definition of done for every milestone:**
1. All feature branches are merged into `main` via PRs.
2. It's deployed, and smoke-tested on the live URL.
3. The README is updated: what's live, how to try it, and the known security gaps.
4. Claude has reviewed it against the security items tagged for this milestone or earlier.
5. A git tag `vX.Y.0` and a GitHub Release with short notes. This teaches semantic versioning.

### M0: Walking skeleton → `v0.0.1` (aim: 1–2 evenings)
- **Build:** move to `app/main.py`, set up pydantic-settings config + `.env` / `.env.example`, an async SQLAlchemy engine to Neon, `GET /health` that runs `SELECT 1`, and CORS.
- **Deploy:** Render or Railway (check current free tiers and WebSocket support). Auto-deploy from `main` with env vars set in the dashboard, a single uvicorn worker, and Neon branches `main` (prod) and `dev` (local).
- **Learn:** ASGI/uvicorn, 12-factor config, the async engine/session lifecycle, Neon pooled vs. direct connections, and how the platform builds a uv project.
- **Done when:** the public `/health` returns OK, including the DB check.

### M1: Accounts → `v0.1.0` (demo: live Swagger `/docs`)
- **Build:** `User` model + Alembic (first migration; migrations run as a pre-deploy step using the direct Neon URL), register, login, logout, `GET/PATCH /users/me`, and `GET /users/{username}`. Argon2id. An access JWT in an httpOnly cookie, and a `get_current_user` dependency. Basic profile fields: display name, bio, pronouns, accent color, theme.
- **Learn:** Alembic autogenerate (and *reviewing* what it generates), Argon2id, JWT anatomy and validation, cookie flags, dependency injection, Create/Read/Update schemas, layering.
- **Manual testing:** Swagger UI, plus a committed `requests.http` file (VS Code REST Client or the JetBrains HTTP client) that doubles as API documentation.

### M2: Social → `v0.2.0` (demo: live Swagger `/docs`)
- **Build:** posts CRUD, idempotent like/unlike, a keyset-paginated feed, a user's posts, blocking, and a privacy setting for who can see posts.
- **Learn:** relationships, N+1 queries and eager loading, keyset pagination, unique constraints and race conditions, authorization/IDOR in services, counting likes (a denormalized counter vs. `COUNT(*)`).

### H1: Hardening and safety net → `v0.3.0` (no new features)
Now that ~15 endpoints exist, manual re-testing hurts. That's the motivation. Do it in this order:
1. **Tooling:** ruff config, mypy (strict, fixing existing code), and pre-commit with gitleaks.
2. **Tests:** pytest + Docker Postgres. Turn every `TODO(test)` into a real test, including authz-negative and validation-negative tests.
3. **Auth hardening:**
   - refresh token rotation with reuse detection, access token cut to 5–15 min
   - a sessions list and "log out all devices"
   - CSRF
   - rate limiting with backoff on auth endpoints, plus correct client IPs behind the proxy
   - security headers, TrustedHost, and a body size limit
   - the HIBP breached-password check
4. **CI:** a GitHub Actions workflow on every PR (ruff, mypy, pytest, pip-audit, bandit), and branch protection on `main` that requires it to pass.
- **Why here:** WebSockets (M3) build on the *final* token design, so auth must be finished first.
- **Done when:** CI is green, the security regression tests exist, and the "Known security gaps" list in the README has shrunk.

### F1: Frontend foundation → `v0.4.0` (demo: a real UI)
- **Build:** start `wyd-frontend/` (React + Vite + TS; write its own CLAUDE.md first) with login/register, profile, feed, posting, and likes. It calls the API with `credentials: "include"` and sends the CSRF header. Deploy it as a static site.
- **Key lesson:** the **same-site cookie problem** (see Security → Cookies). Pick a custom domain (recommended; ~$10/yr) or a reverse proxy *before* debugging why login "doesn't work".
- After F1, disable `/docs` in production.

### M3: Realtime DMs → `v0.5.0` (demo: two browsers chatting live)
- **Backend:** direct conversations, messages, a WS endpoint (handshake auth + Origin check), an in-memory connection manager, persist-then-broadcast, history pagination, reconnect and resync, and per-connection rate limits. Write WS tests, including security tests.
- **Frontend:** a chat UI.
- **Learn:** the WebSocket protocol, event envelope design, CSWSH, asyncio concurrency, and why one worker is required for now.

### M4: Groups and media → `v1.0.0` 🎉 MVP / portfolio launch
- **Build:** group chats (create, invite, kick, leave), roles and permissions, chat customization (name, icon, theme, emoji, per-member nicknames), message edit and soft delete. The R2 media pipeline for avatars, banners, post images and chat images.
- **Learn:** RBAC, presigned URLs, upload attacks, image processing.
- **Launch:** a polished README with an architecture diagram, screenshots, a security write-up (what you implemented and why), a demo account, and seed data.

### Post-MVP (order is flexible; pick what interests you)
- **M5: Advanced auth:** TOTP 2FA + backup codes + step-up auth; OAuth with GitHub and Google.
- **M6: Polish and observability:** typing indicators, read receipts, unread counts, presence, notifications; structlog JSON logs, request IDs, OpenTelemetry, audit log; a multi-stage non-root Dockerfile.
- **M7: Scale:** run 2 workers, watch chat and rate limiting break *on purpose*, then fix them with Redis pub/sub and Redis-backed rate limits.

## Testing conventions (from H1)

Before H1, test by hand with Swagger and `requests.http`, and mark test ideas with `# TODO(test): …`. Claude shouldn't push test setup before H1, but should suggest `TODO(test)` notes for important cases (especially security negatives).

- `pytest` + `pytest-asyncio`, with httpx `AsyncClient` over the ASGI transport against Docker Postgres, and a transaction rollback per test.
- Every endpoint gets at least a happy-path test, an **authz-negative** test (wrong user or not logged in), and a **validation-negative** test.
- WebSocket tests use Starlette's `TestClient.websocket_connect`.
- **Security regression tests are mandatory:** refresh token reuse, missing or invalid CSRF, IDOR, bad `Origin` on WS, rate limit triggers, and oversized uploads.
- Never run tests against the Neon database.

## Teaching reminders for Claude

- **At the start of a milestone or feature:** name the concepts to learn, link the docs to read, and remind the user to create a branch (suggest a name). Keep the setup minimal: only what this milestone needs.
- **During work:** answer with explanations and hints. Ask what the user thinks before revealing the solution.
- **At a checkpoint:** remind the user to commit and suggest a Conventional Commit message.
- **At the end of a feature branch:** remind the user to open a PR, self-review the diff, and merge into `main`.
- **At the end of a milestone:** walk through the definition of done: deploy, smoke-test live, README, a security review against the items tagged for this milestone, then tag + GitHub Release.
- **Scope creep:** if the user starts pulling in a later milestone's work, point it out and ask whether it's worth doing now. Shipping the current demo comes first.
