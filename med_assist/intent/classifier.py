"""Rule-based intent classifier.

The chatbot has two very different jobs depending on what the user wants:

  • SYMPTOM_TRIAGE  — "mă doare capul" → ask followups, eventually recommend.
  • MEDICINE_LOOKUP — "ce este Sinupret?" → explain a specific medicine.

Misrouting matters: if a user describes symptoms and we treat the message
as a medicine lookup we skip the red-flag re-check inside the followup
loop; if we treat a medicine-name question as symptoms we end up asking
"unde te doare?" which is the exact bug this layer fixes.

The classifier is deterministic on purpose — every routing decision is
auditable from the matched-terms list, and a cheap rule never silently
mis-routes the way an LLM call would on a quiet day.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

from med_assist.data.models import Medicine
from med_assist.intent.types import IntentResult
from med_assist.observability import observe

# These tokens are real medicine trade names in ANMDM but also everyday
# Romanian words, so a bare occurrence is not enough to call MEDICINE_LOOKUP.
_AMBIGUOUS_NAMES: frozenset[str] = frozenset({
    "apa", "sare", "lapte", "miere", "ulei", "alcool", "ceai",
    "zinc", "fier", "iod", "potasiu", "calciu",
})

# Minimum length for a single-token trade name or DCI to be considered a
# safe match — shorter strings cause too many false positives on common
# Romanian fragments (e.g. "as", "ai", "or").
_MIN_SINGLE_TOKEN_LEN = 4

# Phrases that strongly indicate the user is asking *about* a medicine,
# not describing symptoms. Folded (no diacritics) so the regex doesn't
# have to worry about ă/â/î/ș/ț casing.
_LOOKUP_PHRASES: tuple[str, ...] = (
    r"\bce este\b",
    r"\bce e\b(?!\s+rau)",
    r"\bce face\b",
    r"\bce contine\b",
    r"\bla ce (e|este) (bun|folosit|indicat)\b",
    r"\bla ce serveste\b",
    r"\bla ce ajuta\b",
    r"\bpentru ce (e|este|se da|se ia|serveste)\b",
    r"\bcand (iau|se ia|trebuie|se da)\b",
    r"\bcum se ia\b",
    r"\bindicatii\b",
    r"\beste indicat\b",
    r"\bexplica\b",
    r"\bexplica.mi\b",
    r"\bce e (cu|asta)\b",
    r"\bla ce e\b",
    r"\bla ce folose\b",
    r"\bin ce caz\b",
    r"\bce trateaz\b",
    r"\bla ce.{0,10}foloseste\b",
)

# Phrases that say "I have a symptom right now" — when these co-occur with
# a medicine name we still want SYMPTOM_TRIAGE (e.g. "Am Nurofen dar mă
# doare capul rău" — they're not asking what Nurofen is).
_SYMPTOM_PHRASES: tuple[str, ...] = (
    r"\bma doare\b",
    r"\bma simt\b",
    r"\bam febra\b",
    r"\bam dureri\b",
    r"\bam o durere\b",
    r"\bsimt\b",
    r"\bnu pot\b",
    r"\bsuf[ea]r\b",
    r"\btuse\s",
    r"\braceala\b",
    r"\bracit\b",
    r"\balergie\b",
    r"\bsimptom\b",
)

_LOOKUP_RE = re.compile("|".join(_LOOKUP_PHRASES), flags=re.IGNORECASE)
_SYMPTOM_RE = re.compile("|".join(_SYMPTOM_PHRASES), flags=re.IGNORECASE)


def _fold(text: str) -> str:
    """Lowercase + strip diacritics. Mirrors triage.redflags._fold so the
    intent layer matches on the same normalized text the rule engine sees."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokenize(folded: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", folded)


