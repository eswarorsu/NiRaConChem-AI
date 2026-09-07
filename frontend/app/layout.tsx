import type { Metadata, Viewport } from "next";

// One typeface, self-hosted (fontsource) rather than fetched through
// next/font/google. Three reasons: the build needs no network access to
// fonts.googleapis.com, there is no third-party request at runtime, and the
// exact files that were design-reviewed are the ones that ship.
//
// Plus Jakarta Sans carries every size — display, body, UI and figures. The
// earlier mixed serif/grotesque/mono stack is gone: three families competing
// on one page was a large part of what read as assembled rather than designed.
import "@fontsource-variable/plus-jakarta-sans";
// Doto is the dot-matrix face used by the closing wordmark and nothing else.
// It is the licensable stand-in for OffBit DotBold — see the @font-face block
// at the top of landing.css, which takes over the moment the licensed file is
// dropped into public/fonts/.
import "@fontsource-variable/doto/full.css";

import { ServiceWorkerRegistration } from "./components/ServiceWorkerRegistration";
import "./globals.css";
// Loaded after globals so the Warm Glow layer wins the cascade while the older
// rules in globals.css are retired component by component.
import "./styles/app-surface.css";
import "./styles/a11y.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL?.trim() || "http://localhost:3000";

const TITLE = "NiRaConChem AI — construction chemical intelligence";
const DESCRIPTION =
  "AI-powered construction chemical recommendations for smarter, faster and more reliable project decisions. Built for UAE construction.";

export const metadata: Metadata = {
  // Without metadataBase, Next emits relative OG/Twitter image URLs, which every
  // social and chat scraper rejects — the link preview silently falls back to a
  // grey box. Set NEXT_PUBLIC_SITE_URL in the deploy environment.
  metadataBase: new URL(SITE_URL),
  applicationName: "NiRaConChem AI",
  title: {
    default: TITLE,
    template: "%s · NiRaConChem AI",
  },
  description: DESCRIPTION,
  manifest: "/manifest.webmanifest",
  keywords: [
    "construction chemicals",
    "waterproofing",
    "concrete repair",
    "UAE construction",
    "product recommendation",
    "technical datasheet",
  ],
  authors: [{ name: "NiRaConChem AI" }],
  openGraph: {
    type: "website",
    siteName: "NiRaConChem AI",
    title: TITLE,
    description: DESCRIPTION,
    url: SITE_URL,
    locale: "en_AE",
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "NiRaConChem AI",
  },
  // app/icon.png and app/apple-icon.png are picked up automatically by the App
  // Router, so the icon set is no longer declared by hand.
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f5ee" },
    { media: "(prefers-color-scheme: dark)", color: "#14110d" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#top">
          Skip to content
        </a>
        {children}
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
