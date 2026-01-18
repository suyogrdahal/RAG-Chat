# Architecture Decisions (Sprint 1)

## ADR-001: Vector Database
**Decision:** Use Qdrant as the vector database.
**Status:** Accepted
**Why:** Qdrant provides strong metadata filtering and explicit guidance for multitenancy. We will avoid creating many collections per tenant to reduce overhead, following Qdrant’s recommended multitenancy approach.

## ADR-002: Multi-Tenant Isolation Strategy (Vectors)
**Decision:** Use payload/metadata-based multitenancy (org_id filter), not separate collections/namespaces per tenant.
**Status:** Accepted
**Rules:**
- Every vector point must include `org_id` in payload.
- Every retrieval query must apply a filter on `org_id`.
- Tenant context is derived server-side from JWT/API key (never trust client org_id).

## ADR-003: Embedding Model (Local)
**Decision:** Run embeddings locally using an open-source embedding model (default: `BAAI/bge-small-en-v1.5`).
**Status:** Accepted
**Why:** No per-request API cost for embeddings; reduces operational cost. Tradeoff is local CPU/GPU usage and increased infra complexity vs hosted embeddings.
**Notes:** Keep an `EmbeddingProvider` abstraction so we can swap models or move to hosted embeddings if needed.

## ADR-004: LLM for Answer Generation (Cheap API)
**Decision:** Use a low-cost hosted LLM API for response generation (default: OpenAI `gpt-4o-mini` or `gpt-4.1-mini`).
**Status:** Accepted
**Why:** Faster development and higher-quality responses without self-hosting complexity; cost is pay-per-token and controllable via limits.
**Notes:** Enforce token limits + rate limiting per org to control spend.
