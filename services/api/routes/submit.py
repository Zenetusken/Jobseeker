"""
Submit Routes — Trigger Playwright-based application submission via Celery.
"""
import json
import datetime
from datetime import timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from services.tasks.submit_task import submit_application_task
from config.settings import settings

router = APIRouter()

HISTORY_KEY = "jobseeker:submissions"
HISTORY_MAX = 200


class SubmitRequest(BaseModel):
    job_id: str
    resume_id: str
    tailored_resume: dict
    job_url: str
    job_title: str = ""
    company: str = ""


class SubmitResponse(BaseModel):
    task_id: str
    status: str


def _get_redis():
    import redis as redis_lib
    return redis_lib.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        decode_responses=True,
    )


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

        # Persist submission metadata to Redis for history
        record = {
            "task_id": task.id,
            "job_id": req.job_id,
            "resume_id": req.resume_id,
            "job_title": req.job_title,
            "company": req.company,
            "job_url": req.job_url,
            "submitted_at": datetime.datetime.now(timezone.utc).isoformat(),
            "status": "queued",
        }
        try:
            r = _get_redis()
            r.lpush(HISTORY_KEY, json.dumps(record))
            r.ltrim(HISTORY_KEY, 0, HISTORY_MAX - 1)
        except Exception as redis_err:
            logger.warning(f"Could not write submission history: {redis_err}")

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
    """Get recent submission history, enriched with live Celery task state."""
    from services.tasks.celery_app import celery_app
    try:
        r = _get_redis()
        raw_entries = r.lrange(HISTORY_KEY, 0, limit - 1)
    except Exception as e:
        logger.warning(f"Could not read submission history: {e}")
        return {"submissions": [], "total": 0}

    submissions = []
    for raw in raw_entries:
        try:
            record = json.loads(raw)
            # Enrich with live Celery state
            task_id = record.get("task_id", "")
            if task_id:
                result = celery_app.AsyncResult(task_id)
                live_status = result.state
                if live_status not in ("PENDING", "STARTED"):
                    record["status"] = live_status.lower()
                if result.ready() and isinstance(result.result, dict):
                    record["result_status"] = result.result.get("status", "")
                    record["error"] = result.result.get("error")
            submissions.append(record)
        except Exception:
            continue

    return {"submissions": submissions, "total": len(submissions)}
