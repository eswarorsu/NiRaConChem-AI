import json
import os
import re
from collections.abc import Callable
from typing import Any

from groq import Groq

from app.agent_prompt import NIRACONCHEM_AGENT_SYSTEM_PROMPT

FOUNDER_REPLY = (
    "NIRACONCHEM AI was founded by Sravani Uppu, a specialist in construction "
    "chemicals specifications with 10 years of experience."
)

GREETING_REPLY = (
    "Hi, I am NIRACONCHEM AI. Tell me the construction chemical problem first, "
    "and I will collect the project details needed for an accurate recommendation "
    "and PDF technical report."
)

CONSTRUCTION_TERMS = {
    "waterproof",
    "waterproofing",
    "basement",
    "roof",
    "rooftop",
    "terrace",
    "bathroom",
    "wet area",
    "pool",
    "tank",
    "floor",
    "flooring",
    "epoxy",
    "pu",
    "polyurethane",
    "repair",
    "concrete",
    "crack",
    "honeycomb",
    "sealant",
    "joint",
    "coating",
    "tile",
    "adhesive",
    "grout",
    "screed",
    "mortar",
    "plaster",
    "chemical",
    "chemicals",
    "construction",
}

BROAD_TERMS = {
    "waterproofing",
    "flooring",
    "repair",
    "coating",
    "sealant",
    "tile adhesive",
    "construction chemicals",
    "chemical",
    "chemicals",
}

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
    "wall",
    "slab",
    "balcony",
    "podium",
}

EXPOSURE_TERMS = {
    "uv",
    "heat",
    "traffic",
    "chemical",
    "chloride",
    "coastal",
    "water",
    "pressure",
    "hydrostatic",
    "potable",
    "external",
    "exterior",
    "interior",
    "crack",
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
    "grout",
    "leak",
    "crack",
    "honeycomb",
    "corrosion",
    "protection",
}

PROJECT_REQUEST_TERMS = {
    "i need",
    "need",
    "recommend",
    "suggest",
    "select",
    "best",
    "use for",
    "for my",
    "project",
    "site",
    "problem",
    "solution",
    "system",
    "report",
    "pdf",
}

KNOWLEDGE_QUESTION_STARTERS = (
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
)


def normalize_message(message: str) -> str:
    return " ".join(message.strip().split())


def normalize_search_text(message: str) -> str:
    normalized = normalize_message(message).lower()
    replacements = {
        "water proofing": "waterproofing",
        "water proof": "waterproof",
        "tile fixing": "tile adhesive",
        "pu ": "polyurethane ",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def has_any_term(text: str, terms: set[str]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) for term in terms)


def first_matching_term(text: str, terms: set[str]) -> str | None:
    for term in sorted(terms, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text):
            return term
    return None


def consultation_context(message: str, history: list[dict[str, str]]) -> str:
    user_messages = [
        normalize_message(item.get("content", ""))
        for item in history
        if item.get("role") == "user" and item.get("content")
    ]
    user_messages.append(message)
    return " ".join(part for part in user_messages if part)


def extract_requirements(message: str) -> dict[str, str | None]:
    normalized = normalize_search_text(message)
    return {
        "problem_requirement": first_matching_term(normalized, REQUIREMENT_TERMS),
        "application_area": first_matching_term(normalized, AREA_TERMS),
        "substrate": first_matching_term(normalized, SUBSTRATE_TERMS),
        "exposure": first_matching_term(normalized, EXPOSURE_TERMS),
        "location": first_matching_term(normalized, LOCATION_TERMS),
    }


def is_general_knowledge_question(message: str) -> bool:
    normalized = normalize_search_text(message)
    has_question_shape = normalized.endswith("?") or any(
        normalized.startswith(starter) for starter in KNOWLEDGE_QUESTION_STARTERS
    )
    if not has_question_shape:
        return False
    if has_any_term(normalized, PROJECT_REQUEST_TERMS):
        return False
    return True


