"use client";

import { useEffect, useRef, useState } from "react";
import {
  Building2,
  HardHat,
  ClipboardCheck,
  Factory,
  Wrench,
} from "lucide-react";

type Role = {
  id: string;
  label: string;
  Icon: typeof Building2;
  intro: string;
  helps: { title: string; body: string }[];
};

const ROLES: Role[] = [
  {
    id: "clients",
    label: "Clients & Property Owners",
    Icon: Building2,
    intro:
      "Take control of your project from planning to completion. NiRa helps property owners find budget-friendly construction chemicals, connect with trusted contractors, negotiate confidently, and discover reliable manufacturers and suppliers through one connected network.",
    helps: [
      {
        title: "Find Products Within Budget",
        body: "Compare suitable construction chemicals without compromising project needs.",
      },
      {
        title: "Connect with Contractors",
        body: "Discover contractors through the NiRa network and discuss project requirements directly.",
      },
      {
        title: "Negotiate with Confidence",
        body: "Use clear product and project information to make informed budget decisions.",
      },
      {
        title: "Access Trusted Suppliers",
        body: "Find verified manufacturers and suppliers for reliable project sourcing.",
      },
    ],
  },
  {
    id: "contractors",
    label: "Contractors",
    Icon: HardHat,
    intro:
      "Keep projects moving with faster product discovery, verified technical information, and a powerful professional network. NiRa connects contractors with manufacturers, suppliers, and skilled subcontractors to source materials, build dependable teams, and complete projects efficiently.",
    helps: [
      {
        title: "Save Sourcing Time",
        body: "Find suitable products without searching through multiple catalogs.",
      },
      {
        title: "Connect with Manufacturers",
        body: "Build direct relationships with manufacturers and suppliers across the NiRa network.",
      },
      {
        title: "Find Subcontractors",
        body: "Connect with skilled specialists who can help deliver each stage of the project.",
      },
      {
        title: "Deliver with Confidence",
        body: "Use verified product data and installation guidance to reduce execution errors.",
      },
    ],
  },
  {
    id: "consultants",
    label: "Consultants",
    Icon: ClipboardCheck,
    intro:
      "Give clients confident, evidence-based guidance with verified technical documentation, side-by-side product comparisons, and trusted manufacturer information—all available through one professional platform.",
    helps: [
      {
        title: "Centralize Research",
        body: "Gather relevant product and manufacturer information in one place.",
      },
      {
        title: "Recommend Accurately",
        body: "Support recommendations with verified technical product information.",
      },
      {
        title: "Review Compliance",
        body: "Evaluate standards, certifications, and technical documentation with confidence.",
      },
      {
        title: "Improve Project Outcomes",
        body: "Help clients select durable, high-performing solutions for their requirements.",
      },
    ],
  },
  {
    id: "manufacturers",
    label: "Manufacturers & Suppliers",
    Icon: Factory,
    intro:
      "Put your products in front of the people actively planning and delivering construction projects. Promote your portfolio, build valuable industry relationships, discover new project opportunities, and collaborate with NiRa on targeted product promotion.",
    helps: [
      {
        title: "Promote Your Products",
        body: "Showcase products and verified technical information to relevant buyers.",
      },
      {
        title: "Grow Your Network",
        body: "Connect with clients, contractors, consultants, and subcontractors.",
      },
      {
        title: "Win More Projects",
        body: "Discover qualified opportunities through the expanding NiRa network.",
      },
      {
        title: "Collaborate with NiRa",
        body: "Build promotional partnerships that increase product reach and visibility.",
      },
    ],
  },
  {
    id: "subcontractors",
    label: "Subcontractors",
    Icon: Wrench,
    intro:
      "Find relevant project opportunities from contractors, negotiate directly with suppliers, and source the right products for dependable execution. NiRa helps specialist teams complete work efficiently while prioritizing quality and long-term durability.",
    helps: [
      {
        title: "Find Project Opportunities",
        body: "Connect with contractors seeking skilled teams for active projects.",
      },
      {
        title: "Deal Directly with Suppliers",
        body: "Build supplier relationships and discuss product requirements without friction.",
      },
      {
        title: "Choose the Right Products",
        body: "Use NiRa to find products suited to each application and site condition.",
      },
      {
        title: "Build for Durability",
        body: "Select reliable solutions that support quality work and long service life.",
      },
    ],
  },
];

