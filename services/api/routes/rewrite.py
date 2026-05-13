"""
Rewrite Routes — LLM-powered resume tailoring.
Uses Foundation-Sec-8B via vLLM with Outlines constraints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from services.rewrite.rewriter import rewrite_resume_for_job, RewriteResult

router = APIRouter()


class RewriteRequest(BaseModel):
    resume_id: str
    job_id: str


class RewriteResponse(BaseModel):
    job_title: str
    company: str
    original_resume: dict
    tailored_resume: dict
    diff: list[dict]
    match_score: float


@router.post("/tailor")
async def tailor_resume(req: RewriteRequest):
    """Rewrite a resume to match a specific job description."""
    try:
        result: RewriteResult = rewrite_resume_for_job(
            resume_id=req.resume_id,
            job_id=req.job_id,
        )
        return {
            "job_title": result.job_title,
            "company": result.company,
            "original_resume": result.original_resume,
            "tailored_resume": result.tailored_resume,
            "diff": result.diff,
            "match_score": result.match_score,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Rewrite failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
