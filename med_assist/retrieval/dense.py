"""Dense retrieval: encode query with sentence-transformers, search FAISS.

Heavy deps (faiss, sentence_transformers, numpy.float32 cast) are imported
inside the methods that actually use them — keeping module-level import light
so tests with `_StubRetrieval` don't pull a 200MB faiss wheel."""

from __future__ import annotations

from med_assist.data.models import Chunk, RetrievalHit


class DenseRetriever:
    def __init__(self, faiss_index, chunks: list[Chunk], model_id: str):
        from sentence_transformers import SentenceTransformer

        self.index = faiss_index
        self.chunks = chunks
        self.model = SentenceTransformer(model_id)

    def search(self, query: str, top_k: int = 50) -> list[RetrievalHit]:
        import numpy as np

        query_vec = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).astype(np.float32)
        scores, indices = self.index.search(query_vec, top_k)
        hits: list[RetrievalHit] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0:
                continue
            hits.append(RetrievalHit(
                chunk=self.chunks[idx],
                score=float(score),
                source="dense",
                rank=rank,
            ))
        return hits
