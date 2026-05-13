"""
Tier 2 — Core service tests for pdf_generator.py.
Tests PDF generation from tailored resume dicts.
"""
import os
import tempfile
import pytest
from services.automation.pdf_generator import (
    generate_tailored_resume_pdf,
    generate_pdf_bytes,
)


class TestGenerateTailoredResumePdf:
    @pytest.fixture
    def full_resume(self):
        return {
            "contact_info": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "555-0123",
                "location": "Washington, DC",
                "linkedin": "linkedin.com/in/janedoe",
            },
            "tailored_summary": "Experienced cybersecurity professional with 5+ years.",
            "skills_highlighted": ["SIEM", "Splunk", "Python", "Firewall"],
            "certifications_emphasized": ["CISSP", "CEH"],
            "experience": [
                {
                    "title": "Security Analyst",
                    "company": "Tech Corp",
                    "bullets": [
                        {"original": "Managed SIEM", "tailored": "Architected SIEM deployment"},
                        {"original": "Led IR", "tailored": "Led incident response using MITRE ATT&CK"},
                    ],
                }
            ],
            "education": [
                {"degree": "BS Computer Science", "school": "MIT", "graduation_year": "2018"}
            ],
        }

    @pytest.fixture
    def minimal_resume(self):
        return {
            "contact_info": {"name": "John"},
            "tailored_summary": "",
        }

    def test_creates_file(self, full_resume):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name

        try:
            result = generate_tailored_resume_pdf(full_resume, output_path)
            assert result == output_path
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_file_is_valid_pdf(self, full_resume):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name

        try:
            generate_tailored_resume_pdf(full_resume, output_path)
            with open(output_path, "rb") as f:
                header = f.read(5)
            assert header == b"%PDF-"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_minimal_resume(self, minimal_resume):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name

        try:
            result = generate_tailored_resume_pdf(minimal_resume, output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_empty_resume(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name

        try:
            result = generate_tailored_resume_pdf({}, output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_missing_contact_info(self):
        resume = {"tailored_summary": "Just a summary"}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name

        try:
            result = generate_tailored_resume_pdf(resume, output_path)
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestGeneratePdfBytes:
    def test_returns_bytes(self):
        resume = {
            "contact_info": {"name": "Test User", "email": "test@test.com"},
            "tailored_summary": "A summary",
            "skills_highlighted": ["Python"],
        }
        result = generate_pdf_bytes(resume)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_pdf_header(self):
        resume = {"contact_info": {"name": "Test"}}
        result = generate_pdf_bytes(resume)
        assert result[:5] == b"%PDF-"

    def test_empty_resume(self):
        result = generate_pdf_bytes({})
        assert isinstance(result, bytes)
        assert len(result) > 0