def is_requirement_detail_message(message: str) -> bool:
    normalized = normalize_search_text(message)
    detail_terms = REQUIREMENT_TERMS | AREA_TERMS | SUBSTRATE_TERMS | EXPOSURE_TERMS | LOCATION_TERMS
    return has_any_term(normalized, detail_terms)


def missing_requirements(requirements: dict[str, str | None]) -> list[str]:
    labels = {
        "problem_requirement": "problem or required system",
        "application_area": "application area",
        "substrate": "substrate",
        "exposure": "exposure condition",
        "location": "project location",
    }
    return [labels[key] for key, value in requirements.items() if not value]


def captured_requirements_text(requirements: dict[str, str | None]) -> str:
    labels = {
        "problem_requirement": "system",
        "application_area": "area",
        "substrate": "substrate",
        "exposure": "exposure",
        "location": "location",
    }
    captured = [
        f"{labels[key]}: {value}"
        for key, value in requirements.items()
        if value
    ]
    return ", ".join(captured)


def clarification_reply(requirements: dict[str, str | None], missing: list[str]) -> str:
    captured = captured_requirements_text(requirements)

    if len(missing) == 1:
        missing_item = missing[0]
        if missing_item == "problem or required system":
            return (
                f"Got it. I have {captured}. One last detail: what system do you need "
                "for this project - waterproofing, coating, concrete repair, flooring, "
                "sealant, tile adhesive, or something else?"
            )
        if missing_item == "application area":
            return (
                f"Got it. I have {captured}. One last detail: which area is this for - "
                "roof, basement, wet area, parking floor, tank, joint, or another area?"
            )
        if missing_item == "substrate":
            return (
                f"Got it. I have {captured}. One last detail: what is the substrate - "
                "concrete, screed, existing tile, metal, blockwork, or something else?"
            )
        if missing_item == "exposure condition":
            return (
                f"Got it. I have {captured}. One last detail: what exposure should the "
                "system handle - UV/heat, water pressure, traffic, chemicals, coastal "
                "chloride, or interior use?"
            )
        if missing_item == "project location":
            return f"Got it. I have {captured}. One last detail: where is the project located?"

    if captured:
        return (
            f"Got it. I have {captured}. I need the remaining details before I recommend "
            "a system and prepare the PDF report."
        )

    return (
        "I can help with that. Tell me the project problem, area, substrate, exposure, "
        "and location so I can recommend the correct construction chemical system."
    )


def detect_intent(message: str) -> str:
    normalized = normalize_search_text(message)
    if has_any_term(normalized, {"founder", "founded", "owner", "sravani", "uppu"}):
        return "brand_identity"
    if has_any_term(normalized, {"hi", "hello", "hey"}) and len(normalized.split()) <= 4:
        return "greeting"
    if is_general_knowledge_question(normalized):
        return "general_question"
    if has_any_term(normalized, CONSTRUCTION_TERMS):
        return "technical_consultation"
    if "niraconchem" in normalized:
        return "brand_identity"
    return "general_question"


def clarification_questions(message: str) -> list[str]:
    requirements = extract_requirements(message)
    questions: list[str] = []
    if not requirements["problem_requirement"]:
        questions.append("What problem are we solving: waterproofing, concrete repair, flooring, coating, sealant, tile adhesive, or another construction chemical need?")
    if not requirements["application_area"]:
        questions.append("Which area is this for: roof, basement, wet area, parking floor, tank, joint, or concrete repair?")
    if not requirements["substrate"]:
        questions.append("What is the substrate: concrete, screed, existing tile, metal, blockwork, or something else?")
    if not requirements["exposure"]:
        questions.append("What exposure should the system handle: UV/heat, water pressure, traffic, chemicals, coastal chloride, or interior use?")
    if not requirements["location"]:
        questions.append("Where is the project located?")
    return questions


