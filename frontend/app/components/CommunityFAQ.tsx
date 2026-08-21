"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

type QA = { q: string; a: string };

const FEATURE_POINTS = [
  {
    title: "Zero Hallucinations",
    body: "Every recommendation is backed by verified manufacturer data.",
  },
  {
    title: "Verified Datasheets",
    body: "Technical documents are validated before recommendations.",
  },
  {
    title: "Location Aware",
    body: "Site conditions influence every recommendation.",
  },
  {
    title: "Explainable AI",
    body: "Understand why each product was selected.",
  },
  {
    title: "Manufacturer Connect",
    body: "Reach the manufacturer directly from NiRa.",
  },
];

const QUESTIONS: QA[] = [
  {
    q: "How does NiRa AI pick the right construction chemical?",
    a: "NiRa reads your project spec, site conditions, and requirements, then matches products against a verified manufacturer catalog using explainable logic — so every recommendation cites why it fits your exact use case.",
  },
  {
    q: "Is NiRa AI only useful for contractors?",
    a: "No. Clients, contractors, consultants, manufacturers, suppliers, and subcontractors all use NiRa differently — from budgeting and sourcing to compliance review and winning projects.",
  },
  {
    q: "Can I upload my project file instead of typing a query?",
    a: "Yes. Attach a PDF, DOCX, XLSX, or TXT and NiRa extracts locations, construction areas, and requirements automatically, then returns a tighter, document-aware recommendation.",
  },
  {
    q: "Are the recommendations UAE-ready?",
    a: "They are. NiRa tailors suggestions to UAE project contexts — climate, standards, and regional supplier availability — so you get guidance that works on site, not just in theory.",
  },
  {
    q: "How do manufacturers and suppliers benefit?",
    a: "You put your portfolio in front of people actively planning and delivering projects, grow your network, discover new opportunities, and can collaborate with NiRa on targeted promotion.",
  },
  {
    q: "Can I export the recommendation as a PDF?",
    a: "When a report is ready, a Download PDF button appears so you can share a clean, cited recommendation with clients, consultants, or your project team.",
  },
];

export default function CommunityFAQ() {
  const [open, setOpen] = useState<number | null>(null);
  const [activePoint, setActivePoint] = useState(0);
  const featureRef = useRef<HTMLDivElement | null>(null);

  // Scroll-driven sequencing: as the feature section scrolls through the
  // viewport, advance the active point. Each point enters from the right,
  // holds, then exits to the right before the next one appears.
  useEffect(() => {
    const el = featureRef.current;
    if (!el) return;
    const onScroll = () => {
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      // progress 0 (just entering bottom) -> 1 (leaving top)
      const total = rect.height + vh;
      const seen = vh - rect.top;
      const p = Math.min(1, Math.max(0, seen / total));
      const idx = Math.min(
        FEATURE_POINTS.length - 1,
        Math.floor(p * FEATURE_POINTS.length),
      );
      setActivePoint(idx);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <section className="community-faq" aria-label="Community">
      {/* SLIDE 0: tall track that pins the feature (image centered) while the
          user scrolls; each scroll step advances one feature point. */}
      <div className="community-faq-feature-track" ref={featureRef}>
        <div className="community-faq-feature">
          <div className="community-faq-feature-media">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/assets/feature-slide.png"
              alt="NiRaConChem AI in action"
              className="community-faq-feature-img"
            />
          </div>
          <ul className="feature-points" aria-label="Key features">
            {FEATURE_POINTS.map((point, i) => (
              <li
                key={point.title}
                className={`feature-point${i === activePoint ? " is-active" : ""}${i < activePoint ? " is-past" : ""}`}
              >
                <h3 className="feature-point-title">{point.title}</h3>
                <p className="feature-point-body">{point.body}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* SLIDE 1: heading + laptop image (left) + tagline (right) */}
      <h2 className="community-faq-join-title">Join Our Network</h2>
      <div className="community-faq-hero">
        <div className="community-faq-media">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/assets/file_00000000b0748207849d1f00bcad5474.png"
            alt="NiRa AI on laptop and mobile"
            className="community-faq-img"
          />
        </div>
        <p className="community-faq-tagline">
          Join the engineers and manufacturers already running their sourcing decisions through NiRa AI.
        </p>
      </div>

      {/* SLIDE 2: title */}
      <h2 className="community-faq-title">Questions engineers ask</h2>

      {/* SLIDE 3: questions */}
      <div className="faq-list">
        {QUESTIONS.map((item, i) => {
          const isOpen = open === i;
          return (
            <div className={`faq-item${isOpen ? " is-open" : ""}`} key={i}>
              <button
                type="button"
                className="faq-question"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : i)}
              >
                <span>{item.q}</span>
                <ChevronDown size={20} strokeWidth={2.2} className="faq-chevron" aria-hidden="true" />
              </button>
              <div className="faq-answer" hidden={!isOpen}>
                <p>{item.a}</p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
