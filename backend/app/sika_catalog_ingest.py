"""
sika_catalog_ingest.py
----------------------
Preprocess data/datasheets/sika_products.json (831 scraped Sika UAE products) into
the two structures the retrieval layer already consumes:

  * product profiles  -> data/vector_store/product_profiles.json
  * RAG text chunks   -> data/vector_store/rag_chunks.json

Why a dedicated module instead of the generic datasheet ingest:
  * rag_ingest.ingest_datasheets() only understands .pdf/.docx/.xlsx/.txt and would
    skip the JSON entirely.
  * The catalog carries a REAL taxonomy (category_level_1..4) plus usage, technical
    and application blocks. Mapping that directly is far more accurate than
    build_profiles_from_catalog.py's guess-from-the-product-name rules.

Every product becomes its own chunk "filename" so retrieve_rag_chunks()'s
one-chunk-per-file diversity filter still returns a spread of products.

Run:
    python -m app.sika_catalog_ingest
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.rag_store import tokenize

ROOT_DIR = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT_DIR / "data" / "datasheets" / "sika_products.json"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 160
SOURCE_TAG = "sika_products.json"

# --------------------------------------------------------------------------- #
# 1. Taxonomy mapping: Sika's own categories -> the engine's category vocabulary
#    (waterproofing / flooring / coating / repair / grout / sealant / adhesive /
#     admixture / anchor). Keyed by (category_level_2, category_level_3).
# --------------------------------------------------------------------------- #
CATEGORY_MAP: dict[tuple[str, str | None], str] = {
    ("Waterproofing", "Liquid Applied Membrane"): "waterproofing",
    ("Waterproofing", "Sheet Membrane"): "waterproofing",
    ("Waterproofing", "Bituminous Sheet Membrane"): "waterproofing",
    ("Waterproofing", "Waterproofing mortar"): "waterproofing",
    ("Waterproofing", "Waterproofing Admixture"): "waterproofing",
    ("Waterproofing", "Joint Waterproofing"): "waterproofing",
    ("Waterproofing", "Injection"): "waterproofing",
    ("Roofing", "FPO Membrane"): "waterproofing",
    ("Roofing", "PVC Membranes"): "waterproofing",
    ("Roofing", "Additional Roofing Product"): "waterproofing",
    ("Flooring and Coating", "Industrial Flooring"): "flooring",
    ("Flooring and Coating", "Flooring System"): "flooring",
    ("Flooring and Coating", "Industrial Coating"): "coating",
    ("Refurbishment", "Concrete Repair"): "repair",
    ("Refurbishment", "Structural Strengthening"): "repair",
    ("Refurbishment", "Grouting"): "grout",
    ("Refurbishment", "Concrete Protection"): "coating",
    ("Refurbishment", "Wall & Facade System"): "coating",
    ("Building Finishing", "Tiling System"): "adhesive",
    ("Sealing & Bonding Solutions", "Floor Joints Sealant"): "sealant",
    ("Sealing & Bonding Solutions", "Building Envelope Solution"): "sealant",
    ("Sealing & Bonding Solutions", "Expansion Foam"): "sealant",
    ("Sealing & Bonding Solutions", "Construction Adhesives"): "adhesive",
}

# Fallback when category_level_3 is missing or unmapped.
CATEGORY_BY_LEVEL2: dict[str, str] = {
    "Waterproofing": "waterproofing",
    "Roofing": "waterproofing",
    "Flooring and Coating": "flooring",
    "Refurbishment": "repair",
    "Building Finishing": "adhesive",
    "Sealing & Bonding Solutions": "sealant",
    "Concrete": "admixture",
}

SYSTEM_TYPE_BY_LEVEL3: dict[str, str] = {
    "Liquid Applied Membrane": "Liquid-applied waterproofing membrane system",
    "Sheet Membrane": "Sheet waterproofing membrane system",
    "Bituminous Sheet Membrane": "Bituminous sheet waterproofing system",
    "Waterproofing mortar": "Cementitious waterproofing mortar system",
    "Waterproofing Admixture": "Integral waterproofing admixture",
    "Joint Waterproofing": "Joint waterproofing system",
    "Injection": "Injection waterproofing / crack sealing system",
    "FPO Membrane": "FPO single-ply roofing membrane system",
    "PVC Membranes": "PVC single-ply roofing membrane system",
    "Additional Roofing Product": "Roofing ancillary product",
    "Industrial Flooring": "Industrial resin flooring system",
    "Flooring System": "Flooring system",
    "Industrial Coating": "Industrial protective coating system",
    "Concrete Repair": "Concrete repair mortar system",
    "Structural Strengthening": "Structural strengthening system",
    "Grouting": "Cementitious / epoxy grouting system",
    "Concrete Protection": "Concrete protective coating system",
    "Wall & Facade System": "Wall and facade coating system",
    "Tiling System": "Tile fixing system",
    "Floor Joints Sealant": "Floor joint sealant system",
    "Building Envelope Solution": "Building envelope sealing system",
    "Expansion Foam": "Expanding foam sealing system",
    "Construction Adhesives": "Construction adhesive",
    "Water Reducers": "Concrete water-reducing admixture",
    "Concrete Admixture": "Concrete admixture",
    "Manufacturing Aids for Concrete": "Concrete manufacturing aid",
    "Concrete Essentials": "Concrete ancillary product",
    "Fibers": "Concrete reinforcing fibre",
    "Durability Enhancers": "Concrete durability enhancing admixture",
    "Concrete Accelerator": "Concrete accelerating admixture",
    "Concrete Retarder": "Concrete retarding admixture",
    "Shotcrete Production": "Shotcrete admixture system",
}

# Name-level overrides. Applied AFTER the taxonomy map because Sika files a few
# product families under a parent category that hides what they actually are.
NAME_OVERRIDES: list[tuple[str, str]] = [
    ("anchor", "anchorfix"),
    ("anchor", "anchor fix"),
    ("anchor", "rebar connection"),
    ("grout", "sikagrout"),
    ("grout", "ceramic tile grout"),
    ("grout", "tile grout"),
    ("adhesive", "sikabond"),
    ("adhesive", "sikaceram"),
    ("sealant", "sikaflex"),
    ("sealant", "sikahyflex"),
    ("sealant", "sikasil"),
]

# Secondary category labels, so a query that names the niche still matches even
# when the primary category is broader.
SECONDARY_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("tile adhesive", ("tile adhesive", "fixing tiles", "ceramic tile", "sikaceram", "tiling")),
    ("grout", ("grout", "grouting")),
    ("anchor", ("anchor", "anchoring", "rebar", "dowel")),
    ("crack injection", ("injection", "crack inject", "resin injection")),
    ("waterproofing", ("waterproof", "watertight", "membrane", "tanking")),
    ("repair mortar", ("repair mortar", "patch repair", "spall", "honeycomb")),
    ("sealant", ("sealant", "joint seal")),
    ("coating", ("protective coating", "anti-carbonation", "protective layer")),
    ("flooring", ("floor coating", "industrial floor", "screed", "self-levelling", "self levelling")),
    ("admixture", ("admixture", "plasticiser", "superplasticiser", "water reducer")),
]

# Application areas, matched against the product's INTENT text (tagline +
# description + overview usage) rather than the whole datasheet, so a passing
# mention in an application note doesn't mislabel the product.
AREA_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("roof", ("roof", "rooftop", "roofing", "terrace")),
    ("basement", ("basement", "tanking", "retaining wall", "below ground", "below-ground", "substructure")),
    ("balcony", ("balcony", "balconies")),
    ("podium", ("podium",)),
    ("parking", ("parking", "car park", "traffic deck", "trafficked deck", "vehicular")),
    ("wet area", ("wet area", "bathroom", "kitchen", "shower", "swimming pool", "wet room")),
    ("water tank", ("water tank", "reservoir", "potable water", "drinking water", "cistern")),
    ("joint", ("joint sealant", "movement joint", "expansion joint", "construction joint", "joint seal")),
    ("concrete repair", ("concrete repair", "repair mortar", "spall", "honeycomb", "patch repair", "reinstat")),
    ("facade", ("facade", "façade", "external wall", "cladding", "render")),
    ("tunnel", ("tunnel", "shotcrete", "underground structure")),
    ("industrial floor", ("industrial floor", "warehouse floor", "factory floor", "workshop floor")),
]

# A placement area only makes sense for some product families. Without this gate,
# every admixture whose usage text says "foundations" or "roofs" gets stamped with
# that area and then wins a +0.55 area boost on queries that actually want a
# membrane. Areas are therefore intersected with what the category can serve.
AREA_ELIGIBILITY: dict[str, set[str]] = {
    "waterproofing": {"roof", "basement", "balcony", "podium", "parking", "wet area",
                      "water tank", "joint", "facade", "tunnel", "industrial floor",
                      "concrete repair"},
    "coating": {"roof", "facade", "parking", "water tank", "wet area", "tunnel",
                "basement", "industrial floor", "concrete repair"},
    "flooring": {"industrial floor", "parking", "wet area", "balcony", "podium"},
    "sealant": {"joint", "facade", "parking", "wet area", "water tank", "roof", "basement"},
    "adhesive": {"wet area", "facade", "industrial floor", "balcony"},
    "repair": {"concrete repair", "facade", "tunnel", "basement", "parking"},
    "grout": {"concrete repair", "basement"},
    "anchor": {"concrete repair"},
    "admixture": {"tunnel"},
}


CLIMATE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("UAE/GCC climate", ("hot climate", "tropical", "hot and tropical", "high temperature", "uv", "gcc", "middle east")),
    ("roof waterproofing", ("roof waterproofing", "roofing membrane", "exposed roof")),
    ("basement waterproofing", ("basement", "tanking", "below ground", "below-ground")),
    ("concrete repair", ("concrete repair", "repair mortar")),
    ("joint sealing", ("joint sealant", "movement joint", "expansion joint")),
    ("flooring", ("industrial floor", "floor coating", "screed")),
]

# Technical properties worth surfacing to the LLM, keyed by the label Sika uses.
PERFORMANCE_KEYS = {
    "tensile strength": "tensile_strength",
    "tensile adhesion strength": "bond_strength",
    "adhesive strength": "bond_strength",
    "bond strength": "bond_strength",
    "pull-off strength": "bond_strength",
    "elongation at break": "elongation",
    "tensile elongation": "elongation",
    "compressive strength": "compressive_strength",
    "flexural strength": "flexural_strength",
    "shore a hardness": "shore_a_hardness",
    "shore d hardness": "shore_d_hardness",
    "water tightness": "water_tightness",
    "watertightness": "water_tightness",
    "resistance to water pressure": "water_pressure",
    "temperature resistance": "temperature_resistance",
    "service temperature": "service_temperature",
    "chemical resistance": "chemical_resistance",
    "abrasion resistance": "abrasion_resistance",
    "reaction to fire": "reaction_to_fire",
    "solar reflectance": "solar_reflective_index",
    "crack bridging ability": "crack_bridging",
    "crack bridging": "crack_bridging",
}


# --------------------------------------------------------------------------- #
# 2. Flattening helpers — the JSON nests dicts, lists and list-of-lists.
# --------------------------------------------------------------------------- #
def flatten(value: Any, depth: int = 0) -> str:
    """Render any nested JSON value as one readable line of text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        if value and all(isinstance(item, list) for item in value):
            rows = [": ".join(flatten(cell, depth + 1) for cell in row if flatten(cell, depth + 1)) for row in value]
            return "; ".join(row for row in rows if row)
        return "; ".join(part for part in (flatten(item, depth + 1) for item in value) if part)
    if isinstance(value, dict):
        parts = []
        for key, sub in value.items():
            rendered = flatten(sub, depth + 1)
            if rendered:
                parts.append(f"{key}: {rendered}" if key else rendered)
            elif key:
                parts.append(str(key))
        return ". ".join(parts)
    return str(value)


