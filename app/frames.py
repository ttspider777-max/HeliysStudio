"""Рамки для аватарок: 35+ стилей, всё рисуется Pillow (без внешних файлов).

Каждый стиль — функция fn(cv, av, c1, c2, R): cv — прозрачный RGBA-холст (2× для сглаживания),
av — квадратная аватарка, c1/c2 — цвета палитры, R — половина размера холста.
«Тематические» стили (themed=True) используют свои цвета и не зависят от палитры.
"""
from __future__ import annotations

import math
import random
from typing import Callable

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

Color = tuple[int, int, int]
TAU = math.tau


# ======================================================================================
# примитивы
# ======================================================================================
def mix(a: Color, b: Color, t: float) -> Color:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def shade(c: Color, k: float) -> Color:
    """k>0 — к белому, k<0 — к чёрному."""
    if k >= 0:
        return tuple(min(255, round(v + (255 - v) * k)) for v in c)  # type: ignore[return-value]
    return tuple(max(0, round(v * (1 + k))) for v in c)  # type: ignore[return-value]


def _circle(S: int, r: float, cx: float | None = None, cy: float | None = None) -> Image.Image:
    cx = S / 2 if cx is None else cx
    cy = S / 2 if cy is None else cy
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    return m


def _ring(S: int, ro: float, ri: float, cx: float | None = None, cy: float | None = None) -> Image.Image:
    return ImageChops.subtract(_circle(S, ro, cx, cy), _circle(S, ri, cx, cy))


def _paint(cv: Image.Image, src: Color | Image.Image, mask: Image.Image, op: float = 1.0) -> None:
    if op < 1:
        mask = mask.point(lambda v: int(v * op))
    layer = Image.new("RGBA", mask.size, (*src, 255)) if isinstance(src, tuple) else src.convert("RGBA")
    layer.putalpha(mask)
    cv.alpha_composite(layer)


def _grad(S: int, c1: Color, c2: Color, angle: float = 45) -> Image.Image:
    g = Image.linear_gradient("L").resize((768, 768), Image.BICUBIC).rotate(angle, resample=Image.BICUBIC)
    g = g.crop((128, 128, 640, 640)).resize((S, S), Image.BICUBIC)
    return Image.composite(Image.new("RGB", (S, S), c2), Image.new("RGB", (S, S), c1), g)


def _vgrad(S: int, stops: list[Color]) -> Image.Image:
    img = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(img)
    n = len(stops) - 1
    for y in range(S):
        p = y / (S - 1) * n
        k = min(int(p), n - 1)
        d.line([(0, y), (S, y)], fill=mix(stops[k], stops[k + 1], p - k))
    return img


def _conic(S: int, stops: list[Color], rot: float = -90.0, steps: int = 180) -> Image.Image:
    full, S = S, max(128, S // 2)
    img = Image.new("RGB", (S, S), stops[0])
    d = ImageDraw.Draw(img)
    n = len(stops)
    box = (S / 2 - S, S / 2 - S, S / 2 + S, S / 2 + S)
    for i in range(steps):
        pos = i / steps * n
        k = int(pos)
        f = pos - k
        f = f * f * (3 - 2 * f)
        a0 = rot + 360 * i / steps
        d.pieslice(box, a0, a0 + 360 / steps + 1.2, fill=mix(stops[k % n], stops[(k + 1) % n], f))
    return img.resize((full, full), Image.BICUBIC)


def _glow(m: Image.Image, radius: float, gain: float = 2.0) -> Image.Image:
    return m.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * gain)))


def _avatar(cv: Image.Image, av: Image.Image, r: float, cx: float | None = None, cy: float | None = None, pixel: int = 0) -> None:
    S = cv.width
    cx = S / 2 if cx is None else cx
    cy = S / 2 if cy is None else cy
    d = int(round(r * 2))
    a = ImageOps.fit(av, (d, d), Image.LANCZOS).convert("RGBA")
    if pixel:
        n = max(8, int(d / (pixel * 0.75)))
        a = a.resize((n, n), Image.BILINEAR).resize((d, d), Image.NEAREST)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    layer.paste(a, (int(cx - d / 2), int(cy - d / 2)))
    layer.putalpha(_pixel_circle(S, r, pixel) if pixel else _circle(S, r, cx, cy))
    cv.alpha_composite(layer)


def _pixel_circle(S: int, r: float, cell: int) -> Image.Image:
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    n = S // cell + 1
    for j in range(n):
        for i in range(n):
            if math.hypot(i * cell + cell / 2 - S / 2, j * cell + cell / 2 - S / 2) < r:
                d.rectangle((i * cell, j * cell, i * cell + cell - 1, j * cell + cell - 1), fill=255)
    return m


def _arcs(S: int, r_out: float, width: float, n: int, fill_deg: float, start: float = -90) -> Image.Image:
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    box = (S / 2 - r_out, S / 2 - r_out, S / 2 + r_out, S / 2 + r_out)
    step = 360 / n
    for i in range(n):
        a0 = start + i * step + (step - fill_deg) / 2
        d.arc(box, a0, a0 + fill_deg, fill=255, width=int(width))
    return m


def _pol(S: int, r: float, a: float, cx: float | None = None, cy: float | None = None) -> tuple[float, float]:
    """Точка на окружности: угол a от верха по часовой стрелке (радианы)."""
    cx = S / 2 if cx is None else cx
    cy = S / 2 if cy is None else cy
    return cx + r * math.sin(a), cy - r * math.cos(a)


def _rot(x: float, y: float, a: float) -> tuple[float, float]:
    c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c


