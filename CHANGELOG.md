# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.0.3-beta] - 2026-05-14

### Added

#### Security Hardening

- **`services/api/security.py`** — New `get_api_key` FastAPI dependency. When `API_KEY` is set in `.env`, every protected endpoint validates the `X-API-Key` request header; returns HTTP 401 on mismatch. No-ops in dev mode (`API_KEY` empty) with a startup `CRITICAL` warning.
- **`services/api/main.py`** — `SecurityHeadersMiddleware`: attaches `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Cache-Control: no-store` to every response.
- **`services/api/main.py`** — `RateLimitMiddleware`: in-process sliding-window rate limiter keyed by `(client IP, method, path)`. Per-route limits: tailor (10/min), submit (5/min), resume upload (30/min), job ingest (60/min), batch ingest (10/min), file ingest (20/min). Returns HTTP 429 with `Retry-After` header when exceeded.
- **`services/api/validators.py`** — Four input-validation helpers used across all routes:
  - `validate_job_url()` — SSRF guard: rejects non-HTTP/S schemes and URLs resolving to RFC-1918/loopback/link-local/CGNAT addresses.
  - `validate_job_url_http()` — HTTP 422-raising wrapper for use outside Pydantic validators.
  - `check_upload_size()` — Raises HTTP 413 when uploaded content exceeds `MAX_UPLOAD_BYTES`.
  - `sanitize_filename()` — Strips directory separators and null bytes; limits to 255 chars.
  - `validate_uuid()` — Raises HTTP 422 for malformed UUID path parameters.
- **`services/api/main.py`** — Swagger UI / ReDoc / OpenAPI JSON gated behind `API_DEBUG=true`; disabled by default in production.
- **`services/api/main.py`** — CORS tightened: `allow_origins` from `settings.allowed_origins_list` (empty = deny all cross-origin), `allow_credentials=False`, methods restricted to `GET, POST, DELETE`, headers restricted to `X-API-Key, Content-Type`.
- **`Makefile`** — `check-secrets` target verifies `API_KEY`, `REDIS_PASSWORD`, and `QDRANT_API_KEY` are not placeholder values before a production deploy.
- **`.env.example`** — New `[Security]` block: `API_KEY`, `API_DEBUG`, `ALLOWED_ORIGINS`, `REDIS_PASSWORD`, `QDRANT_API_KEY`; new `[Upload / Validation Limits]` block: `MAX_UPLOAD_BYTES`, `MAX_DESCRIPTION_LENGTH`, `MAX_BATCH_SIZE`.
- **`services/api/routes/jobs.py`** — `JobIngestRequest` fields annotated with `Field(max_length=…)` limits; `check_upload_size` and `sanitize_filename` applied to file-upload endpoint; description truncated to `MAX_DESCRIPTION_LENGTH`; error details no longer leak internal exception strings (returns `"Internal server error"`).
- **`services/api/routes/resumes.py`**, **`match.py`**, **`rewrite.py`**, **`submit.py`** — `get_api_key` dependency added to all routes; `validate_uuid` applied to path parameters; `check_upload_size` applied to file uploads; internal exception messages hidden from HTTP responses.

#### FSM / Zero-Retry JSON Hardening

- **`services/rewrite/outlines_constraint.py`** — `validate_schema_self_contained(schema: dict) -> None`: walks every `$ref` in the schema and raises `ValueError` if any reference is not a local `#/$defs/…` pointer or if the target name is absent from `schema["$defs"]`. Pre-flight guard called before every vLLM request.
- **`services/rewrite/outlines_constraint.py`** — `build_json_schema_description()` now resolves `$ref` entries against `$defs` recursively and inlines the `TailoredExperience` and `TailoredBullet` field names into the prompt hint (previously rendered as `[/* array of objects */]`).

#### Scraper — Full Job Description Pipeline

