"""Render the profile's static SVGs and a seamless, 24-second ASCII GIF loop.

Requires numpy and Pillow. No network requests or image generation service.
Run: python3 tools/render_header.py
"""
from argparse import ArgumentParser
from html import escape
from math import cos, pi, sin
from pathlib import Path
import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
COLS, ROWS = 92, 39
CHARS = ".,:;=+*oO#@"
LETTERS = {
    "h": ["10000", "10000", "10110", "11001", "10001", "10001", "10001"],
    "r": ["00000", "00000", "10110", "11001", "10000", "10000", "10000"],
    "x": ["00000", "00000", "10001", "01010", "00100", "01010", "10001"],
    "l": ["01100", "00100", "00100", "00100", "00100", "00100", "01110"],
    "o": ["00000", "00000", "01110", "10001", "10001", "10001", "01110"],
    "u": ["00000", "00000", "10001", "10001", "10001", "10011", "01101"],
}
THEMES = {
    "dark": ("#0d1117", "#e6edf3", "#8b949e", "#79c0ff", "#30363d"),
    "light": ("#ffffff", "#1f2328", "#656d76", "#0969da", "#d8dee4"),
}


def font_path(explicit=None):
    candidates = [explicit] if explicit else []
    candidates += [
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("A monospace font is required; pass its path with --font.")


def mesh():
    """Sample the Mobius surface and its analytic, two-sided normals."""
    u, v = np.meshgrid(
        np.linspace(0, 2 * pi, 1000, endpoint=False),
        np.linspace(-0.52, 0.52, 100),
        indexing="ij",
    )
    u, v = u.ravel(), v.ravel()
    cu, su, ch, sh = np.cos(u), np.sin(u), np.cos(u / 2), np.sin(u / 2)
    radius = 1 + v * ch
    points = np.array([radius * cu, radius * su, v * sh])
    tangent_u = np.array([
        -radius * su - 0.5 * v * sh * cu,
        radius * cu - 0.5 * v * sh * su,
        0.5 * v * ch,
    ])
    tangent_v = np.array([ch * cu, ch * su, sh])
    normals = np.cross(tangent_u.T, tangent_v.T).T
    normals /= np.linalg.norm(normals, axis=0)
    return points, normals


def rotate(values, angle):
    x, y, z = values
    a, b, c = 0.87, -0.27 + angle, -0.45
    y, z = y * cos(a) - z * sin(a), y * sin(a) + z * cos(a)
    x, z = x * cos(b) + z * sin(b), -x * sin(b) + z * cos(b)
    return np.array([x * cos(c) - y * sin(c), x * sin(c) + y * cos(c), z])


def sample_frames(count):
    points, normals = mesh()
    angles = np.arange(count) * (2 * pi / count)
    # Fit the entire rotation once, rather than resizing the object per frame.
    max_x = max_y = 0.0
    for angle in angles:
        x, y, z = rotate(points, angle)
        perspective = 1 / (1 - z * 0.13)
        max_x = max(max_x, float(np.max(np.abs(x * perspective))))
        max_y = max(max_y, float(np.max(np.abs(y * perspective))))
    scale_x, scale_y = min(27, 42 / max_x), min(14, 16 / max_y)
    frames, bounds = [], []
    for angle in angles:
        x, y, z = rotate(points, angle)
        nx, ny, nz = rotate(normals, angle)
        perspective = 1 / (1 - z * 0.13)
        px = np.rint(COLS / 2 + x * scale_x * perspective).astype(int)
        py = np.rint(ROWS / 2 - y * scale_y * perspective).astype(int)
        assert px.min() >= 0 and px.max() < COLS
        assert py.min() >= 0 and py.max() < ROWS
        bounds.append((int(px.min()), int(py.min()), int(px.max()), int(py.max())))
        pixel = py * COLS + px
        # Last item in each pixel group is the closest visible surface point.
        order = np.lexsort((z, pixel))
        sorted_pixel = pixel[order]
        selected = order[np.r_[sorted_pixel[1:] != sorted_pixel[:-1], True]]
        shade = 0.2 + 0.8 * np.abs(nx * 0.2 - ny * 0.55 + nz * 0.81)
        glyph = np.full(COLS * ROWS, -1, dtype=np.int8)
        color = np.zeros(COLS * ROWS, dtype=np.uint8)
        glyph[pixel[selected]] = np.minimum(len(CHARS) - 1, (shade[selected] * (len(CHARS) - 1)).astype(int))
        color[pixel[selected]] = np.where(shade[selected] > 0.94, 3, np.where(shade[selected] > 0.68, 2, 1))
        frames.append((glyph.reshape(ROWS, COLS), color.reshape(ROWS, COLS)))
    return frames, bounds


def dot_centers():
    for index, letter in enumerate("hrxlou"):
        for row, pattern in enumerate(LETTERS[letter]):
            for col, enabled in enumerate(pattern):
                if enabled == "1":
                    yield 52 + index * 44 + col * 6.3, 115 + row * 6.3


def static_svg(frame, theme, mobile):
    bg, fg, muted, accent, line = THEMES[theme]
    width, height = (600, 500) if mobile else (1200, 360)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">hrxlou · Hyun Kim</title>',
        '<desc id="desc">Dot-matrix lettering and a Möbius ribbon drawn entirely with ASCII characters. Static version for reduced motion.</desc>',
        f'<rect width="{width}" height="{height}" fill="{bg}"/>',
        '<g transform="translate(0 -70)">' if mobile else '<g>',
    ]
    for x, y in dot_centers():
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.05" fill="{fg}"/>')
    svg += [
        f'<text x="50" y="220" fill="{muted}" font-family="Menlo,Consolas,monospace" font-size="26">Hyun Kim</text>',
        '</g>',
        '<g transform="translate(-385 195) scale(.85)">' if mobile else '<g>',
    ]
    glyphs, colors = frame
    for row, col in zip(*np.where(glyphs >= 0)):
        char, color = CHARS[glyphs[row, col]], (muted, fg, accent)[colors[row, col] - 1]
        x, y = 480 + col * 7.1, 23 + row * 8.2
        svg.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-family="Menlo,Consolas,monospace" font-size="11.5">{escape(char)}</text>')
    svg += ['</g>', f'<path d="M50 {490 if mobile else 339}H{550 if mobile else 1150}" stroke="{line}"/>', '</svg>']
    return "\n".join(svg) + "\n"


