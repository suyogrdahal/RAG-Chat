# High-Level Architecture Diagram

## System Overview (End-to-End)

```mermaid
flowchart LR

  %% Actors
  Admin[Org Admin Browser]
  Visitor[Website Visitor Browser]

  %% Frontend
  Dashboard[Admin Dashboard - Next.js]
  Widget[Embeddable Chat Widget]

  %% Backend
  API[Backend API - FastAPI]
  Auth[Auth and Tenant Context]
  DocSvc[Document Service]
  RAG[RAG Service]

  %% Storage
  DB[(PostgreSQL)]
  Storage[(Object Storage)]
  VDB[(Vector DB - Qdrant)]

  %% AI
  Embed[Local Embedding Model]
  LLM[LLM API - Cheap Model]

  %% Flows
  Admin --> Dashboard
  Dashboard -->|JWT| API

  Visitor --> Widget
  Widget -->|Signed Token| API

  API --> Auth
  API --> DocSvc
  API --> RAG

  DocSvc --> DB
  DocSvc --> Storage

  DocSvc --> Embed
  Embed --> VDB

  RAG -->|Similarity Search (org_id filter)| VDB
  RAG -->|Prompt + Context| LLM
  LLM --> API

  API --> Widget
  API --> Dashboard

