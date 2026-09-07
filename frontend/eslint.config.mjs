import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

/**
 * Next 16 dropped the `next lint` command and ships flat config directly, so
 * ESLint is wired up here rather than through FlatCompat.
 *
 * The project previously had no linter at all — `npm run lint` was aliased to
 * `tsc --noEmit`, which checks types and nothing else. Type-checking now has
 * its own script (`npm run typecheck`) and `npm run check` runs lint, types and
 * a production build together.
 */
const config = [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "design/**",
      "preview/**",
      "public/**",
      "next-env.d.ts",
    ],
  },
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    rules: {
      // The market grid renders remote catalog URLs and the landing serves
      // pre-sized static files; moving both to next/image is its own task, so
      // this stays visible as a warning rather than blocking the build.
      "@next/next/no-img-element": "warn",
      "react-hooks/exhaustive-deps": "warn",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
];

export default config;
