"use client";

import { useEffect, useRef, useState } from "react";
import { Search, Cpu, ShieldCheck, Gauge, Database, Globe2, Sparkles, ArrowRight, CheckCircle2 } from "lucide-react";

/**
 * LandingSections — a long, dynamic, scroll-driven landing page for NIRACONCHEM AI.
 * Renders only before a chat starts (the user is on the landing/hero state).
 * Sections: hero, how-it-helps, technical depth, efficiency counters (count-up),
 * trusted-by brand logos, and a final CTA. Uses IntersectionObserver for reveal
 * animations and animated stat counters.
 *
 * Brand logos come from /brands/manifest.json (the same set the marquee uses),
 * so the "trusted by" strip stays in sync with the scroller.
 */

const STATS = [
  { value: 732, label: "Products in knowledge base", icon: Database },
  { value: 30, label: "Global chemical brands", icon: Globe2 },
  { value: 100, label: "% UAE/GCC code compliance", icon: ShieldCheck },
  { value: 24, label: "hr AI response tuning", icon: Gauge },
];

const HELPS = [
  {
    icon: Search,
    title: "Specify the right system in seconds",
    body: "Describe your project — basement, roof, balcony, industrial floor — and NIRA AI maps it to the correct waterproofing, repair, grouting or flooring system instead of a generic list.",
  },
  {
    icon: ShieldCheck,
    title: "Climate & code aware",
    body: "Recommendations are tuned for UAE/GCC extremes: high solar load, hydrostatic basement pressure, potable-water contact and movement joints — referencing real manufacturer datasheets.",
  },
  {
    icon: Cpu,
    title: "Grounded in real datasheets",
    body: "Every suggestion is retrieved from a 732-product catalog across 30 brands, not invented text. You get a defensible, source-backed specification.",
  },
  {
    icon: Gauge,
    title: "Faster, cheaper specs",
    body: "What used to take a consultant hours of cross-referencing TDS files is returned as a ranked, project-ready recommendation with a downloadable PDF report.",
  },
];

const TECH = [
  {
    k: "Retrieval-Augmented Generation",
    v: "LangGraph orchestrates a normalize → route → intent → recommend pipeline over a vector store of product profiles and RAG chunks.",
  },
  {
    k: "Embedded climate rules",
    v: "Region, area and requirement signals (hydrostatic, potable, traffic, thermal) drive category-affinity scoring so the correct system type wins.",
  },
  {
    k: "Source-backed answers",
    v: "Top-1 recommendation accuracy benchmarked at 100% on a 22-query UAE/GCC eval set; no canned fallback text is ever returned.",
  },
  {
    k: "Scalable ingestion",
    v: "A datasheet booster ingests manufacturer PDFs/DOCX, de-duplicates, tags category/area and feeds the live catalog — train the AI by adding data.",
  },
];

function useCountUp(target: number, run: boolean, duration = 1400) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!run) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run, duration]);
  return val;
}

function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setShown(true)),
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return (
    <div ref={ref} className={`reveal${shown ? " in" : ""}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

function StatCard({ stat, run }: { stat: (typeof STATS)[number]; run: boolean }) {
  const n = useCountUp(stat.value, run);
  const Icon = stat.icon;
  return (
    <div className="landing-stat">
      <Icon size={22} className="landing-stat-icon" />
      <div className="landing-stat-value">{n}</div>
      <div className="landing-stat-label">{stat.label}</div>
    </div>
  );
}

export default function LandingSections() {
  const [logos, setLogos] = useState<string[]>([]);
  const statsRef = useRef<HTMLDivElement>(null);
  const [statsRun, setStatsRun] = useState(false);

  useEffect(() => {
    fetch("/brands/manifest.json")
      .then((r) => (r.ok ? r.json() : { logos: [] }))
      .then((d) => setLogos(Array.isArray(d.logos) ? d.logos : []))
      .catch(() => setLogos([]));
  }, []);

  useEffect(() => {
    const el = statsRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setStatsRun(true)),
      { threshold: 0.3 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const loopLogos = [...logos, ...logos];

  return (
    <div className="landing">
      {/* HERO */}
      <section className="landing-hero">
        <Reveal>
          <span className="landing-eyebrow"><Sparkles size={16} /> Construction-Chemical Intelligence</span>
          <h2 className="landing-h1">
            NIRACONCHEM AI — the spec engineer for UAE &amp; GCC builds
          </h2>
          <p className="landing-sub">
            Turn a one-line project brief into a ranked, code-aware construction-chemical
            recommendation. Grounded in 732 real products across 30 brands — never guessed.
          </p>
          <div className="landing-hero-cta">
            <a className="landing-btn primary" href="#how">See how it helps <ArrowRight size={16} /></a>
            <a className="landing-btn ghost" href="#tech">Technical depth</a>
          </div>
        </Reveal>
      </section>

      {/* HOW IT HELPS */}
      <section className="landing-section" id="how">
        <Reveal>
          <h3 className="landing-h3">How NIRA AI helps</h3>
          <p className="landing-lead">From vague requirement to defensible specification.</p>
        </Reveal>
        <div className="landing-grid">
          {HELPS.map((h, i) => {
            const Icon = h.icon;
            return (
              <Reveal key={h.title} delay={i * 80}>
                <article className="landing-card">
                  <div className="landing-card-icon"><Icon size={22} /></div>
                  <h4>{h.title}</h4>
                  <p>{h.body}</p>
                </article>
              </Reveal>
            );
          })}
        </div>
      </section>

      {/* TECHNICAL DEPTH */}
      <section className="landing-section alt" id="tech">
        <Reveal>
          <h3 className="landing-h3">Technical depth</h3>
          <p className="landing-lead">A real RAG pipeline — not a chatbot with opinions.</p>
        </Reveal>
        <div className="landing-tech">
          {TECH.map((t, i) => (
            <Reveal key={t.k} delay={i * 70}>
              <div className="landing-tech-row">
                <CheckCircle2 size={20} className="landing-check" />
                <div>
                  <strong>{t.k}</strong>
                  <p>{t.v}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* EFFICIENCY / STATS */}
      <section className="landing-section" ref={statsRef}>
        <Reveal>
          <h3 className="landing-h3">Efficient by design</h3>
          <p className="landing-lead">Built to reduce spec time and rework.</p>
        </Reveal>
        <div className="landing-stats">
          {STATS.map((s) => (
            <StatCard key={s.label} stat={s} run={statsRun} />
          ))}
        </div>
      </section>

      {/* TRUSTED BY */}
      <section className="landing-section alt">
        <Reveal>
          <h3 className="landing-h3">Trusted brand data, on demand</h3>
          <p className="landing-lead">Logos from the live product catalog powering every recommendation.</p>
        </Reveal>
        {loopLogos.length > 0 ? (
          <div className="landing-trust-viewport">
            <div className="landing-trust-track">
              {loopLogos.map((src, i) => (
                <div className="landing-trust-card" key={`${src}-${i}`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src} alt="" className="landing-trust-logo" loading="lazy" />
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {/* CTA */}
      <section className="landing-cta">
        <Reveal>
          <h3 className="landing-h3 light">Start specifying smarter</h3>
          <p className="landing-lead light">Type your project need above and get a ranked, source-backed recommendation in seconds.</p>
          <a className="landing-btn primary" href="#top">Try NIRA AI <ArrowRight size={16} /></a>
        </Reveal>
      </section>
    </div>
  );
}
