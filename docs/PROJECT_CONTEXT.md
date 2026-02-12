This file is for the LLM model used as an coding assistant for project development.

# PROJECT_CONTEXT.md

## Project Name
**Multi-Tenant RAG Chatbot Platform with Embeddable Web Component**

---

## 1. Project Overview

This project is a **multi-tenant Retrieval-Augmented Generation (RAG) chatbot platform** that allows organizations to:

- Upload their own documents
- Have those documents embedded and stored securely
- Embed a chatbot into their website via a simple widget
- Answer user questions using only their organization’s data

The system is designed as a **production-style prototype** emphasizing:
- security,
- tenant isolation,
- clean architecture,
- and real-world SaaS patterns.

---

## 2. Core Goals

### Functional Goals
- Allow organizations to onboard and manage their own data
- Provide an admin dashboard for document ingestion and management
- Provide a public-facing chatbot widget for end users
- Ensure **strict tenant isolation** across all data paths
- Use Retrieval-Augmented Generation (RAG) for accurate answers

### Non-Functional Goals
- Secure by design (no cross-tenant leakage)
- Cost-controlled AI usage
- Modular, extensible architecture
- Suitable for cloud deployment
- Maintainable by a single developer

---

## 3. High-Level Architecture

### System Components
- **Frontend**
  - Admin Dashboard (React / Next.js)
  - Embeddable Chat Widget (custom web component)
- **Backend**
  - FastAPI application
  - Auth & tenant context layer
  - Document ingestion pipeline
  - RAG orchestration layer
- **Storage**
  - PostgreSQL (relational data)
  - Object storage (documents)
  - Qdrant (vector embeddings)
- **AI**
  - Local open-source embedding models
  - Cheap hosted LLM APIs for answer generation

All components communicate over HTTPS and are containerizable via Docker.

---

## 4. Multi-Tenancy Model

### Tenant Definition
- A **tenant = organization**
- Each tenant owns:
  - users
  - documents
  - embeddings
  - widget configuration
- Tenants must never see or influence each other’s data

### Tenant Isolation Strategy
- **Payload-based isolation** in vector database
- **org_id present everywhere**
- **org_id derived server-side only**
- UUIDs used for all identifiers

---

## 5. Authentication & Identity Model

### Admin Authentication
- JWT-based authentication
- JWT contains:
  - `user_id`
  - `org_id`
  - `role`
- Admin users access dashboard APIs

### Widget Authentication
- Widget does **not** trust client-provided org_id
- Tenant context established via:
  - signed widget token, or
  - server-verified API key
- Optional domain whitelist enforcement

---

## 6. Database Design

### Primary Database
- **PostgreSQL**

### Core Tables
- `organizations`
- `users`
- `documents`
- optional: `document_chunks`

### ID Strategy
- UUIDs for all primary keys
- Prevents ID enumeration
- Safe for distributed systems

All tenant-owned tables include `org_id`.

---

## 7. Vector Database Design

### Vector DB
- **Qdrant**

### Strategy
- Single collection
- Metadata (payload) includes:
  - `org_id`
  - `document_id`
  - `chunk_id`
- Every retrieval query **must include org_id filter**

This is the primary enforcement layer against cross-tenant RAG leakage.

---

## 8. Embedding Strategy

### Decision
- **Local, open-source embedding models**
- No per-request API cost

### Rationale
- Embeddings can be generated during ingestion
- Reduces operational cost
- Avoids vendor lock-in
- Acceptable CPU cost for a prototype

Embedding model choice is abstracted behind an `EmbeddingProvider` interface.

---

## 9. LLM Strategy (Answer Generation)

### Decision
- Use **cheap hosted LLM APIs** (e.g., lightweight OpenAI or equivalent)

### Rationale
- Higher quality responses
- Faster development
- No GPU/self-hosting overhead
- Token usage controlled via:
  - max tokens per request
  - rate limiting per org

LLM access is abstracted behind an `LLMProvider`.

---

## 10. RAG Flow (End-to-End)

1. Organization uploads document
2. Document is chunked
3. Chunks are embedded locally
4. Embeddings stored in Qdrant with org_id payload
5. User asks question via widget
6. Backend derives org_id from auth context
7. Vector search filtered by org_id
8. Retrieved chunks injected into prompt
9. Hosted LLM generates answer
10. Answer returned to user

The LLM never sees data outside retrieved context.

---

## 11. Security Constraints & Assumptions

### Non-Negotiable Rules
- org_id is never trusted from client input
- Every DB query is scoped by org_id
- Every vector search includes org_id filter
- UUIDs everywhere
- No secrets in logs
- No document text logged in production

### Threats Considered
- Cross-tenant data leakage
- Widget theft
- ID enumeration
- Prompt injection
- Token leakage
- Overuse / abuse of LLM APIs

---

## 12. Development Constraints

- **Single developer**
- **3-month timeline**
- Feature scope intentionally limited
- Prioritize correctness over scale
- Production-grade patterns without overengineering

---

## 13. Feature Scope

### Included (Planned)
- Org onboarding
- Admin dashboard
- Document upload & ingestion
- RAG-based chatbot
- Embeddable widget
- JWT authentication
- Tenant isolation
- Rate limiting
- Basic usage controls

### Explicitly Excluded (Out of Scope)
- Billing system
- Advanced analytics
- Fine-grained RBAC
- Multi-language support
- Real-time document sync
- Federated search across orgs

---

## 14. Deployment Assumptions

- Dockerized services
- Local development via venv
- Docker used for:
  - consistency
  - verification
  - production parity
- Cloud deployment target:
  - Google Cloud Run or AWS ECS

---

## 15. Sprint Status

### Sprint 1 — COMPLETE
- Repo structure
- Backend skeleton
- Config system
- Dockerization
- Architecture decisions
- Tenant isolation rules
- Schema design
- Architecture diagram

### Sprint 2 — IN PROGRESS
- Authentication
- JWT
- Org scoping
- API protection
- Cross-tenant access prevention

---

## 16. Guiding Principle

> **Tenant isolation is enforced by architecture, not developer discipline.**

Every design choice favors correctness, security, and clarity over convenience.

---

## End of Context
