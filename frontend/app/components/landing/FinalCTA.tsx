"use client";

import { motion, useReducedMotion } from "motion/react";
import { ArrowRight } from "@phosphor-icons/react";

import { inView, liftIn, spring } from "../../lib/motion";
import { scrollToId } from "./nav";

export default function FinalCTA({ onTryAi }: { onTryAi: () => void }) {
  const reduced = useReducedMotion();

  return (
    <section className="nrc-section nrc-final" id="start">
      <div className="nrc-wrap">
        <motion.div className="nrc-final-inner" variants={liftIn} {...inView}>
          <h2>Ready to make construction <span className="nrc-grad">chemistry</span> <span className="nrc-grad">intelligent</span>?</h2>
          <p>Explore construction chemicals through AI-powered technical intelligence.</p>
          <div className="nrc-final-actions">
            <motion.button
              className="nrc-btn nrc-btn--ink"
              onClick={onTryAi}
              transition={spring}
              type="button"
              whileHover={reduced ? undefined : { y: -2 }}
              whileTap={reduced ? undefined : { scale: 0.97 }}
            >
              Try NiRaConChem AI
              <ArrowRight size={16} weight="bold" />
            </motion.button>
            <motion.button
              className="nrc-btn nrc-btn--text"
              onClick={() => scrollToId("technology")}
              transition={spring}
              type="button"
              whileHover={reduced ? undefined : { y: -2 }}
              whileTap={reduced ? undefined : { scale: 0.97 }}
            >
              Explore
            </motion.button>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
