"""
Tier 2 — Core service tests for qdrant/init_collections.py.
Tests collection initialization and reset with mocked QdrantClient.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestInitCollections:
    def test_init_collections_creates_collections(self):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = False

        with patch("services.qdrant.init_collections.get_qdrant_client", return_value=mock_client):
            from services.qdrant.init_collections import init_collections
            init_collections()
            assert mock_client.create_collection.call_count == 2

    def test_init_collections_skips_existing(self):
        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True

        with patch("services.qdrant.init_collections.get_qdrant_client", return_value=mock_client):
            from services.qdrant.init_collections import init_collections
            init_collections()
            mock_client.create_collection.assert_not_called()

    def test_reset_collections(self):
        mock_client = MagicMock()
        # First call: collections exist (delete them)
        # After delete, they don't exist (recreate them)
        mock_client.collection_exists.side_effect = [True, True, False, False]

        with patch("services.qdrant.init_collections.get_qdrant_client", return_value=mock_client):
            from services.qdrant.init_collections import reset_collections
            reset_collections()
            assert mock_client.delete_collection.call_count == 2
            assert mock_client.create_collection.call_count == 2

    def test_get_qdrant_client_singleton(self):
        mock_client = MagicMock()

        with patch("services.qdrant.init_collections.get_qdrant_client", return_value=mock_client):
            from services.qdrant.init_collections import get_qdrant_client
            c1 = get_qdrant_client()
            c2 = get_qdrant_client()
            assert c1 is c2
