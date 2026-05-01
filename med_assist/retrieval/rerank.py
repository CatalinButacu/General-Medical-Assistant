"""
Cross-encoder reranker.

Cross-encoders score (query, candidate) pairs jointly, which is much
more accurate than the dot-product on independently-encoded
embeddings — but ~100x slower per pair. So we only run it on the top
~50 candidates from fusion, then keep the best ~10.

Default: cross-encoder/ms-marco-MiniLM-L-6-v2 (English-trained but
robust to Romanian medical text in our smoke tests; multilingual
alternative: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1).
"""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from med_assist.data.models import RetrievalHit

DEFAULT_RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    def __init__(self, model_id: str = DEFAULT_RERANKER):
        self.model = CrossEncoder(model_id)

    def rerank(self, query: str, hits: list[RetrievalHit], top_k: int) -> list[RetrievalHit]:
        if not hits:
            return []
        pairs = [[query, h.chunk.text] for h in hits]
        scores = self.model.predict(pairs)
        scored = sorted(
            zip(scores, hits),
            key=lambda sh: float(sh[0]),
            reverse=True,
        )[:top_k]
        return [
            RetrievalHit(
                chunk=hit.chunk,
                score=float(score),
                source="rerank",
                rank=rank,
            )
            for rank, (score, hit) in enumerate(scored)
        ]
