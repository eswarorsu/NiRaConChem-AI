"use client";

import Image from "next/image";

type CloseProps = {
  onTryAi: () => void;
  canInstall: boolean;
  onInstall: () => void;
};

/** The last screen: water beading on a coated slab, and the one thing to do next. */
export default function Close({ onTryAi, canInstall, onInstall }: CloseProps) {
  return (
    <section aria-labelledby="lp-close-title" className="lp-close">
      <Image
        alt=""
        className="lp-close-img"
        fill
        sizes="100vw"
        src="/landing/close-droplets.webp"
      />
      <div className="lp-close-inner">
        <h2 className="lp-close-line" id="lp-close-title">
          Ask about your site.
        </h2>
        <p className="lp-close-sub">
          Describe the substrate, the exposure and what has to stop. NiRa does the reading.
        </p>
        <div className="lp-close-actions">
          <button className="lp-btn" onClick={onTryAi} type="button">
            Describe a condition
          </button>
          {canInstall ? (
            <button className="lp-textlink" onClick={onInstall} type="button">
              Install the app
            </button>
          ) : null}
        </div>
      </div>
      <p className="lp-close-caption">Water on a coated slab, left, and a bare one. Rendered in Blender.</p>
    </section>
  );
}
