"""
Submit Task — Celery task for Playwright-based application submission.
"""
import json
from celery.utils.log import get_task_logger
from services.tasks.celery_app import celery_app
from services.automation.submitter import submit_application

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="services.tasks.submit_task.submit_application_task")
def submit_application_task(
    self,
    job_id: str,
    resume_id: str,
    tailored_resume: dict,
    job_url: str,
):
    """
    Async task: submit a tailored resume to a job application portal.
    Uses Playwright for headless browser automation.
    """
    logger.info(f"Starting submission for job={job_id}, resume={resume_id}")

    try:
        result = submit_application(
            job_url=job_url,
            tailored_resume=tailored_resume,
            job_id=job_id,
        )

        logger.info(f"Submission complete: {result.get('status')}")
        return {
            "status": result.get("status", "unknown"),
            "job_id": job_id,
            "resume_id": resume_id,
            "timestamp": result.get("timestamp"),
            "screenshot": result.get("screenshot"),
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"Submission failed: {e}")
        return {
            "status": "failed",
            "job_id": job_id,
            "resume_id": resume_id,
            "error": str(e),
        }
