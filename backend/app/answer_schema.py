"""
answer_schema.py
----------------
The structured answer contract for the grounded agent nodes, plus the alignment
layer that enforces it.

Why this exists: the agent used to return free prose. Nothing checked whether a
recommended product actually appeared in the retrieved context, whether a technical
claim came from anywhere, or whether the model was confident because the retrieval
was good or merely because it was fluent. This module makes the answer a validated
object first and prose second.

Three guardrails are enforced here, not in the prompt (a prompt is a request; this
is a check):

  1. PER-CLAIM CITATIONS - every product and every claim must cite a source id that
     was actually placed in the context. Unknown ids are stripped; anything left
     with no valid citation is quarantined into `unverified`, never presented as
     established fact.
  2. CONFIDENCE + ABSTAIN - confidence is CAPPED by measured retrieval quality, so
     the model cannot talk itself into "high". With no usable retrieval the answer
     becomes an explicit abstention.
  3. SCOPE + SAFETY - out-of-domain questions are answered as out-of-scope rather
     than improvised, and products whose chemistry warrants it always carry handling
     precautions, clearly labelled as standard practice rather than datasheet text.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

AnswerType = Literal["recommendation", "knowledge", "out_of_scope", "insufficient_evidence"]
Confidence = Literal["high", "medium", "low"]

CONFIDENCE_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
CONFIDENCE_BY_RANK = ["low", "medium", "high"]

# Chemistry families whose handling guidance is not optional. Matched against the
# recommended product names and the context text.
SAFETY_RULES: list[tuple[tuple[str, ...], str]] = [
    (
        ("epoxy", "sikadur", "sikagard", "sikafloor-2", "epocem"),
        "Epoxy systems: skin and respiratory sensitiser. Nitrile gloves, goggles and "
        "coveralls; forced ventilation in tanks, pits and other confined spaces.",
    ),
    (
        ("polyurethane", "isocyanate", "sikalastic", "sikafloor-4", "pu ", "sikaflex"),
        "Polyurethane / isocyanate systems: use respiratory protection when spraying, "
        "keep uncured material away from moisture, and ventilate enclosed areas.",
    ),
    (
        ("solvent", "primer-3", "thinner", "cleaner"),
        "Solvent-borne product: flammable. Remove ignition sources, ventilate, and "
        "avoid vapour build-up in enclosed areas.",
    ),
    (
        ("cement", "mortar", "grout", "monotop", "sikatop", "screed"),
        "Cementitious product: highly alkaline when wet. Avoid skin contact, wear eye "
        "protection, and control silica dust when cutting or grinding.",
    ),
    (
        ("potable", "drinking water", "food"),
        "Potable-water contact: confirm the product's potable-water approval and the "
        "full cure and flushing regime before the tank is returned to service.",
    ),
]

SAFETY_DISCLAIMER = (
    "Standard handling guidance, not quoted from the datasheet - always follow the "
    "product SDS and the project HSE plan."
)


@dataclass
class SourceRef:
    """One citable item placed in the model's context."""

    source_id: str
    label: str
    kind: Literal["profile", "chunk"]
    product_name: str = ""
    url: str | None = None


@dataclass
class RetrievalQuality:
    """Measured strength of the retrieval behind an answer. Drives the confidence cap."""

    profile_count: int = 0
    chunk_count: int = 0
    top_profile_score: float = 0.0
    top_chunk_score: float = 0.0

    @property
    def has_evidence(self) -> bool:
        return self.profile_count > 0 or self.chunk_count > 0

    def confidence_cap(self) -> Confidence:
        """Ceiling the model's self-reported confidence cannot exceed.

        Thresholds are read off the retrieval scores the benchmark produces: a strong
        profile match lands well above 1.5 and a strong chunk above 0.8, while a
        near-miss sits under half of that.
        """
        if not self.has_evidence:
            return "low"
        strong_profile = self.top_profile_score >= 1.5 and self.profile_count >= 2
        strong_chunk = self.top_chunk_score >= 0.8 and self.chunk_count >= 2
        if strong_profile and strong_chunk:
            return "high"
        if strong_profile or strong_chunk:
            return "medium"
        return "low"

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_count": self.profile_count,
            "chunk_count": self.chunk_count,
            "top_profile_score": round(self.top_profile_score, 4),
            "top_chunk_score": round(self.top_chunk_score, 4),
            "confidence_cap": self.confidence_cap(),
        }


