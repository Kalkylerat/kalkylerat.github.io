"""Shorts departmanı (G12): müzik analizi, kurgucu planının kontrolü, dikey üretim ve metin.

Akış: `analiz` her parçanın saniyelik enerji eğrisini ve önerilen anı `cikti/shorts_analiz.json`'a yazar; kurgucu ajan
bu analize ve görsellere bakarak `shorts_plan.json`'u yazar; plan kod kapısından geçmeden Short üretilmez.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from .kapilar import SES_ESIGI_DB
from .ortak import cikti

SR = 8000  # enerji eğrisi için yeterli (yalnız seviye ölçülür)


def enerji_egrisi(ses: Path, basla: float, sure: float) -> np.ndarray:
    """Sesin [basla, basla + sure) aralığında saniye başına RMS seviyesi (dBFS)."""
    ham = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{basla:.3f}", "-t", f"{sure:.3f}", "-i", str(ses),
                          "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(ham, np.float32)
    n = int(round(sure))
    x = np.pad(x, (0, max(0, n * SR - len(x))))[:n * SR].reshape(n, SR).astype(np.float64)
    return 20 * np.log10(np.sqrt((x * x).mean(axis=1)) + 1e-9)


def en_iyi_aralik(egri: np.ndarray, uzunluk: int, kenar: int = 12) -> int:
    """Ortalama enerjisi en yüksek, içinde sessiz (< G14 eşiği) saniye olmayan pencerenin başlangıç saniyesi.

    Parçanın ilk ve son `kenar` saniyesi (fade ve çapraz geçiş) dışarıda kalır. Uygun pencere yoksa -1."""
    e = np.asarray(egri, np.float64)
    son = len(e) - kenar - uzunluk  # son geçerli başlangıç
    if uzunluk <= 0 or son < kenar:
        return -1
    toplam = np.concatenate([[0.0], np.cumsum(e)])
    sessiz = np.concatenate([[0], np.cumsum(e < SES_ESIGI_DB)])
    bas = np.arange(kenar, son + 1)
    ort = (toplam[bas + uzunluk] - toplam[bas]) / uzunluk
    ort[(sessiz[bas + uzunluk] - sessiz[bas]) > 0] = -np.inf
    if not np.isfinite(ort).any():
        return -1
    return int(bas[np.argmax(ort)])


def analiz(gorev: dict, ayar: dict) -> Path:
    """Her parçanın enerji eğrisi ve önerilen Short anı (mutlak saniye, master zaman çizelgesinde)."""
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    ses = out / "ses.m4a"
    uzunluk = int(ayar["shorts"]["sure_sn"])
    sonuc = []
    for p in bolumler["parcalar"]:
        egri = enerji_egrisi(ses, p["basla"], p["sure"])
        bas = en_iyi_aralik(egri, uzunluk)
        sonuc.append({"parca": p["no"], "ad": p["ad"], "basla": p["basla"], "sure": p["sure"],
                      "egri": [round(float(v), 1) for v in egri],
                      "oneri_basla": round(p["basla"] + bas, 2) if bas >= 0 else None})
    yol = out / "shorts_analiz.json"
    yol.write_text(json.dumps(sonuc, ensure_ascii=False) + "\n", encoding="utf-8")
    return yol
