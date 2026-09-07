# Open Graph image

`app/opengraph-image.png` (1200×630) is picked up automatically by the App
Router and referenced from the OpenGraph and Twitter metadata in
`app/layout.tsx`.

It is a static PNG rather than a `next/og` `ImageResponse` for two reasons: it
costs nothing at request time, and it is rendered with the real Bodoni Moda and
Archivo files, so it matches the site exactly rather than approximating it with
whatever fonts the edge runtime happens to carry.

Regenerate it by rendering the page at 1200×630 and screenshotting, or replace
the file directly — the figures in it come from `app/components/landing/
catalog.data.ts`, so re-run `scripts/generate-landing-catalog.py` first if the
catalog has changed.
