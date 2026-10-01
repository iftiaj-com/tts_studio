"""
tools/make_assets.py
─────────────────────
Regenerates assets/voicecraft.ico (EXE, shortcuts, installer) and
assets/splash.png (PyInstaller splash shown during the slow first start)
from the app's design tokens. The outputs are committed; rerun only to
change the artwork:

    .\\venv_311\\Scripts\\python.exe tools\\make_assets.py
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.constants import COLORS            # noqa: E402
from core.version import APP_TITLE, __version__  # noqa: E402

ASSETS = os.path.join(ROOT, "assets")
BARS = (0.30, 0.55, 0.85, 1.00, 0.70, 0.45, 0.25)   # waveform heights


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _blend(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def draw_mark(size):
    """Rounded tile with a two-tone waveform, drawn at 4x then downsampled."""
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 0.22, fill=_hex(COLORS["bg_card"]))
    a, b = _hex(COLORS["accent_primary"]), _hex(COLORS["accent_secondary"])
    n = len(BARS)
    pad, gap = s * 0.17, s * 0.035
    w = (s - 2 * pad - gap * (n - 1)) / n
    for i, h in enumerate(BARS):
        x0 = pad + i * (w + gap)
        bh = (s - 2 * pad) * h
        y0 = (s - bh) / 2
        d.rounded_rectangle([x0, y0, x0 + w, y0 + bh], radius=w / 2,
                            fill=_blend(a, b, i / (n - 1)))
    return img.resize((size, size), Image.LANCZOS)


def make_ico(path):
    sizes = [16, 24, 32, 48, 64, 128, 256]
    big = draw_mark(256)
    big.save(path, format="ICO", sizes=[(n, n) for n in sizes])


def _font(px, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arial.ttf"):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                                                   "Fonts", name), px)
        except OSError:
            continue
    return ImageFont.load_default()


def make_splash(path):
    W, H = 520, 260
    img = Image.new("RGB", (W, H), _hex(COLORS["bg_dark"]))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 4], fill=_hex(COLORS["accent_primary"]))
    mark = draw_mark(96)
    img.paste(mark, (40, 60), mark)
    d.text((160, 70), APP_TITLE, font=_font(30, bold=True), fill=_hex(COLORS["text_primary"]))
    d.text((161, 115), f"Version {__version__}", font=_font(16), fill=_hex(COLORS["text_muted"]))
    # PyInstaller's splash draws the loading text over this area.
    img.save(path, format="PNG")


if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    make_ico(os.path.join(ASSETS, "voicecraft.ico"))
    make_splash(os.path.join(ASSETS, "splash.png"))
    print("wrote", os.listdir(ASSETS))
