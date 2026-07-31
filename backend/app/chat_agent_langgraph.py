from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from typing import Any, Literal, TypedDict

from groq import Groq
from langgraph.graph import END, START, StateGraph

from app.agent_prompt import NIRACONCHEM_AGENT_SYSTEM_PROMPT
from app.rag_store import (
    load_product_profiles,
    rag_source_labels,
    retrieve_product_profiles,
    retrieve_rag_chunks,
)

BRAND_NAME = "NIRACONCHEM AI"
FOUNDER_NAME = "Sravani Uppu"

FOUNDER_REPLY = (
    f"{BRAND_NAME} was founded by {FOUNDER_NAME}, a construction chemicals "
    "specification specialist with 10 years of hands-on industry experience."
)

GREETING_REPLY = (
    f"Hi, I am {BRAND_NAME}. Tell me the construction chemical problem first, "
    "and I will collect the project details needed for an accurate recommendation "
    "and PDF technical report."
)

VOCAB: dict[str, int] = {
    "waterproofing": 3,
    "waterproof": 3,
    "epoxy": 3,
    "polyurethane": 3,
    "pu coating": 3,
    "cementitious": 3,
    "crystalline": 3,
    "admixture": 3,
    "grout": 3,
    "screed": 3,
    "sealant": 3,
    "honeycomb": 3,
    "hydrostatic": 3,
    "chloride": 3,
    "corrosion inhibitor": 3,
    "concrete repair": 3,
    "tile adhesive": 3,
    "tile fixing": 3,
    "joint filler": 3,
    "crack injection": 3,
    "basement": 2,
    "terrace": 2,
    "rooftop": 2,
    "wet area": 2,
    "swimming pool": 2,
    "parking": 2,
    "podium": 2,
    "balcony": 2,
    "retaining wall": 2,
    "slab": 2,
    "concrete": 2,
    "blockwork": 2,
    "masonry": 2,
    "substrate": 2,
    "repair": 1,
    "coating": 1,
    "floor": 1,
    "roof": 1,
    "wall": 1,
    "tank": 1,
    "crack": 1,
    "leak": 1,
    "chemical": 1,
    "chemicals": 1,
    "construction": 1,
}

KNOWLEDGE_STARTERS = (
    "what is",
    "what are",
    "explain",
    "define",
    "difference between",
    "how does",
    "how do",
    "why does",
    "why do",
    "tell me about",
    "can you explain",
    "what does",
    "describe",
)

BRAND_TERMS = {"founder", "founded", "owner", "sravani", "uppu", "niraconchem"}
GREETING_TERMS = {"hi", "hello", "hey", "good morning", "good afternoon", "howdy"}

AREA_TERMS = {
    "roof",
    "rooftop",
    "terrace",
    "basement",
    "bathroom",
    "wet area",
    "parking",
    "floor",
    "joint",
    "tank",
    "pool",
    "swimming pool",
    "wall",
    "slab",
    "balcony",
    "podium",
    "retaining wall",
    "corridor",
}
SUBSTRATE_TERMS = {
    "concrete",
    "screed",
    "tile",
    "tiles",
    "metal",
    "steel",
    "block",
    "blockwork",
    "masonry",
    "plaster",
    "brick",
    "stone",
}
EXPOSURE_TERMS = {
    "uv",
    "heat",
    "traffic",
    "chemical exposure",
    "chemical resistant",
    "chemicals exposure",
    "chloride",
    "coastal",
    "water",
    "pressure",
    "hydrostatic",
    "potable",
    "external",
    "exterior",
    "interior",
    "freeze",
    "thermal",
    "abrasion",
}
LOCATION_TERMS = {
    "dubai",
    "abu dhabi",
    "sharjah",
    "ajman",
    "rak",
    "ras al khaimah",
    "fujairah",
    "umm al quwain",
    "al ain",
    "uae",
    "gcc",
    "oman",
    "qatar",
    "kuwait",
    "bahrain",
    "saudi",
    "saudi arabia",
    "india",
    "mumbai",
    "bangalore",
    "chennai",
    "delhi",
    "hyderabad",
}
REQUIREMENT_TERMS = {
    "waterproof",
    "waterproofing",
    "water proof",
    "water proofing",
    "repair",
    "coating",
    "flooring",
    "sealant",
    "joint",
    "tile adhesive",
    "tile fixing",
    "tiling",
    "tile installation",
    "grout",
    "leak",
    "crack",
    "honeycomb",
    "corrosion",
    "protection",
    "concrete repair",
    "crack injection",
    "epoxy flooring",
    "pu coating",
    "cementitious",
    "crystalline",
    "admixture",
    "screed",
}

