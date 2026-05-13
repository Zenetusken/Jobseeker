"""
Embedding Service — mxbai-embed-large-v1 on CUDA.
Fits within 1.5GB VRAM partition. Exposes encode() for
single texts and batches.
"""
import torch
from sentence_transformers import SentenceTransformer
from loguru import logger
from config.settings import settings

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model_name}")
        _embedding_model = SentenceTransformer(
            settings.embedding_model_name,
            device=settings.embedding_device,
            trust_remote_code=True,
        )
        # Force model to stay on GPU
        if settings.embedding_device == "cuda":
            _embedding_model = _embedding_model.to(torch.device("cuda"))
        logger.info(
            f"Embedding model loaded. Dim={_embedding_model.get_sentence_embedding_dimension()}"
        )
    return _embedding_model


def encode_text(text: str) -> list[float]:
    """Encode a single text to a vector."""
    model = get_embedding_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def encode_batch(texts: list[str]) -> list[list[float]]:
    """Encode a batch of texts to vectors."""
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()
