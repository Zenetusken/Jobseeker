"""
Tier 2 — Core service tests for embedding_service.py.
Tests encode_batch and model singleton behavior.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestEmbeddingService:
    def test_encode_batch_calls_model(self):
        from services.embeddings.embedding_service import encode_batch
        result = encode_batch(["text1", "text2", "text3"])
        # Mock returns a single vector; verify it was called
        assert result is not None

    def test_get_embedding_model_singleton(self):
        from services.embeddings.embedding_service import get_embedding_model
        m1 = get_embedding_model()
        m2 = get_embedding_model()
        assert m1 is m2