def section_lines(title: str, value: Any) -> list[str]:
    rendered = flatten(value)
    if not rendered:
        return []
    return [f"{title}: {rendered}"]


def clean_name(name: str) -> str:
    """'Sikagard®-62' -> 'Sikagard-62' for token matching, keeping the display name."""
    return re.sub(r"\s+", " ", (name or "").replace("®", "").replace("™", "").replace("©", "")).strip()


def intent_text(item: dict[str, Any]) -> str:
    """Text that states what the product is FOR (not how it is applied)."""
    overview = item.get("overview") or {}
    parts = [
        item.get("product_name") or "",
        item.get("tagline") or "",
        item.get("description") or "",
        flatten(overview.get("Usage")),
        flatten(overview.get("Uses")),
        flatten(overview.get("Advantages")),
        item.get("category_level_2") or "",
        item.get("category_level_3") or "",
        item.get("category_level_4") or "",
    ]
    return " ".join(part for part in parts if part).lower()


def full_text(item: dict[str, Any]) -> str:
    """The complete searchable document for one product."""
    overview = item.get("overview") or {}
    name = item.get("product_name") or "Unnamed Sika product"
    taxonomy = " > ".join(
        part
        for part in (
            item.get("category_level_1"),
            item.get("category_level_2"),
            item.get("category_level_3"),
            item.get("category_level_4"),
        )
        if part
    )

    lines: list[str] = [
        f"{clean_name(name)} ({name}) — {item.get('tagline') or ''}".strip(" —"),
        f"Manufacturer: {item.get('manufacturer') or 'Sika'}. Region: {item.get('region') or 'UAE'}.",
    ]
    if taxonomy:
        lines.append(f"Category: {taxonomy}.")
    if item.get("description"):
        lines.append(f"Description: {flatten(item['description'])}")

    for label, key in (
        ("Uses", "Usage"),
        ("Uses", "Uses"),
        ("Advantages", "Advantages"),
        ("Colour", "Colour"),
        ("Packaging", "Packaging"),
        ("Appearance", "Appearance"),
    ):
        if key in overview:
            lines.extend(section_lines(label, overview.get(key)))

    lines.extend(section_lines("Product details", item.get("product_details")))
    lines.extend(section_lines("Technical information", item.get("technical_information")))
    lines.extend(section_lines("System information", item.get("system_information")))
    lines.extend(section_lines("Application information", item.get("application_information")))
    lines.extend(section_lines("Consumption", item.get("consumption") or item.get("application_consumption")))
    lines.extend(section_lines("Application", item.get("application")))
    lines.extend(section_lines("Certifications and approvals", item.get("certifications")))

    documents = item.get("documents") or []
    doc_bits = [f"{doc.get('document_type') or 'Document'}: {doc.get('url')}" for doc in documents if doc.get("url")]
    if doc_bits:
        lines.append("Documents: " + "; ".join(doc_bits))
    if item.get("product_url"):
        lines.append(f"Product page: {item['product_url']}")

    return "\n".join(line for line in lines if line.strip())


