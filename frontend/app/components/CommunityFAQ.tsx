"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

type QA = { q: string; a: string };

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

  return (
    <section className="community-faq" aria-label="Community">
      {/* SLIDE 1: laptop image (left) + tagline (right) */}
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
          Join! the engineers and manufacturers already running their sourcing decisions through NiRa AI
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
