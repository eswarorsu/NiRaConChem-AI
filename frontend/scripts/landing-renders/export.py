"""Turn the raw Cycles renders into the files the landing page ships.

usage: python3 export.py <renders_dir> <frontend_dir> [buildup_dir] [buildup_width]

Prints the numbers that landing.data.ts needs (VILLA_BOX, LAYER_TAGS) and the
aspect ratio .lp-build-stack uses, so a re-render never drifts out of register.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw

R = sys.argv[1] if len(sys.argv) > 1 else "/root/renders"
F = sys.argv[2] if len(sys.argv) > 2 else "/root/work/frontend"
B = sys.argv[3] if len(sys.argv) > 3 else R  # build-up renders (buildup2.py writes its own folder)
BW = int(sys.argv[4]) if len(sys.argv) > 4 else 1600
OUT = os.path.join(F, "public", "landing")
os.makedirs(OUT, exist_ok=True)


def out(name):
    return os.path.join(OUT, name)


# ---- hero plate: a whisper of grain so the sky gradient never bands ----------
plate = np.array(Image.open(f"{R}/hero-plate-2560.png").convert("RGB")).astype(np.float32)
plate += np.random.default_rng(3).normal(0, 1.4, plate.shape[:2])[..., None]
Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8)).save(out("hero-plate.webp"), quality=82, method=6)

# ---- villa cut-out: crop to what is visible, remember where it sat -----------
villa = np.array(Image.open(f"{R}/hero-villa-2560.png").convert("RGBA"))
villa[villa[..., 3] <= 6] = 0  # shadow-catcher noise below visibility
H, W = villa.shape[:2]
ys, xs = np.where(villa[..., 3] > 20)
keep = ys > 200  # a stray corner pixel on some renders
ys, xs = ys[keep], xs[keep]
pad = 10
x0, y0 = max(xs.min() - pad, 0), max(ys.min() - pad, 0)
x1, y1 = min(xs.max() + 1 + pad, W), min(ys.max() + 1 + pad, H)
Image.fromarray(villa[y0:y1, x0:x1]).save(out("hero-villa.webp"), quality=88, method=6)
villa_box = {"left": round(x0 / W, 4), "top": round(y0 / H, 4),
             "width": round((x1 - x0) / W, 4), "height": round((y1 - y0) / H, 4)}

# ---- build-up stack: the band card and the hero thumbnail --------------------
stack = Image.open(f"{B}/buildup-stack-{BW}.png").convert("RGBA")
a = np.array(stack)[..., 3]
ys, xs = np.where(a > 12)
pad = 24
crop = stack.crop((max(xs.min() - pad, 0), max(ys.min() - pad, 0),
                   min(xs.max() + 1 + pad, stack.width), min(ys.max() + 1 + pad, stack.height)))
card = crop.copy()
card.thumbnail((720, 720), Image.LANCZOS)
card.save(out("roof-stack-card.webp"), quality=88, method=6)
thumb = crop.copy()
thumb.thumbnail((420, 420), Image.LANCZOS)
bg = Image.new("RGBA", (thumb.width + 40, int((thumb.width + 40) / 1.15)), (230, 221, 213, 255))
bg.alpha_composite(thumb, ((bg.width - thumb.width) // 2, (bg.height - thumb.height) // 2))
bg.convert("RGB").save(out("roof-stack-thumb.webp"), quality=86, method=6)

# ---- build-up layers: one shared crop so they stay in register ---------------
keys = ["slab", "primer", "membrane", "insulation", "screed", "tiles"]
layers = [Image.open(f"{B}/buildup-{i + 1}-{k}-{BW}.png").convert("RGBA") for i, k in enumerate(keys)]
LW, LH = layers[0].size
bx0 = by0 = 10**9
bx1 = by1 = 0
for im in layers:
    ys, xs = np.where(np.array(im)[..., 3] > 12)
    bx0, by0 = min(bx0, xs.min()), min(by0, ys.min())
    bx1, by1 = max(bx1, xs.max() + 1), max(by1, ys.max() + 1)
pad = 20
bx0, by0, bx1, by1 = max(0, bx0 - pad), max(0, by0 - pad), min(LW, bx1 + pad), min(LH, by1 + pad)
for i, (k, im) in enumerate(zip(keys, layers)):
    c = im.crop((bx0, by0, bx1, by1))
    c.thumbnail((1200, 1200), Image.LANCZOS)
    c.save(out(f"roof-layer-{i + 1}-{k}.webp"), quality=86, method=6)
anchors = json.load(open(f"{B}/buildup-anchors.json"))
tags = []
for k in keys:
    p = anchors[k]["left"]
    tags.append({"x": round((p["x"] * LW - bx0) / (bx1 - bx0), 4),
                 "y": round((p["y"] * LH - by0) / (by1 - by0), 4)})


# ---- manufacturer coins -------------------------------------------------------
def coin(src, name, box=None, scale=0.6):
    im = Image.open(os.path.join(F, "public", "brands", src)).convert("RGBA")
    if box:
        im = im.crop(box)
    flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat.alpha_composite(im)
    trim = ImageChops.difference(flat.convert("RGB"), Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    im = im.crop(trim)
    S = 192
    c = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    im.thumbnail((int(S * scale), int(S * scale)), Image.LANCZOS)
    c.alpha_composite(im, ((S - im.width) // 2, (S - im.height) // 2))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, S - 1, S - 1), fill=255)
    c.putalpha(mask)
    c.save(out(f"coin-{name}.webp"), quality=90, method=6)


coin("sika.png", "sika", box=(0, 0, 2953, 2350))
coin("mapei.png", "mapei", box=(0, 0, 77, 77), scale=0.7)
coin("fosroc.jpg", "fosroc")

# ---- close: droplets macro ----------------------------------------------------
drops = Image.open(f"{R}/droplets-1920.png").convert("RGB")
drops.save(out("close-droplets.webp"), quality=84, method=6)

print(json.dumps({"VILLA_BOX": villa_box, "LAYER_TAGS": tags,
                  "layer_aspect": round((bx1 - bx0) / (by1 - by0), 4)}, indent=2))

# ---- sources strip: the Sika file carries a wide white margin; trim it -------
sika = Image.open(os.path.join(F, "public", "brands", "sika.png")).convert("RGBA")
flat = Image.new("RGBA", sika.size, (255, 255, 255, 255))
flat.alpha_composite(sika)
box = ImageChops.difference(flat.convert("RGB"), Image.new("RGB", sika.size, (255, 255, 255))).getbbox()
trimmed = flat.crop(box).convert("RGB")
trimmed.thumbnail((240, 240), Image.LANCZOS)
trimmed.save(out("maker-sika.webp"), quality=90, method=6)
print("maker-sika", trimmed.size)