def chunk_text(text: str) -> list[str]:
    words = " ".join(text.split()).split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(CHUNK_SIZE - CHUNK_OVERLAP, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + CHUNK_SIZE])
        if chunk:
            chunks.append(chunk)
        if start + CHUNK_SIZE >= len(words):
            break
    return chunks


# --------------------------------------------------------------------------- #
# 3. Field inference
# --------------------------------------------------------------------------- #
def infer_category(item: dict[str, Any]) -> str:
    name = (item.get("product_name") or "").lower()
    for category, needle in NAME_OVERRIDES:
        if needle in name:
            return category

    level2 = item.get("category_level_2") or ""
    level3 = item.get("category_level_3")
    mapped = CATEGORY_MAP.get((level2, level3))
    if mapped:
        return mapped

    if level2 == "Building Finishing":
        return "grout" if "grout" in name else "adhesive"
    if level2 == "Sealing & Bonding Solutions":
        return "adhesive" if any(term in name for term in ("bond", "adhesive")) else "sealant"
    return CATEGORY_BY_LEVEL2.get(level2, "general construction chemicals")


def infer_categories(item: dict[str, Any], primary: str) -> list[str]:
    text = intent_text(item)
    labels = [primary]
    for label, needles in SECONDARY_CATEGORY_RULES:
        if label != primary and any(needle in text for needle in needles):
            labels.append(label)
    return list(dict.fromkeys(labels))


