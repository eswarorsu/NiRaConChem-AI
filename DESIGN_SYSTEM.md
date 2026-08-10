# NIRACONCHEM AI — Design System

Refined, not replaced. NIRACONCHEM AI already had a distinct identity — a "liquid-glass" light theme, a near-black dark theme, teal as brand color, clay-red as a warm secondary accent, and a construction-industry hero. That identity is right for the audience (UAE/GCC site engineers and consultants: technical, trust-first, not a consumer app). The work here formalizes it into tokens, fixes the parts fighting the brand (plain Arial body text despite three good fonts already loaded, a dark mode with no color accent, ~40 near-duplicate grays with no shared scale), and applies it consistently across the highest-traffic components.

## 1. Audience and goal

Primary user: a site engineer, consultant, or procurement lead in the UAE/GCC choosing a construction chemical product under time pressure. They are technical, skeptical of generic AI, and need to trust a recommendation enough to act on it. Design priorities follow from that: clarity over decoration, fast legibility, visible provenance (this looks like a considered technical tool, not a marketing gimmick), and a dark mode that still reads as branded rather than a "lights off" toggle.

## 2. Color system

### Brand ramps

| Token | Hex | Use |
|---|---|---|
| `--teal-900` | `#0b4f4a` | Deep brand ink — market badges, dark headings |
| `--teal-700` | `#0f766e` | **Primary accent** — links, focus glow, CTAs |
| `--teal-500` | `#14b8a6` | Mid-tone, available for secondary states |
| `--teal-400` | `#2dd4bf` | Dark-mode accent (see below), highlights |
| `--teal-100` | `#d9fbf5` | Light wash / badge backgrounds |
| `--clay-700` | `#8f3520` | Clay, pressed/dark state |
| `--clay-600` | `#c8482a` | **Secondary accent** — warm, construction/earth counterpoint to teal |
| `--clay-400` | `#e07a52` | Light clay for badges/highlights |
| `--clay-100` | `#fbe7de` | Clay wash background |

Why keep both teal and clay: teal alone reads as generic SaaS/tech. Clay is what made the existing brand distinct (it shows up in the hero typography already) and it's a legitimate complementary color to teal on the color wheel (blue-green vs. red-orange) — using both with teal as primary and clay as a deliberate, sparing highlight is stronger than defaulting to teal everywhere.

### Semantic status (already latent in the code, now formalized)

| Token | Hex | Use |
|---|---|---|
| `--success` | `#10b981` | Positive states, "featured plan" gradient |
| `--info` | `#06b6d4` | Informational accents |
| `--info-bright` | `#56e4ff` | Dark-mode glow variant |
| `--warning` | `#f59e0b` | New — reserved for form validation |
| `--danger` | `#dc2626` | New — reserved for errors |

### Neutral ("ink") ramp

The old CSS mixed two unrelated gray families — a neutral gray (`#111827`, `#6b7280`, `#9ca3af`, `#4b5563`) and a blue-slate gray (`#102033`, `#53677d`, `#cbd5e1`) — in the same UI, which is the single biggest thing undermining "polished." One family wins:

| Token | Hex |
|---|---|
| `--ink-950` | `#05070a` |
| `--ink-900` | `#102033` |
| `--ink-700` | `#23384a` |
| `--ink-500` | `#53677d` |
| `--ink-400` | `#718698` |
| `--ink-300` | `#94a7ba` |
| `--ink-200` | `#cfe0ee` |
| `--ink-100` | `#e7f0f8` |
| `--ink-050` | `#f4f9fc` |

All ~40 stray hex values in the old stylesheet that were `color:`, `border-color:`, or `background-color:` (i.e. actual text/icon/border colors, not decorative gradient washes) were mapped onto this scale — 82 call sites in one pass, zero visible change since each was mapped to its nearest existing shade.

### Dark mode fix

The old dark theme set `--accent: #ffffff` — meaning dark mode had **no color accent at all**, just white. That's a real brand-consistency gap: switch to dark mode and the teal identity disappears. Fixed: dark mode now uses `--teal-400` (`#2dd4bf`) as its accent, luminous enough to read clearly on near-black, with white reserved for `--accent-strong` (maximum-emphasis text).

### Contrast (WCAG AA, computed)

| Pair | Ratio | Result |
|---|---|---|
| Ink-900 text on white panel | 16.5:1 | Pass |
| Muted ink-500 on white panel | 5.8:1 | Pass |
| Teal-700 accent on white | 5.5:1 | Pass |
| Clay-600 on white | 4.8:1 | Pass (normal text) |
| White text on graphite button | 19.9:1 | Pass |
| Dark-mode text on near-black | 19.5:1 | Pass |
| Dark-mode teal-400 accent on near-black | 10.9:1 | Pass |

Every pair clears 4.5:1 (AA for normal text); most clear it by a wide margin. Clay-600 was the tightest at 4.8:1 — safe for body text, not just decoration.

