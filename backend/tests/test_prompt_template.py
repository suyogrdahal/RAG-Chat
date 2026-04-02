from app.ingestion.prompt_template import build_rag_prompt


def test_prompt_contains_context() -> None:
    context = "The capital of France is Paris."
    prompt = build_rag_prompt(context=context, user_query="What is the capital of France?")
    assert context in prompt


def test_prompt_contains_user_query() -> None:
    query = "When was the company founded?"
    prompt = build_rag_prompt(context="Context here", user_query=query)
    assert query in prompt


def test_guardrail_sentence_exists() -> None:
    prompt = build_rag_prompt(context="x", user_query="y")
    assert "Use the CONTEXT to answer when it contains relevant information." in prompt
    assert "ERR1010" in prompt


def test_format_is_correct() -> None:
    prompt = build_rag_prompt(context="ctx", user_query="q")
    assert prompt.startswith("SYSTEM:\n")
    assert "\n\nCONTEXT:\n" in prompt
    assert "\n\nUSER:\n" in prompt
    assert prompt.endswith("\n\nASSISTANT:")
