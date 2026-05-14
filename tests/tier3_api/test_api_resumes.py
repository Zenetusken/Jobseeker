"""
Tier 3 — FastAPI integration tests for /api/resumes routes.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestResumesAPI:
    @pytest.mark.asyncio
    async def test_upload_resume_file(self, test_app, mock_qdrant_client, mock_embedding):
        with patch("services.api.routes.resumes.parse_resume_file") as mock_parse:
            mock_parse.return_value = {
                "raw_text": "Resume text",
                "certs": ["CISSP"],
                "skills": ["SIEM"],
                "clearance_level": "",
                "structured": None,
            }

            response = await test_app.post(
                "/api/resumes/upload",
                files={"file": ("resume.txt", b"Resume content", "text/plain")},
                params={"label": "my-resume"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "parsed"
            assert "resume_id" in data
            assert data["label"] == "my-resume"

    @pytest.mark.asyncio
    async def test_upload_no_filename(self, test_app):
        response = await test_app.post(
            "/api/resumes/upload",
            files={"file": ("", b"content", "text/plain")},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, test_app):
        with patch("services.api.routes.resumes.parse_resume_file") as mock_parse:
            mock_parse.side_effect = ValueError("Unsupported file format: .xyz")
            response = await test_app.post(
                "/api/resumes/upload",
                files={"file": ("resume.xyz", b"content", "application/octet-stream")},
            )
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_json_resume(self, test_app, mock_qdrant_client, mock_embedding):
        response = await test_app.post("/api/resumes/upload/json", json={
            "resume": {
                "contact_info": {
                    "name": "Jane Doe",
                    "email": "jane@test.com",
                },
                "summary": "Security engineer",
                "experience": [
                    {
                        "title": "Analyst",
                        "company": "Corp",
                        "bullets": ["Did security"],
                    }
                ],
                "skills": ["SIEM", "Python"],
                "certifications": [{"name": "CISSP"}],
            },
            "label": "json-resume",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "parsed"
        assert "resume_id" in data

    @pytest.mark.asyncio
    async def test_upload_invalid_json_resume(self, test_app):
        response = await test_app.post("/api/resumes/upload/json", json={
            "resume": "not_a_dict",
            "label": "bad",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_resumes(self, test_app, mock_qdrant_client):
        mock_record = MagicMock()
        mock_record.id = "resume-1"
        mock_record.payload = {
            "label": "default",
            "filename": "resume.pdf",
            "certs": ["CISSP"],
            "skills": ["SIEM"],
            "clearance_level": "",
        }
        mock_qdrant_client.scroll.return_value = ([mock_record], None)

        response = await test_app.get("/api/resumes/list")
        assert response.status_code == 200
        data = response.json()
        assert "resumes" in data
        assert len(data["resumes"]) == 1

    @pytest.mark.asyncio
    async def test_get_resume_found(self, test_app, mock_qdrant_client):
        mock_record = MagicMock()
        mock_record.id = "resume-1"
        mock_record.payload = {
            "label": "default",
            "filename": "resume.pdf",
            "raw_text": "Full resume text",
            "certs": ["CISSP"],
            "skills": ["SIEM"],
            "clearance_level": "",
        }
        mock_qdrant_client.retrieve.return_value = [mock_record]

        response = await test_app.get("/api/resumes/resume-1")
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "default"

    @pytest.mark.asyncio
    async def test_get_resume_not_found(self, test_app, mock_qdrant_client):
        mock_qdrant_client.retrieve.return_value = []

        response = await test_app.get("/api/resumes/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_resume(self, test_app, mock_qdrant_client):
        response = await test_app.delete("/api/resumes/resume-1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