def _star_pts(cx: float, cy: float, ro: float, ri: float, rot: float = 0, n: int = 5) -> list[tuple[float, float]]:
    pts = []
    for k in range(n * 2):
        r = ro if k % 2 == 0 else ri
        a = rot + math.pi * k / n
        pts.append((cx + r * math.sin(a), cy - r * math.cos(a)))
    return pts


def _sparkle(d: ImageDraw.ImageDraw, x: float, y: float, r: float, col: Color) -> None:
    d.polygon([(x, y - r), (x + r * 0.2, y - r * 0.2), (x + r, y), (x + r * 0.2, y + r * 0.2), (x, y + r), (x - r * 0.2, y + r * 0.2), (x - r, y), (x - r * 0.2, y - r * 0.2)], fill=col)


def _heart_pts(cx: float, cy: float, r: float, ang: float) -> list[tuple[float, float]]:
    """Сердце, «верх» которого направлен по углу ang (от верха по часовой)."""
    ux, uy = math.sin(ang), -math.cos(ang)
    vx, vy = math.cos(ang), math.sin(ang)
    pts = []
    for k in range(40):
        t = TAU * k / 40
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + (x * vx + y * ux) * r / 17, cy + (x * vy + y * uy) * r / 17))
    return pts


def _petal(cx: float, cy: float, r: float, ang: float, notch: float = 0.3, width: float = 0.34) -> list[tuple[float, float]]:
    pts = []
    for k in range(32):
        phi = TAU * k / 32
        px = 0.5 + 0.5 * math.cos(phi)
        py = width * math.sin(phi)
        px -= notch * math.exp(-(min(phi, TAU - phi) / 0.3) ** 2)
        x, y = _rot(px * r, py * r, ang)
        pts.append((cx + x, cy + y))
    return pts


def _leaf(cx: float, cy: float, length: float, width: float, ang: float) -> list[tuple[float, float]]:
    top, bot = [], []
    for k in range(13):
        s = k / 12
        w = width * math.sin(math.pi * s) ** 0.8
        top.append(_rot(s * length, -w, ang))
        bot.append(_rot(s * length, w, ang))
    return [(cx + x, cy + y) for x, y in top + bot[::-1]]


# ======================================================================================
# МОДЕРН (цвета берутся из аватарки)
# ======================================================================================
def classic(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, c1, _ring(S, R * 0.98, R * 0.87))
    _paint(cv, shade(c1, 0.5), _ring(S, R * 0.98, R * 0.965), 0.7)
    _avatar(cv, av, R * 0.87)


def gradient(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, _grad(S, c1, c2), _ring(S, R * 0.98, R * 0.88))
    _avatar(cv, av, R * 0.82)


def double(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, c1, _ring(S, R * 0.98, R * 0.90))
    _paint(cv, c2, _ring(S, R * 0.85, R * 0.81))
    _avatar(cv, av, R * 0.78)


def neon(cv, av, c1, c2, R):
    S = cv.width
    ring = _ring(S, R * 0.90, R * 0.83)
    _paint(cv, c1, _glow(ring, S * 0.014, 2.2))
    _paint(cv, c1, ring)
    _paint(cv, mix(c1, (255, 255, 255), 0.65), _ring(S, R * 0.875, R * 0.855))
    _avatar(cv, av, R * 0.79)


def dashed(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, _grad(S, c1, c2), _arcs(S, R * 0.97, R * 0.09, 28, 360 / 28 * 0.62))
    _avatar(cv, av, R * 0.82)


def story(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, _grad(S, c1, c2, 60), _arcs(S, R * 0.98, R * 0.09, 4, 360 / 4 - 14))
    _avatar(cv, av, R * 0.84)


def aura(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, _grad(S, c1, c2), _glow(_circle(S, R * 0.80), S * 0.05, 1.5))
    _paint(cv, mix(c2, (255, 255, 255), 0.5), _ring(S, R * 0.735, R * 0.715))
    _avatar(cv, av, R * 0.70)


def beads(cv, av, c1, c2, R):
    S = cv.width
    m1, m2 = Image.new("L", (S, S), 0), Image.new("L", (S, S), 0)
    d1, d2 = ImageDraw.Draw(m1), ImageDraw.Draw(m2)
    for i in range(28):
        x, y = _pol(S, R * 0.92, TAU * i / 28)
        rr = R * (0.052 if i % 2 == 0 else 0.03)
        (d1 if i % 2 == 0 else d2).ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
    _paint(cv, c1, m1)
    _paint(cv, c2, m2)
    _paint(cv, c1, _ring(S, R * 0.81, R * 0.795))
    _avatar(cv, av, R * 0.77)


def aurora(cv, av, c1, c2, R):
    S = cv.width
    cone = _conic(S, [c1, mix(c1, c2, 0.5), c2, shade(c1, 0.5), c1])
    ring = _ring(S, R * 0.95, R * 0.83)
    _paint(cv, cone, _glow(ring, S * 0.03, 2.0), 0.85)
    _paint(cv, cone, ring)
    _paint(cv, (255, 255, 255), _ring(S, R * 0.95, R * 0.935), 0.55)
    _avatar(cv, av, R * 0.78)


def glass(cv, av, c1, c2, R):
    S = cv.width
    ring = _ring(S, R * 0.98, R * 0.84)
    _paint(cv, (255, 255, 255), ring, 0.22)
    _paint(cv, _grad(S, c1, c2), ring, 0.65)
    _paint(cv, (255, 255, 255), _ring(S, R * 0.98, R * 0.962), 0.85)
    _paint(cv, shade(c1, 0.4), _ring(S, R * 0.858, R * 0.84), 0.9)
    hl = _arcs(S, R * 0.95, R * 0.035, 1, 70, start=-150)
    _paint(cv, (255, 255, 255), hl, 0.9)
    _avatar(cv, av, R * 0.82)


