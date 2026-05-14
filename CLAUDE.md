# CLAUDE.md — Developer Reference

Developer-focused guide for Jobseeker AI. Covers architecture decisions, conventions, common tasks, and service-specific notes for the root project, backend (orchestrator), and frontend (Streamlit).

---

## Repository Layout

```
Jobseeker/
├── config/settings.py           # Single source of truth for all env-driven config
├── services/                    # Backend — FastAPI + Celery + all service modules
│   ├── api/                     # HTTP layer
│   ├── scraper/                 # Playwright scrapers + ingest + metadata
│   ├── embeddings/              # Sentence-transformer singleton
│   ├── qdrant/                  # Vector DB client + collection management
│   ├── matching/                # Cosine search + hard-filter engine
│   ├── rewrite/                 # vLLM rewrite + Outlines FSM
│   ├── resume/                  # Parser + Pydantic schema
│   ├── tasks/                   # Celery tasks
│   └── automation/              # Playwright submitter + DOM mapper + PDF gen
├── frontend/                    # Streamlit dashboard
│   ├── app.py                   # Multi-page entry point
│   ├── api_client.py            # HTTP helpers (api_get / api_post / api_delete)
│   └── pages/                   # One file per dashboard page
├── tests/                       # pytest — 4-tier structure
├── docker-compose.yml
├── Dockerfile.orchestrator      # python:3.13-slim — FastAPI + Celery + Playwright
├── Dockerfile.streamlit         # python:3.13-slim — Streamlit only
├── requirements.txt             # Orchestrator + Celery worker deps
├── requirements.streamlit.txt   # Streamlit-only deps
├── requirements.test.txt        # pytest + plugins (local dev only)
├── pytest.ini                   # [tool:pytest] — coverage ≥77%, asyncio session scope
└── .env.example                 # Canonical env-var reference
```

---

## Root — Configuration & Infrastructure

### Settings (`config/settings.py`)

- Uses `pydantic-settings` `BaseSettings` with `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`.
- All env vars map 1:1 to field names (case-insensitive). Add new config here — **never** hardcode values in service code.
- `@property` methods derive computed URLs: `vllm_base_url`, `qdrant_url`, `celery_broker_url`, `celery_result_backend`, `allowed_origins_list`.
- Import: `from config.settings import settings` (singleton at module level).

### Environment Variables (`.env`)

Critical production variables — run `make check-secrets` before deploying:

| Variable | Purpose |
|---|---|
| `API_KEY` | Shared secret for `X-API-Key` header auth |
| `REDIS_PASSWORD` | Redis AUTH password |
| `QDRANT_API_KEY` | Qdrant REST API key |
| `API_DEBUG` | `true` enables `/docs`, `/redoc`, `/openapi.json` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins; blank = deny all |

Generate secrets: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### Docker / Compose

- Both images: `python:3.13-slim`.
- `orchestrator` and `celery-worker` require GPU reservation (NVIDIA runtime). Check `docker-compose.yml` `deploy.resources.reservations`.
- First `make up` pulls `vllm/vllm-openai:v0.20.2` (~5 GB) and downloads Foundation-Sec-8B AWQ (~5 GB). Allow 15–30 min.
- `make reset-db` wipes **all** Qdrant data. Use with care.

### Makefile Targets

| Target | Action |
|---|---|
| `make up` | `docker compose build && docker compose up -d` |
| `make down` | Stop all services |
| `make logs` / `make logs-vllm` | Tail all / vLLM-only logs |
| `make status` | `docker compose ps` health overview |
| `make init-db` | Run `services/qdrant/init_collections.py` |
| `make reset-db` | Wipe and recreate Qdrant collections |
| `make clean` | Remove containers, volumes, build cache |
| `make check-secrets` | Fail if placeholder secrets are detected |

---

## Backend — Orchestrator (`services/`)

### FastAPI App (`services/api/main.py`)

Middleware stack (applied in registration order, outermost first at request time):

1. `RateLimitMiddleware` — sliding-window IP-level rate limiting per route
2. `SecurityHeadersMiddleware` — security headers on every response
3. `CORSMiddleware` — restricted to `settings.allowed_origins_list`

