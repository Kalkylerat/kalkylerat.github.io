"""Yazı katmanları: görev kartı, parça etiketi, kapak ve Shorts yazıları (PIL, şeffaf PNG)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

_FONTLAR = {
    "kalin": ["/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "normal": ["/usr/share/fonts/opentype/inter/Inter-Medium.otf", "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


@lru_cache(maxsize=32)
def font(boy: int, agirlik: str = "normal") -> ImageFont.FreeTypeFont:
    for yol in _FONTLAR[agirlik]:
        if Path(yol).exists():
            return ImageFont.truetype(yol, boy)
    return ImageFont.load_default(boy)



def katman(W: int, H: int, satirlar: list[tuple[str, int, str, float]], x: int, y: int,
           hiza: str = "sol", golge: bool = True) -> Image.Image:
    """satirlar: (metin, boy, agirlik, opaklik). (x, y) ilk satırın sol üstü (hiza='orta' ise ortası)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    yy = y
    konumlar = []
    for metin, boy, agirlik, opak in satirlar:
        f = font(boy, agirlik)
        kutu = d.textbbox((0, 0), metin, font=f)
        gen = kutu[2] - kutu[0]
        xx = x - gen // 2 if hiza == "orta" else (x - gen if hiza == "sag" else x)
        konumlar.append((xx, yy, metin, f, opak))
        yy += int(boy * 1.28)
    if golge:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        for xx, yy, metin, f, opak in konumlar:
            gd.text((xx, yy + 2), metin, font=f, fill=(0, 0, 0, int(200 * opak)))
        img = Image.alpha_composite(img, g.filter(ImageFilter.GaussianBlur(max(2, H // 300))))
        d = ImageDraw.Draw(img)
    for xx, yy, metin, f, opak in konumlar:
        d.text((xx, yy), metin, font=f, fill=(240, 240, 245, int(255 * opak)))
    return img


def gorev_karti(W: int, H: int, gorev: dict, kanal: str, saat: int) -> Image.Image:
    o = H / 1080
    satir = [(f"{kanal.upper()}  ·  MISSION {gorev['no']:03d}", int(26 * o), "normal", 0.85),
             (gorev["hedef"], int(72 * o), "kalin", 1.0),
             (f"{gorev['uzaklik']}  ·  {len(gorev['parca'])} destinations  ·  {saat} hours", int(26 * o), "normal",
              0.8)]
    return katman(W, H, satir, int(96 * o), int(H - 300 * o))


def parca_etiketi(W: int, H: int, no: int, parca: dict) -> Image.Image:
    o = H / 1080
    satir = [(f"{no:02d}   {parca['ad']}", int(34 * o), "kalin", 0.92)]
    if parca.get("kisa"):
        satir.append((parca["kisa"], int(22 * o), "normal", 0.72))
    return katman(W, H, satir, int(96 * o), int(H - 190 * o))