- **`services/scraper/scraper.py`** — `_html_to_markdown(html)`: pure helper that strips `<script>`/`<style>` via BeautifulSoup `decompose()`, converts remaining HTML to ATX-style Markdown with `markdownify`, collapses runs of 3+ blank lines, and truncates to `settings.max_description_length`.
- **`services/scraper/scraper.py`** — `_fetch_description_markdown(context, url, selectors)`: async helper that opens a new browser tab in the existing Playwright context, navigates to the job detail URL, tries board-specific CSS selectors in order (`#jobDescriptionText`, `.description__text`, `[data-cy="jobDescriptionHtml"]`, etc.) with `<body>` fallback, converts HTML to Markdown, and closes the tab. Returns `""` on any failure — never raises.
- **`services/scraper/scraper.py`** — All three scrapers (`scrape_indeed`, `scrape_linkedin`, `scrape_dice`) updated to **two-pass** design: Pass 1 collects card metadata and **real job URLs** from anchor `href` attributes; Pass 2 concurrently fetches all detail pages via `asyncio.gather`, then merges full Markdown descriptions back into each job record. Eliminates the `f"{title} at {company}"` stub that broke metadata extraction, embedding quality, and LLM rewriting.
- **`requirements.txt`** — `markdownify==1.2.2` restored to the Web Scraping section (alongside `beautifulsoup4` and `lxml` which were already present).

### Fixed

#### FSM / Zero-Retry JSON Hardening

- **`services/rewrite/rewriter.py`** — Removed `_extract_json_fallback()`. Any `json.JSONDecodeError` or Pydantic `ValidationError` after the guided-decoding call now raises `RuntimeError("Outlines FSM constraint violated …")` immediately with `logger.critical()`. Degraded / empty `RewriteOutput` objects can no longer be silently delivered to the Playwright submitter.
- **`services/rewrite/outlines_constraint.py`** — `apply_outlines_constraint_to_request()` now calls `validate_schema_self_contained()` before attaching the schema to `extra_body`; a broken schema with dangling `$ref` entries raises `ValueError` before reaching vLLM.

#### playwright-stealth v2.0 API

- **`services/scraper/scraper.py`** — `stealth_async(page)` replaced by `Stealth().apply_stealth_async(page)` (playwright-stealth ≥2.0 API).
- **`services/automation/submitter.py`** — `stealth_sync(page)` replaced by `Stealth().apply_stealth_sync(page)`.

#### Test Warning Cleanup

- **`tests/conftest.py`** — `config.addinivalue_line("filterwarnings", …)` in `pytest_configure` suppresses the `reportlab` `ast.NameConstant` and `bs4/lxml` `strip_cdata` third-party `DeprecationWarning`s. Test suite now reports **zero warnings**.
- **`config/settings.py`** — `class Config:` replaced with `model_config = SettingsConfigDict(…)` (Pydantic v2 convention); eliminates `PydanticDeprecatedSince20` warning on every import.

### Changed

#### Dependency Version Sweep — all packages updated to latest stable

- **`requirements.txt`** — 22 packages bumped: `fastapi==0.136.1`, `uvicorn==0.46.0`, `pydantic==2.13.4`, `pydantic-settings==2.14.1`, `httpx==0.28.1`, `openai==2.36.0`, `transformers==5.8.1`, `sentence-transformers==5.5.0`, `torch==2.12.0`, `qdrant-client==1.18.0`, `celery==5.6.3`, `redis==7.4.0`, `PyMuPDF==1.27.2.3`, `python-docx==1.2.0`, `playwright==1.59.0`, `playwright-stealth==2.0.3`, `beautifulsoup4==4.14.3`, `lxml==6.1.0`, `reportlab==4.5.1`, `jinja2==3.1.6`, `tenacity==9.1.4`, `loguru==0.7.3`. `outlines` confirmed correctly absent (FSM runs server-side inside vLLM container).
- **`requirements.test.txt`** — `pytest==9.0.3`, `pytest-asyncio==1.3.0`, `pytest-cov==7.1.0`, `pytest-mock==3.15.1`, `jsonschema==4.26.0`.
- **`requirements.streamlit.txt`** — `streamlit==1.57.0`, `diff-match-patch==20241021`, `pydantic==2.13.4`.
- **`Dockerfile.orchestrator`**, **`Dockerfile.streamlit`** — Base image updated `python:3.12-slim` → `python:3.13-slim`.
- **`docker-compose.yml`** — `vllm/vllm-openai:v0.6.6` → `v0.20.2`; `qdrant/qdrant:v1.12.4` → `v1.18.0`; `redis:7.4-alpine` → `redis:8.6.3-alpine`.
- **`config/settings.py`** — Migrated from deprecated `class Config:` inner class to `model_config = SettingsConfigDict(env_file=…, env_file_encoding=…, extra="ignore")` at the top of the `Settings` class body. Import changed from `pydantic.ConfigDict` to `pydantic_settings.SettingsConfigDict`.
- **`pytest.ini`** — `asyncio_default_fixture_loop_scope = session` added.

