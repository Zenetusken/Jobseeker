# Jobseeker AI — Localized Cybersecurity Resume Automation

> **v0.0.3-beta** — Security hardening, full job description pipeline, FSM/JSON strictness, dependency sweep to latest, Python 3.13.

[![Python](https://img.shields.io/badge/python-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-009688)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/streamlit-FF4B4B)](https://streamlit.io)
[![vLLM](https://img.shields.io/badge/vllm-76B900)](https://github.com/vllm-project/vllm)
[![Qdrant](https://img.shields.io/badge/qdrant-FF0055)](https://qdrant.tech)
[![Redis](https://img.shields.io/badge/redis-DC382D)](https://redis.io)
[![Celery](https://img.shields.io/badge/celery-37814A)](https://docs.celeryq.dev)
[![Playwright](https://img.shields.io/badge/playwright-2EAD33)](https://playwright.dev)
[![Docker](https://img.shields.io/badge/docker-2496ED)](https://www.docker.com)
[![PyTorch](https://img.shields.io/badge/pytorch-EE4C2C)](https://pytorch.org)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](./LICENSE)

---

## Overview

Jobseeker AI is a fully local, privacy-first pipeline that:

1. **Scrapes** cybersecurity job listings from major boards via Playwright
2. **Parses** your resume (PDF / DOCX / TXT / JSON) into a structured schema
3. **Matches** jobs to your resume using semantic vector search + hard metadata filtering (certs, clearance, skills)
4. **Rewrites** your resume for each job using [Foundation-Sec-8B AWQ](https://huggingface.co/fdtn-ai/Foundation-Sec-8B) with Outlines-constrained JSON output (zero hallucination)
5. **Submits** the tailored application via Playwright DOM automation
6. **Tracks** submission history through a Streamlit dashboard

No data ever leaves your machine.

---

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌───────────────┐
│  Streamlit   │───▶│   Celery     │───▶│   Playwright  │
│  Dashboard   │    │   Workers    │    │  Submission   │
│  :8501       │    │              │    │               │
└──────┬───────┘    └──────┬───────┘    └───────────────┘
       │                   │
       ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌───────────────┐
│  Orchestrator│───▶│    vLLM      │    │    Qdrant     │
│  (FastAPI)   │    │  :8000       │    │   :6333       │
│  :8001       │    │  Foundation- │    │  Vector DB    │
└──────────────┘    │  Sec-8B AWQ  │    └───────────────┘
                    └──────────────┘
```

### Service Responsibilities

| Service | Port | Role |
|---|---|---|
| **Streamlit** | 8501 | User dashboard — upload, match, review, submit |
| **Orchestrator** (FastAPI) | 8001 | REST API — coordinates all services |
| **vLLM** | 8000 | Foundation-Sec-8B inference engine |
| **Qdrant** | 6333 | Vector storage for jobs and resumes |
| **Redis** | 6379 | Celery broker + result backend |
| **Celery Workers** | — | Async scraping and submission tasks |

---

## Hardware Requirements

| Component | Minimum |
|---|---|
| GPU | NVIDIA RTX 4070 (12 GB VRAM) or better |
| RAM | 32 GB system RAM |
| Storage | 50 GB free (model cache + Qdrant data) |
| OS | Linux (Ubuntu 22.04+) |
| NVIDIA Driver | 535+ |
| Docker | 24+ with `nvidia-container-toolkit` |

### VRAM Budget (12 GB)

| Component | Allocation |
|---|---|
| System / PyTorch overhead | 2.0 GB |
| Embedding model (`mxbai-embed-large-v1`) | 1.5 GB |
| vLLM generative engine | 8.4 GB |
| Buffer | 0.1 GB |

---

## Quick Start

### 1. Prerequisites

```bash
# Install NVIDIA Container Toolkit
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

### 2. Setup

```bash
git clone https://github.com/Zenetusken/Jobseeker.git
cd Jobseeker

# Copy and edit environment config
cp .env.example .env

# Build and start all services
make up
```

> First launch downloads the AWQ-quantized Foundation-Sec-8B (~5 GB). Allow 5–15 minutes.

### 3. Access

| Interface | URL |
|---|---|
| Streamlit Dashboard | http://localhost:8501 |
| API Docs (Swagger) | http://localhost:8001/docs |
| vLLM API | http://localhost:8000/v1 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Workflow

### Step 1 — Upload Your Resume
**My Resumes** → Upload PDF / DOCX / TXT, or paste a structured JSON resume.

### Step 2 — Add Job Listings
**Job Board** → Browse auto-scraped jobs (runs every 6 h by default) or ingest manually via API.

### Step 3 — Match
**Staged Applications** → Select resume → **Run Matching**.  
Vector similarity search over all ingested jobs, filtered by hard criteria (clearance, required certs, skills).

### Step 4 — Tailor
Click **Tailor Resume** on any match. Foundation-Sec-8B rewrites every bullet point for the target job.  
Output is constrained by an Outlines FSM — malformed JSON is structurally impossible.

### Step 5 — Review & Submit
**Review & Approve** → Side-by-side diff of every change → Enter application URL → **Approve & Submit**.  
Playwright fills the form fields, attaches files, and submits in the background.

### Step 6 — Track
**Application History** → Live status per submission (queued / submitted / failed).

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Foundation-Sec-8B AWQ** | Cybersecurity-specialist LLM (CTIBench-RCM 75.3%), fits 8.4 GB, Llama 3.1 JSON backbone |
| **vLLM + Marlin kernels** | PagedAttention + Marlin gives 10.9× AWQ throughput |
| **Outlines pre-generation FSM** | Zero-retry structured output — invalid JSON is impossible |
| **Temperature = 0.0, seed = 42** | Fully deterministic — no hallucinated credentials, reproducible diffs |
| **Qdrant over Chroma/FAISS** | Native payload filtering, persistent storage, Rust-backed performance |
| **Celery + Redis** | Mature async task queue with scheduling, retries, and result tracking |
| **`mxbai-embed-large-v1`** | 1024-dim, MRL-trained — best-in-class retrieval on MTEB at this size |

---

## Configuration

All options live in `.env` (copied from `.env.example`):

```bash
# Model
VLLM_MODEL_NAME=fdtn-ai/Foundation-Sec-8B-Reasoning
VLLM_GPU_MEMORY_UTILIZATION=0.7

# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_JOBS=job_descriptions
QDRANT_COLLECTION_RESUMES=resumes

# Redis / Celery
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=change-me-strong-redis-password   # required in production

# Scraper
SCRAPER_SCHEDULE_HOURS=6
SCRAPER_SOURCES=indeed,linkedin,dice

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT_MS=30000
PLAYWRIGHT_STEALTH_ENABLED=true

# Security — REQUIRED for production (change ALL values)
API_KEY=change-me-to-a-long-random-secret   # X-API-Key header auth; empty = dev mode
API_DEBUG=false                              # set true to enable /docs, /redoc
ALLOWED_ORIGINS=                            # blank = deny all cross-origin requests
QDRANT_API_KEY=change-me-qdrant-api-key

# Upload / validation limits
MAX_UPLOAD_BYTES=10485760    # 10 MB
MAX_DESCRIPTION_LENGTH=50000
MAX_BATCH_SIZE=100
```

Generate secrets with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Makefile Commands

```bash
make up             # Build and start all services
make down           # Stop all services
make logs           # Tail all service logs
make logs-vllm      # Stream vLLM engine logs only
make status         # Health check across all services
make init-db        # Initialize Qdrant collections
make reset-db       # WARNING: wipe all stored jobs and resumes
make clean          # Remove containers, volumes, and build cache
make check-secrets  # Verify API_KEY, REDIS_PASSWORD, QDRANT_API_KEY are not placeholders
```

---

## Testing

The project ships with a comprehensive pytest suite: **386 tests**, 77% coverage (Playwright browser automation excluded by design, zero warnings).

```bash
# Install test dependencies
pip install -r requirements.test.txt

# Run full suite with coverage
python -m pytest tests/

# Run a specific tier
python -m pytest tests/tier1_critical/
python -m pytest tests/tier2_services/
python -m pytest tests/tier3_api/
python -m pytest tests/tier4_wiring/
```

### Test Structure

```
tests/
├── conftest.py                      # Session fixtures + 3rd-party warning filters
├── tier1_critical/                  # Pure-logic unit tests (no mocks)
│   ├── test_dom_mapper.py
│   ├── test_metadata_extractor.py
│   ├── test_outlines_constraint.py  # Schema validity, FSM self-containment, prompt hints
│   ├── test_pdf_generator.py
│   ├── test_resume_schema.py
│   ├── test_rewrite_schema.py
│   └── test_security_validators.py  # SSRF guard, upload size, filename sanitizer, UUID
├── tier2_services/                  # Service unit tests (mocked Qdrant / embeddings / vLLM)
│   ├── test_embedding.py
│   ├── test_ingest.py
│   ├── test_matcher.py
│   ├── test_parser.py
│   ├── test_pdf_generator.py
│   ├── test_qdrant_init.py
│   ├── test_rewriter.py
│   ├── test_scraper.py              # HTML→Markdown, description fetching, pipeline integration
│   ├── test_settings.py             # SettingsConfigDict migration, zero Pydantic warnings
│   └── test_tasks.py
├── tier3_api/                       # FastAPI integration tests (httpx ASGITransport)
│   ├── test_api_auth.py             # API key enforcement (401/200, dev-mode bypass)
│   ├── test_api_jobs.py
│   ├── test_api_match.py
│   ├── test_api_resumes.py
│   ├── test_api_rewrite.py
│   └── test_api_submit.py
└── tier4_wiring/                    # End-to-end pipeline wiring tests
    └── test_integration_wiring.py
```

### Coverage Summary

| Module | Coverage |
|---|---|
| `config/settings.py` | 100% |
| `services/api/security.py` | 100% |
| `services/api/validators.py` | 100% |
| `services/automation/dom_mapper.py` | 100% |
| `services/embeddings/embedding_service.py` | 100% |
| `services/matching/matcher.py` | 100% |
| `services/resume/schema.py` | 100% |
| `services/rewrite/schema.py` | 100% |
| `services/scraper/ingest.py` | 100% |
| `services/tasks/*` | 100% |
| `services/qdrant/init_collections.py` | 97% |
| `services/api/routes/*` | 85–91% |
| `services/rewrite/rewriter.py` | 90% |
| `services/rewrite/outlines_constraint.py` | 88% |
| `services/automation/submitter.py` | 10% *(requires live Playwright)* |
| `services/scraper/scraper.py` | 12% *(requires live Playwright; HTML→Markdown helpers 100%)* |

---

## Project Structure

```
Jobseeker/
├── docker-compose.yml          # Service orchestration
├── Dockerfile.orchestrator     # FastAPI + Celery + Playwright image
├── Dockerfile.streamlit        # Streamlit frontend image
├── Makefile                    # Developer commands
├── pytest.ini                  # Test configuration (cov threshold: 77%)
├── requirements.txt            # Core dependencies
├── requirements.test.txt       # Test-only dependencies
├── requirements.streamlit.txt  # Frontend dependencies
├── .env.example                # Environment template
├── config/
│   └── settings.py             # Pydantic BaseSettings
├── services/
│   ├── api/                    # FastAPI orchestrator
│   │   ├── main.py             # App factory, lifespan, rate-limit + security-header middleware
│   │   ├── security.py         # X-API-Key dependency
│   │   ├── validators.py       # SSRF guard, upload size, filename sanitizer, UUID check
│   │   └── routes/             # jobs · resumes · match · rewrite · submit
│   ├── embeddings/             # mxbai-embed-large-v1 singleton
│   ├── qdrant/                 # Collection schema + init
│   ├── scraper/                # Playwright scrapers + metadata extractor
│   ├── resume/                 # PDF/DOCX/TXT parser + Pydantic schema
│   ├── matching/               # Cosine search + hard-filter engine
│   ├── rewrite/                # vLLM rewrite + Outlines FSM constraint
│   ├── tasks/                  # Celery app, scrape task, submit task, batch-match task
│   └── automation/             # Playwright submitter + DOM mapper + PDF gen
├── frontend/
│   ├── app.py                  # Streamlit entry point
│   ├── api_client.py           # Typed HTTP client for orchestrator
│   ├── pages/                  # Dashboard, Job Board, Resumes, Match, Review, History
│   └── components/             # Diff viewer component
└── data/                       # Persistent volumes (gitignored)
    ├── qdrant_storage/
    ├── uploads/
    └── outputs/
```

---

## What's New in v0.0.3-beta

| Area | Change |
|---|---|
| **Security** | API key auth (`X-API-Key`) on every route; HTTP 401 on mismatch; dev bypass when `API_KEY` unset |
| **Security** | `SecurityHeadersMiddleware`: 5 hardening headers on every response |
| **Security** | `RateLimitMiddleware`: per-route sliding-window limits; HTTP 429 + `Retry-After` |
| **Security** | SSRF guard (`validate_job_url`), upload-size guard, filename sanitizer, UUID validator across all routes |
| **Security** | CORS tightened to explicit origin list, methods, and headers; Swagger UI gated behind `API_DEBUG=true` |
| **Scraper** | Two-pass design: real job URLs captured; full HTML descriptions fetched concurrently via `asyncio.gather` |
| **Scraper** | `_html_to_markdown()` converts job detail HTML to clean ATX Markdown (script/style stripped, truncated) |
| **Scraper** | `markdownify==1.2.2` restored; description stubs eliminated throughout the pipeline |
| **FSM/JSON** | `_extract_json_fallback()` removed — constraint violation raises `RuntimeError` immediately |
| **FSM/JSON** | `validate_schema_self_contained()` pre-flight on every vLLM request; dangling `$ref` → `ValueError` |
| **FSM/JSON** | `build_json_schema_description` inlines nested `TailoredExperience`/`TailoredBullet` fields in the LLM prompt |
| **Deps** | All 22 packages bumped to latest; `playwright-stealth==2.0.3` API fix (`Stealth().apply_stealth_async`) |
| **Infra** | Python 3.13 in both Docker images; vLLM v0.20.2; Qdrant v1.18.0; Redis 8.6.3 |
| **Config** | `class Config:` → `model_config = SettingsConfigDict(…)` (Pydantic v2 convention) |
| **Tests** | 362 → 386 tests; 5 new test files; zero warnings |

---

## What's New in v0.0.2-beta

| Area | Change |
|---|---|
| **Qdrant** | Thread-safe client singleton; all point lookups use `client.retrieve()` — O(1) vs O(N) scroll |
| **API routes** | `delete_job` / `delete_resume` use `PointIdsList` (was broken); `get_job` / `get_resume` fixed |
| **Matching** | `_get_resume_payload` replaced scroll-loop with O(1) retrieve |
| **Rewriting** | `rewrite_resume_for_job()` accepts `match_score` param — skips redundant vector search |
| **History** | Real submission history persisted to Redis; live Celery state enrichment; full table UI |
| **Scraping** | `playwright-stealth` applied to all three scrapers and the form submitter |
| **Batch match** | New `batch_match_new_jobs` Celery task auto-dispatched after every job ingest batch |
| **Config** | `celery_broker_url` / `celery_result_backend` derived from `redis_host`/`redis_port` `@property` |
| **Docker** | GPU reservation added to `orchestrator` + `celery-worker`; base image → `python:3.12-slim` |
| **DRY** | `pdf_generator.py` refactored; dead `create_outlines_generator()` removed; metadata regex cleaned up |
| **Frontend** | Delete resume button fixed (`api_delete()`); `current_resume_id` propagated through session state |

---

## Limitations & Roadmap

- **Single-user MVP** — multi-user auth and resume namespacing planned for v0.1.0
- **LinkedIn scraping** — fragile against anti-bot measures; `playwright-stealth` mitigates but manual upload is recommended for critical roles
- **DOM mapping** — heuristic-based; complex multi-step ATS forms may need manual review
- **PDF generation** — basic ReportLab layout; LaTeX / HTML templates planned for v0.1.0
- **Model fallback** — if Foundation-Sec-8B is unavailable: `VLLM_MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct`
- **Rate limiter** — in-process, per-worker; not shared across Celery workers or multiple orchestrator replicas. A Redis-backed limiter is planned for v0.1.0

---

## License

MIT
