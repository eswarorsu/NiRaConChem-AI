"use client";

import dynamic from "next/dynamic";
import { useRef, type ReactNode } from "react";
import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { ArrowRight } from "@phosphor-icons/react";

import { riseIn, spring, stagger } from "../../lib/motion";
import { scrollToId } from "./nav";

/* The panel is the largest piece of markup on the page and it is not needed for
   the first paint, so it is split out of the initial payload. */
const HeroPanel = dynamic(() => import("./HeroPanel"), { ssr: false });

type HeroProps = {
  /** The application's live search form, owned by the page. */
  searchSlot: ReactNode;
  onExploreTechnology: () => void;
};

export default function Hero({ searchSlot, onExploreTechnology }: HeroProps) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLElement>(null);

  // The gradient field drifts a little slower than the page, so the hero has
  // depth as you leave it rather than sliding away as one flat plane.
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const fieldY = useSpring(useTransform(scrollYProgress, [0, 1], [0, 140]), {
    stiffness: 90,
    damping: 26,
  });
  const contentY = useSpring(useTransform(scrollYProgress, [0, 1], [0, -40]), {
    stiffness: 120,
    damping: 28,
  });

  return (
    <section className="nrc-hero" id="top" ref={ref}>
      <motion.div
        aria-hidden="true"
        className="nrc-hero-field"
        style={reduced ? undefined : { y: fieldY }}
      />

      <motion.div
        className="nrc-hero-inner"
        initial="hidden"
        animate="show"
        variants={stagger(0.09, 0.05)}
        style={reduced ? undefined : { y: contentY }}
      >
        <motion.h1 variants={riseIn} data-text="Stop guessing which chemical to spec.">
          Stop guessing which <span className="nrc-grad">chemical</span> to spec.
        </motion.h1>

        <motion.p className="nrc-hero-sub" variants={riseIn}>
          Describe the condition on site. NiRa reads the datasheets and comes back with the
          product, the reason, and the proof.
        </motion.p>

        <motion.div className="nrc-hero-search" variants={riseIn}>
          {searchSlot}
        </motion.div>

        <motion.div className="nrc-hero-actions" variants={riseIn}>
          <motion.button
            className="nrc-btn nrc-btn--ink"
            onClick={() => scrollToId("recommendation")}
            type="button"
            whileHover={reduced ? undefined : { y: -2 }}
            whileTap={reduced ? undefined : { scale: 0.97 }}
            transition={spring}
          >
            See a real recommendation
            <ArrowRight size={16} weight="bold" />
          </motion.button>
          <motion.button
            className="nrc-btn nrc-btn--glass"
            onClick={onExploreTechnology}
            type="button"
            whileHover={reduced ? undefined : { y: -2 }}
            whileTap={reduced ? undefined : { scale: 0.97 }}
            transition={spring}
          >
            How it works
          </motion.button>
        </motion.div>
      </motion.div>

      <HeroPanel />
    </section>
  );
}
