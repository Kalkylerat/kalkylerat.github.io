"""Kapak (3 varyant, YouTube "Test & Compare" için) ve kanal görselleri (banner, profil resmi)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import yazi
from .ortak import KOK, cikti, seri
from .sahne import Sahne, probe_sprite
from .renk import marka_filtresi
from .renk import uygula as renk_uygula
from .tablo import Tablo

VARYANTLAR = [  # (gezegen yerleşimi, yazı konumu)
    ("sag", "sol"),
    ("sol", "sag"),
    ("ust", "alt"),
]


def kapak_yazilari(gorev: dict, ayar: dict, saat: int) -> list[str]:
    return [seri(gorev, ayar)["kapak_yazi"], f"{saat}H"]


def _probe_ekle(img: Image.Image, x: int, y: int, boy: int):
    rgb, alfa = probe_sprite(boy)
    sprite = Image.fromarray((np.concatenate([rgb, alfa], axis=2) * 255).astype(np.uint8), "RGBA")
    img.alpha_composite(sprite, (x - sprite.width // 2, y - sprite.height // 2))


def kapaklar(gorev: dict, ayar: dict) -> list[Path]:
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    saat = round(bolumler["toplam_sn"] / 3600)
    hedef_i = next((i for i, p in enumerate(gorev["parca"]) if p["ad"] == gorev["hedef"]), 0)
    parca = gorev["parca"][hedef_i]
    ust, alt = kapak_yazilari(gorev, ayar, saat)
    W, H = 1280, 720
    yollar = []
    for k, (gyer, yyer) in enumerate(VARYANTLAR):
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
        if yyer == "alt":
            katman = yazi.katman(W, H, [(ust, 104, "kalin", 1.0), (alt, 56, "kalin", 0.9)], W // 2, H - 250,
                                 hiza="orta")
            _probe_ekle(img, int(W * 0.86), int(H * 0.2), 110)
        else:
            x = 70 if yyer == "sol" else W - 70
            katman = yazi.katman(W, H, [(ust.split()[0], 120, "kalin", 1.0)] +
                                 ([(" ".join(ust.split()[1:]), 120, "kalin", 1.0)] if len(ust.split()) > 1 else []) +
                                 [(alt, 60, "kalin", 0.9)], x, 150, hiza="sol" if yyer == "sol" else "sag")
            _probe_ekle(img, int(W * (0.2 if yyer == "sag" else 0.8)), int(H * 0.82), 110)
        img.alpha_composite(katman)
        yol = out / f"kapak_{k + 1}.jpg"
        img.convert("RGB").save(yol, quality=90)
        yollar.append(yol)
    return yollar


def kanal_gorselleri(ayar: dict) -> list[Path]:
    """Banner (2560x1440, metin güvenli alanda) ve profil resmi (800x800)."""
    klasor = KOK / "marka"
    klasor.mkdir(exist_ok=True)
    ad = ayar["kanal"]["ad"].upper()
    W, H = 2560, 1440
    s = Sahne({"tur": "gaz", "halka": True, "palet": ["#050a18", "#1a2c5c", "#3d6fb8", "#d6c7a1"]}, 7, W, H, 40.0,
              yerlesim="sag", olcek=0.55, probe=False)
    kare = s.kare(3.0)
    f = marka_filtresi()
    if f:
        kare = renk_uygula(kare, f)
    banner = Image.fromarray(kare).convert("RGBA")
    banner.alpha_composite(yazi.katman(W, H, [(ad, 120, "kalin", 1.0),
                                              ("ambient music for deep focus  ·  a new mission every week", 40,
                                               "normal", 0.85)], W // 2, H // 2 - 110, hiza="orta"))
    banner_yol = klasor / "banner.jpg"
    banner.convert("RGB").save(banner_yol, quality=92)

    A = 800
    yy, xx = np.mgrid[0:A, 0:A].astype(np.float32)
    r = np.hypot(xx - A / 2, yy - A / 2) / (A / 2)
    taban = np.array([0.03, 0.05, 0.11], np.float32)
    parilti = np.array([0.18, 0.3, 0.55], np.float32)
    arka = taban + parilti * np.exp(-r * 2.4)[..., None] * 0.9
    avatar = Image.fromarray((np.clip(arka, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    halka = Image.new("RGBA", (A, A), (0, 0, 0, 0))
    ImageDraw.Draw(halka).ellipse([110, 110, A - 110, A - 110], outline=(150, 180, 230, 90), width=6)
    avatar.alpha_composite(halka.filter(ImageFilter.GaussianBlur(2)))
    _probe_ekle(avatar, A // 2, A // 2 + 20, 300)
    avatar_yol = klasor / "profil.png"
    avatar.convert("RGB").save(avatar_yol)
    return [banner_yol, avatar_yol]
