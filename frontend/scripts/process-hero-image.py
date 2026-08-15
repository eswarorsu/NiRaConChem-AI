#!/usr/bin/env python3
"""
Process a hero/product image for the NIRACONCHEM AI frontend.

Takes any source image and produces web-ready assets:

  * optional white-background removal (flood fill from the corners, so it only
    removes the *connected* background and leaves white areas inside the
    subject intact)
  * edge decontamination, so no white fringe shows against a coloured page
  * trims dead transparent padding
  * exports 1x and 2x variants as both PNG and WebP

Usage
-----
    python process-hero-image.py SOURCE --name jcb-hero --width 1000
    python process-hero-image.py SOURCE --name jcb-hero --width 1000 --remove-bg

  SOURCE     path to the original image (use the LARGEST original you have)
  --name     output basename; files land in ../public/assets/
  --width    intended CSS display width in px at the largest breakpoint.
             The 2x export targets 2 * this value.
  --remove-bg  run white-background removal (skip if already transparent)
  --tolerance  how close to white counts as background (default 32)

Why 2x: the hero is styled `width: 52vw`. On a 1920px viewport that is ~1000
CSS px, and a HiDPI display needs twice that many real pixels. Shipping only a
1x file is what made the original 800px asset look soft.
"""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:  # pragma: no cover
    sys.exit("Pillow is required:  pip install Pillow")


def remove_white_background(im: Image.Image, tolerance: int = 32) -> Image.Image:
    """Flood fill transparency inward from the image border.

    Only removes background *connected to the edge*, so white highlights inside
    the subject (cab windows, logos) survive. A simple "make every white pixel
    transparent" pass would punch holes in the subject.
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    cutoff = 255 - tolerance

    def is_bg(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        return a > 0 and r >= cutoff and g >= cutoff and b >= cutoff

    seen = bytearray(w * h)
    queue: deque[tuple[int, int]] = deque()

    for x in range(w):
        for y in (0, h - 1):
            if is_bg(x, y):
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(x, y):
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        idx = y * w + x
        if seen[idx]:
            continue
        seen[idx] = 1
        if not is_bg(x, y):
            continue
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                queue.append((nx, ny))

    return im


def white_to_alpha(im: Image.Image, floor: int = 246, white_point: int = 234) -> Image.Image:
    """Convert a white studio background into a smooth alpha ramp.

    Use this instead of --remove-bg for double-exposure / ink-on-white artwork,
    where the subject deliberately *fades* into the background. A flood fill is
    binary: it would cut a hard line exactly where the artwork is supposed to
    dissolve, leaving a visible silhouette edge.

    Here the image is treated as ink printed on white paper and the compositing
    is inverted:

        alpha = 1 - min(r, g, b) / floor        (0 for white, 1 for saturated ink)
        rgb   = (pixel - white * (1 - alpha)) / alpha

    Using min() rather than luminance keeps saturated colour opaque — the orange
    hard hat has a low blue channel, so it survives at ~92% alpha instead of the
    ~50% a luminance ramp would give it. Faded scaffolding stays a soft ghost,
    which is exactly what lets the page colour show through behind it.

    `floor` is the value treated as pure background; anything at or above it
    becomes fully transparent. Real photos of "white" sit around 235-250, so the
    default is slightly below 255.
    """
    im = im.convert("RGB")
    w, h = im.size
    out = Image.new("RGBA", (w, h))
    src = im.load()
    dst = out.load()

    # Real "white" backgrounds are rarely flat — this source drifts from 253 in
    # the centre to 235 at the corners. Without normalisation that vignette is
    # darker than `floor`, so it survives as a grey haze over the page colour.
    # Clipping the top of the range to pure white first removes it outright.
    if white_point and white_point < 255:
        lut = [min(255, round(v * 255 / white_point)) for v in range(256)]
        im = im.point(lut * 3)
        src = im.load()

    for y in range(h):
        for x in range(w):
            r, g, b = src[x, y]
            m = min(r, g, b)
            if m >= floor:
                dst[x, y] = (0, 0, 0, 0)
                continue
            a = 1.0 - m / floor
            inv = 255.0 * (1.0 - a)
            # Unpremultiply against white to recover the original ink colour.
            nr = min(255, max(0, round((r - inv) / a)))
            ng = min(255, max(0, round((g - inv) / a)))
            nb = min(255, max(0, round((b - inv) / a)))
            dst[x, y] = (nr, ng, nb, min(255, round(a * 255)))

    return out


def decontaminate_edges(im: Image.Image) -> Image.Image:
    """Pull leftover light fringe out of semi-transparent edge pixels.

    After any background removal the boundary pixels are a blend of subject and
    old background. Against a coloured page that reads as a pale halo. Nudging
    the alpha curve at the boundary hides it without eating into the subject.
    """
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    # Slight contrast boost on alpha: push near-transparent to 0, near-opaque to 255.
    alpha = alpha.point(lambda a: 0 if a < 24 else (255 if a > 232 else int((a - 24) * 255 / 208)))
    im.putalpha(alpha)
    return im


def _resample(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize, stepping up in stages when enlarging.

    A single large Lanczos jump (e.g. 516px -> 2560px) smears edges, because the
    kernel is sampling far apart in the source. Enlarging at most 2x at a time
    and re-sharpening between steps keeps edges defined. This does NOT invent
    detail — nothing can — but it noticeably beats one big jump and beats
    letting the browser scale the image itself.
    """
    if size[0] <= im.width:
        return im.resize(size, Image.LANCZOS)

    cur = im
    while cur.width * 2 < size[0]:
        cur = cur.resize((cur.width * 2, cur.height * 2), Image.LANCZOS)
        cur = cur.filter(ImageFilter.UnsharpMask(radius=0.8, percent=38, threshold=2))
    return cur.resize(size, Image.LANCZOS)


