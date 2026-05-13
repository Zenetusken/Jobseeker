"""
Shared test fixtures for the Jobseeker test suite.
Provides mocked Qdrant, embeddings, vLLM, and FastAPI TestClient.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Sample Data Fixtures
# ============================================================

@pytest.fixture
def sample_job_payload():
    return {
        "title": "Senior Cybersecurity Engineer",
        "company": "Acme Defense Corp",
        "location": "Washington, DC",
        "description": (
            "Seeking a Senior Cybersecurity Engineer with CISSP certification "
            "and Top Secret clearance. Must have experience with SIEM, Splunk, "
            "firewall management (Palo Alto, Cisco ASA), and incident response. "
            "Knowledge of MITRE ATT&CK framework and NIST 800-53 required."
        ),
        "url": "https://careers.acme.com/apply/123",
        "source": "indeed",
        "required_certs": ["CISSP", "Security+"],
        "required_skills": ["SIEM", "Splunk", "Firewall", "Incident Response"],
        "clearance_level": "Top Secret",
    }


@pytest.fixture
def sample_resume_payload():
    return {
        "label": "default",
        "filename": "resume.pdf",
        "raw_text": (
            "Jane Doe\njane@example.com\nWashington, DC\n\n"
            "Summary: Cybersecurity engineer with 5 years of experience in SIEM "
            "management and incident response.\n\n"
            "Security Analyst at Tech Corp (2020-Present)\n"
            "  - Managed Splunk SIEM deployment across 500+ endpoints\n"
            "  - Led incident response for 50+ security events\n"
            "  - Configured Palo Alto firewalls and Cisco ASA\n\n"
            "Skills: SIEM, Splunk, Python, Firewall, Incident Response\n"
            "Certifications: CISSP, Security+, CEH"
        ),
        "structured": {
            "contact_info": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "555-0123",
                "location": "Washington, DC",
            },
            "summary": "Cybersecurity engineer with 5 years of experience.",
            "experience": [
                {
                    "title": "Security Analyst",
                    "company": "Tech Corp",
                    "start_date": "2020",
                    "end_date": "Present",
                    "bullets": [
                        "Managed Splunk SIEM deployment across 500+ endpoints",
                        "Led incident response for 50+ security events",
                        "Configured Palo Alto firewalls and Cisco ASA",
                    ],
                }
            ],
            "education": [
                {"degree": "BS Computer Science", "school": "MIT", "graduation_year": "2018"}
            ],
            "certifications": [
                {"name": "CISSP"}, {"name": "Security+"}, {"name": "CEH"}
            ],
            "skills": ["SIEM", "Splunk", "Python", "Firewall", "Incident Response"],
        },
        "certs": ["CISSP", "Security+", "CEH"],
        "skills": ["SIEM", "Splunk", "Python", "Firewall", "Incident Response"],
        "clearance_level": "",
    }


@pytest.fixture
def sample_tailored_resume():
    return {
        "tailored_summary": (
            "Senior Cybersecurity Engineer with 5+ years of hands-on experience "
            "in SIEM architecture, incident response, and enterprise firewall management."
        ),
        "experience": [
            {
                "title": "Security Analyst",
                "company": "Tech Corp",
                "bullets": [
                    {
                        "original": "Managed Splunk SIEM deployment across 500+ endpoints",
                        "tailored": (
                            "Architected and managed enterprise Splunk SIEM deployment "
                            "across 500+ endpoints, aligning with NIST 800-53 monitoring requirements"
                        ),
                        "rationale": "Added NIST framework reference to match job requirements",
                    },
                    {
                        "original": "Led incident response for 50+ security events",
                        "tailored": (
                            "Led incident response for 50+ security events using "
                            "MITRE ATT&CK framework for threat classification and remediation"
                        ),
                        "rationale": "Incorporated MITRE ATT&CK terminology from job description",
                    },
                ],
            }
        ],
        "skills_highlighted": ["SIEM", "Splunk", "Firewall", "Incident Response", "Palo Alto", "Cisco ASA"],
        "certifications_emphasized": ["CISSP", "Security+"],
        "overall_rationale": "Tailored to emphasize NIST and MITRE ATT&CK framework experience.",
    }


# ============================================================
# Pre-collection mocks to prevent CUDA init during imports
# ============================================================

def pytest_configure(config):
    """Mock heavy dependencies before test collection to prevent CUDA init."""
    import sys
    from unittest.mock import MagicMock

    # Prevent SentenceTransformer from trying to use CUDA
    mock_st = MagicMock()
    mock_st_instance = MagicMock()
    mock_st_instance.get_sentence_embedding_dimension.return_value = 1024
    mock_st_instance.encode.return_value = [0.1] * 1024
    mock_st.return_value = mock_st_instance

    # Mock torch.cuda to prevent "no NVIDIA driver" errors
    try:
        import torch
        torch.cuda.is_available = MagicMock(return_value=False)
        torch.cuda.device_count = MagicMock(return_value=0)
    except ImportError:
        pass

    sys.modules["sentence_transformers"] = MagicMock()
    sys.modules["sentence_transformers"].SentenceTransformer = mock_st

    # Mock QdrantClient to prevent connection attempts.
    # Any code that creates QdrantClient() will get a MagicMock.
    try:
        import qdrant_client
        qdrant_client.QdrantClient = MagicMock
    except ImportError:
        pass


# ============================================================
# Mock Fixtures
# ============================================================

@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client with scroll, search, upsert, delete.
    Patches get_qdrant_client in all modules that use it."""
    from unittest.mock import patch

    client = MagicMock()
    client.scroll.return_value = ([], None)
    client.search.return_value = []
    client.collection_exists.return_value = True

    # Patch everywhere get_qdrant_client is imported
    with patch("services.qdrant.init_collections.get_qdrant_client", return_value=client):
        with patch("services.api.routes.jobs.get_qdrant_client", return_value=client):
            with patch("services.api.routes.resumes.get_qdrant_client", return_value=client):
                with patch("services.matching.matcher.get_qdrant_client", return_value=client):
                    with patch("services.rewrite.rewriter.get_qdrant_client", return_value=client):
                        with patch("services.scraper.ingest.get_qdrant_client", return_value=client):
                            yield client


