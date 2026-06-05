import json
import os
import re
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.file_parser import UnsupportedFileType, extract_text_from_file, summarize_document_signals
from app.rag_ingest import ingest_datasheets
from app.rag_store import CHUNKS_PATH, PRODUCT_PROFILES_PATH, rag_source_labels, retrieve_product_profiles, retrieve_rag_chunks

load_dotenv()

app = FastAPI(title="NIRACONCHEM AI API")
_rag_ready = False

frontend_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    *[
        origin.strip().rstrip("/")
        for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
        if origin.strip()
    ],
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_rag_indexes() -> None:
    global _rag_ready
    if _rag_ready and CHUNKS_PATH.exists() and PRODUCT_PROFILES_PATH.exists():
        return
    if not CHUNKS_PATH.exists() or not PRODUCT_PROFILES_PATH.exists():
        ingest_datasheets()
    _rag_ready = True


class RecommendationRequest(BaseModel):
    query: str = Field(min_length=2)
    document_context: str | None = None
    document_name: str | None = None


class FileAnalysisResponse(BaseModel):
    filename: str
    file_type: str
    extracted_characters: int
    preview: str
    locations: list[str]
    construction_areas: list[str]
    requirements: list[str]


class RagIngestResponse(BaseModel):
    files_processed: int
    chunk_count: int


class RecommendationResponse(BaseModel):
    project_summary: str
    detected_location: str
    climate_context: list[str]
    recommended_categories: list[str]
    application_guidance: list[str]
    missing_information: list[str]
    ai_recommendation: str | None = None
    ai_precautions: list[str] = []
    ai_questions: list[str] = []
    source: str = "rules"
    document_name: str | None = None
    document_preview: str | None = None
    rag_sources: list[str] = []
    rag_context: list[str] = []
    best_recommended_system: str | None = None
    best_manufacturer: str | None = None
    recommended_products: dict[str, str] = {}
    why_recommended: list[str] = []
    supporting_datasheet_references: list[str] = []
    selected_product_profile: dict | None = None
    alternative_product_profiles: list[dict] = []


UAE_LOCATIONS = {
    "dubai": "Dubai",
    "abu dhabi": "Abu Dhabi",
    "sharjah": "Sharjah",
    "ajman": "Ajman",
    "ras al khaimah": "Ras Al Khaimah",
    "rak": "Ras Al Khaimah",
    "fujairah": "Fujairah",
    "umm al quwain": "Umm Al Quwain",
    "al ain": "Al Ain",
}

CLIMATE_RULES = {
    "coastal": [
        "High humidity and chloride exposure can affect concrete durability.",
        "Prefer UV-stable, salt-tolerant systems for exposed surfaces.",
    ],
    "desert": [
        "High heat and dry wind increase curing and shrinkage risk.",
        "Use hot-weather application windows and protect fresh materials from rapid moisture loss.",
    ],
    "rooftop": [
        "Direct UV, heat cycling, and thermal movement are major design factors.",
        "Use flexible, UV-resistant waterproofing or coating systems.",
    ],
    "underground": [
        "Hydrostatic pressure and damp substrate conditions should be considered.",
        "Use compatible waterproofing systems with strong substrate preparation.",
    ],
    "industrial": [
        "Chemical exposure, abrasion, and service temperature may govern product selection.",
        "Confirm resistance requirements before final material selection.",
    ],
}

LOCATION_EXPOSURE_HINTS = {
    "Dubai": "coastal",
    "Abu Dhabi": "coastal",
    "Sharjah": "coastal",
    "Ajman": "coastal",
    "Ras Al Khaimah": "coastal",
    "Fujairah": "coastal",
    "Umm Al Quwain": "coastal",
    "Al Ain": "desert",
}

