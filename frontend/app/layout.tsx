import type { Metadata } from "next";
import { Anton, Caveat, Plus_Jakarta_Sans } from "next/font/google";
import { ServiceWorkerRegistration } from "./components/ServiceWorkerRegistration";
import "./globals.css";

const handFont = Caveat({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-hand",
  display: "swap",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-jakarta",
  display: "swap",
});

const displayFont = Anton({
  subsets: ["latin"],
  weight: ["400"],
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
    <html lang="en" className={`${handFont.variable} ${jakarta.variable} ${displayFont.variable}`}>
      <body>
        {children}
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
