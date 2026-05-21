"""
Top-level retrieval service: load FAISS+BM25 indices once, expose
`advise()` — the single entry point that runs triage, retrieval and
returns a TriageDecision the chatbot UI consumes.

Pipeline (advise):
  query -> dense + sparse retrieve -> dedup-by-medicine within each
        -> Reciprocal Rank Fusion -> rx-status filter -> group by medicine
        -> classify (EMERGENCY / OTC_SAFE / UNCERTAIN with sparse-signal gate)
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import re
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

from med_assist.data.loader import load_medicines
from med_assist.data.models import Chunk, Medicine, MedicineHit, RetrievalHit
from med_assist.index import INDEX_DIR
from med_assist.observability import observe
from med_assist.retrieval.dense import DenseRetriever
from med_assist.retrieval.fusion import reciprocal_rank_fusion
from med_assist.retrieval.sparse import SparseRetriever
from med_assist.triage.classifier import TriageDecision, classify

if TYPE_CHECKING:
    from med_assist.retrieval.rerank import Reranker

log = logging.getLogger("medassist.service")

# Romanian + English stopwords + pharma packaging boilerplate that adds noise
# to OCR-text matching. Kept here next to match_by_name() so the BM25-ladder
# logic lives in one place rather than spread between the route and the service.
_OCR_STOPWORDS = frozenset({
    "de", "la", "cu", "si", "in", "pe", "din", "sau", "pentru", "fara", "intre", "doar",
    "the", "and", "of", "for", "with", "to", "in",
    "lot", "exp", "expirare", "valabil", "pana", "fabricat", "import", "importator",
    "produs", "prospect", "rcp", "atc", "anmdm", "comprimate", "capsule", "filmate",
    "sirop", "unguent", "crema", "drajeuri", "orala", "soluție", "suspensie", "sol",
    "mg", "ml", "mcg", "ui", "iu", "ug", "tablete", "ambalaj", "buc", "buc.",
})


def _strip_pharma_suffixes(name: str) -> str:
    """Strip dose/form noise so a partial OCR like 'PARACETAMOL ZENTIVA 500MG' still matches."""
    s = re.sub(r"\b\d+([\.,]\d+)?\s*(mg/ml|mg|ml|mcg|μg|g|ui|iu)\b", " ", name, flags=re.I)
    s = re.sub(r"\b(comprimate|capsule|sirop|unguent|drajeuri|filmate|orala|suspensie|crema|sol\.?)\b", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def _ocr_query_phrases(all_text: str) -> list[str]:
    """Per-line phrases + 2-3-word substrings from an OCR dump, filtered down
    to alphabetic-leaning phrases that aren't entirely stopwords."""
    phrases: list[str] = []
    seen: set[str] = set()
    for line in all_text.splitlines():
        cleaned = re.sub(r"[^A-Za-zĂÂÎȘȚăâîșț0-9 \-]", " ", line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            continue
        words = [w for w in cleaned.split() if len(w) >= 3 and not w.isdigit() and w.lower() not in _OCR_STOPWORDS]
        if not words:
            continue
        full = " ".join(words)
        if full not in seen:
            seen.add(full)
            phrases.append(full)
        for n in (3, 2):
            for i in range(len(words) - n + 1):
                window = " ".join(words[i:i + n])
                if window not in seen:
                    seen.add(window)
                    phrases.append(window)
    return phrases[:25]


class RetrievalService:
    def __init__(self, index_dir: Path = INDEX_DIR):
        # Lazy faiss import: tests use _StubRetrieval and shouldn't need to
        # have a 200MB faiss wheel on PATH for pytest collection.
        import faiss

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

        # Cross-encoder reranker is opt-out via env (default on). Lazy-loaded
        # on first /chat turn so test/import paths don't pay the model load.
        self._rerank_enabled: bool = os.getenv("RERANK_ENABLED", "true").lower() not in ("0", "false", "no")
        self._rerank_top_n: int = int(os.getenv("RERANK_TOP_N", "30"))
        self._reranker: Optional["Reranker"] = None

        logging.info(
            "RetrievalService ready: %d chunks across %d medicines (model=%s, rerank=%s top_n=%d)",
            len(self.chunks), len(self._medicines_by_id), model_id,
            "on" if self._rerank_enabled else "off", self._rerank_top_n,
        )

    def _get_reranker(self) -> Optional["Reranker"]:
        """Lazy-load the cross-encoder. First call downloads / mmaps the model."""
        if not self._rerank_enabled:
            return None
        if self._reranker is None:
            from med_assist.retrieval.rerank import Reranker
            log.info("loading cross-encoder reranker (first /chat after boot will be slower)")
            self._reranker = Reranker()
        return self._reranker

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

    def medicines(self) -> Iterable[Medicine]:
        """Read-only view of the loaded medicine catalogue."""
        return self._medicines_by_id.values()

    @staticmethod
    def _dedup_by_medicine(hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """Keep only the single best-scoring chunk per medicine, preserving order.

        Without this, near-duplicate SKU chunks (e.g. 3 SINUPRET variants each
        with the same lay_summary) flood a retriever's top-K and crowd out
        the second-best medicine.
        """
        seen: set[str] = set()
        out: list[RetrievalHit] = []
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

    def _retrieve(
        self,
        query: str,
        top_k_medicines: int,
        rx_filter: Optional[set[str]],
    ) -> tuple[list[MedicineHit], bool]:
        """Run dense + sparse, fuse, group by medicine. Returns (hits, sparse_signal)."""
        top_k_chunks = max(top_k_medicines * 4, 50)
        dense_hits = self._dedup_by_medicine(self.dense.search(query, top_k=top_k_chunks * 2))
        sparse_hits = self._dedup_by_medicine(self.sparse.search(query, top_k=top_k_chunks * 2))
        sparse_signal = len(sparse_hits) > 0

        fused = reciprocal_rank_fusion([dense_hits, sparse_hits], top_k=top_k_chunks)
        if rx_filter is not None:
            fused = [h for h in fused if h.chunk.metadata.get("rx_status") in rx_filter]

        # Cross-encoder rerank on top-N fused chunks before group-by-medicine.
        # Empirically the biggest single-step retrieval quality lift on hybrid
        # pipelines (MRR@3 ~0.43 → 0.61 in the literature). Skipped silently
        # when RERANK_ENABLED=false or for trivially short result lists.
        reranker = self._get_reranker()
        if reranker is not None and len(fused) > 1:
            fused = reranker.rerank(query, fused, top_k=min(len(fused), self._rerank_top_n))

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
        med_hits: list[MedicineHit] = []
        for mid, entry in ordered:
            med = self._medicines_by_id.get(mid)
            if med is None:
                continue
            med_hits.append(MedicineHit(
                medicine=med,
                score=entry["score"],
                best_chunk=entry["best"],
                supporting_chunks=entry["supporting"],
            ))
        return med_hits, sparse_signal

    @observe(name="retrieval.advise")
    def advise(
        self,
        query: str,
        top_k_medicines: int = 5,
        otc_only: bool = True,
    ) -> TriageDecision:
        """End-to-end pipeline: triage red-flag scan, retrieval, classify."""
        early = classify(query, medicine_hits=None)
        if early.label == "EMERGENCY":
            return early

        rx_filter = {"OTC", "MIXED"} if otc_only else None
        med_hits, sparse_signal = self._retrieve(query, top_k_medicines, rx_filter)
        return classify(query, medicine_hits=med_hits, sparse_signal=sparse_signal)

    @observe(name="retrieval.match_by_name")
    def match_by_name(
        self,
        trade_name: Optional[str],
        all_text: str = "",
        top_k_candidates: int = 3,
    ) -> list[MedicineHit]:
        """OCR-driven trade-name matcher used by /scan.

        Two-stage BM25 ladder: (1) the chosen `trade_name` plus a dose-stripped
        variant; (2) if the best score is still weak, sweep multi-word phrases
        from the full OCR dump. Returns the top-k medicines ordered by score.
        """
        best_by_id: dict[str, RetrievalHit] = {}

        def _record(hits: list[RetrievalHit]) -> None:
            for h in hits:
                mid = h.chunk.medicine_id
                prev = best_by_id.get(mid)
                if prev is None or h.score > prev.score:
                    best_by_id[mid] = h

        if trade_name:
            _record(self._dedup_by_medicine(self.sparse.search(trade_name, top_k=5)))
            stripped = _strip_pharma_suffixes(trade_name)
            if stripped and stripped.upper() != trade_name.upper():
                _record(self._dedup_by_medicine(self.sparse.search(stripped, top_k=5)))

        top_so_far = max((h.score for h in best_by_id.values()), default=0.0)
        if top_so_far < 0.05 and all_text:
            for phrase in _ocr_query_phrases(all_text):
                _record(self._dedup_by_medicine(self.sparse.search(phrase, top_k=3)))

        sorted_hits = sorted(best_by_id.values(), key=lambda h: -h.score)[:top_k_candidates]
        out: list[MedicineHit] = []
        for hit in sorted_hits:
            med = self._medicines_by_id.get(hit.chunk.medicine_id)
            if med is None:
                continue
            out.append(MedicineHit(
                medicine=med,
                score=hit.score,
                best_chunk=hit.chunk,
                supporting_chunks=[hit.chunk],
            ))
        return out
