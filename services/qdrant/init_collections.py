"""
Qdrant Collection Schema & Initialization.
Creates collections for job_descriptions and resumes
with proper vector dimensions and payload indexing.
"""
import threading
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
    OptimizersConfigDiff,
)
from loguru import logger
from config.settings import settings

_qdrant_client: QdrantClient | None = None
_qdrant_lock = threading.Lock()


def get_qdrant_client() -> QdrantClient:
    """Return a module-level singleton QdrantClient (thread-safe)."""
    global _qdrant_client
    if _qdrant_client is None:
        with _qdrant_lock:
            if _qdrant_client is None:
                _qdrant_client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                    api_key=settings.qdrant_api_key or None,
                )
                logger.info(
                    f"QdrantClient created: {settings.qdrant_host}:{settings.qdrant_port}"
                )
    return _qdrant_client


def init_collections() -> None:
    """Create collections if they don't exist."""
    client = get_qdrant_client()

    # --- Job Descriptions Collection ---
    if not client.collection_exists(settings.qdrant_collection_jobs):
        logger.info(f"Creating collection: {settings.qdrant_collection_jobs}")
        client.create_collection(
            collection_name=settings.qdrant_collection_jobs,
            vectors_config=VectorParams(
                size=settings.qdrant_vector_size,
                distance=Distance.COSINE,
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=100,
            ),
        )
        # Create payload indexes for metadata filtering
        client.create_payload_index(
            collection_name=settings.qdrant_collection_jobs,
            field_name="required_certs",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=settings.qdrant_collection_jobs,
            field_name="required_skills",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=settings.qdrant_collection_jobs,
            field_name="clearance_level",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=settings.qdrant_collection_jobs,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info(f"Collection '{settings.qdrant_collection_jobs}' created with indexes")
    else:
        logger.info(f"Collection '{settings.qdrant_collection_jobs}' already exists")

    # --- Resumes Collection ---
    if not client.collection_exists(settings.qdrant_collection_resumes):
        logger.info(f"Creating collection: {settings.qdrant_collection_resumes}")
        client.create_collection(
            collection_name=settings.qdrant_collection_resumes,
            vectors_config=VectorParams(
                size=settings.qdrant_vector_size,
                distance=Distance.COSINE,
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=10,
            ),
        )
        client.create_payload_index(
            collection_name=settings.qdrant_collection_resumes,
            field_name="certs",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=settings.qdrant_collection_resumes,
            field_name="skills",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=settings.qdrant_collection_resumes,
            field_name="clearance_level",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info(f"Collection '{settings.qdrant_collection_resumes}' created with indexes")
    else:
        logger.info(f"Collection '{settings.qdrant_collection_resumes}' already exists")


def reset_collections() -> None:
    """Delete and recreate all collections. Use with caution."""
    global _qdrant_client
    client = get_qdrant_client()
    for name in [settings.qdrant_collection_jobs, settings.qdrant_collection_resumes]:
        if client.collection_exists(name):
            client.delete_collection(name)
            logger.info(f"Deleted collection: {name}")
    # Re-use same client — connection is still valid after collection drops
    init_collections()
