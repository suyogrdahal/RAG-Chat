from __future__ import annotations


def _estimate_tokens(text: str) -> float:
    return len(text) / 4.0


def enforce_token_limit(prompt: str, model_limit: int, reserved_for_answer: int) -> str:
    if _estimate_tokens(prompt) + reserved_for_answer <= model_limit:
        return prompt

    context_marker = "\n\nCONTEXT:\n"
    user_marker = "\n\nUSER:\n"
    assistant_marker = "\n\nASSISTANT:"
    question_marker = "\n\nQUESTION\n"

    context_start = prompt.find(context_marker)
    user_start = prompt.find(user_marker)
    if context_start == -1:
        context_marker = "\n\nCONTEXT\n"
        context_start = prompt.find(context_marker)
    if user_start == -1:
        user_marker = "\n\nUSER\n"
        user_start = prompt.find(user_marker)
    if context_start == -1 or user_start == -1 or user_start <= context_start:
        user_start = prompt.find(question_marker)
        if context_start == -1 or user_start == -1 or user_start <= context_start:
            return prompt

    prefix_end = context_start + len(context_marker)
    prefix = prompt[:prefix_end]
    context = prompt[prefix_end:user_start]
    assistant_start = prompt.find(assistant_marker)
    suffix = prompt[user_start:] if assistant_start == -1 else prompt[user_start:assistant_start] + prompt[assistant_start:]

    lo, hi = 0, len(context)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate_context = context[:mid]
        candidate = f"{prefix}{candidate_context}{suffix}"
        if _estimate_tokens(candidate) + reserved_for_answer <= model_limit:
            best = candidate_context
            lo = mid + 1
        else:
            hi = mid - 1

    return f"{prefix}{best}{suffix}"
