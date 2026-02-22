import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.postgres import Chunk, Document, get_db
from app.db.qdrant import get_qdrant
from app.ingestion.chunker import split_into_chunks
from app.ingestion.parser import extract_text, is_supported
from app.processing.embedder import embed_texts
from qdrant_client.models import PointStruct

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

    # ── Generate embeddings ────────────────────────────────────────────────
    texts = [c.content for c in chunks]
    vectors = embed_texts(texts)

    # ── Index into Qdrant + save to Postgres ───────────────────────────────
    qdrant_client = get_qdrant()
    points: list[PointStruct] = []
    db_chunks: list[Chunk] = []

    for chunk, vector in zip(chunks, vectors):
        point_id = str(uuid.uuid4())

        payload = {
            "content": chunk.content,
            "document_id": doc.id,
            "filename": file.filename,
            "source": source,
            "category": category,
            "client": client,
            "chunk_index": chunk.chunk_index,
        }

        points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        db_chunks.append(
            Chunk(
                document_id=doc.id,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                qdrant_id=point_id,
            )
        )

    # Batch upsert to Qdrant
    await qdrant_client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )

    # Persist chunks to Postgres
    db.add_all(db_chunks)
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

    # Collect qdrant IDs to delete
    chunk_result = await db.execute(
        select(Chunk).where(Chunk.document_id == document_id)
    )
    chunks = chunk_result.scalars().all()
    qdrant_ids = [c.qdrant_id for c in chunks]

    if qdrant_ids:
        qdrant_client = get_qdrant()
        await qdrant_client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=qdrant_ids,
        )

    await db.delete(doc)
    await db.commit()

    return {"message": f"Document {document_id} deleted.", "chunks_removed": len(qdrant_ids)}