def orbit(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, c2, _ring(S, R * 0.905, R * 0.895), 0.85)
    _paint(cv, c1, _ring(S, R * 0.97, R * 0.965), 0.5)
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    for i in range(48):
        x, y = _pol(S, R * 0.905, TAU * i / 48)
        d.ellipse((x - R * 0.009, y - R * 0.009, x + R * 0.009, y + R * 0.009), fill=255)
    _paint(cv, c2, m, 0.7)
    for ang, rad, size, col in ((0.8, 0.905, 0.055, c1), (3.9, 0.905, 0.035, c2), (5.2, 0.97, 0.03, c1)):
        x, y = _pol(S, R * rad, ang)
        g = Image.new("L", (S, S), 0)
        ImageDraw.Draw(g).ellipse((x - R * size, y - R * size, x + R * size, y + R * size), fill=255)
        _paint(cv, col, _glow(g, S * 0.012, 2.5))
        _paint(cv, shade(col, 0.4), g)
    _avatar(cv, av, R * 0.84)


def liquid(cv, av, c1, c2, R):
    S = cv.width
    cx = cy = S / 2
    outer, inner = [], []
    for k in range(240):
        t = TAU * k / 240
        ro = R * (0.93 + 0.028 * math.sin(3 * t + 0.7) + 0.016 * math.sin(5 * t + 2.1))
        ri = R * (0.81 + 0.016 * math.sin(4 * t + 1.3))
        outer.append((cx + ro * math.sin(t), cy - ro * math.cos(t)))
        inner.append((cx + ri * math.sin(t), cy - ri * math.cos(t)))
    mo, mi = Image.new("L", (S, S), 0), Image.new("L", (S, S), 0)
    ImageDraw.Draw(mo).polygon(outer, fill=255)
    ImageDraw.Draw(mi).polygon(inner, fill=255)
    ring = ImageChops.subtract(mo, mi)
    _paint(cv, c1, _glow(ring, S * 0.02, 1.6), 0.6)
    _paint(cv, _grad(S, c1, c2, 35), ring)
    _paint(cv, (255, 255, 255), _arcs(S, R * 0.88, R * 0.02, 1, 55, start=-135), 0.55)
    _avatar(cv, av, R * 0.775)


def duo(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, c1, _arcs(S, R * 0.97, R * 0.11, 1, 168, start=-180))
    _paint(cv, c2, _arcs(S, R * 0.97, R * 0.11, 1, 168, start=0))
    _avatar(cv, av, R * 0.82)


def pulse(cv, av, c1, c2, R):
    S = cv.width
    for ro, op, w in ((0.84, 1.0, 0.016), (0.90, 0.6, 0.014), (0.96, 0.3, 0.012)):
        _paint(cv, c1, _ring(S, R * (ro + w), R * ro), op)
    _paint(cv, c2, _glow(_ring(S, R * 0.85, R * 0.84), S * 0.01, 2.0), 0.7)
    _avatar(cv, av, R * 0.80)


def tech(cv, av, c1, c2, R):
    S = cv.width
    d = ImageDraw.Draw(cv)
    for i in range(72):
        a = TAU * i / 72
        big = i % 6 == 0
        p0 = _pol(S, R * (0.84 if big else 0.87), a)
        p1 = _pol(S, R * 0.93, a)
        d.line([p0, p1], fill=(*c1, 255), width=max(2, int(R * (0.016 if big else 0.008))))
    _paint(cv, c2, _arcs(S, R * 0.985, R * 0.022, 1, 250, start=-60))
    x, y = _pol(S, R * 0.985, 0.0)
    d.polygon([(x - R * 0.03, y - R * 0.01), (x + R * 0.03, y - R * 0.01), (x, y + R * 0.05)], fill=(*c2, 255))
    _avatar(cv, av, R * 0.77)


# ---- модерн, свои цвета ----
def _metal_ring(cv, av, R, stops, glow_col=None):
    S = cv.width
    cone = _conic(S, stops)
    ring = _ring(S, R * 0.98, R * 0.85)
    if glow_col:
        _paint(cv, glow_col, _glow(ring, S * 0.025, 1.6), 0.7)
    _paint(cv, cone, ring)
    _paint(cv, (255, 255, 255), _ring(S, R * 0.98, R * 0.972), 0.6)
    _paint(cv, (0, 0, 0), _ring(S, R * 0.858, R * 0.85), 0.35)
    _avatar(cv, av, R * 0.83)


def holo(cv, av, c1, c2, R):
    _metal_ring(cv, av, R, [(255, 170, 220), (170, 200, 255), (170, 255, 230), (255, 240, 170), (220, 180, 255), (255, 170, 220)], (200, 180, 255))


def rgb(cv, av, c1, c2, R):
    _metal_ring(cv, av, R, [(255, 0, 80), (255, 200, 0), (0, 255, 120), (0, 200, 255), (140, 0, 255), (255, 0, 80)], (120, 120, 255))


def gold(cv, av, c1, c2, R):
    S = cv.width
    _metal_ring(cv, av, R, [(255, 240, 170), (214, 160, 40), (120, 80, 10), (255, 225, 120), (180, 120, 20), (255, 245, 190)], (255, 190, 60))
    d = ImageDraw.Draw(cv)
    for a, r in ((0.7, 0.07), (2.4, 0.045), (4.1, 0.06), (5.5, 0.04)):
        x, y = _pol(S, R * 0.92, a)
        _sparkle(d, x, y, R * r, (255, 252, 225))


def chrome(cv, av, c1, c2, R):
    _metal_ring(cv, av, R, [(250, 250, 255), (120, 125, 140), (30, 32, 40), (200, 205, 220), (70, 72, 85), (250, 250, 255)], (180, 190, 220))


