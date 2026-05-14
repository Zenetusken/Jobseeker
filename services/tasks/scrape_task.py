"""
Scrape Task — Periodic Celery task for job scraping.
"""
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger
from services.tasks.celery_app import celery_app
from services.scraper.scraper import scrape_sync
from services.scraper.ingest import ingest_job_batch

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="services.tasks.scrape_task.scrape_and_ingest_jobs")
def scrape_and_ingest_jobs(self):
    """
    Periodic task: scrape job boards and ingest new listings.
    Runs every N hours based on SCRAPER_SCHEDULE_HOURS.
    """
    logger.info("Starting scheduled job scrape...")
    try:
        jobs = scrape_sync()
        if jobs:
            job_ids = ingest_job_batch(jobs)
            logger.info(f"Scraped and ingested {len(job_ids)} jobs")
            return {"status": "success", "count": len(job_ids)}
        else:
            logger.warning("No jobs scraped")
            return {"status": "empty", "count": 0}
    except MaxRetriesExceededError:
        logger.error("Scrape task exhausted all retries — giving up")
        return {"status": "failed", "error": "max_retries_exceeded"}
    except Exception as e:
        logger.error(f"Scrape task failed: {e}")
        raise self.retry(exc=e, countdown=300, max_retries=3)