def infer_areas(item: dict[str, Any], category: str) -> list[str]:
    text = intent_text(item)
    areas = [area for area, needles in AREA_RULES if any(needle in text for needle in needles)]
    if (item.get("category_level_2") or "") == "Roofing" and "roof" not in areas:
        areas.insert(0, "roof")
    allowed = AREA_ELIGIBILITY.get(category)
    if allowed is not None:
        areas = [area for area in areas if area in allowed]
    return list(dict.fromkeys(areas))


def infer_climate_strengths(item: dict[str, Any]) -> list[str]:
    text = intent_text(item)
    strengths = [label for label, needles in CLIMATE_RULES if any(needle in text for needle in needles)]
    if (item.get("region") or "").upper() in {"UAE", "GCC"} and "UAE/GCC climate" not in strengths:
        strengths.append("UAE/GCC climate")
    strengths.append("local availability")
    return list(dict.fromkeys(strengths))


def extract_performance(item: dict[str, Any]) -> dict[str, str]:
    technical = item.get("technical_information") or {}
    performance: dict[str, str] = {}
    for label, raw in technical.items():
        key = PERFORMANCE_KEYS.get(str(label).strip().lower())
        if not key or key in performance:
            continue
        rendered = flatten(raw)
        if rendered:
            performance[key] = rendered[:220]
    return performance


def primary_usage(item: dict[str, Any]) -> str:
    overview = item.get("overview") or {}
    usage = flatten(overview.get("Usage") or overview.get("Uses"))
    return usage[:900]


