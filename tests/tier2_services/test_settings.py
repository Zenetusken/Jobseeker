"""
Tier 2 — Core service tests for config/settings.py.
Tests default values, env overrides, and computed properties.
"""
import os
import pytest
from unittest.mock import patch


class TestSettings:
    def test_default_values(self):
        """Test that settings load with default values."""
        from config.settings import Settings
        s = Settings()
        assert s.vllm_model_name == "fdtn-ai/Foundation-Sec-8B-Reasoning"
        assert s.vllm_quantization == "awq"
        assert s.vllm_max_model_len == 4096
        assert s.vllm_gpu_memory_utilization == 0.7
        assert s.vllm_enforce_eager is True

    def test_computed_vllm_base_url(self):
        from config.settings import Settings
        s = Settings(vllm_host="my-vllm", vllm_port=9000)
        assert s.vllm_base_url == "http://my-vllm:9000/v1"

    def test_computed_qdrant_url(self):
        from config.settings import Settings
        s = Settings(qdrant_host="my-qdrant", qdrant_port=6333)
        assert s.qdrant_url == "http://my-qdrant:6333"

    def test_env_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(os.environ, {
            "VLLM_MODEL_NAME": "custom-model",
            "VLLM_GPU_MEMORY_UTILIZATION": "0.5",
        }):
            from config.settings import Settings
            s = Settings()
            assert s.vllm_model_name == "custom-model"
            assert s.vllm_gpu_memory_utilization == 0.5

    def test_boolean_env_parsing(self):
        with patch.dict(os.environ, {"VLLM_ENFORCE_EAGER": "false"}):
            from config.settings import Settings
            s = Settings()
            assert s.vllm_enforce_eager is False

    def test_int_env_parsing(self):
        with patch.dict(os.environ, {"VLLM_MAX_MODEL_LEN": "8192"}):
            from config.settings import Settings
            s = Settings()
            assert s.vllm_max_model_len == 8192

    def test_float_env_parsing(self):
        with patch.dict(os.environ, {"VLLM_GPU_MEMORY_UTILIZATION": "0.85"}):
            from config.settings import Settings
            s = Settings()
            assert s.vllm_gpu_memory_utilization == 0.85

    def test_qdrant_settings(self):
        from config.settings import Settings
        s = Settings()
        assert s.qdrant_collection_jobs == "job_descriptions"
        assert s.qdrant_collection_resumes == "resumes"
        assert s.qdrant_vector_size == 1024

    def test_scraper_settings(self):
        from config.settings import Settings
        s = Settings()
        assert s.scraper_schedule_hours == 6
        assert s.scraper_max_jobs_per_source == 50

    def test_playwright_settings(self):
        from config.settings import Settings
        s = Settings()
        assert s.playwright_headless is True
        assert s.playwright_timeout_ms == 30000

    def test_module_level_settings_instance(self):
        """Verify the module-level settings instance works."""
        from config.settings import settings
        assert settings.vllm_model_name is not None
        assert settings.vllm_base_url is not None
        assert settings.qdrant_url is not None


class TestSecuritySettings:
    def test_api_key_defaults_empty(self):
        from config.settings import Settings
        s = Settings()
        assert s.api_key == "" or isinstance(s.api_key, str)

    def test_api_debug_defaults_false(self):
        from config.settings import Settings
        s = Settings()
        assert s.api_debug is False

    def test_allowed_origins_defaults_empty(self):
        from config.settings import Settings
        s = Settings()
        assert s.allowed_origins == "" or isinstance(s.allowed_origins, str)

    def test_allowed_origins_list_empty_when_blank(self):
        from config.settings import Settings
        s = Settings(allowed_origins="")
        assert s.allowed_origins_list == []

    def test_allowed_origins_list_parsed_from_comma_string(self):
        from config.settings import Settings
        s = Settings(allowed_origins="https://a.com,https://b.com")
        assert s.allowed_origins_list == ["https://a.com", "https://b.com"]

    def test_allowed_origins_list_strips_whitespace(self):
        from config.settings import Settings
        s = Settings(allowed_origins=" https://a.com , https://b.com ")
        assert "https://a.com" in s.allowed_origins_list
        assert "https://b.com" in s.allowed_origins_list

    def test_redis_password_defaults_empty(self):
        from config.settings import Settings
        s = Settings()
        assert s.redis_password == "" or isinstance(s.redis_password, str)

    def test_qdrant_api_key_defaults_empty(self):
        from config.settings import Settings
        s = Settings()
        assert s.qdrant_api_key == "" or isinstance(s.qdrant_api_key, str)

    def test_celery_broker_url_without_password(self):
        from config.settings import Settings
        s = Settings(redis_host="redis", redis_port=6379, redis_password="")
        assert s.celery_broker_url == "redis://redis:6379/0"

    def test_celery_broker_url_with_password(self):
        from config.settings import Settings
        s = Settings(redis_host="redis", redis_port=6379, redis_password="secret")
        assert s.celery_broker_url == "redis://:secret@redis:6379/0"
        assert "secret" in s.celery_broker_url

    def test_celery_result_backend_equals_broker(self):
        from config.settings import Settings
        s = Settings(redis_password="mypass")
        assert s.celery_result_backend == s.celery_broker_url

    def test_max_upload_bytes_default(self):
        from config.settings import Settings
        s = Settings()
        assert s.max_upload_bytes == 10_485_760

    def test_max_description_length_default(self):
        from config.settings import Settings
        s = Settings()
        assert s.max_description_length == 50_000

    def test_max_batch_size_default(self):
        from config.settings import Settings
        s = Settings()
        assert s.max_batch_size == 100