### Tests

- **`tests/tier1_critical/test_security_validators.py`** — New test file covering all four validator helpers: SSRF blocking (private IPs, loopback, schemes), `check_upload_size`, `sanitize_filename`, `validate_uuid`.
- **`tests/tier3_api/test_api_auth.py`** — New test file: `401` on wrong key, `401` on missing key, `200` on correct key, dev-mode bypass when `API_KEY` is empty.
- **`tests/tier2_services/test_scraper.py`** — New 24-test file across three classes:
  - `TestHtmlToMarkdown` (11 tests) — pure conversion: script/style stripping, ATX headings, blank-line collapse, truncation, keyword preservation.
  - `TestFetchDescriptionMarkdown` (9 async tests) — mocked Playwright: selector matching, body fallback, navigation failure resilience, page-always-closed guarantee.
  - `TestDescriptionPipelineIntegration` (4 tests) — cert/clearance/skill keywords survive HTML→Markdown→`extract_all_metadata()` round-trip; stub regression guard.
- **`tests/tier2_services/test_settings.py`** — New tests confirming `SettingsConfigDict` migration: `model_config` is a `SettingsConfigDict` instance, `env_file` and `extra` are correctly set, no `PydanticDeprecatedSince20` warning raised on import.
- **`tests/tier1_critical/test_outlines_constraint.py`** — New `TestSchemaValidity` class (7 tests): Draft 7 schema check, all `$ref`s resolve, self-containment guard, instance validation, invalid-structure rejection, dangling-ref and non-local-ref error paths.
- **`tests/tier1_critical/test_outlines_constraint.py`** — `TestGetJsonSchemaForPrompt`: `test_prompt_description_shows_nested_experience_fields` asserts `title`, `company`, `bullets`, `original`, `tailored` appear in the prompt hint.
- **`tests/tier2_services/test_rewriter.py`** — `TestExtractJsonFallback` replaced by `TestCallVLLMConstraintViolation`; `test_call_vllm_json_fallback` → `test_call_vllm_raises_on_malformed_content`.
- **Total**: 362 → **386 tests**, zero warnings.

### Removed

- **`requirements.txt`** — `outlines` package: confirmed not a direct orchestrator dependency (FSM compilation runs inside the vLLM container). Removing eliminates a phantom dependency.

---

## [0.0.2-beta] - 2026-05-13

### Added

- **`services/tasks/match_task.py`** — New `batch_match_new_jobs` Celery task that runs the full matching pipeline for a list of job IDs against all stored resumes; automatically dispatched by `ingest_job_batch()` after every scrape cycle or batch API ingest.
- **`frontend/api_client.py`** — `api_delete()` helper for HTTP DELETE requests; mirrors the existing `api_get()` / `api_post()` pattern.
- **`services/api/routes/submit.py`** — Submission history now persisted to a Redis list (`jobseeker:submissions`, capped at 200 entries); `GET /api/submit/history` reads the list and enriches each record with live Celery task state and result metadata.
- **`frontend/pages/application_history.py`** — Replaced stub placeholder with a real table UI: status icons (`🟡` queued / `🔵` started / `🟢` submitted / `🔴` failed), per-row error expandable, Refresh button.
- **`services/scraper/scraper.py`** — `_apply_stealth(page)` async helper applies `playwright-stealth` to every new page in all three scrapers (Indeed, LinkedIn, Dice); controlled by `settings.playwright_stealth_enabled`; silently skips if package is not installed.
- **`services/automation/submitter.py`** — `_apply_stealth_sync(page)` sync helper applies `playwright-stealth` to the form-submission browser page.
- **`services/api/routes/submit.py`** — `SubmitRequest` extended with optional `job_title` and `company` fields for richer history records.

### Fixed

#### Critical Runtime Bugs

