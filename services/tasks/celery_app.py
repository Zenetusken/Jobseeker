"""
Celery Application — Async task queue configuration.
Uses Redis as broker and result backend.
"""
from celery import Celery
from celery.schedules import crontab
from config.settings import settings

celery_app = Celery(
    "jobseeker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "services.tasks.submit_task",
        "services.tasks.scrape_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 min max per task
    task_soft_time_limit=540,  # 9 min soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "scrape-jobs-periodic": {
        "task": "services.tasks.scrape_task.scrape_and_ingest_jobs",
        "schedule": crontab(hour=f"*/{settings.scraper_schedule_hours}"),
        "options": {"expires": 3600},
    },
}
