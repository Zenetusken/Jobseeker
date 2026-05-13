"""
Tier 3 — FastAPI integration tests for /api/rewrite routes.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestRewriteAPI:
    @pytest.mark.asyncio
    async def test_tailor_resume(self, test_app, mock_qdrant_client, mock_embedding, mock_vllm_client,
                                 sample_job_payload, sample_resume_payload):
        with patch("services.rewrite.rewriter._fetch_job_and_resume",
                   return_value=(sample_job_payload, sample_resume_payload)), \
             patch("services.rewrite.rewriter.match_jobs_to_resume",
                   return_value=[MagicMock(job_id="job-1", score=0.85)]):

            response = await test_app.post("/api/rewrite/tailor", json={
                "resume_id": "resume-1",
                "job_id": "job-1",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["job_title"] == "Senior Cybersecurity Engineer"
            assert data["company"] == "Acme Defense Corp"
            assert "tailored_resume" in data
            assert "diff" in data
            assert data["match_score"] == 0.85

    @pytest.mark.asyncio
    async def test_tailor_job_not_found(self, test_app, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = ([], None)

        response = await test_app.post("/api/rewrite/tailor", json={
            "resume_id": "resume-1",
            "job_id": "nonexistent",
        })
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tailor_resume_not_found(self, test_app, mock_qdrant_client):
        # First call returns job, second returns no resume
        mock_job = MagicMock()
        mock_job.id = "job-1"
        mock_job.payload = {"title": "Engineer", "company": "Corp", "description": "Desc"}

        call_count = [0]

        def scroll_side_effect(*args, **kwargs):
            call_count[0] += 1
            collection = kwargs.get("collection_name", args[0] if args else "")
            if "jobs" in str(collection):
                return ([mock_job], None)
            else:
                return ([], None)

        mock_qdrant_client.scroll.side_effect = scroll_side_effect

        response = await test_app.post("/api/rewrite/tailor", json={
            "resume_id": "nonexistent",
            "job_id": "job-1",
        })
        assert response.status_code == 404
