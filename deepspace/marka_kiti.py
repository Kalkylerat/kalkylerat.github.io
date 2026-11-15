"""Kanal marka kiti (G16): banner, profil, filigran ve tek sayfalık marka kitabı, kayıt defteri dilinde.

Kaynak, kanalda 12 Kasım 2026'dan beri duran ve sahibinin onayladığı defter tasarımıdır
(`deepspace/marka/taslak/banner_defter.jpg`, `profil_defter.png`; çizen kod `taslak/defter_kiti.py`). Banner ve
profil bu dosyaların bayt bayt kopyasıdır (kanaldakiyle aynı kalsın diye yeniden çizilmez). Filigran profildeki işaretin
(kehribar yörünge halkası içinde "7") şeffaf küçültmesidir. Kit sayfası bunları, G7 kapak düzenini (`kapak.kapak_ciz`)
ve paleti gösterir. Fotoğraf zemini ve sahneye çizilmiş sonda yoktur (gorsel-dili 7). Kit değişirse marka istasyonu
yeniden denetlenir ve sahibinin onayı yenilenir.
"""
from __future__ import annotations

import io
import random
import shutil
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import yazi
from .ortak import KOK, marka_yukle, rgb

TASLAK = KOK / "marka" / "taslak"
KAYNAK_BANNER = TASLAK / "banner_defter.jpg"   # sahibinin onayı, kanalda 12 Kasım 2026'dan beri
KAYNAK_PROFIL = TASLAK / "profil_defter.png"
ORNEK_GOREV = KOK / "gorevler" / "001-trappist" / "gorev.toml"  # kapak örneğinin gerçek verisi
GUVENLI_ALAN = (1546, 423)  # YouTube banner'ında her cihazda görünen orta alan (2560x1440 içinde)
FILIGRAN_BOY = 150
FILIGRAN_DISK = 0.94  # mürekkep diskin çapı / filigran kenarı: kenarlar şeffaf kalır
KITAP_BOY = (1600, 1500)


def _vurgu_maskesi(profil: Image.Image) -> np.ndarray:
    """Profildeki kehribar işaretin örtüsü (0..1): mürekkep zeminden vurgu rengine olan uzaklık."""
    m = marka_yukle()["palet"]
    arka, vurgu = np.array(rgb(m["arka"]), float), np.array(rgb(m["vurgu"]), float)
    a = np.asarray(profil.convert("RGB"), float)
    yon = vurgu - arka
    return np.clip(((a - arka) @ yon) / (yon @ yon), 0, 1)


def filigran(profil: Image.Image | None = None) -> Image.Image:
    """150x150 şeffaf video filigranı: profildeki halka-7 işareti, yarı saydam mürekkep disk üstünde kehribar."""
    profil = profil or Image.open(KAYNAK_PROFIL)
    m = marka_yukle()["palet"]
    B, k = FILIGRAN_BOY, 4
    buyuk = B * k
    isaret = Image.fromarray((_vurgu_maskesi(profil) * 255).astype(np.uint8), "L").resize((buyuk, buyuk), Image.LANCZOS)
    disk = Image.new("L", (buyuk, buyuk), 0)
    r = buyuk * FILIGRAN_DISK / 2
    ImageDraw.Draw(disk).ellipse([buyuk / 2 - r, buyuk / 2 - r, buyuk / 2 + r, buyuk / 2 + r], fill=150)
    f = Image.new("RGBA", (buyuk, buyuk), (*rgb(m["arka"]), 0))
    f.putalpha(disk)
    ust = Image.new("RGBA", (buyuk, buyuk), (*rgb(m["vurgu"]), 0))
    ust.putalpha(isaret.point(lambda v: round(v * 0.92)))
    f.alpha_composite(ust)
    f = f.resize((B, B), Image.LANCZOS)
    a = np.asarray(f).copy()
    a[[0, -1], :, 3] = 0
    a[:, [0, -1], 3] = 0
    return Image.fromarray(a, "RGBA")


def _ornek_gorev() -> dict:
    with open(ORNEK_GOREV, "rb") as f:
        g = tomllib.load(f)
    return {k: g.get(k, "") for k in ("no", "ad", "hedef", "koordinat", "uzaklik")}


def ornek_kapak() -> Image.Image:
    """G7 kapak düzeni (`kapak.kapak_ciz`, sol üst varyant) gerçek 001 verisiyle; zemin mürekkep ve seyrek yıldız.

    Gerçek kapakta zemin, görevin ayrı bir parçasının sahnesidir (`kapak_parcalari`); kit yalnız düzeni gösterir."""
    from .kapak import H, W, kapak_ciz
    m = marka_yukle()["palet"]
    zemin = Image.new("RGB", (W, H), rgb(m["arka"]))
    d = ImageDraw.Draw(zemin)
    rs = random.Random(7)
    ikincil = np.array(rgb(m["yazi_ikincil"]), float)
    arka = np.array(rgb(m["arka"]), float)
    for _ in range(260):
        x, y, t = rs.uniform(0, W), rs.uniform(0, H), 0.15 + 0.55 * rs.random() ** 2
        d.point((x, y), fill=tuple(int(v) for v in arka + (ikincil - arka) * t))
    tampon = io.BytesIO()
    zemin.save(tampon, "PNG")
    tampon.seek(0)
    return kapak_ciz(tampon, _ornek_gorev(), {}, "sol_ust", 2)


