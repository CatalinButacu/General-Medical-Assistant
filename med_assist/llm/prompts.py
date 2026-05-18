"""Prompt assembly via a Jinja2 template registry.

The chatbot has three system-prompt families:

  • followup.ro.j2                  — gather one more piece of info from the user
  • recommend.ro.j2 / recommend_low_confidence.ro.j2
                                    — recommend an OTC medicine, or refuse if retrieval is weak
  • explain_medicine.ro.j2          — explain a medicine the user named (no symptom triage)

Each template is paired with a Pydantic context model — missing variables
raise at render time (Jinja2 ``StrictUndefined``) instead of producing a
malformed prompt the LLM would then "creatively" interpret. The render
functions exposed at the bottom of this module are the only public
entry-points; callers never touch raw template names.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field

from med_assist.data.models import Medicine, MedicineHit
from med_assist.profile import UserProfile

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptRegistry:
    """Loads templates once, renders many times.

    Templates are addressed by filename so adding a new conversation
    phase is a matter of dropping a `.j2` file and wiring a context
    model — no Python prompt-string refactoring required.
    """

    def __init__(self, templates_dir: Path = _TEMPLATES_DIR):
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=False,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

    def render(self, template_name: str, context: BaseModel) -> str:
        tmpl = self._env.get_template(template_name)
        fields = {name: getattr(context, name) for name in type(context).model_fields}
        return tmpl.render(**fields)


# ---------- profile rendering ----------------------------------------------

def format_profile_block(profile: Optional[UserProfile]) -> str:
    """Render the user profile as a compact 'already-known' Romanian block.

    Kept as Python (not Jinja) because the formatting rules are noisy and
    Jinja-side conditionals would harm readability of the templates.
    """
    if profile is None or not profile.has_meaningful_data():
        return ""
    lines: list[str] = []
    if profile.age:
        lines.append(f"- Vârstă: {profile.age}")
    if profile.gender or profile.isPregnant:
        gender_ro = {
            "male": "masculin", "female": "feminin", "other": "altul",
        }.get(profile.gender or "", profile.gender or "")
        bits = [gender_ro] if gender_ro else []
        if profile.isPregnant:
            bits.append("gravidă: DA")
        if bits:
            lines.append(f"- Gen: {', '.join(bits)}")
    if profile.allergies:
        lines.append(f"- Alergii: {', '.join(profile.allergies)}")
    if profile.conditions:
        lines.append(f"- Condiții cronice: {', '.join(profile.conditions)}")
    if profile.medications:
        lines.append(f"- Medicamente curente: {', '.join(profile.medications)}")
    if not lines:
        return ""
    return (
        "PROFIL UTILIZATOR (deja cunoscut — NU întreba din nou aceste lucruri):\n"
        + "\n".join(lines)
    )


def retrieval_hint_from_hits(hits: list[MedicineHit]) -> str:
    """Compact category summary used to nudge the followup LLM."""
    if not hits:
        return ""
    cats: list[str] = []
    seen: set[str] = set()
    for h in hits[:5]:
        cat = (h.medicine.category or "").strip()
        if cat and cat not in seen:
            seen.add(cat)
            cats.append(cat)
    return ", ".join(cats)


# ---------- context models -------------------------------------------------

class FollowupContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    profile_block: str = ""
    user_history_text: list[str] = Field(default_factory=list)
    retrieval_hint: str = ""
    forced_topic: Optional[str] = None


class RecommendContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    profile_block: str = ""
    hits: list[dict[str, Any]] = Field(default_factory=list)


class LowConfidenceContext(BaseModel):
    profile_block: str = ""


class ExplainContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    profile_block: str = ""
    medicine: Medicine
    rx_label: str
    indications: str = ""
    contraindications: str = ""


# ---------- helpers --------------------------------------------------------

def _rx_label(rx_status: str) -> str:
    return {
        "OTC": "fără prescripție (OTC)",
        "MIXED": "parțial fără prescripție",
        "RX": "doar cu prescripție medicală (RX)",
        "RESTRICTED": "eliberare restricționată",
        "UNKNOWN": "status necunoscut",
    }.get(rx_status, rx_status)


def _hit_for_template(hit: MedicineHit) -> dict[str, Any]:
    med = hit.medicine
    rx = "OTC" if med.rx_status in ("OTC", "MIXED") else med.rx_status
    symptoms = ", ".join(med.lay_symptoms[:4]) if med.lay_symptoms else "—"
    return {
        "trade_name": med.trade_name,
        "dci": med.dci,
        "atc_code": med.atc_code,
        "category": med.category,
        "rx_label": rx,
        "lay_symptoms_joined": symptoms,
    }


# ---------- module-level registry (one instance is plenty) -----------------

_DEFAULT_REGISTRY: Optional[PromptRegistry] = None


def default_registry() -> PromptRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = PromptRegistry()
    return _DEFAULT_REGISTRY


# ---------- public render entry-points -------------------------------------

def render_followup(
    *,
    user_history_text: list[str],
    profile: Optional[UserProfile],
    retrieval_hint: str = "",
    forced_topic: Optional[str] = None,
    registry: Optional[PromptRegistry] = None,
) -> str:
    reg = registry or default_registry()
    ctx = FollowupContext(
        profile_block=format_profile_block(profile),
        user_history_text=list(user_history_text),
        retrieval_hint=retrieval_hint,
        forced_topic=forced_topic,
    )
    return reg.render("followup.ro.j2", ctx)


def render_recommend(
    *,
    hits: list[MedicineHit],
    profile: Optional[UserProfile],
    forced_low_confidence: bool = False,
    registry: Optional[PromptRegistry] = None,
) -> str:
    reg = registry or default_registry()
    profile_block = format_profile_block(profile)
    if forced_low_confidence or not hits:
        return reg.render(
            "recommend_low_confidence.ro.j2",
            LowConfidenceContext(profile_block=profile_block),
        )
    ctx = RecommendContext(
        profile_block=profile_block,
        hits=[_hit_for_template(h) for h in hits],
    )
    return reg.render("recommend.ro.j2", ctx)


def render_explain(
    *,
    medicine: Medicine,
    profile: Optional[UserProfile],
    registry: Optional[PromptRegistry] = None,
) -> str:
    reg = registry or default_registry()
    sections = medicine.rcp_sections or {}
    ctx = ExplainContext(
        profile_block=format_profile_block(profile),
        medicine=medicine,
        rx_label=_rx_label(medicine.rx_status),
        indications=(sections.get("indications", "") or "").strip(),
        contraindications=(sections.get("contraindications", "") or "").strip(),
    )
    return reg.render("explain_medicine.ro.j2", ctx)