- **A1 — `services/qdrant/init_collections.py`** — `get_qdrant_client()` now enforces a module-level singleton protected by `threading.Lock`; prevents connection pool exhaustion under concurrent Celery workers. Singleton is reset after `reset_collections()` so the next call creates a fresh client.
- **A2 — `services/api/routes/jobs.py`** — `GET /api/jobs/{job_id}` replaced a `scroll(limit=1, filter=…)` loop with `client.retrieve(ids=[job_id])`; fixes incorrect `None` response when the UUID prefix filter produced no match.
- **A3 — `services/api/routes/jobs.py`** — `DELETE /api/jobs/{job_id}` path parameter type corrected from `int` to `str` (Qdrant uses UUID strings); deletion selector changed from a raw list to `PointIdsList(points=[job_id])`.
- **A4 — `services/api/routes/resumes.py`** — `DELETE /api/resumes/{resume_id}` fixed identically to A3; also removed the incorrectly nested `PointsSelector(points=PointIdsList(…))` wrapper — `PointsSelector` is a `Union` alias and cannot be instantiated directly.
- **A5 — `frontend/pages/review_approve.py`** — `resume_id` in the submission payload was hardcoded as `"from_session"`; now reads `st.session_state.get("current_resume_id", "")`.
- **A6 — `frontend/pages/my_resumes.py`** — Delete resume button called `api_get()` (wrong HTTP method); now correctly calls `api_delete()`.
- **A7 — `services/scraper/metadata_extractor.py`** — `extract_all_metadata()` returned `clearance_level: None` when no clearance was found; Qdrant rejects `None` in payload indexes. Now normalizes to `""` (empty string).
- **A8 — `docker-compose.yml`** — `orchestrator` and `celery-worker` services were missing NVIDIA runtime and GPU device reservations; the embedding model (`EMBEDDING_DEVICE=cuda`) would crash at startup without them.

#### Logic / Correctness Bugs

- **B1 — `services/matching/matcher.py`** — `_get_resume_payload()` replaced an O(N) `scroll`-and-loop over the entire collection with `client.retrieve(ids=[resume_id], with_payload=True)`.
- **B2 — `services/rewrite/rewriter.py`** — `_fetch_job_and_resume()` replaced two O(N) scroll calls with two `client.retrieve()` calls; raises `ValueError("Job not found")` / `ValueError("Resume not found")` correctly for missing IDs.
- **B3 — `services/rewrite/rewriter.py`** — `rewrite_resume_for_job()` accepts an optional `match_score: float | None` parameter; when provided, the function skips the redundant `match_jobs_to_resume()` vector search, saving one full embedding round-trip per tailor action.
- **B4 — `services/automation/dom_mapper.py`** — `build_field_mapping()` previously returned the first generic type selector (e.g., `input[type='text']`) for every matched field, causing the submitter to fill the wrong element on forms with multiple inputs. Now returns element-specific selectors: `[name='…']`, `[id='…']`, or `:nth-of-type(N)` fallback.
- **B5 — `services/tasks/scrape_task.py`** — `MaxRetriesExceededError` was caught by the broad `Exception` handler and re-raised with `raise self.retry(…)`, creating an infinite retry loop. Now caught and handled explicitly before the generic handler.

### Changed

- **`services/scraper/ingest.py`** — `ingest_job_batch()` gains an optional `trigger_match: bool = True` parameter; when `True` (default), dispatches `batch_match_new_jobs.delay(job_ids)` after all points are upserted. Wrapped in `try/except` so a missing Celery broker does not break ingestion.
- **`services/scraper/ingest.py`** — `upsert()` call now uses `PointStruct(id=…, vector=…, payload=…)` instead of a raw `dict`; makes the type boundary explicit and matches the qdrant-client typed API.
- **`services/api/routes/resumes.py`** — Both `upsert()` calls now use `PointStruct`; `PointsSelector` import removed (it is a type alias, not a concrete class).
- **`config/settings.py`** — `celery_broker_url` and `celery_result_backend` are now `@property` methods derived from `redis_host` + `redis_port`, matching the pattern used by `vllm_base_url` and `qdrant_url`. The previous hardcoded string fields are removed.
- **`docker-compose.yml`** — Removed deprecated top-level `version: "3.9"` key (warning since Compose v2; ignored in Compose v2.x).
- **`Dockerfile.orchestrator`**, **`Dockerfile.streamlit`** — Base image updated from `python:3.11-slim` to `python:3.12-slim` to align with the declared Python badge and test matrix.
- **`frontend/pages/staged_apps.py`** — Stores `current_resume_id`, `rewrite_job_title`, and `rewrite_company` in session state when the match runs; passes `match_score` to the rewrite API request body so the backend skips a redundant embedding search.
- **`services/tasks/celery_app.py`** — `match_task` module added to the `include` list so the new task is auto-discovered.

### Removed

