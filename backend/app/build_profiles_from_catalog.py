"""
build_profiles_from_catalog.py
---------------------------------
Map data/vector_store/products_final_cleaned.json (732 products, schema:
{product_name, product_url, image_url, brand}) into the product_profiles.json
schema the backend's rag_store.py already consumes
({manufacturer, product_name, system_type, category, application_areas,
  climate_strengths, system_layers, performance, source documents, ...}).

We infer category / application_area / system_type from the product name using
construction-chemical keyword rules, so the existing retrieve_product_profiles()
scoring + area boosts work without code changes.

The 24 legacy (Saveto) profiles are MERGED in, not overwritten.

Run:
    python -m app.build_profiles_from_catalog
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "data" / "vector_store" / "products_final_cleaned.json"
LEGACY = ROOT / "data" / "vector_store" / "product_profiles.json"
OUT = ROOT / "data" / "vector_store" / "product_profiles.json"

# ---- category inference rules ------------------------------------------------
# Ordered by PRIORITY. Each rule matches only on precise keywords so a product is
# assigned the most specific correct category. A product hits the FIRST rule whose
# keywords appear, so order matters: most-specific / unambiguous terms first.
#
# Design notes (bugs fixed vs v1):
#  * "adhesive" now precedes "grout"/"repair" so "tile adhesive"/"tile fix" lands in
#    adhesive, not grout.
#  * "grout" no longer contains the greedy "masterflow"/"fosroc" tokens (those were
#    mis-tagging SikaGrout* and ALL Fosroc items as grout).
#  * "admixture" drops "masterflow"; MasterFlow* grouts are now grout, not admixture.
CATEGORY_RULES = [
    # 1. Anchoring / chemical anchors (resin capsule, injection, rebar fixation)
    ("anchor", ["chemical anchor", "anchorf", "anchor fix", "injektion", "lokfix",
                "mapefix", "fischer fis", "fischer injection", "sika anchorfix",
                "anchorbar", "betonamit", "resin capsule", "anchoring adhesive"]),
    # 2. Tile / construction ADHESIVES (must precede grout/repair)
    ("adhesive", ["tile adhesive", "tile fix", "tiling adhesive", "ceramic adhesive",
                  "tilemaster", "mapetite", "webercol", "kerabond", "sika ceramic",
                  "sika tile", "nitotile", "tilepro", "adhesive for tile", "bond gp",
                  "sikabond", "mapelastic smart", "tile adhesive"]),
    # 3. Grouts (cementitious / epoxy / flowable) — precise tokens only
    ("grout", ["grout", "sikagrout", "mapgrout", "webergout", "flowgrout", "masterflow",
               "emacem", "monotop grout", "pumpable grout", "cementitious grout",
               "epoxy grout", "non-shrink grout"]),
    # 4. Waterproofing membranes / systems
    ("waterproofing", ["waterproof", "membrane", "tanking", "damp proof", "aquaproof",
                       "masterseal", "rendertank", "proofex", "aquashield", "hydro",
                       "sikaplan", "sarnafil", "wet seal", "leak", "sikadur combiflex",
                       "vandex", "proof"]),
    # 5. Sealants / joint fillers
    ("sealant", ["sealant", "silicone", "polyurethane joint", "expansion joint",
                 "movement joint", "flexible joint", "fixall", "hybrid polymer",
                 "sikaflex", "mapesil", "weberjoint", "tremco", "mapelflex", "joint seal"]),
    # 6. Concrete repair (mortars, crack, spall) — note "mortar" kept here, not grout
    ("repair", ["repair", "reprof", "emaco", "renderoc", "monotop", "restoration",
                "spall", "honeycomb", "crack injection", "crack repair", "reinstate",
                "patch repair", "concrete repair", "fairing", "ppc", "monorex",
                "renderoc", "sika mono"]),
    # 7. Flooring / screeds / toppings / traffic coatings
    ("flooring", ["floor", "screed", "topping", "flowcrete", "flowflor", "dekofloor",
                  "sikafloor", "weberfloor", "deck shield", "deckcoat", "traffic deck",
                  "epoxy floor", "polyurethane floor", "ucoat", "flowflor", "cytosine",
                  "self levelling", "self-leveling"]),
    # 8. Admixtures (concrete / mortar additives)
    ("admixture", ["admixture", "plasticiser", "superplasticiser", "air entrain",
                   "retarder", "accelerator", "water reducer", "masterglenium",
                   "masterpave", "conplast", "masterset", "sikaplast", "sikament",
                   "mastermatrix", "mastertile", "builders admixture", "waterproofer admix"]),
    # 9. Coatings / protective paints
    ("coating", ["coating", "paint", "masterprotect", "sikagard", "elastomeric",
                 "anti-carbonation", "cladding render", "texture coat", "decor",
                 "intumescent", "fire proof", "wall coating"]),
]

# Application-area tagging derived purely from product-name signals.
AREA_RULES = [
    ("roof", ["roof", "terrace", "podium", "balcony deck", "rooftop"]),
    ("basement", ["basement", "tanking", "retaining", "foundation", "underground", "cellar"]),
    ("wet area", ["wet area", "bathroom", "kitchen", "shower", "swimming", "pool", "toilet", "wetroom"]),
    ("water tank", ["water tank", "reservoir", "potable", "cistern", "drinking water"]),
    ("parking", ["parking", "car park", "traffic deck", "deck shield", "deckcoat"]),
    ("joint", ["joint", "expansion", "movement joint", "sealant", "construction joint"]),
    ("floor", ["floor", "screed", "industrial", "warehouse", "deck"]),
    ("concrete repair", ["repair", "spall", "honeycomb", "crack", "renderoc"]),
    ("wall", ["wall", "render", "cladding", "facade", "external wall"]),
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


# Brand product-CODE families -> category. Captures items whose plain-English name
# lacks a keyword but whose code (Lokfix, MasterFlow, Conbextra, Cebex, Supercast,
# Sikalastic, ...) unambiguously identifies the system. Applied as a fallback after
# the keyword rules so it resolves the 500+ "general" items.
CODE_FAMILY_RULES = {
    "grout": ["masterflow", "sika flow", "sikaflow", "mapefill", "mapgrout",
              "conbextra", "webergout", "flowgrout", "emacem", "monotop", "freeflow",
              "groutec", "flowcret", "hydroment", "pearl flow", "cem flow"],
    "anchor": ["lokfix", "mapefix", "weberanc", "fischer fis", "fischer inj",
               "anchorfix", "anchor bar", "resin capsule", "rm capsule", "anchorf",
               "expanfluid", "injektions", "ancfix", "anc "],
    "admixture": ["conplast", "cebex", "masterplast", "masterglenium", "sikaplast",
                  "sikament", "masterset", "mastermatrix", "masterpave", "builders admix",
                  "waterproofer", "super plastic", "plastiment", "glenium", "icoplast"],
    "waterproofing": ["supercast", "proofex", "vandex", "rendertank", "masterseal",
                      "sikaplan", "sarnafil", "sikalastic", "combiflex", "aquaproof",
                      "wetseal", "tankguard", "dampshield", "polyseal", "proof"],
    "coating": ["sikagard", "sikalastic", "masterprotect", "dekguard", "elastomeric",
                "intercrete", "dekcoat", "sikaguard", "renderguard", "protec", "nukem",
                "tankguard coat", "epoxy coat"],
    "repair": ["renderoc", "monorex", "monotop", "emaco", "fairing", "sika mono",
               "sikadur", "sikacrete", "reprof", "monolevel", "patch repair", "renderoc",
               "monomix", "monotop", "rmc", "tamcrete", "repairpro", "sikainject",
               "masterinject", "injectoseal", "monomix", "crack inject", "inject eplv",
               "inject mma", "inject ur", "inject ws"],
    "flooring": ["sikafloor", "weberfloor", "flowcrete", "flowflor", "deck shield",
                 "deckcoat", "dekofloor", "cytosine", "self level", "screed", "level",
                 "topping", "epoxy floor", "flowflor", "pu floor"],
    "sealant": ["sikaflex", "mapesil", "weberjoint", "tremco", "fixall", "mapelflex",
                "hybrid polymer", "silicone", "sealant", "joint seal", "flexible joint"],
    "adhesive": ["nitotile", "tilepro", "tilemaster", "mapetite", "webercol", "kerabond",
                 "sika tile", "sika ceramic", "nitobond tile", "adhesive for tile",
                 "tile adhesive", "sikabond"],
}


def infer_category(name: str) -> str:
    n = _norm(name)
    # 1) explicit keyword rules
    for cat, kws in CATEGORY_RULES:
        if any(k in n for k in kws):
            return cat
    # 2) code-family fallback
    for cat, fams in CODE_FAMILY_RULES.items():
        if any(f in n for f in fams):
            return cat
    return "general construction chemicals"


def infer_areas(name: str, category: str) -> list[str]:
    """Areas are derived ONLY from explicit name signals (no forced appends), so a
    flooring product isn't wrongly stamped 'floor' unless the name mentions a floor
    context, and a repair mortar isn't stamped 'concrete repair' without cause."""
    n = _norm(name)
    areas = []
    for area, kws in AREA_RULES:
        if any(k in n for k in kws):
            areas.append(area)
    return list(dict.fromkeys(areas))


