"""
Tier 3 — FastAPI integration tests for /api/match routes.
"""
import pytest
from unittest.mock import MagicMock, patch
from qdrant_client.models import ScoredPoint


class TestMatchAPI:
    @pytest.mark.asyncio
    async def test_match_jobs(self, test_app, mock_qdrant_client, mock_embedding):
        # Setup resume scroll
        mock_resume = MagicMock()
        mock_resume.id = "resume-1"
        mock_resume.payload = {
            "raw_text": "Security engineer with CISSP",
            "certs": ["CISSP"],
            "skills": ["SIEM"],
            "clearance_level": "Top Secret",
        }

        # Setup job search results
        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="job-1",
                version=0,
                score=0.85,
                payload={
                    "title": "Security Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "required_certs": ["CISSP"],
                    "required_skills": ["SIEM"],
                    "clearance_level": "Secret",
                    "url": "https://example.com",
                    "description": "Job desc",
                },
            )
        ]

        mock_qdrant_client.retrieve.return_value = [mock_resume]

        response = await test_app.post("/api/match/jobs", json={
            "resume_id": "resume-1",
            "top_k": 10,
            "min_score": 0.3,
        })
        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert len(data["matches"]) == 1
        assert data["matches"][0]["title"] == "Security Engineer"

    @pytest.mark.asyncio
    async def test_match_resume_not_found(self, test_app, mock_qdrant_client):
        mock_qdrant_client.retrieve.return_value = []

        response = await test_app.post("/api/match/jobs", json={
            "resume_id": "nonexistent",
            "top_k": 10,
            "min_score": 0.3,
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_match_single_job(self, test_app, mock_qdrant_client, mock_embedding):
        mock_resume = MagicMock()
        mock_resume.id = "resume-1"
        mock_resume.payload = {
            "raw_text": "Security engineer",
            "certs": ["CISSP"],
            "skills": ["SIEM"],
            "clearance_level": "",
        }

        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id="job-1",
                version=0,
                score=0.9,
                payload={
                    "title": "Security Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "required_certs": ["CISSP"],
                    "required_skills": [],
                    "clearance_level": "",
                    "url": "",
                    "description": "",
                },
            )
        ]
        mock_qdrant_client.retrieve.return_value = [mock_resume]

        response = await test_app.get("/api/match/job/job-1", params={"resume_id": "resume-1"})
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-1"

    @pytest.mark.asyncio
    async def test_match_single_job_not_found(self, test_app, mock_qdrant_client, mock_embedding):
        mock_resume = MagicMock()
        mock_resume.id = "resume-1"
        mock_resume.payload = {
            "raw_text": "Security engineer",
            "certs": [],
            "skills": [],
            "clearance_level": "",
        }

        mock_qdrant_client.search.return_value = []
        mock_qdrant_client.retrieve.return_value = [mock_resume]

        response = await test_app.get("/api/match/job/nonexistent", params={"resume_id": "resume-1"})
        assert response.status_code == 404