CATEGORY_RULES = [
    (
        ("waterproof", "leak", "basement", "roof", "pool", "bathroom", "wet area"),
        [
            "Cementitious waterproofing coating",
            "Polyurethane or acrylic liquid-applied membrane",
            "Flexible sealant for movement joints",
        ],
    ),
    (
        ("repair", "spall", "honeycomb", "crack", "damaged concrete"),
        [
            "Polymer-modified repair mortar",
            "Epoxy bonding agent",
            "Crack injection resin for structural cracks",
        ],
    ),
    (
        ("tile", "adhesive", "pool tile", "cladding"),
        [
            "Cementitious tile adhesive with polymer modification",
            "Epoxy grout for wet or chemically exposed zones",
            "Flexible tile grout for thermal movement areas",
        ],
    ),
    (
        ("floor", "warehouse", "parking", "industrial floor"),
        [
            "Floor hardener or dry-shake topping",
            "Epoxy floor coating",
            "Polyurethane coating for UV or thermal movement exposure",
        ],
    ),
    (
        ("corrosion", "steel", "rebar", "marine", "chloride"),
        [
            "Anti-corrosion rebar coating",
            "Anti-carbonation protective coating",
            "Chloride-resistant concrete protection system",
        ],
    ),
    (
        ("sealant", "joint", "expansion", "movement"),
        [
            "Polyurethane joint sealant",
            "Backer rod and primer system",
            "UV-resistant exterior joint sealant",
        ],
    ),
]


def has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) for term in terms)


def infer_missing_information(text: str) -> list[str]:
    normalized = text.lower()
    has_area = has_any_term(
        normalized,
        (
            "roof",
            "rooftop",
            "basement",
            "bathroom",
            "wet area",
            "parking",
            "floor",
            "joint",
            "expansion joint",
            "tank",
            "pool",
            "wall",
            "slab",
            "podium",
            "terrace",
            "balcony",
        ),
    )
    has_substrate = has_any_term(
        normalized,
        ("concrete", "screed", "tile", "tiles", "metal", "steel", "blockwork", "masonry", "plaster"),
    )
    has_exposure = has_any_term(
        normalized,
        (
            "interior",
            "indoor",
            "exterior",
            "external",
            "outdoor",
            "uv",
            "heat",
            "thermal",
            "water",
            "hydrostatic",
            "chemical",
            "chloride",
            "coastal",
            "traffic",
            "potable",
        ),
    )
    has_performance = has_any_term(
        normalized,
        (
            "coverage",
            "thickness",
            "mm",
            "micron",
            "standard",
            "astm",
            "bs ",
            "en ",
            "crack",
            "movement",
            "load",
            "heavy traffic",
            "light traffic",
            "warranty",
            "specification",
        ),
    )

    missing: list[str] = []
    if not (has_area and has_substrate):
        missing.append("Exact construction area and substrate")
    if not has_exposure:
        missing.append("Interior or exterior exposure")
    if not has_any_term(normalized, ("water", "uv", "heat", "thermal", "chemical", "chloride", "coastal", "traffic", "hydrostatic")):
        missing.append("Expected water, UV, chemical, chloride, traffic, or heat exposure")
    if not has_performance:
        missing.append("Required coverage, thickness, movement, traffic load, or performance standard")
    return missing


def build_rule_based_response(
    query: str,
    document_context: str | None = None,
    document_name: str | None = None,
) -> RecommendationResponse:
    combined_context = f"{query}\n{document_context or ''}"
    normalized = combined_context.lower()

    detected_location = "UAE general"
    for key, label in UAE_LOCATIONS.items():
        if key in normalized:
            detected_location = label
            break

    exposure = LOCATION_EXPOSURE_HINTS.get(detected_location, "desert")
    for candidate in CLIMATE_RULES:
        if candidate in normalized:
            exposure = candidate
            break

    recommended_categories: list[str] = []
    for keywords, categories in CATEGORY_RULES:
        if any(keyword in normalized for keyword in keywords):
            recommended_categories.extend(categories)

    if not recommended_categories:
        recommended_categories = [
            "Construction chemical category assessment required",
            "General substrate primer or bonding system",
            "Protective coating or waterproofing system based on exposure",
        ]

    return RecommendationResponse(
        project_summary=f"Initial assessment for: {query}",
        detected_location=detected_location,
        climate_context=CLIMATE_RULES.get(exposure, CLIMATE_RULES["desert"]),
        recommended_categories=list(dict.fromkeys(recommended_categories)),
        application_guidance=[
            "Confirm substrate type, moisture condition, and surface strength before selection.",
            "Prepare the surface by cleaning dust, laitance, oil, loose concrete, and weak material.",
            "Apply during cooler UAE site hours where possible and protect fresh work from direct heat.",
        ],
        missing_information=infer_missing_information(combined_context),
        document_name=document_name,
        document_preview=document_context[:1200] if document_context else None,
    )


