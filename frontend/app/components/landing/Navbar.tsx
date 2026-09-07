"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";
import { ArrowRight, List, X } from "@phosphor-icons/react";
import { NAV_LINKS, scrollToId } from "./nav";
import { spring, springPop } from "../../lib/motion";

type NavbarProps = {
  onTryAi: () => void;
};

/**
 * Transparent over the hero, densifying into a frosted bar once the user
 * scrolls. The links are in-page anchors: the application is a single route,
 * so inventing /product or /technology pages would create dead ends.
 */
export default function Navbar({ onTryAi }: NavbarProps) {
  const [stuck, setStuck] = useState(false);
  const [open, setOpen] = useState(false);

  const { scrollY } = useScroll();
  useMotionValueEvent(scrollY, "change", (value) => {
    setStuck(value > 24);
  });

  // Close the mobile sheet when the viewport grows past the breakpoint,
  // otherwise it stays mounted and swallows clicks on desktop.
  useEffect(() => {
    const query = window.matchMedia("(min-width: 901px)");
    const onChange = () => setOpen(false);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  function go(id: string) {
    setOpen(false);
    scrollToId(id);
  }

  return (
    <motion.header
      animate={{ y: 0, opacity: 1 }}
      className={`nrc-nav${stuck || open ? " is-stuck" : ""}`}
      initial={{ y: -28, opacity: 0 }}
      transition={{ ...spring, delay: 0.05 }}
    >
      <div className="nrc-nav-inner">
        <a
          className="nrc-brand"
          href="#top"
          onClick={(event) => {
            event.preventDefault();
            go("top");
          }}
        >
          <span className="nrc-brand-mark" aria-hidden="true">
            <Image src="/icons/brand-mark.jpg" alt="" width={22} height={22} priority />
          </span>
          <span className="nrc-brand-name">NiRaConChem AI</span>
        </a>

        <nav className="nrc-nav-links" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <a
              key={link.id}
              href={`#${link.id}`}
              onClick={(event) => {
                event.preventDefault();
                go(link.id);
              }}
            >
              <span>{link.label}</span>
            </a>
          ))}
        </nav>

        <motion.button
          className="nrc-btn nrc-btn--accent nrc-btn--sm nrc-nav-cta"
          onClick={onTryAi}
          transition={springPop}
          type="button"
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
        >
          Try AI
          <ArrowRight size={15} weight="bold" aria-hidden="true" />
        </motion.button>

        <button
          aria-controls="nrc-nav-sheet"
          aria-expanded={open}
          aria-label={open ? "Close menu" : "Open menu"}
          className="nrc-nav-burger"
          onClick={() => setOpen((value) => !value)}
          type="button"
        >
          {open ? <X size={19} weight="bold" /> : <List size={19} weight="bold" />}
        </button>
      </div>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            animate={{ height: "auto", opacity: 1 }}
            className="nrc-nav-sheet is-open"
            exit={{ height: 0, opacity: 0 }}
            id="nrc-nav-sheet"
            initial={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 34, mass: 0.8 }}
          >
            <div className="nrc-nav-sheet-inner">
              {NAV_LINKS.map((link, index) => (
                <motion.a
                  animate={{ opacity: 1, y: 0 }}
                  href={`#${link.id}`}
                  initial={{ opacity: 0, y: 10 }}
                  key={link.id}
                  onClick={(event) => {
                    event.preventDefault();
                    go(link.id);
                  }}
                  transition={{ ...spring, delay: 0.04 + index * 0.04 }}
                >
                  {link.label}
                </motion.a>
              ))}
              <button
                className="nrc-btn nrc-btn--accent"
                onClick={() => {
                  setOpen(false);
                  onTryAi();
                }}
                type="button"
              >
                Try AI
                <ArrowRight size={16} weight="bold" aria-hidden="true" />
              </button>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.header>
  );
}
