from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    """Load model once and cache it for the lifetime of the process."""
    print(f"[Embedder] Loading model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    print("[Embedder] Model loaded.")
    return model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Returns a list of float vectors.
    """
    model = get_embedder()
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,  # Cosine sim = dot product on normalized vecs
    )
    return embeddings.tolist()

def embed_query(query: str) -> list[float]:
    """Generate embedding for a single query string."""
    return embed_texts([query])[0]