All routes are protected by the `get_api_key` dependency (`services/api/security.py`). Routes import it as:
```python
from services.api.security import get_api_key
# ...
@router.post("/endpoint", dependencies=[Depends(get_api_key)])
```

Swagger/ReDoc UI is only mounted when `settings.api_debug is True`.

### Input Validation (`services/api/validators.py`)

Always use these helpers — never validate in route handlers inline:

```python
from services.api.validators import (
    validate_job_url_http,   # SSRF guard — call before any Playwright navigation
    check_upload_size,       # Call immediately after file.read()
    sanitize_filename,       # Call on any user-supplied filename
    validate_uuid,           # Call on UUID path params
)
```

`validate_job_url()` resolves DNS and blocks RFC-1918, loopback, link-local, and CGNAT ranges. Use `validate_job_url_http()` in routes (raises HTTP 422), `validate_job_url()` in Pydantic validators (raises `ValueError`).

### Qdrant Client (`services/qdrant/init_collections.py`)

- `get_qdrant_client()` returns a module-level singleton protected by `threading.Lock`. Safe under concurrent Celery workers.
- Always use `client.retrieve(ids=[id], with_payload=True)` for single-point lookups — O(1). Never use `scroll` for ID-based retrieval.
- Delete uses `PointIdsList(points=[id])`. Do **not** wrap in `PointsSelector` (it is a type alias).
- After `reset_collections()`, the singleton is cleared so the next call creates a fresh client.

### Scraper (`services/scraper/scraper.py`)

Two-pass architecture:
1. **Pass 1** — Playwright navigates the job board listing page, collects card metadata (title, company, location, source) and the raw `href` job-detail URL.
2. **Pass 2** — `asyncio.gather` concurrently calls `_fetch_description_markdown(context, url, selectors)` for every collected URL, using board-specific CSS selectors with `<body>` fallback.

Key helpers:
- `_html_to_markdown(html)` — strips `<script>`/`<style>` via `soup.decompose()`, converts with `markdownify(heading_style="ATX")`, collapses blank lines, truncates to `settings.max_description_length`. Pure function; unit-tested without Playwright.
- `_fetch_description_markdown(context, url, selectors)` — always closes the page in a `finally` block; returns `""` on any error (never raises).
- `_apply_stealth(page)` — wraps `Stealth().apply_stealth_async(page)` from playwright-stealth ≥2.0; skips silently if not installed.

CSS selectors by board:
- Indeed: `["#jobDescriptionText", ".jobsearch-JobComponent-description"]`
- LinkedIn: `[".description__text", ".jobs-description__content"]`
- Dice: `["[data-cy='jobDescriptionHtml']", "#jobdescSec", ".job-description"]`

### Rewriter (`services/rewrite/rewriter.py`)

- `_call_vllm()` raises `RuntimeError` immediately on any `json.JSONDecodeError` or Pydantic `ValidationError`. No fallback path exists.
- `rewrite_resume_for_job(job_id, resume_id, match_score=None)` — pass `match_score` from the match step to skip the redundant embedding round-trip.

### Outlines Constraint (`services/rewrite/outlines_constraint.py`)

- `validate_schema_self_contained(schema)` — call this before every vLLM request. Raises `ValueError` for dangling `$ref` or non-local references.
- `build_json_schema_description(schema)` — generates an inline plain-text description of the full schema (including nested `TailoredExperience` / `TailoredBullet` fields) for the LLM system prompt.
- `apply_outlines_constraint_to_request(request, schema)` — validates self-containment, then sets `extra_body={"guided_json": schema}`.

### Celery Tasks (`services/tasks/`)

| Module | Task | Trigger |
|---|---|---|
| `scrape_task.py` | `run_scrape_and_ingest` | Periodic (every `SCRAPER_SCHEDULE_HOURS` h) |
| `submit_task.py` | `submit_application` | API call to `POST /api/submit/apply` |
| `match_task.py` | `batch_match_new_jobs` | Auto-dispatched after every `ingest_job_batch()` |

