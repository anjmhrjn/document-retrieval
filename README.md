# Document Retrieval

An intelligent document ingestion and hybrid search system. Upload PDFs, DOCX, and TXT files and search across them using natural language — powered by semantic vector search and BM25 keyword search fused via Reciprocal Rank Fusion.

---

## Features

- **Hybrid search** — combines semantic similarity (Qdrant) and keyword matching (BM25) for high-precision retrieval
- **Multi-format ingestion** — supports PDF, DOCX, TXT, and Markdown
- **User isolation** — each user can only access their own documents
- **JWT authentication** — register, login, and protected routes
- **Metadata filtering** — filter search results by source, category, or client
- **Minimalist UI** — clean Next.js frontend with search, upload, and document management pages
- **Fully Dockerized** — one command to run the entire stack

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | Next.js 14 + Tailwind CSS |
| Vector DB | Qdrant |
| Relational DB | PostgreSQL |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) |
| Keyword Search | BM25 (`rank_bm25`) |
| Auth | JWT (`python-jose`) + bcrypt |
| Orchestration | Docker Compose |

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) + Docker Compose

### Run

```bash
git clone https://github.com/yourname/document-retrieval.git
cd document-retrieval
docker compose up --build
```

> First build takes ~5 minutes — the embedding model (~90MB) is downloaded into the image.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

### First steps

1. Open `http://localhost:3000`
2. Register an account
3. Upload a document on the Upload page
4. Search across it on the Search page

---

## API Reference

### Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| GET | `/auth/me` | Current user info |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingest/` | Upload and ingest a document |
| GET | `/ingest/documents` | List your documents |
| DELETE | `/ingest/documents/{id}` | Delete a document and its chunks |

### Search

| Method | Endpoint | Description |
|---|---|---|
| POST | `/search/` | Hybrid semantic + keyword search |
| GET | `/search/?q=...` | Quick search via query param |

---

## Stopping and Starting

```bash
docker compose down          # Stop (data is preserved)
docker compose up            # Start again
docker compose down --volumes  # Stop and wipe all data
```