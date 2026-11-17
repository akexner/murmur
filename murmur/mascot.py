"""Murmi, the little puff-bird. Palette + a PIL renderer (tray icon, .ico)."""
from PIL import Image, ImageDraw

BODY = "#B9A9FF"
BODY_DARK = "#9D8CFF"
BELLY = "#F4EFFF"
BEAK = "#FFA94D"
INK = "#2B2438"
CHEEK = "#FF9EB5"


def draw(size=256, blink=False, bg=None) -> Image.Image:
    S = 4  # supersample
    n = size * S
    im = Image.new("RGBA", (n, n), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = n / 120.0

    def e(cx, cy, rx, ry, fill):
        d.ellipse([(cx - rx) * u, (cy - ry) * u, (cx + rx) * u, (cy + ry) * u], fill=fill)

    # tuft
    d.polygon([(56 * u, 26 * u), (52 * u, 10 * u), (59 * u, 18 * u), (62 * u, 6 * u),
               (66 * u, 18 * u), (72 * u, 11 * u), (66 * u, 28 * u)], fill=BODY_DARK)
    e(21, 70, 9, 14, BODY_DARK)
    e(99, 70, 9, 14, BODY_DARK)
    e(60, 64, 42, 40, BODY)
    e(60, 76, 27, 22, BELLY)
    e(46, 104, 8, 4, BEAK)
    e(74, 104, 8, 4, BEAK)
    e(37, 68, 6, 4.5, CHEEK)
    e(83, 68, 6, 4.5, CHEEK)
    if blink:
        for cx in (46, 74):
            d.arc([(cx - 5) * u, 52 * u, (cx + 5) * u, 62 * u], 200, 340, fill=INK, width=int(2.2 * u))
    else:
        for cx in (46, 74):
            e(cx, 57, 4.6, 5.6, INK)
            e(cx + 1.6, 55, 1.6, 1.6, "#FFFFFF")
    d.polygon([(53 * u, 64 * u), (67 * u, 64 * u), (60 * u, 73 * u)], fill=BEAK)
    return im.resize((size, size), Image.LANCZOS)


def save_ico(path):
    im = draw(256)
    im.save(path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
