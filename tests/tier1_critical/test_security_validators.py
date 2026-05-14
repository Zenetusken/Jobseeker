"""
Tier 1 — Critical pure-logic tests for services/api/validators.py.

Validates:
- SSRF guard (validate_job_url)
- File-size guard (check_upload_size)
- Filename sanitizer (sanitize_filename)
- UUID validator (validate_uuid)
"""
import pytest
from unittest.mock import patch
from fastapi import HTTPException

from services.api.validators import (
    validate_job_url,
    validate_job_url_http,
    check_upload_size,
    sanitize_filename,
    validate_uuid,
)


# ---------------------------------------------------------------------------
# SSRF guard — validate_job_url
# ---------------------------------------------------------------------------

class TestValidateJobUrl:

    def test_valid_public_https_url_is_allowed(self):
        url = "https://www.indeed.com/jobs?q=cybersecurity"
        assert validate_job_url(url) == url

    def test_valid_public_http_url_is_allowed(self):
        url = "http://dice.com/jobs"
        assert validate_job_url(url) == url

    def test_empty_url_is_allowed(self):
        """Empty url (optional field) must pass without error."""
        assert validate_job_url("") == ""

    def test_file_scheme_is_blocked(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_job_url("file:///etc/passwd")

    def test_ftp_scheme_is_blocked(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_job_url("ftp://attacker.com/payload")

    def test_localhost_is_blocked(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 0))]):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_job_url("http://localhost/admin")

    def test_rfc1918_10_block_is_blocked(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("10.0.0.1", 0))]):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_job_url("http://internal.corp/api")

    def test_rfc1918_172_block_is_blocked(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("172.20.0.5", 0))]):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_job_url("http://172.20.0.5/secret")

    def test_rfc1918_192_168_is_blocked(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("192.168.1.1", 0))]):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_job_url("http://router/admin")

    def test_link_local_metadata_endpoint_is_blocked(self):
        """AWS/GCP instance metadata endpoint must be blocked."""
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("169.254.169.254", 0))]):
            with pytest.raises(ValueError, match="private/reserved"):
                validate_job_url("http://169.254.169.254/latest/meta-data/")

    def test_url_with_no_hostname_is_blocked(self):
        with pytest.raises(ValueError, match="hostname"):
            validate_job_url("http://")

    def test_http_wrapper_raises_422_on_invalid(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 0))]):
            with pytest.raises(HTTPException) as exc_info:
                validate_job_url_http("http://localhost/")
        assert exc_info.value.status_code == 422

    def test_http_wrapper_returns_url_on_valid(self):
        url = "https://www.linkedin.com/jobs"
        result = validate_job_url_http(url)
        assert result == url


# ---------------------------------------------------------------------------
# File-size guard — check_upload_size
# ---------------------------------------------------------------------------

class TestCheckUploadSize:

    def test_under_limit_passes(self):
        content = b"x" * 1000
        check_upload_size(content, max_bytes=10_485_760)

    def test_at_limit_passes(self):
        content = b"x" * 10_485_760
        check_upload_size(content, max_bytes=10_485_760)

    def test_over_limit_raises_413(self):
        content = b"x" * (10_485_760 + 1)
        with pytest.raises(HTTPException) as exc_info:
            check_upload_size(content, max_bytes=10_485_760)
        assert exc_info.value.status_code == 413

    def test_error_message_contains_size(self):
        content = b"x" * (5_242_881)
        with pytest.raises(HTTPException) as exc_info:
            check_upload_size(content, max_bytes=5_242_880, label="resume")
        assert "resume" in exc_info.value.detail or "MB" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Filename sanitizer — sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:

    def test_normal_filename_unchanged(self):
        assert sanitize_filename("resume.pdf") == "resume.pdf"

    def test_path_traversal_stripped(self):
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert ".." not in result
        assert result == "passwd"

    def test_windows_path_stripped(self):
        result = sanitize_filename(r"C:\Users\attacker\evil.exe")
        assert "\\" not in result
        assert result == "evil.exe"

    def test_null_byte_removed(self):
        result = sanitize_filename("resume\x00.pdf")
        assert "\x00" not in result

    def test_long_filename_truncated(self):
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name, max_length=255)
        assert len(result) <= 255

    def test_empty_filename_returns_upload(self):
        assert sanitize_filename("") == "upload"


# ---------------------------------------------------------------------------
# UUID validator — validate_uuid
# ---------------------------------------------------------------------------

class TestValidateUuid:

    def test_valid_uuid_passes(self):
        valid = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_uuid(valid) == valid

    def test_arbitrary_string_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("not-a-uuid", field_name="task_id")
        assert exc_info.value.status_code == 422
        assert "task_id" in exc_info.value.detail

    def test_empty_string_raises_422(self):
        with pytest.raises(HTTPException):
            validate_uuid("")

    def test_sql_injection_attempt_raises_422(self):
        with pytest.raises(HTTPException):
            validate_uuid("'; DROP TABLE tasks; --")

    def test_almost_valid_uuid_raises_422(self):
        with pytest.raises(HTTPException):
            validate_uuid("550e8400-e29b-41d4-a716-44665544000Z")
