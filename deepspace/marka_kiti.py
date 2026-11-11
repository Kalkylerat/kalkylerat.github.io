"""Kanal marka kiti (G16): banner, profil, filigran ve tek sayfalık marka kitabı, kitin kaynak görselinden.

Kaynak `deepspace/marka/kaynak/A2.png` (sahibinin seçtiği ana görsel, 11 Kasım 2026). Renk tonu `marka.toml [filtre]`,
yazılar `[sablon]` ve Space Mono. Kit değişirse marka istasyonu yeniden denetlenir ve sahibinin onayı yenilenir.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import yazi
from .ortak import KOK, marka_yukle, rgb
from .renk import marka_filtresi
from .renk import uygula as renk_uygula
from .sahne import probe_sprite

KAYNAK = KOK / "marka" / "kaynak" / "A2.png"
ALT_YAZI = "SPACE AMBIENT FOR FOCUS & SLEEP  ·  NEW MISSION WEEKLY"
GUVENLI_ALAN = (1546, 423)  # YouTube banner'ında her cihazda görünen orta alan (2560x1440 içinde)
# Banner kaynağı: ufuk kemeri güvenli banda girsin diye görsel yukarı kaydırılır (kaynağın 765 satırında 80 satır);
# alttaki boşluk ufkun altındaki karanlık zeminin (640. satırdan sonrası) dikey esnetilmesiyle dolar.
BANNER_KAYDIR, BANNER_ZEMIN = 80 / 765, 640 / 765
BANNER_BASLIK_Y, BANNER_PROBE_Y, BANNER_PROBE_BOY = 510, 812, 70
FILIGRAN_HALKA, FILIGRAN_PROBE = (6, 144), 68  # PROBE-7'nin panel uçları halkanın iç kenarından ~6 px içeride


def _filtrele(img: Image.Image) -> Image.Image:
    t = marka_filtresi()
    rgb_img = img.convert("RGB")
    return Image.fromarray(renk_uygula(np.asarray(rgb_img), t)) if t else rgb_img


def probe_ekle(img: Image.Image, x: float, y: float, boy: int) -> None:
    rgb_, alfa = probe_sprite(boy)
    s = Image.fromarray((np.concatenate([rgb_, alfa], axis=2) * 255).astype(np.uint8), "RGBA")
    img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))


def _baslik(img: Image.Image, ust: str, alt: str, y: float, boy: int, alt_boy: int, cizgi: int) -> None:
    m = marka_yukle()["palet"]
    katman = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(katman)
    W = img.width
    yazi._aralikli(d, ust, yazi.font(boy, "normal"), boy * 0.27, W / 2, y, (*rgb(m["yazi"]), 255), 2)
    cy = y + boy * 1.45
    d.line([(W / 2 - cizgi / 2, cy), (W / 2 + cizgi / 2, cy)], fill=(*rgb(m["vurgu"]), 255), width=max(2, boy // 30))
    yazi._aralikli(d, alt, yazi.font(alt_boy, "kalin"), alt_boy * 0.15, W / 2, cy + alt_boy * 0.6,
                   (*rgb(m["vurgu"]), 255), 2)
    img.alpha_composite(katman)


def _kirp_169(img: Image.Image) -> Image.Image:
    W, H = img.size
    h = round(W * 9 / 16)
    return img.crop((0, 0, W, min(H, h)))


def _banner_kaynak(ana: Image.Image) -> Image.Image:
    """16:9 kaynak, ufuk yukarıda: üstten BANNER_KAYDIR kırpılır, ufkun altındaki zemin esnetilerek boy korunur."""
    k = _kirp_169(ana)
    W, H = k.size
    ust, kes = round(H * BANNER_KAYDIR), round(H * BANNER_ZEMIN)
    yeni = Image.new("RGB", (W, H))
    yeni.paste(k.crop((0, ust, W, kes)), (0, 0))
    yeni.paste(k.crop((0, kes, W, H)).resize((W, H - (kes - ust)), Image.LANCZOS), (0, kes - ust))
    return yeni


def banner(ana: Image.Image) -> Image.Image:
    b = _filtrele(_banner_kaynak(ana).resize((2560, 1440), Image.LANCZOS)).convert("RGBA")
    _baslik(b, "DEEP SPACE LOG", ALT_YAZI, BANNER_BASLIK_Y, 120, 34, 560)
    probe_ekle(b, 2560 * 0.5, BANNER_PROBE_Y, BANNER_PROBE_BOY)
    return b


def profil(ana: Image.Image) -> Image.Image:
    """800x800: ufuk kemerinin ortası, ortada PROBE-7 (98 px dairede de seçilir)."""
    t = _filtrele(ana)
    W, H = t.size
    k = min(W, H) * 600 // 768
    kare = t.crop((W // 2 - k // 2, 0, W // 2 + k // 2, k)).resize((800, 800), Image.LANCZOS).convert("RGBA")
    kare.alpha_composite(Image.new("RGBA", (800, 800), (*rgb(marka_yukle()["palet"]["arka"]), 90)))
    probe_ekle(kare, 400, 330, 360)
    return kare


def filigran() -> Image.Image:
    """150x150 şeffaf video filigranı: PROBE-7 ve ince kehribar halka."""
    m = marka_yukle()["palet"]
    f = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
    a, z = FILIGRAN_HALKA
    ImageDraw.Draw(f).ellipse([a, a, z, z], fill=(*rgb(m["arka"]), 150), outline=(*rgb(m["vurgu"]), 230),
                              width=3)
    probe_ekle(f, 75, 75, FILIGRAN_PROBE)
    return f


def ornek_kapak(ana: Image.Image) -> Image.Image:
    k = _filtrele(_kirp_169(ana).resize((1280, 720), Image.LANCZOS)).convert("RGBA")
    k.alpha_composite(yazi.kapak_katmani(1280, 720, "DEEP FOCUS", "2H", "ust"))
    probe_ekle(k, 1280 * 0.84, 720 * 0.40, 54)
    return k


def kitap(b: Image.Image, p: Image.Image, fil: Image.Image, kapak: Image.Image) -> Image.Image:
    m = marka_yukle()
    gri, beyaz = (170, 175, 190), rgb(m["palet"]["yazi"])
    S = Image.new("RGB", (1600, 1500), (10, 12, 20))
    d = ImageDraw.Draw(S)
    yazi._aralikli(d, "DEEP SPACE LOG  ·  BRAND KIT", yazi.font(34, "kalin"), 6, 800, 40, (*beyaz, 255), 0)
    S.paste(b.convert("RGB").resize((1000, 562)), (40, 120))
    d.text((40, 690), "Banner 2560x1440 (yazı güvenli alanda)", font=yazi.font(18), fill=gri)
    S.paste(p.convert("RGB").resize((240, 240)), (1100, 120))
    av = p.convert("RGB").resize((98, 98))
    maske = Image.new("L", (98, 98), 0)
    ImageDraw.Draw(maske).ellipse([0, 0, 97, 97], fill=255)
    S.paste(av, (1370, 120), maske)
    d.text((1100, 370), "Profil 800x800 · 98 px daire", font=yazi.font(18), fill=gri)
    S.paste(fil, (1100, 420), fil)
    d.text((1270, 480), "Filigran 150x150", font=yazi.font(18), fill=gri)
    S.paste(kapak.convert("RGB").resize((760, 428)), (40, 740))
    S.paste(kapak.convert("RGB").resize((168, 94)), (820, 740))
    d.text((40, 1178), "Kapak şablonu 1280x720 (en fazla 3 kelime) · sağda 168x94", font=yazi.font(18), fill=gri)
    for i, (ad, h) in enumerate(m["palet"].items()):
        x, y = 1100 + (i % 3) * 160, 620 + (i // 3) * 160
        d.rectangle([x, y, x + 130, y + 90], fill=h, outline=(60, 64, 80))
        d.text((x, y + 96), ad, font=yazi.font(16), fill=gri)
        d.text((x, y + 116), h, font=yazi.font(16), fill=gri)
    ton = m.get("filtre", {}).get("secim") or "yok"
    for j, (metin, boy) in enumerate([("Yazı: Space Mono (OFL)", 22), (f"Film tonu: {ton}", 18),
                                      ("Vurgu: kehribar çizgi ve etiket", 18), ("PROBE-7 gökte, küçük", 18)]):
        d.text((1100, 960 + j * 34), metin, font=yazi.font(boy, "kalin" if j == 0 else "normal"),
               fill=beyaz if j == 0 else gri)
    d.text((40, 1230), "Görsel dili: karanlık durgun ufuk, gökyüzünü kaplayan tek galaksi/bulutsu, bol boşluk,",
           font=yazi.font(20), fill=beyaz)
    d.text((40, 1262), "üstte ince harf aralıklı başlık. Her sahne uzayda; insan figürü yok ya da çok küçük.",
           font=yazi.font(20), fill=beyaz)
    return S


def uret(kaynak: Path = KAYNAK, hedef: Path = KOK / "marka") -> list[Path]:
    hedef = Path(hedef)
    hedef.mkdir(parents=True, exist_ok=True)
    ana = Image.open(kaynak).convert("RGB")
    b, p, fil = banner(ana), profil(ana), filigran()
    yollar = [hedef / "banner.jpg", hedef / "profil.png", hedef / "filigran.png", hedef / "marka_kitabi.jpg"]
    b.convert("RGB").save(yollar[0], quality=92)
    p.convert("RGB").save(yollar[1])
    fil.save(yollar[2])
    kitap(b, p, fil, ornek_kapak(ana)).save(yollar[3], quality=90)
    return yollar
