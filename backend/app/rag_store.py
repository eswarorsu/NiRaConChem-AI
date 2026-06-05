import json
import math
import re
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
INDEX_PATH = ROOT_DIR / "data" / "vector_store" / "rag_index.json"
CHUNKS_PATH = ROOT_DIR / "data" / "vector_store" / "rag_chunks.json"
PRODUCT_PROFILES_PATH = ROOT_DIR / "data" / "vector_store" / "product_profiles.json"
STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "a",
    "an",
    "is",
    "be",
    "by",
}

QUERY_EXPANSIONS = {
    "rooftop": ["roof", "roofing", "membrane", "uv", "thermal"],
    "roof": ["roofing", "rooftop", "membrane", "uv", "thermal"],
    "waterproofing": ["waterproof", "membrane", "coating"],
    "waterproof": ["waterproofing", "membrane", "coating"],
    "basement": ["tanking", "retaining", "groundwater"],
    "heat": ["uv", "thermal", "temperature"],
}


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def expand_query_tokens(tokens: list[str]) -> list[str]:
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(QUERY_EXPANSIONS.get(token, []))
    return expanded


def has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) for term in terms)


def load_index() -> list[dict[str, Any]]:
    if not CHUNKS_PATH.exists():
        return []
    with CHUNKS_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return list(payload.get("chunks", [])) if isinstance(payload, dict) else []


def load_product_profiles() -> list[dict[str, Any]]:
    if not PRODUCT_PROFILES_PATH.exists():
        return []
    with PRODUCT_PROFILES_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return list(payload) if isinstance(payload, list) else []


def profile_search_text(profile: dict[str, Any]) -> str:
    parts = [
        profile.get("manufacturer", ""),
        profile.get("country", ""),
        profile.get("product_name", ""),
        profile.get("system_type", ""),
        profile.get("category", ""),
        " ".join(profile.get("products", [])),
        " ".join(profile.get("categories", [])),
        " ".join(profile.get("application_areas", [])),
        " ".join(profile.get("climate_strengths", [])),
        " ".join(profile.get("documents_available", [])),
        " ".join(profile.get("source_documents", [])),
        " ".join(str(value) for value in profile.get("system_layers", {}).values()),
        " ".join(str(value) for value in profile.get("performance", {}).values()),
    ]
    return " ".join(parts)


def retrieve_product_profiles(query: str, document_context: str | None = None, limit: int = 3) -> list[dict[str, Any]]:
    profiles = load_product_profiles()
    if not profiles:
        return []

    query_text = f"{query} {document_context or ''}".lower()
    query_tokens = expand_query_tokens(tokenize(query_text))
    if not query_tokens:
        return []

    query_counts = {token: query_tokens.count(token) for token in set(query_tokens)}
    wants_roof = has_any_term(query_text, ("roof", "rooftop", "roofing"))
    wants_waterproofing = any(term in query_text for term in ("waterproof", "waterproofing", "membrane"))
    wants_facade = any(term in query_text for term in ("facade", "eifs", "insulation", "exterior insulation"))
    requested_areas = {
        "roof": wants_roof,
        "basement": has_any_term(query_text, ("basement", "tanking", "retaining wall")),
        "balcony": has_any_term(query_text, ("balcony",)),
        "parking": has_any_term(query_text, ("parking", "floor", "traffic", "deck")),
        "wet area": has_any_term(query_text, ("wet area", "bathroom", "kitchen")),
        "water tank": has_any_term(query_text, ("tank", "reservoir", "potable")),
        "joint": has_any_term(query_text, ("joint", "sealant", "expansion")),
        "concrete repair": has_any_term(query_text, ("repair", "spall", "honeycomb", "crack mortar")),
    }
    active_requested_areas = [area for area, active in requested_areas.items() if active]
    wants_heat = any(term in query_text for term in ("heat", "uv", "sun", "thermal", "exposure"))

    scored: list[tuple[float, dict[str, Any]]] = []
    for profile in profiles:
        text = profile_search_text(profile).lower()
        profile_tokens = set(tokenize(text))
        if not profile_tokens:
            continue
        overlap = sum(weight for token, weight in query_counts.items() if token in profile_tokens)
        score = overlap / math.sqrt(max(len(profile_tokens), 1))
        score += float(profile.get("score", 0)) / 20
        if profile.get("manufacturer") and profile.get("manufacturer") != "Unknown":
            score += 0.25

        areas = profile.get("application_areas", [])
        category = profile.get("category", "")
        system_type = profile.get("system_type", "").lower()
        strengths = profile.get("climate_strengths", [])
        layers = profile.get("system_layers", {})
        performance = profile.get("performance", {})
        product_text = " ".join([profile.get("product_name", ""), " ".join(profile.get("products", []))]).lower()

        if wants_roof:
            if "roof" in areas:
                score += 0.45
            if "roofing" in system_type or "roof waterproofing" in strengths:
                score += 0.35
            if "pvc roofing" in system_type or "acrylic/pu hybrid roofing" in system_type:
                score += 0.25
            if "eifs" in text and not wants_facade:
                score -= 0.8

        if wants_waterproofing:
            if category == "waterproofing" or "waterproofing" in profile.get("categories", []):
                score += 0.35
            if any(layers.values()):
                score += 0.2

        for area in active_requested_areas:
            if area in areas:
                score += 0.55
            elif areas:
                score -= 0.2

        if active_requested_areas and not wants_roof and "roof" in areas:
            score -= 0.3

        if has_any_term(query_text, ("floor",)) and ("flooring" in profile.get("categories", []) or category == "flooring"):
            score += 0.55
        if has_any_term(query_text, ("repair", "spall", "honeycomb")) and ("repair mortar" in profile.get("categories", []) or category == "repair"):
            score += 0.55
            if "vetorep" in product_text or category == "repair":
                score += 0.8
            elif category == "waterproofing":
                score -= 0.35
        if has_any_term(query_text, ("joint", "sealant")) and ("sealant" in profile.get("categories", []) or category == "sealant"):
            score += 0.55

        if has_any_term(query_text, ("tank", "reservoir", "potable", "liner")):
            if "water tank" in areas:
                score += 0.85
            if category == "coating" or "coating" in profile.get("categories", []):
                score += 0.65
            if "ec722" in product_text or "ep722" in product_text:
                score += 0.45
            if "roof" in areas and "water tank" not in areas:
                score -= 0.45

        if wants_heat:
            if "solar_reflective_index" in performance:
                score += 0.45
            if "cool top" in text:
                score += 0.35
            if "UAE/GCC climate" in strengths or "uae/gcc climate" in text:
                score += 0.2

        if score <= 0:
            continue
        enriched = dict(profile)
        enriched["match_score"] = round(score, 4)
        scored.append((score, enriched))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [profile for _, profile in scored[:limit]]


