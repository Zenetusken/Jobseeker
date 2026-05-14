"""
Match Task — Celery task that runs matching for all stored resumes
after new jobs are ingested. Triggered by the ingest pipeline.
"""
from celery.utils.log import get_task_logger
from services.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="services.tasks.match_task.batch_match_new_jobs")
def batch_match_new_jobs(self, job_ids: list[str]):
    """
    For each newly ingested job, run matching against all stored resumes
    and log the results. In a production system this would persist
    the match results to a database for dashboard display.
    """
    from services.qdrant.init_collections import get_qdrant_client
    from services.matching.matcher import match_jobs_to_resume
    from config.settings import settings

    logger.info(f"batch_match_new_jobs triggered for {len(job_ids)} jobs")

    client = get_qdrant_client()
    resume_records, _ = client.scroll(
        collection_name=settings.qdrant_collection_resumes,
        limit=100,
        with_payload=False,
        with_vectors=False,
    )
    resume_ids = [str(r.id) for r in resume_records]

    if not resume_ids:
        logger.info("No resumes stored — skipping batch match")
        return {"status": "skipped", "reason": "no_resumes"}

    total_matches = 0
    errors = 0
    for resume_id in resume_ids:
        try:
            matches = match_jobs_to_resume(
                resume_id=resume_id,
                top_k=len(job_ids) * 3,
                min_score=0.3,
            )
            relevant = [m for m in matches if m.job_id in job_ids]
            total_matches += len(relevant)
            logger.info(
                f"Resume {resume_id[:8]}: {len(relevant)} new relevant matches"
            )
        except Exception as e:
            logger.error(f"Match failed for resume {resume_id}: {e}")
            errors += 1

    logger.info(
        f"Batch match complete — {total_matches} matches across "
        f"{len(resume_ids)} resumes, {errors} errors"
    )
    return {
        "status": "success",
        "job_ids": job_ids,
        "resumes_checked": len(resume_ids),
        "total_matches": total_matches,
        "errors": errors,
    }
