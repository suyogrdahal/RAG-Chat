from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


class EmbeddingDimensionError(ValueError):
    pass


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embed_model_name, device="cpu")


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    model = _get_model()
    vectors = model.encode(
        texts,
        batch_size=settings.embed_batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    result = vectors.tolist()

    expected_dim = 384
    for idx, vector in enumerate(result):
        if len(vector) != expected_dim:
            raise EmbeddingDimensionError(
                f"Embedding dimension mismatch at index {idx}: expected {expected_dim}, got {len(vector)}"
            )
    return result