def score_product(item: dict[str, Any], areas: list[str], performance: dict[str, str]) -> float:
    score = 5.5
    if item.get("description"):
        score += 0.5
    if primary_usage(item):
        score += 0.6
    if performance:
        score += 0.6
    if item.get("application_information"):
        score += 0.3
    if item.get("certifications"):
        score += 0.3
    if areas:
        score += 0.4
    if any(doc.get("url") for doc in (item.get("documents") or [])):
        score += 0.5
    return round(min(score, 10.0), 1)


def datasheet_url(item: dict[str, Any]) -> str | None:
    for doc in item.get("documents") or []:
        if doc.get("url"):
            return doc["url"]
    return None


def document_types(item: dict[str, Any]) -> list[str]:
    labels = []
    for doc in item.get("documents") or []:
        label = doc.get("document_type") or doc.get("type")
        if label:
            labels.append(str(label))
    return list(dict.fromkeys(labels)) or ["PDS"]


# --------------------------------------------------------------------------- #
# 4. Builders
# --------------------------------------------------------------------------- #
def build_profile(item: dict[str, Any]) -> dict[str, Any]:
    name = (item.get("product_name") or "").strip()
    category = infer_category(item)
    areas = infer_areas(item, category)
    performance = extract_performance(item)
    level3 = item.get("category_level_3")
    system_type = SYSTEM_TYPE_BY_LEVEL3.get(level3 or "", f"{category} system".capitalize())

    return {
        "manufacturer": item.get("manufacturer") or "Sika",
        "brand": item.get("manufacturer") or "Sika",
        "country": "UAE" if (item.get("region") or "").upper() == "UAE" else (item.get("region") or "Unknown"),
        "product_name": name,
        "products": [name],
        "tagline": item.get("tagline") or "",
        "description": " ".join((item.get("description") or "").split())[:900],
        "usage": primary_usage(item),
        "system_type": system_type,
        "category": category,
        "categories": infer_categories(item, category),
        "application_areas": areas,
        "climate_strengths": infer_climate_strengths(item),
        "system_layers": {},
        "performance": performance,
        "documents_available": document_types(item),
        "source_documents": [SOURCE_TAG],
        "product_url": item.get("product_url"),
        "datasheet_url": datasheet_url(item),
        "image_url": item.get("product_image"),
        "catalog_path": [
            part
            for part in (
                item.get("category_level_1"),
                item.get("category_level_2"),
                item.get("category_level_3"),
                item.get("category_level_4"),
            )
            if part
        ],
        "score": score_product(item, areas, performance),
    }


def build_chunks(item: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, Any]]:
    name = profile["product_name"] or "Sika product"
    filename = f"{clean_name(name)} (Sika PDS)"
    document_profile = {
        "manufacturer": profile["manufacturer"],
        "country": profile["country"],
        "products": profile["products"],
        "categories": profile["categories"],
        "strengths": profile["climate_strengths"],
        "documents_available": profile["documents_available"],
        "application_areas": profile["application_areas"],
        "system_type": profile["system_type"],
        "category": profile["category"],
        "product_url": profile["product_url"],
        "score": profile["score"],
    }

    chunks = []
    for index, text in enumerate(chunk_text(full_text(item)), start=1):
        chunks.append(
            {
                "filename": filename,
                "relative_path": str(CATALOG_PATH.relative_to(ROOT_DIR)).replace("\\", "/"),
                "chunk_id": index,
                "text": text,
                "tokens": tokenize(text),
                "categories": profile["categories"],
                "areas": profile["application_areas"],
                "document_profile": document_profile,
            }
        )
    return chunks


def load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                payload = value
                break
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


def build_catalog(items: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (profiles, chunks) for the Sika catalog, de-duplicated by product."""
    items = load_catalog() if items is None else items
    profiles: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        name = (item.get("product_name") or "").strip()
        if not name:
            continue
        key = clean_name(name).lower()
        if key in seen:
            continue
        seen.add(key)
        profile = build_profile(item)
        profiles.append(profile)
        chunks.extend(build_chunks(item, profile))

    return profiles, chunks


if __name__ == "__main__":
    from collections import Counter

    catalog_profiles, catalog_chunks = build_catalog()
    print(f"Sika catalog: {len(catalog_profiles)} profiles, {len(catalog_chunks)} chunks")
    print("categories:", dict(Counter(p["category"] for p in catalog_profiles)))
    area_counts = Counter(area for p in catalog_profiles for area in p["application_areas"])
    print("areas:", dict(area_counts))
    print("no-area products:", sum(1 for p in catalog_profiles if not p["application_areas"]))
    print("with performance:", sum(1 for p in catalog_profiles if p["performance"]))
