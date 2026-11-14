# WYD

A live chat and social app: user accounts, posts and likes, 1:1 and group chats, image sharing, and lots of profile and chat customization.

This is a learning and portfolio project with a strong focus on security. It's built in small milestones, and every milestone ends deployed and tagged.

**Live API:** https://wyd-chat.up.railway.app · [Swagger UI](https://wyd-chat.up.railway.app/docs)

## Repository layout

| Folder | What it is | Status |
|---|---|---|
| [`wyd-backend/`](wyd-backend/README.md) | FastAPI + SQLAlchemy (async) + PostgreSQL on Neon | M1 accounts ✅ (`v0.1.0`), M2 next |
| `wyd-frontend/` | React + Vite + TypeScript SPA | starts at milestone F1 |

Setup, design notes and the list of known security gaps are in the [backend README](wyd-backend/README.md).

## Roadmap

| Milestone | Tag | Demo |
|---|---|---|
| **M0 Walking skeleton** ✅ | v0.0.1 | live `/health` |
| **M1 Accounts** ✅ | v0.1.0 | live Swagger `/docs` |
| M2 Social: posts, likes, feed, blocking | v0.2.0 | live Swagger `/docs` |
| H1 Hardening: tests, CI, refresh rotation, CSRF, rate limits | v0.3.0 | green CI, security write-up |
| F1 Frontend foundation | v0.4.0 | real UI |
| M3 Realtime DMs over WebSockets | v0.5.0 | two browsers chatting |
| M4 Group chats + image uploads | v1.0.0 | MVP |

## Workflow

GitHub Flow (short-lived branches merged through PRs) and [Conventional Commits](https://www.conventionalcommits.org/).
