# Landing page renders

Every picture on the landing page is a Blender render made from these scripts.
Nothing is a stock photo, and nothing needs the Blender app: the scripts run on
the `bpy` Python module (Blender 5.0) with Cycles on the CPU.

```bash
pip install bpy            # Blender as a Python module (Python 3.11)
cd frontend/scripts/landing-renders

python3 hero.py both 2560 64 /tmp/renders        # desert plate + villa cut-out (~20 min on 2 cores)
curl -LO https://raw.githubusercontent.com/pmndrs/drei-assets/master/hdri/studio_small_03_1k.hdr
python3 buildup.py 1600 64 /tmp/renders/b2 all   # roof build-up: stack + one image per layer (~25 min)
python3 droplets.py 1920 40 /tmp/renders         # water beading on a coated slab (~5 min)
python3 export.py /tmp/renders ../.. /tmp/renders/b2 1600   # crop, encode WebP, write public/landing/
```

`export.py` prints `VILLA_BOX`, `LAYER_TAGS` and the layer aspect ratio. Copy
them into `app/components/landing/landing.data.ts` (and the aspect ratio into
`.lp-build-stack` in `landing.css`) whenever the cameras or models change —
they are what keep the hotspots and layer numbers on the right pixels.

| Script | Scene |
| --- | --- |
| `hero.py` | Concrete villa with a rounded, finned upper floor on a sand plain; dunes and a hazy ridge behind; dusk sky with the pink Belt of Venus band. Rendered twice from one camera — the plate without the villa, the villa alone over a shadow catcher — so the page can move them at different depths. |
| `buildup.py` | Stepped cutaway of a Gulf roof: saw-cut slab with aggregate and rebar, epoxy primer, polyurea membrane, XPS boards, sand-cement screed, porcelain tiles on a combed adhesive bed. Lit by Poly Haven's "Studio Small 03" HDRI (CC0, via the pmndrs/drei-assets GitHub repo) plus three area lights. Rendered as one stack and as six transparent layers in register. |
| `droplets.py` | Macro with shallow focus: water beads on the coated half of a slab and soaks into the bare half. |
| `common.py` | Materials, fog, geometry helpers shared by the three scenes. |