@dataclass
class ProductPick:
    name: str
    role: str = "primary"
    manufacturer: str = ""
    why: str = ""
    citations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "manufacturer": self.manufacturer,
            "why": self.why,
            "citations": self.citations,
        }


@dataclass
class Claim:
    statement: str
    citations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"statement": self.statement, "citations": self.citations}


@dataclass
class StructuredAnswer:
    answer_type: AnswerType = "knowledge"
    summary: str = ""
    confidence: Confidence = "low"
    confidence_reason: str = ""
    recommended_system: str | None = None
    products: list[ProductPick] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    application_notes: list[str] = field(default_factory=list)
    precautions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    follow_up: str | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    retrieval: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer_type": self.answer_type,
            "summary": self.summary,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "recommended_system": self.recommended_system,
            "products": [p.as_dict() for p in self.products],
            "claims": [c.as_dict() for c in self.claims],
            "application_steps": self.application_notes,
            "application_notes": self.application_notes,
            "precautions": self.precautions,
            "missing_information": self.missing_information,
            "unverified": self.unverified,
            "follow_up": self.follow_up,
            "citations": self.citations,
            "retrieval": self.retrieval,
            "validation": self.validation,
        }


# --------------------------------------------------------------------------- #
# Prompting
# --------------------------------------------------------------------------- #
SCHEMA_INSTRUCTIONS = """Return ONLY a JSON object with exactly these keys:

{
  "answer_type": "recommendation" | "knowledge" | "out_of_scope",
  "summary": "1-3 sentences answering the user directly. No preamble.",
  "confidence": "high" | "medium" | "low",
  "confidence_reason": "one short sentence on why",
  "recommended_system": "the system/family name, or null",
  "products": [
    {"name": "...", "role": "primer|membrane|topcoat|standalone|alternative",
     "manufacturer": "...", "why": "one sentence", "citations": ["P1", "C2"]}
  ],
  "claims": [
    {"statement": "one technical fact", "citations": ["C1"]}
  ],
  "application_steps": ["ordered steps, one action each, in the order carried out"],
  "precautions": ["handling / HSE points"],
  "missing_information": ["project details that would change the answer"],
  "follow_up": "one short question, or null"
}

Rules you must follow:
- Cite using ONLY the source ids shown in the context (P1, P2, C1, C2, ...). Never
  invent an id. Every product and every claim needs at least one id.
- Put a fact in "claims" only if a cited source states it. If you know something
  useful that the sources do not state, leave it out - do not put it in claims.
- Never state a numeric datasheet value (pot life, coverage, strength, temperature,
  cure time) unless it appears in a cited source.
- "application_steps" must be a SEQUENCE: step 1 first, each entry one action, in
  the order it is carried out on site (prepare, prime, apply, cure, protect). One
  short imperative sentence per step. No bullets, no numbering inside the strings.
- If the sources do not answer the question, set answer_type to "out_of_scope" or
  return an empty products list and say so in "summary".
- No markdown, no code fences, no text outside the JSON object."""


def build_system_prompt(brand: str, mode: Literal["recommendation", "knowledge"]) -> str:
    intent = (
        "recommend the right product system for the user's situation"
        if mode == "recommendation"
        else "answer the user's technical question"
    )
    return (
        f"You are {brand}, a senior construction chemicals consultant for UAE/GCC projects. "
        f"Your job is to {intent}, grounded strictly in the supplied product data.\n\n"
        f"{SCHEMA_INSTRUCTIONS}"
    )


