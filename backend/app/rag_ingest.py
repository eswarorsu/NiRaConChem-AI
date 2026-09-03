import json
import re
from pathlib import Path

from app.file_parser import AREA_KEYWORDS, REQUIREMENT_KEYWORDS, extract_text_from_file, find_keywords, normalize_text
from app.rag_store import CHUNKS_PATH, INDEX_PATH, PRODUCT_PROFILES_PATH, tokenize
from app.sika_catalog_ingest import build_catalog as build_sika_catalog

ROOT_DIR = Path(__file__).resolve().parents[2]
DATASHEETS_DIR = ROOT_DIR / "data" / "datasheets"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 160

PRODUCT_PATTERNS = [
    r"\bSaveto\s+Cool\s+Top\b",
    r"\bVetoprime\s+[A-Z]{1,4}\d{2,4}\b",
    r"\bVetoproof\s+[A-Z]{1,4}\d{2,4}\b",
    r"\bVetotop\s+[A-Za-z0-9]+\b",
    r"\bVeto[a-zA-Z]+\s+[A-Z]{1,4}\d{2,4}\b",
]

STRENGTH_RULES = {
    "roof waterproofing": ("roof", "roofing", "rooftop", "pvc roofing", "cool top"),
    "basement waterproofing": ("basement", "retaining wall", "tanking"),
    "UAE/GCC climate": ("uae", "gcc", "hot climate", "uv", "thermal", "heat"),
    "concrete repair": ("repair mortar", "concrete repair", "spall"),
    "joint sealing": ("joint sealant", "movement joint", "sealant"),
    "flooring": ("floor", "traffic coating", "deck coating"),
    "local availability": ("saveto", "saudi", "gcc"),
}

SYSTEM_RULES = [
    (
        "Epoxy protective coating system for concrete tanks",
        ("potable water", "reservoir", "special coating", "vetoproof ec722", "concrete tanks"),
        "coating",
    ),
    (
        "PVC roofing membrane system",
        ("polyvinyl-chloride roofing", "pvc roofing", "sheet waterproofing for roofing"),
        "waterproofing",
    ),
    (
        "Acrylic/PU hybrid roofing waterproofing system",
        ("acrylic/polyurethane hybrid", "cool top", "solar reflective index"),
        "waterproofing",
    ),
    (
        "Cold fluid-applied polyurethane waterproofing system",
        ("cold liquid-applied elastomeric", "pitch extended polyurethane", "vetoproof um766"),
        "waterproofing",
    ),
    (
        "Concrete repair mortar system",
        ("repair mortar", "vetorep", "spall", "honeycomb repair"),
        "repair",
    ),
    (
        "Flexible cementitious waterproofing system",
        ("acrylic modified cement", "cementitious", "vetoproof cm745"),
        "waterproofing",
    ),
    (
        "Epoxy / polyurethane flooring system",
        ("traffic coating", "floor coating", "vetotop"),
        "flooring",
    ),
    (
        "Joint sealant system",
        ("joint sealant", "vetoflex", "backer rod"),
        "sealant",
    ),
]


def chunk_text(text: str) -> list[str]:
    words = normalize_text(text).split()
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


def extract_products(text: str) -> list[str]:
    products: list[str] = []
    for pattern in PRODUCT_PATTERNS:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            cleaned = " ".join(match.split())
            if cleaned.lower() not in {product.lower() for product in products}:
                products.append(cleaned)
    return products[:12]


def normalize_categories(text: str) -> list[str]:
    normalized = text.lower()
    categories: list[str] = []
    if any(term in normalized for term in ("waterproof", "membrane", "tanking", "roofing")):
        categories.append("waterproofing")
    if any(term in normalized for term in ("floor", "traffic coating", "deck coating", "vetotop")):
        categories.append("flooring")
    if any(term in normalized for term in ("repair mortar", "concrete repair", "spall", "honeycomb", "vetorep")):
        categories.append("repair mortar")
    if any(term in normalized for term in ("joint sealant", "sealant", "backer rod", "vetoflex")):
        categories.append("sealant")
    if any(term in normalized for term in ("protective coating", "special coating", "epoxy coating")):
        categories.append("coating")
    return categories or ["general construction chemicals"]


