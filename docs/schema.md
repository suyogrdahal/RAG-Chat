# Database Schema (Sprint 1)

## ID Strategy
- Use UUID primary keys for all tables.
- All tenant-owned resources include `org_id` and are queried with `org_id` filter.

## Tables (PostgreSQL)

### organizations
- id (uuid, pk)
- name (text, not null)
- slug (text, unique, optional)
- status (text: active|disabled, default active)
- allowed_domains (text[] or jsonb, default empty)
- rate_limit_per_minute (int, default 60)
- max_tokens_per_request (int, default 800)
- created_at (timestamptz)
- updated_at (timestamptz)

### users
- id (uuid, pk)
- org_id (uuid, fk -> organizations.id, indexed)
- email (text, not null)
- password_hash (text, nullable)
- role (text: owner|admin|viewer, default admin)
- is_active (bool, default true)
- last_login_at (timestamptz, nullable)
- created_at (timestamptz)
- updated_at (timestamptz)
Constraints:
- unique(org_id, email)

### documents
- id (uuid, pk)
- org_id (uuid, fk -> organizations.id, indexed)
- uploaded_by_user_id (uuid, fk -> users.id, nullable)
- filename (text)
- content_type (text)
- storage_path (text)
- status (text: uploaded|processing|ready|failed, default uploaded)
- error_message (text, nullable)
- num_chunks (int, default 0)
- embedding_model (text)
- embedding_dim (int)
- created_at (timestamptz)
- updated_at (timestamptz)

### document_chunks (optional)
- id (uuid, pk)
- org_id (uuid, indexed)
- document_id (uuid, fk -> documents.id, indexed)
- chunk_index (int)
- text (text)
- qdrant_point_id (text/uuid)
- created_at (timestamptz)
Constraints:
- unique(document_id, chunk_index)

## Vector Store (Qdrant) Payload Rules
Each vector point payload must include:
- org_id (uuid)
- document_id (uuid)
- chunk_id (uuid) or (document_id + chunk_index)
Retrieval queries must always filter by org_id to prevent cross-tenant leakage.
