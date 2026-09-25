import path from "node:path";

import type { NextConfig } from "next";

// The app lives in frontend/, but Vercel builds from the repository root and
// sets outputFileTracingRoot to it. Turbopack's root has to be the same folder
// or Next warns on every build, so both point at the repository root here.
const repoRoot = path.join(__dirname, "..");

const nextConfig: NextConfig = {
  outputFileTracingRoot: repoRoot,
  turbopack: {
    root: repoRoot,
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