def get_groq_enhancement(
    query: str,
    base: RecommendationResponse,
    document_context: str | None = None,
    document_name: str | None = None,
    rag_chunks: list[dict] | None = None,
) -> dict | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    prompt = {
        "user_query": query,
        "detected_location": base.detected_location,
        "climate_context": base.climate_context,
        "recommended_generic_categories": base.recommended_categories,
        "application_guidance": base.application_guidance,
        "missing_information": base.missing_information,
        "uploaded_document_name": document_name,
        "uploaded_document_context": document_context,
        "retrieved_datasheet_context": [
            {
                "source": f"{chunk['filename']} chunk {chunk['chunk_id']}",
                "text": chunk["text"][:900],
                "document_profile": chunk.get("document_profile", {}),
            }
            for chunk in (rag_chunks or [])[:3]
        ],
    }

    completion = client.chat.completions.create(
        model=model,
        temperature=0.25,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a UAE construction chemicals recommendation assistant. "
                    "Select the best system and product roles using only retrieved datasheet context. "
                    "You may mention manufacturer and product names only when they appear in retrieved context. "
                    "Use retrieved datasheet context as trusted technical reference when provided. "
                    "Consider UAE heat, UV, humidity, salinity, dust, coastal/desert exposure, "
                    "and practical site application. Return strict JSON with keys: "
                    "best_recommended_system string, best_manufacturer string, recommended_products object "
                    "with keys primer, main_membrane, reinforcement, top_coat, why_recommended string array, "
                    "ai_recommendation string, ai_precautions string array, ai_questions string array."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt),
            },
        ],
    )

    content = completion.choices[0].message.content or "{}"
    content = content.strip()
    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```").strip()
        content = content.removesuffix("```").strip()
    start = content.find("{")
    if start != -1:
        content = content[start:]
    parsed, _ = json.JSONDecoder().raw_decode(content)
    return parsed


def infer_best_system(query: str, rag_chunks: list[dict]) -> str:
    text = " ".join(chunk.get("text", "") for chunk in rag_chunks).lower()
    query_text = query.lower()
    if "pvc" in text and has_any_term(query_text, ("roof", "rooftop", "roofing")):
        return "PVC roofing membrane system OR Acrylic/PU hybrid roofing system"
    if "polyurethane" in text or "cold liquid-applied" in text:
        return "Acrylic/PU hybrid waterproofing membrane system"
    return "Construction chemical system based on retrieved datasheets"


def infer_manufacturer(rag_chunks: list[dict]) -> str:
    for chunk in rag_chunks:
        manufacturer = chunk.get("document_profile", {}).get("manufacturer")
        if manufacturer and manufacturer != "Unknown":
            return manufacturer
    return "Manufacturer name not clearly available in retrieved documents"


def infer_recommended_products(rag_chunks: list[dict]) -> dict[str, str]:
    products: list[str] = []
    context_text = " ".join(chunk.get("text", "") for chunk in rag_chunks).lower()
    for chunk in rag_chunks:
        for product in chunk.get("document_profile", {}).get("products", []):
            if product not in products:
                products.append(product)

    def find_product(*needles: str) -> str:
        for product in products:
            lower = product.lower()
            if any(needle in lower for needle in needles):
                return product
        return ""

    primer = find_product("vetoprime", "prime", "primer")
    main_membrane = find_product("saveto cool top") or find_product("pvc", "membrane", "proof")
    top_coat = find_product("saveto cool top") or find_product("top", "coat", "cool")
    reinforcement = find_product("reinforcement", "mesh", "fabric")

    if not primer and "water repellant and anti-chloride primer" in context_text:
        primer = "Water repellant and anti-chloride primer"
    if not main_membrane and "polyvinyl-chloride" in context_text:
        main_membrane = "PVC roofing membrane"
    if not main_membrane and "acrylic/polyurethane hybrid" in context_text:
        main_membrane = "Acrylic/Polyurethane hybrid roofing/waterproofing membrane"
    if not reinforcement and "polyester fleece" in context_text:
        reinforcement = "Non-woven polyester fleece reinforcement"
    if not top_coat and "top layer" in context_text:
        top_coat = "Acrylic/Polyurethane hybrid waterproofing top coat"

    return {
        "primer": primer,
        "main_membrane": main_membrane,
        "reinforcement": reinforcement,
        "top_coat": top_coat,
    }


def default_why_recommended(query: str) -> list[str]:
    query_text = query.lower()
    reasons = []
    if has_any_term(query_text, ("roof", "rooftop", "roofing")):
        reasons.append("Suitable for rooftop exposure")
        reasons.append("Handles UV and thermal movement")
    if "waterproof" in query_text:
        reasons.append("Matches waterproofing requirement")
    return reasons or ["Matches the stated construction chemical requirement"]