# --------------------------------------------------------------------------- #
# Parsing and validation
# --------------------------------------------------------------------------- #
def extract_json(raw: str) -> dict[str, Any] | None:
    """Pull a JSON object out of a model reply, tolerating fences and stray prose."""
    if not raw:
        return None
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _as_str(value: Any, limit: int = 600) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item) for item in value)
    return " ".join(str(value).split())[:limit]


def _as_str_list(value: Any, limit: int = 8) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    out = [_as_str(item, 400) for item in value]
    return [item for item in out if item][:limit]


def _clean_citations(value: Any, allowed: set[str]) -> tuple[list[str], int]:
    """Keep only ids that were really in the context. Returns (kept, dropped_count)."""
    raw = _as_str_list(value, limit=12)
    kept: list[str] = []
    dropped = 0
    for item in raw:
        token = item.strip().strip("[](),.").upper()
        if token in allowed:
            if token not in kept:
                kept.append(token)
        else:
            dropped += 1
    return kept, dropped


def scoped_context(product_names: list[str], context_text: str) -> str:
    """Narrow the context to the blocks describing the recommended products.

    Safety guidance must follow the products actually recommended. Scanning the whole
    context makes every answer inherit the chemistry of everything retrieved, so an
    epoxy warning shows up on a PVC waterbar recommendation.
    """
    if not product_names or not context_text:
        return ""
    needles = [name.lower() for name in product_names if name]
    blocks = re.split(r"\n(?=\[[PC]\d+\])", context_text)
    kept = [block for block in blocks if any(needle in block.lower() for needle in needles)]
    # If nothing scopes cleanly, fall back to the full context. On safety guidance,
    # over-warning is the correct failure direction.
    return "\n".join(kept) if kept else context_text


def safety_notes(product_names: list[str], context_text: str) -> list[str]:
    """Deterministic handling guidance driven by product chemistry.

    Generated here rather than left to the model so a recommendation can never ship
    without the precaution that its chemistry requires.
    """
    scoped = scoped_context(product_names, context_text)
    haystack = " ".join(product_names).lower() + " " + (scoped or "").lower()
    notes = [note for needles, note in SAFETY_RULES if any(needle in haystack for needle in needles)]
    return notes[:3]