- **`services/rewrite/outlines_constraint.py`** — Dead `create_outlines_generator()` function removed; it was never called and duplicated the logic already provided by `apply_outlines_constraint_to_request()`.

### Refactored

- **`services/automation/pdf_generator.py`** — Extracted `_build_pdf_story(tailored_resume)` private helper that builds the ReportLab `SimpleDocTemplate`, styles, and `story` list; `generate_pdf_bytes()` and `generate_tailored_resume_pdf()` now both delegate to it, eliminating ~90 lines of duplication.
- **`services/scraper/metadata_extractor.py`** — `extract_certs()` no longer calls `text.upper()` before the regex; `re.IGNORECASE` alone is sufficient and the previous `.upper()` made the input uninspectable in debug logs.

### Tests

- `tests/conftest.py` — `mock_qdrant_client` fixture now sets `client.retrieve.return_value = []` as the default, matching the updated implementation.
- `tests/tier1_critical/test_metadata_extractor.py` — `clearance_level` assertions updated from `is None` to `== ""`.
- `tests/tier2_services/test_ingest.py` — PointStruct attribute access (`point.id`, `point.payload`) replaces dict key access; `ingest_job_batch` tests patch `batch_match_new_jobs.delay`.
- `tests/tier2_services/test_matcher.py` — All `TestMatchJobsToResume` tests replaced `scroll.return_value` / `scroll.side_effect` with `retrieve.return_value`.
- `tests/tier2_services/test_rewriter.py` — `test_job_not_found_raises` updated to mock `retrieve` (not `scroll`).
- `tests/tier3_api/test_api_jobs.py` — `test_get_job_found` / `test_get_job_not_found` use `retrieve` mock.
- `tests/tier3_api/test_api_match.py` — All four match tests use `retrieve` mock for resume lookup.
- `tests/tier3_api/test_api_resumes.py` — `test_get_resume_found` / `test_get_resume_not_found` use `retrieve` mock.
- `tests/tier4_wiring/test_integration_wiring.py` — Match step uses `retrieve` mock; submit step patches `_get_redis` to avoid live Redis dependency; `job_title` and `company` added to submit payload.

---

## [0.0.1-beta] - 2026-05-13

### Added

#### Core Services
- `services/api/` — FastAPI orchestrator with lifespan Qdrant initialization and CORS middleware
- `services/api/routes/jobs.py` — Job ingest (single + batch), list, get, delete endpoints
- `services/api/routes/resumes.py` — Resume upload (file + JSON), list, get, delete endpoints
- `services/api/routes/match.py` — Vector similarity matching with hard metadata filter endpoint
- `services/api/routes/rewrite.py` — Resume tailoring via Foundation-Sec-8B endpoint
- `services/api/routes/submit.py` — Celery-backed application submission and status endpoints
- `services/embeddings/embedding_service.py` — Singleton `mxbai-embed-large-v1` encoder (1024-dim, MRL)
- `services/qdrant/init_collections.py` — Qdrant collection initialization and reset with singleton client
- `services/scraper/ingest.py` — Job ingestion pipeline (embed + upsert to Qdrant)
- `services/scraper/metadata_extractor.py` — Regex-based cert, clearance, and skill extraction from job text
- `services/scraper/scraper.py` — Playwright-driven job board scraper (Indeed, LinkedIn, Dice)
- `services/resume/parser.py` — PDF / DOCX / TXT / JSON resume parser
- `services/resume/schema.py` — Pydantic schema for structured resume representation
- `services/matching/matcher.py` — Cosine vector search + hard-filter engine (certs, clearance, skills)
- `services/rewrite/rewriter.py` — Foundation-Sec-8B rewrite pipeline with diff generation
- `services/rewrite/outlines_constraint.py` — Outlines FSM grammar for zero-retry structured JSON output
- `services/rewrite/schema.py` — Pydantic schemas for `RewriteOutput` and `RewriteResult`
- `services/tasks/celery_app.py` — Celery application factory (Redis broker + backend, JSON serialization)
- `services/tasks/scrape_task.py` — Periodic scrape-and-ingest Celery task with retry logic
- `services/tasks/submit_task.py` — Async application submission Celery task with error capture
- `services/automation/dom_mapper.py` — Heuristic HTML form field → resume key mapper with normalization
- `services/automation/submitter.py` — Playwright form-filling and file upload automation
- `services/automation/pdf_generator.py` — ReportLab-based tailored resume PDF generator
- `config/settings.py` — Pydantic `BaseSettings` for all service configuration via `.env`