def retrieve_rag_chunks(query: str, document_context: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    chunks = load_index()
    if not chunks:
        return []

    query_tokens = expand_query_tokens(tokenize(f"{query} {document_context or ''}"))
    if not query_tokens:
        return []

    query_counts = {token: query_tokens.count(token) for token in set(query_tokens)}
    query_text = f"{query} {document_context or ''}".lower()
    wants_roof = has_any_term(query_text, ("roof", "rooftop", "roofing"))
    wants_waterproofing = any(term in query_text for term in ("waterproof", "waterproofing", "membrane"))
    wants_facade = any(term in query_text for term in ("facade", "eifs", "insulation", "exterior insulation"))
    requested_areas = {
        "roof": wants_roof,
        "basement": has_any_term(query_text, ("basement", "tanking", "retaining wall")),
        "balcony": has_any_term(query_text, ("balcony",)),
        "parking": has_any_term(query_text, ("parking", "floor", "traffic", "deck")),
        "wet area": has_any_term(query_text, ("wet area", "bathroom", "kitchen")),
        "water tank": has_any_term(query_text, ("tank", "reservoir", "potable")),
        "joint": has_any_term(query_text, ("joint", "sealant", "expansion")),
        "concrete repair": has_any_term(query_text, ("repair", "spall", "honeycomb", "crack mortar")),
    }
    active_requested_areas = [area for area, active in requested_areas.items() if active]

    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        chunk_tokens = set(chunk.get("tokens", []))
        if not chunk_tokens:
            continue
        overlap = sum(weight for token, weight in query_counts.items() if token in chunk_tokens)
        if overlap <= 0:
            continue
        text = chunk.get("text", "").lower()
        profile = chunk.get("document_profile", {})
        score = overlap / math.sqrt(max(len(chunk_tokens), 1))

        if wants_roof:
            if "polyvinyl-chloride roofing" in text or "pvc roofing" in text:
                score += 0.28
            if "roofing membrane" in text or "sheet waterproofing for roofing" in text:
                score += 0.24
            if "inverted roofs" in text or "inverted roof" in text:
                score += 0.22
            if "cold liquid-applied elastomeric waterproofing" in text:
                score += 0.18
            if "roof waterproofing" in profile.get("strengths", []):
                score += 0.18
            if "eifs" in text and not wants_facade:
                score -= 0.35

        if wants_waterproofing:
            if "waterproofing" in profile.get("categories", []):
                score += 0.1
            if "membrane" in text:
                score += 0.08

        profile_text = profile_search_text(profile).lower()
        for area in active_requested_areas:
            if area in profile_text or area in text:
                score += 0.18
            else:
                score -= 0.08
        if active_requested_areas and not wants_roof and ("pvc roofing" in text or "polyvinyl-chloride roofing" in text):
            score -= 0.25
        if has_any_term(query_text, ("repair", "spall", "honeycomb")) and "vetorep" in text:
            score += 0.35

        if score <= 0:
            continue
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    diverse_scored: list[tuple[float, dict[str, Any]]] = []
    seen_files: set[str] = set()
    for score, chunk in scored:
        filename = chunk.get("filename", "")
        if filename in seen_files:
            continue
        seen_files.add(filename)
        diverse_scored.append((score, chunk))
        if len(diverse_scored) >= limit:
            break

    return [
        {
            "filename": chunk["filename"],
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "score": round(score, 4),
            "categories": chunk.get("categories", []),
            "areas": chunk.get("areas", []),
            "document_profile": chunk.get("document_profile", {}),
        }
        for score, chunk in diverse_scored
    ]


def rag_source_labels(chunks: list[dict[str, Any]]) -> list[str]:
    labels = []
    for chunk in chunks:
        label = f"{chunk['filename']} chunk {chunk['chunk_id']}"
        if label not in labels:
            labels.append(label)
    return labels
