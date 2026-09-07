"use client";

import { motion } from "motion/react";

import { inView, riseIn, stagger } from "../../lib/motion";

const AHEAD = [
  { title: "Product discovery", body: "Systems that fit the condition, not the keyword." },
  { title: "Technical comparison", body: "Candidates side by side on what decides the spec." },
  { title: "Specification assistance", body: "A decision, in the wording a spec needs." },
  { title: "Project decision support", body: "Conditions carried across a whole project." },
  { title: "Knowledge management", body: "New catalogs and datasheets, ingested." },
];

export default function Vision() {
  return (
    <section className="nrc-section nrc-vision" id="vision">
      <div className="nrc-wrap">
        <motion.div variants={stagger()} {...inView}>
          <motion.h2 variants={riseIn}>
            Building the intelligence layer for <span className="nrc-grad">construction chemistry</span>.
          </motion.h2>
          <motion.p className="nrc-lede" variants={riseIn}>
            Catalog, datasheet and site condition have always been three separate things. This is
            the layer that reads all three — starting with the UAE.
          </motion.p>
        </motion.div>

        <motion.div className="nrc-vision-grid" variants={stagger(0.07)} {...inView}>
          {AHEAD.map((item) => (
            <motion.article className="nrc-vision-item" key={item.title} variants={riseIn}>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
