import { describe, expect, it } from "vitest";

import { scoreMarketProduct, tokenizeMarketText } from "../app/lib/market";
import type { MarketProduct } from "../app/lib/types";

function product(overrides: Partial<MarketProduct> = {}): MarketProduct {
  return {
    id: "1",
    name: "Sikalastic Roof Membrane",
    company: "QCON",
    brand: "Sika",
    category: "Products For Waterproofing",
    url: "https://example.test/p",
    imageUrl: "",
    localImage: "",
    description: "Liquid applied roof waterproofing membrane.",
    price: "AED 100",
    keywords: ["roof", "waterproofing"],
    ...overrides,
  };
}

describe("tokenizeMarketText", () => {
  it("normalises the spellings people actually type on site", () => {
    expect(tokenizeMarketText("water proofing")).toContain("waterproofing");
    expect(tokenizeMarketText("concrate slab")).toContain("concrete");
    expect(tokenizeMarketText("fixing tiles")).toContain("adhesive");
  });

  it("expands a waterproofing query into its related system terms", () => {
    const terms = tokenizeMarketText("leak in the basement");
    expect(terms).toEqual(expect.arrayContaining(["membrane", "basement", "waterproofing"]));
  });

  it("drops noise words shorter than three characters", () => {
    expect(tokenizeMarketText("a in the roof")).not.toContain("in");
  });
});

describe("scoreMarketProduct", () => {
  it("scores a matching product above a non-matching one", () => {
    const match = scoreMarketProduct(product(), "roof waterproofing membrane");
    const miss = scoreMarketProduct(
      product({
        name: "Tile Grout",
        category: "Products For Tile Stone",
        description: "Cementitious grout.",
        keywords: ["grout"],
      }),
      "roof waterproofing membrane",
    );
    expect(match).toBeGreaterThan(miss);
  });

  it("weights a name match more heavily than a description match", () => {
    const inName = scoreMarketProduct(
      product({ name: "Membrane", description: "x", keywords: [], category: "" }),
      "membrane",
    );
    const inDescription = scoreMarketProduct(
      product({ name: "x", description: "membrane", keywords: [], category: "" }),
      "membrane",
    );
    expect(inName).toBeGreaterThan(inDescription);
  });

  it("returns zero when nothing in the query relates to the product", () => {
    expect(scoreMarketProduct(product(), "xyzzy")).toBe(0);
  });
});
