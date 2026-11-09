"""Video istasyonu: sahne döngüleri, uzun video (parça parça kodlanıp birleştirilir) ve Shorts.

Bellek güvenli yöntem: video, her parçanın tek başına aktığı "düz" bölümlerle iki parça arasındaki "geçiş"
bölümlerine ayrılır. Her bölüm ayrı kodlanır (paralel), sonra ffmpeg concat ile kopyalanarak birleşir ve ses eklenir.
Böylece iki saatlik video tek bir dev filtre zinciri gerektirmez.
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import numpy as np

from . import yazi
from .ortak import calistir, cikti, seri
from .sahne import Sahne, dongu_kodla


def _tohum(gorev: dict, i: int) -> int:
    return int(gorev["tohum"]) * 100 + i


def _sahne_isi(args):
    parca, tohum, W, H, L, fps, hedef = args
    dongu_kodla(Sahne(parca, tohum, W, H, L), Path(hedef), fps=fps)
    return hedef


def sahneler(gorev: dict, ayar: dict, yeniden: bool = False) -> list[Path]:
    v = ayar["video"]
    klasor = cikti(gorev) / "sahne"
    klasor.mkdir(exist_ok=True)
    isler, yollar = [], []
    for i, p in enumerate(gorev["parca"]):
        hedef = klasor / f"sahne_{i + 1:02d}.mp4"
        yollar.append(hedef)
        if yeniden or not hedef.exists():
            isler.append((p, _tohum(gorev, i), v["genislik"], v["yukseklik"], float(v["dongu_sn"]), v["fps"],
                          str(hedef)))
    if isler:
        with ProcessPoolExecutor(max_workers=v["is_parcacigi"]) as ex:
            list(ex.map(_sahne_isi, isler))
    return yollar


def bolum_plani(bolumler: dict, fps: int) -> list[dict]:
    """Uzun videonun kodlama bölümleri (kare ızgarasına oturtulmuş). Her bölüm:
    {tur: 'duz'|'gecis', i, bas, kare} — bas saniye, kare kare sayısı."""
    capraz = round(bolumler["capraz_gecis_sn"] * fps)
    basla = [round(p["basla"] * fps) for p in bolumler["parcalar"]]
    toplam = round(bolumler["toplam_sn"] * fps)
    n = len(basla)
    plan = []
    for i in range(n):
        bas = basla[i] + (capraz if i > 0 else 0)
        son = basla[i + 1] if i < n - 1 else toplam
        plan.append({"tur": "duz", "i": i, "bas": bas / fps, "kare": son - bas})
        if i < n - 1:
            plan.append({"tur": "gecis", "i": i, "bas": basla[i + 1] / fps, "kare": capraz})
    return plan


def _kodla_parametre(v: dict) -> list[str]:
    return ["-c:v", "libx264", "-preset", v["preset"], "-crf", str(v["crf"]), "-pix_fmt", "yuv420p",
            "-r", str(v["fps"]), "-g", str(v["fps"] * 2), "-threads", "2", "-an"]


def _bolum_kodla(args) -> str:
    b, sahne_yollari, basla, L, v, etiketler, hedef = args
    fps = v["fps"]
    i = b["i"]
    yerel = (b["bas"] - basla[i]) % L
    komut = ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", f"{yerel:.4f}",
             "-i", str(sahne_yollari[i])]
    if b["tur"] == "gecis":
        sure = b["kare"] / fps
        komut += ["-stream_loop", "-1", "-i", str(sahne_yollari[i + 1]), "-filter_complex",
                  f"[0:v]trim=duration={sure:.4f},setpts=PTS-STARTPTS,fps={fps}[a];"
                  f"[1:v]trim=duration={sure:.4f},setpts=PTS-STARTPTS,fps={fps}[b];"
                  f"[a][b]xfade=transition=fade:duration={sure:.4f}:offset=0[v]", "-map", "[v]"]
    else:
        filtre, son, n_girdi = [f"[0:v]fps={fps},setpts=PTS-STARTPTS[v0]"], "v0", 1
        for png, bas, sure in etiketler:
            komut += ["-loop", "1", "-t", f"{sure:.2f}", "-i", png]
            filtre.append(f"[{n_girdi}:v]format=rgba,fade=t=in:st=0:d=1.2:alpha=1,"
                          f"fade=t=out:st={sure - 1.5:.2f}:d=1.5:alpha=1,setpts=PTS+{bas:.2f}/TB[e{n_girdi}]")
            filtre.append(f"[{son}][e{n_girdi}]overlay=0:0:eof_action=pass[o{n_girdi}]")
            son = f"o{n_girdi}"
            n_girdi += 1
        komut += ["-filter_complex", ";".join(filtre), "-map", f"[{son}]"]
    komut += ["-frames:v", str(b["kare"]), *_kodla_parametre(v), hedef]
    calistir(komut)
    return hedef


def uzun_video(gorev: dict, ayar: dict) -> Path:
    v, ks = ayar["video"], ayar["kanal"]
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    sahne_yollari = sahneler(gorev, ayar)
    L, fps, W, H = float(v["dongu_sn"]), v["fps"], v["genislik"], v["yukseklik"]
    basla = [p["basla"] for p in bolumler["parcalar"]]
    saat = round(bolumler["toplam_sn"] / 3600)

    katman_klasor = out / "katman"
    katman_klasor.mkdir(exist_ok=True)
    kart = katman_klasor / "kart.png"
    yazi.gorev_karti(W, H, gorev, ks["ad"], saat).save(kart)
    etiket_yollari = []
    for i, p in enumerate(gorev["parca"]):
        yol = katman_klasor / f"etiket_{i + 1:02d}.png"
        yazi.parca_etiketi(W, H, i + 1, p).save(yol)
        etiket_yollari.append(str(yol))

    plan = bolum_plani(bolumler, fps)
    bolum_klasor = out / "bolum"
    bolum_klasor.mkdir(exist_ok=True)
    isler = []
    for k, b in enumerate(plan):
        etiketler = []
        if b["tur"] == "duz":
            if b["i"] == 0:
                etiketler = [(str(kart), 1.0, 9.0), (etiket_yollari[0], 11.0, 7.0)]
            else:
                etiketler = [(etiket_yollari[b["i"]], 0.5, 7.0)]
            etiketler = [e for e in etiketler if e[1] + e[2] <= b["kare"] / fps]
        isler.append((b, sahne_yollari, basla, L, v, etiketler, str(bolum_klasor / f"b{k:03d}.mp4")))
    with ThreadPoolExecutor(max_workers=v["is_parcacigi"]) as ex:
        parcalar = list(ex.map(_bolum_kodla, isler))

    liste = bolum_klasor / "liste.txt"
    liste.write_text("".join(f"file '{Path(p).name}'\n" for p in parcalar), encoding="utf-8")
    hedef = out / "video.mp4"
    calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(liste),
              "-i", str(out / "ses.m4a"), "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart",
              str(hedef)])
    return hedef


def shorts_secimi(n_parca: int, adet: int) -> list[int]:
    """Parçaları videoya yayarak seçer (ör. 16 parça, 3 adet -> 4, 8, 12. parçalar; 0 tabanlı 3, 7, 11)."""
    return sorted({min(n_parca - 1, max(0, round(n_parca * (k + 1) / (adet + 1)) - 1)) for k in range(adet)})


def shorts(gorev: dict, ayar: dict) -> list[Path]:
    v, sh, ks = ayar["video"], ayar["shorts"], ayar["kanal"]
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    W, H, fps, sure = 1080, 1920, v["fps"], float(sh["sure_sn"])
    saat = round(bolumler["toplam_sn"] / 3600)
    yollar = []
    for k, i in enumerate(shorts_secimi(len(gorev["parca"]), sh["adet"])):
        p, bp = gorev["parca"][i], bolumler["parcalar"][i]
        ust = yazi.katman(W, H, [(ks["ad"].upper(), 40, "kalin", 0.95),
                                 (f"Mission {gorev['no']:03d}  ·  {gorev['hedef']}", 30, "normal", 0.8)],
                          W // 2, 170, hiza="orta")
        alt = yazi.katman(W, H, [(p["ad"], 52, "kalin", 0.95),
                                 (f"Full {saat}-hour mission on the channel", 30, "normal", 0.8)],
                          W // 2, H - 420, hiza="orta")
        ust.alpha_composite(alt)
        katman = np.asarray(ust, np.float32) / 255
        sessiz = out / f"short_{k + 1}_v.mp4"
        dongu_kodla(Sahne(p, _tohum(gorev, i), W, H, float(v["dongu_sn"]), yerlesim="ust"), sessiz, fps=fps,
                    crf=v["crf"], sure=sure, ust_katman=katman)
        bas = max(0.0, bp["basla"] + bp["sure"] / 2 - sure / 2)
        hedef = out / f"short_{k + 1}.mp4"
        calistir(["ffmpeg", "-y", "-loglevel", "error", "-i", str(sessiz), "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}",
                  "-i", str(out / "ses.m4a"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                  "-af", f"afade=t=in:d=1.5,afade=t=out:st={sure - 2.5:.2f}:d=2.5", "-c:a", "aac", "-b:a", "192k",
                  "-shortest", "-movflags", "+faststart", str(hedef)])
        sessiz.unlink()
        yollar.append(hedef)
    return yollar
