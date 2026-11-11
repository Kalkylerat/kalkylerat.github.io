"""Kapak (3 varyant, YouTube "Test & Compare" için) ve kanal görselleri (banner, profil resmi)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import yazi
from .marka_kiti import probe_ekle
from .ortak import cikti, seri
from .sahne import Sahne
from .renk import marka_filtresi
from .renk import uygula as renk_uygula
from .tablo import Tablo

VARYANTLAR = [  # (yedek sahnede gezegen yerleşimi, marka şablonu düzeni, PROBE-7 konumu (W, H oranı))
    ("sag", "ust", (0.84, 0.40)),
    ("sol", "alt", (0.84, 0.22)),
    ("ust", "etiket", (0.16, 0.42)),
]


def kapak_yazilari(gorev: dict, ayar: dict, saat: int) -> list[str]:
    return [seri(gorev, ayar)["kapak_yazi"], f"{saat}H"]


def kapaklar(gorev: dict, ayar: dict) -> list[Path]:
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    saat = round(bolumler["toplam_sn"] / 3600)
    hedef_i = next((i for i, p in enumerate(gorev["parca"]) if p["ad"] == gorev["hedef"]), 0)
    parca = gorev["parca"][hedef_i]
    ust, alt = kapak_yazilari(gorev, ayar, saat)
    W, H = 1280, 720
    yollar = []
    for k, (gyer, duzen, (px, py)) in enumerate(VARYANTLAR):
        from .video import parca_gorseli
        ana, on = parca_gorseli(gorev, hedef_i)
        if ana:  # marka görseli varsa kapak ondan çıkar; varyantlar farklı an ve kadraj
            s = Tablo(ana, W, H, 60.0, tohum=k + 1, on_plan=on, yildiz=0, toz=0, nefes=0.03 * (k + 1))
            img = Image.fromarray(s.kare(10.0 * k)).convert("RGBA")
        else:
            s = Sahne(parca, int(gorev["tohum"]) * 100 + hedef_i, W, H, 40.0, yerlesim=gyer, olcek=1.35, probe=False)
            img = Image.fromarray(s.kare(7.0)).convert("RGBA")
        f = marka_filtresi()
        if f:
            img = Image.fromarray(renk_uygula(np.asarray(img.convert("RGB")), f)).convert("RGBA")
        img.alpha_composite(yazi.kapak_katmani(W, H, ust, alt, duzen))
        probe_ekle(img, W * px, H * py, 54)  # G7: PROBE-7 görünür, gökte küçük
        yol = out / f"kapak_{k + 1}.jpg"
        img.convert("RGB").save(yol, quality=90)
        yollar.append(yol)
    return yollar


def kanal_gorselleri(ayar: dict) -> list[Path]:
    """Banner, profil, filigran ve marka kitabı: onaylı kitin kaynak görselinden (marka_kiti, G16)."""
    from . import marka_kiti
    return marka_kiti.uret()
