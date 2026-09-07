"""
Generate the brand icon set from the single master artwork.

The master (design/source-images/atom-logo-transparent.png.png) is 1254x1254 RGB — its
name says "transparent" but it has an opaque white background, so on the dark
landing surface it rendered as a white square, and all 857 KB of it were being
downloaded to draw a 17px mark.

This keys the white out into an alpha channel (luminance becomes transparency,
which keeps the antialiased edges of the line art), tints the result, and writes
every size the app actually asks for. Re-run after replacing the master:

    python scripts/build-brand-icons.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
# The master lives outside public/ — it is a source file, not something the
# browser should ever be able to download.
MASTER = ROOT / "design/source-images/atom-logo-transparent.png.png"

GRAPHITE = (14, 19, 24)
ACCENT = (89, 217, 192)
INK = (36, 31, 24)


def keyed_master() -> Image.Image:
    """White background -> alpha. Returns a white-on-transparent mark."""
    src = Image.open(MASTER).convert("L")
    alpha = src.point(lambda v: 255 - v)  # dark ink becomes opaque
    mark = Image.new("RGBA", src.size, (255, 255, 255, 0))
    mark.putalpha(alpha)
    return mark


def tint(mark: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    out = Image.new("RGBA", mark.size, rgb + (0,))
    out.putalpha(mark.getchannel("A"))
    return out


def trimmed(mark: Image.Image) -> Image.Image:
    box = mark.getchannel("A").getbbox()
    return mark.crop(box) if box else mark


def on_plate(mark: Image.Image, size: int, inset: float, radius_ratio: float) -> Image.Image:
    """Opaque brand plate with the mark centred inside the safe zone."""
    plate = Image.new("RGBA", (size, size), GRAPHITE + (255,))
    if radius_ratio:
        rounded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        mask = Image.new("L", (size * 4, size * 4), 0)
        from PIL import ImageDraw

        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size * 4 - 1, size * 4 - 1), radius=int(size * 4 * radius_ratio), fill=255
        )
        rounded.paste(plate, (0, 0), mask.resize((size, size), Image.LANCZOS))
        plate = rounded

    inner = int(size * inset)
    art = trimmed(mark).resize((inner, inner), Image.LANCZOS)
    offset = (size - inner) // 2
    plate.alpha_composite(art, (offset, offset))
    return plate


def write(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    print(f"  {path.relative_to(ROOT)}  {path.stat().st_size / 1024:.1f} KB  {image.size[0]}px")


def main() -> None:
    mark = keyed_master()
    accent = tint(mark, ACCENT)
    ink = tint(mark, INK)

    print("brand icons:")
    # Browser tab + PWA: opaque plate so the mark reads on light and dark chrome.
    write(on_plate(accent, 32, 0.66, 0.22), ROOT / "app/icon.png")
    write(on_plate(accent, 180, 0.62, 0.22), ROOT / "app/apple-icon.png")
    # Maskable icons need art inside a 60% safe zone and no transparency.
    write(on_plate(accent, 192, 0.56, 0), ROOT / "public/icons/icon-192.png")
    write(on_plate(accent, 512, 0.56, 0), ROOT / "public/icons/icon-512.png")
    # In-page mark, transparent, drawn in ink for the ivory surfaces. The dark
    # theme inverts it in CSS rather than shipping a second file.
    write(trimmed(ink).resize((96, 96), Image.LANCZOS), ROOT / "public/icons/brand-mark.png")


if __name__ == "__main__":
    main()
