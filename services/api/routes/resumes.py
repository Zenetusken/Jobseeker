"""
Resume Routes — Upload, parse, and manage candidate resumes.
"""
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from qdrant_client.models import PointIdsList, PointStruct

from services.resume.parser import parse_resume_file, parse_resume_json
from services.resume.schema import ResumeSchema
from services.qdrant.init_collections import get_qdrant_client
from services.embeddings.embedding_service import encode_text
from config.settings import settings

router = APIRouter()


class ResumeJsonUpload(BaseModel):
    """Structured JSON resume upload."""
    resume: ResumeSchema
    label: str = "default"


@router.post("/upload")
async def upload_resume_file(file: UploadFile = File(...), label: str = "default"):
    """Upload and parse a resume file (PDF, DOCX, TXT)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    try:
        parsed = parse_resume_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")

    # Embed the full text
    full_text = parsed.get("raw_text", "")
    embedding = encode_text(full_text)

    # Store in Qdrant
    client = get_qdrant_client()
    point_id = str(uuid.uuid4())

    client.upsert(
        collection_name=settings.qdrant_collection_resumes,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "label": label,
                    "filename": file.filename,
                    "raw_text": full_text,
                    "structured": parsed.get("structured"),
                    "certs": parsed.get("certs", []),
                    "skills": parsed.get("skills", []),
                    "clearance_level": parsed.get("clearance_level", ""),
                },
            )
        ],
    )

    return {
        "status": "parsed",
        "resume_id": point_id,
        "label": label,
        "filename": file.filename,
        "certs_found": parsed.get("certs", []),
        "skills_found": parsed.get("skills", []),
    }


@router.post("/upload/json")
async def upload_resume_json(req: ResumeJsonUpload):
    """Upload a structured JSON resume."""
    try:
        parsed = parse_resume_json(req.resume.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    full_text = parsed.get("raw_text", "")
    embedding = encode_text(full_text)

    client = get_qdrant_client()
    point_id = str(uuid.uuid4())

    client.upsert(
        collection_name=settings.qdrant_collection_resumes,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "label": req.label,
                    "filename": "json_upload",
                    "raw_text": full_text,
                    "structured": req.resume.model_dump(),
                    "certs": parsed.get("certs", []),
                    "skills": parsed.get("skills", []),
                    "clearance_level": parsed.get("clearance_level", ""),
                },
            )
        ],
    )

    return {
        "status": "parsed",
        "resume_id": point_id,
        "label": req.label,
        "certs_found": parsed.get("certs", []),
        "skills_found": parsed.get("skills", []),
    }


@router.get("/list")
async def list_resumes():
    """List all stored resumes."""
    client = get_qdrant_client()
    records, _ = client.scroll(
        collection_name=settings.qdrant_collection_resumes,
        limit=50,
        with_payload=True,
        with_vectors=False,
    )

    resumes = []
    for r in records:
        resumes.append({
            "id": r.id,
            "label": r.payload.get("label", ""),
            "filename": r.payload.get("filename", ""),
            "certs": r.payload.get("certs", []),
            "skills": r.payload.get("skills", []),
            "clearance_level": r.payload.get("clearance_level", ""),
        })

    return {"resumes": resumes, "total": len(resumes)}


@router.get("/{resume_id}")
async def get_resume(resume_id: str):
    """Get full resume details."""
    client = get_qdrant_client()
    results = client.retrieve(
        collection_name=settings.qdrant_collection_resumes,
        ids=[resume_id],
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        raise HTTPException(status_code=404, detail="Resume not found")
    r = results[0]
    return {
        "id": r.id,
        "label": r.payload.get("label", ""),
        "filename": r.payload.get("filename", ""),
        "raw_text": r.payload.get("raw_text", ""),
        "structured": r.payload.get("structured"),
        "certs": r.payload.get("certs", []),
        "skills": r.payload.get("skills", []),
        "clearance_level": r.payload.get("clearance_level", ""),
    }


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str):
    """Delete a resume."""
    client = get_qdrant_client()
    client.delete(
        collection_name=settings.qdrant_collection_resumes,
        points_selector=PointIdsList(points=[resume_id]),
    )
    return {"status": "deleted", "resume_id": resume_id}
