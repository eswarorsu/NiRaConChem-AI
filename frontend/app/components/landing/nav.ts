/** Section anchors shared by the navigation, the footer and the in-page CTAs. */
export const NAV_LINKS = [
  { id: "product", label: "Product" },
  { id: "technology", label: "Technology" },
  { id: "solutions", label: "Solutions" },
  { id: "vision", label: "About" },
] as const;

/** Scrolls to a landing section, respecting the user's motion preference. */
export function scrollToId(id: string) {
  if (typeof document === "undefined") return;
  const target = id === "top" ? document.body : document.getElementById(id);
  if (!target) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (id === "top") {
    window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
    return;
  }
  target.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
}