#### Frontend
- `frontend/app.py` — Streamlit multi-page dashboard entry point
- `frontend/api_client.py` — Typed async HTTP client for orchestrator API
- `frontend/pages/` — Dashboard, Job Board, My Resumes, Staged Applications, Review & Approve, Application History
- `frontend/components/diff_viewer.py` — Side-by-side bullet diff visualization component

#### Infrastructure
- `docker-compose.yml` — Full service orchestration (Streamlit, Orchestrator, vLLM, Qdrant, Redis, Celery)
- `Dockerfile.orchestrator` — FastAPI + Celery + Playwright containerized image
- `Dockerfile.streamlit` — Streamlit frontend containerized image
- `Makefile` — Developer convenience targets (`up`, `down`, `logs`, `status`, `init-db`, `reset-db`, `clean`)
- `.env.example` — Environment variable template with all configurable options

#### Testing
- `tests/conftest.py` — Shared pytest fixtures with pre-collection mocks for Qdrant, SentenceTransformers, and torch CUDA
- `tests/tier1_critical/test_dom_mapper.py` — 30+ unit tests for field normalization, matching, value extraction, and `build_field_mapping` with mocked Playwright page
- `tests/tier1_critical/test_metadata_extractor.py` — Regex extraction tests for certs, clearance levels, and skills
- `tests/tier1_critical/test_pdf_generator.py` — PDF generation and formatting tests
- `tests/tier1_critical/test_resume_schema.py` — Pydantic schema validation and edge case tests
- `tests/tier1_critical/test_rewrite_schema.py` — `RewriteOutput` and `TailoredExperience` schema tests
- `tests/tier2_services/test_embedding.py` — Embedding model singleton and encode tests
- `tests/tier2_services/test_ingest.py` — Job ingestion pipeline tests (single + batch, payload structure)
- `tests/tier2_services/test_matcher.py` — Vector search and hard-filter match tests
- `tests/tier2_services/test_parser.py` — Resume file parsing tests
- `tests/tier2_services/test_qdrant_init.py` — Collection init, reset, and singleton client tests
- `tests/tier2_services/test_rewriter.py` — Full rewrite pipeline, `_call_vllm`, JSON fallback, and request structure tests
- `tests/tier2_services/test_tasks.py` — Celery task `run()` tests for submit and scrape tasks
- `tests/tier3_api/test_api_jobs.py` — Jobs API endpoint tests including lifespan coverage
- `tests/tier3_api/test_api_match.py` — Match API tests with mocked vector search
- `tests/tier3_api/test_api_resumes.py` — Resume upload (file + JSON), list, get, delete API tests
- `tests/tier3_api/test_api_rewrite.py` — Rewrite API test with patched internal functions
- `tests/tier3_api/test_api_submit.py` — Submit and status API tests with mocked Celery
- `tests/tier4_wiring/test_integration_wiring.py` — Full 5-step pipeline wiring test and error propagation tests
- `pytest.ini` — Pytest configuration with asyncio mode, coverage thresholds (≥77%), and report formats

### Fixed

- `services/scraper/metadata_extractor.py` — Regex word-boundary bug after `+` in certification names (e.g., `C++`, `CCNP+`); replaced `\b` with `(?:\s|$)` lookahead
- `services/automation/dom_mapper.py` — Empty string input now correctly returns `None` instead of matching the first pattern
- `services/automation/dom_mapper.py` — `cover_letter_upload` now takes precedence over `summary` by reordering `FIELD_PATTERNS` and normalizing both sides of the comparison
- `config/settings.py` — Added `streamlit_port` and `streamlit_host` fields; added `extra = "ignore"` to `Config` to prevent validation errors from unknown environment variables

### Changed

- `services/automation/dom_mapper.py` — Pattern matching now normalizes both field name and pattern string before comparison, eliminating false positives from un-normalized separators

---

[Unreleased]: https://github.com/Zenetusken/Jobseeker/compare/v0.0.3-beta...HEAD
[0.0.3-beta]: https://github.com/Zenetusken/Jobseeker/compare/v0.0.2-beta...v0.0.3-beta
[0.0.2-beta]: https://github.com/Zenetusken/Jobseeker/compare/v0.0.1-beta...v0.0.2-beta
[0.0.1-beta]: https://github.com/Zenetusken/Jobseeker/releases/tag/v0.0.1-beta
