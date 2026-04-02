from app.ingestion.context_assembly import assemble_context


def test_stops_at_token_limit() -> None:
    chunks = [
        {"content": "a" * 400},  # ~100 tokens
        {"content": "b" * 400},  # +~100 tokens (with separator)
        {"content": "c" * 400},  # would exceed 250
    ]
    out = assemble_context(chunks, max_tokens=250)
    assert "a" * 400 in out
    assert "b" * 400 in out
    assert "c" * 400 not in out


def test_deterministic_output() -> None:
    chunks = [
        {"content": "chunk one"},
        {"content": "chunk two"},
        {"content": "chunk three"},
    ]
    out1 = assemble_context(chunks, max_tokens=100)
    out2 = assemble_context(chunks, max_tokens=100)
    assert out1 == out2


def test_returns_empty_string_if_no_chunks() -> None:
    assert assemble_context([], max_tokens=100) == ""


def test_does_not_exceed_token_estimate() -> None:
    chunks = [
        {"content": "x" * 500},  # ~125
        {"content": "y" * 500},  # would exceed 200 with separator
    ]
    out = assemble_context(chunks, max_tokens=200)
    assert len(out) / 4.0 <= 200
