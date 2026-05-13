# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/Zenetusken/Jobseeker/compare/v0.0.1-beta...HEAD
[0.0.1-beta]: https://github.com/Zenetusken/Jobseeker/releases/tag/v0.0.1-beta
