"use client";

import Image from "next/image";

import { NAV_LINKS, scrollToId } from "./nav";

type SiteNavProps = {
  onTryAi: () => void;
};

export default function SiteNav({ onTryAi }: SiteNavProps) {
  return (
    <header className="lp-nav">
      <a
        className="lp-brand"
        href="#top"
        onClick={(event) => {
          event.preventDefault();
          scrollToId("top");
        }}
      >
        <Image alt="" height={30} src="/icons/brand-mark.png" width={30} />
        <span>NiRaConChem</span>
      </a>

      <nav aria-label="Sections" className="lp-nav-links">
        <ul>
          {NAV_LINKS.map((link) => (
            <li key={link.id}>
              <a
                href={`#${link.id}`}
                onClick={(event) => {
                  event.preventDefault();
                  scrollToId(link.id);
                }}
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <button className="lp-textlink lp-nav-cta" onClick={onTryAi} type="button">
        Ask NiRa
      </button>
    </header>
  );
}
