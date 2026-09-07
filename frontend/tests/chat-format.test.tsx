import { describe, expect, it } from "vitest";

import { isConstructionRelatedQuery, normalizeChatReply } from "../app/lib/chat-format";

describe("isConstructionRelatedQuery", () => {
  it("recognises site language", () => {
    expect(isConstructionRelatedQuery("I need waterproofing for a roof")).toBe(true);
    expect(isConstructionRelatedQuery("epoxy floor in a warehouse")).toBe(true);
    expect(isConstructionRelatedQuery("Dubai basement hydrostatic pressure")).toBe(true);
  });

  it("does not claim an unrelated question is a project query", () => {
    expect(isConstructionRelatedQuery("what is the weather today")).toBe(false);
    expect(isConstructionRelatedQuery("hello")).toBe(false);
  });

  it("is case and whitespace insensitive", () => {
    expect(isConstructionRelatedQuery("   WATERPROOFING  ")).toBe(true);
  });
});

describe("normalizeChatReply", () => {
  it("passes a genuine answer through untouched, even one containing prices", () => {
    const reply = "Use a liquid-applied membrane. Typical cost is AED 1,200 per drum.";
    expect(normalizeChatReply(reply, "roof waterproofing")).toBe(reply);
  });

  it("replaces the legacy inert template rather than showing it to the user", () => {
    const legacy = "Next Details Needed\n- application area";
    const out = normalizeChatReply(legacy, "roof waterproofing");
    expect(out).not.toBe(legacy);
    expect(out).toContain("Waterproofing");
  });
});
