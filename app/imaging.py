"""Нарезка сторис и рамки для аватарок (Pillow)."""
from __future__ import annotations

import base64
import colorsys
import io
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

Image.MAX_IMAGE_PIXELS = 80_000_000

STORY_W, STORY_H = 1080, 1920
Color = tuple[int, int, int]


def open_image(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im.load()
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (0, 0, 0))
        bg.paste(im, mask=im.getchannel("A"))
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((8000, 8000), Image.LANCZOS)
    return im


# --------------------------------------------------------------------------------------
# Нарезка сторис
# --------------------------------------------------------------------------------------
def slice_story(im: Image.Image, parts: int, mode: str = "fill") -> list[bytes]:
    parts = max(1, min(6, parts))
    w, h = STORY_W * parts, STORY_H
    if mode == "fit":
        small = ImageOps.fit(im, (w // 4, h // 4), Image.BICUBIC).filter(ImageFilter.GaussianBlur(14))
        canvas = small.resize((w, h), Image.BICUBIC)
        canvas = Image.blend(canvas, Image.new("RGB", canvas.size, (0, 0, 0)), 0.35)
        fg = ImageOps.contain(im, (w, h), Image.LANCZOS)
        canvas.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    else:
        canvas = ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.5))
    tiles = []
    for i in range(parts):
        buf = io.BytesIO()
        canvas.crop((i * STORY_W, 0, (i + 1) * STORY_W, STORY_H)).save(buf, "JPEG", quality=95, subsampling=0)
        tiles.append(buf.getvalue())
    return tiles


# --------------------------------------------------------------------------------------
# Палитры под цвет аватарки
# --------------------------------------------------------------------------------------
def _rgb(h: float, s: float, v: float) -> Color:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return round(r * 255), round(g * 255), round(b * 255)


def hex_of(c: Color) -> str:
    return "#%02x%02x%02x" % c


def make_palettes(im: Image.Image) -> list[tuple[str, Color, Color]]:
    small = im.copy()
    small.thumbnail((96, 96))
    q = small.convert("RGB").quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette() or []
    best, best_score = None, -1.0
    for cnt, idx in q.getcolors() or []:
        r, g, b = pal[idx * 3 : idx * 3 + 3]
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        score = cnt * (s**1.2 + 0.04) * (1.0 if v > 0.18 else 0.2)
        if score > best_score:
            best, best_score = (h, s, v), score
    h, s, v = best or (0.12, 0.8, 1.0)
    if s < 0.15:  # почти серый аватар — берём фирменный фиолетовый (Aurora)
        h, s = 0.745, 0.7
    s = min(0.95, max(s, 0.55))
    v = max(v, 0.92)
    base = _rgb(h, s, v)
    return [
        ("Под цвет", base, _rgb(h + 0.03, s * 0.45, 1.0)),
        ("Контраст", _rgb(h + 0.5, s, v), base),
        ("Соседние", _rgb(h - 0.07, s, v), _rgb(h + 0.07, s, v)),
        ("Светлый", (244, 244, 250), base),
        ("Глубокий", _rgb(h, min(1, s + 0.1), 0.55), _rgb(h, s * 0.6, 1.0)),
        ("Золото", (255, 214, 102), (255, 150, 40)),
    ]


from .frames import CATS, STYLES, render_frame  # noqa: E402,F401


def square_avatar(im: Image.Image, size: int = 1024) -> Image.Image:
    return ImageOps.fit(im, (size, size), Image.LANCZOS)


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=False)
    return buf.getvalue()


def webp_bytes(im: Image.Image, quality: int = 86) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=quality, method=4)
    return buf.getvalue()


def data_url(raw: bytes, mime: str = "image/webp") -> str:
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def previews(av: Image.Image, c1: Color, c2: Color, size: int = 240, only_palette: bool = False) -> list[dict]:
    """Превью всех рамок. only_palette=True — только те, что зависят от палитры."""
    from concurrent.futures import ThreadPoolExecutor

    small = square_avatar(av, 512)

    def one(item):
        sid, st = item
        out = {"id": sid, "name": st["name"], "cat": st["cat"], "themed": st["themed"]}
        if not (only_palette and st["themed"]):
            out["img"] = data_url(webp_bytes(render_frame(small, sid, c1, c2, size), 82))
        return out

    with ThreadPoolExecutor(max_workers=4) as ex:
        return list(ex.map(one, STYLES.items()))


