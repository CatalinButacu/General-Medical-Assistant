"""
LLM-as-judge faithfulness grading for OTC_SAFE eval cases.

For each case: (1) build the same retrieved context the production prompt
would see, (2) ask Gemini to generate a recommend-style answer, (3) ask
Gemini *again* with a judge prompt — "is every medical claim in this answer
supported by the retrieved context?" Returns a verdict (faithful: yes/no)
plus a short rationale.

Two Gemini calls per case. Opt-in only — gated by `--faithfulness` on the
eval CLI. Failures (API error, malformed JSON) are recorded as `faithful=None`
so they don't silently count toward the rate.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional

from med_assist.eval.metrics import CaseEval
from med_assist.llm.client import GeminiClient, build_history
from med_assist.llm.prompts import render_recommend
from med_assist.service import RetrievalService

log = logging.getLogger("medassist.eval.faithfulness")


JUDGE_PROMPT_RO = """\
Ești un evaluator independent al răspunsurilor medicale. Sarcina ta este să
verifici dacă RĂSPUNSUL este fidel CONTEXTULUI PRELUAT.

Fidel înseamnă: orice afirmație medicală din răspuns (nume de medicament,
indicație, doză, contraindicație, efect secundar) este susținută explicit
de context. Răspunsuri vagi sau generale care nu fac afirmații specifice
sunt considerate fidele dacă nu inventează nimic.

NEFIDEL înseamnă: răspunsul introduce un nume de medicament, o doză, o
indicație, sau un efect care NU apare în context.

Returnează DOAR un obiect JSON:
{"faithful": true|false, "rationale": "scurtă explicație în română (max 30 cuvinte)"}
"""


async def _generate_answer(llm: GeminiClient, query: str, hits: list) -> str:
    """Run the same recommend prompt the production /chat would use."""
    system = render_recommend(hits=hits, profile=None, forced_low_confidence=False)
    contents = build_history([{"role": "user", "text": query}])
    parts: list[str] = []
    async for chunk in llm.stream(
        system_instruction=system,
        contents=contents,
        temperature=0.3,
        max_output_tokens=600,
    ):
        parts.append(chunk)
    return "".join(parts).strip()


async def _judge(llm: GeminiClient, query: str, context: str, answer: str) -> tuple[Optional[bool], str]:
    """Returns (faithful, rationale). faithful is None on grading failure."""
    user_payload = f"ÎNTREBARE:\n{query}\n\nCONTEXT PRELUAT:\n{context}\n\nRĂSPUNS DE EVALUAT:\n{answer}"
    contents = build_history([{"role": "user", "text": user_payload}])
    parts: list[str] = []
    try:
        async for chunk in llm.stream(
            system_instruction=JUDGE_PROMPT_RO,
            contents=contents,
            temperature=0.0,
            max_output_tokens=200,
        ):
            parts.append(chunk)
        raw = "".join(parts).strip()
        # Strip a possible ```json fence — Gemini sometimes wraps despite the prompt.
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        return bool(data.get("faithful")), str(data.get("rationale", ""))[:200]
    except Exception as exc:
        log.warning("judge parse failed: %s | raw=%r", exc, "".join(parts)[:200])
        return None, f"judge_error: {type(exc).__name__}"


def _context_for_case(decision) -> str:
    """Concatenate the top-3 medicines' lay summaries + key RCP sections —
    the same evidence the recommend prompt actually exposes to the LLM."""
    parts: list[str] = []
    for hit in decision.medicine_hits[:3]:
        med = hit.medicine
        parts.append(f"## {med.trade_name} ({med.dci}, ATC {med.atc_code})")
        if med.lay_description:
            parts.append(med.lay_description)
        for section in ("indications", "contraindications", "warnings"):
            body = med.rcp_sections.get(section)
            if body:
                parts.append(f"### {section}\n{body[:500]}")
    return "\n\n".join(parts).strip()


def grade_cases(svc: RetrievalService, golden: list[dict], cases: list[CaseEval]) -> None:
    """Mutates `cases` in place: sets faithful + faithfulness_rationale on each
    OTC_SAFE case where retrieval returned at least one medicine. Other cases
    keep faithful=None and don't count toward the rate."""
    llm = GeminiClient()
    case_by_id = {c.case_id: c for c in cases}

    async def _grade_one(golden_case: dict) -> None:
        if golden_case["expected_triage"] != "OTC_SAFE":
            return
        case_id = golden_case["id"]
        case_eval = case_by_id.get(case_id)
        if case_eval is None:
            return
        decision = svc.advise(golden_case["query"], top_k_medicines=5, otc_only=True)
        if not decision.medicine_hits:
            return
        try:
            answer = await _generate_answer(llm, golden_case["query"], decision.medicine_hits)
        except Exception as exc:
            log.warning("answer generation failed for %s: %s", case_id, exc)
            case_eval.faithful = None
            case_eval.faithfulness_rationale = f"answer_error: {type(exc).__name__}"
            return
        verdict, rationale = await _judge(
            llm,
            golden_case["query"],
            _context_for_case(decision),
            answer,
        )
        case_eval.faithful = verdict
        case_eval.faithfulness_rationale = rationale

    async def _grade_all() -> None:
        # Run sequentially (not gather) so we don't hammer Gemini quota and
        # so logging stays readable on a Romanian-language eval print.
        for gc in golden:
            await _grade_one(gc)

    asyncio.run(_grade_all())
