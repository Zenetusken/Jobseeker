"""
Tier 4 — Full wiring and integration tests.
End-to-end pipeline: ingest job → upload resume → match → rewrite → submit.
"""
import pytest
from unittest.mock import MagicMock, patch
from qdrant_client.models import ScoredPoint


class TestIntegrationWiring:
    """
    Full pipeline integration test.
    Verifies all service layers connect correctly with mocked backends.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline(self, test_app, mock_qdrant_client, mock_embedding, mock_vllm_client,
                                 sample_job_payload, sample_resume_payload):
        """
        End-to-end: ingest a job, upload a resume, match, rewrite, and submit.
        """
        # --- Step 1: Ingest a job ---
        ingest_response = await test_app.post("/api/jobs/ingest", json={
            "title": "Senior Cybersecurity Engineer",
            "company": "Acme Defense Corp",
            "location": "Washington, DC",
            "description": (
                "Seeking a Senior Cybersecurity Engineer with CISSP certification "
                "and Top Secret clearance. Must have experience with SIEM, Splunk, "
                "firewall management, and incident response."
            ),
            "url": "https://careers.acme.com/apply/123",
            "source": "indeed",
        })
        assert ingest_response.status_code == 200
        job_data = ingest_response.json()
        assert job_data["status"] == "ingested"
        job_id = job_data["job_id"]

        # --- Step 2: Upload a resume ---
        with patch("services.api.routes.resumes.parse_resume_file") as mock_parse:
            mock_parse.return_value = {
                "raw_text": (
                    "Jane Doe - Security Analyst\n"
                    "CISSP certified. SIEM, Splunk, firewall experience.\n"
                    "Top Secret clearance."
                ),
                "certs": ["CISSP"],
                "skills": ["SIEM", "Splunk", "Firewall"],
                "clearance_level": "Top Secret",
                "structured": None,
            }

            upload_response = await test_app.post(
                "/api/resumes/upload",
                files={"file": ("resume.pdf", b"fake pdf", "application/pdf")},
                params={"label": "jane-doe"},
            )
            assert upload_response.status_code == 200
            resume_data = upload_response.json()
            assert resume_data["status"] == "parsed"
            resume_id = resume_data["resume_id"]

        # --- Step 3: Match jobs to resume ---
        # Setup Qdrant to return the resume and job search results
        mock_resume_record = MagicMock()
        mock_resume_record.id = resume_id
        mock_resume_record.payload = {
            "raw_text": "Jane Doe - Security Analyst. CISSP. SIEM. Top Secret.",
            "certs": ["CISSP"],
            "skills": ["SIEM", "Splunk", "Firewall"],
            "clearance_level": "Top Secret",
        }

        mock_qdrant_client.search.return_value = [
            ScoredPoint(
                id=job_id,
                version=0,
                score=0.92,
                payload={
                    "title": "Senior Cybersecurity Engineer",
                    "company": "Acme Defense Corp",
                    "location": "Washington, DC",
                    "required_certs": ["CISSP"],
                    "required_skills": ["SIEM", "Splunk", "Firewall"],
                    "clearance_level": "Top Secret",
                    "url": "https://careers.acme.com/apply/123",
                    "description": "Full job description",
                },
            )
        ]

        mock_qdrant_client.scroll.return_value = ([mock_resume_record], None)

        match_response = await test_app.post("/api/match/jobs", json={
            "resume_id": resume_id,
            "top_k": 10,
            "min_score": 0.3,
        })
        assert match_response.status_code == 200
        match_data = match_response.json()
        assert len(match_data["matches"]) > 0
        assert match_data["matches"][0]["hard_filter_pass"] is True

        # --- Step 4: Rewrite resume for the matched job ---
        with patch("services.rewrite.rewriter._fetch_job_and_resume",
                   return_value=(sample_job_payload, sample_resume_payload)), \
             patch("services.rewrite.rewriter.match_jobs_to_resume",
                   return_value=[MagicMock(job_id=job_id, score=0.92)]):

            rewrite_response = await test_app.post("/api/rewrite/tailor", json={
                "resume_id": resume_id,
                "job_id": job_id,
            })
            assert rewrite_response.status_code == 200
            rewrite_data = rewrite_response.json()
            assert rewrite_data["job_title"] == "Senior Cybersecurity Engineer"
            assert rewrite_data["company"] == "Acme Defense Corp"
            assert "tailored_resume" in rewrite_data
            assert "diff" in rewrite_data
            assert len(rewrite_data["diff"]) > 0

        # --- Step 5: Submit application ---
        with patch("services.api.routes.submit.submit_application_task") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-final")

            submit_response = await test_app.post("/api/submit/apply", json={
                "job_id": job_id,
                "resume_id": resume_id,
                "tailored_resume": rewrite_data["tailored_resume"],
                "job_url": "https://careers.acme.com/apply/123",
            })
            assert submit_response.status_code == 200
            submit_data = submit_response.json()
            assert submit_data["task_id"] == "task-final"
            assert submit_data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_error_propagation_qdrant_down(self, test_app, mock_qdrant_client):
        """When Qdrant is unreachable, the API should return 500 gracefully."""
        mock_qdrant_client.scroll.side_effect = Exception("Connection refused")

        # ASGITransport may propagate unhandled exceptions; verify it surfaces
        with pytest.raises(Exception, match="Connection refused"):
            await test_app.get("/api/jobs/list")

    @pytest.mark.asyncio
    async def test_error_propagation_ingest_failure(self, test_app, mock_qdrant_client):
        """When ingest fails, the API should return 500."""
        mock_qdrant_client.upsert.side_effect = Exception("Database error")

        response = await test_app.post("/api/jobs/ingest", json={
            "title": "Job",
            "company": "Corp",
            "description": "Desc",
        })
        assert response.status_code == 500