def palette_for(theme):
    bg, fg, muted, accent, line = (ImageColor.getrgb(value) for value in THEMES[theme])
    palette = [bg]
    for color in (muted, fg, accent):
        for level in range(1, 5):
            palette.append(tuple(round(b + (c - b) * level / 4) for b, c in zip(bg, color)))
    palette.append(line)
    palette += [bg] * (256 - len(palette))
    return [channel for color in palette for channel in color]


def glyph_masks(font, mobile):
    typeface = ImageFont.truetype(font, 10 if mobile else 12)
    masks = []
    for char in CHARS:
        image = Image.new("L", (12, 16), 0)
        ImageDraw.Draw(image).text((0, 12), char, font=typeface, fill=255, anchor="ls")
        masks.append(np.rint(np.array(image) * (4 / 255)).astype(np.uint8))
    return masks


def base_image(theme, mobile, font, palette):
    bg, fg, muted, _, line = THEMES[theme]
    image = Image.new("RGB", (600, 500) if mobile else (1200, 360), bg)
    draw = ImageDraw.Draw(image)
    for x, y in dot_centers():
        y -= 70 if mobile else 0
        draw.ellipse((x - 2.05, y - 2.05, x + 2.05, y + 2.05), fill=fg)
    draw.text((50, 150 if mobile else 220), "Hyun Kim", font=ImageFont.truetype(font, 26), fill=muted, anchor="ls")
    draw.line((50, 490 if mobile else 339, 550 if mobile else 1150, 490 if mobile else 339), fill=line)
    reference = Image.new("P", (1, 1))
    reference.putpalette(palette)
    return np.array(image.quantize(palette=reference, dither=Image.Dither.NONE))


