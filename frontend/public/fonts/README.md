# Fonts served from /public

## OffBit DotBold — the closing wordmark

The giant `NiRaConChem` mark at the foot of the landing page is set in
**OffBit DotBold**.

**Licence.** OffBit is a commercial typeface by Power Type Foundry. The free
download covers *personal use only* — a public, commercial deployment of this
site needs a licence from https://www.fontspring.com/fonts/power-type-foundry/offbit
Please make sure one is in place before shipping.

### Files

| File | Size | What it is |
| --- | --- | --- |
| `OffBit-DotBold.woff2` | 2.7 KB | **What the site loads.** Subset to the eleven letters of "NiRaConChem". |
| `OffBit-DotBold.ttf` | 697 KB | The full face. Kept as the source for the subset and as a `src` fallback. |
| `OffBit-Dot.ttf`, `OffBit-Regular.ttf` | — | Not referenced by any stylesheet. |

### Regenerating the subset

The subset contains **only** the characters in "NiRaConChem". Change that
string in `Footer.tsx` and any new character will silently fall back to Doto,
which is obvious on the page. After such a change:

```
npm run font:wordmark        # needs: pip install fonttools brotli
```

and update the `--text=` argument in that script to match the new string.

### Fallback

`--font-wordmark` in `app/styles/tokens.css` lists **Doto**
(`@fontsource-variable/doto`, SIL Open Font Licence 1.1) after OffBit. It is the
same dot-matrix construction and is free for commercial use, so removing the
OffBit files degrades the mark rather than breaking it.
