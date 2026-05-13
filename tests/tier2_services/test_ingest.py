"""
Tier 2 — Core service tests for scraper/ingest.py.
Tests job ingestion with mocked Qdrant and embeddings.
"""
import pytest
from unittest.mock import MagicMock, patch
from services.scraper.ingest import ingest_job_text, ingest_job_batch


class TestIngestJobText:
    def test_returns_job_id(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            job_id = ingest_job_text(
                title="Security Engineer",
                company="Acme",
                description="Looking for CISSP certified engineer",
                location="Remote",
                url="https://example.com",
                source="indeed",
            )
            assert isinstance(job_id, str)
            assert len(job_id) > 0

    def test_calls_qdrant_upsert(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            ingest_job_text(
                title="Engineer",
                company="Corp",
                description="Job description",
            )
            mock_qdrant_client.upsert.assert_called_once()

    def test_upsert_payload_structure(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            ingest_job_text(
                title="Security Engineer",
                company="Acme",
                description="SIEM and CISSP required",
                location="DC",
                url="https://example.com",
                source="manual",
            )

            call_args = mock_qdrant_client.upsert.call_args
            # Check that points were passed
            kwargs = call_args.kwargs
            assert "points" in kwargs
            points = kwargs["points"]
            assert len(points) == 1
            point = points[0]
            assert "id" in point
            assert "vector" in point
            assert "payload" in point
            payload = point["payload"]
            assert payload["title"] == "Security Engineer"
            assert payload["company"] == "Acme"
            assert payload["source"] == "manual"

    def test_default_values(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            job_id = ingest_job_text(
                title="Job",
                company="Corp",
                description="Desc",
            )
            assert job_id is not None

    def test_metadata_extracted(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            ingest_job_text(
                title="Security Engineer",
                company="Acme",
                description="CISSP and Top Secret clearance required. SIEM experience needed.",
            )

            payload = mock_qdrant_client.upsert.call_args.kwargs["points"][0]["payload"]
            assert "CISSP" in payload.get("required_certs", [])
            assert payload.get("clearance_level") == "Top Secret"


class TestIngestJobBatch:
    def test_returns_list_of_ids(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            jobs = [
                {"title": "Job 1", "company": "C1", "description": "Desc 1"},
                {"title": "Job 2", "company": "C2", "description": "Desc 2"},
                {"title": "Job 3", "company": "C3", "description": "Desc 3"},
            ]
            ids = ingest_job_batch(jobs)
            assert len(ids) == 3
            assert all(isinstance(jid, str) for jid in ids)

    def test_empty_list(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            ids = ingest_job_batch([])
            assert ids == []

    def test_handles_missing_fields(self, mock_qdrant_client, mock_embedding):
        with patch("services.scraper.ingest.get_qdrant_client", return_value=mock_qdrant_client):
            jobs = [{"description": "Only description"}]
            ids = ingest_job_batch(jobs)
            assert len(ids) == 1
