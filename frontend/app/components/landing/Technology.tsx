"use client";

import { motion } from "motion/react";

import { CATALOG_COUNTS } from "./catalog.data";
import { inView, riseIn, stagger } from "../../lib/motion";

/* Only what the repository actually runs: a LangGraph agent over a local
   product-profile index and datasheet RAG chunks, with a Groq-hosted model.
   There is no separate vector database service, so none is claimed. */
const LAYERS = [
  { n: "L1", name: "Frontend", desc: "Chat, market results, uploads and report download.", tech: ["Next.js", "React", "TypeScript"] },
  { n: "L2", name: "API", desc: "Typed endpoints for chat, file analysis, ingestion and reports.", tech: ["FastAPI", "Pydantic"] },
  { n: "L3", name: "AI agent", desc: "Routes each request by intent.", tech: ["LangGraph"] },
  { n: "L4", name: "Retrieval", desc: "Datasheets parsed and chunked, then searched per query.", tech: ["RAG", "Document parsing"] },
  {
    n: "L5",
    name: "Knowledge index",
    desc: `${CATALOG_COUNTS.profiles.toLocaleString("en-US")} product profiles with their source documents.`,
    tech: ["Product profiles", "Semantic scoring"],
  },
  { n: "L6", name: "Language model", desc: "Writes the recommendation over retrieved context only.", tech: ["Groq"] },
  { n: "L7", name: "Report", desc: "Renders the technical PDF for the project record.", tech: ["ReportLab"] },
];

export default function Technology() {
  return (
    <section className="nrc-section" id="technology">
      <div className="nrc-wrap">
        <motion.div variants={stagger()} {...inView}>
          <motion.h2 className="nrc-h2" variants={riseIn}>
            Built for <span className="nrc-grad">technical intelligence</span>.
          </motion.h2>
          <motion.p className="nrc-lede" variants={riseIn}>
            Seven layers, one job each. A request enters at the top and leaves traceable to the
            document it came from.
          </motion.p>
        </motion.div>

        <motion.div className="nrc-arch" variants={stagger(0.06)} {...inView}>
          {LAYERS.map((layer) => (
            <motion.div
              className="nrc-layer is-in"
              key={layer.n}
              variants={riseIn}
              whileHover={{ x: 6 }}
              transition={{ type: "spring", stiffness: 320, damping: 26 }}
            >
              <span className="nrc-layer-n">{layer.n}</span>
              <span className="nrc-layer-name">{layer.name}</span>
              <span className="nrc-layer-desc">{layer.desc}</span>
              <span className="nrc-layer-tech">
                {layer.tech.map((item) => (
                  <span className="nrc-chip" key={item}>
                    {item}
                  </span>
                ))}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
