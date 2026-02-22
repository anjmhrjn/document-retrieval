import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.postgres import Chunk, Document, get_db
from app.ingestion.chunker import split_into_chunks
from app.ingestion.parser import extract_text, is_supported

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/", summary="Upload and ingest a document")
async def ingest_document(
    file: UploadFile = File(...),
    source: str = Form(None, description="e.g. 'lecture', 'legal', 'internal'"),
    category: str = Form(None, description="User-defined tag"),
    client: str = Form(None, description="Client name (for legal use case)"),
    db: AsyncSession = Depends(get_db),
):
    # ── Validate file type ─────────────────────────────────────────────────
    if not is_supported(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: .pdf, .docx, .txt, .md",
        )

    # ── Save uploaded file ─────────────────────────────────────────────────
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # ── Extract text ───────────────────────────────────────────────────────
    try:
        raw_text = extract_text(str(file_path))
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Text extraction failed: {e}")

    if not raw_text.strip():
        os.remove(file_path)
        raise HTTPException(status_code=422, detail="Document appears to be empty or unreadable.")

    # ── Save document record ───────────────────────────────────────────────
    file_ext = Path(file.filename).suffix.lower().lstrip(".")
    doc = Document(
        filename=file.filename,
        file_type=file_ext,
        source=source,
        category=category,
        client=client,
    )
    db.add(doc)
    await db.flush()  # Get the document ID before committing

    # ── Chunk text ─────────────────────────────────────────────────────────
    chunks = split_into_chunks(raw_text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract meaningful chunks.")

    await db.commit()

    return {
        "message": "Document ingested successfully.",
        "document_id": doc.id,
        "filename": file.filename,
        "chunks_created": len(chunks),
    }


@router.get("/documents", summary="List all ingested documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.upload_time.desc()))
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "source": d.source,
            "category": d.category,
            "client": d.client,
            "upload_time": d.upload_time,
        }
        for d in docs
    ]


@router.delete("/documents/{document_id}", summary="Delete a document and its chunks")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    await db.delete(doc)
    await db.commit()

    return {"message": f"Document {document_id} deleted."}