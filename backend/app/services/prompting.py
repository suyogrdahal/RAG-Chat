from __future__ import annotations


def build_fallback_message(org_name: str, org_description: str | None) -> str:
    message = (
        f"Hi! I'm the AI assistant for {org_name}. "
        f"I answer questions based on {org_name}'s uploaded documents."
    )
    if org_description and org_description.strip():
        message += f" {org_description.strip()}"
    message += " Try asking about policies, hours, services, or FAQs."
    return message


def build_greeting_message(org_name: str) -> str:
    return f"hi im chat assisant of {org_name} how can i help you"


def build_retrieved_context(chunks: list[dict], max_context_chars: int) -> str:
    parts: list[str] = []
    total = 0
    for chunk in chunks:
        content = str(chunk.get("content", "")).strip()
        if not content:
            continue
        candidate_len = len(content) + (2 if parts else 0)
        if total + candidate_len > max_context_chars:
            remaining = max_context_chars - total
            if remaining > 0:
                parts.append(content[:remaining].rstrip())
            break
        parts.append(content)
        total += candidate_len
    return "\n\n".join(parts).strip()


def build_rag_prompt(
    *,
    org_name: str,
    org_description: str | None,
    context: str,
    user_query: str,
) -> str:
    description = (org_description or "").strip()
    return (
        "SYSTEM:\n"
        f"You are the AI assistant for {org_name}.\n"
        f"Organization description: {description}\n\n"
        "Rules:\n"
        "- Use the CONTEXT to answer when it contains relevant information.\n"
        "- If the CONTEXT does not contain the answer, output exactly: ERR1010\n"
        "- Do not output anything else if you output ERR1010.\n\n"
        "CONTEXT:\n"
        f"{context}\n\n"
        "USER:\n"
        f"{user_query}\n\n"
        "ASSISTANT:"
    )
