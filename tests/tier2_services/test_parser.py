"""
Tier 2 — Core service tests for resume/parser.py.
Tests PDF, DOCX, TXT parsing and JSON resume processing.
"""
import pytest
from unittest.mock import patch, MagicMock
from services.resume.parser import (
    parse_txt,
    parse_resume_file,
    parse_resume_json,
)


class TestParseTxt:
    def test_utf8_text(self):
        result = parse_txt(b"Hello World")
        assert result == "Hello World"

    def test_ascii_text(self):
        result = parse_txt(b"Plain ASCII text")
        assert result == "Plain ASCII text"

    def test_empty_bytes(self):
        result = parse_txt(b"")
        assert result == ""

    def test_invalid_utf8_replaced(self):
        result = parse_txt(b"\xff\xfe invalid")
        assert "invalid" in result


class TestParseResumeFile:
    def test_txt_file(self):
        result = parse_resume_file(b"Resume content here", "resume.txt")
        assert result["raw_text"] == "Resume content here"
        assert "required_certs" in result
        assert "required_skills" in result

    def test_md_file(self):
        result = parse_resume_file(b"# Resume\nContent", "resume.md")
        assert "# Resume" in result["raw_text"]

    def test_text_extension(self):
        result = parse_resume_file(b"Content", "resume.text")
        assert result["raw_text"] == "Content"

    @patch("services.resume.parser.parse_pdf")
    def test_pdf_file(self, mock_parse_pdf):
        mock_parse_pdf.return_value = "PDF extracted text"
        result = parse_resume_file(b"fake pdf bytes", "resume.pdf")
        assert result["raw_text"] == "PDF extracted text"
        mock_parse_pdf.assert_called_once()

    @patch("services.resume.parser.parse_docx")
    def test_docx_file(self, mock_parse_docx):
        mock_parse_docx.return_value = "DOCX extracted text"
        result = parse_resume_file(b"fake docx bytes", "resume.docx")
        assert result["raw_text"] == "DOCX extracted text"
        mock_parse_docx.assert_called_once()

    @patch("services.resume.parser.parse_docx")
    def test_doc_file(self, mock_parse_docx):
        mock_parse_docx.return_value = "DOC extracted text"
        result = parse_resume_file(b"fake doc bytes", "resume.doc")
        assert result["raw_text"] == "DOC extracted text"

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            parse_resume_file(b"data", "resume.xyz")

    def test_no_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            parse_resume_file(b"data", "noextension")

    @patch("services.resume.parser.parse_txt")
    def test_empty_extracted_text_raises(self, mock_parse):
        mock_parse.return_value = ""
        with pytest.raises(ValueError, match="No text could be extracted"):
            parse_resume_file(b"empty", "resume.txt")

    @patch("services.resume.parser.parse_txt")
    def test_whitespace_only_raises(self, mock_parse):
        mock_parse.return_value = "   \n  "
        with pytest.raises(ValueError, match="No text could be extracted"):
            parse_resume_file(b"whitespace", "resume.txt")

    def test_metadata_extraction(self):
        result = parse_resume_file(
            b"Security Engineer with CISSP and Top Secret clearance. SIEM and Splunk experience.",
            "resume.txt",
        )
        assert "CISSP" in result.get("required_certs", [])
        assert "SIEM" in result.get("required_skills", [])


class TestParseResumeJson:
    def test_full_json(self):
        data = {
            "contact_info": {
                "name": "Jane Doe",
                "email": "jane@test.com",
                "location": "DC",
            },
            "summary": "Security engineer",
            "experience": [
                {
                    "title": "Analyst",
                    "company": "Corp",
                    "bullets": ["Did security stuff"],
                }
            ],
            "education": [{"degree": "BS", "school": "MIT"}],
            "certifications": [{"name": "CISSP"}],
            "skills": ["SIEM", "Python"],
        }
        result = parse_resume_json(data)
        assert "Jane Doe" in result["raw_text"]
        assert "Security engineer" in result["raw_text"]
        assert "Analyst at Corp" in result["raw_text"]
        assert "CISSP" in result["raw_text"]
        assert "SIEM" in result["raw_text"]
        assert result["structured"] == data

    def test_minimal_json(self):
        data = {"contact_info": {"name": "John"}}
        result = parse_resume_json(data)
        assert "John" in result["raw_text"]

    def test_empty_json(self):
        result = parse_resume_json({})
        assert result["raw_text"] == ""
        assert result["structured"] == {}

    def test_metadata_extraction(self):
        data = {
            "contact_info": {"name": "Jane"},
            "skills": ["SIEM", "Splunk", "Python"],
            "certifications": [{"name": "CISSP"}, {"name": "CEH"}],
        }
        result = parse_resume_json(data)
        assert "CISSP" in result.get("required_certs", [])
        assert "SIEM" in result.get("required_skills", [])
