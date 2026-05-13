"""
Tier 3 — FastAPI integration tests for /api/submit routes.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestSubmitAPI:
    @pytest.mark.asyncio
    async def test_submit_application(self, test_app):
        with patch("services.api.routes.submit.submit_application_task") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-123")

            response = await test_app.post("/api/submit/apply", json={
                "job_id": "job-1",
                "resume_id": "resume-1",
                "tailored_resume": {"tailored_summary": "Test"},
                "job_url": "https://careers.example.com/apply",
            })
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_submit_missing_fields(self, test_app):
        response = await test_app.post("/api/submit/apply", json={
            "job_id": "job-1",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_submission_status(self, test_app):
        with patch("services.tasks.celery_app.celery_app") as mock_celery:
            mock_result = MagicMock()
            mock_result.state = "SUCCESS"
            mock_result.ready.return_value = True
            mock_result.result = {"status": "submitted"}
            mock_celery.AsyncResult.return_value = mock_result

            response = await test_app.get("/api/submit/status/task-123")
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_get_submission_history(self, test_app):
        response = await test_app.get("/api/submit/history")
        assert response.status_code == 200
        data = response.json()
        assert "submissions" in data
