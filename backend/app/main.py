from fastapi import FastAPI

app = FastAPI(
    title="Document Retrieval - Intelligent Document Ingestion & Search",
    description=(
        "A hybrid semantic + keyword search system for unstructured documents. "
        "Upload PDFs, DOCX, or TXT files, then search with natural language."
    ),
    version="1.0.0",
)

@app.get("/", target=["Health"])
async def root():
    return {
        "service": "Document Retrieval API",
        "status": "running",
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}