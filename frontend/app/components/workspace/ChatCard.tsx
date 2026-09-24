"use client";

import { DotsThreeVertical, FilePdf, House, Plus } from "@phosphor-icons/react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import Orb from "./Orb";

type ChatCardProps = {
  title: string;
  /** Empty state: greeting and composer sit together in the middle. */
  centered?: boolean;
  status?: string | null;
  children: ReactNode;
  footer?: ReactNode;
  canDownloadReport: boolean;
  isDownloading: boolean;
  onDownloadReport: () => void;
  onNewChat: () => void;
  onHome: () => void;
};

/** The main panel: a header pill, a scrolling body, and the composer pinned below. */
export default function ChatCard({
  title,
  centered = false,
  status,
  children,
  footer,
  canDownloadReport,
  isDownloading,
  onDownloadReport,
  onNewChat,
  onHome,
}: ChatCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointer = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    menuRef.current?.querySelector<HTMLButtonElement>("[role='menuitem']:not(:disabled)")?.focus();
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  function run(action: () => void) {
    setMenuOpen(false);
    action();
  }

  return (
    <section
      aria-label="Conversation"
      className={`ws-card${centered ? " is-centered" : ""}`}
      id="top"
      tabIndex={-1}
    >
      <header className="ws-card-head">
        <h2 className="ws-card-title">
          <Orb size="sm" />
          {title}
        </h2>
        <div className="ws-card-actions">
          {status ? <span className="ws-chip-status">{status}</span> : null}
          <div className="ws-menu" ref={menuRef}>
            <button
              aria-expanded={menuOpen}
              aria-haspopup="menu"
              aria-label="More actions"
              className="ws-icon-btn"
              onClick={() => setMenuOpen((open) => !open)}
              ref={buttonRef}
              type="button"
            >
              <DotsThreeVertical aria-hidden="true" size={20} weight="bold" />
            </button>
            {menuOpen ? (
              <div className="ws-menu-list" role="menu">
                <button
                  className="ws-menu-item"
                  disabled={!canDownloadReport || isDownloading}
                  onClick={() => run(onDownloadReport)}
                  role="menuitem"
                  type="button"
                >
                  <FilePdf aria-hidden="true" size={17} weight="duotone" />
                  {isDownloading ? "Preparing PDF…" : "Download PDF report"}
                </button>
                <button className="ws-menu-item" onClick={() => run(onNewChat)} role="menuitem" type="button">
                  <Plus aria-hidden="true" size={17} weight="bold" />
                  New chat
                </button>
                <button className="ws-menu-item" onClick={() => run(onHome)} role="menuitem" type="button">
                  <House aria-hidden="true" size={17} weight="duotone" />
                  Back to the home page
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <div className="ws-card-body">{children}</div>
      {footer ? <div className="ws-card-foot">{footer}</div> : null}
    </section>
  );
}
