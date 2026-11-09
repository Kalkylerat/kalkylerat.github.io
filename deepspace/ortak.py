"""Ortak yardımcılar: ayar ve görev okuma, süre biçimi, ffmpeg çağrısı."""
from __future__ import annotations

import copy
import json
import subprocess
import tomllib
from pathlib import Path

KOK = Path(__file__).resolve().parent
AYAR_DOSYASI = KOK / "ayar.toml"
KAYIT_DOSYASI = KOK / "kayit.json"
MARKA_DOSYASI = KOK / "marka.toml"


def ayar_yukle() -> dict:
    return tomllib.loads(AYAR_DOSYASI.read_text(encoding="utf-8"))


def marka_yukle() -> dict:
    return tomllib.loads(MARKA_DOSYASI.read_text(encoding="utf-8"))


def rgb(hexs: str) -> tuple[int, int, int]:
    h = hexs.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _birlestir(taban: dict, ust: dict) -> dict:
    for k, v in ust.items():
        if isinstance(v, dict) and isinstance(taban.get(k), dict):
            _birlestir(taban[k], v)
        else:
            taban[k] = v
    return taban


def gorev_yukle(klasor: Path) -> tuple[dict, dict]:
    """(gorev, ayar) döndürür; ayar, görevin [ayar] tablosuyla ezilmiş kanal ayarıdır."""
    klasor = Path(klasor)
    gorev = tomllib.loads((klasor / "gorev.toml").read_text(encoding="utf-8"))
    ayar = _birlestir(copy.deepcopy(ayar_yukle()), gorev.get("ayar", {}))
    gorev["klasor"] = klasor
    return gorev, ayar


def seri(gorev: dict, ayar: dict) -> dict:
    return ayar["seri"][gorev["seri"]]


def cikti(gorev: dict) -> Path:
    yol = Path(gorev["klasor"]) / "cikti"
    yol.mkdir(exist_ok=True)
    return yol


def kayit_yukle() -> dict:
    if KAYIT_DOSYASI.exists():
        return json.loads(KAYIT_DOSYASI.read_text(encoding="utf-8"))
    return {"gorevler": []}


def zaman(sn: float) -> str:
    """YouTube bölüm biçimi: 0:00, 7:52, 1:03:10."""
    sn = int(round(sn))
    s, d, kalan = sn // 3600, (sn % 3600) // 60, sn % 60
    return f"{s}:{d:02d}:{kalan:02d}" if s else f"{d}:{kalan:02d}"


def sure_oku(metin: str) -> float:
    """'7:30' -> 450."""
    parca = [float(p) for p in str(metin).split(":")]
    sn = 0.0
    for p in parca:
        sn = sn * 60 + p
    return sn


def calistir(komut: list[str], **kw) -> subprocess.CompletedProcess:
    sonuc = subprocess.run(komut, capture_output=True, text=True, **kw)
    if sonuc.returncode != 0:
        raise RuntimeError(f"komut başarısız ({sonuc.returncode}): {' '.join(komut[:6])} ...\n{sonuc.stderr[-2000:]}")
    return sonuc


def ffprobe_sure(dosya: Path) -> float:
    s = calistir(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dosya)])
    return float(s.stdout.strip())
