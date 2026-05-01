"""
Top-level retrieval service: load indices once, expose a query() that
returns medicine-level recommendations with retrieval provenance.

Flow:
  query -> dense + sparse retrieve -> RRF fusion -> filter
        -> dedup chunks to medicines -> top-N medicines

Filtering options at query time:
  rx_filter:        keep only medicines with rx_status in this set
  exclude_chunks:   skip chunk types (e.g. don't surface contraindications text)
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Optional

import faiss

from med_assist.data.models import Chunk, Medicine, MedicineHit, RetrievalHit
from med_assist.data.loader import load_medicines
from med_assist.index.builder import INDEX_DIR
from med_assist.retrieval.dense import DenseRetriever
from med_assist.retrieval.fusion import reciprocal_rank_fusion
from med_assist.retrieval.sparse import SparseRetriever


class RetrievalService:
    def __init__(self, index_dir: Path = INDEX_DIR):
        self.index_dir = index_dir
        self.manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        self.chunks = self._load_chunks(index_dir / "chunks.jsonl")
        self.faiss_index = faiss.read_index(str(index_dir / "faiss.index"))
        with (index_dir / "bm25.pkl").open("rb") as f:
            self.bm25 = pickle.load(f)

        model_id = self.manifest["model"]
        self.dense = DenseRetriever(self.faiss_index, self.chunks, model_id)
        self.sparse = SparseRetriever(self.bm25, self.chunks)

        self._medicines_by_id: dict[str, Medicine] = {m.id: m for m in load_medicines()}
        logging.info(
            "RetrievalService ready: %d chunks across %d medicines (model=%s)",
            len(self.chunks), len(self._medicines_by_id), model_id,
        )

    @staticmethod
    def _load_chunks(path: Path) -> list[Chunk]:
        out: list[Chunk] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                out.append(Chunk(
                    id=d["id"], medicine_id=d["medicine_id"],
                    text=d["text"], chunk_type=d["chunk_type"],
                    metadata=d.get("metadata", {}),
                ))
        return out

    @staticmethod
    def _dedup_by_medicine(hits: list) -> list:
        """Keep only the single best-scoring chunk per medicine, preserving order.

        Without this, near-duplicate SKU chunks (e.g. 3 SINUPRET variants each
        with the same lay_summary) flood a retriever's top-K and crowd out
        the second-best medicine.
        """
        seen: set[str] = set()
        out = []
        new_rank = 0
        for h in hits:
            mid = h.chunk.medicine_id
            if mid in seen:
                continue
            seen.add(mid)
            h.rank = new_rank
            new_rank += 1
            out.append(h)
        return out

    def query(
        self,
        query: str,
        top_k_chunks: int = 50,
        top_k_medicines: int = 10,
        rx_filter: Optional[set[str]] = None,
        exclude_chunk_types: Optional[set[str]] = None,
    ) -> list[MedicineHit]:
        dense_hits = self._dedup_by_medicine(self.dense.search(query, top_k=top_k_chunks * 2))
        sparse_hits = self._dedup_by_medicine(self.sparse.search(query, top_k=top_k_chunks * 2))
        fused = reciprocal_rank_fusion([dense_hits, sparse_hits], top_k=top_k_chunks)

        if exclude_chunk_types:
            fused = [h for h in fused if h.chunk.chunk_type not in exclude_chunk_types]

        if rx_filter is not None:
            fused = [h for h in fused if h.chunk.metadata.get("rx_status") in rx_filter]

        # Dedup chunks to medicine level — keep best supporting chunk per medicine
        by_med: dict[str, dict] = {}
        for hit in fused:
            mid = hit.chunk.medicine_id
            if mid not in by_med:
                by_med[mid] = {"score": hit.score, "best": hit.chunk, "supporting": [hit.chunk]}
            else:
                by_med[mid]["supporting"].append(hit.chunk)
                if hit.score > by_med[mid]["score"]:
                    by_med[mid]["score"] = hit.score
                    by_med[mid]["best"] = hit.chunk

        ordered = sorted(by_med.items(), key=lambda kv: kv[1]["score"], reverse=True)[:top_k_medicines]
        out: list[MedicineHit] = []
        for mid, entry in ordered:
            med = self._medicines_by_id.get(mid)
            if med is None:
                continue
            out.append(MedicineHit(
                medicine=med,
                score=entry["score"],
                best_chunk=entry["best"],
                supporting_chunks=entry["supporting"],
            ))
        return out
