"""
Red-flag symptom rules in Romanian for triage routing.

Each rule has:
  - name           stable id for telemetry / tests
  - category       organ system / type, surfaced to user
  - description    short Romanian explanation surfaced to user
  - patterns       list of regex (single = trigger) or tuple-of-regex (all-must-match within text)
  - severity       "emergency" -> 112; "urgent" -> ER asap; "see_doctor" -> doctor visit
  - action_ro      lay-Romanian recommended action

Bias is toward over-triage on safety-critical signs (chest pain, stroke,
anaphylaxis, head injury): false positive sends a healthy user to a
pharmacist; false negative could cost a life.

Rules curated from:
  - NHS 111 triage red flags
  - Romanian SMURD (national emergency service) public guidance
  - WHO IMCI (children) for pediatric flags
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["emergency", "urgent", "see_doctor"]


class RedFlag(BaseModel):
    model_config = ConfigDict(frozen=False)

    name: str
    category: str
    description: str
    severity: Severity
    action_ro: str
    matched_pattern: str = ""


@dataclass
class _Rule:
    name: str
    category: str
    description: str
    severity: Severity
    action_ro: str
    # Each entry is either a single regex (matches alone triggers)
    # or a tuple of regexes (all must match somewhere in the query).
    patterns: list  # list[str | tuple[str, ...]]


CALL_112 = "Sunați 112 imediat. Nu așteptați."
GO_ER = "Mergeți la cea mai apropiată unitate de urgență."
SEE_DOCTOR = "Consultați medicul cât mai curând."

RULES: list[_Rule] = [
    # ─── Cardiovascular emergencies ─────────────────────────────────
    _Rule(
        name="chest_pain_acs",
        category="cardiac",
        description="Durere în piept cu semne de sindrom coronarian acut",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            # Stem patterns to catch all forms: transpir/transpiratie, iradi/iradiaza,
            # brat/bratul stang, maxilar, umar.
            (r"(durere|dureri).{0,30}piept", r"(transpir|iradi|brat|maxilar|umar|amorteala)"),
            (r"(durere|dureri).{0,30}piept", r"(lipsa aer|sufocare|respiratie)"),
            r"infarct",
            r"angina pectoral",
        ],
    ),
    _Rule(
        name="severe_dyspnea",
        category="respiratory",
        description="Dificultate severă de respirație",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            r"nu pot respira",
            r"sufocare",
            r"ma sufoc",
            (r"lipsa aer", r"(buze albastre|paloare|amorteala)"),
        ],
    ),
    # ─── Stroke / neurological ──────────────────────────────────────
    _Rule(
        name="stroke_face_arm_speech",
        category="neurological",
        description="Posibil accident vascular cerebral (AVC)",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            r"avc",
            r"accident vascular",
            r"paralizie",
            r"amorteala.{0,30}(o jumatate|brat|picior|fata)",
            r"(vorbire neclara|nu pot vorbi|nu mai pot vorbi)",
            r"(gura stramba|colt gura|fata stramba)",
            (r"slabiciune", r"(brat|picior|jumatate)"),
        ],
    ),
    _Rule(
        name="severe_headache_meningitis",
        category="neurological",
        description="Posibilă meningită sau hemoragie cerebrală (durere de cap + semne neurologice)",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            # Meningitis triad: headache + fever + neck stiffness (no severity qualifier needed —
            # any combination of these three is emergent). Allow 0-25 chars between "gat/ceafa"
            # and "intepenit/tepan" so "gatul îmi este înțepenit" matches.
            (r"(durere|dureri|doare).{0,40}cap", r"(rigiditate|(gat\w*|ceafa\w*).{0,25}(intepenit|tepan|rigid))", r"febr"),
            (r"(durere|dureri|doare).{0,40}cap", r"(gat\w*|ceafa\w*).{0,25}(intepenit|tepan|rigid)"),
            (r"durere.{0,30}cap.{0,30}(severa|puternica|cea mai|teribil)", r"(voma|varsaturi|confuz)"),
            r"(cea mai puternica durere|durere de cap teribila)",
            r"meningita",
            r"hemoragie cerebrala",
        ],
    ),
    _Rule(
        name="seizure",
        category="neurological",
        description="Convulsii sau pierdere de cunoștință",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            r"convulsii",
            r"criza epileptica",
            r"epilepsie.{0,20}criza",
            r"pierdere.{0,20}cunostint",
            r"lesin.{0,20}(repetat|prelungit)",
        ],
    ),
    _Rule(
        name="head_injury",
        category="trauma",
        description="Lovitură la cap cu semne de gravitate",
        severity="urgent",
        action_ro=GO_ER,
        patterns=[
            # Stem "lovi" catches lovit/lovitura/lovitul; "cazut" catches căzut/cazatura.
            (r"(lovi|cazut|cazatura|traumatism).{0,30}cap", r"(varsat|varsatur|amnezi|confuz|lesin|lichid|sange)"),
            r"traumatism cranian",
            (r"cap", r"sange.{0,20}(nas|urechi)"),
        ],
    ),
    # ─── Anaphylaxis ────────────────────────────────────────────────
    _Rule(
        name="anaphylaxis",
        category="allergic",
        description="Reacție alergică severă (anafilaxie)",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            r"anafilax",
            (r"umflare", r"(gat|limba|buze|fata)"),
            (r"alerg", r"(lipsa aer|nu pot respira|sufocare|umflare gat)"),
            r"soc anafilactic",
        ],
    ),
    # ─── GI emergencies ─────────────────────────────────────────────
    _Rule(
        name="gi_bleed",
        category="digestive",
        description="Sângerare digestivă",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            # Cover voma/vomit/vomitat/varsat/varsatura — any verb form near "sange"/"sangerare".
            (r"(voma|vomit|varsat|varsatur).{0,15}sange",),
            r"hematemez",
            r"melena",
            r"scaun negru",
            (r"(scaun|diaree)", r"(sange|hemoragi)"),
        ],
    ),
    _Rule(
        name="acute_abdomen",
        category="digestive",
        description="Abdomen acut chirurgical",
        severity="urgent",
        action_ro=GO_ER,
        patterns=[
            (r"durere abdomin.{0,20}severa", r"(rigid|nu pot atinge|lemnos)"),
            r"abdomen acut",
            (r"durere", r"(apendicita|peritonit)"),
        ],
    ),
    _Rule(
        name="severe_dehydration",
        category="digestive",
        description="Diaree severă cu semne de deshidratare",
        severity="urgent",
        action_ro=GO_ER,
        patterns=[
            (r"diaree", r"(febra mare|peste 38|peste 39|deshidrat|nu mai urinez)"),
            (r"voma", r"(continu|nu pot retine|24 de ore)"),
        ],
    ),
    # ─── Pregnancy ──────────────────────────────────────────────────
    _Rule(
        name="pregnancy_bleeding",
        category="obstetric",
        description="Sângerare în timpul sarcinii",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            (r"insarcinat|sarcin", r"(sange|sangerare|hemoragie)"),
            (r"insarcinat|sarcin", r"(durere abdomin|contractii|lichid amniotic)"),
        ],
    ),
    # ─── Mental health emergency ────────────────────────────────────
    _Rule(
        name="suicidal_ideation",
        category="mental",
        description="Gânduri de auto-vătămare sau suicid",
        severity="emergency",
        action_ro="Sunați 112 sau Telverde 0800 801 200 (TelVerde Antisuicid). Nu sunteți singur(ă).",
        patterns=[
            r"vreau sa.{0,10}mor",
            r"sa.mi pun capat",
            r"gand.{0,15}sinucidere",
            r"sa ma sinucid",
            r"sa.mi fac rau",
        ],
    ),
    # ─── Overdose / poisoning ───────────────────────────────────────
    _Rule(
        name="overdose_poisoning",
        category="toxicology",
        description="Posibilă supradoză sau intoxicație",
        severity="emergency",
        action_ro="Sunați 112 sau Centrul Antitoxic 021 318 36 06 imediat.",
        patterns=[
            r"supradoz",
            r"am luat prea mult",
            r"prea multe pastile",
            r"intoxica",
            r"otrav",
        ],
    ),
    # ─── Pediatric flags (kids) ─────────────────────────────────────
    _Rule(
        name="pediatric_high_fever",
        category="pediatric",
        description="Febră înaltă la sugar",
        severity="urgent",
        action_ro=GO_ER,
        patterns=[
            (r"(bebelus|sugar|copil sub 3 luni|nou.nascut)", r"(febra|temperatura)"),
        ],
    ),
    _Rule(
        name="pediatric_dehydration",
        category="pediatric",
        description="Semne de deshidratare la copil",
        severity="urgent",
        action_ro=GO_ER,
        patterns=[
            (r"copil|bebelus|sugar", r"(nu mai urinez|fontanel|adormit greu|piele uscata)"),
        ],
    ),
    # ─── Other ─────────────────────────────────────────────────────
    _Rule(
        name="severe_burn",
        category="trauma",
        description="Arsură severă",
        severity="urgent",
        action_ro=GO_ER,
        patterns=[
            r"arsura.{0,20}(grad 3|adanc|fata|maini|electric|chimic)",
            r"electrocut",
        ],
    ),
    _Rule(
        name="loss_of_vision",
        category="ophthalmologic",
        description="Pierdere bruscă de vedere",
        severity="emergency",
        action_ro=CALL_112,
        patterns=[
            r"nu mai vad",
            r"pierdere.{0,20}vedere",
            r"orbire brusca",
        ],
    ),
]


def _fold(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _match_one(pattern, folded_text: str) -> str | None:
    """Return the first matching substring, or None if no match."""
    if isinstance(pattern, tuple):
        # All sub-patterns must match somewhere
        snippets = []
        for sub in pattern:
            m = re.search(sub, folded_text, flags=re.IGNORECASE)
            if not m:
                return None
            snippets.append(m.group(0))
        return " + ".join(snippets)
    m = re.search(pattern, folded_text, flags=re.IGNORECASE)
    return m.group(0) if m else None


def scan(text: str) -> list[RedFlag]:
    """Run every red-flag rule against the user's text. Return all matches."""
    if not text:
        return []
    folded = _fold(text)
    out: list[RedFlag] = []
    for rule in RULES:
        for pattern in rule.patterns:
            snippet = _match_one(pattern, folded)
            if snippet is not None:
                out.append(RedFlag(
                    name=rule.name,
                    category=rule.category,
                    description=rule.description,
                    severity=rule.severity,
                    action_ro=rule.action_ro,
                    matched_pattern=snippet,
                ))
                break  # one match per rule is enough
    return out


def has_emergency(flags: list[RedFlag]) -> bool:
    return any(f.severity == "emergency" for f in flags)


def has_urgent(flags: list[RedFlag]) -> bool:
    return any(f.severity == "urgent" for f in flags)
