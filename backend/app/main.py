import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.api.routes import ingest, search, auth
from app.db.postgres import init_db, Chunk
from app.db.qdrant import init_qdrant
from app.search.bm25_index import bm25_index

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup & shutdown logic.
    - Initialize Postgres tables
    """
    print("[Startup] Initializing database...")
    await init_db()

    print("[Startup] Initializing Qdrant...")
    await init_qdrant()

    print("[Startup] Rebuilding BM25 index from database...")
    await _rebuild_bm25()

    print("[Startup] Ready.")
    yield

    print("[Shutdown] Cleaning up...")

async def _rebuild_bm25():
    """Load all chunks from Postgres and rebuild the BM25 index."""
    from app.db.postgres import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Chunk))
        chunks = result.scalars().all()

    entries = [(c.qdrant_id, c.content) for c in chunks]
    if entries:
        bm25_index.rebuild_from(entries)
        print(f"[BM25] Indexed {len(entries)} chunks.")
    else:
        print("[BM25] No existing chunks found — starting fresh.")

app = FastAPI(
    title="Document Retrieval - Intelligent Document Ingestion & Search",
    description=(
        "A hybrid semantic + keyword search system for unstructured documents. "
        "Upload PDFs, DOCX, or TXT files, then search with natural language."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(search.router)

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Document Retrieval API",
        "status": "running",
        "bm25_index_size": bm25_index.size,
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}