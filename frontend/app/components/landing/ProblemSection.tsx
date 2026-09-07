"use client";

import { motion } from "motion/react";

import Counter from "./Counter";
import { CATALOG_COUNTS } from "./catalog.data";
import { inView, riseIn, stagger } from "../../lib/motion";

const CELLS = [
  {
    value: CATALOG_COUNTS.profiles,
    tail: "",
    title: "Product profiles",
    body: "One condition can match dozens of valid systems.",
  },
  {
    value: CATALOG_COUNTS.marketCategories,
    tail: "",
    title: "Categories",
    body: "Each with its own selection logic.",
  },
  { value: 6, tail: "+", title: "Variables per decision", body: "Substrate, exposure, movement, traffic, temperature, pressure." },
  {
    value: CATALOG_COUNTS.marketProducts,
    tail: "",
    title: "Market listings",
    body: "Local options to check availability against.",
  },
];

export default function ProblemSection() {
  return (
    <section className="nrc-section" id="problem">
      <div className="nrc-wrap">
        <motion.div className="nrc-problem-head" variants={stagger()} {...inView}>
          <motion.div variants={riseIn}>
            <h2 className="nrc-h2">
              Choosing the right construction chemical shouldn&rsquo;t be guesswork.
            </h2>
          </motion.div>
          <motion.p className="nrc-lede" variants={riseIn}>
            The information exists. It is just spread across catalogs, datasheets and site
            conditions that nobody has time to reconcile.
          </motion.p>
        </motion.div>

        <motion.div className="nrc-complexity" variants={stagger(0.08)} {...inView}>
          {CELLS.map((cell) => (
            <motion.article className="nrc-complexity-cell" key={cell.title} variants={riseIn}>
              <p className="nrc-complexity-n">
                <Counter to={cell.value} />
                {cell.tail ? <span>{cell.tail}</span> : null}
              </p>
              <h3 className="nrc-complexity-t">{cell.title}</h3>
              <p className="nrc-complexity-d">{cell.body}</p>
            </motion.article>
          ))}
        </motion.div>

        <motion.div className="nrc-transition" variants={stagger(0.1)} {...inView}>
          <motion.span className="nrc-transition-step" variants={riseIn}>
            Complexity
          </motion.span>
          <motion.span className="nrc-transition-arrow" aria-hidden="true" variants={riseIn} />
          <motion.span className="nrc-transition-step" variants={riseIn}>
            Technical intelligence
          </motion.span>
          <motion.span className="nrc-transition-arrow" aria-hidden="true" variants={riseIn} />
          <motion.span className="nrc-transition-step" variants={riseIn}>
            NiRaConChem AI
          </motion.span>
        </motion.div>
      </div>
    </section>
  );
}
