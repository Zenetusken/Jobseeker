"""
Input validators shared across API routes.

validate_job_url  — SSRF guard for Playwright-navigated URLs.
check_upload_size — file-size guard; raises HTTP 413 before parsing.
sanitize_filename — strips path separators and limits length.
validate_uuid     — ensures a string is a well-formed UUID.
"""
import ipaddress
import socket
import urllib.parse
import os
import uuid as _uuid_mod

from fastapi import HTTPException, status


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("100.64.0.0/10"),   # CGNAT
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_ALLOWED_SCHEMES = {"http", "https"}


def validate_job_url(url: str) -> str:
    """Validate that *url* is a public HTTP/HTTPS URL.

    Raises ``ValueError`` (suitable for Pydantic field_validator) if:
    - scheme is not http or https
    - host resolves to a private / loopback / link-local address
    - host is empty

    Returns the original url string on success.
    """
    if not url:
        return url

    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{parsed.scheme}' is not allowed. Only http and https are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    try:
        resolved_ip = socket.getaddrinfo(hostname, None)[0][4][0]
        ip_obj = ipaddress.ip_address(resolved_ip)
    except (socket.gaierror, ValueError) as exc:
        raise ValueError(f"Cannot resolve hostname '{hostname}': {exc}") from exc

    for network in _BLOCKED_NETWORKS:
        if ip_obj in network:
            raise ValueError(
                f"URL '{url}' resolves to a private/reserved address and is not permitted."
            )

    return url


def validate_job_url_http(url: str) -> str:
    """HTTP 422-raising wrapper for use outside Pydantic validators."""
    try:
        return validate_job_url(url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# File-size guard
# ---------------------------------------------------------------------------

def check_upload_size(content: bytes, max_bytes: int, label: str = "file") -> None:
    """Raise HTTP 413 if *content* exceeds *max_bytes*."""
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Uploaded {label} exceeds the maximum allowed size of "
                f"{max_bytes // 1_048_576} MB."
            ),
        )


# ---------------------------------------------------------------------------
# Filename sanitizer
# ---------------------------------------------------------------------------

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Strip directory separators and limit filename length."""
    name = filename.replace("\\", "/").replace("\x00", "")
    name = os.path.basename(name)
    return name[:max_length] if name else "upload"


# ---------------------------------------------------------------------------
# UUID validator
# ---------------------------------------------------------------------------

def validate_uuid(value: str, field_name: str = "id") -> str:
    """Raise HTTP 422 if *value* is not a valid UUID string."""
    try:
        _uuid_mod.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{field_name}' must be a valid UUID.",
        )
    return value
