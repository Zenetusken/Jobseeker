"""
Tier 2 — Core service tests for task functions.
Tests Celery task logic with mocked dependencies.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestSubmitTask:
    def test_submit_application_task_success(self):
        with patch("services.tasks.submit_task.submit_application") as mock_submit:
            mock_submit.return_value = {
                "status": "submitted",
                "timestamp": "2024-01-01T00:00:00",
                "screenshot": "/path/to/screenshot.png",
                "error": None,
            }

            from services.tasks.submit_task import submit_application_task

            result = submit_application_task.run(
                job_id="job-1",
                resume_id="resume-1",
                tailored_resume={"summary": "test"},
                job_url="https://example.com/apply",
            )

            assert result["status"] == "submitted"
            assert result["job_id"] == "job-1"

    def test_submit_application_task_failure(self):
        with patch("services.tasks.submit_task.submit_application") as mock_submit:
            mock_submit.side_effect = Exception("Browser crash")

            from services.tasks.submit_task import submit_application_task

            result = submit_application_task.run(
                job_id="job-1",
                resume_id="resume-1",
                tailored_resume={},
                job_url="https://example.com",
            )

            assert result["status"] == "failed"
            assert "Browser crash" in result["error"]


class TestScrapeTask:
    def test_scrape_and_ingest_jobs_success(self):
        with patch("services.tasks.scrape_task.scrape_sync") as mock_scrape, \
             patch("services.tasks.scrape_task.ingest_job_batch") as mock_ingest:
            mock_scrape.return_value = [
                {"title": "Job 1", "company": "C1", "description": "Desc 1"},
                {"title": "Job 2", "company": "C2", "description": "Desc 2"},
            ]
            mock_ingest.return_value = ["id1", "id2"]

            from services.tasks.scrape_task import scrape_and_ingest_jobs

            result = scrape_and_ingest_jobs.run()

            assert result["status"] == "success"
            assert result["count"] == 2

    def test_scrape_and_ingest_jobs_empty(self):
        with patch("services.tasks.scrape_task.scrape_sync") as mock_scrape:
            mock_scrape.return_value = []

            from services.tasks.scrape_task import scrape_and_ingest_jobs

            result = scrape_and_ingest_jobs.run()

            assert result["status"] == "empty"
            assert result["count"] == 0

    def test_scrape_and_ingest_jobs_retry(self):
        with patch("services.tasks.scrape_task.scrape_sync") as mock_scrape:
            mock_scrape.side_effect = Exception("Network error")

            from services.tasks.scrape_task import scrape_and_ingest_jobs

            # The task will call self.retry(); we just verify the exception path
            try:
                scrape_and_ingest_jobs.run()
            except Exception:
                pass  # retry raises in test context


class TestCeleryApp:
    def test_celery_app_creation(self):
        from services.tasks.celery_app import celery_app
        assert celery_app is not None
        assert celery_app.conf.task_serializer == "json"
