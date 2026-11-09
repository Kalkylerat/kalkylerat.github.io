"""Marka renk derecelendirmesi (sinema LUT'u): bütün görsellere aynı film tonu (SOZLESME.md G6, marka.toml [filtre]).

Filmlerdeki "color grade" adımlarının sadeleştirilmiş hali, hepsi yalnızca renge bağlı (piksel komşuluğu yok), bu
yüzden tek bir 3D LUT'a (.cube) birebir sığar:
  0. beyaz dengesi (renk sıcaklığı kayması),
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
    # 9 Kasım 2026: kırmızı-turuncu tonlar beğenilmedi, sahibi "daha sarımsı" istedi. Yoğunluk orta (guc ~0.6).
    "altin_saat": {"aciklama": "gün batımı ışığı: parlak alanlar altın sarısı, gölgeler sıcak kahve",
                   "pozlama": 0.02, "kontrast": 0.3, "lift": "#1a1206", "lift_miktar": 0.02, "tavan": 0.99,
                   "golge": "#5a3a14", "parlak": "#ffd27a", "ton_miktar": 0.28, "doygunluk": 1.0,
                   "soguk_bastir": 0.45, "sicak_merkez": 45, "beyaz_denge": (1.04, 1.0, 0.80), "guc": 0.75},
    "bal_kehribar": {"aciklama": "koyu bal ve kehribar; daha doygun, sıcak ve yoğun sarı",
                     "pozlama": 0.0, "kontrast": 0.35, "lift": "#140c04", "lift_miktar": 0.015, "tavan": 0.99,
                     "golge": "#4a2a0a", "parlak": "#ffc04d", "ton_miktar": 0.32, "doygunluk": 1.05,
                     "soguk_bastir": 0.55, "sicak_merkez": 40, "beyaz_denge": (1.06, 0.98, 0.72), "guc": 0.75},
    "eski_film": {"aciklama": "70'lerin film rengi: kalkık sıcak siyahlar, soluk sarı ışık, nostaljik",
                  "pozlama": 0.02, "kontrast": 0.2, "lift": "#2a2010", "lift_miktar": 0.05, "tavan": 0.96,
                  "golge": "#4a3818", "parlak": "#f5e1a4", "ton_miktar": 0.25, "doygunluk": 0.8,
                  "soguk_bastir": 0.4, "sicak_merkez": 50, "beyaz_denge": (1.03, 1.0, 0.84), "guc": 0.7},
    "kum_altini": {"aciklama": "kum ve soluk altın; renkler sade, epik ve sakin",
                   "pozlama": 0.0, "kontrast": 0.25, "lift": "#1e1608", "lift_miktar": 0.03, "tavan": 0.97,
                   "golge": "#3d2a14", "parlak": "#f0d28c", "ton_miktar": 0.26, "doygunluk": 0.72,
                   "soguk_bastir": 0.6, "sicak_merkez": 45, "beyaz_denge": (1.03, 0.99, 0.82), "guc": 0.75},
    "sari_camgobegi": {"aciklama": "sinema klasiği: parlak alanlar sarı-altın, gölgelerde hafif camgöbeği; sarı daha çok parlar",
                       "pozlama": 0.0, "kontrast": 0.3, "lift": "#06100f", "lift_miktar": 0.015, "tavan": 0.99,
                       "golge": "#1d4a4a", "parlak": "#ffd36e", "ton_miktar": 0.26, "doygunluk": 1.0,
                       "soguk_bastir": 0.25, "sicak_merkez": 45, "beyaz_denge": (1.03, 1.01, 0.86), "guc": 0.7},
}


def _renk(h: str) -> np.ndarray:
    return np.array(rgb(h), np.float32) / 255


def uygula(img: np.ndarray, ton: dict) -> np.ndarray:
    """img: HxWx3 uint8 ya da 0..1 float. Aynı biçimde döner."""
    tam = img.dtype == np.uint8
    x0 = img.astype(np.float32) / 255 if tam else img.astype(np.float32)
    x = np.clip(x0 * (2.0 ** ton.get("pozlama", 0.0)), 0, 1)
    # 0. beyaz dengesi: bütün görüntüyü sarıya ısıtır (mavi azalır), filmlerdeki sıcak denge gibi
    x = np.clip(x * np.array(ton.get("beyaz_denge", (1.0, 1.0, 1.0)), np.float32), 0, 1)
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
    m = ton.get("sicak_merkez", 30)  # sıcak tonların merkezi (derece): 30 turuncu, 45-50 sarı
    sicaklik = np.clip(1 - np.minimum(np.abs(hue - m), np.abs(hue - m - 360)) / 60, 0, 1)
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
