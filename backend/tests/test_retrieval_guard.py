from app.ingestion.retrieval_guard import evaluate_retrieval_results


def test_no_chunks_proceed_false() -> None:
    result = evaluate_retrieval_results([], threshold=0.5)
    assert result["proceed"] is False
    assert result["confidence"] == 0.0


def test_low_confidence_proceed_false() -> None:
    chunks = [{"score": 0.22}, {"score": 0.35}]
    result = evaluate_retrieval_results(chunks, threshold=0.5)
    assert result["proceed"] is False
    assert result["confidence"] == 0.35


def test_high_confidence_proceed_true() -> None:
    chunks = [{"score": 0.41}, {"score": 0.78}, {"score": 0.66}]
    result = evaluate_retrieval_results(chunks, threshold=0.7)
    assert result["proceed"] is True
    assert result["confidence"] == 0.78