def profile_to_product_roles(profile: dict | None) -> dict[str, str]:
    if not profile:
        return {}
    layers = profile.get("system_layers", {})
    roles = {
        "primer": layers.get("primer", ""),
        "main_membrane": layers.get("main_membrane", ""),
        "reinforcement": layers.get("reinforcement", ""),
        "top_coat": layers.get("top_coat", ""),
    }
    return roles if any(roles.values()) else {}


def profile_why_recommended(profile: dict | None, query: str) -> list[str]:
    if not profile:
        return default_why_recommended(query)
    reasons = []
    application_areas = profile.get("application_areas", [])
    climate_strengths = profile.get("climate_strengths", [])
    performance = profile.get("performance", {})
    if application_areas:
        reasons.append(f"Matches application area: {', '.join(application_areas[:3])}.")
    if climate_strengths:
        reasons.append(f"Relevant strengths: {', '.join(climate_strengths[:3])}.")
    if performance:
        reasons.append("Supported by extracted technical performance data from datasheets.")
    if profile.get("documents_available"):
        reasons.append(f"Backed by available documents: {', '.join(profile['documents_available'])}.")
    return reasons or default_why_recommended(query)


def build_recommendation(
    query: str,
    document_context: str | None = None,
    document_name: str | None = None,
) -> RecommendationResponse:
    ensure_rag_indexes()
    response = build_rule_based_response(query, document_context, document_name)
    product_profiles = retrieve_product_profiles(query, document_context, limit=3)
    rag_chunks = retrieve_rag_chunks(query, document_context, limit=8)
    response.rag_sources = rag_source_labels(rag_chunks)
    response.rag_context = [chunk["text"][:500] for chunk in rag_chunks]
    response.selected_product_profile = product_profiles[0] if product_profiles else None
    response.alternative_product_profiles = product_profiles[1:]
    profile_references = [
        f"{source} product profile"
        for source in (response.selected_product_profile or {}).get("source_documents", [])
    ]
    response.supporting_datasheet_references = list(dict.fromkeys(profile_references + response.rag_sources))[:3]
    inferred_system = infer_best_system(query, rag_chunks)
    profile_system = response.selected_product_profile.get("system_type") if response.selected_product_profile else None
    response.best_recommended_system = (
        inferred_system if " OR " in inferred_system and profile_system else profile_system
    ) or inferred_system
    response.best_manufacturer = (
        response.selected_product_profile.get("manufacturer") if response.selected_product_profile else None
    ) or infer_manufacturer(rag_chunks)
    response.recommended_products = profile_to_product_roles(response.selected_product_profile) or infer_recommended_products(rag_chunks)
    response.why_recommended = profile_why_recommended(response.selected_product_profile, query)

    try:
        enhancement = get_groq_enhancement(query, response, document_context, document_name, rag_chunks)
    except Exception:
        enhancement = None

    if enhancement:
        response.ai_recommendation = enhancement.get("ai_recommendation")
        response.ai_precautions = enhancement.get("ai_precautions", [])
        response.ai_questions = enhancement.get("ai_questions", [])
        response.best_recommended_system = response.best_recommended_system or enhancement.get("best_recommended_system")
        response.best_manufacturer = enhancement.get("best_manufacturer") or response.best_manufacturer
        if not response.selected_product_profile:
            enhanced_products = enhancement.get("recommended_products") or {}
            response.recommended_products = {
                key: value or enhanced_products.get(key) or ""
                for key, value in response.recommended_products.items()
            }
        response.why_recommended = enhancement.get("why_recommended") or response.why_recommended
        response.source = "profiles+rag+groq" if product_profiles else ("rag+groq" if rag_chunks else "groq")
    elif product_profiles:
        response.source = "profiles+rag"
    elif rag_chunks:
        response.source = "rag+rules"

    return response


def bullet_list(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style), leftIndent=8) for item in items],
        bulletType="bullet",
        leftIndent=14,
    )


