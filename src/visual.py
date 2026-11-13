from __future__ import annotations
import random
from pathlib import Path
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont
from .config import BASE

PALETTES = [
    {"bg": ("#0F0C29", "#302B63"), "accent": "#FFD400", "text": "#FFFFFF", "btn_text": "#111111"},
    {"bg": ("#141E30", "#243B55"), "accent": "#00E5A0", "text": "#FFFFFF", "btn_text": "#0B1B17"},
    {"bg": ("#200122", "#6F0000"), "accent": "#FFB347", "text": "#FFFFFF", "btn_text": "#2A0A00"},
    {"bg": ("#000000", "#434343"), "accent": "#FF3B6B", "text": "#FFFFFF", "btn_text": "#FFFFFF"},
    {"bg": ("#0575E6", "#021B79"), "accent": "#FFE53B", "text": "#FFFFFF", "btn_text": "#111111"},
    {"bg": ("#42275A", "#734B6D"), "accent": "#7CFFCB", "text": "#FFFFFF", "btn_text": "#122018"},
]

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
    "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font_path() -> str | None:
    custom = sorted((BASE / "fonts").glob("*.ttf")) + sorted((BASE / "fonts").glob("*.otf"))
    if custom:
        return str(custom[0])
    for c in FONT_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def _font(path, size):
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size)


def _wrap(text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if font.getlength(t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(text, path, max_w, max_h, start, minimum, spacing=1.18):
    size = start
    while True:
        f = _font(path, size)
        lines = _wrap(text, f, max_w)
        ok = len(lines) * size * spacing <= max_h and all(f.getlength(l) <= max_w for l in lines)
        if ok or size <= minimum:
            return f, lines, size
        size -= 4


def _draw_lines(img, lines, font, size, cy, fill, spacing=1.18, shadow=True):
    d = ImageDraw.Draw(img)
    W = img.width
    total = len(lines) * size * spacing
    y = cy - total / 2
    for l in lines:
        if shadow:
            d.text((W / 2 + 4, y + 5), l, font=font, fill=(0, 0, 0, 140), anchor="ma")
        d.text((W / 2, y), l, font=font, fill=fill, anchor="ma")
        y += size * spacing


def pick_palette(projet: dict) -> dict:
    pal = dict(random.choice(PALETTES))
    c = projet.get("couleur", "").strip()
    if c:
        try:
            ImageColor.getrgb(c)
            pal["accent"] = c
        except ValueError:
            pass
    return pal


def _cover(img, size):
    W, H = size
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def _photo_background(size, pal, photo):
    """Photo plein cadre + voile coloré dégradé pour garder le texte lisible."""
    W, H = size
    base = _cover(photo, size).convert("RGBA")
    top = ImageColor.getrgb(pal["bg"][0]) + (150,)
    bottom = ImageColor.getrgb(pal["bg"][1]) + (205,)
    mask = Image.linear_gradient("L").resize((W, H))
    veil = Image.composite(Image.new("RGBA", size, bottom), Image.new("RGBA", size, top), mask)
    return Image.alpha_composite(base, veil)


def _background(size, pal, photo=None):
    if photo is not None:
        return _photo_background(size, pal, photo)
    W, H = size
    mask = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGB", size, pal["bg"][1]), Image.new("RGB", size, pal["bg"][0]), mask).convert("RGBA")
    deco = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(deco)
    r, g, b = ImageColor.getrgb(pal["accent"])
    for _ in range(4):
        rad = random.randint(int(W * 0.25), int(W * 0.5))
        x, y = random.randint(-rad // 2, W), random.randint(0, H)
        d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=(r, g, b, random.randint(25, 55)))
    return Image.alpha_composite(img, deco.filter(ImageFilter.GaussianBlur(int(W * 0.08))))


def build_visual(copy: dict, projet: dict, size, folder: Path, name: str, pal: dict, photo=None) -> dict:
    """Produit le fond, 3 calques transparents (titre, sous-titre, bouton) et le visuel complet."""
    W, H = size
    folder.mkdir(parents=True, exist_ok=True)
    fp = _font_path()
    acc, txt = pal["accent"], pal["text"]
    box_w = int(W * 0.86)

    bg = _background(size, pal, photo)
    tag = projet.get("nom", "").strip()
    if tag:
        f = _font(fp, int(W * 0.04))
        ImageDraw.Draw(bg).text((W / 2, H * 0.12), tag.upper(), font=f, fill=acc, anchor="mm")

    # calque 1 : accroche
    l1 = Image.new("RGBA", size, (0, 0, 0, 0))
    f, lines, sz = _fit(copy["headline"].upper(), fp, box_w, H * 0.27, int(W * 0.11), int(W * 0.05))
    _draw_lines(l1, lines, f, sz, H * 0.335, txt)
    bar_y = int(H * 0.335 + len(lines) * sz * 1.18 / 2 + H * 0.02)
    ImageDraw.Draw(l1).rounded_rectangle((W * 0.38, bar_y, W * 0.62, bar_y + 12), 6, fill=acc)

    # calque 2 : sous-titre
    l2 = Image.new("RGBA", size, (0, 0, 0, 0))
    f, lines, sz = _fit(copy["subline"], fp, box_w, H * 0.17, int(W * 0.056), int(W * 0.035))
    _draw_lines(l2, lines, f, sz, H * 0.60, txt, shadow=True)

    # calque 3 : bouton CTA
    l3 = Image.new("RGBA", size, (0, 0, 0, 0))
    d3 = ImageDraw.Draw(l3)
    bw, bh = int(W * 0.74), int(H * 0.07)
    x0, y0 = (W - bw) // 2, int(H * 0.70)
    d3.rounded_rectangle((x0 + 0, y0 + 8, x0 + bw, y0 + bh + 8), bh // 2, fill=(0, 0, 0, 120))
    d3.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), bh // 2, fill=acc)
    f, lines, sz = _fit(copy["cta"].upper(), fp, int(bw * 0.86), bh * 0.7, int(W * 0.05), int(W * 0.03))
    d3.text((W / 2, y0 + bh / 2), " ".join(lines), font=f, fill=pal["btn_text"], anchor="mm")

    paths = []
    flat = bg.copy()
    bg_p = folder / f"{name}_bg.png"
    bg.convert("RGB").save(bg_p)
    for i, layer in enumerate((l1, l2, l3), 1):
        p = folder / f"{name}_l{i}.png"
        layer.save(p)
        paths.append(p)
        flat = Image.alpha_composite(flat, layer)
    flat_p = folder / f"{name}_flat.png"
    flat.convert("RGB").save(flat_p, quality=95)
    return {"bg": bg_p, "layers": paths, "flat": flat_p}
