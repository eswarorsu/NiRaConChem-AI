"use client";

import Image from "next/image";
import { useRef } from "react";

import { gsap, useGSAP } from "../../lib/gsap";
import { LAYER_TAGS, LAYERS } from "./landing.data";

/** Resting separation between layers, as a share of the image height.
 *  Keep in step with the transform on .lp-layer-img in landing.css. */
const GAP = 0.09;

/**
 * The one scroll moment on the page. The roof build-up is rendered as six
 * transparent images from a single camera, so the layers can be lifted apart
 * without anything drifting out of register.
 *
 * The resting state (no JS, reduced motion, narrow screens) is the build-up
 * already pulled apart, with every layer named. On wide screens the section
 * pins and scrolling separates the layers one at a time.
 */
export default function BuildUp() {
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference) and (min-width: 1100px)", () => {
        const layers = gsap.utils.toArray<HTMLElement>(".lp-layer-img");
        const items = gsap.utils.toArray<HTMLElement>(".lp-build-list li");
        const tags = gsap.utils.toArray<HTMLElement>(".lp-layer-tag");

        // At rest (CSS) each layer is lifted by --i × GAP of its own height. GSAP
        // reads that transform as its starting y, so y: 0 is the stacked roof;
        // each step then lifts one layer, and everything above it, by one GAP.

        const tl = gsap.timeline({
          defaults: { ease: "power2.inOut" },
          scrollTrigger: {
            trigger: root.current,
            start: "top top",
            end: "+=160%",
            scrub: 0.8,
            pin: ".lp-build-pin",
            invalidateOnRefresh: true,
          },
        });

        const gap = () => GAP * layers[0].offsetHeight;

        tl.set(layers, { y: 0 });
        tl.set(items, { autoAlpha: 0.28 });
        tl.set(tags, { autoAlpha: 0, scale: 0.6 });
        tl.to(items[0], { autoAlpha: 1, duration: 0.4 }, 0);
        tl.to(tags[0], { autoAlpha: 1, scale: 1, duration: 0.4 }, 0);

        // Step k lifts layer k and everything resting on it by one gap.
        for (let k = 1; k < layers.length; k += 1) {
          const at = 0.4 + (k - 1);
          tl.to(layers.slice(k), { y: () => `-=${gap()}`, duration: 1 }, at);
          tl.to(items[k], { autoAlpha: 1, duration: 0.5 }, at + 0.35);
          tl.to(tags[k], { autoAlpha: 1, scale: 1, duration: 0.5 }, at + 0.45);
        }
        tl.to({}, { duration: 0.5 });
      });
    },
    { scope: root },
  );

  return (
    <section aria-labelledby="lp-build-title" className="lp-build" id="how" ref={root}>
      <div className="lp-build-pin">
        <div className="lp-build-copy">
          <h2 className="lp-h2" id="lp-build-title">
            A roof is a system, not a product.
          </h2>
          <p className="lp-build-lede">
            Each layer has its own datasheet, its own limits and its own way of failing in Gulf
            sun. Ask about the one you are stuck on, and NiRa answers from the maker&rsquo;s page,
            not from memory.
          </p>
          <ol className="lp-build-list">
            {LAYERS.map((layer, i) => (
              <li key={layer.key}>
                <span aria-hidden="true" className="lp-build-n">
                  {i + 1}
                </span>
                <div>
                  <h3>{layer.name}</h3>
                  <p>{layer.note}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div aria-hidden="true" className="lp-build-art">
          <div className="lp-build-stack">
            {LAYERS.map((layer, i) => (
              <div
                className="lp-layer-img"
                data-i={i}
                key={layer.key}
                style={{ zIndex: i + 1, ["--i" as string]: i }}
              >
                <Image
                  alt=""
                  fill
                  sizes="(min-width: 1100px) 46vw, 92vw"
                  src={`/landing/roof-layer-${i + 1}-${layer.key}.webp`}
                />
                <span
                  className="lp-layer-tag"
                  style={{ left: `${LAYER_TAGS[i].x * 100}%`, top: `${LAYER_TAGS[i].y * 100}%` }}
                >
                  {i + 1}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
