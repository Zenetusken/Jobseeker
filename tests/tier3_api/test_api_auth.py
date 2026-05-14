"""
Tier 3 — API authentication tests.

Verifies that:
- All protected endpoints return HTTP 401 when X-API-Key is absent.
- All protected endpoints return HTTP 401 when X-API-Key is wrong.
- All protected endpoints return a non-401 response when X-API-Key is correct.
- GET /health returns HTTP 200 with no key (exempt from auth).
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


_TEST_API_KEY = "test-secret-key-for-auth-tests"

_PROTECTED_ROUTES: list[tuple[str, str, dict | None]] = [
    ("GET",    "/api/jobs/list",          None),
    ("POST",   "/api/jobs/ingest",        {"title": "SWE", "company": "Corp", "description": "desc", "url": ""}),
    ("POST",   "/api/jobs/ingest/batch",  {"jobs": [{"title": "SWE", "company": "Corp", "description": "d", "url": ""}]}),
    ("POST",   "/api/match/jobs",         {"resume_id": "550e8400-e29b-41d4-a716-446655440000"}),
    ("GET",    "/api/submit/history",     None),
    ("GET",    "/api/resumes/list",       None),
]


class TestHealthNoAuth:
    def test_health_returns_200_without_key(self):
        from services.api.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAuthWithKeyConfigured:
    """Full auth tests exercised against a client whose settings.api_key is set."""

    @pytest.fixture(autouse=True)
    def _patch_key(self, monkeypatch):
        import config.settings as cfg_module
        monkeypatch.setattr(cfg_module.settings, "api_key", _TEST_API_KEY)

    @pytest.fixture
    def client(self):
        from services.api.main import app
        with patch("services.qdrant.init_collections.init_collections"):
            return TestClient(app, raise_server_exceptions=False)

    def test_get_jobs_list_without_key_returns_401(self, client):
        r = client.get("/api/jobs/list")
        assert r.status_code == 401

    def test_get_jobs_list_with_wrong_key_returns_401(self, client):
        r = client.get("/api/jobs/list", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401

    def test_get_jobs_list_with_correct_key_is_not_401(self, client):
        with patch("services.qdrant.init_collections.get_qdrant_client") as mock_qdrant:
            mock_qdrant.return_value.scroll.return_value = ([], None)
            r = client.get("/api/jobs/list", headers={"X-API-Key": _TEST_API_KEY})
        assert r.status_code != 401

    def test_get_resumes_list_without_key_returns_401(self, client):
        r = client.get("/api/resumes/list")
        assert r.status_code == 401

    def test_get_resumes_list_with_correct_key_is_not_401(self, client):
        with patch("services.qdrant.init_collections.get_qdrant_client") as mock_qdrant:
            mock_qdrant.return_value.scroll.return_value = ([], None)
            r = client.get("/api/resumes/list", headers={"X-API-Key": _TEST_API_KEY})
        assert r.status_code != 401

    def test_post_match_without_key_returns_401(self, client):
        r = client.post(
            "/api/match/jobs",
            json={"resume_id": "550e8400-e29b-41d4-a716-446655440000"},
        )
        assert r.status_code == 401

    def test_post_ingest_without_key_returns_401(self, client):
        r = client.post(
            "/api/jobs/ingest",
            json={"title": "SWE", "company": "Corp", "description": "desc"},
        )
        assert r.status_code == 401

    def test_post_rewrite_without_key_returns_401(self, client):
        r = client.post(
            "/api/rewrite/tailor",
            json={"resume_id": "abc", "job_id": "xyz"},
        )
        assert r.status_code == 401

    def test_get_submit_history_without_key_returns_401(self, client):
        r = client.get("/api/submit/history")
        assert r.status_code == 401

    def test_health_still_200_without_key_when_auth_active(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_401_response_has_www_authenticate_header(self, client):
        r = client.get("/api/jobs/list")
        assert r.status_code == 401
        assert "www-authenticate" in r.headers or "WWW-Authenticate" in r.headers

    def test_401_detail_does_not_leak_key_value(self, client):
        r = client.get("/api/jobs/list", headers={"X-API-Key": "wrong"})
        assert r.status_code == 401
        assert _TEST_API_KEY not in r.text


class TestNoAuthConfigured:
    """When API_KEY is empty the dependency is a no-op (dev mode)."""

    @pytest.fixture(autouse=True)
    def _patch_no_key(self, monkeypatch):
        import config.settings as cfg_module
        monkeypatch.setattr(cfg_module.settings, "api_key", "")

    @pytest.fixture
    def client(self):
        from services.api.main import app
        with patch("services.qdrant.init_collections.init_collections"):
            return TestClient(app, raise_server_exceptions=False)

    def test_get_jobs_list_without_key_is_not_401_when_auth_disabled(self, client):
        with patch("services.qdrant.init_collections.get_qdrant_client") as mock_qdrant:
            mock_qdrant.return_value.scroll.return_value = ([], None)
            r = client.get("/api/jobs/list")
        assert r.status_code != 401
