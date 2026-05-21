"""
Build dense (FAISS) + sparse (BM25) indices over the chunked corpus.

Outputs (under med_assist/index/store/):
  faiss.index           normalized inner-product over MiniLM embeddings
  chunks.jsonl          one Chunk per line (id-aligned with FAISS row id)
  bm25.pkl              pickled BM25Okapi over tokenized chunk text
  manifest.json         build metadata (model, dims, count, timestamp)
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import time
import unicodedata
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from med_assist.data.chunker import chunk_corpus
from med_assist.data.loader import load_medicines
from med_assist.data.models import Chunk

INDEX_DIR = Path(__file__).resolve().parent / "store"
# Multilingual MiniLM: same architecture/dim as the English-only baseline,
# but trained on paraphrase pairs across 50+ languages including Romanian.
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Romanian function words. Without this filter, brand suffixes like
# "CONCOR AM" tokenize to {"concor", "am"} and dominate any user query
# that contains the Romanian verb "am" (= I have).
STOPWORDS_RO = {
    "a", "ai", "am", "ar", "are", "ati", "au",
    "ca", "care", "cat", "cate", "ce", "cel", "cea", "cele", "cu", "cum",
    "da", "de", "din", "doar", "dupa",
    "e", "el", "ea", "ei", "ele", "este", "esti", "eu", "este",
    "fara", "fi", "fie", "fost",
    "i", "ii", "il", "in", "intre",
    "la", "le", "lor", "lui",
    "ma", "mai", "mea", "meu", "mi", "mie",
    "ne", "nici", "noi", "noastra", "noi", "nu",
    "o", "ori",
    "pe", "pentru", "peste", "pot", "prin",
    "sa", "sau", "se", "si", "sunt",
    "ta", "te", "tu", "tine",
    "un", "una", "unde", "unei", "unor",
    "va", "voi", "vor",
}


def fold_diacritics(text: str) -> str:
    """Strip Romanian diacritics so users typing 'diaree' match 'diaree' too."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def tokenize(text: str) -> list[str]:
    folded = fold_diacritics(text.lower())
    out: list[str] = []
    buf: list[str] = []
    for ch in folded:
        if ch.isalnum():
            buf.append(ch)
        elif buf:
            out.append("".join(buf))
            buf = []
    if buf:
        out.append("".join(buf))
    return [t for t in out if len(t) > 1 and t not in STOPWORDS_RO]


def build_dense_index(chunks: list[Chunk], model_id: str, batch_size: int = 64) -> tuple:
    logging.info("loading model: %s", model_id)
    model = SentenceTransformer(model_id)
    dim = model.get_sentence_embedding_dimension()
    logging.info("encoding %d chunks (dim=%d)", len(chunks), dim)
    t0 = time.time()
    embeddings = model.encode(
        [c.text for c in chunks],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype(np.float32)
    elapsed = time.time() - t0
    logging.info("encoded in %.1fs (%.0f chunks/s)", elapsed, len(chunks) / elapsed)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index, dim, elapsed


def build_sparse_index(chunks: list[Chunk]) -> BM25Okapi:
    logging.info("tokenizing %d chunks for BM25", len(chunks))
    t0 = time.time()
    tokenized = [tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    logging.info("BM25 built in %.1fs (avg %.1f tokens/chunk)",
                 time.time() - t0,
                 sum(len(t) for t in tokenized) / max(len(tokenized), 1))
    return bm25


def save(index_dir: Path, faiss_index, chunks: list[Chunk], bm25: BM25Okapi, manifest: dict) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(faiss_index, str(index_dir / "faiss.index"))
    with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.model_dump(), ensure_ascii=False) + "\n")
    with (index_dir / "bm25.pkl").open("wb") as f:
        pickle.dump(bm25, f)
    (index_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None, help="limit medicines for fast smoke test")
    parser.add_argument("--out", type=Path, default=INDEX_DIR)
    args = parser.parse_args()

    medicines = load_medicines()
    if args.limit:
        medicines = medicines[: args.limit]
    chunks = chunk_corpus(medicines)
    logging.info("loaded %d medicines -> %d chunks", len(medicines), len(chunks))

    faiss_index, dim, encode_secs = build_dense_index(chunks, args.model)
    bm25 = build_sparse_index(chunks)

    manifest = {
        "model": args.model,
        "embedding_dim": dim,
        "medicine_count": len(medicines),
        "chunk_count": len(chunks),
        "encode_seconds": round(encode_secs, 1),
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save(args.out, faiss_index, chunks, bm25, manifest)
    logging.info("saved index to %s", args.out)
    logging.info("manifest: %s", json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
