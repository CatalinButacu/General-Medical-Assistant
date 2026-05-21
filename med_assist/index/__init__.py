"""Light constants + tokenizer used by both index builder and sparse retrieval.

These are deliberately heavy-dep-free (no faiss, no sentence_transformers, no
rank_bm25) so test modules that touch `med_assist.conversation` →
`med_assist.service` don't transitively need a 200MB faiss wheel installed.
The actual index build (`med_assist.index.builder`) still pulls those in."""

from __future__ import annotations

import unicodedata
from pathlib import Path

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


__all__ = ["INDEX_DIR", "DEFAULT_MODEL", "STOPWORDS_RO", "fold_diacritics", "tokenize"]
