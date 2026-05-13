"""
API Client — HTTP client for the orchestrator backend.
"""
import httpx
from typing import Optional

API_BASE = "http://orchestrator:8001"


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


def api_get(path: str, params: Optional[dict] = None) -> dict:
    with httpx.Client(timeout=30) as client:
        r = client.get(_url(path), params=params)
        r.raise_for_status()
        return r.json()


def api_post(path: str, json_data: dict) -> dict:
    with httpx.Client(timeout=120) as client:
        r = client.post(_url(path), json=json_data)
        r.raise_for_status()
        return r.json()


def api_upload(path: str, file_bytes: bytes, filename: str, params: Optional[dict] = None) -> dict:
    with httpx.Client(timeout=60) as client:
        files = {"file": (filename, file_bytes)}
        r = client.post(_url(path), files=files, params=params)
        r.raise_for_status()
        return r.json()