def build_pdf_report(query: str, recommendation: RecommendationResponse) -> BytesIO:
    def detect_project_type() -> str:
        text = f"{query} {' '.join(recommendation.recommended_categories)}".lower()
        if has_any_term(text, ("roof", "rooftop")) or "waterproof" in text:
            return "Waterproofing"
        if "floor" in text or "parking" in text:
            return "Industrial Floor / Flooring"
        if "repair" in text or "crack" in text:
            return "Concrete Repair"
        if "tile" in text:
            return "Tile Installation"
        return "Construction Chemical Recommendation"

    def detect_project_area() -> str:
        text = query.lower()
        area_map = {
            "roof": "Roof",
            "rooftop": "Roof",
            "balcony": "Balcony",
            "podium": "Podium",
            "basement": "Basement",
            "parking": "Parking",
            "tank": "Water Tank",
            "wet area": "Wet Area",
        }
        for keyword, label in area_map.items():
            if keyword in text:
                return label
        return "Not specified"

    def climate_label() -> str:
        context = " ".join(recommendation.climate_context).lower()
        labels = []
        if "uv" in context or "heat" in context:
            labels.append("High UV / Heat")
        if "humidity" in context or "chloride" in context:
            labels.append("Coastal / High Humidity")
        if "desert" in context or "dry" in context:
            labels.append("Desert")
        if "chemical" in context:
            labels.append("Industrial Exposure")
        return ", ".join(labels) or "UAE General Climate"

    def detected_exposures() -> list[str]:
        text = f"{query} {' '.join(recommendation.climate_context)} {' '.join(recommendation.recommended_categories)}".lower()
        checks = [
            ("Water Exposure", ("water", "waterproof", "leak", "wet")),
            ("UV Exposure", ("uv", "sun", "rooftop")),
            ("Thermal Movement", ("thermal", "heat", "movement", "rooftop")),
            ("Chemical Exposure", ("chemical", "industrial")),
            ("Chloride Exposure", ("chloride", "coastal", "marine", "humidity")),
            ("Abrasion Exposure", ("abrasion", "traffic", "floor", "parking")),
        ]
        exposures = [label for label, terms in checks if any(term in text for term in terms)]
        if has_any_term(text, ("roof", "roofing")):
            if "UV Exposure" not in exposures:
                exposures.append("UV Exposure")
            if "Thermal Movement" not in exposures:
                exposures.append("Thermal Movement")
        return exposures or ["Exposure level not fully defined"]

    def risk_factors() -> list[str]:
        risks = []
        text = query.lower()
        if has_any_term(text, ("roof", "rooftop")):
            risks.extend(["Direct UAE sun and UV exposure", "Thermal expansion and contraction of the roof substrate"])
        if "waterproof" in text:
            risks.append("Water ingress if detailing, laps, joints, or terminations are not treated correctly")
        if recommendation.detected_location != "UAE general":
            risks.append(f"Local {recommendation.detected_location} climate and site exposure must be confirmed")
        return risks or ["Site exposure and substrate condition require confirmation"]

    def confidence_score() -> str:
        score = 55
        if recommendation.rag_sources:
            score += 20
        if recommendation.source == "rag+groq":
            score += 15
        if recommendation.best_manufacturer and "not clearly" not in recommendation.best_manufacturer.lower():
            score += 5
        if recommendation.recommended_products:
            score += 5
        return f"{min(score, 95)}%"

    def first_available_product(*keys: str) -> str:
        for key in keys:
            value = recommendation.recommended_products.get(key)
            if value:
                return value
        return "Not clearly available in retrieved documents"

    def product_detail_rows() -> list[list[str]]:
        manufacturer = recommendation.best_manufacturer or "Not clearly available"
        return [
            ["Primer", f"Product Name: {first_available_product('primer')}\nManufacturer: {manufacturer}\nPurpose: Improve adhesion and prepare substrate"],
            ["Intermediate Coat", f"Product Name: {first_available_product('reinforcement')}\nManufacturer: {manufacturer}\nPurpose: Reinforcement or build-up layer where required"],
            ["Main Product", f"Product Name: {first_available_product('main_membrane')}\nManufacturer: {manufacturer}\nPurpose: Primary waterproofing/protection membrane"],
            ["Top Coat", f"Product Name: {first_available_product('top_coat')}\nManufacturer: {manufacturer}\nPurpose: UV/weather exposed finishing coat"],
        ]

    def extract_property(label: str, patterns: tuple[str, ...]) -> str:
        text = " ".join(recommendation.rag_context)
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split())
        return "TBD - verify in final datasheet"

    profile_performance = (recommendation.selected_product_profile or {}).get("performance", {})
    performance_rows = [
        ["Bond Strength", profile_performance.get("bond_strength") or extract_property("Bond Strength", (r"Bond Strength[:\s]+([^\.]{1,80})",))],
        ["Tensile Strength", profile_performance.get("tensile_strength") or extract_property("Tensile Strength", (r"Tensile Strength[:\s]+([^\.]{1,80})",))],
        ["Elongation", profile_performance.get("elongation") or extract_property("Elongation", (r"Elongation(?: at Break)?[:\s]+([^\.]{1,80})",))],
        ["Water Pressure Resistance", profile_performance.get("water_pressure") or extract_property("Water Pressure Resistance", (r"Resistance to Positive Water Pressure[:\s]+([^\.]{1,80})", r"Water Pressure[:\s]+([^\.]{1,80})"))],
        ["Abrasion Resistance", profile_performance.get("abrasion_resistance") or extract_property("Abrasion Resistance", (r"Abrasion Resistance[:\s]+([^\.]{1,80})",))],
        ["UV Resistance", "Supported by retrieved roof/UV/heat exposure context" if any("uv" in c.lower() or "weathering" in c.lower() for c in recommendation.rag_context) else "TBD - verify in final datasheet"],
        ["Solar Reflective Index", profile_performance.get("solar_reflective_index") or "TBD - verify in final datasheet"],
        ["Chemical Resistance", extract_property("Chemical Resistance", (r"Chemical Resistance[:\s]+([^\.]{1,80})",))],
        ["Service Life", "Project warranty/service life to be confirmed from project specification"],
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="NIRACONCHEM AI Technical Recommendation Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#0b4f4a"),
        fontSize=15.5,
        leading=19,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0f766e"),
        fontSize=12,
        leading=15,
        spaceBefore=14,
        spaceAfter=7,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#102033"),
        fontSize=9,
        leading=12.5,
        wordWrap="CJK",
    )
    label_style = ParagraphStyle(
        "Label",
        parent=body_style,
        textColor=colors.HexColor("#0b4f4a"),
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10.5,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=body_style,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    muted_style = ParagraphStyle(
        "Muted",
        parent=body_style,
        textColor=colors.HexColor("#53677d"),
        fontSize=8.2,
        leading=11,
    )

    def section(title: str) -> Paragraph:
        return Paragraph(title, section_style)

    def cell(value: object, style: ParagraphStyle) -> Paragraph:
        text = escape(str(value or ""))
        text = text.replace("\n", "<br/>")
        return Paragraph(text, style)

    def data_table(rows: list[list[str]], widths: list[float] | None = None, header: bool = False) -> Table:
        wrapped_rows = []
        for row_index, row in enumerate(rows):
            wrapped_row = []
            for col_index, value in enumerate(row):
                style = body_style
                if header and row_index == 0:
                    style = header_cell_style
                elif not header and col_index == 0:
                    style = label_style
                wrapped_row.append(cell(value, style))
            wrapped_rows.append(wrapped_row)

        table_style = [
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#d7e7e3")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        if header:
            table_style.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        else:
            table_style.extend(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef8f7")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0b4f4a")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ]
            )
        return Table(wrapped_rows, colWidths=widths, splitByRow=True, repeatRows=1 if header else 0, style=TableStyle(table_style))

    story = [
        Paragraph("NIRACONCHEM AI TECHNICAL RECOMMENDATION REPORT", title_style),
        Spacer(1, 4),
        section("1. PROJECT INFORMATION"),
        data_table(
            [
                ["Project Query", query],
                ["Project Type", detect_project_type()],
                ["Project Area", detect_project_area()],
                ["Detected Location", recommendation.detected_location],
                ["Climate Conditions", climate_label()],
                ["Report Date", datetime.now().strftime("%d %B %Y")],
                ["Recommendation Source", "AI + Vector Database + Technical Datasheets" if recommendation.rag_sources else recommendation.source],
            ],
            [56 * mm, 106 * mm],
        ),
        section("2. PROJECT CONDITION ASSESSMENT"),
        Paragraph("<b>Project Summary:</b>", body_style),
        Paragraph(recommendation.project_summary, body_style),
        Spacer(1, 4),
        Paragraph("<b>Detected Exposure Conditions:</b>", body_style),
        bullet_list(detected_exposures(), body_style),
        Paragraph("<b>Risk Factors:</b>", body_style),
        bullet_list(risk_factors(), body_style),
        section("3. RECOMMENDED SYSTEM"),
        data_table(
            [
                ["System Name", recommendation.best_recommended_system or "Not clearly available"],
                ["System Category", detect_project_type()],
                ["Application Area", detect_project_area()],
                ["Recommended Manufacturer", recommendation.best_manufacturer or "Not clearly available"],
                ["Confidence Score", confidence_score()],
            ],
            [56 * mm, 106 * mm],
        ),
        PageBreak(),
        section("4. RECOMMENDED PRODUCTS"),
        data_table(
            [["Layer", "Product Details"]] + product_detail_rows(),
            [42 * mm, 120 * mm],
            header=True,
        ),
        Paragraph("<b>Accessories:</b>", body_style),
        bullet_list(["Reinforcement mesh/fleece where specified", "Joint sealant at movement joints", "Backer rod where joint detailing requires it", "Compatible detailing accessories per manufacturer method statement"], body_style),
        section("5. TECHNICAL JUSTIFICATION"),
        Paragraph("<b>Why This System Was Selected:</b>", body_style),
        bullet_list(recommendation.why_recommended or ["Suitable for project conditions.", "Supported by technical datasheets."], body_style),
        section("6. PRODUCT PERFORMANCE DATA"),
        data_table([["Physical Property", "Retrieved / Required Value"]] + performance_rows, [60 * mm, 102 * mm], header=True),
        PageBreak(),
        section("7. APPLICATION SYSTEM"),
        data_table(
            [
                ["Step 1", "Surface Preparation"],
                ["Step 2", "Primer Application"],
                ["Step 3", "Base Coat Application"],
                ["Step 4", "Reinforcement Installation"],
                ["Step 5", "Intermediate Coat Application"],
                ["Step 6", "Top Coat Application"],
                ["Step 7", "Curing"],
                ["Step 8", "Final Inspection"],
            ],
            [28 * mm, 134 * mm],
        ),
        section("8. APPLICATION GUIDANCE"),
        bullet_list(recommendation.application_guidance, body_style),
        section("9. QUALITY ASSURANCE REQUIREMENTS"),
        data_table(
            [
                ["Manufacturer Qualification", "Approved manufacturer with relevant project references."],
                ["Installer Qualification", "Certified or manufacturer-approved applicator recommended."],
                ["Mock-Up Requirement", "Recommended before large-scale application."],
                ["Inspection Requirement", "Visual, substrate, thickness, adhesion, and water-tightness checks before handover."],
            ],
            [58 * mm, 104 * mm],
        ),
        section("10. SAFETY PRECAUTIONS"),
        bullet_list(
            recommendation.ai_precautions
            or [
                "Use PPE during application.",
                "Ensure adequate ventilation.",
                "Avoid skin and eye contact.",
                "Follow manufacturer SDS requirements.",
                "Keep flammable materials away from ignition sources.",
                "Dispose waste according to regulations.",
            ],
            body_style,
        ),
        section("11. MISSING INFORMATION"),
        Paragraph(
            "The following information is required for final recommendation:"
            if recommendation.missing_information
            else "No major missing information detected from the provided project details.",
            body_style,
        ),
        *([bullet_list(recommendation.missing_information, body_style)] if recommendation.missing_information else []),
        PageBreak(),
        section("12. DATASHEET REFERENCES"),
        Paragraph("<b>Referenced Documents:</b>", body_style),
        bullet_list(recommendation.supporting_datasheet_references or ["No datasheet reference found."], body_style),
    ]

    if recommendation.document_preview:
        story.extend(
            [
                Paragraph("<b>Uploaded Document Context:</b>", body_style),
                Paragraph(recommendation.document_preview[:1200], body_style),
            ]
        )
    if recommendation.rag_context:
        story.append(Paragraph("<b>Supporting Context:</b>", body_style))
        for source, context in list(zip(recommendation.rag_sources, recommendation.rag_context, strict=False))[:3]:
            story.extend(
                [
                    Paragraph(source, muted_style),
                    Paragraph(escape(context[:650]), muted_style),
                    Spacer(1, 6),
                ]
            )

    alternative_rows = [
        [
            "Option 1",
            f"Manufacturer: {recommendation.best_manufacturer or 'Not clearly available'}\n"
            f"System: {recommendation.best_recommended_system or 'Not clearly available'}\n"
            "Advantages: Primary selected product profile",
        ]
    ]
    for index, profile in enumerate(recommendation.alternative_product_profiles[:2], start=2):
        alternative_rows.append(
            [
                f"Option {index}",
                f"Manufacturer: {profile.get('manufacturer') or 'Not clearly available'}\n"
                f"System: {profile.get('system_type') or 'Not clearly available'}\n"
                f"Advantages: {', '.join(profile.get('climate_strengths', [])[:3]) or 'Alternative retrieved profile'}",
            ]
        )
    while len(alternative_rows) < 3:
        option_number = len(alternative_rows) + 1
        alternative_rows.append(
            [
                f"Option {option_number}",
                "Manufacturer: Approved equal\nSystem: Equivalent system meeting same technical performance\nAdvantages: Use only after datasheet/submittal verification",
            ]
        )

    story.extend(
        [
            section("13. ALTERNATIVE MANUFACTURERS"),
            data_table(alternative_rows, [35 * mm, 127 * mm], header=False),
            section("14. FINAL RECOMMENDATION"),
            data_table(
                [
                    ["Recommended Manufacturer", recommendation.best_manufacturer or "Not clearly available"],
                    ["Recommended Product System", recommendation.best_recommended_system or "Not clearly available"],
                    ["Reason for Selection", " ".join(recommendation.why_recommended) if recommendation.why_recommended else "Supported by retrieved technical datasheets."],
                    ["Overall Recommendation", recommendation.ai_recommendation or "Proceed with the recommended system only after verifying site substrate, exposure, thickness, detailing, and manufacturer method statement."],
                ],
                [58 * mm, 104 * mm],
            ),
            section("15. DISCLAIMER"),
            Paragraph(
                "This report provides preliminary technical guidance based on available project information, uploaded technical documents, "
                "engineering rules, vector database retrieval, technical datasheets, and AI-assisted analysis. Final product selection must "
                "be verified through site inspection, substrate assessment, project specifications, manufacturer technical datasheets, method "
                "statements, and applicable local standards before implementation.",
                muted_style,
            ),
        ]
    )

    doc.build(story)
    buffer.seek(0)
    return buffer


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest) -> RecommendationResponse:
    return build_recommendation(
        request.query.strip(),
        request.document_context,
        request.document_name,
    )


