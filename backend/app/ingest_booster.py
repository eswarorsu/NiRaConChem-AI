"""
ingest_booster.py — expand the NIRACONCHEM AI dataset from many manufacturer datasheets.

Two jobs:
  1. bulk_ingest(folder)  — ingest a batch of manufacturer TDS PDFs/DOCX/XLSX/TXT from ANY
                            folder (e.g. a "raw_manufacturer_docs/" drop) into the SAME schema
                            rag_ingest.py uses, reusing its extraction logic, then de-duplicates
                            and runs a quality gate so accuracy doesn't regress.
  2. Builds merged product_profiles.json + rag_chunks.json + rag_index.json in data/vector_store.

Run:
    python -m app.ingest_booster --source ../raw_manufacturer_docs --rewrite
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from app.rag_ingest import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    INDEX_PATH,
    CHUNKS_PATH,
    PRODUCT_PROFILES_PATH,
    build_document_profile,
    build_product_profile,
    chunk_text,
    extract_text_from_file,
    tokenize,
)
from app.file_parser import AREA_KEYWORDS, REQUIREMENT_KEYWORDS, find_keywords

# ---------------------------------------------------------------------------
# Brands whose product codes we *recognise*. Used to auto-detect manufacturer
# when the datasheet text does not name it. Add more as you add sources.
# ---------------------------------------------------------------------------
BRAND_CODE_PATTERNS = {
    "Sika":      [r"\bSika[A-Za-z0-9 ]{0,12}\b"],
    "Mapei":     [r"\bMape[A-Za-z0-9 ]{0,12}\b", r"\bPlanitop\b", r"\bMapelastic\b"],
    "Fosroc":    [r"\bFosroc\b", r"\bConbextra\b", r"\bRenderoc\b", r"\bNitobond\b"],
    "Weber":     [r"\bweber[A-Za-z0-9 ]{0,12}\b", r"\bWeber\b"],
    "Saveto":    [r"\bSaveto\b", r"\bVetoprime\b", r"\bVetoproof\b", r"\bVetotop\b",
                  r"\bVetorep\b", r"\bVetoflex\b"],
    "BASF / Master Builders": [r"\bMaster[Bb]uilders\b", r"\bMasterSeal\b", r"\bMasterEmaco\b", r"\bMasterFlow\b"],
    "Sika (flagship)": [r"\bSikadur\b", r"\bSikaflex\b", r"\bSikaTop\b", r"\bSikaMonoTop\b"],
}


def detect_manufacturer(text: str) -> str:
    """Best-effort manufacturer detection from datasheet body."""
    lowered = text.lower()
    # explicit naming
    for brand, pats in BRAND_CODE_PATTERNS.items():
        for pat in pats:
            if re.search(pat, text, flags=re.IGNORECASE):
                # remove the "(flagship)" suffix for a clean label
                return brand.split(" (")[0]
    # fallback heuristics on common phrasing
    for name in ("saveto", "sika", "mapei", "fosroc", "weber", "basf"):
        if name in lowered:
            return name.capitalize()
    return "Unknown"


def bulk_ingest(source_folder: str | Path) -> dict:
    """Ingest every supported file in `source_folder` (non-recursive + 1 level deep)."""
    root = Path(source_folder)
    if not root.exists():
        raise FileNotFoundError(f"Source folder not found: {root}")

    supported = {".pdf", ".docx", ".xlsx", ".txt"}
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in supported and p.name != ".gitkeep":
            files.append(p)
    print(f"[booster] found {len(files)} source files in {root}")

    chunks, documents, product_profiles = [], [], []
    for path in files:
        try:
            data = path.read_bytes()
            text = extract_text_from_file(path.name, data)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {path.name}: {exc}")
            continue
        if not text or len(text.strip()) < 40:
            continue
        # override manufacturer detection from actual content
        doc_profile = build_document_profile(path.name, path.suffix.lower(), text)
        detected = detect_manufacturer(text)
        if doc_profile.get("manufacturer") in (None, "Unknown") and detected != "Unknown":
            doc_profile["manufacturer"] = detected
        documents.append(doc_profile)
        product_profiles.append(build_product_profile(doc_profile, text, path.name))
        for idx, chunk in enumerate(chunk_text(text), start=1):
            chunks.append({
                "filename": path.name,
                "relative_path": str(path.relative_to(root.parent)),
                "chunk_id": idx,
                "text": chunk,
                "tokens": tokenize(chunk),
                "categories": find_keywords(chunk, REQUIREMENT_KEYWORDS),
                "areas": find_keywords(chunk, AREA_KEYWORDS),
                "document_profile": doc_profile,
            })

    print(f"[booster] raw -> {len(documents)} docs, {len(product_profiles)} profiles, {len(chunks)} chunks")
    return {
        "documents": documents,
        "product_profiles": product_profiles,
        "chunks": chunks,
        "files_processed": len(files),
    }


# ---------------------------------------------------------------------------
# De-duplication + quality gate (fixes the defects found in the accuracy audit)
# ---------------------------------------------------------------------------
def _identity(p: dict) -> tuple:
    return (
        p.get("manufacturer"),
        p.get("product_name"),
        p.get("system_type"),
        tuple(p.get("application_areas") or []),
    )


def dedupe_and_clean(profiles: list[dict]) -> list[dict]:
    seen = {}
    out = []
    for p in profiles:
        key = _identity(p)
        if key in seen:
            continue
        seen[key] = True
        # quality fixes
        cat = p.get("category")
        areas = p.get("application_areas") or []
        strengths = p.get("climate_strengths") or []
        # [A3] strip 'roof waterproofing' strength from non-waterproofing items
        if cat != "waterproofing":
            strengths = [s for s in strengths if s != "roof waterproofing"]
            # [A4] drop 'roof' area from non-roof-intended categories
            if cat in ("repair", "sealant", "coating"):
                areas = [a for a in areas if a != "roof"]
        p["climate_strengths"] = strengths
        p["application_areas"] = areas
        out.append(p)
    return out


def write_merged(existing: dict, new_data: dict, rewrite: bool) -> Path:
    old_profiles = existing.get("product_profiles", [])
    old_chunks = existing.get("chunks", [])
    old_docs = existing.get("documents", [])

    if rewrite:
        merged_profiles = new_data["product_profiles"]
        merged_chunks = new_data["chunks"]
        merged_docs = new_data["documents"]
        note = "REWRITTEN from booster source"
    else:
        merged_profiles = old_profiles + new_data["product_profiles"]
        merged_chunks = old_chunks + new_data["chunks"]
        merged_docs = old_docs + new_data["documents"]
        note = "APPENDED to existing store"

    # de-dup + clean on the final set
    merged_profiles = dedupe_and_clean(merged_profiles)
    # re-dedup chunks by (filename, chunk_id)
    seen_c = set()
    merged_chunks = [c for c in merged_chunks
                     if (c["filename"], c["chunk_id"]) not in seen_c
                     and not seen_c.add((c["filename"], c["chunk_id"]))]

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(merged_docs, indent=2), encoding="utf-8")
    CHUNKS_PATH.write_text(json.dumps(
        {"version": 2, "files_processed": len(merged_docs),
         "chunk_count": len(merged_chunks), "chunks": merged_chunks}, indent=2), encoding="utf-8")
    PRODUCT_PROFILES_PATH.write_text(json.dumps(merged_profiles, indent=2), encoding="utf-8")

    print(f"[booster] {note}: {len(merged_profiles)} profiles, {len(merged_chunks)} chunks")
    return PRODUCT_PROFILES_PATH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="folder of manufacturer datasheets")
    ap.add_argument("--rewrite", action="store_true",
                    help="replace the store instead of appending")
    args = ap.parse_args()

    # load current store (best-effort)
    existing = {"product_profiles": [], "chunks": [], "documents": []}
    if PRODUCT_PROFILES_PATH.exists():
        try:
            existing["product_profiles"] = json.loads(PRODUCT_PROFILES_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    if CHUNKS_PATH.exists():
        try:
            payload = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
            existing["chunks"] = payload.get("chunks", [])
        except Exception:  # noqa: BLE001
            pass

    new_data = bulk_ingest(args.source)
    write_merged(existing, new_data, args.rewrite)


if __name__ == "__main__":
    main()
