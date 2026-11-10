"""Hareketli klip -> dikişsiz döngü (SOZLESME.md G6).

Yapay zekâ ile üretilmiş kısa bir klip (Kling, Veo, Seedance, Runway; gorsel/NN.mp4) olduğu gibi tekrarlansa sonda
başa atlar. Burada klibin son X saniyesi ilk X saniyesine çapraz geçişle bağlanır: döngünün ilk karesi klibin
X. saniyesi, son karesi de yine X. saniyeye kavuşur. Klip üretirken başlangıç ve bitiş karesine aynı görsel verilirse
geçiş hiç fark edilmez. Aynı adımda çıkış boyutuna ölçeklenir ve marka tonu (LUT) uygulanır.
"""
from __future__ import annotations

from pathlib import Path

from .ortak import calistir, ffprobe_sure, filtre_yolu


def dongu(kaynak: Path, hedef: Path, W: int, H: int, fps: int = 24, lut: Path | None = None,
          capraz: float = 1.5, crf: int = 16) -> Path:
    D = ffprobe_sure(kaynak)
    X = min(capraz, D / 4)
    renk = f",lut3d=file={filtre_yolu(lut)}" if lut else ""
    filtre = (f"[0:v]fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
              f"setsar=1{renk},split[a][b];"
              f"[a]trim=start={X:.4f},setpts=PTS-STARTPTS[a1];"
              f"[b]trim=end={X:.4f},setpts=PTS-STARTPTS[b1];"
              f"[a1][b1]xfade=transition=fade:duration={X:.4f}:offset={D - 2 * X:.4f}[v]")
    calistir(["ffmpeg", "-y", "-loglevel", "error", "-i", str(kaynak), "-filter_complex", filtre, "-map", "[v]",
              "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
              "-g", str(fps * 2), str(hedef)])
    return hedef
