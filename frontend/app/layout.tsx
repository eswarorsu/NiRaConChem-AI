import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NIRACONCHEM AI",
  description: "UAE construction chemicals recommendation agent",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
