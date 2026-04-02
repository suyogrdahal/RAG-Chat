from app.ingestion.prompt_template import build_rag_prompt
from app.ingestion.token_limit import enforce_token_limit


def test_prompt_under_limit_unchanged() -> None:
    prompt = build_rag_prompt("short context", "short question")
    out = enforce_token_limit(prompt, model_limit=5000, reserved_for_answer=200)
    assert out == prompt


def test_prompt_over_limit_truncated() -> None:
    long_context = "x" * 20000
    prompt = build_rag_prompt(long_context, "What is this?")
    out = enforce_token_limit(prompt, model_limit=1000, reserved_for_answer=200)
    assert len(out) < len(prompt)
    assert "USER:\nWhat is this?" in out


def test_reserved_tokens_respected() -> None:
    long_context = "y" * 16000
    prompt = build_rag_prompt(long_context, "Q?")
    out = enforce_token_limit(prompt, model_limit=1200, reserved_for_answer=300)
    assert (len(out) / 4.0) + 300 <= 1200


def test_question_never_removed() -> None:
    long_context = "z" * 30000
    question = "Critical question stays."
    prompt = build_rag_prompt(long_context, question)
    out = enforce_token_limit(prompt, model_limit=800, reserved_for_answer=200)
    assert "\n\nUSER:\n" in out
    assert question in out
    assert out.endswith("\n\nASSISTANT:")