class IntentClassifier:
    """Build name indices once at startup, then `classify()` per turn."""

    def __init__(self, medicines: Iterable[Medicine]):
        # Single-token name -> Medicine (first wins; brands rarely collide
        # in ANMDM and when they do the canonical 'Strepsils' beats a
        # rare same-name molecule for lookup intent).
        self._by_single_token: dict[str, Medicine] = {}
        # Multi-word folded trade name -> Medicine, indexed by token count
        # so we only slide windows of the right size against the query.
        self._by_multitoken: dict[int, dict[str, Medicine]] = {}
        # Single-token DCI (active substance) -> Medicine. Multiple meds
        # can share a DCI (paracetamol → many brands); we keep the first
        # OTC we see so the explain branch shows a representative entry.
        self._by_dci_single: dict[str, Medicine] = {}

        for med in medicines:
            self._index_name(med.trade_name, med)
            self._index_dci(med.dci, med)

    def _index_name(self, name: str, med: Medicine) -> None:
        folded = _fold(name).strip()
        if not folded:
            return
        tokens = _tokenize(folded)
        if not tokens:
            return
        if len(tokens) == 1:
            tok = tokens[0]
            if len(tok) < _MIN_SINGLE_TOKEN_LEN or tok in _AMBIGUOUS_NAMES:
                return
            self._by_single_token.setdefault(tok, med)
        else:
            key = " ".join(tokens)
            self._by_multitoken.setdefault(len(tokens), {}).setdefault(key, med)

    def _index_dci(self, dci: str, med: Medicine) -> None:
        folded = _fold(dci).strip()
        if not folded:
            return
        tokens = _tokenize(folded)
        # Multi-word DCIs ("acid acetilsalicilic") are uncommon as a
        # user-typed query; the single-token DCI is what people remember.
        if len(tokens) != 1:
            return
        tok = tokens[0]
        if len(tok) < 5 or tok in _AMBIGUOUS_NAMES:
            return
        # Only index OTC entries as the representative DCI hit — RX
        # explanations are out of scope for this branch.
        if med.rx_status not in ("OTC", "MIXED"):
            return
        self._by_dci_single.setdefault(tok, med)

    def _find_medicine(self, folded_query: str) -> tuple[Optional[Medicine], list[str]]:
        """Return (medicine, matched_terms) or (None, [])."""
        tokens = _tokenize(folded_query)
        if not tokens:
            return None, []

        # Multi-word trade names first — "Coldrex Hotrem" beats "Coldrex" alone.
        for n in sorted(self._by_multitoken.keys(), reverse=True):
            bucket = self._by_multitoken[n]
            for i in range(len(tokens) - n + 1):
                key = " ".join(tokens[i : i + n])
                med = bucket.get(key)
                if med is not None:
                    return med, [key]

        for tok in tokens:
            med = self._by_single_token.get(tok)
            if med is not None:
                return med, [tok]

        for tok in tokens:
            med = self._by_dci_single.get(tok)
            if med is not None:
                return med, [tok]

        return None, []

    @observe(name="intent.classify")
    def classify(self, text: str) -> IntentResult:
        folded = _fold(text)
        if not folded.strip():
            return IntentResult(
                label="SYMPTOM_TRIAGE",
                confidence=0.0,
                rationale="Mesaj gol — căderea pe fluxul implicit.",
            )

        medicine, matched = self._find_medicine(folded)
        lookup_phrase = bool(_LOOKUP_RE.search(folded))
        symptom_phrase = bool(_SYMPTOM_RE.search(folded))
        word_count = len(_tokenize(folded))

        if medicine is not None and lookup_phrase and not symptom_phrase:
            return IntentResult(
                label="MEDICINE_LOOKUP",
                confidence=0.9,
                medicine=medicine,
                matched_terms=matched,
                rationale=(
                    f"Întrebare directă despre {medicine.trade_name} "
                    f"(potrivit: {', '.join(matched)})."
                ),
            )

        if medicine is not None and not symptom_phrase and word_count <= 10:
            return IntentResult(
                label="MEDICINE_LOOKUP",
                confidence=0.7,
                medicine=medicine,
                matched_terms=matched,
                rationale=(
                    f"Mesaj scurt centrat pe {medicine.trade_name} fără simptome "
                    "declarate — interpretat ca cerere de explicație."
                ),
            )

        return IntentResult(
            label="SYMPTOM_TRIAGE",
            confidence=0.6 if symptom_phrase else 0.4,
            medicine=medicine,
            matched_terms=matched,
            rationale=(
                "Simptom explicit detectat." if symptom_phrase
                else "Fără potrivire pe nume de medicament și fără cerere de explicație."
            ),
        )
