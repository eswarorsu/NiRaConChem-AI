"""Alignment tests for the structured answer layer.

These assert the guardrails hold regardless of what the model returns, so run them
without any API key configured too - the deterministic fallback must satisfy the
same contract.

    python -m tests.test_alignment        (from backend/)
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.answer_schema import (  # noqa: E402
    RetrievalQuality,
    SourceRef,
    fallback_answer,
    render_answer,
    validate_answer,
)

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((PASS if condition else FAIL, name, detail))


SOURCES = [
    SourceRef("P1", "Sikagard-1816 (Sika)", "profile", "Sikagard-1816", "https://example/1816"),
    SourceRef("C1", "Sikagard-1816 (Sika PDS) chunk 1", "chunk", "Sikagard-1816", None),
]
STRONG = RetrievalQuality(profile_count=5, chunk_count=5, top_profile_score=2.9, top_chunk_score=1.2)
WEAK = RetrievalQuality(profile_count=1, chunk_count=1, top_profile_score=0.4, top_chunk_score=0.2)
NONE = RetrievalQuality()


# 1. Invented citation ids are stripped and the product is dropped with them.
answer = validate_answer(
    {
        "answer_type": "recommendation",
        "summary": "Use Sikagard-1816.",
        "confidence": "high",
        "products": [
            {"name": "Sikagard-1816", "citations": ["P1"]},
            {"name": "TotallyMadeUp-900", "citations": ["P9", "C7"]},
        ],
        "claims": [],
    },
    SOURCES,
    STRONG,
    context_text="epoxy polysulfide potable water tank",
)
check("invented citation ids are dropped", answer.validation["invalid_citation_ids_dropped"] == 2,
      str(answer.validation))
check("uncitable product is not recommended",
      [p.name for p in answer.products] == ["Sikagard-1816"],
      str([p.name for p in answer.products]))

# 2. Uncited claims are quarantined, never presented as fact.
answer = validate_answer(
    {
        "answer_type": "recommendation",
        "summary": "s",
        "confidence": "high",
        "products": [{"name": "Sikagard-1816", "citations": ["P1"]}],
        "claims": [
            {"statement": "Pot life is 30 minutes at 25 C.", "citations": []},
            {"statement": "Developed for potable water tanks.", "citations": ["C1"]},
        ],
    },
    SOURCES,
    STRONG,
    context_text="epoxy potable water",
)
check("uncited claim is removed from claims",
      [c.statement for c in answer.claims] == ["Developed for potable water tanks."],
      str([c.statement for c in answer.claims]))
check("uncited claim is surfaced as unverified", len(answer.unverified) == 1, str(answer.unverified))
check("uncited claim never reaches the rendered reply",
      "Pot life is 30 minutes" not in render_answer(answer))

# 3. Confidence is capped by retrieval strength, not self-reported.
answer = validate_answer(
    {"answer_type": "recommendation", "summary": "s", "confidence": "high",
     "products": [{"name": "Sikagard-1816", "citations": ["P1"]}], "claims": []},
    SOURCES,
    WEAK,
    context_text="epoxy",
)
check("weak retrieval caps a 'high' claim to 'low'", answer.confidence == "low", answer.confidence)
check("the cap is explained", "capped" in answer.confidence_reason, answer.confidence_reason)

answer = validate_answer(
    {"answer_type": "recommendation", "summary": "s", "confidence": "high",
     "products": [{"name": "Sikagard-1816", "citations": ["P1"]}], "claims": [],
     "confidence_reason": "strong match"},
    SOURCES,
    STRONG,
    context_text="epoxy",
)
check("strong retrieval allows 'high'", answer.confidence == "high", answer.confidence)

# 4. No retrieval means abstain, not improvise.
answer = validate_answer(
    {"answer_type": "recommendation", "summary": "Use anything.", "confidence": "high",
     "products": [{"name": "Whatever", "citations": ["P1"]}], "claims": []},
    [],
    NONE,
)
check("no evidence forces insufficient_evidence", answer.answer_type == "insufficient_evidence",
      answer.answer_type)
check("no evidence yields no products", answer.products == [])

# 5. Safety notes are attached deterministically by chemistry.
answer = validate_answer(
    {"answer_type": "recommendation", "summary": "s", "confidence": "medium",
     "products": [{"name": "Sikadur-31 CF", "citations": ["P1"]}], "claims": [], "precautions": []},
    SOURCES,
    STRONG,
    context_text="two part epoxy resin for potable water tanks",
)
joined = " ".join(answer.precautions).lower()
check("epoxy recommendation carries handling guidance", "epoxy" in joined, joined[:120])
check("potable-water contact is flagged", "potable" in joined, joined[:200])
check("safety guidance is labelled as non-datasheet",
      any("not quoted from the datasheet" in note for note in answer.precautions))

# 6. Garbage in still produces a valid object.
answer = validate_answer({}, SOURCES, STRONG)
check("empty payload still validates", answer.confidence in {"low", "medium", "high"})
check("empty payload renders without error", isinstance(render_answer(answer), str))

# 7. The LLM-free fallback satisfies the same contract.
profiles = [
    {"product_name": "Sikagard-1816", "manufacturer": "Sika", "system_type": "Concrete protective coating system",
     "usage": "Internal protection of potable water tanks", "tagline": "NON-TOXIC COATING", "category": "coating"},
]
answer = fallback_answer("potable water tank coating", SOURCES, STRONG, profiles, "epoxy potable water")
check("fallback produces a cited product",
      bool(answer.products) and bool(answer.products[0].citations), str(answer.as_dict())[:200])
check("fallback confidence stays low", answer.confidence == "low", answer.confidence)
check("fallback renders", "Sikagard-1816" in render_answer(answer))

failures = [r for r in results if r[0] == FAIL]
width = max(len(name) for _, name, _ in results)
for status, name, detail in results:
    print(f"{status}  {name:<{width}}  {detail if status == FAIL else ''}".rstrip())
print(f"\n{len(results) - len(failures)}/{len(results)} alignment checks passed")
sys.exit(1 if failures else 0)
