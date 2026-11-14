"""Ses istasyonu: parçaları ölçer, seviyeyi eşitler, çapraz geçişle birleştirir, bölüm zamanlarını çıkarır.

Ücretli çağrı yok: yalnızca ffmpeg. Çalışma müziği olduğu için hedef -16 LUFS (YouTube'un -14'ünden biraz kısık).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .ortak import calistir, cikti, ffprobe_sure

_LUFS = re.compile(r"I:\s+(-?[\d.]+) LUFS")
_TEPE = re.compile(r"Peak:\s+(-?[\d.]+|-inf) dBFS")
_SESSIZ_BAS = re.compile(r"silence_start: (-?[\d.]+)")
_SESSIZ_SON = re.compile(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)")


def olc(dosya: Path, sessizlik_db: float = -60, sessizlik_sn: float = 4) -> dict:
    """Bir ses dosyasının süresi, entegre ses yüksekliği (LUFS), gerçek tepe (dBTP) ve sessiz bölgeleri."""
    sure = ffprobe_sure(dosya)
    s = calistir(["ffmpeg", "-hide_banner", "-nostats", "-i", str(dosya), "-af",
                  f"silencedetect=n={sessizlik_db}dB:d={sessizlik_sn},ebur128=peak=true", "-f", "null", "-"])
    log = s.stderr
    ozet = log[log.rfind("Summary:"):]
    lufs = float(_LUFS.search(ozet).group(1)) if _LUFS.search(ozet) else None
    tepe_m = _TEPE.search(ozet)
    tepe = None if not tepe_m or tepe_m.group(1) == "-inf" else float(tepe_m.group(1))
    sessiz = [(float(son) - float(uz), float(son)) for son, uz in _SESSIZ_SON.findall(log)]
    acik = _SESSIZ_BAS.findall(log)
    if len(acik) > len(sessiz):  # dosya sessizlikle bitiyor
        sessiz.append((float(acik[-1]), sure))
    return {"dosya": Path(dosya).name, "sure": round(sure, 3), "lufs": lufs, "tepe_dbtp": tepe, "sessiz": sessiz}


def zaman_cizelgesi(sureler: list[float], capraz: float) -> list[float]:
    """Parça i'nin başlangıcı: önceki sürelerin toplamı eksi i kez çapraz geçiş."""
    basla, t = [], 0.0
    for i, s in enumerate(sureler):
        basla.append(round(t, 3))
        t += s - capraz
    return basla


def toplam_sure(sureler: list[float], capraz: float) -> float:
    return sum(sureler) - capraz * (len(sureler) - 1)


SES_UZANTI = (".mp3", ".wav", ".m4a", ".flac")


def ses_dosyalari(gorev: dict) -> list[Path]:
    """Parça dosyaları. SUNO.md'deki ad birebir yoksa aynı adın başka ses uzantısı da kabul edilir
    (Suno'dan WAV indirilirse yeniden adlandırma gerekmez). Hiçbiri yoksa beklenen ad döner (eksik raporu için)."""
    klasor = Path(gorev["klasor"]) / "ses"
    sonuc = []
    for p in gorev["parca"]:
        tam = klasor / p["dosya"]
        diger = (tam.with_suffix(u) for u in SES_UZANTI if u != tam.suffix.lower())
        sonuc.append(tam if tam.exists() else next((d for d in diger if d.exists()), tam))
    return sonuc


def ozetler(gorev: dict) -> list[str]:
    """Var olan parça dosyalarının sha256 özetleri (özgünlük ve Shorts kaydı için). Eksik dosya listede yer almaz."""
    return [hashlib.sha256(d.read_bytes()).hexdigest() for d in ses_dosyalari(gorev) if d.exists()]


def ham_birlesim_argumanlari(dosyalar: list[Path], capraz: float) -> list[str]:
    """G3: ffmpeg girdi ve filtre argümanları. Yalnız biçim birleştirme (48 kHz stereo) ve eşit güç (qsin) çapraz
    geçiş; ses kazancı, loudnorm, sıkıştırma ya da kırpma yoktur."""
    girdi, filtre = [], []
    for i, d in enumerate(dosyalar):
        girdi += ["-i", str(d)]
        filtre.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[g{i}]")
    son = "g0"
    for i in range(1, len(dosyalar)):
        filtre.append(f"[{son}][g{i}]acrossfade=d={capraz:g}:c1=qsin:c2=qsin[x{i}]")
        son = f"x{i}"
    return [*girdi, "-filter_complex", ";".join(filtre), "-map", f"[{son}]"]


def birlestir(gorev: dict, ayar: dict) -> dict:
    """G3 (14 Kasım 2026): parçaları Suno'dan geldiği gibi, kesmeden ve eşitlemeden, eşit güç eğrili çapraz geçişle
    birleştirir; loudnorm ya da başka master işlemi yoktur. Çıktı: cikti/ses.m4a ve cikti/bolumler.json."""
    a = ayar["ses"]
    dosyalar = ses_dosyalari(gorev)
    eksik = [d.name for d in dosyalar if not d.exists()]
    if eksik:
        raise FileNotFoundError(f"ses klasöründe eksik dosya: {', '.join(eksik)}")
    olcumler = [olc(d, a["sessizlik_db"], a["sessizlik_max_sn"]) for d in dosyalar]
    capraz = float(a["capraz_gecis_sn"])
    hedef_dosya = cikti(gorev) / "ses.m4a"
    calistir(["ffmpeg", "-y", "-hide_banner", "-nostats", "-threads", "1",
              *ham_birlesim_argumanlari(dosyalar, capraz), "-c:a", "aac", "-b:a", "320k", str(hedef_dosya)])

    sureler = [o["sure"] for o in olcumler]
    basla = zaman_cizelgesi(sureler, capraz)
    bolumler = {
        "capraz_gecis_sn": capraz,
        "toplam_sn": round(toplam_sure(sureler, capraz), 3),
        "parcalar": [{"no": i + 1, "ad": p["ad"], "basla": b, "sure": s, "olcum": o}
                     for i, (p, b, s, o) in enumerate(zip(gorev["parca"], basla, sureler, olcumler))],
        "master": olc(hedef_dosya, a["sessizlik_db"], a["sessizlik_max_sn"]),
    }
    (cikti(gorev) / "bolumler.json").write_text(json.dumps(bolumler, indent=2, ensure_ascii=False), encoding="utf-8")
    return bolumler
