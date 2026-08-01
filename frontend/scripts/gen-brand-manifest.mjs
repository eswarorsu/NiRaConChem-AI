// scripts/gen-brand-manifest.mjs
// Scans public/brands for image files and writes public/brands/manifest.json
// so the client BrandScroller can load every logo without fs access.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const dir = path.join(root, "public", "brands");
const exts = new Set([".png", ".jpg", ".jpeg", ".svg", ".webp"]);

const logos = fs
  .readdirSync(dir)
  .filter((f) => exts.has(path.extname(f).toLowerCase()))
  .map((f) => `/brands/${f}`)
  .sort();

fs.writeFileSync(
  path.join(dir, "manifest.json"),
  JSON.stringify({ logos }, null, 2) + "\n",
);

console.log(`Wrote manifest with ${logos.length} brand logos.`);
