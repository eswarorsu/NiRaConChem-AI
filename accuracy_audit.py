#!/usr/bin/env python3
"""Accuracy audit for NIRACONCHEM AI retrieval layer.
Uses the engine's OWN retrieve_product_profiles() so the benchmark reflects real behavior."""
import sys, json
sys.path.insert(0, ".")
from app.rag_store import (retrieve_product_profiles, retrieve_rag_chunks,
                           load_product_profiles, load_index)

profiles = load_product_profiles()
print("="*70)
print("PART A — DATASET DEFECT AUDIT (24 product profiles)")
print("="*70)

# 1) duplicates
seen = {}
dups = []
for p in profiles:
    key = (p.get("product_name"), p.get("category"), p.get("system_type"),
           tuple(p.get("application_areas") or []))
    seen[key] = seen.get(key, 0) + 1
print(f"\n[A1] Duplicate profile rows: {sum(v-1 for v in seen.values() if v>1)}")
for k,v in seen.items():
    if v>1:
        print(f"    x{v}: {k[0]} | {k[1]} | {k[2]} | areas={list(k[3])}")

# 2) empty areas
empty = [p for p in profiles if not (p.get("application_areas") or [])]
print(f"\n[A2] Profiles with EMPTY application_areas ({len(empty)}):")
for p in empty:
    print(f"    - {p.get('product_name')} [{p.get('category')}]")

# 3) strength pollution: 'roof waterproofing' on non-waterproofing
polluted = [p for p in profiles if "roof waterproofing" in (p.get("climate_strengths") or [])
           and p.get("category") != "waterproofing"]
print(f"\n[A3] Non-waterproofing items claiming 'roof waterproofing' strength ({len(polluted)}):")
for p in polluted:
    print(f"    - {p.get('product_name')} [{p.get('category')}] areas={p.get('application_areas')}")

# 4) mislabeled 'roof' area on non-roof-intended categories
roof_mis = [p for p in profiles if "roof" in (p.get("application_areas") or [])
            and p.get("category") in ("repair","sealant","coating")]
print(f"\n[A4] repair/sealant/coating tagged with 'roof' area ({len(roof_mis)}):")
for p in roof_mis:
    print(f"    - {p.get('product_name')} [{p.get('category')}] areas={p.get('application_areas')}")

# 5) category coverage
from collections import Counter
cov = Counter(p.get("category") for p in profiles)
print(f"\n[A5] Category coverage: {dict(cov)}")
print("    -> tile adhesive / grout products present? ",
      any('tile' in (p.get('category') or '').lower() or 'adhesive' in (p.get('category') or '').lower() for p in profiles))

print()
print("="*70)
print("PART B — RETRIEVAL BENCHMARK (realistic UAE/GCC queries)")
print("="*70)

# Each test: query, expected category, expected area (None = any)
tests = [
    ("Dubai basement waterproofing against hydrostatic pressure", "waterproofing", "basement"),
    ("roof waterproofing membrane for villa rooftop", "waterproofing", "roof"),
    ("balcony waterproofing in Abu Dhabi", "waterproofing", "balcony"),
    ("swimming pool waterproofing wet area", "waterproofing", "wet area"),
    ("epoxy floor coating for parking deck with vehicle traffic", "flooring", "parking"),
    ("joint sealant for expansion joint on roof", "sealant", "joint"),
    ("concrete repair mortar for honeycomb spall", "repair", "concrete repair"),
    ("water tank potable protective coating", "coating", "water tank"),
    ("tile adhesive for fixing tiles on concrete substrate", "tile adhesive", None),
    ("crack injection resin for structural crack", "repair", None),
    ("Sharjah terrace waterproofing UV exposure", "waterproofing", None),
    ("industrial floor epoxy with chemical resistance", "flooring", None),
]

def relevant(p, exp_cat, exp_area):
    cat_ok = (p.get("category") == exp_cat)
    if not cat_ok:
        return False
    if exp_area is None:
        return True
    areas = p.get("application_areas") or []
    return (exp_area in areas) or (len(areas) == 0)  # empty-area products can be relevant by cat

p1_correct = 0
recall3 = 0
coverage_gap = []
for q, ec, ea in tests:
    res = retrieve_product_profiles(q, limit=3)
    top1 = res[0] if res else None
    has_rel = any(relevant(r, ec, ea) for r in res)
    top1_rel = (top1 is not None and relevant(top1, ec, ea))
    p1_correct += int(top1_rel)
    recall3 += int(has_rel)
    flag = "" if has_rel else "   <-- NO RELEVANT IN TOP3"
    if not has_rel:
        coverage_gap.append((q, ec, ea))
    print(f"\nQ: {q}")
    print(f"   expect cat={ec} area={ea}  -> top1={'OK' if top1_rel else 'WRONG'}")
    for i, r in enumerate(res,1):
        mark = "✓" if relevant(r, ec, ea) else "✗"
        print(f"    {mark} #{i} {r.get('product_name'):38s} [{r.get('category')}] areas={r.get('application_areas')} score={r.get('match_score')}")
    print(f"    {flag}")

print("\n" + "="*70)
print("PART C — SCORECARD")
print("="*70)
n = len(tests)
print(f"Top-1 category/area correctness : {p1_correct}/{n}  ({100*p1_correct/n:.0f}%)")
print(f"Recall@3 (relevant in top 3)   : {recall3}/{n}  ({100*recall3/n:.0f}%)")
if coverage_gap:
    print("Coverage gaps (no relevant product retrievable):")
    for q,ec,ea in coverage_gap:
        print(f"   - {q}  [want {ec}/{ea}]")
