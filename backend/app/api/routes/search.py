from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_current_user
from app.search.hybrid import hybrid_search

router = APIRouter(prefix="/search", tags=["Search"], dependencies=[Depends(get_current_user)])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    # Optional metadata filters
    source: str | None = Field(None, description="Filter by source (e.g. 'lecture', 'legal')")
    category: str | None = Field(None, description="Filter by category tag")
    client: str | None = Field(None, description="Filter by client name")


class SearchResultItem(BaseModel):
    qdrant_id: str
    score: float
    content: str
    document_id: int
    filename: str
    source: str | None
    category: str | None
    client: str | None
    chunk_index: int


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[SearchResultItem]


@router.post("/", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    user_id = int(current_user["sub"])

    filters = {
        "source": request.source,
        "category": request.category,
        "client": request.client,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    results = await hybrid_search(
        query=request.query,
        user_id=user_id,
        top_k=request.top_k,
        filters=filters or None,
    )

    return SearchResponse(
        query=request.query,
        total_results=len(results),
        results=[
            SearchResultItem(
                qdrant_id=r.qdrant_id,
                score=r.score,
                content=r.content,
                document_id=r.document_id,
                filename=r.filename,
                source=r.source,
                category=r.category,
                client=r.client,
                chunk_index=r.chunk_index,
            )
            for r in results
        ],
    )


@router.get("/", response_model=SearchResponse)
async def search_get(
    q: str = Query(...),
    top_k: int = Query(default=10, ge=1, le=50),
    source: str | None = Query(None),
    category: str | None = Query(None),
    client: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    return await search(
        SearchRequest(query=q, top_k=top_k, source=source, category=category, client=client),
        current_user=current_user,
    )