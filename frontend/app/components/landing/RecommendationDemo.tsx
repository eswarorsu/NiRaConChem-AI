"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, Check } from "@phosphor-icons/react";
import { CATALOG_PRODUCTS } from "./catalog.data";
import { usePrefersReducedMotion, useReveal } from "../../lib/hooks";
import { inView, riseIn, stagger } from "../../lib/motion";

const QUERY =
  "Recommend a waterproofing solution for a concrete roof exposed to high temperatures and heavy rainfall.";

/* Read straight off the demonstration query above — these are the project
   conditions the sentence states, not claims about any product. */
const PARSED = [
  { k: "Application", v: "Waterproofing" },
  { k: "Substrate", v: "Concrete" },
  { k: "Area", v: "Roof" },
  { k: "Exposure", v: "High temperature · Heavy rainfall" },
];

const STEPS = [
  "Analyzing requirements",
  "Searching product knowledge",
  "Matching technical properties",
  "Evaluating application compatibility",
];

/* The demonstration answers with a real record from the product index rather
   than an invented one, and every line under "why it matches" is read off that
   record — no performance number is written by hand. */
const MATCH = CATALOG_PRODUCTS[0];

/** "shore_d_hardness" -> "Shore D hardness" — the same shape the product
 *  console uses, so a performance key reads the same wherever it appears. */
function humanise(key: string) {
  return key
    .split("_")
    .map((word, index) => {
      if (word.length <= 2) return word.toUpperCase();
      return index === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word;
    })
    .join(" ");
}

type Phase = "typing" | "processing" | "result";

export default function RecommendationDemo({ onTryAi }: { onTryAi: () => void }) {
  const [stageRef, stageIn] = useReveal<HTMLDivElement>({ threshold: 0.28 });
  const reducedMotion = usePrefersReducedMotion();

  const [typed, setTyped] = useState("");
  const [phase, setPhase] = useState<Phase>("typing");
  const [step, setStep] = useState(-1);

  // The sequence runs only while the section is on screen. Under reduced motion
  // it never runs at all — the finished state is derived below rather than
  // written into state from an effect, which would cost a cascading render.
  useEffect(() => {
    if (!stageIn || reducedMotion) return;

    let cancelled = false;
    const timers: number[] = [];

    function run() {
      setTyped("");
      setStep(-1);
      setPhase("typing");

      let index = 0;
      const typer = window.setInterval(() => {
        if (cancelled) return;
        index += 2;
        setTyped(QUERY.slice(0, index));
        if (index >= QUERY.length) {
          window.clearInterval(typer);
          setPhase("processing");
          STEPS.forEach((_, stepIndex) => {
            timers.push(
              window.setTimeout(() => {
                if (!cancelled) setStep(stepIndex);
              }, 420 + stepIndex * 760),
            );
          });
          timers.push(
            window.setTimeout(() => {
              if (!cancelled) {
                setStep(STEPS.length);
                setPhase("result");
              }
            }, 420 + STEPS.length * 760),
          );
          timers.push(
            window.setTimeout(() => {
              if (!cancelled) run();
            }, 420 + STEPS.length * 760 + 9000),
          );
        }
      }, 26);
      timers.push(typer);
    }

    run();

    return () => {
      cancelled = true;
      timers.forEach((timer) => {
        window.clearTimeout(timer);
        window.clearInterval(timer);
      });
    };
  }, [stageIn, reducedMotion]);

  // Reduced motion shows the completed answer immediately.
  const shownQuery = reducedMotion ? QUERY : typed;
  const shownStep = reducedMotion ? STEPS.length : step;
  const shownPhase: Phase = reducedMotion ? "result" : phase;

  const performanceEntries = Object.entries(MATCH.performance);

  return (
    <section className="nrc-section" id="recommendation">
      <div className="nrc-wrap">
        <motion.div variants={stagger()} {...inView}>
          <motion.h2 className="nrc-h2 nrc-h2--wide" variants={riseIn}>
            Ask in project language. Get an answer in{" "}
            <span className="nrc-grad">technical language</span>.
          </motion.h2>
        </motion.div>

        <motion.div className="nrc-demo" ref={stageRef} variants={riseIn} {...inView}>
          <div className="nrc-demo-col">
            <p className="nrc-label nrc-label--plain">Project query</p>
            <p className="nrc-demo-query">
              {shownQuery}
              {shownPhase === "typing" ? <i className="nrc-demo-caret" aria-hidden="true" /> : null}
            </p>

            <ul className="nrc-steps">
              {STEPS.map((label, index) => {
                const done = shownStep > index;
                const active = shownStep === index;
                return (
                  <li
                    className={`nrc-step${active ? " is-active" : ""}${done ? " is-done" : ""}`}
                    key={label}
                  >
                    <span className="nrc-step-icon" aria-hidden="true">
                      {done ? (
                        <Check size={13} weight="bold" />
                      ) : active ? (
                        <i className="nrc-spinner" />
                      ) : null}
                    </span>
                    {label}
                    {active ? "…" : ""}
                  </li>
                );
              })}
            </ul>

            <dl className={`nrc-parsed${shownStep >= 0 ? " is-in" : ""}`}>
              {PARSED.map((row, index) => (
                <div key={row.k} style={{ "--d": `${index * 90}ms` } as React.CSSProperties}>
                  <dt>{row.k}</dt>
                  <dd>{row.v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="nrc-demo-col">
            <div className={`nrc-result${shownPhase === "result" ? " is-in" : ""}`}>
              <p className="nrc-result-head">
                <span className="nrc-pulse" aria-hidden="true" />
                Recommended solution
              </p>
              <h3>{MATCH.name}</h3>
              <p className="nrc-result-cat">
                {MATCH.manufacturer} · {MATCH.systemType}
              </p>

              <ul className="nrc-match">
                <li>
                  <Check size={14} weight="bold" />
                  <span>
                    <b>Suitable application.</b> Indexed as {MATCH.category} — {MATCH.tagline.toLowerCase()}.
                  </span>
                </li>
                <li>
                  <Check size={14} weight="bold" />
                  <span>
                    <b>Compatible areas.</b> Listed application areas: {MATCH.applicationAreas.join(", ")}.
                  </span>
                </li>
                <li>
                  <Check size={14} weight="bold" />
                  <span>
                    <b>Environmental suitability.</b> {MATCH.climateStrengths.join(", ")}.
                  </span>
                </li>
                {performanceEntries.slice(0, 2).map(([key, value]) => (
                  <li key={key}>
                    <Check size={14} weight="bold" />
                    <span>
                      <b>{humanise(key)}.</b> {value}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="nrc-demo-actions">
                <button className="nrc-btn nrc-btn--primary" onClick={onTryAi} type="button">
                  Try NiRaConChem AI
                  <ArrowRight size={16} weight="bold" />
                </button>
                {MATCH.datasheetUrl ? (
                  <a
                    className="nrc-btn nrc-btn--ghost"
                    href={MATCH.datasheetUrl}
                    rel="noreferrer noopener"
                    target="_blank"
                  >
                    View the datasheet
                    <ArrowRight size={16} weight="bold" />
                  </a>
                ) : null}
              </div>

              <p className="nrc-demo-footnote">
                A demonstration. The product record and its values are read from the
                manufacturer datasheet held in the index.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