// Radial menu geometry: icons on a SEMICIRCLE whose diameter runs along the
// right screen edge (flat side = right edge, arc bulges to the left).
const RADIUS = 260; // px radius of the semicircle (a bit bigger)

export default function RoleCarousel() {
  const [active, setActive] = useState(0);
  const sectionRef = useRef<HTMLElement | null>(null);
  const n = ROLES.length;
  const current = ROLES[active];
  const ActiveIcon = current.Icon;

  // As the user scrolls THROUGH this section, the active icon advances
  // automatically (0 -> n-1). Clicking an icon still works (sets active too).
  useEffect(() => {
    function onScroll() {
      const section = sectionRef.current;
      if (!section) return;
      const rect = section.getBoundingClientRect();
      const vh = window.innerHeight;
      const total = rect.height;
      // Hold icon 0 (Clients) centered first: progress stays 0 while the section
      // settles into the middle of the screen, then ramps across the rest of the
      // sticky travel so the next options advance on scroll.
      const start = vh / 2;
      const travel = Math.max(total - vh, 1);
      const scrolled = start - rect.top; // 0 when section top hits center
      const SETTLE = 0.18;               // fraction of travel that holds icon 0 centered
      let p = scrolled / travel;
      p = Math.min(Math.max(p, 0), 1);
      // remap: 0..SETTLE -> 0 (hold), SETTLE..1 -> 0..1 (advance)
      p = p <= SETTLE ? 0 : (p - SETTLE) / (1 - SETTLE);
      const idx = Math.min(n - 1, Math.max(0, Math.round(p * (n - 1))));
      setActive(idx);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [n]);

  // position each icon on a LEFT-bulging semicircle:
  // diameter is the vertical RIGHT edge of the container (x = R = screen edge),
  // arc curves out to the left (x = 0 at the middle). theta: 0=top end, PI=bottom end.
  const positions = ROLES.map((_, i) => {
    const theta = (Math.PI * i) / (n - 1); // 0 .. PI
    const x = RADIUS - Math.sin(theta) * RADIUS; // R at ends (on edge), 0 at middle (bulge left)
    const y = -Math.cos(theta) * RADIUS;         // -R (top) .. +R (bottom)
    const rot = (theta * 180) / Math.PI - 90;     // orient icons along the arc
    return { x, y, rot };
  });

  return (
    <section className="role-carousel" aria-label="Who Nira is for" ref={sectionRef}>
      <div className="role-pin">
      {/* LEFT: selected category data */}
      <div className="role-detail" key={current.id}>
        <div className="role-detail-head">
          <span className="role-detail-icon" aria-hidden="true">
            <ActiveIcon size={28} strokeWidth={1.9} />
          </span>
          <h3>{current.label}</h3>
        </div>
        <p className="role-detail-intro">{current.intro}</p>
        <p className="role-detail-helps-title">How NiRa helps you</p>
        <div className="role-detail-grid">
          {current.helps.map((h) => (
            <div className="role-detail-item" key={h.title}>
              <h4>{h.title}</h4>
              <p>{h.body}</p>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT: semicircle radial menu */}
      <div className="role-radial" aria-label="Select a role">
        <img className="role-radial-center" src="/assets/home-icon.png" alt="" aria-hidden="true" />
        {ROLES.map((role, i) => {
          const p = positions[i];
          const Icon = role.Icon;
          const isActive = i === active;
          return (
            <button
              key={role.id}
              type="button"
              className={`role-node${isActive ? " is-active" : ""}`}
              style={{
                transform: `translate(${p.x}px, ${p.y}px) scale(${isActive ? 1.18 : 1})`,
                zIndex: isActive ? 50 : 1,
              }}
              onClick={() => setActive(i)}
              aria-label={role.label}
              aria-pressed={isActive}
            >
              <Icon size={isActive ? 30 : 22} strokeWidth={1.9} aria-hidden="true" />
              <span className={`role-node-tip${isActive ? " is-open" : ""}`}>{role.label}</span>
            </button>
          );
        })}
      </div>
      </div>
    </section>
  );
}
