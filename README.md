# David AI — Backend

**David is the orchestrator, not the model.**

This is the backend for David AI: a modular personal AI platform that stores
memory, manages projects/tasks, enforces permissions, and routes chat
requests across multiple AI providers (Gemini, Groq, Hugging Face,
OpenRouter, Cerebras, SambaNova) with automatic fallback.

This build implements **v0.7 (Foundation)** and **v0.8 (AI Integration
Layer)** in full, plus stable scaffolding/placeholders for v0.9–v1.4 so the
codebase can grow without a rewrite (research/web fetch, voice, vision,
plugins, dashboard, uploads, auth).

---

## 1. Quick start (local, no Docker)

```bash
cd David
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit .env and add your API keys
uvicorn main:app --reload
```

Visit:
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8000/dashboard
- Health check: http://localhost:8000/api/health

David works even with **zero API keys configured** — it just returns a
graceful "no provider available" message instead of crashing. Add keys to
`.env` as you get them and the router will start using them automatically.

## 2. Quick start (Docker)

```bash
cp .env.example .env            # add your API keys
docker compose up --build
```

The app will be available on `http://localhost:8000`.

## 3. Running tests

```bash
pip install -r requirements.txt
pytest
```

Tests cover: health/status, memory add+search, projects/tasks lifecycle,
auth register/login/me, permission checks, plugin execution, and router
fallback behavior (must never crash even with no provider keys).

## 4. Project layout

```
David/
├── main.py                 # FastAPI app, mounts every route group
├── data/                   # JSON-backed storage (auto-created)
├── logs/                   # david.log (secrets are auto-redacted)
├── uploads/                # uploaded files land here
├── tests/                  # pytest suite
└── david/
    ├── api/                 # one routes_*.py file per endpoint group
    ├── core/david.py        # the orchestrator (handle_chat)
    ├── router/               # AIRouter, metrics, cache
    ├── providers/            # one file per AI provider, common interface
    ├── memory/               # MemoryEngine (search/add/forget)
    ├── planning/             # projects, tasks, learning, decisions
    ├── security/              # auth (JWT+bcrypt), permissions engine
    ├── database/               # JSONStore (active) + SQLAlchemy models (future)
    ├── plugins/                 # plugin manager + builtin plugins
    ├── tools/                    # tool manager (permission-aware)
    ├── web/research.py            # URL fetch + summarizable text extraction
    ├── voice/, vision/             # stable interfaces, stubbed pending v1.0/v1.1
    ├── config/settings.py           # loads .env once, exposes get_settings()
    └── utils/                        # logger (redacts secrets), helpers
```

## 5. How the request flow works (Section 5)

1. `POST /api/chat` receives a message.
2. `MemoryEngine.search()` pulls relevant context for that user.
3. `AIRouter.chat()` picks the best available provider (by priority, health,
   or task type in `smart` mode) and tries it.
4. If that provider fails or has no key, the router automatically tries the
   next one in `PROVIDER_PRIORITY`, and the next, until one succeeds or all
   are exhausted (in which case it returns a graceful error — never a crash).
5. The exchange is written back into memory.
6. One unified reply is returned. The caller never knows which provider
   answered.

## 6. Adding a new AI provider

1. Create `david/providers/yourprovider.py`, subclassing `BaseProvider`
   (see `david/providers/base.py`) and implementing `chat()`.
2. Register it in `AIRouter.__init__` in `david/router/ai_router.py`.
3. Add its API key + model env vars to `.env.example` and `config/settings.py`.
4. Add it to `PROVIDER_PRIORITY` in `.env` in whatever order you want it tried.

## 7. Environment variables

See `.env.example` for the full list. Nothing sensitive is ever hard-coded
in source, logged, or returned by any endpoint.

## 8. What's stubbed vs fully built

| Area | Status |
|---|---|
| Memory / Projects / Tasks / Learning / Decisions | ✅ Fully built (v0.7) |
| Auth (register/login/JWT) | ✅ Fully built (v0.7) |
| Permissions engine | ✅ Fully built (v0.7) |
| AI Router + 6 providers + fallback + metrics + cache | ✅ Fully built (v0.8) |
| Uploads | ✅ Fully built (v0.7/v0.9 groundwork) |
| Research (URL fetch + extraction) | ✅ Fetch works; `web_search` is a stub — plug in a search API key |
| Plugins (calculator, notes) + plugin manager | ✅ Fully built, easy to extend |
| Dashboard | ✅ Minimal working dashboard (chat + live provider health) |
| Voice (STT/TTS) | 🧩 Interface stubbed, returns "not implemented yet" (v1.0) |
| Vision (image analysis) | 🧩 Interface stubbed, returns "not implemented yet" (v1.1+) |
| SQL database | 🧩 SQLAlchemy models defined in `database/models.py`, not wired in yet (JSONStore is active) |

## 9. Next steps (Section 37 build order)

1. Add real API keys and live-test each provider.
2. Implement `web_search` in `david/web/research.py` with a real search API.
3. Wire STT/TTS (`david/voice/voice_engine.py`) to a real provider.
4. Wire vision analysis (`david/vision/vision_engine.py`) to a vision-capable model.
5. Add streaming responses to the router + `/api/chat`.
6. Migrate JSONStore-backed collections to the SQLAlchemy models when scale requires it.
7. Add rate limiting + audit logs.
8. Expand the dashboard (project/task boards, usage charts, settings/logs pages).


## Workspace privacy
When a user logs in, David scopes memory, projects, tasks, uploads, notes, and exports to that user only.


## Private single-user mode

This build is configured for one owner only:
`sebiomoa231@gmail.com`

Registration and login are restricted to the owner email.

## Capabilities

See `/api/capabilities` for the capability registry and future-suite roadmap.
