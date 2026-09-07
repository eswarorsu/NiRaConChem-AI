"use client";

import { motion, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  Cpu,
  Database,
  FileText,
  MagnifyingGlass,
  ScanSmiley,
  Terminal,
  TreeStructure,
} from "@phosphor-icons/react";
import { CATALOG_COUNTS } from "./catalog.data";
import { useReveal, useSequence } from "../../lib/hooks";
import { inView, riseIn, spring, stagger } from "../../lib/motion";
import { scrollToId } from "./nav";

/* These stages mirror what the backend actually runs: FastAPI takes the query,
   a LangGraph agent routes it by intent, retrieval pulls datasheet chunks and
   product profiles, the model writes the rationale, ReportLab renders the PDF. */
const STAGES = [
  {
    icon: Terminal,
    name: "Project requirements",
    desc: "A site question, a set of conditions, or an uploaded document.",
    tag: "Query",
    stage: "Receiving project input",
  },
  {
    icon: TreeStructure,
    name: "AI agent",
    desc: "Routes the request by intent.",
    tag: "LangGraph",
    stage: "Routing by intent",
  },
  {
    icon: MagnifyingGlass,
    name: "Retrieval",
    desc: "Pulls datasheet chunks for the matching application.",
    tag: "RAG",
    stage: "Retrieving context",
  },
  {
    icon: ScanSmiley,
    name: "Semantic matching",
    desc: "Scores candidates on area, substrate, exposure and climate.",
    tag: "Ranking",
    stage: "Matching properties",
  },
  {
    icon: Database,
    name: "Product knowledge",
    desc: `${CATALOG_COUNTS.profiles.toLocaleString("en-US")} profiles, each with its source documents.`,
    tag: "Index",
    stage: "Reading the index",
  },
  {
    icon: Cpu,
    name: "AI reasoning",
    desc: "Writes the recommendation and why it fits.",
    tag: "LLM",
    stage: "Writing the rationale",
  },
  {
    icon: FileText,
    name: "Recommendation",
    desc: "On screen, and as a technical PDF when the project data is complete.",
    tag: "Output",
    stage: "Recommendation ready",
  },
];

export default function AIEngine() {
  const reduced = useReducedMotion();
  const [bodyRef, bodyIn] = useReveal<HTMLDivElement>({ threshold: 0.25 });
  const active = useSequence(bodyIn, STAGES.length - 1, 1150);

  return (
    <section className="nrc-section" id="engine">
      <div className="nrc-wrap">
        <motion.div variants={stagger()} {...inView}>
          <motion.h2 className="nrc-h2" variants={riseIn}>
            From project requirements to the <span className="nrc-grad">right product</span>.
          </motion.h2>
        </motion.div>

        <motion.div className="nrc-engine" ref={bodyRef} variants={riseIn} {...inView}>
          <div className="nrc-engine-aside">
            <p className="nrc-engine-stage" aria-live="off">
              {active >= 0 ? STAGES[Math.min(active, STAGES.length - 1)].stage : ""}
            </p>
            <p className="nrc-engine-note">
              Every recommendation takes the same path. The model reasons only over context
              that was retrieved for that query.
            </p>
            <div className="nrc-engine-links">
              <button
                className="nrc-btn nrc-btn--ghost nrc-btn--sm"
                onClick={() => scrollToId("technology")}
                type="button"
              >
                Technical architecture
                <ArrowRight size={15} weight="bold" />
              </button>
            </div>
          </div>

          <div className="nrc-pipeline">
            <div className="nrc-pipeline-head">
              <span>Recommendation pipeline</span>
              <span>{STAGES.length} stages</span>
            </div>
            <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {STAGES.map((stage, index) => {
                const Icon = stage.icon;
                const live = index <= active;
                return (
                  <motion.li
                    animate={live ? { scale: 1 } : { scale: 0.99 }}
                    className={`nrc-node${live ? " is-live" : ""}`}
                    key={stage.name}
                    transition={reduced ? { duration: 0 } : spring}
                  >
                    <span className="nrc-node-dot" aria-hidden="true">
                      <Icon size={20} weight="duotone" />
                    </span>
                    <span className="nrc-node-name">
                      {stage.name}
                      <span className="nrc-node-desc">{stage.desc}</span>
                    </span>
                    <span className="nrc-node-tag">{stage.tag}</span>
                  </motion.li>
                );
              })}
            </ol>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
