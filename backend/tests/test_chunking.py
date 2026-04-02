from app.ingestion.chunking import chunk_text


def test_chunking_produces_reasonable_sizes() -> None:
    paragraph = (
        "This is a paragraph about retrieval augmented generation. "
        "It contains multiple sentences and enough context to form chunks. "
        "Each paragraph should preserve semantic continuity for better citations. "
    )
    text = ("\n\n".join([paragraph * 8 for _ in range(6)])).strip()
    chunks = chunk_text(text)

    assert chunks
    assert all(len(c.content) <= 1200 for c in chunks)
    if len(chunks) > 1:
        assert all(len(c.content) >= 200 for c in chunks)


def test_overlap_present() -> None:
    text = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu " * 300).strip()
    chunks = chunk_text(text)
    assert len(chunks) >= 2

    for i in range(len(chunks) - 1):
        assert chunks[i + 1].start_char < chunks[i].end_char


def test_deterministic_output_same_input() -> None:
    text = (
        "# Heading\n"
        "A deterministic chunker should always return the same output for the same input.\n\n"
        "Paragraph two with additional details and repeated structures for stable splitting.\n\n"
        "Paragraph three to ensure recursive splitting can happen when content grows."
    ) * 20

    first = chunk_text(text)
    second = chunk_text(text)
    assert first == second