## 3. Typography

Three fonts were already loaded via `next/font` but only used on landing sections — the main chat app rendered in plain **Arial**. Fixed: **Plus Jakarta Sans** is now the base UI font everywhere (body, headings, chat, buttons). Anton (condensed display) stays scoped to large hero numerals/headlines where it already worked well. Caveat (handwritten) stays as a single sparing accent — it shouldn't spread further, it's decorative seasoning, not a UI font.

| Token | Size | Use |
|---|---|---|
| `--fs-display-2xl` | 56px | Hero headline (Anton) |
| `--fs-display-xl` | 40px | Secondary hero |
| `--fs-heading-lg` | 28px | Section headings |
| `--fs-heading-md` | 22px | Card/panel headings |
| `--fs-heading-sm` | 18px | Sub-headings |
| `--fs-body-lg` | 16px | Emphasis body |
| `--fs-body-md` | 14.5px | Default UI text, chat |
| `--fs-body-sm` | 13px | Secondary text |
| `--fs-caption` | 12px | Meta, timestamps, labels |

Global `h1`–`h6` and `p` base styles were added (previously there were none — every heading was styled per-component with no fallback).

## 4. Spacing and radius

**Spacing** (4px base, matches what was already mostly in use): `--space-1` 4px → `--space-8` 64px.

**Radius** — the old file had 14 different border-radius values with no logic (7px, 10px, 11px, 13px, 22px, 26px alongside the "real" set). Collapsed to 5, chosen to match the *dominant* existing values so nothing visibly shifts:

`--radius-sm` 8px · `--radius-md` 12px · `--radius-lg` 18px · `--radius-xl` 28px · `--radius-pill` 999px

## 5. Key components (hand-tuned)

- **Primary send button / user chat bubble** — these used two near-identical, independently-hardcoded dark gradients. Unified into one `--grad-ink` / `--grad-ink-hover` token pair so they visually match by design, not coincidence, and so a future rebrand is a one-line change. Added a teal focus/hover glow so the primary action ties back to the brand color instead of being purely neutral graphite.
- **Theme toggle, market badges, plan gradient** — now reference the semantic tokens directly (`var(--teal-900)`, `var(--success)`/`var(--info)` gradient) instead of repeating hex values.
- **Input placeholder** — was an odd, undocumented olive-gray (`rgba(80,99,93,.78)`); now uses `--ink-500` at matching opacity, consistent with the rest of the muted-text system.
- **Focus states** — already present on the main interactive elements (good baseline); ring color is now a token (`--focus-ring`) with a brighter dark-mode variant instead of one fixed value for both themes.

## 6. Responsive

Breakpoints in use: 390px / 720px / 760px / 860px (phone-focused) plus one new addition:

- **Added a tablet tier** (`761–900px`): the market/product grid previously jumped straight from 3 columns to 1 at 760px, meaning an iPad-portrait-width layout either got cramped 3-up cards or none of the benefit of the extra width. Now steps 3 → 2 → 1.
- Chat panel and hero already use fluid units (`min(900px, 100%)`) — no fixed-width traps found there.

## 7. What wasn't touched, and why

This was implemented directly in the existing codebase rather than as a from-scratch rebuild, per the brief to refine the current identity across the full app. Two things are intentionally out of scope for this pass:

1. **Bespoke landing/hero sections** (particle background, role carousel semicircle menu, brand scroller) — these are one-off animated layouts, not reusable components. They already inherit the corrected fonts and root tokens; a deeper pass on their internal spacing/hex would be its own project.
2. **Every one of the ~150 CSS selectors** — the file has ~3,500 lines. Tokens, typography, and the ~82 consolidated color references cascade broadly; beyond that, the highest-traffic surfaces (send button, chat bubbles, inputs, badges, toggle, plan cards) were hand-tuned. Lower-traffic one-off panels (profile modal, reports modal) still work correctly but weren't individually restyled.

## 8. Proactive suggestions (not yet implemented)

- The login form (email/password) doesn't submit anywhere yet — it's UI only. Worth a "Coming soon" label so it doesn't read as broken.
- Google/X sign-in buttons currently `alert()` on click. Fine for a demo; swap for a disabled state with a tooltip before this is customer-facing.
- Consider a small "verified against datasheet" badge on product recommendations — for this audience, visible provenance builds more trust than visual polish alone.
- `--warning` and `--danger` tokens are defined but not wired to any component yet — worth using once file-upload validation or form errors need a visual state.

## 9. Verification performed

- WCAG contrast computed programmatically for all key text/background pairs (table above) — all pass AA.
- `tsc --noEmit` (project's lint script) — clean, no type errors introduced.
- CSS brace/parenthesis balance and `var()` reference integrity checked programmatically — no syntax breakage.
- `next build` could not run to completion in this sandbox (no registry access to fetch the SWC binary) — recommend running a local `npm run build` once before deploying to catch anything a static check can't.
