"""Sparse retrieval: tokenize query, score with BM25Okapi.

`tokenize` lives in the light `med_assist.index` package now — pulling it
from `med_assist.index.builder` (which has heavy deps) would defeat the
lazy-import scheme that keeps test collection cheap."""

from __future__ import annotations

from med_assist.data.models import Chunk, RetrievalHit
from med_assist.index import tokenize


class SparseRetriever:
    def __init__(self, bm25, chunks: list[Chunk]):
        self.bm25 = bm25
        self.chunks = chunks

    def search(self, query: str, top_k: int = 50) -> list[RetrievalHit]:
        import numpy as np

        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        top_idx = np.argsort(scores)[::-1][:top_k]
        hits: list[RetrievalHit] = []
        for rank, idx in enumerate(top_idx):
            score = float(scores[idx])
            if score <= 0:
                continue
            hits.append(RetrievalHit(
                chunk=self.chunks[idx],
                score=score,
                source="sparse",
                rank=rank,
            ))
        return hits