NORMALISE_MAP = {
    "water proofing": "waterproofing",
    "water proof": "waterproof",
    "tailing": "tiling",
    "tails": "tiles",
    "concrate": "concrete",
    "tile fixing": "tile adhesive",
    "tiles fixing": "tile adhesive",
    "fixing tiles": "tile adhesive",
    "fix tiles": "tile adhesive",
    "tiles to fix": "tile adhesive",
    "pu ": "polyurethane ",
    "p.u.": "polyurethane",
    "u.a.e": "uae",
    "r.a.k": "rak",
}

MISSING_LABELS = {
    "problem_requirement": "problem or required system",
    "application_area": "application area",
    "substrate": "substrate",
    "exposure": "exposure condition",
    "location": "project location",
}


class Slots(TypedDict, total=False):
    problem_requirement: str | None
    application_area: str | None
    substrate: str | None
    exposure: str | None
    location: str | None


class AgentState(TypedDict, total=False):
    message: str
    history: list[dict[str, str]]
    context: str
    intent: str
    normalised_text: str
    slots: Slots
    reply: str
    needs_clarification: bool
    questions: list[str]
    sources: list[str]
    rag_context: str | None
    retrieved_profiles: list[dict[str, Any]] | None
    retrieved_chunks: list[dict[str, Any]] | None
    recommendation: dict[str, Any] | None
    report_ready: bool
    report_endpoint: str | None
    report_payload: dict[str, Any] | None
    missing_slots: list[str]


_recommendation_builder: Callable[[str], Any] | None = None


def normalize_text(text: str) -> str:
    out = " ".join(text.strip().split()).lower()
    for source, target in NORMALISE_MAP.items():
        out = out.replace(source, target)
    return out


def has_term(text: str, terms: set[str]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) for term in terms)


def first_term(text: str, terms: set[str]) -> str | None:
    for term in sorted(terms, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text):
            return term
    return None


def construction_score(text: str) -> int:
    return sum(
        weight
        for term, weight in VOCAB.items()
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text)
    )


def history_context(message: str, history: list[dict[str, str]]) -> str:
    user_messages = [
        item.get("content", "")
        for item in history
        if item.get("role") == "user" and item.get("content")
    ]
    user_messages.append(message)
    return " ".join(" ".join(part.strip().split()) for part in user_messages if part)


def extract_slots(text: str) -> Slots:
    normalized = normalize_text(text)
    problem_requirement = first_term(normalized, REQUIREMENT_TERMS)
    substrate = first_term(normalized, SUBSTRATE_TERMS)
    application_area = first_term(normalized, AREA_TERMS)

    if "tile adhesive" in normalized or "tiling" in normalized:
        problem_requirement = "tile adhesive"
        substrate = substrate or "tiles"
    if "flooring" in normalized and "tile adhesive" in normalized:
        application_area = application_area or "floor"

    return Slots(
        problem_requirement=problem_requirement,
        application_area=application_area,
        substrate=substrate,
        exposure=first_term(normalized, EXPOSURE_TERMS),
        location=first_term(normalized, LOCATION_TERMS),
    )


def missing_slot_keys(slots: Slots) -> list[str]:
    keys = ["problem_requirement", "application_area", "substrate", "exposure", "location"]
    if slots.get("problem_requirement") == "tile adhesive":
        keys = ["problem_requirement", "application_area", "substrate", "location"]
    return [key for key in keys if not slots.get(key)]


def captured_slots_text(slots: Slots) -> str:
    labels = {
        "problem_requirement": "system",
        "application_area": "area",
        "substrate": "substrate",
        "exposure": "exposure",
        "location": "location",
    }
    return ", ".join(f"{labels[key]}: {value}" for key, value in slots.items() if value)


def clarification_questions(missing: list[str]) -> list[str]:
    question_map = {
        "problem_requirement": "What problem or system do you need: waterproofing, tile fixing, flooring, concrete repair, sealant, or coating?",
        "application_area": "Which application area is this for: roof, basement, bathroom, parking deck, floor, pool, tank, wall, or joint?",
        "substrate": "What is the substrate: concrete, screed, existing tile, blockwork, plaster, metal, or stone?",
        "exposure": "What exposure should it handle: water, UV/heat, hydrostatic pressure, traffic, chemical exposure, chloride/coastal, or interior use?",
        "location": "Where is the project located: Dubai, Abu Dhabi, Sharjah, another UAE emirate, or another GCC location?",
    }
    return [question_map[key] for key in missing if key in question_map]


