import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
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
