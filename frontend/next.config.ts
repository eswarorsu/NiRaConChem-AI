import path from "node:path";

import type { NextConfig } from "next";

// The app lives in frontend/. Vercel builds from the repository root and sets
// outputFileTracingRoot to it, and Turbopack's root has to be the same folder or
// Next warns on every build. Locally both stay on frontend/ so the dev server
// does not watch the backend and data folders next to it.
const projectRoot = process.env.VERCEL ? path.join(__dirname, "..") : __dirname;

const nextConfig: NextConfig = {
  outputFileTracingRoot: projectRoot,
  turbopack: {
    root: projectRoot,
  },
  images: {
    // The market grid falls back to the supplier's own CDN for the products
    // whose thumbnails have not been mirrored locally. next/image refuses any
    // host that is not declared, so this is the allowlist rather than a
    // convenience.
    remotePatterns: [{ protocol: "https", hostname: "qconinternational.com" }],
    formats: ["image/avif", "image/webp"],
  },
  // Trims the response by a few hundred bytes per request and stops advertising
  // the framework version.
  poweredByHeader: false,
};

export default nextConfig;
