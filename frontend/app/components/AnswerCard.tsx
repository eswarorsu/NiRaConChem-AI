"use client";

import { Fragment, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, BookOpen, ChevronDown, FlaskConical, ListOrdered } from "lucide-react";

/* ------------------------------------------------------------------ *
 * Types — mirrors backend/app/answer_schema.py
 * ------------------------------------------------------------------ */
export type StructuredProduct = {
  name: string;
  role?: string;
  manufacturer?: string;
  why?: string;
  citations?: string[];
};

export type StructuredClaim = {
  statement: string;
  citations?: string[];
};

export type StructuredCitation = {
  id: string;
  label: string;
  kind?: string;
  product?: string;
  url?: string | null;
};

export type StructuredAnswer = {
  answer_type?: string;
  summary?: string;
  confidence?: "high" | "medium" | "low";
  confidence_reason?: string;
  recommended_system?: string | null;
  products?: StructuredProduct[];
  claims?: StructuredClaim[];
  application_steps?: string[];
  application_notes?: string[];
  precautions?: string[];
  missing_information?: string[];
  unverified?: string[];
  follow_up?: string | null;
  citations?: StructuredCitation[];
  retrieval?: Record<string, unknown>;
  validation?: Record<string, unknown>;
};

/* ------------------------------------------------------------------ *
 * Chemistry + product highlighting
 *
 * Terms come from two places: the answer's own product names (exact, so no
 * guessing) and a fixed vocabulary of material chemistry. Matches render as
 * <strong class="chem-term">, which the stylesheet sets to uppercase — the
 * underlying text keeps its real casing so copy/paste stays faithful.
 * ------------------------------------------------------------------ */
const CHEMISTRY_TERMS = [
  "epoxy polysulfide",
  "epoxy polysulphide",
  "polysulfide",
  "polysulphide",
  "polyurethane",
  "polyurea",
  "polyolefin",
  "isocyanate",
  "polycarboxylate",
  "lignosulphonate",
  "methacrylate",
  "cementitious",
  "bituminous",
  "bitumen",
  "elastomeric",
  "acrylic",
  "silicone",
  "siloxane",
  "silane",
  "epoxy",
  "epoxide",
  "latex",
  "styrene",
  "portland cement",
  "silica fume",
  "fly ash",
  "microsilica",
  "superplasticiser",
  "superplasticizer",
  "plasticiser",
  "plasticizer",
  "calcium nitrate",
  "sodium silicate",
  "quartz",
  "chloride",
  "sulphate",
  "sulfate",
  "alkali",
  "resin",
  "PVC",
  "FPO",
  "TPO",
  "EPDM",
  "MMA",
  "PU",
];

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Strip trademark marks so "Sikagard®-1816" also matches "Sikagard-1816". */
function stripMarks(value: string) {
  return value.replace(/[®™©]/g, "").replace(/\s+/g, " ").trim();
}

function buildTermPattern(productNames: string[]): RegExp | null {
  const terms = new Set<string>();
  productNames.forEach((name) => {
    const trimmed = (name || "").trim();
    if (trimmed.length < 3) return;
    terms.add(trimmed);
    const stripped = stripMarks(trimmed);
    if (stripped.length >= 3) terms.add(stripped);
  });
  CHEMISTRY_TERMS.forEach((term) => terms.add(term));

  const sorted = Array.from(terms).sort((a, b) => b.length - a.length);
  if (!sorted.length) return null;

  // \b fails against a leading "(" or a trailing "+", so the boundaries are
  // written as "not a word character" lookarounds instead.
  const body = sorted.map(escapeRegExp).join("|");
  try {
    return new RegExp(`(?<![A-Za-z0-9])(${body})(?![A-Za-z0-9])`, "gi");
  } catch {
    return new RegExp(`(${body})`, "gi");
  }
}

function highlight(text: string, pattern: RegExp | null, keyPrefix: string): ReactNode {
  if (!text) return null;
  if (!pattern) return text;
  pattern.lastIndex = 0;

  const nodes: ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  let index = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) nodes.push(text.slice(cursor, match.index));
    nodes.push(
      <strong className="chem-term" key={`${keyPrefix}-${index}`}>
        {match[0]}
      </strong>,
    );
    cursor = match.index + match[0].length;
    index += 1;
    if (match[0].length === 0) pattern.lastIndex += 1;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes.length ? nodes : text;
}

/* ------------------------------------------------------------------ *
 * Card
 * ------------------------------------------------------------------ */
const CONFIDENCE_COPY: Record<string, string> = {
  high: "Backed by a strong match in the indexed datasheets.",
  medium: "Partly supported — check the cited datasheets before specifying.",
  low: "Weak match. Treat as a starting point, not a specification.",
};

