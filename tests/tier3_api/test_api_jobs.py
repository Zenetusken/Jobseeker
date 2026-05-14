"""
Tier 3 — FastAPI integration tests for /api/jobs routes.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestJobsAPI:
    @pytest.mark.asyncio
    async def test_ingest_single_job(self, test_app, mock_qdrant_client, mock_embedding):
        response = await test_app.post("/api/jobs/ingest", json={
            "title": "Security Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Looking for CISSP certified engineer",
            "url": "https://example.com",
            "source": "manual",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ingested"
        assert "job_id" in data

    @pytest.mark.asyncio
    async def test_ingest_missing_required_fields(self, test_app):
        response = await test_app.post("/api/jobs/ingest", json={
            "title": "Engineer",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_batch(self, test_app, mock_qdrant_client, mock_embedding):
        response = await test_app.post("/api/jobs/ingest/batch", json={
            "jobs": [
                {"title": "Job 1", "company": "C1", "description": "Desc 1"},
                {"title": "Job 2", "company": "C2", "description": "Desc 2"},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ingested"
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_ingest_empty_batch(self, test_app, mock_qdrant_client, mock_embedding):
        response = await test_app.post("/api/jobs/ingest/batch", json={"jobs": []})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_list_jobs(self, test_app, mock_qdrant_client):
        from qdrant_client.models import ScoredPoint
        mock_record = MagicMock()
        mock_record.id = "job-1"
        mock_record.payload = {
            "title": "Security Engineer",
            "company": "Acme",
            "location": "Remote",
            "source": "indeed",
            "required_certs": ["CISSP"],
            "required_skills": ["SIEM"],
            "clearance_level": "Secret",
            "url": "https://example.com",
        }
        mock_qdrant_client.scroll.return_value = ([mock_record], None)

        response = await test_app.get("/api/jobs/list")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["title"] == "Security Engineer"

    @pytest.mark.asyncio
    async def test_list_jobs_with_source_filter(self, test_app, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = ([], None)

        response = await test_app.get("/api/jobs/list", params={"source": "indeed"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_job_found(self, test_app, mock_qdrant_client):
        mock_record = MagicMock()
        mock_record.id = "job-1"
        mock_record.payload = {
            "title": "Security Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Full job description",
            "source": "indeed",
            "url": "https://example.com",
            "required_certs": ["CISSP"],
            "required_skills": ["SIEM"],
            "clearance_level": "Secret",
        }
        mock_qdrant_client.retrieve.return_value = [mock_record]

        response = await test_app.get("/api/jobs/job-1")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Security Engineer"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, test_app, mock_qdrant_client):
        mock_qdrant_client.retrieve.return_value = []

        response = await test_app.get("/api/jobs/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job(self, test_app, mock_qdrant_client):
        response = await test_app.delete("/api/jobs/123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_health(self, test_app):
        response = await test_app.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_api_docs_disabled_in_production(self, test_app):
        """Swagger UI must be disabled when api_debug=False (default)."""
        response = await test_app.get("/docs")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_openapi_schema_disabled_in_production(self, test_app):
        """OpenAPI schema endpoint must be disabled when api_debug=False (default)."""
        response = await test_app.get("/openapi.json")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_lifespan_executes(self, test_app, mock_qdrant_client, mock_embedding):
        """Verify the app starts up and can serve requests (lifespan coverage)."""
        # Make multiple requests to ensure lifespan has executed
        response = await test_app.get("/health")
        assert response.status_code == 200

        response = await test_app.post("/api/jobs/ingest", json={
            "title": "Test Job",
            "company": "Test Corp",
            "description": "A test job description",
        })
        assert response.status_code == 200
