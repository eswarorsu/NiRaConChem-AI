"use client";

import type { ReactNode } from "react";

// The display serif belongs to this surface only, so it loads with it rather
// than in the root layout. Plus Jakarta Sans (loaded in layout.tsx) carries
// every line of UI and body copy.
import "@fontsource-variable/cormorant-garamond/wght.css";
import "@fontsource-variable/cormorant-garamond/wght-italic.css";

import BuildUp from "./BuildUp";
import Close from "./Close";
import HeroScene from "./HeroScene";
import { scrollToId } from "./nav";
import Proof from "./Proof";
import SiteFooter from "./SiteFooter";
import SiteNav from "./SiteNav";
import "./landing.css";

type LandingPageProps = {
  /** The application's live search form, owned by the page so its state stays put. */
  searchSlot: ReactNode;
  /** Brings the user back to the search field and focuses it. */
  onTryAi: () => void;
  canInstall: boolean;
  onInstall: () => void;
};

/**
 * The marketing surface of NiRaConChem AI. It renders only while no chat has
 * started; the moment a query is sent the page swaps to the workspace.
 *
 * Four beats, nothing more: a rendered dusk scene with the live search and a
 * real product answer, the roof build-up pulled apart layer by layer, where the
 * answers come from, and the close. All three pictures are Blender renders
 * made for this page (see scripts/landing-renders/).
 */
export default function LandingPage({ searchSlot, onTryAi, canInstall, onInstall }: LandingPageProps) {
  return (
    <div className="lp">
      <SiteNav onTryAi={onTryAi} />
      <HeroScene onShowLayers={() => scrollToId("how")} searchSlot={searchSlot} />
      <BuildUp />
      <Proof />
      <Close canInstall={canInstall} onInstall={onInstall} onTryAi={onTryAi} />
      <SiteFooter onTryAi={onTryAi} />
    </div>
  );
}