export default function AnswerCard({
  answer,
  showCursor = false,
}: {
  answer: StructuredAnswer;
  showCursor?: boolean;
}) {
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const products = answer.products ?? [];
  const claims = answer.claims ?? [];
  const steps = answer.application_steps ?? answer.application_notes ?? [];
  const precautions = answer.precautions ?? [];
  const missing = answer.missing_information ?? [];
  const citations = answer.citations ?? [];
  const unverifiedCount = (answer.unverified ?? []).length;

  const pattern = useMemo(() => {
    const names = [
      ...products.map((product) => product.name),
      ...citations.map((citation) => citation.product || ""),
    ].filter(Boolean);
    return buildTermPattern(names);
  }, [products, citations]);

  const confidence = answer.confidence ?? "low";

  return (
    <div className="answer-card">
      {answer.summary ? (
        <p className="answer-summary">
          {highlight(answer.summary, pattern, "summary")}
          {showCursor ? <span className="typing-cursor" aria-hidden="true" /> : null}
        </p>
      ) : null}

      {products.length ? (
        <section className="answer-block">
          <h4 className="answer-block-title">
            <FlaskConical size={13} strokeWidth={2.4} aria-hidden="true" />
            Recommended
            {answer.recommended_system ? (
              <span className="answer-block-note">{answer.recommended_system}</span>
            ) : null}
          </h4>
          <ul className="answer-products">
            {products.map((product, index) => (
              <li className="answer-product" key={`${product.name}-${index}`}>
                <div className="answer-product-head">
                  <strong className="chem-term">{stripMarks(product.name)}</strong>
                  {product.manufacturer ? (
                    <span className="answer-product-brand">{product.manufacturer}</span>
                  ) : null}
                  {product.role && product.role !== "primary" ? (
                    <span className="answer-role-tag">{product.role}</span>
                  ) : null}
                </div>
                {product.why ? (
                  <p className="answer-product-why">{highlight(product.why, pattern, `why-${index}`)}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {steps.length ? (
        <section className="answer-block">
          <h4 className="answer-block-title">
            <ListOrdered size={13} strokeWidth={2.4} aria-hidden="true" />
            Application steps
          </h4>
          <ol className="answer-steps">
            {steps.map((step, index) => (
              <li className="answer-step" key={`step-${index}`}>
                <span className="answer-step-index" aria-hidden="true">
                  {index + 1}
                </span>
                <span className="answer-step-text">{highlight(step, pattern, `step-${index}`)}</span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {claims.length ? (
        <section className="answer-block">
          <h4 className="answer-block-title">
            <BookOpen size={13} strokeWidth={2.4} aria-hidden="true" />
            From the datasheets
          </h4>
          <ul className="answer-claims">
            {claims.map((claim, index) => (
              <li key={`claim-${index}`}>
                {highlight(claim.statement, pattern, `claim-${index}`)}
                {claim.citations?.length ? (
                  <span className="answer-cite">{claim.citations.join(" ")}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {precautions.length ? (
        <section className="answer-block answer-block-warning">
          <h4 className="answer-block-title">
            <AlertTriangle size={13} strokeWidth={2.4} aria-hidden="true" />
            Precautions
          </h4>
          <ul className="answer-precautions">
            {precautions.map((note, index) => (
              <li key={`precaution-${index}`}>{highlight(note, pattern, `prec-${index}`)}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {missing.length ? (
        <section className="answer-block">
          <h4 className="answer-block-title">Tell me this and I can firm it up</h4>
          <ul className="answer-missing">
            {missing.map((item, index) => (
              <li key={`missing-${index}`}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {answer.follow_up ? <p className="answer-followup">{answer.follow_up}</p> : null}

      <footer className="answer-footer">
        <span className={`answer-confidence answer-confidence-${confidence}`} title={CONFIDENCE_COPY[confidence]}>
          <span className="answer-confidence-dot" aria-hidden="true" />
          {confidence} confidence
        </span>

        {unverifiedCount ? (
          <span className="answer-unverified" title="Statements the assistant could not trace to an indexed datasheet were removed.">
            {unverifiedCount} unverified statement{unverifiedCount > 1 ? "s" : ""} removed
          </span>
        ) : null}

        {citations.length ? (
          <button
            aria-expanded={sourcesOpen}
            className="answer-sources-toggle"
            onClick={() => setSourcesOpen((open) => !open)}
            type="button"
          >
            <ChevronDown className={sourcesOpen ? "is-open" : ""} size={13} strokeWidth={2.4} aria-hidden="true" />
            {citations.length} source{citations.length > 1 ? "s" : ""}
          </button>
        ) : null}
      </footer>

      {sourcesOpen && citations.length ? (
        <ul className="answer-sources">
          {citations.map((citation) => (
            <li key={citation.id}>
              <span className="answer-cite">{citation.id}</span>
              {citation.url ? (
                <a href={citation.url} rel="noreferrer noopener" target="_blank">
                  {citation.label}
                </a>
              ) : (
                <Fragment>{citation.label}</Fragment>
              )}
            </li>
          ))}
        </ul>
      ) : null}

      {answer.confidence_reason ? (
        <p className="answer-confidence-reason">{answer.confidence_reason}</p>
      ) : null}
    </div>
  );
}
