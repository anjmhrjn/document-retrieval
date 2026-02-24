import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.postgres import Chunk, Document, get_db
from app.db.qdrant import get_qdrant
from app.ingestion.chunker import split_into_chunks
from app.ingestion.parser import extract_text, is_supported
from app.processing.embedder import embed_texts
from app.search.bm25_index import bm25_index
from qdrant_client.models import PointStruct

router = APIRouter(prefix="/ingest", tags=["Ingestion"], dependencies=[Depends(get_current_user)])


@router.post("/", summary="Upload and ingest a document")
async def ingest_document(
    file: UploadFile = File(...),
    source: str = Form(None, description="e.g. 'lecture', 'legal', 'internal'"),
    category: str = Form(None, description="User-defined tag"),
    client: str = Form(None, description="Client name (for legal use case)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not is_supported(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: .pdf, .docx, .txt, .md",
        )

    # Save uploaded file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / safe_name

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Extract text
    try:
        raw_text = extract_text(str(file_path))
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Text extraction failed: {e}")

    if not raw_text.strip():
        os.remove(file_path)
        raise HTTPException(status_code=422, detail="Document appears to be empty or unreadable.")

    # Save document record — scoped to current user
    user_id = int(current_user["sub"])
    file_ext = Path(file.filename).suffix.lower().lstrip(".")
    doc = Document(
        uploaded_by=user_id,
        filename=file.filename,
        file_type=file_ext,
        source=source,
        category=category,
        client=client,
    )
    db.add(doc)
    await db.flush()

    # Chunk and embed
    chunks = split_into_chunks(raw_text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract meaningful chunks.")

    texts = [c.content for c in chunks]
    vectors = embed_texts(texts)

    # Index into Qdrant + Postgres
    qdrant_client = get_qdrant()
    points: list[PointStruct] = []
    db_chunks: list[Chunk] = []

    for chunk, vector in zip(chunks, vectors):
        point_id = str(uuid.uuid4())
        payload = {
            "content": chunk.content,
            "document_id": doc.id,
            "uploaded_by": user_id,
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
        bm25_index.add(point_id, chunk.content)

    await qdrant_client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )
    bm25_index.build()

    db.add_all(db_chunks)
    await db.commit()

    return {
        "message": "Document ingested successfully.",
        "document_id": doc.id,
        "filename": file.filename,
        "chunks_created": len(chunks),
    }


@router.get("/documents", summary="List documents belonging to the current user")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["sub"])
    result = await db.execute(
        select(Document)
        .where(Document.uploaded_by == user_id)
        .order_by(Document.upload_time.desc())
    )
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
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["sub"])

    # Only allow deletion of own documents
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.uploaded_by == user_id,
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Fetch all chunk qdrant IDs before deleting
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

    deleted_ids = set(qdrant_ids)
    entries = [
        (qid, text)
        for qid, text in zip(bm25_index.corpus_ids, bm25_index.corpus_texts)
        if qid not in deleted_ids
    ]

    bm25_index.rebuild_from(entries)

    return {
        "message": f"Document {document_id} and all its chunks have been deleted.",
        "chunks_removed": len(qdrant_ids),
    }