def clarification_reply(slots: Slots, missing: list[str]) -> str:
    captured = captured_slots_text(slots)
    questions = clarification_questions(missing)
    lines = [
        "I can recommend the correct construction chemical system, but I need a few project details first.",
    ]
    if captured:
        lines.append(f"I already captured: {captured}.")
    lines.append("Please answer these so I can give the complete output:")
    lines.extend(f"- {question}" for question in questions)
    return "\n\n".join([lines[0], *(lines[1:2] if captured else []), "\n".join(lines[2:] if captured else lines[1:])])


def marketplace_ready_reply(query: str, slots: Slots) -> str:
    captured = captured_slots_text(slots)
    guidance = infer_query_guidance(query)
    categories = ", ".join(guidance["categories"])
    return (
        "I have the required inputs now.\n\n"
        f"Project Summary\n{captured or 'Inputs captured from the conversation.'}\n\n"
        f"Requirement Type\n{categories}\n\n"
        "MARKET RESULT is ready. Open that tab to view the matched options.\n\n"
        "The chat will only handle project inputs and guidance."
    )


def recommendation_summary(recommendation: Any) -> dict[str, Any]:
    return {
        "project_summary": getattr(recommendation, "project_summary", None),
        "detected_location": getattr(recommendation, "detected_location", None),
        "climate_context": getattr(recommendation, "climate_context", None),
        "recommended_categories": getattr(recommendation, "recommended_categories", []),
        "why_recommended": getattr(recommendation, "why_recommended", []),
    }


