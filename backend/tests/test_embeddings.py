import numpy as np

from app.ingestion import embeddings


class _DummyModel:
    def __init__(self, dim: int) -> None:
        self.dim = dim

    def encode(
        self,
        texts,
        batch_size,
        normalize_embeddings,
        convert_to_numpy,
        show_progress_bar,
    ):
        assert convert_to_numpy is True
        assert normalize_embeddings is True
        return np.array([[0.01] * self.dim for _ in texts], dtype=float)


def test_embeddings_return_correct_count(monkeypatch) -> None:
    monkeypatch.setattr(embeddings, "_get_model", lambda: _DummyModel(384))
    out = embeddings.embed_texts(["a", "b", "c"])
    assert len(out) == 3


def test_embeddings_dimension_matches_expected(monkeypatch) -> None:
    monkeypatch.setattr(embeddings, "_get_model", lambda: _DummyModel(384))
    out = embeddings.embed_texts(["default model dimension check"])
    assert len(out) == 1
    assert len(out[0]) == 384
