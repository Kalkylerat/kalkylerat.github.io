"""Tek parçalık referans video: bir görselin sahnesi + bir ses dosyası (sahibine örnek göstermek için).

Kurallar (SOZLESME.md G14): sessiz döngü `cikti/ornek/ara/` içinde kalır; teslim klasöründe yalnız sesli video olur
ve ses gerçekten duyuluyor mu ölçülmeden "hazır" denmez. Ses G3 gibi: iki geçişli loudnorm -16 LUFS, tepe -1.5 dBTP.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import kapilar, video
from .ortak import calistir, cikti, ffprobe_sure
from .sahne import dongu_kodla


def _loudnorm(ses: Path, sure: float, basla: float = 0.0, giris: float = 3.0, cikis: float = 5.0) -> str:
    """İki geçişli loudnorm filtresi; ölçüm sesin [basla, basla + sure] dilimindendir. giris/cikis: fade süreleri."""
    aralik = (["-ss", f"{basla:.3f}"] if basla else []) + ["-t", f"{sure:.3f}"]
    olc = calistir(["ffmpeg", "-hide_banner", "-nostats", *aralik, "-i", str(ses), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", olc).group(0))
    return (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
            f"linear=true,aresample=48000,afade=t=in:d={giris:g},"
            f"afade=t=out:st={max(0.0, sure - cikis):.2f}:d={cikis:g}")


def _defter(gorev: dict, ayar: dict, parca: int, ses: Path, W: int, H: int) -> Path:
    """Seyir Defteri modu: kareler doğrudan sesle birlikte kodlanır (ara dosya yok)."""
    from . import defter
    from .renk import marka_filtresi
    ana, _ = video.parca_gorseli(gorev, parca - 1)
    if not ana:
        raise FileNotFoundError(f"parça {parca:02d}: görsel yok")
    fps = int(ayar["video"]["fps"])
    sure = ffprobe_sure(ses)
    bilgi = video.parca_bilgisi(gorev, parca - 1)
    sahne = defter.SeyirDefteri(ana, defter.katmanlari_oku(ana), W, H, fps, sure, defter.ses_ozeti(ses, fps), bilgi,
                                tohum=int(gorev["tohum"]) * 100 + parca, ton=marka_filtresi())
    klasor = cikti(gorev) / "ornek"
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / f"{Path(ses).stem.lower().replace(' ', '_')}_{parca:02d}_defter_{H}p.mp4"
    return defter.kodla(sahne, ses, hedef, _loudnorm(ses, sure))


def ornek(gorev: dict, ayar: dict, parca: int, ses: Path, W: int = 1920, H: int = 1080, mod: str = "defter") -> Path:
    if mod == "defter":
        hedef = _defter(gorev, ayar, parca, ses, W, H)
        duyuluyor, ayrinti = kapilar.ses_duyuluyor(hedef)
        if not duyuluyor:
            raise RuntimeError(f"G14: {hedef.name} içinde ses duyulmuyor ({ayrinti})")
        return hedef
    v = ayar["video"]
    L, fps = float(v["dongu_sn"]), int(v["fps"])
    klasor = cikti(gorev) / "ornek"
    ara = klasor / "ara"
    ara.mkdir(parents=True, exist_ok=True)
    dongu = ara / f"dongu_{parca:02d}_{H}p.mp4"
    dongu_kodla(video.sahne_nesnesi(gorev, parca - 1, W, H, L), dongu, fps=fps, crf=18, lut=video.marka_lut(gorev))
    sure = ffprobe_sure(ses)
    hedef = klasor / f"{Path(ses).stem.lower().replace(' ', '_')}_{parca:02d}_{H}p.mp4"
    calistir(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(dongu), "-i", str(ses),
              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", _loudnorm(ses, sure), "-c:a", "aac",
              "-b:a", "320k", "-t", f"{sure:.3f}", "-movflags", "+faststart", str(hedef)])
    duyuluyor, ayrinti = kapilar.ses_duyuluyor(hedef)
    if not duyuluyor:
        raise RuntimeError(f"G14: {hedef.name} içinde ses duyulmuyor ({ayrinti})")
    return hedef