def _daire(img: Image.Image, boy: int) -> tuple[Image.Image, Image.Image]:
    kucuk = img.convert("RGB").resize((boy, boy), Image.LANCZOS)
    maske = Image.new("L", (boy * 4, boy * 4), 0)
    ImageDraw.Draw(maske).ellipse([0, 0, boy * 4 - 1, boy * 4 - 1], fill=255)
    return kucuk, maske.resize((boy, boy), Image.LANCZOS)


def kitap(b: Image.Image, p: Image.Image, fil: Image.Image, kapak: Image.Image) -> Image.Image:
    """Tek sayfa kit özeti (sahibine ve ajanlara referans). Yalnız kitin kendi dosyaları ve gerçek veri."""
    m = marka_yukle()
    gri, beyaz, vurgu = rgb(m["palet"]["yazi_ikincil"]), rgb(m["palet"]["yazi"]), rgb(m["palet"]["vurgu"])
    S = Image.new("RGB", KITAP_BOY, rgb(m["palet"]["arka"]))
    d = ImageDraw.Draw(S)
    yazi._aralikli(d, "DEEP SPACE LOG  ·  BRAND KIT", yazi.font(34, "kalin"), 6, 800, 40, (*beyaz, 255), 0)
    d.line([(680, 96), (920, 96)], fill=vurgu, width=2)
    S.paste(b.convert("RGB").resize((1000, 562), Image.LANCZOS), (40, 130))
    d.text((40, 700), "Banner 2560x1440 · yazı ortadaki 1546x423 güvenli alanda", font=yazi.font(18), fill=gri)
    S.paste(p.convert("RGB").resize((240, 240), Image.LANCZOS), (1100, 130))
    for boy, x in ((98, 1370), (40, 1490)):
        av, maske = _daire(p, boy)
        S.paste(av, (x, 130), maske)
    d.text((1100, 380), "Profil 800x800 · 98 px ve 40 px daire", font=yazi.font(18), fill=gri)
    yama = Image.new("RGB", (190, 190), (46, 52, 66))  # filigran video üstünde orta tonlu bir zeminde
    yama.paste(fil, (20, 20), fil)
    S.paste(yama, (1100, 420))
    d.text((1310, 500), "Filigran 150x150", font=yazi.font(18), fill=gri)
    d.text((1310, 524), "şeffaf PNG", font=yazi.font(18), fill=gri)
    S.paste(kapak.convert("RGB").resize((760, 428), Image.LANCZOS), (40, 750))
    S.paste(kapak.convert("RGB").resize((168, 94), Image.LANCZOS), (820, 750))
    d.text((40, 1190), "Kapak düzeni 1280x720 (G7): görev no + görev adı, gerçek veri satırı, köşe nişanları.",
           font=yazi.font(18), fill=gri)
    d.text((40, 1216), "Zemin görevin ayrı bir parçasının sahnesidir · sağda 168x94", font=yazi.font(18), fill=gri)
    for i, (ad, h) in enumerate(m["palet"].items()):
        x, y = 1100 + (i % 3) * 160, 650 + (i // 3) * 160
        d.rectangle([x, y, x + 130, y + 90], fill=h, outline=(60, 64, 80))
        d.text((x, y + 96), ad, font=yazi.font(16), fill=gri)
        d.text((x, y + 116), h, font=yazi.font(16), fill=gri)
    ton = m.get("filtre", {}).get("secim") or "yok"
    for j, metin in enumerate(["Yazı: Space Mono (OFL)", f"Film tonu: {ton}", "Vurgu: kehribar, yüzey başına tek çizgi",
                               "PROBE-7: halka içinde 7, yalnız arayüzde"]):
        d.text((1100, 990 + j * 34), metin, font=yazi.font(22 if j == 0 else 18, "kalin" if j == 0 else "normal"),
               fill=beyaz if j == 0 else gri)
    for j, metin in enumerate([
            "Görsel dili: PROBE-7'nin kamerası. Karanlık, durgun bir yabancı ufuk ya da yörüngeden görünüm;",
            "tek büyük gerçek gök cismi, bol boşluk. Sahnede insan, araç, sonda, bina yok; ışık fiziği doğru.",
            "Grafik katman kayıt defteri: mürekkep zemin, ince çizgi, gerçek veri. Kapakta seri adı, süre ve",
            "söz veren yazı yok."]):
        d.text((40, 1290 + j * 34), metin, font=yazi.font(20), fill=beyaz)
    return S


def uret(hedef: Path = KOK / "marka", banner_kaynak: Path = KAYNAK_BANNER,
         profil_kaynak: Path = KAYNAK_PROFIL) -> list[Path]:
    hedef = Path(hedef)
    hedef.mkdir(parents=True, exist_ok=True)
    yollar = [hedef / "banner.jpg", hedef / "profil.png", hedef / "filigran.png", hedef / "marka_kitabi.jpg"]
    shutil.copyfile(banner_kaynak, yollar[0])   # kanaldaki onaylı dosya, değiştirilmeden
    shutil.copyfile(profil_kaynak, yollar[1])
    b, p = Image.open(yollar[0]), Image.open(yollar[1])
    fil = filigran(p)
    fil.save(yollar[2])
    kitap(b, p, fil, ornek_kapak()).save(yollar[3], quality=90)
    return yollar