def validate_answer(
    payload: dict[str, Any],
    sources: list[SourceRef],
    quality: RetrievalQuality,
    context_text: str = "",
    mode: Literal["recommendation", "knowledge"] = "recommendation",
) -> StructuredAnswer:
    """Turn a raw model payload into a validated answer, enforcing the guardrails."""
    allowed = {source.source_id.upper() for source in sources}
    by_id = {source.source_id.upper(): source for source in sources}

    answer = StructuredAnswer()
    answer.retrieval = quality.as_dict()

    raw_type = _as_str(payload.get("answer_type"), 40).lower()
    if raw_type not in {"recommendation", "knowledge", "out_of_scope"}:
        raw_type = "recommendation" if mode == "recommendation" else "knowledge"
    answer.answer_type = raw_type  # type: ignore[assignment]

    answer.summary = _as_str(payload.get("summary"), 900)
    answer.recommended_system = _as_str(payload.get("recommended_system"), 200) or None
    answer.application_notes = _as_str_list(
        payload.get("application_steps") or payload.get("application_notes"), limit=10
    )
    answer.missing_information = _as_str_list(payload.get("missing_information"), limit=6)
    answer.follow_up = _as_str(payload.get("follow_up"), 300) or None
    answer.confidence_reason = _as_str(payload.get("confidence_reason"), 300)

    dropped_ids = 0
    uncited: list[str] = []

    # --- products -----------------------------------------------------------
    for item in payload.get("products") or []:
        if not isinstance(item, dict):
            continue
        name = _as_str(item.get("name"), 160)
        if not name:
            continue
        citations, dropped = _clean_citations(item.get("citations"), allowed)
        dropped_ids += dropped
        pick = ProductPick(
            name=name,
            role=_as_str(item.get("role"), 40) or "primary",
            manufacturer=_as_str(item.get("manufacturer"), 80),
            why=_as_str(item.get("why"), 400),
            citations=citations,
        )
        if citations:
            answer.products.append(pick)
        else:
            # Guardrail 1: a product nobody can trace does not get recommended.
            uncited.append(f"product '{name}' was dropped - no valid source citation")

    # --- claims -------------------------------------------------------------
    for item in payload.get("claims") or []:
        if isinstance(item, str):
            item = {"statement": item, "citations": []}
        if not isinstance(item, dict):
            continue
        statement = _as_str(item.get("statement"), 500)
        if not statement:
            continue
        citations, dropped = _clean_citations(item.get("citations"), allowed)
        dropped_ids += dropped
        if citations:
            answer.claims.append(Claim(statement=statement, citations=citations))
        else:
            uncited.append(statement)

    answer.unverified = uncited[:6]

    # --- guardrail 3: safety ------------------------------------------------
    model_precautions = _as_str_list(payload.get("precautions"), limit=6)
    required = safety_notes([p.name for p in answer.products], context_text)
    merged = list(model_precautions)
    for note in required:
        head = note.split(":", 1)[0].lower()
        if not any(head in existing.lower() for existing in merged):
            merged.append(note)
    if merged:
        merged.append(SAFETY_DISCLAIMER)
    answer.precautions = merged[:7]

    # --- guardrail 2: confidence cap and abstain ----------------------------
    claimed = _as_str(payload.get("confidence"), 20).lower()
    if claimed not in CONFIDENCE_ORDER:
        claimed = "medium"
    cap = quality.confidence_cap()
    capped = CONFIDENCE_ORDER[claimed] > CONFIDENCE_ORDER[cap]
    effective = cap if capped else claimed

    # Losing citations is itself evidence the answer is weaker than it looks.
    if answer.unverified and CONFIDENCE_ORDER[effective] > 0:
        effective = CONFIDENCE_BY_RANK[CONFIDENCE_ORDER[effective] - 1]
    if answer.answer_type == "recommendation" and not answer.products:
        effective = "low"

    answer.confidence = effective  # type: ignore[assignment]
    reasons = []
    if answer.confidence_reason:
        reasons.append(answer.confidence_reason)
    if capped:
        reasons.append(f"capped at '{cap}' by retrieval strength")
    if answer.unverified:
        reasons.append(f"{len(answer.unverified)} uncited statement(s) removed")
    answer.confidence_reason = "; ".join(reasons)[:400]

    # "out_of_scope" means the question is not ours to answer. When we DID retrieve
    # relevant products but the specific fact is missing, the honest label is that the
    # evidence is insufficient, not that the topic is off-limits.
    if answer.answer_type == "out_of_scope" and quality.has_evidence:
        answer.answer_type = "insufficient_evidence"

    if not quality.has_evidence:
        answer.answer_type = "insufficient_evidence"
        answer.products = []
        answer.claims = []
        answer.confidence = "low"
        if not answer.summary:
            answer.summary = (
                "Nothing in the indexed product catalog matches this question closely enough "
                "for me to recommend a specific system."
            )

    answer.citations = [
        {
            "id": by_id[cid].source_id,
            "label": by_id[cid].label,
            "kind": by_id[cid].kind,
            "product": by_id[cid].product_name,
            "url": by_id[cid].url,
        }
        for cid in sorted(
            {c for p in answer.products for c in p.citations} | {c for cl in answer.claims for c in cl.citations}
        )
        if cid in by_id
    ]
    answer.validation = {
        "invalid_citation_ids_dropped": dropped_ids,
        "uncited_statements_removed": len(answer.unverified),
        "confidence_capped": capped,
        "sources_offered": len(sources),
        "sources_cited": len(answer.citations),
    }
    return answer


