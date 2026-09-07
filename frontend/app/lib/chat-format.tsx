import { Fragment, type ReactNode } from "react";

/** Query classification and assistant-reply rendering. Pure functions, no state
 *  and no side effects, so they are trivial to reason about and to test. */

const broadTerms = ["waterproofing", "flooring", "repair", "coating", "sealant", "tile adhesive", "chemical"];
const areaTerms = ["roof", "rooftop", "basement", "bathroom", "wet", "parking", "floor", "joint", "tank", "pool", "wall", "slab", "villa"];
const exposureTerms = ["uv", "heat", "traffic", "chemical", "chloride", "coastal", "water", "pressure", "potable", "external", "interior", "crack"];
const substrateTerms = ["concrete", "screed", "tile", "metal", "block", "masonry", "plaster"];
const constructionTerms = [
  ...broadTerms,
  ...areaTerms,
  ...exposureTerms,
  ...substrateTerms,
  "construction",
  "building",
  "site",
  "project",
  "datasheet",
  "specification",
  "membrane",
  "epoxy",
  "polyurethane",
  "cementitious",
  "grout",
  "anchor",
  "adhesive",
  "joint",
  "waterproof",
];

export function includesAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

export function isConstructionRelatedQuery(value: string) {
  const normalized = value.toLowerCase().trim();
  return includesAny(normalized, constructionTerms);
}

export function inferNaturalChatReply(query: string) {
  const normalized = query.toLowerCase();
  const sections: { title: string; guidance: string[] }[] = [];

  if (normalized.includes("tile") || normalized.includes("adhesive") || normalized.includes("grout") || normalized.includes("fix")) {
    sections.push({
      title: "Tile Fixing / Grouting",
      guidance: [
        "clean the surface and remove dust, oil, weak plaster, or laitance",
        "use the correct installation method for the selected material",
        "allow the installed system to cure as required by the datasheet",
      ],
    });
  }

  if (normalized.includes("water") || normalized.includes("leak") || normalized.includes("roof") || normalized.includes("basement") || normalized.includes("bathroom") || normalized.includes("pool") || normalized.includes("tank")) {
    sections.push({
      title: "Waterproofing",
      guidance: [
        "confirm whether the water pressure is positive, negative, or hydrostatic",
        "treat cracks, corners, pipe penetrations, and construction joints first",
        "check required thickness, coverage, curing, and test requirements",
      ],
    });
  }

  if (normalized.includes("floor") || normalized.includes("parking") || normalized.includes("traffic") || normalized.includes("warehouse") || normalized.includes("epoxy") || normalized.includes("pu")) {
    sections.push({
      title: "Flooring / Coating",
      guidance: [
        "check concrete moisture, surface strength, and contamination before coating",
        "select the system by traffic load, UV, exposure, and slip resistance",
        "prepare the surface as required by the datasheet",
      ],
    });
  }

  if (normalized.includes("repair") || normalized.includes("crack") || normalized.includes("honeycomb") || normalized.includes("spall")) {
    sections.push({
      title: "Concrete Repair",
      guidance: [
        "remove loose concrete and clean reinforcement before repair",
        "confirm whether cracks are active, dormant, structural, or non-structural",
        "cure repair mortar correctly, especially in hot site conditions",
      ],
    });
  }

  if (normalized.includes("joint") || normalized.includes("sealant") || normalized.includes("expansion")) {
    sections.push({
      title: "Sealant / Joint Treatment",
      guidance: [
        "confirm joint width, depth, movement, and exposure",
        "clean and prime joint faces before sealant application",
        "use backer rod to control sealant depth and avoid three-side adhesion",
      ],
    });
  }

  const selected = sections.length
    ? sections
    : [
        {
          title: "Construction Chemical Selection",
          guidance: [
            "confirm the application area, substrate, exposure, and location",
            "match the product category to the actual site condition",
            "verify the final selection against the datasheet",
          ],
        },
      ];

  const first = selected[0];
  return [
    `Based on your query, this looks like a ${selected.map((section) => section.title).join(" + ")} requirement.`,
    "Next Details Needed\n- application area\n- substrate\n- exposure condition\n- project location",
    `Application Notes\n${first.guidance.map((item) => `- ${item}`).join("\n")}`,
    "MARKET RESULT is ready for matched options. The chat will only handle project inputs and guidance.",
  ].join("\n\n");
}

