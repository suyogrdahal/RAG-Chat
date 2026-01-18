# Tenant Isolation Strategy (Day 5)

## Goals
- Prevent any cross-organization (cross-tenant) data access.
- Ensure all retrieval (vector DB) and storage (DB/files) are tenant-scoped.
- Ensure org identity is derived server-side (never trusted from client input).

---

## Core Design Choices

### 1) Vector DB Filtering Approach (Qdrant)
**Approach:** Single collection for all tenants + strict payload filtering.

**Payload standard (required for every vector point):**
- org_id: UUID
- document_id: UUID
- chunk_id: UUID (or document_id + chunk_index)
- optional: source filename, chunk_index, created_at

**Retrieval rule:**
Every search MUST include a filter `org_id == <current_org_id>`.
No exceptions.

**Ingestion rule:**
Every upsert MUST attach `org_id` to payload.

---

### 2) org_id Propagation (How tenant context flows)

#### Admin Dashboard APIs (authenticated users)
- Client authenticates via JWT.
- JWT contains `org_id` (and `user_id`, `role`).
- Backend derives `current_org_id` from JWT claims.

**Rule:** Never accept `org_id` from request body/query for tenant scoping.
If request contains org_id, it must match JWT org_id OR be ignored.

#### Widget Chat APIs (public embed)
Two valid patterns (pick one; both work):

**Option A (Recommended for v1): Signed Widget Token**
- Widget HTML includes a public org identifier (org_slug or org_id).
- Backend issues a short-lived signed token for that org (and optional domain).
- Widget uses this token for chat calls.
- Backend derives `current_org_id` from the signed token.

**Option B: API Key per Organization**
- Widget uses an org API key (danger: key leakage if not protected).
- Backend maps API key -> org_id server-side.

**Rule:** Widget requests MUST NOT rely solely on a client-provided org_id without server verification.

---

## Isolation Rules (Non-Negotiable)

### A) API Enforcement
1. All protected endpoints require auth (JWT or signed widget token).
2. Every endpoint sets `current_org_id` from auth context.
3. All DB queries must include `WHERE org_id = current_org_id`.
4. All vector DB searches must include filter `org_id = current_org_id`.
5. All file storage paths must be partitioned by org_id (e.g., /storage/<org_id>/...).

### B) Data Model Enforcement
- Organization-owned tables include org_id:
  - documents.org_id
  - document_chunks.org_id (if used)
  - users.org_id
- Indices exist on org_id columns for performance + consistent query patterns.

### C) Role-Based Access (Admin UI)
- Roles: owner/admin/viewer
- Minimum enforcement:
  - viewer: read-only (documents list, usage)
  - admin: upload/manage documents
  - owner: manage org settings (domains, limits, API keys)

---

## Leakage Prevention Notes (Threat Model)

### 1) Cross-tenant leakage via vector retrieval
**Risk:** A search without org_id filter could return another org’s chunks.
**Mitigation:**
- Retrieval wrapper function ALWAYS applies org filter (single place).
- Unit tests: retrieval must fail if org filter missing.
- Code review rule: direct qdrant client usage is forbidden outside vector service layer.

### 2) Cross-tenant leakage via DB queries
**Risk:** Developer forgets `WHERE org_id = ...`.
**Mitigation:**
- Create repository/service functions that require `org_id` parameter.
- Avoid raw queries in route handlers.
- Tests for “cannot access other org’s document by ID”.

### 3) ID guessing / enumeration
**Risk:** If IDs are incremental, attackers guess IDs.
**Mitigation:**
- UUIDs for all IDs (org_id, user_id, document_id, chunk_id).

### 4) Widget theft (someone embeds your widget on another domain)
**Risk:** Unauthorized domain uses your org widget.
**Mitigation:**
- Domain whitelist per org.
- Validate request `Origin` / `Referer` against allowed domains (best-effort).
- Signed widget tokens should include allowed domain claim if possible.
- Rate limits per org + per IP.

### 5) Prompt injection / data exfiltration attempts
**Risk:** User asks model to ignore rules or reveal other org data.
**Mitigation:**
- Retrieval layer is the true boundary: model only sees retrieved chunks for current org.
- Limit max chunks + token limits.
- Optional: refuse if question asks for secrets/credentials.

### 6) Logging leaks
**Risk:** Logs contain retrieved text or secrets.
**Mitigation:**
- Never log full document chunks in production.
- Redact tokens/secrets in logs.
- Log IDs and counts, not raw content.

---

## Implementation Guardrails (Engineering Practices)

### Mandatory service boundaries
- `AuthContext` module: returns current_org_id, user_id, role
- `DocumentService`: all DB access requires org_id
- `VectorService`: all Qdrant operations require org_id

### Testing requirements
- Create two orgs (OrgA, OrgB) in tests.
- Upload documents for both.
- Assert:
  - OrgA cannot list/get OrgB documents.
  - OrgA retrieval never returns OrgB chunk payload.
  - Widget requests from non-whitelisted domains are rejected (or denied token).

---

## Definition of Done
- Isolation rules above are implemented as reusable services.
- No route handler directly queries Qdrant or DB without passing current_org_id.
- Tests exist proving cross-tenant access is impossible via API.