def raster_frame(frame, base, masks, palette, mobile):
    pixels = base.copy()
    glyphs, colors = frame
    for row, col in zip(*np.where(glyphs >= 0)):
        x, baseline = 480 + col * 7.1, 23 + row * 8.2
        if mobile:
            x, baseline = -385 + x * 0.85, 195 + baseline * 0.85
        x, y = round(x), round(baseline) - 12
        mask = masks[glyphs[row, col]]
        region = pixels[y:y + mask.shape[0], x:x + mask.shape[1]]
        assert region.shape == mask.shape, "Artwork must stay inside its canvas."
        np.copyto(region, (colors[row, col] - 1) * 4 + mask, where=mask > 0)
    image = Image.fromarray(pixels).convert("P")
    image.putpalette(palette)
    return image


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=192)
    parser.add_argument("--seconds", type=float, default=24)
    parser.add_argument("--font")
    args = parser.parse_args()
    if args.frames < 8 or args.seconds * 1000 / args.frames < 20:
        parser.error("Use at least eight frames and at least 20 ms per frame.")
    font = font_path(args.font)
    OUT.mkdir(exist_ok=True)
    frames, bounds = sample_frames(args.frames)
    # GIF stores duration in 10-ms ticks. Alternate 120/130 ms for 8 fps exactly.
    ticks = np.rint(np.linspace(0, args.seconds * 100, args.frames + 1)).astype(int)
    durations = (np.diff(ticks) * 10).tolist()
    samples = []
    for theme in THEMES:
        for mobile in (False, True):
            stem = f"header-ascii-{'mobile-' if mobile else ''}{theme}"
            (OUT / f"{stem}.svg").write_text(static_svg(frames[0], theme, mobile))
            palette = palette_for(theme)
            base = base_image(theme, mobile, font, palette)
            masks = glyph_masks(font, mobile)
            images = [raster_frame(frame, base, masks, palette, mobile) for frame in frames]
            path = OUT / f"{stem}.gif"
            images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0, disposal=1, optimize=False)
            with Image.open(path) as gif:
                total = 0
                for index in range(gif.n_frames):
                    gif.seek(index)
                    total += gif.info["duration"]
                assert total == round(args.seconds * 100) * 10
                assert gif.n_frames == args.frames
                assert gif.info["loop"] == 0
            print(f"{path.name}: {path.stat().st_size:,} bytes, {len(images)} frames, {sum(durations)} ms", flush=True)
            if theme == "dark" and not mobile:
                samples = [images[round(args.frames * fraction)].convert("RGB") for fraction in (0, .25, .5, .75)]
            del images
    diagnostics = ROOT / ".git" / "ascii-animation-contact-sheet.png"
    sheet = Image.new("RGB", (1200, 360 * 4), THEMES["dark"][0])
    for index, image in enumerate(samples):
        sheet.paste(image, (0, index * 360))
    sheet.save(diagnostics)
    changed = [int(np.count_nonzero(frames[index][0] != frames[(index + 1) % args.frames][0])) for index in range(args.frames)]
    assert min(changed) > 0
    print(f"Cell changes per step: min={min(changed)}, max={max(changed)}, loop seam={changed[-1]}")
    print(f"Cell bounds across the full turn: x={min(b[0] for b in bounds)}..{max(b[2] for b in bounds)}, y={min(b[1] for b in bounds)}..{max(b[3] for b in bounds)}")
    print(f"Contact sheet: {diagnostics}")


if __name__ == "__main__":
    main()