# --------------------------------------------------------------------------------------
# демо-материалы (онбординг, ролик)
# --------------------------------------------------------------------------------------
def demo_avatar(n: int = 1024) -> Image.Image:
    """Стилизованный портрет для демонстраций — без реальных людей."""
    k = n / 1024
    im = Image.new("RGB", (n, n))
    d = ImageDraw.Draw(im)
    for y in range(n):
        t = y / n
        d.line([(0, y), (n, y)], fill=(int(255 - 150 * t), int(140 - 70 * t), int(100 + 130 * t)))
    glow = Image.new("RGB", (n, n), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse((n * 0.15, n * 0.05, n * 0.85, n * 0.7), fill=(255, 190, 120))
    im = Image.blend(im, Image.composite(glow, im, glow.convert("L").filter(ImageFilter.GaussianBlur(120 * k))), 0.45)
    d = ImageDraw.Draw(im)
    d.ellipse((n * 0.06, n * 0.68, n * 0.94, n * 1.35), fill=(36, 32, 58))          # плечи
    d.ellipse((n * 0.30, n * 0.60, n * 0.70, n * 0.80), fill=(48, 43, 76))           # капюшон
    d.rectangle((n * 0.44, n * 0.52, n * 0.56, n * 0.70), fill=(226, 170, 140))       # шея
    d.ellipse((n * 0.33, n * 0.22, n * 0.67, n * 0.62), fill=(240, 192, 160))         # лицо
    d.pieslice((n * 0.30, n * 0.16, n * 0.70, n * 0.54), 180, 360, fill=(58, 34, 30))  # волосы
    d.ellipse((n * 0.30, n * 0.26, n * 0.38, n * 0.44), fill=(58, 34, 30))
    d.ellipse((n * 0.62, n * 0.26, n * 0.70, n * 0.44), fill=(58, 34, 30))
    for x in (0.43, 0.57):
        d.ellipse((n * (x - 0.018), n * 0.405, n * (x + 0.018), n * 0.435), fill=(40, 28, 28))
    d.arc((n * 0.44, n * 0.45, n * 0.56, n * 0.54), 20, 160, fill=(170, 100, 90), width=max(2, int(5 * k)))
    return im.filter(ImageFilter.GaussianBlur(1.2 * k))


def demo_panorama(w: int = 3240, h: int = 1920) -> Image.Image:
    """Панорама «закат в горах» для демонстрации нарезки."""
    import random

    rnd = random.Random(4)
    im = _vgrad_img(w, h, [(18, 10, 52), (88, 28, 120), (232, 70, 130), (255, 150, 70), (255, 214, 120)])
    d = ImageDraw.Draw(im)
    for _ in range(220):                                                              # звёзды
        x, y = rnd.uniform(0, w), rnd.uniform(0, h * 0.45)
        r = rnd.choice((1, 1, 2, 3))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 250, 235))
    sun = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sun).ellipse((w * 0.5 - 330, h * 0.60 - 330, w * 0.5 + 330, h * 0.60 + 330), fill=255)
    halo = sun.filter(ImageFilter.GaussianBlur(160)).point(lambda v: int(v * 1.2))
    im = Image.composite(Image.new("RGB", (w, h), (255, 190, 110)), im, halo.point(lambda v: min(255, v)))
    ImageDraw.Draw(im).ellipse((w * 0.5 - 230, h * 0.60 - 230, w * 0.5 + 230, h * 0.60 + 230), fill=(255, 240, 190))
    import math

    d = ImageDraw.Draw(im)
    for layer, (base, amp, col) in enumerate(((0.66, 0.15, (96, 42, 120)), (0.74, 0.14, (58, 26, 96)), (0.84, 0.12, (30, 16, 62)), (0.93, 0.07, (14, 8, 34)))):
        ph = rnd.uniform(0, 6)
        pts = [(0, h)]
        for x in range(0, w + 20, 20):
            t = x / w * 6.28
            y = h * base - h * amp * (0.55 * abs(math.sin(t * (1.1 + layer * 0.35) + ph)) + 0.3 * abs(math.sin(t * (2.7 + layer) + ph * 2)) + 0.15 * math.sin(t * 7 + ph))
            pts.append((x, y))
        pts.append((w, h))
        d.polygon(pts, fill=col)
    for _ in range(9):                                                                # птицы
        x, y, s = rnd.uniform(0.1, 0.9) * w, rnd.uniform(0.18, 0.4) * h, rnd.uniform(14, 30)
        d.line([(x - s, y), (x - s / 2, y - s / 2), (x, y), (x + s / 2, y - s / 2), (x + s, y)], fill=(30, 14, 50), width=4, joint="curve")
    return im.filter(ImageFilter.GaussianBlur(1.4))


def _vgrad_img(w: int, h: int, stops: list[Color]) -> Image.Image:
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    n = len(stops) - 1
    for y in range(h):
        p = y / (h - 1) * n
        k = min(int(p), n - 1)
        a, b = stops[k], stops[k + 1]
        f = p - k
        d.line([(0, y), (w, y)], fill=tuple(round(a[i] + (b[i] - a[i]) * f) for i in range(3)))
    return img