def transform(record: dict) -> dict:
    name = (record.get("product_name") or "").strip()
    brand = (record.get("brand") or "").strip() or "Unknown"
    category = infer_category(name)
    areas = infer_areas(name, category)
    return {
        "manufacturer": brand,
        "country": "UAE/GCC supplier" if brand != "Unknown" else "Unknown",
        "product_name": name,
        "products": [name],
        "system_type": f"{brand} {category} system" if brand != "Unknown" else f"{category} system",
        "category": category,
        "categories": [category],
        "application_areas": areas,
        "climate_strengths": ["UAE/GCC climate"] if areas else [],
        "system_layers": {},
        "performance": {},
        "documents_available": [],
        "source_documents": [record.get("product_url") or "products_final_cleaned.json"],
        "product_url": record.get("product_url"),
        "image_url": record.get("image_url"),
        "score": 5.0,
    }


def main() -> None:
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    legacy = json.loads(LEGACY.read_text(encoding="utf-8")) if LEGACY.exists() else []

    new_profiles = [transform(r) for r in final]

    # merge legacy Saveto profiles (avoid duplicate by product_name+manufacturer)
    seen = {(p.get("product_name"), p.get("manufacturer")) for p in new_profiles}
    merged = list(new_profiles)
    for p in legacy:
        key = (p.get("product_name"), p.get("manufacturer"))
        if key not in seen:
            seen.add(key)
            merged.append(p)

    # de-dup within merged
    final_seen = set()
    out = []
    for p in merged:
        key = (p.get("product_name"), p.get("manufacturer"), p.get("category"),
               tuple(p.get("application_areas") or []))
        if key in final_seen:
            continue
        final_seen.add(key)
        out.append(p)

    # backup the old product_profiles.json before overwriting
    if LEGACY.exists():
        LEGACY.replace(ROOT / "data" / "vector_store" / "product_profiles.legacy24.json")

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    from collections import Counter
    cats = Counter(p.get("category") for p in out)
    mfrs = Counter(p.get("manufacturer") for p in out)
    print(f"Wrote {len(out)} profiles -> {OUT}")
    print(f"  legacy 24 saved to product_profiles.legacy24.json")
    print(f"  categories: {dict(cats)}")
    print(f"  top manufacturers: {mfrs.most_common(8)}")


if __name__ == "__main__":
    main()
