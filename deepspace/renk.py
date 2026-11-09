"""Marka renk filtresi: bütün görsellere aynı kırmızı -> turuncu tonu verir (SOZLESME.md G6, marka.toml [filtre]).

Yöntem "gradient map": her pikselin parlaklığı, koyudan açığa sıralı renk duraklarına eşlenir ve orijinal renkle
`guc` oranında karıştırılır. Videoda filtre ffmpeg'in lut3d süzgeciyle uygulanır (hızlı); kapak ve banner gibi
durağan görsellerde aynı hesap numpy ile yapılır, böylece ikisi birebir aynı görünür.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .ortak import marka_yukle, rgb

# Sahibine sunulan seçenekler (9 Kasım 2026). Seçilen marka.toml [filtre]'ye yazılır.
SECENEKLER = {
    "ember": {"duraklar": ["#050101", "#2a0505", "#9c1f17", "#f0642a", "#ffd2a0"], "guc": 0.85, "kontrast": 1.10},
    "mars_dusk": {"duraklar": ["#100706", "#3e1710", "#94402a", "#d9874f", "#f2d3b2"], "guc": 0.70, "kontrast": 1.0},
    "solar_flare": {"duraklar": ["#000000", "#4a0800", "#d83c16", "#ffa01e", "#fff1cc"], "guc": 0.90, "kontrast": 1.25},
    "crimson_night": {"duraklar": ["#030001", "#300405", "#82111a", "#df561f", "#ffb36c"], "guc": 0.90, "kontrast": 1.15},
    "amber_haze": {"duraklar": ["#0c0603", "#381909", "#974812", "#ee912c", "#ffe3b3"], "guc": 0.75, "kontrast": 0.95},
}


def uygula(img: np.ndarray, duraklar: list[str], guc: float, kontrast: float = 1.0) -> np.ndarray:
    """img: HxWx3 uint8 ya da 0..1 float. Aynı biçimde döner."""
    tam = img.dtype == np.uint8
    x = img.astype(np.float32) / 255 if tam else img.astype(np.float32)
    lum = x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722
    lum = np.clip((lum - 0.5) * kontrast + 0.5, 0, 1)
    renkler = np.array([rgb(d) for d in duraklar], np.float32) / 255
    konum = np.linspace(0, 1, len(renkler))
    harita = np.stack([np.interp(lum, konum, renkler[:, k]) for k in range(3)], axis=-1)
    out = x * (1 - guc) + harita * guc
    return (np.clip(out, 0, 1) * 255).astype(np.uint8) if tam else np.clip(out, 0, 1)


def marka_filtresi() -> dict | None:
    f = marka_yukle().get("filtre")
    return f if f and f.get("duraklar") else None


def cube_yaz(hedef: Path, filtre: dict, boy: int = 33) -> Path:
    """ffmpeg lut3d için .cube dosyası (R en hızlı değişen eksen)."""
    g = np.linspace(0, 1, boy, dtype=np.float32)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")
    izgara = np.stack([r, gg, b], axis=-1).reshape(-1, 1, 3)
    cikis = uygula(izgara, filtre["duraklar"], filtre["guc"], filtre.get("kontrast", 1.0)).reshape(-1, 3)
    satir = [f"LUT_3D_SIZE {boy}"] + [f"{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}" for c in cikis]
    hedef.write_text("\n".join(satir) + "\n", encoding="ascii")
    return hedef
