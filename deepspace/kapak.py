"""Kapak (3 varyant, YouTube "Test & Compare" için) ve kanal görselleri (banner, profil resmi).

Kapak dili (G7, 11 Kasım 2026, bağımsız inceleme önerisi; sahibinin onayı): kayıt defteri. Sol üstte büyük görev
numarası ve görev adı, altta küçük gerçek veri satırı (hedef, gök koordinatı, uzaklık), dört köşede ince nişan
işaretleri. Görsel durağandır ve üç varyant üç ayrı parçanın görselidir (yakınlaştırma değil): Test & Compare
gerçekten farklı sahneleri dener. Görseli olmayan varyant için kod sahnesi çizilmez; kapak üretilmez (G6).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .defter import _font, _kapla
from .ortak import cikti, marka_yukle, rgb, seri
from .renk import marka_filtresi
from .renk import uygula as renk_uygula

W, H = 1280, 720
VARYANTLAR = ["sol_ust", "sol_alt", "orta_ust"]  # başlık bloğunun yeri; her varyant ayrı parçanın görseli


def kapak_yazilari(gorev: dict, ayar: dict, saat: int) -> list[str]:
    """Kapağın büyük yazıları: görev numarası ve görev adı (en çok 3 kelime). Küçük veri satırı sayılmaz."""
    ad = (gorev.get("ad") or seri(gorev, ayar)["kapak_yazi"]).upper()
    return [f"{int(gorev.get('no', 0)):03d}", ad]


def veri_satiri(gorev: dict) -> str:
    parcalar = [gorev.get("hedef", ""), gorev.get("koordinat", ""), gorev.get("uzaklik", "").upper()]
    return "  ·  ".join(p for p in parcalar if p)


def kapak_parcalari(gorev: dict) -> list[int]:
    """Üç varyantın parça sırası (0'dan). gorev.toml `kapak_parcalari` (1'den) ya da hedef + son + ilk parça."""
    n = len(gorev["parca"])
    if gorev.get("kapak_parcalari"):
        return [int(i) - 1 for i in gorev["kapak_parcalari"]][:3]
    hedef = next((i for i, p in enumerate(gorev["parca"]) if p["ad"].startswith(gorev["hedef"])), 0)
    return list(dict.fromkeys([hedef, n - 1, 0]))[:3]


def _nisan(d: ImageDraw.ImageDraw, renk, kalin: int):
    m, L = 34, 30
    for x, y, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=renk, width=kalin)
        d.line([(x, y), (x, y + sy * L)], fill=renk, width=kalin)


def kapak_ciz(gorsel: Path, gorev: dict, ayar: dict, duzen: str, saat: int) -> Image.Image:
    palet = marka_yukle()["palet"]
    vurgu, ikincil, yazi = rgb(palet["vurgu"]), rgb(palet["yazi_ikincil"]), (244, 241, 234)
    img = _kapla(Image.open(gorsel).convert("RGB"), W, H)
    f = marka_filtresi()
    if f:
        img = Image.fromarray(renk_uygula(np.asarray(img), f))
    a = np.asarray(img, np.float32) / 255
    # yazı bloğunun arkası hafifçe koyulur (okunurluk), görüntü bükülmez
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cy = 0.24 * H if duzen != "sol_alt" else 0.74 * H
    cx = 0.5 * W if duzen == "orta_ust" else 0.3 * W
    golge = np.exp(-(((xx - cx) / (0.42 * W)) ** 2 + ((yy - cy) / (0.26 * H)) ** 2)) * 0.45
    a *= (1 - golge)[..., None]
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    kat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    no, ad = kapak_yazilari(gorev, ayar, saat)
    f_no, f_ad, f_veri, f_marka = _font(88, True), _font(74, True), _font(19), _font(18, True)
    ara = 10  # harf aralığı (ince, geniş başlık)

    def aralikli(xy, metin, font, renk, hiza="sol"):
        gen = sum(d.textlength(c, font=font) for c in metin) + ara * (len(metin) - 1)
        x, y = xy
        if hiza == "orta":
            x -= gen / 2
        for c in metin:
            d.text((x, y), c, font=font, fill=renk, stroke_width=2, stroke_fill=(5, 7, 15, 160))
            x += d.textlength(c, font=font) + ara
        return gen

    y0 = 84 if duzen != "sol_alt" else H - 300
    if duzen == "orta_ust":
        aralikli((W / 2, y0), no, f_no, (*vurgu, 255), "orta")
        aralikli((W / 2, y0 + 108), ad, f_ad, (*yazi, 255), "orta")
        d.line([(W / 2 - 120, y0 + 222), (W / 2 + 120, y0 + 222)], fill=(*vurgu, 220), width=2)
    else:
        x0 = 86
        aralikli((x0, y0), no, f_no, (*vurgu, 255))
        aralikli((x0, y0 + 108), ad, f_ad, (*yazi, 255))
        d.line([(x0, y0 + 222), (x0 + 240, y0 + 222)], fill=(*vurgu, 220), width=2)
    veri = veri_satiri(gorev)
    vy = H - 76 if duzen != "sol_alt" else 74
    d.text((86, vy), veri, font=f_veri, fill=(*ikincil, 235), stroke_width=2, stroke_fill=(5, 7, 15, 170))
    marka = "DEEP SPACE LOG  ·  PROBE-7"
    d.text((W - 86 - d.textlength(marka, font=f_marka), H - 76 if duzen == "sol_alt" else 74), marka,
           font=f_marka, fill=(*vurgu, 230), stroke_width=2, stroke_fill=(5, 7, 15, 170))
    _nisan(d, (*vurgu, 200), 2)
    img.alpha_composite(kat)
    return img.convert("RGB")


def kapaklar(gorev: dict, ayar: dict) -> list[Path]:
    import json
    from .video import parca_gorseli
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    saat = round(bolumler["toplam_sn"] / 3600)
    yollar = []
    for k, (i, duzen) in enumerate(zip(kapak_parcalari(gorev), VARYANTLAR)):
        gorsel = parca_gorseli(gorev, i)[0]
        if gorsel is None:
            raise FileNotFoundError(f"kapak {k + 1}: parça {i + 1} görseli yok; kapak üretilmedi (G6/G7)")
        yol = out / f"kapak_{k + 1}.jpg"
        kapak_ciz(gorsel, gorev, ayar, duzen, saat).save(yol, quality=90)
        yollar.append(yol)
    return yollar


def kanal_gorselleri(ayar: dict) -> list[Path]:
    """Banner, profil, filigran ve marka kitabı: onaylı kitin kaynak görselinden (marka_kiti, G16)."""
    from . import marka_kiti
    return marka_kiti.uret()