def build_document_profile(filename: str, extension: str, text: str) -> dict:
    normalized = text.lower()
    manufacturer = "Unknown"
    if "saveto" in normalized:
        manufacturer = "Saveto"

    country = "Unknown"
    if "saudi arabia" in normalized or "saudi" in normalized:
        country = "Saudi Arabia"

    categories = normalize_categories(text)

    strengths = [
        strength
        for strength, keywords in STRENGTH_RULES.items()
        if any(keyword in normalized for keyword in keywords)
    ]

    documents_available = []
    if extension == ".pdf":
        documents_available.append("TDS")
    if "guide specification" in normalized or "section " in normalized:
        documents_available.append("specification")
    if "method statement" in normalized or "application" in normalized:
        documents_available.append("method statement")
    if not documents_available:
        documents_available.append(extension.removeprefix(".").upper())

    products = extract_products(text)
    score = 4.5
    score += min(len(products), 4) * 0.7
    score += min(len(categories), 4) * 0.45
    score += min(len(strengths), 4) * 0.45
    if manufacturer != "Unknown":
        score += 0.8
    if country != "Unknown":
        score += 0.3

    return {
        "manufacturer": manufacturer,
        "country": country,
        "products": products,
        "categories": categories,
        "strengths": strengths,
        "documents_available": list(dict.fromkeys(documents_available)),
        "score": round(min(score, 10), 1),
    }


