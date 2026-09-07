"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { CheckCircle, Drop, Sun, Timer } from "@phosphor-icons/react";

import { CATALOG_PRODUCTS } from "./catalog.data";
import { popIn, spring, springPop, springSoft } from "../../lib/motion";

/**
 * The frosted panel under the headline: the product's actual job, running.
 *
 * Conditions arrive one at a time, then the recommendation resolves against
 * them. The product and its performance values are read from the real catalog
 * record (see catalog.data.ts) — nothing here is written by hand.
 */

const MATCH = CATALOG_PRODUCTS[0];
const PERFORMANCE = Object.entries(MATCH.performance).slice(0, 2);

const CONDITIONS = [
  { icon: Drop, label: "Concrete roof · heavy rainfall" },
  { icon: Sun, label: "High surface temperature" },
  { icon: Timer, label: "Foot traffic, occasional" },
];

const CYCLE_MS = 900;
const HOLD_MS = 4200;

export default function HeroPanel() {
  const reduced = useReducedMotion();
  const [step, setStep] = useState(reduced ? 99 : 0);

  useEffect(() => {
    if (reduced) return;
    let cancelled = false;
    const timers: number[] = [];

    function run() {
      setStep(0);
      for (let i = 1; i <= CONDITIONS.length + 1; i += 1) {
        timers.push(
          window.setTimeout(() => {
            if (!cancelled) setStep(i);
          }, i * CYCLE_MS),
        );
      }
      timers.push(
        window.setTimeout(run, (CONDITIONS.length + 1) * CYCLE_MS + HOLD_MS),
      );
    }

    run();
    return () => {
      cancelled = true;
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, [reduced]);

  const resolved = step > CONDITIONS.length;

  return (
    <motion.div
      className="nrc-panel"
      initial={{ opacity: 0, y: 80, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ ...springSoft, delay: 0.5 }}
    >
      <div className="nrc-panel-bar" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <div className="nrc-panel-body">
        <section className="nrc-panel-col">
          <h2 className="nrc-panel-title">Your condition</h2>
          <ul className="nrc-panel-list">
            {CONDITIONS.map((condition, index) => {
              const Icon = condition.icon;
              const shown = reduced || step > index;
              return (
                <motion.li
                  animate={shown ? { opacity: 1, x: 0 } : { opacity: 0, x: -14 }}
                  className="nrc-panel-row"
                  key={condition.label}
                  transition={spring}
                >
                  <span className="nrc-panel-icon is-on">
                    <Icon size={15} weight="fill" />
                  </span>
                  {condition.label}
                </motion.li>
              );
            })}
          </ul>
        </section>

        <section className="nrc-panel-col">
          <h2 className="nrc-panel-title">
            NiRa recommends
            <AnimatePresence>
              {!resolved ? (
                <motion.span
                  animate={{ opacity: 1 }}
                  className="nrc-panel-thinking"
                  exit={{ opacity: 0 }}
                  initial={{ opacity: 0 }}
                >
                  reading datasheets…
                </motion.span>
              ) : null}
            </AnimatePresence>
          </h2>

          <motion.div
            animate={resolved ? { opacity: 1, y: 0 } : { opacity: 0.25, y: 8 }}
            transition={springSoft}
          >
            <motion.p
              animate={resolved ? "show" : "hidden"}
              className="nrc-panel-match"
              initial="hidden"
              variants={popIn}
            >
              <span className="nrc-panel-icon is-solid">
                <CheckCircle size={15} weight="fill" />
              </span>
              {MATCH.name}
            </motion.p>

            <ul className="nrc-panel-list">
              {PERFORMANCE.map(([key, value], index) => (
                <motion.li
                  animate={resolved ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }}
                  className="nrc-panel-row is-quiet"
                  key={key}
                  transition={{ ...springPop, delay: resolved ? 0.1 + index * 0.08 : 0 }}
                >
                  <span className="nrc-panel-dot" aria-hidden="true" />
                  {value}
                </motion.li>
              ))}
              <motion.li
                animate={resolved ? { opacity: 1, x: 0 } : { opacity: 0, x: -10 }}
                className="nrc-panel-row is-quiet"
                transition={{ ...springPop, delay: resolved ? 0.26 : 0 }}
              >
                <span className="nrc-panel-dot" aria-hidden="true" />
                Suits {MATCH.applicationAreas.join(", ")}
              </motion.li>
            </ul>
          </motion.div>
        </section>
      </div>
    </motion.div>
  );
}
