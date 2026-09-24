"use client";

import Image from "next/image";

import { COUNTS, MAKERS } from "./landing.data";

/** Wide wordmarks and square badges need different heights to look the same size. */
function shapeOf(width: number, height: number) {
  const ratio = width / height;
  if (ratio > 3) return "wide";
  if (ratio > 1.6) return "mid";
  return "square";
}

/** Where the answers come from. */
export default function Proof() {
  const others = COUNTS.manufacturers - MAKERS.length;

  return (
    <section aria-labelledby="lp-proof-title" className="lp-proof" id="sources">
      <div className="lp-proof-inner">
        <h2 className="lp-h2" id="lp-proof-title">
          Answers you can check.
        </h2>
        <p className="lp-proof-lede">
          Every recommendation cites the datasheet it came from. Anything NiRa cannot trace to a
          manufacturer&rsquo;s own page is left out of the answer.
        </p>

        <ul aria-label="Some of the manufacturers in the index" className="lp-makers">
          {MAKERS.map((maker) => (
            <li data-shape={shapeOf(maker.width, maker.height)} key={maker.name}>
              <Image
                alt={maker.name}
                height={maker.height}
                sizes="140px"
                src={maker.src}
                width={maker.width}
              />
            </li>
          ))}
        </ul>
        <p className="lp-makers-more">and {others} more manufacturers in the index</p>
      </div>
    </section>
  );
}