# --------------------------------------------------------------------------- #
# Deterministic fallback and rendering
# --------------------------------------------------------------------------- #
def fallback_answer(
    question: str,
    sources: list[SourceRef],
    quality: RetrievalQuality,
    profiles: list[dict[str, Any]],
    context_text: str = "",
    mode: Literal["recommendation", "knowledge"] = "recommendation",
) -> StructuredAnswer:
    """Structured answer built without an LLM.

    Used when no model is reachable or the model returned unusable JSON, so the API
    contract holds even with no API key configured.
    """
    profile_sources = [s for s in sources if s.kind == "profile"]
    payload: dict[str, Any] = {
        "answer_type": mode,
        "summary": "",
        "confidence": "low",
        "confidence_reason": "assembled directly from retrieval without a language model",
        "products": [],
        "claims": [],
        "application_steps": [],
        "precautions": [],
        "missing_information": [],
    }

    if profiles and profile_sources:
        top = profiles[0]
        name = str(top.get("product_name") or "").strip()
        payload["recommended_system"] = top.get("system_type")
        payload["summary"] = (
            f"Closest match in the catalog for \"{question.strip()}\" is {name}"
            + (f" ({top.get('manufacturer')})" if top.get("manufacturer") else "")
            + f", a {top.get('system_type') or top.get('category')}."
        )
        for profile, source in zip(profiles[:3], profile_sources[:3]):
            payload["products"].append(
                {
                    "name": profile.get("product_name"),
                    "role": "primary" if profile is profiles[0] else "alternative",
                    "manufacturer": profile.get("manufacturer"),
                    "why": profile.get("tagline") or profile.get("system_type") or "",
                    "citations": [source.source_id],
                }
            )
            usage = str(profile.get("usage") or "").strip()
            if usage:
                payload["claims"].append(
                    {"statement": f"{profile.get('product_name')} is specified for: {usage[:300]}",
                     "citations": [source.source_id]}
                )
    else:
        payload["summary"] = (
            "I could not match this to a product in the indexed catalog. Tell me the substrate, "
            "the exposure and where on the structure it is, and I will narrow it down."
        )
    return validate_answer(payload, sources, quality, context_text=context_text, mode=mode)


def render_answer(answer: StructuredAnswer) -> str:
    """Markdown rendering of the object, so existing chat UIs keep working."""
    lines: list[str] = []
    if answer.summary:
        lines.append(answer.summary)

    if answer.products:
        lines.append("")
        lines.append("**Recommended**" + (f" - {answer.recommended_system}" if answer.recommended_system else ""))
        for product in answer.products:
            bits = [f"**{product.name}**"]
            if product.manufacturer:
                bits.append(f"({product.manufacturer})")
            if product.role and product.role != "primary":
                bits.append(f"- {product.role}")
            line = "- " + " ".join(bits)
            if product.why:
                line += f" - {product.why}"
            if product.citations:
                line += f" [{', '.join(product.citations)}]"
            lines.append(line)

    if answer.claims:
        lines.append("")
        lines.append("**From the datasheets**")
        for claim in answer.claims:
            lines.append(f"- {claim.statement} [{', '.join(claim.citations)}]")

    if answer.application_notes:
        lines.append("")
        lines.append("**Application steps**")
        lines.extend(f"{index}. {note}" for index, note in enumerate(answer.application_notes, start=1))

    if answer.precautions:
        lines.append("")
        lines.append("**Precautions**")
        lines.extend(f"- {note}" for note in answer.precautions)

    if answer.missing_information:
        lines.append("")
        lines.append("**To firm this up I need**")
        lines.extend(f"- {item}" for item in answer.missing_information)

    if answer.unverified:
        lines.append("")
        lines.append(
            "*Not shown: "
            + str(len(answer.unverified))
            + " statement(s) I could not trace to a datasheet in the index.*"
        )

    lines.append("")
    confidence_line = f"*Confidence: {answer.confidence}*"
    if answer.confidence_reason:
        confidence_line = f"*Confidence: {answer.confidence} - {answer.confidence_reason}*"
    lines.append(confidence_line)

    if answer.citations:
        labels = ", ".join(f"{c['id']} {c['label']}" for c in answer.citations)
        lines.append(f"*Sources: {labels}*")

    if answer.follow_up:
        lines.append("")
        lines.append(answer.follow_up)

    return "\n".join(lines).strip()
