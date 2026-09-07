"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { DownloadSimple } from "@phosphor-icons/react";
import { scrollToId } from "./nav";
import { inView, riseIn, stagger } from "../../lib/motion";

type FooterProps = {
  onTryAi: () => void;
  canInstall: boolean;
  onInstall: () => void;
};

/**
 * Deliberately minimal. There is no contact route, no marketing site and no
 * verified social account in this project, so none is linked — a footer full of
 * dead links is the fastest way to make a product look unfinished.
 */
const WORDMARK = "NiRaConChem";

/**
 * Sizes the closing wordmark so its INK spans the full line.
 *
 * Two things rule out a CSS constant. The mark may resolve to OffBit DotBold,
 * to Doto, or to the sans fallback, and those three set the same eleven letters
 * at very different widths. And sizing to the advance width leaves the font's
 * side bearings as dead space — on OffBit that is over 200px of nothing at each
 * end, which reads as a mark that failed to reach the edges.
 *
 * So the measurement is canvas ink bounds, not layout width. The resulting
 * advance box is wider than the line by exactly the side bearings, and the
 * container's overflow:hidden swallows them.
 */
function useFitWordmark() {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const textRef = useRef<HTMLSpanElement | null>(null);

  const fit = useCallback(() => {
    const box = boxRef.current;
    if (!box) return;
    const available = box.clientWidth;
    if (available <= 0) return;

    const PROBE = 200;
    const style = getComputedStyle(box);
    const context = document.createElement("canvas").getContext("2d");
    let inkWidth = 0;

    if (context) {
      context.font = `${style.fontWeight} ${PROBE}px ${style.fontFamily}`;
      const metrics = context.measureText(WORDMARK);
      // actualBoundingBox* is the drawn extent, so this excludes side bearings.
      inkWidth = metrics.actualBoundingBoxLeft + metrics.actualBoundingBoxRight;
    }

    if (!inkWidth) {
      // No canvas, or a browser without ink metrics: fall back to the advance.
      const text = textRef.current;
      if (!text) return;
      box.style.fontSize = `${PROBE}px`;
      inkWidth = text.scrollWidth;
    }

    // Written to the box: both stacked copies inherit it, so the sharp half and
    // the blurred half stay in register.
    if (inkWidth > 0) box.style.fontSize = `${(PROBE * available) / inkWidth}px`;
  }, []);

  useEffect(() => {
    fit();
    const box = boxRef.current;
    if (!box) return;
    const observer = new ResizeObserver(fit);
    observer.observe(box);
    // Fonts land after first paint; without this the mark keeps the fallback's
    // measurements and overflows or falls short once the real face arrives.
    document.fonts?.ready.then(fit).catch(() => {});
    return () => observer.disconnect();
  }, [fit]);

  return { boxRef, textRef };
}

export default function Footer({ onTryAi, canInstall, onInstall }: FooterProps) {
  const year = new Date().getFullYear();
  const { boxRef, textRef } = useFitWordmark();

  return (
    <footer className="nrc-footer">
      <div className="nrc-wrap">
        <motion.div className="nrc-footer-top" variants={stagger(0.08)} {...inView}>
          <motion.div variants={riseIn}>
            <p className="nrc-footer-tag">AI-powered construction chemical intelligence.</p>
          </motion.div>

          <motion.nav className="nrc-footer-nav" aria-label="Footer" variants={riseIn}>
            <button onClick={() => scrollToId("top")} type="button">
              Home
            </button>
            <button onClick={onTryAi} type="button">
              AI Recommendations
            </button>
            <button onClick={() => scrollToId("technology")} type="button">
              Technology
            </button>
            <button onClick={() => scrollToId("vision")} type="button">
              About
            </button>
            {canInstall ? (
              <button onClick={onInstall} type="button">
                <DownloadSimple size={14} weight="bold" aria-hidden="true" /> Install app
              </button>
            ) : null}
          </motion.nav>
        </motion.div>

        <div className="nrc-footer-above">
          <span>© {year} NiRaConChem AI</span>
          <span>Construction chemical intelligence · United Arab Emirates</span>
        </div>

        <div className="nrc-footer-bottom">
        </div>
      </div>

      {/* The closing signature. Set to the full width of the page and cropped by
          the page edge, so the name reads as a mark rather than another line of
          copy. aria-hidden because the name is already in the footer above —
          a screen reader should not hear it twice. */}
      <motion.div
        aria-hidden="true"
        className="nrc-wordmark"
        initial={{ opacity: 0, y: 44 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.4 }}
        transition={{ type: "spring", stiffness: 120, damping: 26, mass: 1.1 }}
      >
        <div className="nrc-wordmark-fit" ref={boxRef}>
          <span className="nrc-wordmark-sharp" ref={textRef}>
            {WORDMARK}
          </span>
          <span className="nrc-wordmark-blur">{WORDMARK}</span>
        </div>
      </motion.div>
    </footer>
  );
}
