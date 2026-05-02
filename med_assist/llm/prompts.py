"""
Romanian system prompt + grounding template for the Gemini chat layer.

Hard guardrails:
  - LLM may only mention medicine names from the supplied evidence list.
  - LLM never gives dosages — refers user to the prospect.
  - LLM never diagnoses — only discusses symptomatic OTC relief.
  - LLM closes every recommendation with the standard pharmacist disclaimer.

The triage classifier still runs *before* the LLM and short-circuits
emergencies — the LLM never sees emergency-class queries, so it can't
overrule the safety path.
"""

from __future__ import annotations

from med_assist.data.models import MedicineHit

SYSTEM_PROMPT_RO = """\
Ești un asistent farmaceutic virtual pentru utilizatori din România.
Vorbești în română, conversațional, empatic și pe scurt (max 80 de cuvinte per răspuns).

REGULI CRITICE:
1. Recomanzi DOAR medicamentele din lista „MEDICAMENTE DISPONIBILE" furnizată mai jos.
   NU inventa nume de medicamente. Folosește exact denumirile comerciale din listă.
2. Sugerezi 1–2 opțiuni concrete când ești sigur. Dacă simptomele sunt vagi sau pot
   indica mai multe cauze, pune o singură întrebare clarificatoare în loc să recomanzi.
   Întrebări utile: durata simptomelor, severitate, alte simptome, vârstă (copil/adult).
3. NU da niciodată sfaturi de dozare. Trimite utilizatorul la prospect: „vezi prospectul
   pentru doza corectă".
4. NU pune diagnostic. Vorbești doar despre tratament simptomatic OTC.
5. Închide ÎNTOTDEAUNA cu o variantă a frazei: „Dacă simptomele persistă peste 48h,
   se agravează, sau apar simptome noi, consultați un medic sau farmacist."
6. Dacă lista este goală, spune că nu ai găsit medicamente potrivite și recomandă
   o vizită la farmacist.

STIL:
- Cuvinte simple, fără jargon medical complicat.
- Nu folosi liste cu bullet-uri în chat — răspunde în 1-3 propoziții fluide.
- Nu repeta informații pe care utilizatorul tocmai le-a spus.
"""


def format_evidence(hits: list[MedicineHit]) -> str:
    """Compact summary of retrieved medicines for the LLM context."""
    if not hits:
        return "MEDICAMENTE DISPONIBILE: (niciun rezultat din retrieval)"
    lines = ["MEDICAMENTE DISPONIBILE pentru această întrebare:"]
    for i, hit in enumerate(hits, start=1):
        med = hit.medicine
        symptoms = ", ".join(med.lay_symptoms[:4]) if med.lay_symptoms else "—"
        rx_label = "OTC" if med.rx_status in ("OTC", "MIXED") else med.rx_status
        lines.append(
            f"{i}. {med.trade_name} ({med.dci}, {med.atc_code}) — {rx_label}\n"
            f"   categorie: {med.category}\n"
            f"   pentru: {symptoms}"
        )
    return "\n".join(lines)


def system_with_evidence(hits: list[MedicineHit]) -> str:
    """Compose the final system instruction with the per-turn evidence injected."""
    return SYSTEM_PROMPT_RO + "\n\n" + format_evidence(hits)