@app.post("/analyze-file", response_model=FileAnalysisResponse)
async def analyze_file(file: UploadFile = File(...)) -> FileAnalysisResponse:
    filename = file.filename or "uploaded-file"
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size limit is 10 MB.")

    try:
        extracted_text = extract_text_from_file(filename, data)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    signals = summarize_document_signals(extracted_text)
    return FileAnalysisResponse(
        filename=filename,
        file_type=(filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"),
        extracted_characters=len(extracted_text),
        preview=str(signals["preview"]),
        locations=list(signals["locations"]),
        construction_areas=list(signals["construction_areas"]),
        requirements=list(signals["requirements"]),
    )


@app.post("/rag/ingest", response_model=RagIngestResponse)
def ingest_rag() -> RagIngestResponse:
    result = ingest_datasheets()
    global _rag_ready
    _rag_ready = True
    return RagIngestResponse(**result)


@app.get("/rag/status")
def rag_status() -> dict:
    ensure_rag_indexes()
    chunks_count = 0
    profiles_count = 0
    if CHUNKS_PATH.exists():
        try:
            payload = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
            chunks_count = len(payload.get("chunks", [])) if isinstance(payload, dict) else 0
        except json.JSONDecodeError:
            chunks_count = 0
    if PRODUCT_PROFILES_PATH.exists():
        try:
            payload = json.loads(PRODUCT_PROFILES_PATH.read_text(encoding="utf-8"))
            profiles_count = len(payload) if isinstance(payload, list) else 0
        except json.JSONDecodeError:
            profiles_count = 0
    return {
        "rag_ready": chunks_count > 0 and profiles_count > 0,
        "chunks_path_exists": CHUNKS_PATH.exists(),
        "product_profiles_path_exists": PRODUCT_PROFILES_PATH.exists(),
        "chunks_count": chunks_count,
        "product_profiles_count": profiles_count,
    }


@app.post("/recommend/report")
def recommend_report(request: RecommendationRequest) -> StreamingResponse:
    query = request.query.strip()
    recommendation = build_recommendation(query, request.document_context, request.document_name)
    pdf = build_pdf_report(query, recommendation)
    safe_name = "".join(char for char in query.lower() if char.isalnum() or char in (" ", "-"))
    safe_name = "-".join(safe_name.split())[:60] or "recommendation"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=niraconchem-{safe_name}.pdf"},
    )
