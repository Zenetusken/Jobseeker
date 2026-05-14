.PHONY: help build up down restart logs logs-vllm logs-orchestrator logs-streamlit logs-celery \
        init-db reset-db shell-orchestrator shell-streamlit clean status ps

# Default target
help:
	@echo "Jobseeker AI — Localized Cybersecurity Resume Automation"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup:"
	@echo "  build            Build all Docker images"
	@echo "  up               Start all services (detached)"
	@echo "  down             Stop all services"
	@echo "  restart          Restart all services"
	@echo ""
	@echo "Monitoring:"
	@echo "  logs             Tail all service logs"
	@echo "  logs-vllm        Tail vLLM engine logs"
	@echo "  logs-orchestrator Tail orchestrator API logs"
	@echo "  logs-streamlit   Tail Streamlit frontend logs"
	@echo "  logs-celery      Tail Celery worker logs"
	@echo "  status           Show service health"
	@echo "  ps               List running containers"
	@echo ""
	@echo "Database:"
	@echo "  init-db          Initialize Qdrant collections"
	@echo "  reset-db         WARNING: Delete and recreate all collections"
	@echo ""
	@echo "Shell:"
	@echo "  shell-orchestrator  Open shell in orchestrator container"
	@echo "  shell-streamlit     Open shell in Streamlit container"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Remove all containers, volumes, and cache"
	@echo ""
	@echo "URLs:"
	@echo "  Streamlit:   http://localhost:8501"
	@echo "  API Docs:    http://localhost:8001/docs"
	@echo "  vLLM API:    http://localhost:8000/v1"
	@echo "  Qdrant:      http://localhost:6333/dashboard"

# ============================================================
# Build & Run
# ============================================================
check-secrets:
	@echo "=== Checking required production secrets ==="
	@if [ -z "$$API_KEY" ] || [ "$$API_KEY" = "change-me-to-a-long-random-secret" ]; then \
		echo "ERROR: API_KEY is not set or is the placeholder value."; exit 1; fi
	@if [ -z "$$REDIS_PASSWORD" ] || [ "$$REDIS_PASSWORD" = "change-me-strong-redis-password" ]; then \
		echo "ERROR: REDIS_PASSWORD is not set or is the placeholder value."; exit 1; fi
	@if [ -z "$$QDRANT_API_KEY" ] || [ "$$QDRANT_API_KEY" = "change-me-qdrant-api-key" ]; then \
		echo "ERROR: QDRANT_API_KEY is not set or is the placeholder value."; exit 1; fi
	@echo "All required secrets are set."

build:
	docker compose build

up:
	docker compose up -d
	@echo ""
	@echo "Services starting..."
	@echo "  Streamlit:   http://localhost:8501"
	@echo "  API Docs:    http://localhost:8001/docs"
	@echo "  vLLM API:    http://localhost:8000/v1"
	@echo ""
	@echo "Note: vLLM may take 2-5 minutes to download and load the model on first run."

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d

# ============================================================
# Logs
# ============================================================
logs:
	docker compose logs -f --tail=50

logs-vllm:
	docker compose logs -f vllm-engine

logs-orchestrator:
	docker compose logs -f orchestrator

logs-streamlit:
	docker compose logs -f streamlit

logs-celery:
	docker compose logs -f celery-worker

# ============================================================
# Status
# ============================================================
status:
	@echo "=== Service Health ==="
	@docker compose ps
	@echo ""
	@echo "=== vLLM Model Status ==="
	@curl -s http://localhost:8000/v1/models 2>/dev/null | python3 -m json.tool || echo "vLLM not ready yet"
	@echo ""
	@echo "=== Qdrant Collections ==="
	@curl -s http://localhost:6333/collections 2>/dev/null | python3 -m json.tool || echo "Qdrant not ready yet"

ps:
	docker compose ps

# ============================================================
# Database
# ============================================================
init-db:
	docker compose exec orchestrator python -c "from services.qdrant.init_collections import init_collections; init_collections(); print('Collections initialized')"

reset-db:
	@echo "WARNING: This will delete all job and resume data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose exec orchestrator python -c "from services.qdrant.init_collections import reset_collections; reset_collections(); print('Collections reset')"; \
	else \
		echo "Cancelled."; \
	fi

# ============================================================
# Shell Access
# ============================================================
shell-orchestrator:
	docker compose exec orchestrator bash

shell-streamlit:
	docker compose exec streamlit bash

# ============================================================
# Cleanup
# ============================================================
clean:
	docker compose down -v --rmi all --remove-orphans
	rm -rf data/qdrant_storage/*
	rm -rf data/uploads/*
	rm -rf data/outputs/*
	@echo "Cleaned all containers, volumes, images, and local data."
