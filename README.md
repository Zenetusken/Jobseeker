# Jobseeker AI — Localized Cybersecurity Resume Automation

> **v0.0.1-beta** — Production-ready MVP for automated cybersecurity resume parsing, tailoring, and job application submission, running entirely on local consumer-grade hardware.

[![Tests](https://img.shields.io/badge/tests-298%20passed-brightgreen)](./tests)
[![Coverage](https://img.shields.io/badge/coverage-77%25-yellowgreen)](./htmlcov)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org)
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

# Scraper
SCRAPER_SCHEDULE_HOURS=6

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT_MS=30000
```

---

## Makefile Commands

```bash
make up          # Build and start all services
make down        # Stop all services
make logs        # Tail all service logs
make logs-vllm   # Stream vLLM engine logs only
make status      # Health check across all services
make init-db     # Initialize Qdrant collections
make reset-db    # WARNING: wipe all stored jobs and resumes
make clean       # Remove containers, volumes, and build cache
```

---

## Testing

The project ships with a comprehensive pytest suite covering 77% of business logic (Playwright browser automation excluded by design).

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
├── conftest.py              # Session fixtures: Qdrant, embedding, vLLM, Playwright mocks
├── tier1_critical/          # Pure-logic unit tests (no mocks)
│   ├── test_dom_mapper.py
│   ├── test_metadata_extractor.py
│   ├── test_pdf_generator.py
│   ├── test_resume_schema.py
│   └── test_rewrite_schema.py
├── tier2_services/          # Service unit tests (mocked Qdrant / embeddings / vLLM)
│   ├── test_embedding.py
│   ├── test_ingest.py
│   ├── test_matcher.py
│   ├── test_parser.py
│   ├── test_qdrant_init.py
│   ├── test_rewriter.py
│   └── test_tasks.py
├── tier3_api/               # FastAPI integration tests (httpx ASGITransport)
│   ├── test_api_jobs.py
│   ├── test_api_match.py
│   ├── test_api_resumes.py
│   ├── test_api_rewrite.py
│   └── test_api_submit.py
└── tier4_wiring/            # End-to-end pipeline wiring tests
    └── test_integration_wiring.py
```

### Coverage Summary

| Module | Coverage |
|---|---|
| `config/settings.py` | 100% |
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
| `services/automation/submitter.py` | 10% *(requires live Playwright)* |
| `services/scraper/scraper.py` | 7% *(requires live Playwright)* |

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
│   │   ├── main.py             # App factory + lifespan
│   │   └── routes/             # jobs · resumes · match · rewrite · submit
│   ├── embeddings/             # mxbai-embed-large-v1 singleton
│   ├── qdrant/                 # Collection schema + init
│   ├── scraper/                # Playwright scrapers + metadata extractor
│   ├── resume/                 # PDF/DOCX/TXT parser + Pydantic schema
│   ├── matching/               # Cosine search + hard-filter engine
│   ├── rewrite/                # vLLM rewrite + Outlines FSM constraint
│   ├── tasks/                  # Celery app, scrape task, submit task
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

## Limitations & Roadmap

- **Single-user MVP** — multi-user auth and resume namespacing planned for v0.1.0
- **LinkedIn scraping** — fragile against anti-bot measures; manual upload recommended for critical roles
- **DOM mapping** — heuristic-based; complex multi-step forms may need manual review
- **PDF generation** — basic ReportLab layout; LaTeX templates planned
- **Model fallback** — if Foundation-Sec-8B is unavailable: `VLLM_MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct`

---

## License

MIT
