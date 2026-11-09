"""Marka renk derecelendirmesi (sinema LUT'u): bütün görsellere aynı film tonu (SOZLESME.md G6, marka.toml [filtre]).

Filmlerdeki "color grade" adımlarının sadeleştirilmiş hali, hepsi yalnızca renge bağlı (piksel komşuluğu yok), bu
yüzden tek bir 3D LUT'a (.cube) birebir sığar:
  1. pozlama ve filmik S eğrisi (kontrast, yumuşak parlak alan),
  2. siyah kaldırma (lift) ve parlak alan tavanı,
  3. renk tonuna göre doygunluk: sıcaklar korunur, mavi/yeşil/mor bastırılır,
  4. split toning: alt-orta tonlar bir renge, üst tonlar başka bir renge çekilir (saf siyah ve beyaz korunur),
  5. son ton karışımı (gücü `guc`).
Videoda ffmpeg lut3d ile, kapak ve banner'da aynı hesap numpy ile uygulanır; ikisi aynı görünür.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .ortak import marka_yukle, rgb

# Sahibine sunulan film tonları (9 Kasım 2026). Seçilen marka.toml [filtre]'ye yazılır.
SECENEKLER = {
    # 9 Kasım 2026: sahibi "çok yoğun, gerçeklikten kopmayalım" dedi; hepsi hafif (görselin kendi renkleri korunur).
    "ember_film": {"aciklama": "sıcak kırmızı-turuncu hava, gölgeler hafif kızıl, parlak alanlar kehribar",
                   "pozlama": 0.0, "kontrast": 0.25, "lift": "#140405", "lift_miktar": 0.012, "tavan": 0.99,
                   "golge": "#7a1410", "parlak": "#ffb067", "ton_miktar": 0.18, "doygunluk": 1.0,
                   "soguk_bastir": 0.35, "guc": 0.5},
    "col_epigi": {"aciklama": "hafif okra ve pas, renkler biraz soluk, epik çöl filmi hissi",
                  "pozlama": 0.0, "kontrast": 0.2, "lift": "#2a160e", "lift_miktar": 0.03, "tavan": 0.97,
                  "golge": "#5a2a18", "parlak": "#f2c08a", "ton_miktar": 0.18, "doygunluk": 0.8,
                  "soguk_bastir": 0.4, "guc": 0.5},
    "turuncu_sis": {"aciklama": "belirgin ama ölçülü turuncu pus, derin siyahlar",
                    "pozlama": 0.0, "kontrast": 0.3, "lift": "#0a0302", "lift_miktar": 0.01, "tavan": 0.99,
                    "golge": "#6e1a06", "parlak": "#ff9a3c", "ton_miktar": 0.22, "doygunluk": 1.05,
                    "soguk_bastir": 0.45, "guc": 0.5},
    "kizil_kodak": {"aciklama": "film negatifi gibi doğal; en hafif sıcaklık, renkler neredeyse olduğu gibi",
                    "pozlama": 0.0, "kontrast": 0.2, "lift": "#1a0608", "lift_miktar": 0.01, "tavan": 0.985,
                    "golge": "#5c1018", "parlak": "#ffc88e", "ton_miktar": 0.14, "doygunluk": 0.98,
                    "soguk_bastir": 0.25, "guc": 0.45},
}


def _renk(h: str) -> np.ndarray:
    return np.array(rgb(h), np.float32) / 255


def uygula(img: np.ndarray, ton: dict) -> np.ndarray:
    """img: HxWx3 uint8 ya da 0..1 float. Aynı biçimde döner."""
    tam = img.dtype == np.uint8
    x0 = img.astype(np.float32) / 255 if tam else img.astype(np.float32)
    x = np.clip(x0 * (2.0 ** ton.get("pozlama", 0.0)), 0, 1)
    # 1. filmik S eğrisi
    s = x * x * (3 - 2 * x)
    x = x * (1 - ton["kontrast"]) + s * ton["kontrast"]
    # 2. lift (renkli siyah) ve tavan
    lc = _renk(ton["lift"])
    L = ton["lift_miktar"] * lc / max(float(lc.max()), 1e-3)
    x = L + x * (ton["tavan"] - L)
    x = np.clip(x, 0, 1)
    # 3. renk tonuna göre doygunluk: sıcak tonlar (kırmızı-turuncu-sarı) korunur, mavi/yeşil/mor bastırılır
    mx, mn = x.max(axis=-1), x.min(axis=-1)
    fark = mx - mn + 1e-6
    r, gg, b = x[..., 0], x[..., 1], x[..., 2]
    hue = np.where(mx == r, ((gg - b) / fark) % 6, np.where(mx == gg, (b - r) / fark + 2, (r - gg) / fark + 4)) * 60
    sicaklik = np.clip(1 - np.minimum(np.abs(hue - 30), np.abs(hue - 390)) / 60, 0, 1)  # 330..90 derece sıcak
    lum = (r * 0.2126 + gg * 0.7152 + b * 0.0722)[..., None]
    doy = ton["doygunluk"] * (1 - ton["soguk_bastir"] * (1 - sicaklik))[..., None]
    x = np.clip(lum + (x - lum) * doy, 0, 1)
    # 4. split toning: gölge rengi alt-orta tonlarda, parlak rengi üst tonlarda; saf siyah ve beyaz korunur
    g, p = _renk(ton["golge"]), _renk(ton["parlak"])
    w_g = 6.75 * lum * (1 - lum) ** 2      # en çok lum = 1/3'te
    w_p = 6.75 * lum ** 2 * (1 - lum)      # en çok lum = 2/3'te
    x = x + ton["ton_miktar"] * (w_g * (g - g.mean()) + w_p * (p - p.mean())) * 1.6
    x = np.clip(x, 0, 1)
    out = np.clip(x0 * (1 - ton["guc"]) + np.clip(x, 0, 1) * ton["guc"], 0, 1)
    return (out * 255 + 0.5).astype(np.uint8) if tam else out


def marka_filtresi() -> dict | None:
    f = marka_yukle().get("filtre", {})
    secim = f.get("secim")
    if not secim:
        return None
    ton = dict(SECENEKLER[secim])
    ton.update({k: v for k, v in f.items() if k != "secim"})
    return ton


def cube_yaz(hedef: Path, ton: dict, boy: int = 33) -> Path:
    """ffmpeg lut3d için .cube dosyası (R en hızlı değişen eksen)."""
    g = np.linspace(0, 1, boy, dtype=np.float32)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")
    izgara = np.stack([r, gg, b], axis=-1).reshape(-1, 1, 3)
    cikis = uygula(izgara, ton).reshape(-1, 3)
    satir = [f"LUT_3D_SIZE {boy}"] + [f"{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}" for c in cikis]
    hedef.write_text("\n".join(satir) + "\n", encoding="ascii")
    return hedef
