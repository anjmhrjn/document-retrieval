import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select, text

from app.api.routes import ingest
from app.db.postgres import init_db
from app.db.qdrant import init_qdrant

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

    print("[Startup] Ready.")
    yield

    print("[Shutdown] Cleaning up...")

app = FastAPI(
    title="Document Retrieval - Intelligent Document Ingestion & Search",
    description=(
        "A hybrid semantic + keyword search system for unstructured documents. "
        "Upload PDFs, DOCX, or TXT files, then search with natural language."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(ingest.router)

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Document Retrieval API",
        "status": "running",
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}