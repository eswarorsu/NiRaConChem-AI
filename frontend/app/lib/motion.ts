"use client";

import type { Transition, Variants } from "motion/react";

/**
 * Shared motion language.
 *
 * Everything on this site moves on springs, not on duration curves — a spring
 * carries momentum, which is what makes motion read as physical rather than
 * as a timed CSS transition. These are the only springs in use, so the whole
 * page moves with one hand.
 */

/** Default: settles quickly, barely overshoots. Entrances and reveals. */
export const spring: Transition = { type: "spring", stiffness: 260, damping: 30, mass: 0.9 };

/** Softer and slower. Large surfaces — panels, cards, section blocks. */
export const springSoft: Transition = { type: "spring", stiffness: 150, damping: 26, mass: 1.1 };

/** Snappy with visible overshoot. Small elements that should feel alive:
 *  chips, badges, counters, anything that "pops" in. */
export const springPop: Transition = { type: "spring", stiffness: 420, damping: 22, mass: 0.7 };

/** Rise-and-fade. The workhorse for anything entering the viewport. */
export const riseIn: Variants = {
  hidden: { opacity: 0, y: 26 },
  show: { opacity: 1, y: 0, transition: springSoft },
};

/** Same, but scaled — for panels and cards where the size change reads. */
export const liftIn: Variants = {
  hidden: { opacity: 0, y: 42, scale: 0.97 },
  show: { opacity: 1, y: 0, scale: 1, transition: springSoft },
};

/** Pops in from small. Chips and badges. */
export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.7 },
  show: { opacity: 1, scale: 1, transition: springPop },
};

/** Parent that releases its children one after another. */
export function stagger(each = 0.07, delay = 0): Variants {
  return {
    hidden: {},
    show: { transition: { staggerChildren: each, delayChildren: delay } },
  };
}

/** The props every section uses to animate itself in on first scroll-past. */
export const inView = {
  initial: "hidden" as const,
  whileInView: "show" as const,
  viewport: { once: true, amount: 0.25 },
};
