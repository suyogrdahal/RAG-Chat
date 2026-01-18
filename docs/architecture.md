# High-Level Architecture Diagram

## System Overview (End-to-End)

```mermaid
flowchart LR
  %% ========== Actors ==========
  A1[Org Admin<br/>Browser] -->|HTTPS| FE1[Admin Dashboard<br/>Next.js/React]
  A2[Website Visitor<br/>Browser] -->|Loads script tag| W1[Embeddable Widget<br/>&lt;aichatbot/&gt; Web Component]

  %% ========== Frontend to API ==========
  FE1 -->|JWT (admin login)| API[Backend API<br/>FastAPI]
  W1 -->|Signed Widget Token<br/>or Org Public ID| API

  %% ========== Core Backend Modules ==========
  API --> AUTH[Auth + Tenant Context<br/>(Derive org_id server-side)]
  API --> DOC[Document Service<br/>Upload / Status]
  API --> RAG[RAG Service<br/>Retrieve + Prompt + Generate]

  %% ========== Storage ==========
  DOC --> DB[(PostgreSQL<br/>orgs/users/docs)]
  DOC --> OBJ[(Object Storage<br/>Local/S3/GCS)]

  %% ========== Embeddings + Vector DB ==========
  DOC --> EMB[Local Embeddings<br/>(e.g., bge-small)]
  EMB --> VDB[(Vector DB<br/>Qdrant)]
  RAG -->|Similarity Search<br/>FILTER org_id| VDB

  %% ========== LLM ==========
  RAG -->|Prompt + Retrieved Context| LLM[LLM API<br/>(cheap model)]
  LLM -->|Answer| API

  %% ========== Response Flow ==========
  API -->|Chat Response| W1
  API -->|Admin APIs| FE1

  %% ========== Security Controls ==========
  subgraph Controls[Security & Abuse Prevention]
    C1[Domain Whitelist<br/>(widget theft protection)]
    C2[Rate Limiting<br/>per org + per IP]
    C3[Token Limits<br/>max tokens per request]
    C4[Logging/Redaction<br/>no secrets in logs]
  end

  API --- C2
  API --- C3
  W1 --- C1
  API --- C4
