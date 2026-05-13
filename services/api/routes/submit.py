"""
Submit Routes — Trigger Playwright-based application submission via Celery.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from services.tasks.submit_task import submit_application_task

router = APIRouter()


class SubmitRequest(BaseModel):
    job_id: str
    resume_id: str
    tailored_resume: dict
    job_url: str


class SubmitResponse(BaseModel):
    task_id: str
    status: str


@router.post("/apply")
async def submit_application(req: SubmitRequest):
    """Dispatch an application submission to the Celery worker."""
    try:
        task = submit_application_task.delay(
            job_id=req.job_id,
            resume_id=req.resume_id,
            tailored_resume=req.tailored_resume,
            job_url=req.job_url,
        )
        return {
            "task_id": task.id,
            "status": "queued",
            "message": "Application submission dispatched",
        }
    except Exception as e:
        logger.error(f"Submit dispatch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_submission_status(task_id: str):
    """Check the status of a submission task."""
    from services.tasks.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
    }


@router.get("/history")
async def get_submission_history(limit: int = 50):
    """Get recent submission history."""
    # In production, this would query a database.
    # For MVP, we scan Celery results in Redis.
    return {
        "submissions": [],
        "note": "Submission history will be populated as applications are processed",
    }
