import qconMarketData from "../data/qcon-market-products.json";
import type { ChatResponse, MarketProduct } from "./types";

/** Local ranking over the scraped QCON catalog. Runs in the browser: the market
 *  view is a filter over data the page already has, not another round trip. */

export function tokenizeMarketText(value: string) {
  const normalized = value
    .toLowerCase()
    .replace(/\bwater\s+proof(?:ing)?\b/g, "waterproofing")
    .replace(/\bfix(?:ing)?\s+tiles?\b/g, "tile adhesive")
    .replace(/\btiles?\s+fix(?:ing)?\b/g, "tile adhesive")
    .replace(/\btails?\b/g, "tiles")
    .replace(/\bconcrate\b/g, "concrete");

  const terms = normalized
    .split(/[^a-z0-9]+/)
    .filter((term) => term.length > 2);

  if (normalized.includes("waterproof") || normalized.includes("leak") || normalized.includes("bathroom") || normalized.includes("basement") || normalized.includes("roof")) {
    terms.push("waterproof", "waterproofing", "membrane", "sealant", "primer", "coating", "roof", "basement", "wet", "tank", "pool");
  }
  if (normalized.includes("floor") || normalized.includes("parking") || normalized.includes("traffic") || normalized.includes("warehouse")) {
    terms.push("flooring", "floor", "coating", "screed", "epoxy", "polyurethane", "deck");
  }
  if (normalized.includes("tile") || normalized.includes("adhesive") || normalized.includes("grout")) {
    terms.push("tile", "tiles", "adhesive", "grout", "sealer", "primer", "porcelain", "ceramic");
  }
  if (normalized.includes("repair") || normalized.includes("crack") || normalized.includes("honeycomb") || normalized.includes("spall")) {
    terms.push("repair", "concrete", "mortar", "grout", "crack", "epoxy");
  }
  if (normalized.includes("joint") || normalized.includes("sealant") || normalized.includes("expansion")) {
    terms.push("joint", "sealant", "polyurethane", "backer", "primer");
  }

  return [...new Set(terms)];
}

export function scoreMarketProduct(product: MarketProduct, searchText: string) {
  const terms = tokenizeMarketText(searchText);
  const name = product.name.toLowerCase();
  const category = product.category.toLowerCase();
  const description = product.description.toLowerCase();
  const keywordText = product.keywords.join(" ");
  const brand = `${product.brand} ${product.company}`.toLowerCase();

  return terms.reduce((score, term) => {
    if (name.includes(term)) return score + 7;
    if (category.includes(term)) return score + 5;
    if (brand.includes(term)) return score + 3;
    if (keywordText.includes(term)) return score + 3;
    if (description.includes(term)) return score + 2;
    return score;
  }, 0);
}

const ALL_PRODUCTS = qconMarketData.products as MarketProduct[];

/** Ranked matches for the conversation so far, falling back to a stable slice
 *  of the catalog when nothing scores. */
export function selectMarketProducts(searchText: string): MarketProduct[] {
  const ranked = ALL_PRODUCTS.map((product) => ({
    product,
    score: scoreMarketProduct(product, searchText),
  }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || a.product.name.localeCompare(b.product.name))
    .slice(0, 12)
    .map(({ product }) => product);

  return ranked.length ? ranked : ALL_PRODUCTS.slice(0, 8);
}

/** The text the ranking reads: what the user asked, what the assistant replied,
 *  and any structured requirements the backend resolved. */
export function marketSearchText(
  latestUserMessage: string,
  latestChat: ChatResponse | null,
): string {
  return [
    latestUserMessage,
    latestChat?.reply || "",
    latestChat ? Object.values(latestChat.requirements).filter(Boolean).join(" ") : "",
  ].join(" ");
}
