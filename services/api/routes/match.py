"""
Match Routes — Vector search + metadata filtering for job-resume matching.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger

from services.matching.matcher import match_jobs_to_resume, MatchResult

router = APIRouter()


class MatchRequest(BaseModel):
    resume_id: str
    top_k: int = Field(10, ge=1, le=500)
    min_score: float = Field(0.3, ge=0.0, le=1.0)


class MatchResponse(BaseModel):
    matches: list[dict]
    total_jobs_searched: int
    resume_id: str


@router.post("/jobs")
async def match_jobs(req: MatchRequest):
    """Find top matching jobs for a given resume."""
    try:
        results = match_jobs_to_resume(
            resume_id=req.resume_id,
            top_k=req.top_k,
            min_score=req.min_score,
        )
        return {
            "matches": [r.to_dict() for r in results],
            "total_jobs_searched": len(results),
            "resume_id": req.resume_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Match failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/job/{job_id}")
async def match_single_job(
    job_id: str,
    resume_id: str = Query(...),
):
    """Get match score for a single job against a resume."""
    try:
        results = match_jobs_to_resume(
            resume_id=resume_id,
            top_k=100,
            min_score=0.0,
        )
        for r in results:
            if str(r.job_id) == str(job_id):
                return r.to_dict()
        raise HTTPException(status_code=404, detail="Job not found in matches")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
