from __future__ import annotations

import logging
from threading import Lock

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


logger = logging.getLogger("app.embeddings")
EXPECTED_EMBEDDING_DIMENSION = 384
_model: SentenceTransformer | None = None
_model_lock = Lock()


class EmbeddingDimensionError(ValueError):
    pass


def get_embedding_model() -> SentenceTransformer:
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                settings = get_settings()
                try:
                    _model = SentenceTransformer(
                        settings.embed_model_name,
                        device="cpu",
                        local_files_only=settings.embed_local_files_only,
                    )
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to load embedding model '{settings.embed_model_name}'. "
                        "Ensure the model is available locally or network access is configured."
                    ) from exc
                logger.info("Embedding model loaded: %s", settings.embed_model_name)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    model = get_embedding_model()
    vectors = model.encode(
        texts,
        batch_size=settings.embed_batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    result = vectors.tolist()

    for idx, vector in enumerate(result):
        if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
            raise EmbeddingDimensionError(
                f"Embedding dimension mismatch at index {idx}: "
                f"expected {EXPECTED_EMBEDDING_DIMENSION}, got {len(vector)}"
            )
    return result


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def preload_embedding_model() -> None:
    settings = get_settings()
    if not settings.embed_preload_on_startup:
        return

    try:
        get_embedding_model()
    except Exception as exc:
        logger.warning("Embedding model preload skipped: %s", exc)