def export(im: Image.Image, out_dir: Path, name: str, target_w: int, label: str) -> None:
    ratio = im.height / im.width
    size = (target_w, max(1, round(target_w * ratio)))
    resized = _resample(im, size)

    # A light unsharp pass counteracts the softening that any resample introduces.
    resized = resized.filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=3))

    png_path = out_dir / f"{name}{label}.png"
    webp_path = out_dir / f"{name}{label}.webp"
    resized.save(png_path, "PNG", optimize=True)
    resized.save(webp_path, "WEBP", quality=90, method=6)

    print(
        f"  {png_path.name:32s} {size[0]:5d}x{size[1]:<5d} "
        f"{png_path.stat().st_size/1024:7.0f} KB"
    )
    print(
        f"  {webp_path.name:32s} {size[0]:5d}x{size[1]:<5d} "
        f"{webp_path.stat().st_size/1024:7.0f} KB"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--width", type=int, default=1000, help="CSS display width at largest breakpoint")
    ap.add_argument("--remove-bg", action="store_true")
    ap.add_argument("--tolerance", type=int, default=32)
    ap.add_argument(
        "--white-to-alpha",
        action="store_true",
        help="soft alpha ramp for ink-on-white / double-exposure art (see white_to_alpha)",
    )
    ap.add_argument("--floor", type=int, default=246, help="value treated as pure white background")
    ap.add_argument("--white-point", type=int, default=234,
                    help="clip input levels at/above this to pure white before the alpha ramp")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "public" / "assets",
    )
    args = ap.parse_args()

    if not args.source.exists():
        sys.exit(f"Source not found: {args.source}")

    im = Image.open(args.source).convert("RGBA")
    print(f"source: {args.source.name}  {im.width}x{im.height}")

    if args.white_to_alpha:
        print(f"converting white background to a soft alpha ramp (floor={args.floor}, white-point={args.white_point})...")
        im = white_to_alpha(im, args.floor, args.white_point)
    elif args.remove_bg:
        print("removing white background (edge-connected flood fill)...")
        im = remove_white_background(im, args.tolerance)

    # The alpha ramp is the point of white-to-alpha mode; hardening it would
    # reintroduce the very edge this mode exists to avoid.
    if not args.white_to_alpha:
        im = decontaminate_edges(im)

    bbox = im.getbbox()
    if bbox and bbox != (0, 0, im.width, im.height):
        before = im.size
        im = im.crop(bbox)
        print(f"trimmed padding: {before[0]}x{before[1]} -> {im.width}x{im.height}")

    needed = args.width * 2
    if im.width < needed:
        print(
            f"\n  WARNING: source is {im.width}px wide but the 2x export needs "
            f"{needed}px.\n  Upscaling cannot invent detail — the result will still look "
            f"soft on HiDPI screens.\n  Supply a larger original for a genuinely sharp result.\n"
        )

    args.out.mkdir(parents=True, exist_ok=True)
    print("exports:")
    export(im, args.out, args.name, args.width, "")
    export(im, args.out, args.name, needed, "@2x")


if __name__ == "__main__":
    main()
