"use client";

import type { ComponentType } from "react";
import { motion } from "motion/react";
import { Cpu, Database, Gauge, GlobeHemisphereEast, Stack, MagnifyingGlass } from "@phosphor-icons/react";

import { CATALOG_COUNTS } from "./catalog.data";
import { inView, riseIn, stagger } from "../../lib/motion";

type IconType = ComponentType<{ size?: number; weight?: "fill" | "duotone" | "bold" }>;

type Cap = {
  span: "lead" | "wide" | "third" | "full";
  icon: IconType;
  title: string;
  body: string;
  chips?: { label: string; on: boolean }[];
};

/* The previous version of this section carried a bar chart and three progress
   meters whose values were invented to look like data. They are gone: nothing
   on this page draws a number it cannot source. */
const CAPS: Cap[] = [
  {
    span: "lead",
    icon: Cpu,
    title: "AI-powered recommendations",
    body: "Describe the project as it exists on site. Get a decision, not a longlist.",
  },
  {
    span: "wide",
    icon: Database,
    title: "Retrieval-grounded knowledge",
    body: "Answers are built from retrieved datasheets and product profiles — not from what the model remembers.",
  },
  {
    span: "third",
    icon: MagnifyingGlass,
    title: "Semantic product search",
    body: "Matches on what a product does, not on the words the query happened to use.",
  },
  {
    span: "third",
    icon: GlobeHemisphereEast,
    title: "UAE construction focus",
    body: "Selection logic built around the conditions that decide specifications in the Gulf.",
    chips: [
      { label: "Heat", on: true },
      { label: "UV", on: true },
      { label: "Chloride", on: true },
      { label: "Coastal", on: true },
      { label: "Hydrostatic", on: false },
      { label: "Traffic", on: false },
    ],
  },
  {
    span: "third",
    icon: Gauge,
    title: "Faster decisions",
    body: "One query instead of an afternoon in catalogs — and a technical PDF at the end of it.",
  },
  {
    span: "full",
    icon: Stack,
    title: "Scalable intelligence",
    body: `${CATALOG_COUNTS.profiles.toLocaleString("en-US")} product profiles and ${CATALOG_COUNTS.marketProducts} market listings today. It grows as new catalogs and datasheets are ingested.`,
  },
];

export default function Features() {
  return (
    <section className="nrc-section" id="solutions">
      <div className="nrc-wrap">
        <motion.div variants={stagger()} {...inView}>
          <motion.h2 className="nrc-h2" variants={riseIn}>
            Built around how these products are <span className="nrc-grad">actually chosen</span>.
          </motion.h2>
        </motion.div>

        <motion.div className="nrc-caps" variants={stagger(0.07)} {...inView}>
          {CAPS.map((cap) => {
            const Icon = cap.icon;
            return (
              <motion.article
                className={`nrc-cap nrc-cap--${cap.span}`}
                key={cap.title}
                variants={riseIn}
                whileHover={{ y: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
              >
                <span className="nrc-cap-icon" aria-hidden="true">
                  <Icon size={24} weight="duotone" />
                </span>
                <h3>{cap.title}</h3>
                <p>{cap.body}</p>
                {cap.chips ? (
                  <div className="nrc-chips">
                    {cap.chips.map((chip) => (
                      <span
                        className={`nrc-chip${chip.on ? " nrc-chip--on" : ""}`}
                        key={chip.label}
                      >
                        {chip.label}
                      </span>
                    ))}
                  </div>
                ) : null}
              </motion.article>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}