`MaxRetriesExceededError` is caught before the generic `Exception` handler in `scrape_task.py` to avoid an infinite retry loop.

---

## Frontend — Streamlit (`frontend/`)

### API Client (`frontend/api_client.py`)

Three helpers wrap all HTTP communication:
```python
api_get(path)               # GET /api/{path}
api_post(path, data)        # POST /api/{path} with JSON body
api_delete(path)            # DELETE /api/{path}
```

All helpers attach `X-API-Key: {API_KEY}` if the env var is set. They raise `st.error()` and return `None` on failure — callers must check for `None`.

### Page Conventions

- Each page lives in `frontend/pages/` as a standalone Python file.
- Session state keys: `current_resume_id`, `rewrite_job_title`, `rewrite_company`, `match_results`.
- The `review_approve.py` page reads `st.session_state["current_resume_id"]` — this must be set by `staged_apps.py` before navigating to it.

---

## Testing

### Running Tests

```bash
pip install -r requirements.test.txt
python -m pytest tests/                  # full suite, coverage report
python -m pytest tests/tier1_critical/  # pure unit tests — fast, no mocks needed
python -m pytest tests/ -k "security"   # filter by name
python -m pytest tests/ --no-cov -q    # fast run without coverage
```

### Tier Responsibilities

| Tier | What it tests | Mock strategy |
|---|---|---|
| `tier1_critical` | Pure functions, schemas, validators | None (no external deps) |
| `tier2_services` | Service logic | Qdrant, embeddings, vLLM mocked via `conftest.py` fixtures |
| `tier3_api` | FastAPI routes | Full ASGI with `httpx.AsyncClient(transport=ASGITransport)` |
| `tier4_wiring` | End-to-end pipeline call chain | All external services mocked; tests pipeline plumbing, not data |

### Fixtures (`tests/conftest.py`)

| Fixture | Provides |
|---|---|
| `mock_qdrant_client` | `MagicMock` with `retrieve`, `upsert`, `search`, `delete` pre-wired |
| `mock_embedding` | `MagicMock` encoding returning `[0.1] * 1024` |
| `mock_vllm_client` | `MagicMock` for `openai.OpenAI` |
| `test_app` | `httpx.AsyncClient` with `ASGITransport(app=app)` |
| `sample_job` / `sample_resume` | Pre-built `dict` payloads |

`pytest_configure` also:
- Mocks `sentence_transformers.SentenceTransformer` to prevent CUDA init at collection time.
- Filters `reportlab` and `bs4/lxml` third-party `DeprecationWarning`s.

### Async Tests

Use `@pytest.mark.asyncio` on every `async def test_*`. The `[tool:pytest]` section in `pytest.ini` sets `asyncio_mode = auto` for CI (Docker-based test runner), but the local `pytest-asyncio==0.24.0` requires explicit decorators.

### Adding New Tests

1. Place pure-function tests in `tier1_critical/`.
2. Place service tests that need the shared fixtures in `tier2_services/`.
3. Place route tests in `tier3_api/` — use `test_app` fixture.
4. Do **not** lower the `--cov-fail-under=77` threshold without a corresponding discussion.

---

## Conventions

### Error Handling

- Routes catch `HTTPException` first (re-raise), then `Exception` (log + return generic `"Internal server error"`). Never leak stack traces or internal messages to HTTP responses.
- Service layer raises domain exceptions (`ValueError`, `RuntimeError`) — routes translate these to `HTTPException`.

### Logging

`loguru` is used throughout. Import: `from loguru import logger`. Use `logger.critical()` for FSM violations, `logger.error()` for recoverable service errors, `logger.warning()` for degraded-mode notices.

### Typing

- All function signatures have return type annotations.
- Pydantic models use `Field(max_length=…)` for string inputs received from the network.
- Use `str | None` union syntax (Python 3.10+), not `Optional[str]`.

### Dependency Pinning

All three requirements files are fully pinned (no `>=` or `~=`). When bumping a package:
1. Update the version in the relevant requirements file.
2. Run `python -m pytest tests/` to confirm no regressions.
3. Update `CHANGELOG.md` under the appropriate version section.
