"""
Hybrid Search: Reciprocal Rank Fusion (RRF) of semantic + BM25 results.

Why RRF instead of raw score fusion?
- Semantic scores (cosine) and BM25 scores have different scales.
- RRF normalizes by rank position, making fusion stable and robust.
- Formula: RRF(d) = Σ 1 / (k + rank(d))  where k=60 is a smoothing constant.
"""

from dataclasses import dataclass

from qdrant_client.models import Filter

from app.core.config import settings
from app.db.qdrant import get_qdrant
from app.processing.embedder import embed_query
from app.search.bm25_index import bm25_index


RRF_K = 60  # Standard RRF smoothing constant


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
    top_k: int = None,
    filters: dict | None = None,
) -> list[SearchResult]:
    """
    Performs hybrid search combining:
      1. Semantic search via Qdrant
      2. Keyword search via BM25
    Results are fused using Reciprocal Rank Fusion.
    """
    top_k = top_k or settings.top_k
    fetch_k = top_k * 3  # Fetch more candidates before re-ranking

    # ── 1. Semantic search ─────────────────────────────────────────────────
    query_vector = embed_query(query)
    qdrant_filter = _build_qdrant_filter(filters)

    qdrant_client = get_qdrant()
    semantic_hits = await qdrant_client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=fetch_k,
        query_filter=qdrant_filter,
        with_payload=True,
    )

    semantic_ranked: dict[str, int] = {
        str(hit.id): rank for rank, hit in enumerate(semantic_hits, start=1)
    }
    payload_map: dict[str, dict] = {
        str(hit.id): hit.payload for hit in semantic_hits
    }

    # ── 2. BM25 keyword search ──────────────────────────────────────────────
    bm25_results = bm25_index.query(query, top_k=fetch_k)
    bm25_ranked: dict[str, int] = {
        qid: rank for rank, (qid, _) in enumerate(bm25_results, start=1)
    }

    # Collect all candidate IDs
    all_ids = set(semantic_ranked.keys()) | set(bm25_ranked.keys())

    # ── 3. Reciprocal Rank Fusion ───────────────────────────────────────────
    rrf_scores: dict[str, float] = {}
    for doc_id in all_ids:
        sem_rank = semantic_ranked.get(doc_id, fetch_k + 1)
        bm25_rank = bm25_ranked.get(doc_id, fetch_k + 1)

        sem_rrf = settings.hybrid_alpha * (1 / (RRF_K + sem_rank))
        bm25_rrf = (1 - settings.hybrid_alpha) * (1 / (RRF_K + bm25_rank))

        rrf_scores[doc_id] = sem_rrf + bm25_rrf

    # Sort by fused score
    ranked_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]

    # ── 4. Fetch missing payloads from Qdrant if needed ────────────────────
    missing_ids = [uid for uid in ranked_ids if uid not in payload_map]
    if missing_ids:
        fetched = await qdrant_client.retrieve(
            collection_name=settings.qdrant_collection,
            ids=missing_ids,
            with_payload=True,
        )
        for point in fetched:
            payload_map[str(point.id)] = point.payload

    # ── 5. Build results ───────────────────────────────────────────────────
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


def _build_qdrant_filter(filters: dict | None) -> Filter | None:
    """Convert filter dict to Qdrant filter model."""
    if not filters:
        return None

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    conditions = []
    for key, value in filters.items():
        if value:
            conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )

    return Filter(must=conditions) if conditions else None