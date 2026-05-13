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
