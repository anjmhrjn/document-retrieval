import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select, text

from app.api.routes import ingest
from app.db.postgres import Chunk, init_db, engine

async def wait_for_postgres(retries: int = 10, delay: float = 3.0):
    """Retry connecting to Postgres until it's ready."""
    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print("[Startup] Postgres is ready.")
            return
        except Exception as e:
            print(f"[Startup] Postgres not ready (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                await asyncio.sleep(delay)
    raise RuntimeError("Could not connect to Postgres after multiple retries.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup & shutdown logic.
    - Initialize Postgres tables
    """
    print("[Startup] Waiting for Postgres...")
    await wait_for_postgres()

    print("[Startup] Initializing database...")
    await init_db()

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