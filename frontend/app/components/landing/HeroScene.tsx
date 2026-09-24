"use client";

import Image from "next/image";
import { useCallback, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import { gsap, useGSAP } from "../../lib/gsap";
import { COUNTS, SPOTS, VILLA_BOX, type SpotKey } from "./landing.data";

type HeroSceneProps = {
  searchSlot: ReactNode;
  onShowLayers: () => void;
};

const fmt = new Intl.NumberFormat("en-US");

/**
 * The hero is one rendered scene in three depths: the desert plate, the product
 * card, and the villa cut-out in front of it. The card sits *behind* the villa,
 * so the roof breaks over its lower edge. The tabs on the card switch between
 * four real products from the index.
 */
export default function HeroScene({ searchSlot, onShowLayers }: HeroSceneProps) {
  const root = useRef<HTMLElement>(null);
  const [active, setActive] = useState<SpotKey>("roof");
  const spot = SPOTS.find((item) => item.key === active) ?? SPOTS[0];

  const tabRefs = useRef<Record<SpotKey, HTMLButtonElement | null>>({
    roof: null,
    facade: null,
    joints: null,
    repair: null,
  });

  // Depth: pointer parallax on fine pointers, a slow drift of the plate on scroll.
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(
        "(prefers-reduced-motion: no-preference) and (pointer: fine) and (min-width: 1100px)",
        () => {
          const layers = gsap.utils.toArray<HTMLElement>("[data-depth]");
          const movers = layers.map((el) => {
            const depth = Number(el.dataset.depth);
            return {
              depth,
              x: gsap.quickTo(el, "x", { duration: 1.1, ease: "power3.out" }),
              y: gsap.quickTo(el, "y", { duration: 1.1, ease: "power3.out" }),
            };
          });
          const onMove = (event: PointerEvent) => {
            const nx = event.clientX / window.innerWidth - 0.5;
            const ny = event.clientY / window.innerHeight - 0.5;
            for (const mover of movers) {
              mover.x(-nx * 22 * mover.depth);
              mover.y(-ny * 12 * mover.depth);
            }
          };
          window.addEventListener("pointermove", onMove, { passive: true });
          return () => window.removeEventListener("pointermove", onMove);
        },
      );
      mm.add("(prefers-reduced-motion: no-preference) and (min-width: 1100px)", () => {
        gsap.to(".lp-plate-drift", {
          yPercent: 7,
          ease: "none",
          scrollTrigger: { trigger: root.current, start: "top top", end: "bottom top", scrub: true },
        });
      });
    },
    { scope: root },
  );

  // Answer swap: the card's copy fades over to the chosen part.
  const choose = useCallback(
    (key: SpotKey, focusTab = false) => {
      if (key === active) return;
      setActive(key);
      if (focusTab) tabRefs.current[key]?.focus();
    },
    [active],
  );

  const first = useRef(true);
  useGSAP(
    () => {
      if (first.current) {
        first.current = false;
        return;
      }
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      gsap.fromTo(
        ".lp-answer > *",
        { autoAlpha: 0, y: 8 },
        { autoAlpha: 1, y: 0, duration: 0.45, stagger: 0.05, ease: "power2.out", overwrite: true },
      );
    },
    { scope: root, dependencies: [active], revertOnUpdate: false },
  );

  // Arrow keys, Home and End move between tabs (WAI-ARIA tabs pattern).
  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    const index = SPOTS.findIndex((item) => item.key === active);
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % SPOTS.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + SPOTS.length) % SPOTS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = SPOTS.length - 1;
    else return;
    event.preventDefault();
    choose(SPOTS[next].key, true);
  };

  return (
    <section aria-labelledby="lp-hero-title" className="lp-hero" id="top" ref={root}>
      <div aria-hidden="true" className="lp-scene">
        <div className="lp-frame lp-plate" data-depth="0.35">
          <div className="lp-plate-drift">
            <Image
              alt=""
              className="lp-plate-img"
              fetchPriority="high"
              fill
              preload
              sizes="(min-width: 1100px) 120vw, 200vw"
              src="/landing/hero-plate.webp"
            />
          </div>
        </div>

        <div className="lp-frame lp-villa-frame" data-depth="1">
          <div
            className="lp-villa"
            style={{
              left: `${VILLA_BOX.left * 100}%`,
              top: `${VILLA_BOX.top * 100}%`,
              width: `${VILLA_BOX.width * 100}%`,
              height: `${VILLA_BOX.height * 100}%`,
            }}
          >
            <Image
              alt=""
              fetchPriority="high"
              fill
              loading="eager"
              sizes="(min-width: 1100px) 72vw, 125vw"
              src="/landing/hero-villa.webp"
            />
          </div>
        </div>

        <div className="lp-shade" />
      </div>

      <div className="lp-hero-copy">
        <h1 className="lp-title" id="lp-hero-title">
          <span className="lp-title-line">
            <span>The right</span>
          </span>
          <span className="lp-title-line">
            <span>chemistry</span>
          </span>
        </h1>
        <p className="lp-hero-tag">for every layer of a Gulf building</p>
        <p className="lp-hero-lede">
          Describe the condition on site. NiRa reads {fmt.format(COUNTS.profiles)} manufacturer
          product profiles and answers with the system that fits, and the datasheet it came from.
        </p>
        <div className="lp-hero-search">{searchSlot}</div>
      </div>

      <div className="lp-card" data-depth="0.6">
        <div aria-label="Parts of the building" className="lp-tabs" role="tablist">
          {SPOTS.map((item) => (
            <button
              aria-controls="lp-answer"
              aria-selected={item.key === active}
              className="lp-tab"
              id={`lp-tab-${item.key}`}
              key={item.key}
              onClick={() => choose(item.key)}
              onKeyDown={onTabKey}
              ref={(el) => {
                tabRefs.current[item.key] = el;
              }}
              role="tab"
              tabIndex={item.key === active ? 0 : -1}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>

        <div
          aria-labelledby={`lp-tab-${spot.key}`}
          className="lp-answer"
          id="lp-answer"
          role="tabpanel"
        >
          <h2 className="lp-answer-name">{spot.product.name}</h2>
          <p className="lp-answer-summary">{spot.summary}</p>
          <p className="lp-answer-fact">
            <span>{spot.fact.term}</span> {spot.fact.value}
          </p>
          <a
            className="lp-answer-link"
            href={spot.product.datasheetUrl}
            rel="noopener noreferrer"
            target="_blank"
          >
            {spot.product.manufacturer} datasheet
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </div>

        <button className="lp-thumb" onClick={onShowLayers} type="button">
          <span className="lp-thumb-label">Layer view</span>
          <span className="lp-thumb-img">
            <Image alt="" fill sizes="160px" src="/landing/roof-stack-thumb.webp" />
          </span>
          <span aria-hidden="true" className="lp-thumb-play">
            <svg viewBox="0 0 24 24">
              <path d="M9 7.2v9.6c0 .6.7 1 1.2.6l7-4.8c.4-.3.4-.9 0-1.2l-7-4.8C9.7 6.2 9 6.6 9 7.2Z" />
            </svg>
          </span>
          <span className="sr-only">: see the roof build-up, layer by layer</span>
        </button>
      </div>

      <div className="lp-band">
        <article className="lp-band-card">
          <h2>Every layer, from the datasheet</h2>
          <p>Primer to tile, each answer is traced to the maker&rsquo;s own page.</p>
          <div aria-hidden="true" className="lp-band-card-img">
            <Image alt="" fill sizes="(min-width: 1100px) 240px, 50vw" src="/landing/roof-stack-card.webp" />
          </div>
        </article>

        <div className="lp-band-stat">
          <ul aria-label="Manufacturers in the index" className="lp-coins">
            <li>
              <Image alt="Sika" height={44} src="/landing/coin-sika.webp" width={44} />
            </li>
            <li>
              <Image alt="Mapei" height={44} src="/landing/coin-mapei.webp" width={44} />
            </li>
            <li>
              <Image alt="Fosroc" height={44} src="/landing/coin-fosroc.webp" width={44} />
            </li>
          </ul>
          <p className="lp-stat">
            <span className="lp-stat-n">{fmt.format(COUNTS.profiles)}</span>
            <span className="lp-stat-t">
              product profiles from {COUNTS.manufacturers} manufacturers
            </span>
          </p>
        </div>

        <div className="lp-band-note">
          <p>From site condition to specified system</p>
          <a
            href="#how"
            onClick={(event) => {
              event.preventDefault();
              onShowLayers();
            }}
          >
            See how it works
          </a>
        </div>
      </div>
    </section>
  );
}