def extract_property(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = " ".join(match.group(1).split())
            value = re.split(
                r"\s+(?:Bond Strength|Tensile Strength|Elongation|Static Crack|Dynamic Crack|Weathering Resistance|Solar Reflective Index|Abrasion Resistance|Resistance to Positive Water Pressure)\b",
                value,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            value = value.strip(" .;,:")
            if value.lower() in {"by pull-off", "test methods", "taber abrader"} and "Abrasion" not in pattern:
                continue
            return value[:120]
    return None


def infer_system_type(text: str) -> tuple[str, str]:
    normalized = text.lower()
    for system_name, keywords, category in SYSTEM_RULES:
        if any(keyword in normalized for keyword in keywords):
            return system_name, category
    if "waterproof" in normalized:
        return "Waterproofing system", "waterproofing"
    if "floor" in normalized:
        return "Flooring / coating system", "flooring"
    if "repair" in normalized:
        return "Concrete repair system", "repair"
    return "Construction chemical system", "general"


def infer_application_areas(text: str, system_type: str, category: str) -> list[str]:
    normalized = text.lower()
    first_scope = normalized[:3500]
    if "related sections" in first_scope:
        first_scope = first_scope.split("related sections", 1)[0]
    if "references" in first_scope:
        first_scope = first_scope.split("references", 1)[0]
    system_text = system_type.lower()

    areas: list[str] = []
    if "roof" in system_text or any(term in first_scope for term in ("roof", "rooftop", "roofing", "inverted roof")):
        areas.append("roof")
    if any(term in first_scope for term in ("basement", "tanking", "retaining wall")):
        areas.append("basement")
    if "balcony" in first_scope or ("balconies" in normalized and category == "waterproofing"):
        areas.append("balcony")
    if "podium" in first_scope:
        areas.append("podium")
    if any(term in first_scope for term in ("parking", "traffic coating", "deck coating")) or category == "flooring":
        areas.append("parking")
    if any(term in first_scope for term in ("wet area", "bathroom", "kitchen")):
        areas.append("wet area")
    if any(term in first_scope for term in ("water tank", "reservoir", "potable water")):
        areas.append("water tank")
    if "sealant" in system_text or category == "sealant":
        areas.append("joint")
    if category == "repair" or "repair mortar" in first_scope or "vetorep" in normalized[:5000]:
        areas.append("concrete repair")

    return list(dict.fromkeys(areas))


def infer_system_layers(text: str, products: list[str], system_type: str) -> dict[str, str]:
    normalized = text.lower()

    def find_product(*needles: str) -> str:
        for product in products:
            lower = product.lower()
            if any(needle in lower for needle in needles):
                return product
        return ""

    primer = find_product("vetoprime", "prime")
    main = find_product("saveto cool top") or find_product("vetoproof", "vetotop")
    reinforcement = ""
    top_coat = find_product("saveto cool top") or find_product("vetotop")

    if not primer:
        primer_match = re.search(r"Primer:\s*([^\.]{1,100})", text, flags=re.IGNORECASE)
        if primer_match:
            primer = " ".join(primer_match.group(1).split())
    if primer.lower().startswith(("is not usually required", "not usually required")):
        primer = ""
    if "pvc roofing" in normalized or "polyvinyl-chloride roofing" in normalized:
        main = main or "PVC roofing membrane"
    if "acrylic/polyurethane hybrid" in normalized:
        main = main or "Acrylic/Polyurethane hybrid roofing/waterproofing membrane"
        top_coat = top_coat or "Acrylic/Polyurethane hybrid waterproofing top coat"
    if "polyester fleece" in normalized:
        reinforcement = "Non-woven polyester fleece reinforcement"
    if "reinforcement mesh" in normalized:
        reinforcement = reinforcement or "Reinforcement mesh"
    if "repair mortar" in system_type.lower() or "concrete repair" in system_type.lower():
        main = find_product("vetorep") or main

    return {
        "primer": primer,
        "main_membrane": main,
        "reinforcement": reinforcement,
        "top_coat": top_coat,
    }


def select_primary_product(products: list[str], category: str, system_type: str) -> str:
    lowered = [(product, product.lower()) for product in products]
    if category == "repair" or "repair" in system_type.lower():
        for product, lower in lowered:
            if "vetorep" in lower:
                return product
    if category == "flooring":
        for product, lower in lowered:
            if "vetotop" in lower:
                return product
    if category == "waterproofing":
        for product, lower in lowered:
            if "saveto cool top" in lower or "vetoproof" in lower:
                return product
    return products[0] if products else system_type


def build_product_profile(document_profile: dict, text: str, filename: str) -> dict:
    system_type, category = infer_system_type(text)
    products = document_profile["products"]
    performance_text = text
    lower_text = text.lower()
    for marker in ("part 2 products", "2.2 special coatings", "materials"):
        marker_index = lower_text.find(marker)
        if marker_index != -1:
            performance_text = text[marker_index:]
            break
    performance = {
        "bond_strength": extract_property(performance_text, (r"Bond Strength\s+by\s+pull-off[:\s]+(.{1,120}?)(?=\. [A-Z]|\sTensile Strength|\sElongation|$)", r"Bond Strength[:\s]+(.{1,120}?)(?=\. [A-Z]|\sTensile Strength|\sElongation|$)")),
        "tensile_strength": extract_property(performance_text, (r"Tensile Strength(?: at 7 days)?(?:\s+ASTM [A-Z0-9 \-,()]+)?[:\s]+(.{1,120}?)(?=\. [A-Z]|\sElongation|\sStatic Crack|\s\d+\.|$)",)),
        "elongation": extract_property(performance_text, (r"Elongation(?: at Break| at 7 days)?(?:\s+ASTM [A-Z0-9 \-,()]+)?[:\s]+(.{1,120}?)(?=\. [A-Z]|\sStatic Crack|\sDynamic Crack|\sSolids|\s\d+\.|$)",)),
        "water_pressure": extract_property(performance_text, (r"Resistance to Positive Water Pressure[:\s]+(.{1,120}?)(?=\. [A-Z]|\sBond Strength|\sTensile Strength|$)",)),
        "solar_reflective_index": extract_property(performance_text, (r"Solar Reflective Index[:\s]+(.{1,120}?)(?=\. [A-Z]|\sManufacturer|$)",)),
        "abrasion_resistance": extract_property(performance_text, (r"Abrasion Resistance[:\s]+(.{1,120}?)(?=\. [A-Z]|\sChloride|\sCO2|$)",)),
    }
    performance = {key: value for key, value in performance.items() if value}
    layers = infer_system_layers(text, products, system_type)
    application_areas = infer_application_areas(text, system_type, category)
    climate_strengths = [
        strength
        for strength in document_profile["strengths"]
        if strength in {"roof waterproofing", "UAE/GCC climate", "local availability", "basement waterproofing", "flooring"}
    ]

    score = document_profile["score"]
    score += 0.4 if any(layers.values()) else 0
    score += 0.4 if performance else 0
    score += 0.3 if application_areas else 0

    return {
        "manufacturer": document_profile["manufacturer"],
        "country": document_profile["country"],
        "product_name": select_primary_product(products, category, system_type),
        "products": products,
        "system_type": system_type,
        "category": category,
        "categories": document_profile["categories"],
        "application_areas": application_areas,
        "climate_strengths": climate_strengths,
        "system_layers": layers,
        "performance": performance,
        "documents_available": document_profile["documents_available"],
        "source_documents": [filename],
        "score": round(min(score, 10), 1),
    }


def _profile_key(profile: dict) -> str:
    """Identity used for cross-source de-duplication: the product name, stripped of
    trademark marks, punctuation and case."""
    name = (profile.get("product_name") or "").lower()
    name = name.replace("\u00ae", "").replace("\u2122", "")
    return re.sub(r"[^a-z0-9]+", "", name)


def _profile_richness(profile: dict) -> int:
    """Higher wins when two sources describe the same product. A profile carrying
    description / usage / technical values grounds the LLM far better than one
    inferred from a product name alone."""
    richness = 0
    if profile.get("description"):
        richness += 3
    if profile.get("usage"):
        richness += 3
    if profile.get("performance"):
        richness += 2
    if any((profile.get("system_layers") or {}).values()):
        richness += 2
    if profile.get("application_areas"):
        richness += 1
    if profile.get("datasheet_url") or profile.get("product_url"):
        richness += 1
    if (profile.get("manufacturer") or "Unknown") != "Unknown":
        richness += 1
    return richness


def merge_profiles(*sources: list[dict]) -> list[dict]:
    """Merge profile lists, keeping the richest profile per product name."""
    best: dict[str, dict] = {}
    order: list[str] = []
    for source in sources:
        for profile in source:
            key = _profile_key(profile)
            if not key:
                continue
            if key not in best:
                best[key] = profile
                order.append(key)
            elif _profile_richness(profile) > _profile_richness(best[key]):
                best[key] = profile
    return [best[key] for key in order]


def build_legacy_catalog_profiles() -> list[dict]:
    """Regenerate the name-inferred QCon catalog profiles from their raw source so a
    re-ingest never silently drops them."""
    try:
        from app.build_profiles_from_catalog import FINAL, transform
    except Exception:
        return []
    if not FINAL.exists():
        return []
    try:
        records = json.loads(FINAL.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [transform(record) for record in records if isinstance(record, dict)]


def ingest_datasheets() -> dict[str, int]:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    documents = []
    document_profiles = []
    files_processed = 0
    supported_extensions = {".pdf", ".docx", ".xlsx", ".txt"}

    for path in sorted(DATASHEETS_DIR.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep" or path.suffix.lower() not in supported_extensions:
            continue

        data = path.read_bytes()
        text = extract_text_from_file(path.name, data)
        if not text:
            continue

        files_processed += 1
        profile = build_document_profile(path.name, path.suffix.lower(), text)
        documents.append(profile)
        document_profiles.append(build_product_profile(profile, text, path.name))
        for index, chunk in enumerate(chunk_text(text), start=1):
            chunks.append(
                {
                    "filename": path.name,
                    "relative_path": str(path.relative_to(ROOT_DIR)),
                    "chunk_id": index,
                    "text": chunk,
                    "tokens": tokenize(chunk),
                    "categories": find_keywords(chunk, REQUIREMENT_KEYWORDS),
                    "areas": find_keywords(chunk, AREA_KEYWORDS),
                    "document_profile": profile,
                }
            )

    # Structured catalogs. These are not parseable documents, so they get their own
    # preprocessing path and are appended to the same index.
    sika_profiles, sika_chunks = build_sika_catalog()
    if sika_chunks:
        chunks.extend(sika_chunks)
        files_processed += 1

    legacy_catalog_profiles = build_legacy_catalog_profiles()

    # Precedence: rich structured catalog > document-derived > name-inferred catalog.
    product_profiles = merge_profiles(sika_profiles, document_profiles, legacy_catalog_profiles)

    chunks_payload = {
        "version": 3,
        "files_processed": files_processed,
        "chunk_count": len(chunks),
        "sources": {
            "datasheet_chunks": len(chunks) - len(sika_chunks),
            "sika_catalog_chunks": len(sika_chunks),
        },
        "chunks": chunks,
    }
    INDEX_PATH.write_text(json.dumps(documents, indent=2), encoding="utf-8")
    CHUNKS_PATH.write_text(json.dumps(chunks_payload, ensure_ascii=False), encoding="utf-8")
    PRODUCT_PROFILES_PATH.write_text(
        json.dumps(product_profiles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "files_processed": files_processed,
        "chunk_count": len(chunks),
        "product_profile_count": len(product_profiles),
    }


if __name__ == "__main__":
    result = ingest_datasheets()
    print(
        f"Ingested {result['files_processed']} sources into {result['chunk_count']} chunks "
        f"and {result['product_profile_count']} product profiles."
    )
