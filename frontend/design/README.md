# design/

Source material that is **not** served to the browser.

`source-images/` holds photography and artwork that is no longer referenced by
any component. It was moved out of `public/` so the deployed static output only
contains files the site actually requests — `public/` is copied verbatim into
every build and deploy, so unreferenced files there inflate the artifact even
though they cost the visitor nothing.

Nothing here is deleted: this is the pool to draw on when the landing page moves
from CSS-drawn visuals to real imagery. Anything promoted back into `public/`
should be resized and converted first (see `scripts/`).
