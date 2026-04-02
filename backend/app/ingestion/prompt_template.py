from __future__ import annotations


def build_rag_prompt(
    context: str,
    user_query: str,
    *,
    org_name: str = "the organization",
    organization_description: str | None = None,
) -> str:
    description = (organization_description or "").strip()
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