@pytest.fixture
def mock_embedding():
    """Mock embedding that returns fixed 1024-dim vectors."""
    with patch("services.embeddings.embedding_service.encode_text") as mock_encode:
        mock_encode.return_value = [0.1] * 1024
        yield mock_encode


@pytest.fixture
def mock_embedding_batch():
    """Mock batch embedding."""
    with patch("services.embeddings.embedding_service.encode_batch") as mock_batch:
        mock_batch.return_value = [[0.1] * 1024]
        yield mock_batch


@pytest.fixture
def mock_vllm_client():
    """Mock OpenAI client for vLLM calls."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()

    import json
    from services.rewrite.schema import RewriteOutput

    sample = RewriteOutput(
        tailored_summary="Tailored summary text.",
        experience=[
            {
                "title": "Security Analyst",
                "company": "Tech Corp",
                "bullets": [
                    {
                        "original": "Original bullet",
                        "tailored": "Tailored bullet",
                        "rationale": "Better match",
                    }
                ],
            }
        ],
        skills_highlighted=["SIEM", "Splunk"],
        certifications_emphasized=["CISSP"],
        overall_rationale="Good match.",
    )

    mock_message.content = json.dumps(sample.model_dump())
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("services.rewrite.rewriter._get_vllm_client", return_value=mock_client):
        yield mock_client


# ============================================================
# FastAPI TestClient Fixture
# ============================================================

@pytest.fixture
def test_app(mock_qdrant_client, mock_embedding):
    """FastAPI TestClient with mocked backend services."""
    from services.api.main import app
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client


# ============================================================
# Settings Override Fixture
# ============================================================

@pytest.fixture
def test_settings():
    """Override settings for test environment."""
    with patch("config.settings.settings") as mock_settings:
        mock_settings.vllm_base_url = "http://vllm:8000/v1"
        mock_settings.qdrant_url = "http://qdrant:6333"
        mock_settings.qdrant_collection_jobs = "job_descriptions"
        mock_settings.qdrant_collection_resumes = "resumes"
        mock_settings.qdrant_vector_size = 1024
        mock_settings.vllm_model_name = "test-model"
        mock_settings.embedding_model_name = "test-embedding"
        mock_settings.embedding_device = "cpu"
        mock_settings.celery_broker_url = "redis://redis:6379/0"
        mock_settings.celery_result_backend = "redis://redis:6379/0"
        yield mock_settings
