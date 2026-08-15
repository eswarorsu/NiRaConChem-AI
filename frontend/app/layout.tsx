import type { Metadata } from "next";
import { Lora, Playfair_Display } from "next/font/google";
import { ServiceWorkerRegistration } from "./components/ServiceWorkerRegistration";
import "./globals.css";

// Body serif for the cream paper theme. The CSS variable keeps its original
// name so the ~13 font-family declarations in globals.css don't need edits.
const jakarta = Lora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-jakarta",
  display: "swap",
});

const displayFont = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "700", "800", "900"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  applicationName: "NIRACONCHEM AI",
  title: "NIRACONCHEM AI",
  description: "UAE construction chemicals recommendation agent",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "NIRACONCHEM AI",
  },
  icons: {
    icon: [
      {
        url: "/assets/atom-logo-transparent.png.png",
        sizes: "512x512",
        type: "image/png",
      },
    ],
    apple: [
      {
        url: "/assets/atom-logo-transparent.png.png",
        sizes: "180x180",
        type: "image/png",
      },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${jakarta.variable} ${displayFont.variable}`}>
      <body>
        {children}
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
