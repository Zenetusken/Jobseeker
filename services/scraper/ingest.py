"""
Job Ingestion — Embed and store job descriptions in Qdrant.
"""
import uuid
from loguru import logger
from qdrant_client.models import PointStruct

from services.embeddings.embedding_service import encode_text
from services.scraper.metadata_extractor import extract_all_metadata
from services.qdrant.init_collections import get_qdrant_client
from config.settings import settings


def ingest_job_text(
    title: str,
    company: str,
    description: str,
    location: str = "",
    url: str = "",
    source: str = "manual",
) -> str:
    """Embed and store a single job description."""
    # Extract metadata
    metadata = extract_all_metadata(description)

    # Build searchable text
    searchable_text = f"{title}\n{company}\n{description}"

    # Generate embedding
    embedding = encode_text(searchable_text)

    # Store in Qdrant
    client = get_qdrant_client()
    point_id = str(uuid.uuid4())

    client.upsert(
        collection_name=settings.qdrant_collection_jobs,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": description,
                    "url": url,
                    "source": source,
                    **metadata,
                },
            )
        ],
    )

    logger.info(f"Ingested job: {title} @ {company} [{point_id}]")
    return point_id


def ingest_job_batch(jobs: list[dict], trigger_match: bool = True) -> list[str]:
    """Embed and store multiple job descriptions."""
    job_ids = []
    for job in jobs:
        jid = ingest_job_text(
            title=job.get("title", ""),
            company=job.get("company", ""),
            description=job.get("description", ""),
            location=job.get("location", ""),
            url=job.get("url", ""),
            source=job.get("source", "batch"),
        )
        job_ids.append(jid)

    if job_ids and trigger_match:
        try:
            from services.tasks.match_task import batch_match_new_jobs
            batch_match_new_jobs.delay(job_ids)
            logger.info(f"Dispatched batch_match_new_jobs for {len(job_ids)} jobs")
        except Exception as e:
            logger.warning(f"Could not dispatch batch_match task: {e}")

    return job_ids