def needs_clarification(message: str) -> bool:
    normalized = normalize_search_text(message).strip()
    words = normalized.split()
    requirements = extract_requirements(normalized)
    is_broad = normalized in BROAD_TERMS or any(normalized == f"{term} system" for term in BROAD_TERMS)
    missing_count = len(missing_requirements(requirements))
    return is_broad or len(words) <= 3 or missing_count > 0


def recommendation_summary(recommendation: Any) -> dict[str, Any]:
    profile = recommendation.selected_product_profile or {}
    return {
        "project_summary": recommendation.project_summary,
        "detected_location": recommendation.detected_location,
        "climate_context": recommendation.climate_context,
        "recommended_categories": recommendation.recommended_categories,
        "best_recommended_system": recommendation.best_recommended_system,
        "best_manufacturer": recommendation.best_manufacturer,
        "recommended_products": recommendation.recommended_products,
        "why_recommended": recommendation.why_recommended,
        "missing_information": recommendation.missing_information,
        "supporting_datasheet_references": recommendation.supporting_datasheet_references,
        "selected_product_profile": {
            "product_name": profile.get("product_name"),
            "category": profile.get("category"),
            "application_areas": profile.get("application_areas", []),
            "performance": profile.get("performance", {}),
        },
    }


def fallback_technical_reply(recommendation: Any) -> str:
    system = recommendation.best_recommended_system or "the appropriate construction chemical system"
    manufacturer = recommendation.best_manufacturer or "a verified manufacturer"
    reasons = recommendation.why_recommended or ["matches the stated project requirement"]
    missing = recommendation.missing_information or []
    sources = recommendation.supporting_datasheet_references or []

    reply = [
        f"Based on the project details, I would shortlist {system}.",
        f"The matched manufacturer from the retrieved data is {manufacturer}.",
        "Why this fits: " + " ".join(reasons[:3]),
    ]
    if sources:
        reply.append("I found supporting datasheet references: " + ", ".join(sources[:3]) + ".")
    if missing:
        reply.append("Before final selection, please confirm: " + "; ".join(missing[:3]) + ".")
    reply.append(
        "I have enough information to prepare the PDF report draft now. Final approval should still be "
        "checked against the project specification, site condition, and manufacturer datasheet."
    )
    return "\n\n".join(reply)


def fallback_general_reply(message: str) -> str:
    normalized = normalize_search_text(message)
    if has_any_term(normalized, {"thank", "thanks"}):
        return "You are welcome. Ask me anything, or tell me a construction chemical requirement when you want a project recommendation."
    return (
        "I can answer general questions too. For a deeper LLM answer, connect the Groq API key in the backend environment. "
        "If you want a construction chemical recommendation, tell me the project problem and I will collect the area, "
        "substrate, exposure, and location."
    )


def get_general_llm_reply(message: str, history: list[dict[str, str]]) -> str | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    completion = client.chat.completions.create(
        model=model,
        temperature=0.45,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NIRACONCHEM AI. Answer normal general questions naturally and concisely. "
                    "If the user asks for construction chemical product selection, site recommendation, "
                    "or a PDF report, explain that you need project area, substrate, exposure, and location. "
                    "Do not invent private company facts. Founder detail, if asked: Sravani Uppu is the founder "
                    "and is a construction chemicals specifications specialist with 10 years of experience."
                ),
            },
            *[
                {"role": item["role"], "content": item["content"]}
                for item in history[-6:]
                if item.get("role") in {"user", "assistant"} and item.get("content")
            ],
            {"role": "user", "content": message},
        ],
    )
    reply = completion.choices[0].message.content
    return reply.strip() if reply else None


