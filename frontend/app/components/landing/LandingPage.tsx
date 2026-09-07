"use client";

import type { ReactNode } from "react";
import Navbar from "./Navbar";
import Hero from "./Hero";
import ProblemSection from "./ProblemSection";
import BrandStrip from "./BrandStrip";
import AIEngine from "./AIEngine";
import ProductIntelligence from "./ProductIntelligence";
import RecommendationDemo from "./RecommendationDemo";
import IntelligenceNetwork from "./IntelligenceNetwork";
import Vision from "./Vision";
import FinalCTA from "./FinalCTA";
import Footer from "./Footer";
import { scrollToId } from "./nav";
// Typefaces are loaded once in app/layout.tsx — both surfaces share them now.
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
 * started; the moment the user sends a query the page swaps to the application
 * shell, which keeps its own theme. Nothing here touches app state beyond the
 * search form it is handed.
 */
export default function LandingPage({
  searchSlot,
  onTryAi,
  canInstall,
  onInstall,
}: LandingPageProps) {
  return (
    <div className="nrc">
      <div className="nrc-atmosphere" aria-hidden="true" />
      <Navbar onTryAi={onTryAi} />
      <div className="nrc-shell">
        <Hero onExploreTechnology={() => scrollToId("technology")} searchSlot={searchSlot} />
        <ProblemSection />
        <BrandStrip />
        <AIEngine />
        <ProductIntelligence />
        <RecommendationDemo onTryAi={onTryAi} />
        <IntelligenceNetwork />
        <Vision />
        <FinalCTA onTryAi={onTryAi} />
        <Footer canInstall={canInstall} onInstall={onInstall} onTryAi={onTryAi} />
      </div>
    </div>
  );
}
