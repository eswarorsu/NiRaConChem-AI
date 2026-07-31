import type { Metadata } from "next";
import { ServiceWorkerRegistration } from "./components/ServiceWorkerRegistration";
import "./globals.css";

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
    <html lang="en">
      <body>
        {children}
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