# ======================================================================================
# MINECRAFT (пиксельные блоки, аватарка тоже пикселизуется)
# ======================================================================================
def _block(d: ImageDraw.ImageDraw, x0: int, y0: int, cell: int, color: Color, rng: random.Random, ore: Color | None) -> None:
    base = shade(color, rng.uniform(-0.08, 0.08))
    d.rectangle((x0, y0, x0 + cell - 1, y0 + cell - 1), fill=base)
    sub = max(2, cell // 4)
    for _ in range(6):
        sx, sy = rng.randrange(4) * sub, rng.randrange(4) * sub
        d.rectangle((x0 + sx, y0 + sy, x0 + sx + sub - 1, y0 + sy + sub - 1), fill=shade(base, rng.choice((-0.18, -0.1, 0.1, 0.16))))
    if ore:
        for _ in range(4):
            sx, sy = rng.randrange(4) * sub, rng.randrange(4) * sub
            d.rectangle((x0 + sx, y0 + sy, x0 + sx + sub - 1, y0 + sy + sub - 1), fill=ore)
    t = max(1, cell // 14)
    d.rectangle((x0, y0, x0 + cell - 1, y0 + t - 1), fill=shade(base, 0.2))
    d.rectangle((x0, y0, x0 + t - 1, y0 + cell - 1), fill=shade(base, 0.1))
    d.rectangle((x0, y0 + cell - t, x0 + cell - 1, y0 + cell - 1), fill=shade(base, -0.28))
    d.rectangle((x0 + cell - t, y0, x0 + cell - 1, y0 + cell - 1), fill=shade(base, -0.2))


def _minecraft(seed: int, pick: Callable, tufts: Callable) -> Callable:
    def fn(cv, av, c1, c2, R):
        S = cv.width
        cell = max(6, S // 40)
        rng = random.Random(seed)
        ro = R * 0.97
        ri = ro - cell * 4
        _avatar(cv, av, ri, pixel=cell)
        d = ImageDraw.Draw(cv)
        n = S // cell + 1
        for j in range(n):
            for i in range(n):
                x0, y0 = i * cell, j * cell
                px, py = x0 + cell / 2 - S / 2, y0 + cell / 2 - S / 2
                dist = math.hypot(px, py)
                if dist < ri or dist > ro:
                    continue
                color, ore = pick(-py / dist, int((dist - ri) / cell), rng)
                _block(d, x0, y0, cell, color, rng, ore)
        tufts(d, S, cell, ro, rng)

    return fn


GRASS = [(95, 159, 53), (110, 177, 62), (84, 140, 46)]
DIRT = [(134, 96, 67), (121, 85, 58), (146, 105, 74)]
STONE = [(125, 125, 125), (136, 136, 136), (112, 112, 112)]
ORES = [(92, 240, 230), (250, 214, 70), (220, 30, 30), (216, 175, 147), (30, 30, 30)]


def _pick_over(cos_t, layer, rng):
    if cos_t > 0.2:
        return rng.choice(GRASS if layer == 3 else DIRT), None
    if cos_t < -0.35:
        return rng.choice(STONE), (rng.choice(ORES) if rng.random() < 0.16 else None)
    return rng.choice(DIRT), None


def _tufts_over(d, S, cell, ro, rng):
    for _ in range(90):
        a = rng.uniform(-1.0, 1.0)
        x, y = _pol(S, ro + cell * 0.55, a)
        i, j = int(x // cell), int(y // cell)
        if rng.random() < 0.55:
            _block(d, i * cell, j * cell, cell, rng.choice(GRASS), rng, None)


NETHER = [(111, 54, 53), (124, 62, 60), (96, 42, 45)]


def _pick_nether(cos_t, layer, rng):
    if cos_t > 0.2 and layer == 3:
        return rng.choice([(150, 30, 40), (190, 40, 50)]), None
    if cos_t < -0.4 and layer >= 1 and rng.random() < 0.55:
        return rng.choice([(255, 130, 30), (255, 190, 50), (230, 90, 20)]), None
    return rng.choice(NETHER), ((255, 215, 120) if rng.random() < 0.1 else None)


def _tufts_nether(d, S, cell, ro, rng):
    for _ in range(60):
        x, y = _pol(S, ro + cell * 0.55, rng.uniform(-1.2, 1.2))
        if rng.random() < 0.5:
            _block(d, int(x // cell) * cell, int(y // cell) * cell, cell, rng.choice([(255, 140, 30), (255, 200, 60), (210, 60, 20)]), rng, None)


ENDST = [(222, 224, 170), (210, 212, 155), (232, 233, 184)]


def _pick_end(cos_t, layer, rng):
    if rng.random() < 0.15:
        return (28, 12, 46), None
    if cos_t > 0.2 and layer == 3:
        return rng.choice([(150, 90, 160), (176, 112, 190)]), None
    return rng.choice(ENDST), None


def _tufts_end(d, S, cell, ro, rng):
    for _ in range(70):
        a = rng.uniform(0, TAU)
        x, y = _pol(S, ro + rng.uniform(0.2, 1.8) * cell, a)
        s = cell // 3
        d.rectangle((x, y, x + s, y + s), fill=rng.choice([(200, 100, 255), (150, 70, 230), (230, 170, 255)]))


DEEP = [(58, 58, 66), (70, 70, 80), (48, 48, 56)]


def _pick_dia(cos_t, layer, rng):
    r = rng.random()
    if r < 0.2:
        return rng.choice(DEEP), (92, 240, 230)
    if r < 0.26:
        return (250, 214, 60), None
    return rng.choice(DEEP), None


def _tufts_dia(d, S, cell, ro, rng):
    for _ in range(26):
        x, y = _pol(S, ro + rng.uniform(0.4, 2.2) * cell, rng.uniform(0, TAU))
        _sparkle(d, x, y, cell * rng.uniform(0.3, 0.7), (150, 255, 250))


mc_grass = _minecraft(11, _pick_over, _tufts_over)
mc_nether = _minecraft(23, _pick_nether, _tufts_nether)
mc_end = _minecraft(37, _pick_end, _tufts_end)
mc_diamond = _minecraft(41, _pick_dia, _tufts_dia)


# ======================================================================================
# ПРИРОДА
# ======================================================================================
def _flower(d, cx, cy, r, rot, petals, col, col2, center, notch=0.3, width=0.34):
    for k in range(petals):
        a = rot + TAU * k / petals
        d.polygon(_petal(cx, cy, r, a, notch, width), fill=col)
    for k in range(petals):
        a = rot + TAU * k / petals
        d.polygon(_petal(cx, cy, r * 0.6, a, notch, width), fill=col2)
    d.ellipse((cx - r * 0.15, cy - r * 0.15, cx + r * 0.15, cy + r * 0.15), fill=center)
    for k in range(7):
        a = rot + TAU * k / 7 + 0.3
        x, y = cx + math.cos(a) * r * 0.3, cy + math.sin(a) * r * 0.3
        d.line([(cx, cy), (x, y)], fill=center, width=max(1, int(r * 0.03)))
        d.ellipse((x - r * 0.04, y - r * 0.04, x + r * 0.04, y + r * 0.04), fill=shade(center, -0.2))


def _wavy_path(S, r0, amp, k, n=360, phase=0.0):
    pts = []
    for i in range(n + 1):
        t = TAU * i / n
        rr = r0 + amp * math.sin(k * t + phase)
        pts.append((S / 2 + rr * math.sin(t), S / 2 - rr * math.cos(t)))
    return pts


def sakura(cv, av, c1, c2, R):
    S = cv.width
    rng = random.Random(5)
    _avatar(cv, av, R * 0.82)
    d = ImageDraw.Draw(cv)
    path = _wavy_path(S, R * 0.89, R * 0.012, 7)
    d.line(path, fill=(92, 58, 46, 255), width=int(R * 0.034), joint="curve")
    d.line(path, fill=(138, 90, 70, 255), width=int(R * 0.012), joint="curve")
    for _ in range(14):  # веточки
        a = rng.uniform(0, TAU)
        p0, p1 = _pol(S, R * 0.89, a), _pol(S, R * rng.uniform(0.95, 1.0), a + rng.uniform(-0.12, 0.12))
        d.line([p0, p1], fill=(92, 58, 46, 255), width=int(R * 0.016))
    n = 15
    flowers = []
    for i in range(n):
        a = TAU * i / n + rng.uniform(-0.1, 0.1)
        x, y = _pol(S, R * (0.89 + rng.uniform(-0.02, 0.02)), a)
        flowers.append((rng.uniform(0.08, 0.125) * R, x, y, rng.uniform(0, TAU)))
    for r, x, y, rot in sorted(flowers):
        _flower(d, x, y, r, rot, 5, (255, 205, 220), (255, 150, 185), (255, 120, 150))
    for _ in range(26):  # лепестки
        a, rr = rng.uniform(0, TAU), R * rng.uniform(0.72, 1.02)
        x, y = _pol(S, rr, a)
        s = R * rng.uniform(0.025, 0.05)
        d.polygon(_petal(x, y, s, rng.uniform(0, TAU), 0.2, 0.4), fill=rng.choice([(255, 215, 228), (255, 190, 210), (255, 235, 242)]))


def autumn(cv, av, c1, c2, R):
    S = cv.width
    rng = random.Random(9)
    _avatar(cv, av, R * 0.82)
    d = ImageDraw.Draw(cv)
    d.line(_wavy_path(S, R * 0.88, R * 0.01, 6), fill=(98, 60, 36, 255), width=int(R * 0.03), joint="curve")
    cols = [(214, 69, 27), (240, 140, 30), (250, 200, 50), (170, 60, 25), (196, 44, 34), (225, 110, 30)]
    items = []
    for i in range(22):
        a = TAU * i / 22 + rng.uniform(-0.1, 0.1)
        x, y = _pol(S, R * rng.uniform(0.86, 0.93), a)
        items.append((rng.random(), x, y, a))
    for _, x, y, a in sorted(items):
        ang = a - math.pi / 2 + rng.uniform(-1.0, 1.0)
        col = rng.choice(cols)
        L, W = R * rng.uniform(0.14, 0.2), R * rng.uniform(0.05, 0.07)
        d.polygon(_leaf(x, y, L, W, ang), fill=col)
        x2, y2 = _rot(L * 0.95, 0, ang)
        d.line([(x, y), (x + x2, y + y2)], fill=shade(col, -0.35), width=max(2, int(R * 0.008)))
    for _ in range(12):
        x, y = _pol(S, R * rng.uniform(0.74, 1.0), rng.uniform(0, TAU))
        d.polygon(_leaf(x, y, R * 0.07, R * 0.025, rng.uniform(0, TAU)), fill=rng.choice(cols))


def laurel(cv, av, c1, c2, R):
    S = cv.width
    _avatar(cv, av, R * 0.80)
    d = ImageDraw.Draw(cv)
    light = shade(c1, 0.35)
    for side in (1, -1):
        stem = [_pol(S, R * 0.86, math.radians(178 - 150 * k / 40) * side) for k in range(41)]
        d.line(stem, fill=(*c2, 255), width=max(2, int(R * 0.012)), joint="curve")
        for k in range(1, 13):
            a = math.radians(178 - 150 * k / 12) * side
            x, y = _pol(S, R * 0.86, a)
            heading = math.atan2(-side * math.sin(a), -side * math.cos(a))  # куда растёт ветка
            L = R * (0.10 + 0.005 * k)
            for sgn, col in ((1, c1), (-1, light)):
                d.polygon(_leaf(x, y, L, R * 0.04, heading + sgn * 0.7), fill=(*col, 255))
    x, y = _pol(S, R * 0.87, 0.0)
    d.polygon(_leaf(x, y, R * 0.1, R * 0.04, -math.pi / 2), fill=(*c1, 255))


def daisy(cv, av, c1, c2, R):
    S = cv.width
    rng = random.Random(3)
    _avatar(cv, av, R * 0.82)
    d = ImageDraw.Draw(cv)
    d.line(_wavy_path(S, R * 0.88, R * 0.012, 5), fill=(60, 140, 80, 255), width=int(R * 0.028), joint="curve")
    for i in range(18):
        x, y = _pol(S, R * 0.88, TAU * i / 18 + 0.15)
        d.polygon(_leaf(x, y, R * 0.12, R * 0.04, TAU * i / 18 + rng.uniform(0, 1.5)), fill=rng.choice([(70, 165, 95), (96, 190, 110), (50, 130, 80)]))
    n = 11
    for i in range(n):
        a = TAU * i / n + rng.uniform(-0.08, 0.08)
        x, y = _pol(S, R * 0.89, a)
        r = R * rng.uniform(0.075, 0.1)
        _flower(d, x, y, r, rng.uniform(0, TAU), 12, (255, 255, 255), (238, 240, 246), (255, 196, 40), notch=0.0, width=0.14)


def snow(cv, av, c1, c2, R):
    S = cv.width
    rng = random.Random(8)
    ring = _ring(S, R * 0.90, R * 0.83)
    _paint(cv, (150, 220, 255), _glow(ring, S * 0.02, 2.0), 0.8)
    _paint(cv, _grad(S, (236, 250, 255), (110, 195, 250), 70), ring)
    _paint(cv, (255, 255, 255), _ring(S, R * 0.90, R * 0.885), 0.8)
    _avatar(cv, av, R * 0.79)
    d = ImageDraw.Draw(cv)

    def flake(x, y, r, col):
        w = max(2, int(r * 0.11))
        for k in range(6):
            a = TAU * k / 6
            ex, ey = x + r * math.cos(a), y + r * math.sin(a)
            d.line([(x, y), (ex, ey)], fill=col, width=w)
            for f in (0.5, 0.75):
                bx, by = x + r * f * math.cos(a), y + r * f * math.sin(a)
                for s in (-1, 1):
                    d.line([(bx, by), (bx + r * 0.28 * math.cos(a + s * 1.05), by + r * 0.28 * math.sin(a + s * 1.05))], fill=col, width=w)

    for i in range(11):
        x, y = _pol(S, R * rng.uniform(0.9, 0.97), TAU * i / 11 + rng.uniform(-0.08, 0.08))
        flake(x, y, R * rng.uniform(0.055, 0.1), (255, 255, 255, 255))
    for _ in range(40):
        x, y = _pol(S, R * rng.uniform(0.78, 1.02), rng.uniform(0, TAU))
        rr = R * rng.uniform(0.006, 0.014)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(255, 255, 255, 255))
    for a in (0.5, 2.3, 4.0, 5.3):
        x, y = _pol(S, R * 0.9, a)
        _sparkle(d, x, y, R * 0.05, (210, 245, 255))


def fire(cv, av, c1, c2, R):
    S = cv.width
    rng = random.Random(21)
    ring = _ring(S, R * 0.86, R * 0.78)
    _paint(cv, (255, 90, 20), _glow(_ring(S, R * 0.97, R * 0.78), S * 0.03, 1.6), 0.75)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(54):
        a = TAU * i / 54 + rng.uniform(-0.04, 0.04)
        h = R * rng.uniform(0.09, 0.2)
        w = R * rng.uniform(0.04, 0.06)
        lean = rng.uniform(-0.5, 0.5)
        for scale, col in ((1.0, (255, 70, 20)), (0.7, (255, 150, 30)), (0.4, (255, 228, 100))):
            ux, uy = math.sin(a), -math.cos(a)
            vx, vy = math.cos(a), math.sin(a)
            bx, by = _pol(S, R * 0.84, a)
            hh, ww = h * scale, w * scale
            pts = [(bx - vx * ww, by - vy * ww), (bx - vx * ww * 1.1 + ux * hh * 0.5, by - vy * ww * 1.1 + uy * hh * 0.5),
                   (bx + ux * hh + vx * hh * 0.25 * lean, by + uy * hh + vy * hh * 0.25 * lean),
                   (bx + vx * ww * 1.1 + ux * hh * 0.5, by + vy * ww * 1.1 + uy * hh * 0.5), (bx + vx * ww, by + vy * ww)]
            d.polygon(pts, fill=col)
    cv.alpha_composite(layer.filter(ImageFilter.GaussianBlur(S * 0.0025)))
    _paint(cv, _grad(S, (255, 90, 20), (255, 210, 70), 90), ring)
    _paint(cv, (255, 240, 170), _ring(S, R * 0.805, R * 0.79), 0.8)
    _avatar(cv, av, R * 0.76)
    d2 = ImageDraw.Draw(cv)
    for _ in range(26):
        x, y = _pol(S, R * rng.uniform(0.95, 1.05), rng.uniform(0, TAU))
        rr = R * rng.uniform(0.006, 0.014)
        d2.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(255, 190, 60, 255))


# ======================================================================================
# КОСМОС / КИБЕР
# ======================================================================================
def galaxy(cv, av, c1, c2, R):
    S = cv.width
    rng = random.Random(14)
    cone = _conic(S, [(90, 60, 255), (255, 80, 200), (60, 170, 255), (120, 60, 255), (90, 60, 255)])
    _paint(cv, cone, _glow(_ring(S, R * 0.95, R * 0.8), S * 0.04, 1.9), 0.9)
    _paint(cv, cone, _ring(S, R * 0.885, R * 0.835))
    _paint(cv, (255, 255, 255), _ring(S, R * 0.885, R * 0.875), 0.6)
    _avatar(cv, av, R * 0.80)
    d = ImageDraw.Draw(cv)
    for _ in range(130):
        x, y = _pol(S, R * rng.uniform(0.9, 1.02), rng.uniform(0, TAU))
        rr = R * rng.uniform(0.004, 0.012)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=rng.choice([(255, 255, 255, 255), (200, 190, 255, 255), (255, 235, 170, 255)]))
    for _ in range(14):
        x, y = _pol(S, R * rng.uniform(0.82, 1.0), rng.uniform(0, TAU))
        _sparkle(d, x, y, R * rng.uniform(0.025, 0.055), (255, 255, 255))


def cyber(cv, av, c1, c2, R):
    S = cv.width
    rng = random.Random(30)
    _avatar(cv, av, R * 0.82)
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    off = S * 0.009
    for col, o in (((0, 240, 255), -off), (((255, 43, 214)), off)):
        _paint(lay, col, _ring(S, R * 0.94, R * 0.87, S / 2 + o))
    for _ in range(9):
        y, h, dx = int(rng.uniform(0.1, 0.9) * S), int(rng.uniform(0.012, 0.03) * S), int(rng.uniform(-0.05, 0.05) * S)
        strip = lay.crop((0, y, S, y + h))
        lay.paste((0, 0, 0, 0), (0, y, S, y + h))
        lay.paste(strip, (dx, y), strip)
    cv.alpha_composite(lay)
    d = ImageDraw.Draw(cv)
    w, L, m = int(R * 0.016), R * 0.16, R * 0.05
    for sx in (1, -1):
        for sy in (1, -1):
            x, y = S / 2 + sx * (R - m), S / 2 + sy * (R - m)
            d.line([(x - sx * L, y), (x, y), (x, y - sy * L)], fill=(0, 240, 255, 255), width=w)


def retro(cv, av, c1, c2, R):
    S = cv.width
    ring = _ring(S, R * 0.97, R * 0.84)
    for k in range(7):
        y = S / 2 + R * (0.12 + 0.125 * k)
        h = R * (0.012 + 0.012 * k)
        ImageDraw.Draw(ring).rectangle((0, y, S, y + h), fill=0)
    _paint(cv, (255, 60, 160), _glow(ring, S * 0.02, 1.6), 0.6)
    _paint(cv, _vgrad(S, [(255, 225, 90), (255, 140, 60), (255, 50, 150), (130, 60, 255)]), ring)
    _paint(cv, (0, 235, 255), _ring(S, R * 0.995, R * 0.985), 0.9)
    _avatar(cv, av, R * 0.80)


def stars(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, c2, _ring(S, R * 0.835, R * 0.82), 0.9)
    d = ImageDraw.Draw(cv)
    for i in range(16):
        x, y = _pol(S, R * 0.915, TAU * i / 16)
        big = i % 2 == 0
        ro = R * (0.072 if big else 0.04)
        d.polygon(_star_pts(x, y, ro, ro * 0.45, TAU * i / 16), fill=(*(c1 if big else c2), 255))
    _avatar(cv, av, R * 0.80)


def hearts(cv, av, c1, c2, R):
    S = cv.width
    _paint(cv, c2, _ring(S, R * 0.835, R * 0.82), 0.9)
    d = ImageDraw.Draw(cv)
    for i in range(14):
        a = TAU * i / 14
        x, y = _pol(S, R * 0.91, a)
        big = i % 2 == 0
        d.polygon(_heart_pts(x, y, R * (0.11 if big else 0.07), a + math.pi), fill=(*(c1 if big else c2), 255))
    _avatar(cv, av, R * 0.80)


# ======================================================================================
# ФАН
# ======================================================================================
def king(cv, av, c1, c2, R):
    S = cv.width
    cy = S / 2 + R * 0.10
    gold_stops = [(255, 240, 170), (214, 160, 40), (120, 80, 10), (255, 225, 120), (180, 120, 20), (255, 245, 190)]
    ring = _ring(S, R * 0.78, R * 0.70, S / 2, cy)
    _paint(cv, (255, 190, 60), _glow(ring, S * 0.02, 1.6), 0.7)
    _paint(cv, _conic(S, gold_stops), ring)
    _avatar(cv, av, R * 0.67, S / 2, cy)
    d = ImageDraw.Draw(cv)
    W, H = R * 0.56, R * 0.27
    x0, yb = S / 2, cy - R * 0.70
    pts = [(x0 - W / 2, yb), (x0 - W / 2, yb - H), (x0 - W / 4, yb - H * 0.45), (x0, yb - H * 1.15), (x0 + W / 4, yb - H * 0.45), (x0 + W / 2, yb - H), (x0 + W / 2, yb)]
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    _paint(cv, _vgrad(S, [(255, 240, 150), (240, 180, 40), (170, 110, 15)]), m)
    d.rectangle((x0 - W / 2, yb - R * 0.045, x0 + W / 2, yb), fill=(170, 110, 15, 255))
    for (px, py), col, r in (((x0 - W / 2, yb - H), (255, 255, 255), 0.035), ((x0, yb - H * 1.15), (255, 70, 90), 0.045), ((x0 + W / 2, yb - H), (255, 255, 255), 0.035)):
        d.ellipse((px - R * r, py - R * r, px + R * r, py + R * r), fill=(*col, 255))
    for k in (-1, 0, 1):
        d.ellipse((x0 + k * W * 0.3 - R * 0.016, yb - R * 0.028, x0 + k * W * 0.3 + R * 0.016, yb - R * 0.012), fill=(255, 235, 150, 255))


def cat(cv, av, c1, c2, R):
    S = cv.width
    cy = S / 2 + R * 0.06
    d = ImageDraw.Draw(cv)
    inner = mix(c1, (255, 175, 195), 0.6)
    for side in (-1, 1):
        a0, a1 = math.radians(18) * side, math.radians(64) * side
        base0, base1 = _pol(S, R * 0.74, a0, S / 2, cy), _pol(S, R * 0.74, a1, S / 2, cy)
        tip = _pol(S, R * 1.04, (a0 + a1) / 2 + 0.06 * side, S / 2, cy)
        d.polygon([base0, tip, base1], fill=(*c1, 255))
        mid = ((base0[0] + base1[0]) / 2, (base0[1] + base1[1]) / 2)
        pts = [(mid[0] + (p[0] - mid[0]) * 0.55, mid[1] + (p[1] - mid[1]) * 0.55) for p in (base0, tip, base1)]
        pts = [(p[0] + (tip[0] - mid[0]) * 0.08, p[1] + (tip[1] - mid[1]) * 0.08) for p in pts]
        d.polygon(pts, fill=(*inner, 255))
    _paint(cv, c1, _ring(S, R * 0.80, R * 0.73, S / 2, cy))
    _paint(cv, shade(c1, 0.5), _ring(S, R * 0.80, R * 0.785, S / 2, cy), 0.6)
    _avatar(cv, av, R * 0.73, S / 2, cy)


def halo(cv, av, c1, c2, R):
    S = cv.width
    cy = S / 2 + R * 0.10
    ring = _ring(S, R * 0.76, R * 0.71, S / 2, cy)
    _paint(cv, (255, 215, 110), ring, 0.9)
    _avatar(cv, av, R * 0.69, S / 2, cy)
    hm = Image.new("L", (S, S), 0)
    ImageDraw.Draw(hm).ellipse((S / 2 - R * 0.36, cy - R * 0.93, S / 2 + R * 0.36, cy - R * 0.69), outline=255, width=int(R * 0.05))
    _paint(cv, (255, 200, 80), _glow(hm, S * 0.02, 2.2), 0.9)
    _paint(cv, _vgrad(S, [(255, 250, 200), (255, 205, 90)]), hm)
    d = ImageDraw.Draw(cv)
    for a, r in ((-0.6, 0.05), (0.7, 0.04)):
        x, y = _pol(S, R * 0.95, a)
        _sparkle(d, x, y, R * r, (255, 250, 220))


# ======================================================================================
# реестр
# ======================================================================================
CATS = [("all", "Все"), ("modern", "Модерн"), ("mc", "Minecraft"), ("nature", "Природа"), ("space", "Космос"), ("fun", "Фан")]

STYLES: dict[str, dict] = {}


def _reg(sid: str, name: str, cat: str, themed: bool, fn: Callable) -> None:
    STYLES[sid] = {"name": name, "cat": cat, "themed": themed, "fn": fn}


_reg("neon", "Неон", "modern", False, neon)
_reg("aurora", "Аврора", "modern", False, aurora)
_reg("glass", "Стекло", "modern", False, glass)
_reg("liquid", "Жидкость", "modern", False, liquid)
_reg("gradient", "Градиент", "modern", False, gradient)
_reg("orbit", "Орбита", "modern", False, orbit)
_reg("aura", "Аура", "modern", False, aura)
_reg("pulse", "Импульс", "modern", False, pulse)
_reg("tech", "HUD", "modern", False, tech)
_reg("story", "Сегменты", "modern", False, story)
_reg("duo", "Дуэт", "modern", False, duo)
_reg("double", "Двойное", "modern", False, double)
_reg("dashed", "Пунктир", "modern", False, dashed)
_reg("beads", "Бусины", "modern", False, beads)
_reg("classic", "Классика", "modern", False, classic)
_reg("holo", "Голограмма", "modern", True, holo)
_reg("rgb", "RGB", "modern", True, rgb)
_reg("gold", "Золото", "modern", True, gold)
_reg("chrome", "Хром", "modern", True, chrome)
_reg("mc_grass", "Майнкрафт", "mc", True, mc_grass)
_reg("mc_nether", "Незер", "mc", True, mc_nether)
_reg("mc_end", "Энд", "mc", True, mc_end)
_reg("mc_diamond", "Алмазы", "mc", True, mc_diamond)
_reg("sakura", "Сакура", "nature", True, sakura)
_reg("autumn", "Осень", "nature", True, autumn)
_reg("daisy", "Ромашки", "nature", True, daisy)
_reg("snow", "Зима", "nature", True, snow)
_reg("fire", "Огонь", "nature", True, fire)
_reg("laurel", "Лавр", "nature", False, laurel)
_reg("galaxy", "Галактика", "space", True, galaxy)
_reg("cyber", "Киберпанк", "space", True, cyber)
_reg("retro", "Синтвейв", "space", True, retro)
_reg("stars", "Звёзды", "space", False, stars)
_reg("hearts", "Сердечки", "fun", False, hearts)
_reg("king", "Корона", "fun", True, king)
_reg("cat", "Кошка", "fun", False, cat)
_reg("halo", "Нимб", "fun", True, halo)


def render_frame(av: Image.Image, style: str, c1: Color, c2: Color, size: int = 1024) -> Image.Image:
    S = size * 2
    cv = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    STYLES[style]["fn"](cv, av, c1, c2, S / 2)
    return cv.resize((size, size), Image.LANCZOS)