def get_llm_chat_reply(message: str, history: list[dict[str, str]], recommendation: Any) -> str | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    payload = {
        "user_message": message,
        "recent_history": history[-6:],
        "recommendation": recommendation_summary(recommendation),
        "minimum_report_inputs_confirmed": True,
    }
    completion = client.chat.completions.create(
        model=model,
        temperature=0.35,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    NIRACONCHEM_AGENT_SYSTEM_PROMPT
                    + "\nReturn strict JSON with one key: reply. The reply must be conversational, concise, "
                    "technically careful, and must not invent products or specifications beyond the supplied "
                    "recommendation context. The minimum report inputs are already confirmed, so do not say "
                    "that a PDF report cannot be prepared or that details are required before preparing it. "
                    "If useful, mention that extra site details can refine the final specification."
                ),
            },
            {"role": "user", "content": json.dumps(payload)},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    parsed = json.loads(content)
    reply = parsed.get("reply")
    clean_reply = str(reply).strip() if reply else ""
    if not clean_reply:
        return None
    blocking_report_patterns = [
        r"before i (provide|prepare|generate).*report.*i need",
        r"before .*pdf report.*i need",
        r"(still|also) need .*finali[sz]e.*pdf report",
        r"need .*details.*finali[sz]e.*pdf report",
        r"please provide .* so i can finali[sz]e.*report",
        r"cannot .*report",
        r"can't .*report",
    ]
    if any(re.search(pattern, clean_reply.lower(), re.DOTALL) for pattern in blocking_report_patterns):
        return None
    return clean_reply


def run_chat_agent(
    message: str,
    history: list[dict[str, str]],
    recommendation_builder: Callable[[str], Any],
) -> dict[str, Any]:
    clean_message = normalize_message(message)
    context = consultation_context(clean_message, history)
    current_intent = detect_intent(clean_message)
    context_intent = detect_intent(context)
    is_slot_follow_up = (
        context_intent == "technical_consultation"
        and is_requirement_detail_message(clean_message)
        and not is_general_knowledge_question(clean_message)
    )
    intent = (
        current_intent
        if current_intent in {"brand_identity", "greeting"} or (current_intent == "general_question" and not is_slot_follow_up)
        else context_intent
    )
    context_requirements = extract_requirements(context)
    context_missing = missing_requirements(context_requirements)

    if current_intent == "brand_identity":
        return {
            "reply": FOUNDER_REPLY,
            "intent": intent,
            "needs_clarification": False,
            "questions": [],
            "sources": [],
            "recommendation": None,
            "requirements": {},
            "missing_requirements": [],
            "report_ready": False,
            "report_endpoint": None,
            "report_payload": None,
        }

    if current_intent == "greeting" and not history:
        return {
            "reply": GREETING_REPLY,
            "intent": intent,
            "needs_clarification": False,
            "questions": [],
            "sources": [],
            "recommendation": None,
            "requirements": {},
            "missing_requirements": [],
            "report_ready": False,
            "report_endpoint": None,
            "report_payload": None,
        }

    if current_intent == "general_question" and not is_slot_follow_up:
        return {
            "reply": get_general_llm_reply(clean_message, history) or fallback_general_reply(clean_message),
            "intent": intent,
            "needs_clarification": False,
            "questions": [],
            "sources": [],
            "recommendation": None,
            "requirements": context_requirements,
            "missing_requirements": context_missing,
            "report_ready": False,
            "report_endpoint": None,
            "report_payload": None,
        }

    requirements = context_requirements
    missing = context_missing

    if needs_clarification(context):
        questions = clarification_questions(context)
        return {
            "reply": clarification_reply(requirements, missing),
            "intent": intent,
            "needs_clarification": True,
            "questions": questions,
            "sources": [],
            "recommendation": None,
            "requirements": requirements,
            "missing_requirements": missing,
            "report_ready": False,
            "report_endpoint": None,
            "report_payload": None,
        }

    recommendation = recommendation_builder(context)
    reply = get_llm_chat_reply(context, history, recommendation) or fallback_technical_reply(recommendation)
    return {
        "reply": reply,
        "intent": intent,
        "needs_clarification": False,
        "questions": recommendation.ai_questions or [],
        "sources": recommendation.supporting_datasheet_references,
        "recommendation": recommendation_summary(recommendation),
        "requirements": requirements,
        "missing_requirements": missing,
        "report_ready": True,
        "report_endpoint": "/recommend/report",
        "report_payload": {"query": context},
    }
