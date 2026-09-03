#!/usr/bin/env python3
"""Accuracy audit for the NIRACONCHEM AI retrieval layer.

Runs against the engine's OWN retrieve_product_profiles() / retrieve_rag_chunks()
so the numbers reflect real behaviour, not a parallel re-implementation.

  PART A  dataset defect audit      (duplicates, empty fields, category pollution)
  PART B  retrieval benchmark       (40 labelled UAE/GCC queries)
  PART C  scorecard                 (Top-1, Recall@3, MRR, chunk grounding)

Run from the repo root:   python accuracy_audit.py
Optionally snapshot the result:   python accuracy_audit.py --save reports/audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from app.rag_store import (  # noqa: E402
    load_index,
    load_product_profiles,
    retrieve_product_profiles,
    retrieve_rag_chunks,
)

# --------------------------------------------------------------------------- #
# Labelled benchmark. (query, expected category, expected application area|None)
# Expected category is satisfied by profile["category"] OR membership in
# profile["categories"], so a product filed under a broader primary category still
# counts when it genuinely serves the niche.
# --------------------------------------------------------------------------- #
TESTS: list[tuple[str, str, str | None]] = [
    # --- waterproofing ---
    ("Dubai basement waterproofing against hydrostatic pressure", "waterproofing", "basement"),
    ("roof waterproofing membrane for villa rooftop", "waterproofing", "roof"),
    ("balcony waterproofing in Abu Dhabi", "waterproofing", "balcony"),
    ("swimming pool waterproofing wet area", "waterproofing", "wet area"),
    ("liquid applied waterproofing membrane for exposed roof", "waterproofing", "roof"),
    ("bituminous sheet membrane torch applied for foundation raft", "waterproofing", None),
    ("self adhesive sheet membrane for below ground structure", "waterproofing", "basement"),
    ("cementitious waterproofing mortar for water retaining structure", "waterproofing", None),
    ("integral waterproofing admixture added to the concrete mix", "waterproofing", None),
    ("waterstop for construction joint in a retaining wall", "waterproofing", "joint"),
    ("Sharjah terrace waterproofing with UV exposure", "waterproofing", None),
    ("tunnel waterproofing membrane", "waterproofing", "tunnel"),
    # --- roofing ---
    ("single ply PVC roofing membrane mechanically fastened", "waterproofing", "roof"),
    ("FPO roof membrane for a warehouse roof", "waterproofing", "roof"),
    # --- flooring ---
    ("epoxy floor coating for parking deck with vehicle traffic", "flooring", "parking"),
    ("industrial floor epoxy with chemical resistance", "flooring", "industrial floor"),
    ("self levelling screed to level an uneven concrete floor", "flooring", None),
    ("polyurethane floor coating for a food factory", "flooring", None),
    ("anti slip car park deck coating", "flooring", "parking"),
    # --- coating / protection ---
    ("anti carbonation protective coating for concrete facade", "coating", "facade"),
    ("water tank potable protective coating", "coating", "water tank"),
    ("epoxy protective coating for a chemical storage tank", "coating", None),
    ("facade wall coating for external render", "coating", "facade"),
    # --- repair ---
    ("concrete repair mortar for honeycomb spall", "repair", "concrete repair"),
    ("structural strengthening with carbon fibre plate", "repair", None),
    ("crack injection resin for structural crack", "crack injection", None),
    ("fairing coat to level a patch repaired concrete surface", "repair", None),
    ("corrosion protection primer for exposed reinforcement steel", "repair", None),
    # --- grout / anchor ---
    ("non shrink cementitious grout for machine base plate", "grout", None),
    ("epoxy anchoring adhesive for rebar into concrete", "anchor", None),
    ("free flowing grout under a steel column base", "grout", None),
    # --- sealant ---
    ("joint sealant for expansion joint on roof", "sealant", "joint"),
    ("silicone sealant for glazing and curtain wall", "sealant", None),
    ("polyurethane floor joint sealant for a warehouse", "sealant", "joint"),
    ("fire rated joint sealant", "sealant", None),
    # --- adhesive / tiling ---
    ("tile adhesive for fixing tiles on concrete substrate", "tile adhesive", None),
    ("tile grout for bathroom floor joints", "grout", None),
    ("construction adhesive for bonding new concrete to old", "adhesive", None),
    # --- admixture ---
    ("superplasticiser water reducer for ready mix concrete", "admixture", None),
    ("set retarder for hot weather concreting in Dubai", "admixture", None),
    ("shotcrete accelerator for tunnel lining", "admixture", None),
    ("curing compound for a large concrete slab", "admixture", None),
]


# A second set, written AFTER the scoring rules were tuned on TESTS above, phrased
# the way a site engineer would actually ask. It exists to catch overfitting: a big
# gap between the two sets means the rules were tuned to the benchmark, not to the
# domain. Do not tune against this set without replacing it.
HOLDOUT_TESTS: list[tuple[str, str, str | None]] = [
    ("stop water leaking through a basement wall crack", "waterproofing", None),
    ("what can I use to protect a car park soffit from carbonation", "coating", None),
    ("mortar to rebuild a broken concrete column edge", "repair", None),
    ("something to fill the gap around aluminium window frames", "sealant", None),
    ("high strength bedding material under a crane rail", "grout", None),
    ("make concrete more workable without adding water", "admixture", None),
    ("hard wearing resin floor for a workshop", "flooring", "industrial floor"),
    ("membrane under screed on a hotel bathroom floor", "waterproofing", "wet area"),
    ("fix porcelain tiles to a swimming pool wall", "adhesive", None),
    ("resin to glue steel plates onto a beam soffit", "repair", None),
    ("elastic sealant that survives 40 degree summers on a rooftop joint", "sealant", "joint"),
    ("stop rebar rusting after concrete spalling repair", "repair", None),
    ("waterproof a lift pit", "waterproofing", None),
    ("coating that reflects heat on an exposed roof slab", "waterproofing", "roof"),
    ("fibres to control shrinkage cracking in a slab pour", "admixture", None),
    ("waterproofing for a planter box", "waterproofing", None),
]


# Sub-type discrimination. Matching the `admixture` category is not enough when the
# catalog holds 389 of them - recommending an accelerator for a hot-weather pour is a
# real site error. Each entry asserts a keyword that must appear in the rank-1
# product's system_type, name or tagline.
SUBTYPE_TESTS: list[tuple[str, str]] = [
    ("superplasticiser for ready mix concrete in 45 degree heat", "water-reducing"),
    ("set retarder for hot weather concreting in Dubai", "retarding"),
    ("shotcrete accelerator for tunnel lining", "accelerating"),
    ("curing compound for a large concrete slab", "curing"),
    ("fibres to control shrinkage cracking in a slab pour", "fibre"),
    ("PVC single ply roofing membrane", "pvc"),
    ("FPO roofing membrane", "fpo"),
    ("non shrink grout under a base plate", "grout"),
    ("silicone sealant for glazing", "silicone"),
    ("self levelling epoxy floor screed", "flooring"),
]


def profile_categories(profile: dict) -> set[str]:
    labels = {profile.get("category") or ""}
    labels.update(profile.get("categories") or [])
    return {label.lower() for label in labels if label}


def relevant(profile: dict, expected_category: str, expected_area: str | None) -> bool:
    if expected_category.lower() not in profile_categories(profile):
        return False
    if expected_area is None:
        return True
    areas = profile.get("application_areas") or []
    # A product with no declared areas is not disqualified: the catalog simply
    # doesn't state a placement for it.
    return expected_area in areas or not areas


def part_a(profiles: list[dict], chunks: list[dict]) -> dict:
    print("=" * 74)
    print(f"PART A - DATASET DEFECT AUDIT ({len(profiles)} product profiles, {len(chunks)} chunks)")
    print("=" * 74)

    keys = Counter(
        (
            (p.get("product_name") or "").strip().lower(),
            p.get("manufacturer"),
            p.get("category"),
            tuple(p.get("application_areas") or []),
        )
        for p in profiles
    )
    duplicates = sum(count - 1 for count in keys.values() if count > 1)
    print(f"\n[A1] Duplicate profile rows: {duplicates}")
    for key, count in keys.items():
        if count > 1:
            print(f"    x{count}: {key[0]} | {key[2]}")

    unnamed = [p for p in profiles if not (p.get("product_name") or "").strip()]
    print(f"[A2] Profiles with no product name: {len(unnamed)}")

    empty_areas = [p for p in profiles if not (p.get("application_areas") or [])]
    print(f"[A3] Profiles with empty application_areas: {len(empty_areas)} ({100*len(empty_areas)/max(len(profiles),1):.0f}%)")

    polluted = [
        p for p in profiles
        if "roof waterproofing" in (p.get("climate_strengths") or []) and p.get("category") != "waterproofing"
    ]
    print(f"[A4] Non-waterproofing products claiming 'roof waterproofing': {len(polluted)}")
    for p in polluted[:8]:
        print(f"    - {p.get('product_name')} [{p.get('category')}]")

    roof_mis = [
        p for p in profiles
        if "roof" in (p.get("application_areas") or []) and p.get("category") in ("admixture", "grout", "anchor")
    ]
    print(f"[A5] admixture/grout/anchor tagged with a 'roof' area: {len(roof_mis)}")

    grounded = sum(1 for p in profiles if p.get("description") or p.get("usage"))
    with_perf = sum(1 for p in profiles if p.get("performance"))
    with_url = sum(1 for p in profiles if p.get("product_url") or p.get("datasheet_url"))
    print(f"\n[A6] Grounding coverage")
    print(f"    description or usage text : {grounded}/{len(profiles)}  ({100*grounded/max(len(profiles),1):.0f}%)")
    print(f"    technical performance data: {with_perf}/{len(profiles)}  ({100*with_perf/max(len(profiles),1):.0f}%)")
    print(f"    citable product/PDS link  : {with_url}/{len(profiles)}  ({100*with_url/max(len(profiles),1):.0f}%)")

    categories = Counter(p.get("category") for p in profiles)
    print(f"\n[A7] Category coverage: {dict(categories)}")
    manufacturers = Counter(p.get("manufacturer") for p in profiles)
    print(f"[A8] Manufacturers: {dict(manufacturers.most_common(8))}")

    return {
        "profiles": len(profiles),
        "chunks": len(chunks),
        "duplicates": duplicates,
        "empty_areas": len(empty_areas),
        "grounded_pct": round(100 * grounded / max(len(profiles), 1), 1),
        "categories": dict(categories),
    }


def part_b(tests: list[tuple[str, str, str | None]], label: str, verbose: bool = True) -> dict:
    print()
    print("=" * 74)
    print(f"{label} ({len(tests)} labelled queries)")
    print("=" * 74)

    top1 = 0
    recall3 = 0
    reciprocal = 0.0
    chunk_hits = 0
    gaps: list[tuple[str, str, str | None]] = []

    for query, expected_category, expected_area in tests:
        results = retrieve_product_profiles(query, limit=3)
        hit_rank = next(
            (i for i, r in enumerate(results, start=1) if relevant(r, expected_category, expected_area)),
            None,
        )
        top1 += int(hit_rank == 1)
        recall3 += int(hit_rank is not None)
        reciprocal += 1 / hit_rank if hit_rank else 0.0
        if hit_rank is None:
            gaps.append((query, expected_category, expected_area))

        chunks = retrieve_rag_chunks(query, limit=3)
        chunk_ok = any(
            expected_category.lower() in {c.lower() for c in (chunk.get("categories") or [])}
            or expected_category.lower()
            in {str(chunk.get("document_profile", {}).get("category", "")).lower()}
            for chunk in chunks
        )
        chunk_hits += int(chunk_ok)

        if verbose:
            print(f"\nQ: {query}")
            print(f"   want cat={expected_category} area={expected_area}  -> top1={'OK' if hit_rank == 1 else 'MISS'}")
            for i, r in enumerate(results, start=1):
                mark = "+" if relevant(r, expected_category, expected_area) else "-"
                print(
                    f"    {mark} #{i} {(r.get('product_name') or '')[:40]:40s} "
                    f"[{r.get('category')}] areas={r.get('application_areas')} score={r.get('match_score')}"
                )
            if not results:
                print("      (no profiles retrieved)")
            print(f"    chunk grounding: {'OK' if chunk_ok else 'MISS'}")

    n = len(tests)
    return {
        "queries": n,
        "top1": top1,
        "top1_pct": round(100 * top1 / n, 1),
        "recall3": recall3,
        "recall3_pct": round(100 * recall3 / n, 1),
        "mrr": round(reciprocal / n, 3),
        "chunk_grounding": chunk_hits,
        "chunk_grounding_pct": round(100 * chunk_hits / n, 1),
        "gaps": [{"query": q, "category": c, "area": a} for q, c, a in gaps],
    }


def part_b3(verbose: bool = True) -> dict:
    print()
    print("=" * 74)
    print(f"PART B3 - SUB-TYPE DISCRIMINATION ({len(SUBTYPE_TESTS)} queries)")
    print("=" * 74)
    hits = 0
    misses = []
    for query, keyword in SUBTYPE_TESTS:
        results = retrieve_product_profiles(query, limit=1)
        top = results[0] if results else {}
        haystack = " ".join(
            str(top.get(field) or "") for field in ("system_type", "product_name", "tagline", "category")
        ).lower()
        ok = keyword.lower() in haystack
        hits += int(ok)
        if not ok:
            misses.append((query, keyword, top.get("product_name"), top.get("system_type")))
        if verbose:
            print(f"  {'OK  ' if ok else 'MISS'} {query}")
            print(f"        -> {top.get('product_name')} | {top.get('system_type')}")
    n = len(SUBTYPE_TESTS)
    return {
        "queries": n,
        "hits": hits,
        "hits_pct": round(100 * hits / n, 1),
        "misses": [
            {"query": q, "wanted": k, "got": name, "system_type": st} for q, k, name, st in misses
        ],
    }


def part_c(dataset: dict, retrieval: dict, holdout: dict, subtype: dict) -> None:
    print()
    print("=" * 74)
    print("PART C - SCORECARD")
    print("=" * 74)
    n = retrieval["queries"]
    print(f"Profiles indexed               : {dataset['profiles']}")
    print(f"RAG chunks indexed             : {dataset['chunks']}")
    print(f"Profiles with grounding text   : {dataset['grounded_pct']}%")
    print(f"Top-1 category/area correctness: {retrieval['top1']}/{n}  ({retrieval['top1_pct']}%)")
    print(f"Recall@3                       : {retrieval['recall3']}/{n}  ({retrieval['recall3_pct']}%)")
    print(f"MRR@3                          : {retrieval['mrr']}")
    print(f"Chunk grounding hit rate       : {retrieval['chunk_grounding']}/{n}  ({retrieval['chunk_grounding_pct']}%)")
    print()
    m = holdout["queries"]
    print(f"HELD-OUT Top-1                 : {holdout['top1']}/{m}  ({holdout['top1_pct']}%)")
    print(f"HELD-OUT Recall@3              : {holdout['recall3']}/{m}  ({holdout['recall3_pct']}%)")
    print(f"HELD-OUT MRR@3                 : {holdout['mrr']}")
    print(f"Sub-type discrimination        : {subtype['hits']}/{subtype['queries']}  ({subtype['hits_pct']}%)")
    for miss in subtype["misses"]:
        print(f"   - {miss['query']}  wanted '{miss['wanted']}', got {miss['got']} ({miss['system_type']})")
    for name, block in (("benchmark", retrieval), ("held-out", holdout)):
        if block["gaps"]:
            print(f"\nCoverage gaps in the {name} set (nothing relevant in top 3):")
            for gap in block["gaps"]:
                print(f"   - {gap['query']}  [want {gap['category']}/{gap['area']}]")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", help="write the scorecard as JSON to this path")
    parser.add_argument("--quiet", action="store_true", help="scorecard only, no per-query detail")
    args = parser.parse_args()

    profiles = load_product_profiles()
    chunks = load_index()
    dataset = part_a(profiles, chunks)
    retrieval = part_b(TESTS, "PART B - RETRIEVAL BENCHMARK", verbose=not args.quiet)
    holdout = part_b(HOLDOUT_TESTS, "PART B2 - HELD-OUT SET", verbose=not args.quiet)
    subtype = part_b3(verbose=not args.quiet)
    part_c(dataset, retrieval, holdout, subtype)

    if args.save:
        out = ROOT / args.save
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {"dataset": dataset, "retrieval": retrieval, "holdout": holdout, "subtype": subtype},
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nSaved scorecard -> {out}")


if __name__ == "__main__":
    main()
