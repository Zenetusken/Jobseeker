"""
Centralized configuration via pydantic-settings.
Reads from environment / .env file.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Model
    vllm_model_name: str = "fdtn-ai/Foundation-Sec-8B-Reasoning"
    vllm_quantization: str = "awq"
    vllm_max_model_len: int = 4096
    vllm_gpu_memory_utilization: float = 0.7
    vllm_enforce_eager: bool = True
    vllm_host: str = "vllm-engine"
    vllm_port: int = 8000

    # Embedding
    embedding_model_name: str = "mixedbread-ai/mxbai-embed-large-v1"
    embedding_device: str = "cuda"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection_jobs: str = "job_descriptions"
    qdrant_collection_resumes: str = "resumes"
    qdrant_vector_size: int = 1024

    # Redis / Celery
    redis_host: str = "redis"
    redis_port: int = 6379

    # Scraper
    scraper_schedule_hours: int = 6
    scraper_max_jobs_per_source: int = 50
    scraper_sources: str = "indeed,linkedin,dice"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001

    # Streamlit
    streamlit_host: str = "0.0.0.0"
    streamlit_port: int = 8501

    # Playwright
    playwright_headless: bool = True
    playwright_timeout_ms: int = 30000
    playwright_stealth_enabled: bool = True

    @property
    def vllm_base_url(self) -> str:
        return f"http://{self.vllm_host}:{self.vllm_port}/v1"

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def celery_result_backend(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
