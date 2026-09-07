"use client";

import { motion } from "motion/react";

import BrandScroller from "../BrandScroller";
import { CATALOG_COUNTS } from "./catalog.data";
import { inView, riseIn } from "../../lib/motion";

export default function BrandStrip() {
  return (
    <section className="nrc-brands" aria-label="Manufacturers represented in the catalog">
      <motion.div variants={riseIn} {...inView}>
        <p className="nrc-label nrc-label--plain nrc-brands-label">
          {CATALOG_COUNTS.brandLogos} manufacturer catalogs in the index
        </p>
      </motion.div>
      <BrandScroller visible />
    </section>
  );
}
