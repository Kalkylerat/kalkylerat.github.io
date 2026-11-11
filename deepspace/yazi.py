"""Yazı katmanları: görev kartı, parça etiketi, kapak ve Shorts yazıları (PIL, şeffaf PNG)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .ortak import marka_yukle, rgb

FONT = Path(__file__).resolve().parent / "font"
_FONTLAR = {  # marka yazısı Space Mono (marka.toml [yazi]); yoksa sistem fontları
    "kalin": [str(FONT / "SpaceMono-Bold.ttf"), "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "normal": [str(FONT / "SpaceMono-Regular.ttf"), "/usr/share/fonts/opentype/inter/Inter-Medium.otf", "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
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
    palet = marka_yukle()["palet"]
    for k, (xx, yy, metin, f, opak) in enumerate(konumlar):
        renk = rgb(palet["yazi"] if k == 0 or f.size >= konumlar[0][3].size else palet["yazi_ikincil"])
        d.text((xx, yy), metin, font=f, fill=(*renk, int(255 * opak)))
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


KAPAK_DUZENLERI = ("ust", "alt", "etiket")


def _aralikli(d: ImageDraw.ImageDraw, metin: str, f: ImageFont.FreeTypeFont, iz: float, cx: float, y: float,
              renk: tuple, golge: int) -> None:
    gen = sum(f.getlength(c) for c in metin) + iz * (len(metin) - 1)
    x = cx - gen / 2
    for c in metin:
        if golge:
            d.text((x + golge, y + golge), c, font=f, fill=(0, 0, 0, 160))
        d.text((x, y), c, font=f, fill=renk)
        x += f.getlength(c) + iz


def kapak_katmani(W: int, H: int, baslik: str, etiket: str, duzen: str) -> Image.Image:
    """Marka kapak şablonu (G16): ortada harf aralıklı başlık, kehribar çizgi ve kehribar etiket.

    duzen: 'ust' başlık üstte; 'alt' başlık altta; 'etiket' seri etiketi başlığın önünde (üstte).
    Boyutlar marka.toml [sablon]'dan, 720 yüksekliğe göre ölçeklenir.
    """
    if duzen not in KAPAK_DUZENLERI:
        raise ValueError(f"bilinmeyen kapak düzeni: {duzen}")
    m = marka_yukle()
    o = H / 720
    boy, eboy = int(m["sablon"]["kapak_baslik"] * o), int(m["sablon"]["kapak_etiket"] * o)
    iz, eiz = boy * 0.29, eboy * 0.32
    fb = font(boy, "normal")  # ince başlık, kalın etiket (marka kiti)
    while sum(fb.getlength(c) for c in baslik) + iz * (len(baslik) - 1) > W * 0.9 and boy > eboy * 2:
        boy = int(boy * 0.92)
        iz, fb = boy * 0.29, font(boy, "normal")
    fe = font(eboy, "kalin")
    yazi_rgb, vurgu = rgb(m["palet"]["yazi"]), rgb(m["palet"]["vurgu"])
    cizgi, kalinlik = boy * 4, max(2, boy // 30)
    golge = max(1, round(2 * o))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bas = round(46 * o)
    if duzen == "etiket":
        _aralikli(d, etiket, fe, eiz, W / 2, bas, (*vurgu, 255), golge)
        cy = bas + eboy * 1.6
        d.line([(W / 2 - cizgi / 2, cy), (W / 2 + cizgi / 2, cy)], fill=(*vurgu, 255), width=kalinlik)
        _aralikli(d, baslik, fb, iz, W / 2, cy + boy * 0.3, (*yazi_rgb, 255), golge)
        return img
    blok = boy * 1.45 + eboy * 1.9
    y = bas if duzen == "ust" else H - round(60 * o) - blok
    _aralikli(d, baslik, fb, iz, W / 2, y, (*yazi_rgb, 255), golge)
    cy = y + boy * 1.45
    d.line([(W / 2 - cizgi / 2, cy), (W / 2 + cizgi / 2, cy)], fill=(*vurgu, 255), width=kalinlik)
    _aralikli(d, etiket, fe, eiz, W / 2, cy + eboy * 0.6, (*vurgu, 255), golge)
    return img
