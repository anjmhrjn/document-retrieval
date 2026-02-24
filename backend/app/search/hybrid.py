"""
Hybrid Search: Reciprocal Rank Fusion (RRF) of semantic + BM25 results.
Results are filtered by owner (uploaded_by) and a minimum relevance threshold
to prevent unrelated documents from surfacing.
"""

from dataclasses import dataclass

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.db.qdrant import get_qdrant
from app.processing.embedder import embed_query
from app.search.bm25_index import bm25_index

RRF_K = 60

MIN_SCORE_THRESHOLD = 0.003


@dataclass
class SearchResult:
    qdrant_id: str
    score: float
    content: str
    document_id: int
    filename: str
    source: str | None
    category: str | None
    client: str | None
    chunk_index: int


async def hybrid_search(
    query: str,
    user_id: int,
    top_k: int = None,
    filters: dict | None = None,
) -> list[SearchResult]:
    top_k = top_k or settings.top_k
    fetch_k = top_k * 3

    # ── 1. Semantic search ─────────────────────────────────────────────────
    query_vector = embed_query(query)
    qdrant_filter = _build_qdrant_filter(user_id, filters)

    qdrant_client = get_qdrant()
    semantic_hits = await qdrant_client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=fetch_k,
        query_filter=qdrant_filter,
        with_payload=True,
        score_threshold=0.2,   # Minimum cosine similarity — drops clearly unrelated chunks
    )

    semantic_ranked: dict[str, int] = {
        str(hit.id): rank for rank, hit in enumerate(semantic_hits, start=1)
    }
    payload_map: dict[str, dict] = {
        str(hit.id): hit.payload for hit in semantic_hits
    }

    # ── 2. BM25 keyword search ──────────────────────────────────────────────
    user_chunk_ids = set(payload_map.keys())  # Only chunks returned by Qdrant (already user-scoped)

    bm25_results = bm25_index.query(query, top_k=fetch_k)
    # Filter BM25 results to only include the current user's chunks
    bm25_ranked: dict[str, int] = {
        qid: rank
        for rank, (qid, _) in enumerate(bm25_results, start=1)
        if qid in user_chunk_ids or qid in semantic_ranked
    }

    # ── 3. Reciprocal Rank Fusion ───────────────────────────────────────────
    all_ids = set(semantic_ranked.keys()) | set(bm25_ranked.keys())

    rrf_scores: dict[str, float] = {}
    for doc_id in all_ids:
        sem_rank = semantic_ranked.get(doc_id, fetch_k + 1)
        bm25_rank = bm25_ranked.get(doc_id, fetch_k + 1)

        sem_rrf = settings.hybrid_alpha * (1 / (RRF_K + sem_rank))
        bm25_rrf = (1 - settings.hybrid_alpha) * (1 / (RRF_K + bm25_rank))

        rrf_scores[doc_id] = sem_rrf + bm25_rrf

    # ── 4. Apply minimum score threshold ───────────────────────────────────
    rrf_scores = {
        uid: score
        for uid, score in rrf_scores.items()
        if score >= MIN_SCORE_THRESHOLD
    }

    ranked_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]

    # ── 5. Fetch missing payloads ──────────────────────────────────────────
    missing_ids = [uid for uid in ranked_ids if uid not in payload_map]
    if missing_ids:
        fetched = await qdrant_client.retrieve(
            collection_name=settings.qdrant_collection,
            ids=missing_ids,
            with_payload=True,
        )
        for point in fetched:
            payload_map[str(point.id)] = point.payload

    # ── 6. Build results ───────────────────────────────────────────────────
    results = []
    for uid in ranked_ids:
        payload = payload_map.get(uid, {})
        results.append(
            SearchResult(
                qdrant_id=uid,
                score=round(rrf_scores[uid], 6),
                content=payload.get("content", ""),
                document_id=payload.get("document_id", -1),
                filename=payload.get("filename", ""),
                source=payload.get("source"),
                category=payload.get("category"),
                client=payload.get("client"),
                chunk_index=payload.get("chunk_index", 0),
            )
        )

    return results


def _build_qdrant_filter(user_id: int, filters: dict | None) -> Filter:
    """Always filter by uploaded_by (user isolation), plus optional metadata filters."""
    conditions = [
        FieldCondition(key="uploaded_by", match=MatchValue(value=user_id))
    ]

    if filters:
        for key, value in filters.items():
            if value:
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )

    return Filter(must=conditions)