def profile_value(profile: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def profile_list(profile: dict[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        value = profile.get(key)
        if isinstance(value, list):
            values.extend(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, str) and value.strip():
            values.append(value.strip())
    return list(dict.fromkeys(values))


def infer_query_guidance(query: str) -> dict[str, list[str] | str]:
    normalized = normalize_text(query)
    category_rules = [
        (
            "Tile fixing / grouting",
            ("tile", "tiles", "tiling", "adhesive", "grout", "ceramic", "porcelain"),
            [
                "clean the surface and remove dust, oil, paint, or laitance",
                "use the correct installation method for the selected material",
                "allow the installed system to cure as required by the datasheet",
            ],
        ),
        (
            "Waterproofing",
            ("waterproof", "waterproofing", "water proof", "leak", "leakage", "damp", "bathroom", "roof", "basement", "tank", "pool"),
            [
                "identify whether the water pressure is positive, negative, or hydrostatic",
                "treat cracks, pipe penetrations, corners, and construction joints before application",
                "verify thickness, coverage, curing time, and testing requirements from the datasheet",
            ],
        ),
        (
            "Flooring / coating",
            ("floor", "flooring", "epoxy", "pu", "polyurethane", "traffic", "parking", "warehouse", "deck"),
            [
                "check substrate moisture, surface strength, and contamination before application",
                "select the system by traffic load, UV exposure, chemical exposure, and slip resistance",
                "prepare the surface using the method required by the datasheet",
            ],
        ),
        (
            "Concrete repair",
            ("repair", "spall", "honeycomb", "crack", "patch", "mortar", "rebar", "corrosion"),
            [
                "remove weak concrete and clean exposed reinforcement before repair",
                "confirm whether cracks are active, dormant, structural, or non-structural",
                "cure repair mortar correctly, especially in hot UAE/GCC conditions",
            ],
        ),
        (
            "Sealant / joints",
            ("sealant", "joint", "expansion", "movement", "gap", "backer"),
            [
                "confirm joint width, depth, movement, exposure, and traffic condition",
                "clean and prime joint faces before applying sealant",
                "use backer rod to control sealant depth and avoid three-side adhesion",
            ],
        ),
    ]

    matched_categories = []
    guidance = []
    for category, keywords, steps in category_rules:
        if any(keyword in normalized for keyword in keywords):
            matched_categories.append(category)
            guidance.extend(steps)

    if not matched_categories:
        matched_categories = ["Construction chemical selection"]
        guidance = [
            "confirm the application area, substrate, exposure, and project location",
            "match the product category to the site condition before choosing a brand",
            "verify the final selection against the datasheet",
        ]

    keywords = tokenize_query_keywords(normalized)
    return {
        "categories": list(dict.fromkeys(matched_categories)),
        "guidance": list(dict.fromkeys(guidance))[:5],
        "keywords": keywords[:8],
    }


def product_profile_reply(query: str, profiles: list[dict[str, Any]]) -> str:
    return marketplace_ready_reply(query, extract_slots(query))


def profile_text(profile: dict[str, Any]) -> dict[str, str]:
    return {
        "name": profile_value(profile, "product_name").lower(),
        "brand": profile_value(profile, "brand", "manufacturer").lower(),
        "description": profile_value(profile, "description").lower(),
        "usage": profile_value(profile, "usage").lower(),
        "url": profile_value(profile, "product_url").lower(),
        "price": profile_value(profile, "price").lower(),
    }


def expanded_query_terms(text: str) -> list[str]:
    normalized = normalize_text(text)
    terms = tokenize_query_keywords(normalized)
    expansions = {
        "tile": ["tile", "tiles", "ceramic", "porcelain", "adhesive", "grout"],
        "tiles": ["tile", "tiles", "ceramic", "porcelain", "adhesive", "grout"],
        "tiling": ["tile", "tiles", "ceramic", "porcelain", "adhesive"],
        "adhesive": ["adhesive", "fix", "fixing", "bond"],
        "waterproof": ["waterproof", "waterproofing", "membrane", "seal", "coating"],
        "waterproofing": ["waterproof", "waterproofing", "membrane", "seal", "coating"],
        "basement": ["basement", "tanking", "waterproofing", "membrane"],
        "roof": ["roof", "roofing", "waterproofing", "membrane", "uv"],
        "concrete": ["concrete", "cement", "cementitious", "repair", "protection"],
        "repair": ["repair", "mortar", "patch", "honeycomb", "crack"],
        "floor": ["floor", "flooring", "epoxy", "polyurethane", "coating"],
        "flooring": ["floor", "flooring", "epoxy", "polyurethane", "coating"],
        "sealant": ["sealant", "joint", "expansion", "pu", "silicone"],
        "joint": ["sealant", "joint", "expansion"],
        "anchor": ["anchor", "anchoring", "fixing", "epoxy", "mortar"],
        "grout": ["grout", "joint", "tile", "epoxy"],
        "primer": ["primer", "prime", "bond", "surface"],
    }
    expanded = list(terms)
    for term in terms:
        expanded.extend(expansions.get(term, []))
    if "chemical anchor" in normalized or "anchoring" in normalized:
        expanded.extend(["anchor", "anchoring", "epoxy", "mortar", "rebar"])
    if "tile adhesive" in normalized:
        expanded.extend(["tile", "adhesive", "fix", "ceramic", "porcelain"])
    return list(dict.fromkeys(expanded))


def profile_score(query: str, profile: dict[str, Any]) -> float:
    normalized = normalize_text(query)
    fields = profile_text(profile)
    all_text = " ".join(fields.values())
    terms = expanded_query_terms(normalized)
    score = 0.0
    query_tokens = set(tokenize_query_keywords(normalized))
    name_tokens = set(tokenize_query_keywords(fields["name"]))
    brand_tokens = set(tokenize_query_keywords(fields["brand"]))

    if fields["name"] and fields["name"] in normalized:
        score += 220
    if name_tokens:
        coverage = len(query_tokens & name_tokens) / max(len(name_tokens), 1)
        if coverage >= 1:
            score += 170
        elif coverage >= 0.75:
            score += 120
        elif coverage >= 0.5:
            score += 60
    if brand_tokens and query_tokens & brand_tokens and name_tokens and query_tokens & name_tokens:
        score += 35

    for term in terms:
        if term in fields["name"]:
            score += 14
        if term in fields["brand"]:
            score += 9
        if term in fields["description"]:
            score += 5
        if term in fields["usage"]:
            score += 5
        if term in fields["url"]:
            score += 2

    phrase_boosts = {
        "tile adhesive": ("adhesive", "tile"),
        "fix tiles": ("adhesive", "tile"),
        "tiles to fix": ("adhesive", "tile"),
        "waterproofing": ("waterproof", "membrane"),
        "concrete repair": ("repair", "mortar"),
        "epoxy flooring": ("epoxy", "floor"),
        "chemical anchor": ("anchor", "epoxy"),
        "expansion joint": ("joint", "sealant"),
    }
    for phrase, required_terms in phrase_boosts.items():
        if phrase in normalized and all(term in all_text for term in required_terms):
            score += 35

    if fields["price"]:
        score += 4
    if fields["url"]:
        score += 3
    if fields["brand"]:
        score += 3
    if fields["description"] or fields["usage"]:
        score += 3

    article_markers = ("importance of", "detail", "system for", "factors affecting", "method", "guide")
    if any(marker in fields["name"] for marker in article_markers) and fields["price"] == "":
        score -= 18

    if "tile adhesive" in normalized or "tiling" in normalized:
        if "adhesive" in all_text and ("tile" in all_text or "ceramic" in all_text or "porcelain" in all_text):
            score += 45
        if "fix" in normalized and "fix" in fields["name"]:
            score += 35
        if "tilepro" in all_text:
            score += 12
        if "grout" in fields["name"] and "grout" not in normalized:
            score -= 16

    if "waterproof" in normalized:
        if "waterproof" in all_text or "membrane" in all_text:
            score += 30
        if "tile" in fields["name"] and "tile" not in normalized:
            score -= 8

    if "concrete" in normalized and ("concrete" in all_text or "cement" in all_text):
        score += 18

    if "why" in normalized or "how" in normalized or "where" in normalized or "what is" in normalized:
        query_tokens = set(tokenize_query_keywords(normalized))
        name_tokens = set(tokenize_query_keywords(fields["name"]))
        if len(query_tokens & name_tokens) >= min(2, len(name_tokens)):
            score += 70

    return score


def is_product_profile_query(text: str) -> bool:
    query_tokens = set(tokenize_query_keywords(text))
    for profile in load_product_profiles():
        name = profile_value(profile, "product_name").lower()
        brand = profile_value(profile, "brand", "manufacturer").lower()
        name_tokens = set(tokenize_query_keywords(name))
        brand_tokens = set(tokenize_query_keywords(brand))
        if len(query_tokens & name_tokens) >= min(2, len(name_tokens)) or (brand_tokens and query_tokens & brand_tokens and query_tokens & name_tokens):
            return True

    profiles = retrieve_product_profiles(text, limit=5)
    if not profiles:
        return False
    for profile in profiles:
        name = profile_value(profile, "product_name").lower()
        brand = profile_value(profile, "brand", "manufacturer").lower()
        name_tokens = set(tokenize_query_keywords(name))
        brand_tokens = set(tokenize_query_keywords(brand))
        if (query_tokens & name_tokens) or (brand_tokens and query_tokens & brand_tokens):
            return True
    return False


def product_profiles_for_query(text: str, limit: int = 5) -> list[dict[str, Any]]:
    scored = [
        (profile_score(text, profile), profile)
        for profile in load_product_profiles()
    ]
    scored = [(score, profile) for score, profile in scored if score > 0]
    scored.sort(
        key=lambda item: (
            item[0],
            bool(profile_value(item[1], "price")),
            bool(profile_value(item[1], "product_url")),
            bool(profile_value(item[1], "description", "usage")),
        ),
        reverse=True,
    )
    if scored:
        return [profile for _, profile in scored[:limit]]
    return retrieve_product_profiles(text, limit=limit)


def tokenize_query_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text)
    useful = [
        word
        for word in words
        if len(word) > 2
        and word
        not in {
            "the",
            "for",
            "and",
            "use",
            "what",
            "which",
            "should",
            "how",
            "why",
            "where",
            "can",
            "you",
            "tell",
            "about",
        }
    ]
    if "waterproof" in text:
        useful.extend(["waterproof", "waterproofing", "membrane"])
    if "tile" in text or "tiling" in text:
        useful.extend(["tile", "adhesive", "grout"])
    if "floor" in text:
        useful.extend(["floor", "flooring", "coating"])
    return list(dict.fromkeys(useful))


def groq_reply(system: str, user: str, temperature: float = 0.35, json_mode: bool = False) -> str | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    completion = client.chat.completions.create(**kwargs)
    content = completion.choices[0].message.content
    return content.strip() if content else None


def fallback_general_reply(message: str) -> str:
    normalized = normalize_text(message)
    if has_term(normalized, {"thank", "thanks"}):
        return "You are welcome. Ask me anything, or tell me a construction chemical requirement when you want a project recommendation."
    return (
        "I can help collect the project requirement, area, substrate, exposure, and location. "
        "Once those inputs are complete, MARKET RESULT will show the matched options."
    )


def fallback_technical_reply(recommendation: Any) -> str:
    return (
        "I have enough information to continue.\n\n"
        "Open MARKET RESULT to view the matched options. "
        "The chat will stay focused on project inputs and guidance."
    )


def tile_adhesive_reply(slots: Slots, recommendation: Any | None) -> str:
    return (
        "I have enough tile-fixing context to continue.\n\n"
        "Open MARKET RESULT to view the matched options. "
        "The chat will stay focused on project inputs and guidance."
    )


def final_reply_needs_guard(reply: str) -> bool:
    lowered = reply.lower()
    blocked = (
        "i need more information",
        "need more information",
        "please provide",
        "can you please provide",
        "to provide a more accurate",
        "to refine the final specification",
        "what is the required",
        "what are the required",
    )
    return any(phrase in lowered for phrase in blocked) or "?" in reply


def node_normalise(state: AgentState) -> dict[str, Any]:
    message = " ".join(state.get("message", "").strip().split())
    history = state.get("history", [])
    return {
        "message": message,
        "context": history_context(message, history),
        "normalised_text": normalize_text(message),
    }


def node_route_intent(state: AgentState) -> dict[str, str]:
    normalized = state.get("normalised_text", "")
    history = state.get("history", [])

    if has_term(normalized, BRAND_TERMS):
        return {"intent": "brand_identity"}
    if has_term(normalized, GREETING_TERMS) and len(normalized.split()) <= 5 and not history:
        return {"intent": "greeting"}
    if is_product_profile_query(normalized):
        return {"intent": "technical_consultation"}

    knowledge_shape = normalized.endswith("?") or any(normalized.startswith(starter) for starter in KNOWLEDGE_STARTERS)
    is_slot_detail = has_term(
        normalized,
        REQUIREMENT_TERMS | AREA_TERMS | SUBSTRATE_TERMS | EXPOSURE_TERMS | LOCATION_TERMS,
    )
    current_score = construction_score(normalized)
    context_score = construction_score(normalize_text(state.get("context", "")))

    if knowledge_shape:
        return {"intent": "general_question"}
    if is_slot_detail:
        return {"intent": "technical_consultation"}
    if current_score + context_score // 2 >= 2:
        return {"intent": "technical_consultation"}
    return {"intent": "general_question"}


def terminal_response(
    state: AgentState,
    reply: str,
    needs_clarification: bool = False,
    questions: list[str] | None = None,
    recommendation: dict[str, Any] | None = None,
    report_ready: bool = False,
    report_payload: dict[str, Any] | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "reply": reply,
        "needs_clarification": needs_clarification,
        "questions": questions or [],
        "sources": sources or [],
        "recommendation": recommendation,
        "report_ready": report_ready,
        "report_endpoint": "/recommend/report" if report_ready else None,
        "report_payload": report_payload,
    }


def node_brand(state: AgentState) -> dict[str, Any]:
    return terminal_response(state, FOUNDER_REPLY)


def node_greeting(state: AgentState) -> dict[str, Any]:
    # Greet naturally via the LLM, but keep the brand/founder fact available.
    message = state.get("message", "")
    system = (
        f"You are {BRAND_NAME}, a friendly construction-chemicals assistant. "
        f"{BRAND_NAME} was founded by {FOUNDER_NAME}. Greet the user naturally and briefly. "
        "If they seem ready to describe a problem, invite them to share it, but keep it short and human."
    )
    reply = groq_reply(system, message, temperature=0.6) or GREETING_REPLY
    return terminal_response(state, reply)


def node_general(state: AgentState) -> dict[str, Any]:
    # General, casual, and knowledge questions: let the LLM answer naturally.
    # No RAG retrieval and no "retrieved context" framing for these.
    message = state.get("message", "")
    system = (
        f"You are {BRAND_NAME}, a concise, friendly, and helpful assistant. "
        f"If asked about the founder: {FOUNDER_NAME} founded {BRAND_NAME}. "
        "Answer naturally and conversationally. For construction-chemical topics, you may answer from your "
        "own knowledge, but keep it brief and practical. Do not force follow-up questions or forms."
    )
    reply = groq_reply(system, message, temperature=0.5) or fallback_general_reply(message)
    return terminal_response(state, reply, sources=[])


def build_rag_context(state: AgentState) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Retrieve product profiles + datasheet chunks for the user query and build a
    grounded context block. Returns (context_text, profiles, chunks, source_labels)."""
    message = state.get("context", state.get("message", "")) or state.get("message", "")
    profiles = product_profiles_for_query(message, limit=5)
    chunks = retrieve_rag_chunks(message, limit=6)
    sources = rag_source_labels(chunks) if chunks else []

    parts: list[str] = []
    if profiles:
        parts.append("## Matching product profiles")
        for profile in profiles:
            name = profile_value(profile, "product_name") or profile_value(profile, "name") or "Unnamed product"
            brand = profile_value(profile, "brand", "manufacturer")
            category = profile_value(profile, "category", "system_type")
            description = profile_value(profile, "description")
            usage = profile_value(profile, "usage")
            lines = [f"- {name}" + (f" ({brand})" if brand else "") + (f" [{category}]" if category else "")]
            if description:
                lines.append(f"  description: {description}")
            if usage:
                lines.append(f"  usage: {usage}")
            products = profile_list(profile, "products")
            if products:
                lines.append(f"  related products: {', '.join(products)}")
            parts.append("\n".join(lines))
            source_name = name + (f" ({brand})" if brand else "")
            if source_name not in sources:
                sources.append(source_name)
    if chunks:
        parts.append("\n## Retrieved datasheet context")
        for chunk in chunks[:4]:
            snippet = " ".join(chunk.get("text", "").split())
            if len(snippet) > 700:
                snippet = snippet[:700] + "…"
            parts.append(f"- [{chunk.get('filename', 'datasheet')} chunk {chunk.get('chunk_id')}]: {snippet}")

    return "\n\n".join(parts), profiles, chunks, sources


def node_knowledge(state: AgentState) -> dict[str, Any]:
    message = state.get("message", "")
    context_text, profiles, chunks, sources = build_rag_context(state)

    system = (
        f"You are {BRAND_NAME}, a senior construction chemicals expert for UAE/GCC projects. "
        "Answer the user's specific question directly and accurately using the retrieved context below. "
        "Lead with a direct answer, then give practical detail. Do not invent product names, standards, "
        "or datasheet values that are not present in the context. If the context does not cover the question, "
        "say so and answer from general engineering knowledge, clearly marking it as general guidance. "
        "Do not ask the user for project details in a knowledge question unless essential."
    )
    user = message
    if context_text:
        user = (
            f"Retrieved context:\n{context_text}\n\n"
            f"User question: {message}\n\n"
            "Answer the user's specific question using the retrieved context."
        )
    reply = groq_reply(system, user, temperature=0.3)
    if not reply:
        reply = fallback_grounded_reply(message, context_text, profiles, chunks)
    return terminal_response(state, reply, sources=sources)


def fallback_grounded_reply(
    message: str,
    context_text: str,
    profiles: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> str:
    """Rule-based grounded fallback used when no Groq API key is available.
    Produces a query-specific answer from retrieved data instead of a canned message."""
    normalized = normalize_text(message)
    lines: list[str] = []

    if profiles:
        lines.append("Based on the available product profiles, here is what matches your query:")
        for profile in profiles[:3]:
            name = profile_value(profile, "product_name") or profile_value(profile, "name") or "Unnamed product"
            brand = profile_value(profile, "brand", "manufacturer")
            description = profile_value(profile, "description")
            usage = profile_value(profile, "usage")
            heading = f"- {name}" + (f" ({brand})" if brand else "")
            lines.append(heading)
            if description:
                lines.append(f"  {description}")
            if usage:
                lines.append(f"  Typical use: {usage}")
    if chunks:
        lines.append("\nFrom the retrieved technical documents:")
        for chunk in chunks[:2]:
            snippet = " ".join(chunk.get("text", "").split())
            if len(snippet) > 360:
                snippet = snippet[:360] + "…"
            lines.append(f"- {snippet}")
    if not lines:
        lines.append(
            "I could not find product data matching your exact question in the current knowledge base. "
            "Tell me the application area, substrate, exposure, and project location so I can recommend the "
            "correct construction chemical system."
        )
    # Add the practical category guidance only when we have something to anchor it to.
    guidance = infer_query_guidance(message)
    if profiles or chunks:
        lines.append("\nPractical notes:")
        lines.extend(f"- {note}" for note in guidance["guidance"])
    return "\n".join(lines)


def node_technical(state: AgentState) -> dict[str, Any]:
    slots = extract_slots(state.get("context", ""))
    context_text, profiles, chunks, sources = build_rag_context(state)
    return {
        "slots": slots,
        "rag_context": context_text,
        "retrieved_profiles": profiles,
        "retrieved_chunks": chunks,
        "sources": sources,
        "missing_slots": [],
    }


def node_recommend(state: AgentState) -> dict[str, Any]:
    context = state.get("context", state.get("message", ""))
    slots = state.get("slots", {})
    pdf_missing = missing_slot_keys(slots)

    # Always answer the user's specific query from retrieved RAG context instead of
    # stonewalling for missing slots. We already retrieved profiles/chunks in node_technical.
    rag_context = state.get("rag_context", "")
    retrieved_profiles = state.get("retrieved_profiles") or []
    retrieved_chunks = state.get("retrieved_chunks") or []
    sources = state.get("sources") or []
    message = state.get("message", "")

    system = (
        f"You are {BRAND_NAME}, a senior construction chemicals expert for UAE/GCC projects. "
        "Answer the user's question directly and naturally, as a real consultant would speak. "
        "Use the retrieved context below to ground your recommendation in actual product names, "
        "manufacturers, and datasheet facts. Lead with the recommended chemical/system, then give brief "
        "practical guidance. Do NOT start your reply with phrases like 'Based on the retrieved context' or "
        "'Based on your query' — just answer. Do not invent product names, standards, or datasheet values "
        "that are not present in the context. If the context does not cover the question, say so and answer "
        "from general engineering knowledge, clearly marking it as general guidance. Do not force long "
        "clarification questions unless the user asks for a formal PDF report."
    )
    user = message
    if rag_context:
        user = (
            f"Reference product data (use it to ground your answer, but do not mention 'retrieved context'):\n{rag_context}\n\n"
            f"User question: {message}\n\n"
            "Answer naturally and directly, recommending the specific chemical/system from the data above. "
            "At the end, if project details (substrate, exposure, location) are still missing for a formal "
            "recommendation, add ONE short line saying those details would let you generate a full PDF "
            "technical report."
        )
    reply = groq_reply(system, user, temperature=0.3)
    if not reply:
        reply = fallback_grounded_reply(message, rag_context, retrieved_profiles, retrieved_chunks)

    # Only mark clarification-needed when something is genuinely missing AND we have
    # no retrieved data to answer with. Otherwise we already answered above.
    needs_clarification = bool(pdf_missing) and not (retrieved_profiles or retrieved_chunks)
    questions = clarification_questions(pdf_missing) if needs_clarification else []

    profiles_found = bool(product_profiles_for_query(context, limit=5))
    report_ready = profiles_found and not pdf_missing

    return terminal_response(
        state,
        str(reply).strip(),
        needs_clarification=needs_clarification,
        questions=questions,
        recommendation=None,
        report_ready=report_ready,
        report_payload={"query": context, "slots": dict(slots)},
        sources=sources,
    ) | (
        {"missing_slots": pdf_missing}
    )


def route_after_intent(
    state: AgentState,
) -> Literal["node_brand", "node_greeting", "node_general", "node_knowledge", "node_technical"]:
    return {
        "brand_identity": "node_brand",
        "greeting": "node_greeting",
        "general_question": "node_general",
        "knowledge_question": "node_knowledge",
        "technical_consultation": "node_technical",
    }.get(state.get("intent", "general_question"), "node_general")


def route_after_technical(state: AgentState) -> Literal["node_recommend"]:
    return "node_recommend"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("node_normalise", node_normalise)
    graph.add_node("node_route_intent", node_route_intent)
    graph.add_node("node_brand", node_brand)
    graph.add_node("node_greeting", node_greeting)
    graph.add_node("node_general", node_general)
    graph.add_node("node_knowledge", node_knowledge)
    graph.add_node("node_technical", node_technical)
    graph.add_node("node_recommend", node_recommend)

    graph.add_edge(START, "node_normalise")
    graph.add_edge("node_normalise", "node_route_intent")
    graph.add_conditional_edges("node_route_intent", route_after_intent)
    graph.add_conditional_edges("node_technical", route_after_technical)
    for terminal in ("node_brand", "node_greeting", "node_general", "node_knowledge", "node_recommend"):
        graph.add_edge(terminal, END)
    return graph.compile()


_graph = build_graph()


def run_chat_agent(
    message: str,
    history: list[dict[str, str]],
    recommendation_builder: Callable[[str], Any],
    thread_id: str = "default",
) -> dict[str, Any]:
    global _recommendation_builder
    _recommendation_builder = recommendation_builder

    initial: AgentState = {
        "message": message,
        "history": history,
        "intent": "",
        "normalised_text": "",
        "slots": Slots(),
        "reply": "",
        "needs_clarification": False,
        "questions": [],
        "sources": [],
        "recommendation": None,
        "report_ready": False,
        "report_endpoint": None,
        "report_payload": None,
        "missing_slots": [],
    }
    final = _graph.invoke(initial, config={"configurable": {"thread_id": thread_id}})
    slots = final.get("slots") or {}
    missing = final.get("missing_slots") if "missing_slots" in final else missing_slot_keys(slots)
    return {
        "reply": final.get("reply", ""),
        "intent": final.get("intent", ""),
        "needs_clarification": final.get("needs_clarification", False),
        "questions": final.get("questions", []),
        "sources": final.get("sources", []),
        "recommendation": final.get("recommendation"),
        "requirements": {key: value for key, value in slots.items() if value},
        "missing_requirements": [MISSING_LABELS.get(key, key) for key in missing],
        "report_ready": final.get("report_ready", False),
        "report_endpoint": final.get("report_endpoint"),
        "report_payload": final.get("report_payload"),
    }
