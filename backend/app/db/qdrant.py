from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import settings

_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
    return _client


async def init_qdrant():
    client = get_qdrant()
    existing = await client.get_collections()
    existing_names = [c.name for c in existing.collections]

    if settings.qdrant_collection not in existing_names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dim,
                distance=Distance.COSINE,
            ),
        )
        print(f"[Qdrant] Created collection '{settings.qdrant_collection}'")
    else:
        print(f"[Qdrant] Collection '{settings.qdrant_collection}' already exists")