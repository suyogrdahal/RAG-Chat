# Multi-Tenant RAG Chatbot Platform

## Overview
A plug-and-play, multi-tenant Retrieval-Augmented Generation (RAG) chatbot platform
that organizations can embed into their websites using a simple HTML tag.

Organizations upload documents which are transformed into vector embeddings,
allowing the chatbot to answer questions using organization-specific knowledge only.

## Key Features
- Multi-tenant architecture with strict data isolation
- Secure document ingestion and vector storage
- Retrieval-Augmented Generation (RAG) pipeline
- Embeddable chatbot web component
- Admin dashboard for organizations
- Cloud-native deployment

## Tech Stack
**Backend**
- FastAPI (Python)
- LangChain / LlamaIndex
- JWT Authentication

**Vector Database**
- Qdrant / PGVector (TBD)

**Frontend**
- React / Next.js
- TailwindCSS
- Custom Web Component

**AI**
- GPT-4.1 / Gemini 1.5 Flash
- bge-small or equivalent embedding model

**Infrastructure**
- Docker
- Google Cloud Run or AWS ECS

## Repository Structure
/backend → API, RAG pipeline, auth
/frontend → Admin dashboard & widget
/docs → Architecture & documentation

## Status
🚧 Project under active development