"""
Reciprocal Rank Fusion: combine multiple ranked lists into a single list.

RRF score for chunk c = sum over rankers r of 1 / (k + rank_r(c)).
Robust to scale differences between dense (cosine) and sparse (BM25),
which is why we use it instead of weighted score addition.
"""

from __future__ import annotations

from typing import Iterable

from med_assist.data.models import RetrievalHit


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[RetrievalHit]],
    k: int = 60,
    top_k: int = 50,
) -> list[RetrievalHit]:
    fused: dict[str, dict] = {}
    for hits in ranked_lists:
        for hit in hits:
            entry = fused.setdefault(hit.chunk.id, {"chunk": hit.chunk, "score": 0.0, "sources": []})
            entry["score"] += 1.0 / (k + hit.rank + 1)
            entry["sources"].append((hit.source, hit.rank, hit.score))
    ordered = sorted(fused.values(), key=lambda e: e["score"], reverse=True)[:top_k]
    return [
        RetrievalHit(
            chunk=e["chunk"],
            score=e["score"],
            source="fusion",
            rank=rank,
        )
        for rank, e in enumerate(ordered)
    ]
