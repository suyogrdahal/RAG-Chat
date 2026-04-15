import numpy as np

import app.services.embeddings as embeddings


class _DummySettings:
    embed_model_name = "BAAI/bge-small-en-v1.5"
    embed_batch_size = 64
    embed_local_files_only = False
    embed_preload_on_startup = True


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
        assert show_progress_bar is False
        assert batch_size > 0
        return np.array([[0.01] * self.dim for _ in texts], dtype=float)


def test_get_embedding_model_returns_same_instance(monkeypatch) -> None:
    embeddings._model = None
    created: list[_DummyModel] = []
    monkeypatch.setattr(embeddings, "get_settings", lambda: _DummySettings())

    def _factory(*args, **kwargs):
        model = _DummyModel(384)
        created.append(model)
        return model

    monkeypatch.setattr(embeddings, "SentenceTransformer", _factory)

    model1 = embeddings.get_embedding_model()
    model2 = embeddings.get_embedding_model()

    assert id(model1) == id(model2)
    assert len(created) == 1
    embeddings._model = None


def test_embed_texts_returns_vectors(monkeypatch) -> None:
    monkeypatch.setattr(embeddings, "get_settings", lambda: _DummySettings())
    embeddings._model = _DummyModel(384)

    out = embeddings.embed_texts(["a", "b", "c"])

    assert len(out) == 3
    assert all(len(vector) == 384 for vector in out)
    embeddings._model = None


def test_model_loads_only_once(monkeypatch) -> None:
    embeddings._model = None
    calls: list[tuple[tuple, dict]] = []
    monkeypatch.setattr(embeddings, "get_settings", lambda: _DummySettings())

    def _factory(*args, **kwargs):
        calls.append((args, kwargs))
        return _DummyModel(384)

    monkeypatch.setattr(embeddings, "SentenceTransformer", _factory)

    embeddings.get_embedding_model()
    embeddings.get_embedding_model()
    embeddings.embed_texts(["singleton"])

    assert len(calls) == 1
    embeddings._model = None
