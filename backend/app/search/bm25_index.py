"""
BM25 index for keyword-based retrieval.

The index is kept in memory and rebuilt from the database on startup.
It maps BM25 rank positions back to Qdrant point IDs for score fusion.
"""

import re
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi


@dataclass
class BM25Index:
    corpus_ids: list[str] = field(default_factory=list)  # qdrant_ids in order
    corpus_texts: list[str] = field(default_factory=list)
    _bm25: BM25Okapi | None = None

    def add(self, qdrant_id: str, text: str):
        self.corpus_ids.append(qdrant_id)
        self.corpus_texts.append(text)
        self._bm25 = None  # Invalidate

    def build(self):
        tokenized = [_tokenize(t) for t in self.corpus_texts]
        self._bm25 = BM25Okapi(tokenized)

    def query(self, query_text: str, top_k: int) -> list[tuple[str, float]]:
        """Returns list of (qdrant_id, bm25_score) sorted descending."""
        if self._bm25 is None:
            if not self.corpus_texts:
                return []
            self.build()

        tokens = _tokenize(query_text)
        scores = self._bm25.get_scores(tokens)

        # Pair with IDs and sort
        scored = sorted(
            zip(self.corpus_ids, scores),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(qid, float(score)) for qid, score in scored[:top_k]]

    def rebuild_from(self, entries: list[tuple[str, str]]):
        """Rebuild index from list of (qdrant_id, text) tuples."""
        self.corpus_ids = [e[0] for e in entries]
        self.corpus_texts = [e[1] for e in entries]
        self.build()

    @property
    def size(self) -> int:
        return len(self.corpus_ids)


def _tokenize(text: str) -> list[str]:
    """Lowercase + split on non-alphanumeric."""
    text = text.lower()
    return re.findall(r"\b\w+\b", text)


# Global singleton index
bm25_index = BM25Index()