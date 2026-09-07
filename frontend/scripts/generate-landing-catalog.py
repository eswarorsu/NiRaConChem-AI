import json, io, re

SRC = "data/vector_store/product_profiles.json"
OUT = "frontend/app/components/landing/catalog.data.ts"

WANT = [
    "Sikalastic®-841 ST",
    "Sikafloor®-2200",
    "Sika MonoTop®-620 AE",
    "Sikagard®-550 W Elastic (G)",
    "Sikaflex®-11 FC+",
]

profiles = json.load(open(SRC, encoding="utf-8"))
by_name = {}
for p in profiles:
    n = p.get("product_name")
    if n and n not in by_name and p.get("performance"):
        by_name[n] = p

picked = []
for name in WANT:
    p = by_name.get(name)
    if not p:
        raise SystemExit("missing product: " + name)
    perf = {k: v for k, v in (p.get("performance") or {}).items() if v}
    picked.append({
        "name": p["product_name"],
        "manufacturer": p.get("manufacturer") or "",
        "tagline": p.get("tagline") or "",
        "description": p.get("description") or "",
        "usage": p.get("usage") or "",
        "systemType": p.get("system_type") or "",
        "category": p.get("category") or "",
        "applicationAreas": p.get("application_areas") or [],
        "climateStrengths": p.get("climate_strengths") or [],
        "performance": perf,
        "documents": p.get("documents_available") or [],
        "productUrl": p.get("product_url") or "",
        "datasheetUrl": p.get("datasheet_url") or "",
        "country": p.get("country") or "",
    })

market = json.load(open("frontend/app/data/qcon-market-products.json", encoding="utf-8"))
brands = json.load(open("frontend/public/brands/manifest.json", encoding="utf-8"))

counts = {
    "profiles": len(profiles),
    "marketProducts": market.get("productCount") or len(market["products"]),
    "marketCategories": len({p["category"] for p in market["products"]}),
    "brandLogos": len(brands["logos"]),
}

header = '''/**
 * catalog.data.ts — GENERATED, do not hand-edit.
 *
 * Every value below is copied verbatim out of the application's own catalog:
 *   - product records  ->  data/vector_store/product_profiles.json
 *   - market counts    ->  app/data/qcon-market-products.json
 *   - brand logo count ->  public/brands/manifest.json
 *
 * Nothing here is written by hand, so the landing page cannot state a
 * manufacturer claim, certification or performance figure that the platform
 * does not actually hold. Regenerate with scripts/generate-landing-catalog.py.
 */

export type CatalogPerformance = Record<string, string>;

export type CatalogProduct = {
  name: string;
  manufacturer: string;
  tagline: string;
  description: string;
  usage: string;
  systemType: string;
  category: string;
  applicationAreas: string[];
  climateStrengths: string[];
  performance: CatalogPerformance;
  documents: string[];
  productUrl: string;
  datasheetUrl: string;
  country: string;
};

'''

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(header)
    f.write("export const CATALOG_COUNTS = " + json.dumps(counts, indent=2) + " as const;\n\n")
    f.write("export const CATALOG_PRODUCTS: CatalogProduct[] = " + json.dumps(picked, indent=2, ensure_ascii=False) + ";\n")

print("wrote", OUT, counts)
