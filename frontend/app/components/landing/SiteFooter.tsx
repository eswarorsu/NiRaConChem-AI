"use client";

import { NAV_LINKS, scrollToId } from "./nav";

type SiteFooterProps = {
  onTryAi: () => void;
};

export default function SiteFooter({ onTryAi }: SiteFooterProps) {
  return (
    <footer className="lp-footer">
      <div className="lp-footer-top">
        <p className="lp-footer-mark">NiRaConChem</p>
        <nav aria-label="Footer" className="lp-footer-links">
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
            <li>
              <button onClick={onTryAi} type="button">
                Ask NiRa
              </button>
            </li>
          </ul>
        </nav>
      </div>
      <div className="lp-footer-bottom">
        <p>Construction chemical intelligence for the UAE and GCC.</p>
        <p>&copy; {new Date().getFullYear()} NiRaConChem AI</p>
      </div>
    </footer>
  );
}