export function normalizeChatReply(reply: string, query: string) {
  // Only rewrite the legacy inert template. Detect it by its exact signature so
  // genuine RAG answers (which legitimately contain numbered lists, AED prices,
  // or URLs) are shown verbatim instead of being replaced with canned text.
  const isLegacyTemplate =
    reply.includes("MARKET RESULT is ready for matched options") ||
    reply.includes("Next Details Needed");
  if (isLegacyTemplate) {
    return inferNaturalChatReply(query);
  }
  return reply;
}

/** Minimal inline markdown: **bold** and *italic*. The backend renders its answers
 *  as markdown, and the previous plain-text renderer showed the asterisks verbatim. */
export function renderInline(text: string, keyPrefix: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  if (parts.length === 1) return text;
  return parts.map((part, index) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={`${keyPrefix}-${index}`}>{part.slice(2, -2)}</strong>
    ) : (
      <Fragment key={`${keyPrefix}-${index}`}>{part}</Fragment>
    ),
  );
}

export function renderAssistantContent(content: string, showCursor: boolean) {
  const blocks = content.split(/\n{2,}/).filter((block) => block.trim());

  return (
    <div className="chat-answer">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n").filter((line) => line.trim());
        const isList = lines.every((line) => /^[-*•]\s+/.test(line.trim()));
        const hasHeadingWithList = lines.length > 1 && !/^[-*•]\s+/.test(lines[0].trim()) && lines.slice(1).every((line) => /^[-*•]\s+/.test(line.trim()));

        if (isList) {
          return (
            <ul className="chat-answer-list" key={`${block}-${blockIndex}`}>
              {lines.map((line, lineIndex) => (
                <li key={`${line}-${lineIndex}`}>
                  {renderInline(line.replace(/^[-*•]\s+/, ""), `li-${lineIndex}`)}
                </li>
              ))}
            </ul>
          );
        }

        if (hasHeadingWithList) {
          return (
            <section className="chat-answer-section" key={`${block}-${blockIndex}`}>
              <strong>{renderInline(lines[0], `head-${blockIndex}`)}</strong>
              <ul className="chat-answer-list">
                {lines.slice(1).map((line, lineIndex) => (
                  <li key={`${line}-${lineIndex}`}>
                    {renderInline(line.replace(/^[-*•]\s+/, ""), `sli-${lineIndex}`)}
                  </li>
                ))}
              </ul>
              {showCursor && blockIndex === blocks.length - 1 ? <span className="typing-cursor" aria-hidden="true" /> : null}
            </section>
          );
        }

        const text = lines.join(" ");
        const [label, ...rest] = text.split(":");
        const hasShortLabel = rest.length > 0 && label.length <= 34;

        return (
          <p className={blockIndex === 0 ? "chat-answer-lead" : ""} key={`${text}-${blockIndex}`}>
            {hasShortLabel ? (
              <>
                <strong>{renderInline(label, `lbl-${blockIndex}`)}:</strong>
                {renderInline(rest.join(":"), `rest-${blockIndex}`)}
              </>
            ) : (
              renderInline(text, `txt-${blockIndex}`)
            )}
            {showCursor && blockIndex === blocks.length - 1 ? <span className="typing-cursor" aria-hidden="true" /> : null}
          </p>
        );
      })}
      {showCursor && blocks.length === 0 ? <span className="typing-cursor" aria-hidden="true" /> : null}
    </div>
  );
}
