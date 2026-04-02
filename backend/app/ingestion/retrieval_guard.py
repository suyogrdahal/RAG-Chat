from __future__ import annotations


def evaluate_retrieval_results(chunks: list[dict], threshold: float) -> dict:
    if not chunks:
        return {"proceed": False, "confidence": 0.0}

    scores = [float(c.get("score", 0.0)) for c in chunks]
    best_score = max(scores) if scores else 0.0
    print("Best retrieval score:", best_score)
    if best_score < float(threshold):
        return {"proceed": False, "confidence": best_score}
    return {"proceed": True, "confidence": best_score}
