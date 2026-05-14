"""
Job Routes — Ingest, list, and manage job descriptions.
"""
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger
from qdrant_client.models import PointIdsList

from services.scraper.ingest import ingest_job_text, ingest_job_batch
from services.qdrant.init_collections import get_qdrant_client
from services.api.validators import (
    check_upload_size,
    sanitize_filename,
)
from config.settings import settings

router = APIRouter()


class JobIngestRequest(BaseModel):
    title: str = Field(..., max_length=500)
    company: str = Field(..., max_length=500)
    location: str = Field("", max_length=300)
    description: str = Field(..., max_length=settings.max_description_length)
    url: str = Field("", max_length=2048)
    source: str = Field("manual", max_length=100)


class JobIngestBatchRequest(BaseModel):
    jobs: list[JobIngestRequest] = Field(..., max_length=settings.max_batch_size)


@router.post("/ingest")
async def ingest_single_job(req: JobIngestRequest):
    """Ingest a single job description."""
    try:
        job_id = ingest_job_text(
            title=req.title,
            company=req.company,
            location=req.location,
            description=req.description,
            url=req.url,
            source=req.source,
        )
        return {"status": "ingested", "job_id": job_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ingest/batch")
async def ingest_jobs_batch(req: JobIngestBatchRequest):
    """Ingest multiple job descriptions."""
    try:
        jobs_dicts = [j.model_dump() for j in req.jobs]
        job_ids = ingest_job_batch(jobs_dicts)
        return {"status": "ingested", "count": len(job_ids), "job_ids": job_ids}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch job ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ingest/file")
async def ingest_job_file(file: UploadFile = File(...)):
    """Upload and ingest a job description from a text file."""
    content = await file.read()
    check_upload_size(content, settings.max_upload_bytes, label="job file")
    safe_name = sanitize_filename(file.filename or "upload")
    text = content.decode("utf-8", errors="replace")
    if len(text) > settings.max_description_length:
        text = text[: settings.max_description_length]
        logger.warning(f"Job file '{safe_name}' truncated to {settings.max_description_length} chars")
    job_id = ingest_job_text(
        title=safe_name,
        company="Unknown",
        description=text,
        source="file_upload",
    )
    return {"status": "ingested", "job_id": job_id, "filename": safe_name}


@router.get("/list")
async def list_jobs(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    source: Optional[str] = None,
):
    """List ingested jobs with optional source filter."""
    client = get_qdrant_client()
    scroll_filter = None
    if source:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        scroll_filter = Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=source))]
        )

    records, next_offset = client.scroll(
        collection_name=settings.qdrant_collection_jobs,
        scroll_filter=scroll_filter,
        limit=limit,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )

    jobs = []
    for r in records:
        jobs.append({
            "id": r.id,
            "title": r.payload.get("title", ""),
            "company": r.payload.get("company", ""),
            "location": r.payload.get("location", ""),
            "source": r.payload.get("source", ""),
            "required_certs": r.payload.get("required_certs", []),
            "required_skills": r.payload.get("required_skills", []),
            "clearance_level": r.payload.get("clearance_level", ""),
            "url": r.payload.get("url", ""),
        })

    return {"jobs": jobs, "total": len(jobs), "next_offset": next_offset}


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get full job details by ID."""
    client = get_qdrant_client()
    results = client.retrieve(
        collection_name=settings.qdrant_collection_jobs,
        ids=[job_id],
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        raise HTTPException(status_code=404, detail="Job not found")
    r = results[0]
    return {
        "id": r.id,
        "title": r.payload.get("title", ""),
        "company": r.payload.get("company", ""),
        "location": r.payload.get("location", ""),
        "description": r.payload.get("description", ""),
        "source": r.payload.get("source", ""),
        "url": r.payload.get("url", ""),
        "required_certs": r.payload.get("required_certs", []),
        "required_skills": r.payload.get("required_skills", []),
        "clearance_level": r.payload.get("clearance_level", ""),
    }


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a job by ID."""
    client = get_qdrant_client()
    client.delete(
        collection_name=settings.qdrant_collection_jobs,
        points_selector=PointIdsList(points=[job_id]),
    )
    return {"status": "deleted", "job_id": job_id}
