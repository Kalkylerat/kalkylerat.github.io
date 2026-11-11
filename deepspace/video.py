"""Video istasyonu: sahne döngüleri, uzun video (parça parça kodlanıp birleştirilir) ve Shorts.

Bellek güvenli yöntem: video, her parçanın tek başına aktığı "düz" bölümlerle iki parça arasındaki "geçiş"
bölümlerine ayrılır. Her bölüm ayrı kodlanır (paralel), sonra ffmpeg concat ile kopyalanarak birleşir ve ses eklenir.
Böylece iki saatlik video tek bir dev filtre zinciri gerektirmez.
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from . import klip, yazi
from .ortak import calistir, cikti, ffprobe_sure
from .sahne import Sahne, dongu_kodla
from .tablo import Tablo, Tablo3D

GORSEL_UZANTI = (".png", ".jpg", ".jpeg", ".webp")


def _tohum(gorev: dict, i: int) -> int:
    return int(gorev["tohum"]) * 100 + i


def parca_gorseli(gorev: dict, i: int) -> tuple[Path | None, Path | None]:
    """gorsel/NN.png (ya da .jpg/.webp) ve isteğe bağlı şeffaf ön plan gorsel/NN_on.png."""
    klasor = Path(gorev["klasor"]) / "gorsel"
    ana = next((klasor / f"{i + 1:02d}{u}" for u in GORSEL_UZANTI if (klasor / f"{i + 1:02d}{u}").exists()), None)
    on = klasor / f"{i + 1:02d}_on.png"
    return ana, (on if on.exists() else None)


def parca_klibi(gorev: dict, i: int) -> Path | None:
    """Hareketli klip gorsel/NN.mp4 (yapay zekâ videosu). Varsa görselden önce gelir."""
    yol = Path(gorev["klasor"]) / "gorsel" / f"{i + 1:02d}.mp4"
    return yol if yol.exists() else None


def _derinlik_dene(ana: Path):
    """Derinlik haritası (önbellekli). Model ya da paketler yoksa None: düz canlı tabloya düşülür."""
    try:
        import cv2  # noqa: F401
        from .derinlik import derinlik_haritasi
        return derinlik_haritasi(ana)
    except Exception:  # paket yok, model inmedi: 3D olmadan devam (G6 yine sağlanır)
        return None


def sahne_nesnesi(gorev: dict, i: int, W: int, H: int, L: float, **kw):
    """Öncelik: klip (sahneler() doğrudan döngüye çevirir) > sinemagraf (gorsel/NN_hareket.json) > 3D fotoğraf
    (derinlik modeli) > canlı tablo > yedek kod sahnesi."""
    ana, on = parca_gorseli(gorev, i)
    if ana:
        from .canli import Sinemagraf, tarif_oku
        tarif = tarif_oku(ana)
        if tarif:  # sinemagraf: görüntü sabit, yalnızca tarifteki bölgeler hareket eder
            return Sinemagraf(ana, tarif, W, H, L, tohum=_tohum(gorev, i), derinlik=_derinlik_dene(ana))
        d = _derinlik_dene(ana)
        if d is not None:  # 3D fotoğraf efekti (ücretsiz derinlik modeli)
            return Tablo3D(ana, d, W, H, L, tohum=_tohum(gorev, i))
        return Tablo(ana, W, H, L, tohum=_tohum(gorev, i), on_plan=on)
    return Sahne(gorev["parca"][i], _tohum(gorev, i), W, H, L, **kw)


def marka_lut(gorev: dict) -> Path | None:
    """marka.toml'da filtre seçiliyse .cube dosyasını yazar (G6: bütün görseller aynı tonda)."""
    from .renk import cube_yaz, marka_filtresi
    f = marka_filtresi()
    return cube_yaz(cikti(gorev) / "marka.cube", f) if f else None


def _sahne_isi(args):
    gorev, i, W, H, L, fps, hedef, lut = args
    kaynak = parca_klibi(gorev, i)
    if kaynak:  # öncelik: hareketli klip -> dikişsiz döngü
        klip.dongu(kaynak, Path(hedef), W, H, fps=fps, lut=lut)
    else:
        dongu_kodla(sahne_nesnesi(gorev, i, W, H, L), Path(hedef), fps=fps, lut=lut)
    return hedef


def sahneler(gorev: dict, ayar: dict, yeniden: bool = False) -> list[Path]:
    v = ayar["video"]
    klasor = cikti(gorev) / "sahne"
    klasor.mkdir(exist_ok=True)
    isler, yollar = [], []
    lut = marka_lut(gorev)
    for i, p in enumerate(gorev["parca"]):
        hedef = klasor / f"sahne_{i + 1:02d}.mp4"
        yollar.append(hedef)
        if yeniden or not hedef.exists():
            isler.append((gorev, i, v["genislik"], v["yukseklik"], float(v["dongu_sn"]), v["fps"], str(hedef), lut))
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
    b, sahne_yollari, basla, donguler, v, etiketler, hedef = args
    fps = v["fps"]
    i = b["i"]
    yerel = (b["bas"] - basla[i]) % donguler[i]  # her sahnenin kendi döngü süresi (klipler farklı uzunlukta)
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


def parca_bilgisi(gorev: dict, i: int) -> dict:
    """Seyir Defteri kaydı için parça bilgisi (gerçek bilgi gorev.toml'dan). i: 0'dan."""
    p, n = gorev["parca"][i], len(gorev["parca"])
    return {"ad": p["ad"], "kisa": p.get("kisa", ""), "bilgi": p.get("bilgi", ""), "gorev_no": gorev["no"],
            "hedef": gorev["hedef"], "parca_no": i + 1, "parca_say": n,
            "sonraki": gorev["parca"][i + 1]["ad"] if i + 1 < n else ""}


def bolum_kesimleri(bolumler: dict) -> list[tuple[float, float]]:
    """Parça i'nin görüntü aralığı (sn). Kesim çapraz geçişin ortasındadır; ilk 0'dan, son toplam süreye kadar."""
    yarim = bolumler["capraz_gecis_sn"] / 2
    basla = [p["basla"] for p in bolumler["parcalar"]]
    kes = [0.0] + [b + yarim for b in basla[1:]] + [float(bolumler["toplam_sn"])]
    return list(zip(kes[:-1], kes[1:]))


def _defter_bolumu(args) -> str:
    """Bir parçanın Seyir Defteri bölümü (ayrı süreçte): görsel + katmanlar + o aralığın müziği, sessiz ara çıktı."""
    from . import defter
    from .renk import marka_filtresi
    gorev, i, ilk, son, v, ses, hedef, gecis_sn = args
    fps = v["fps"]
    gorsel = parca_gorseli(gorev, i)[0]
    bas, sure = ilk / fps, (son - ilk) / fps
    if gorsel is None:  # G6/G13: görseli olmayan parça kod sahnesine düşmez; video çıkmaz, sahibine sorulur
        raise FileNotFoundError(f"parça {i + 1} için onaylı görsel yok (gorsel/{i + 1:02d}.png); video üretilmedi")
    n = len(gorev["parca"])
    onceki = parca_gorseli(gorev, i - 1)[0] if i > 0 else None
    sonraki = parca_gorseli(gorev, i + 1)[0] if i + 1 < n else None
    imza = _bolum_imzasi(gorsel, onceki, sonraki, ilk, son, v, parca_bilgisi(gorev, i), ses)
    imza_yolu = Path(hedef).with_suffix(".imza")
    if Path(hedef).exists() and imza_yolu.exists() and imza_yolu.read_text(encoding="utf-8") == imza:
        return hedef  # kaldığı yerden devam: aynı girdilerle kodlanmış bölüm yeniden kodlanmaz
    muzik = defter.ses_ozeti(ses, fps, basla=bas, sure=sure)
    sahne = defter.SeyirDefteri(gorsel, defter.katmanlari_oku(gorsel), v["genislik"], v["yukseklik"], fps, sure,
                                muzik, parca_bilgisi(gorev, i), tohum=_tohum(gorev, i), ton=marka_filtresi(), t0=bas,
                                onceki=onceki, sonraki=sonraki, gecis_sn=gecis_sn)
    yol = str(defter.kodla(sahne, None, Path(hedef), None, crf=v["crf"], preset=v["preset"]))
    imza_yolu.write_text(imza, encoding="utf-8")
    return yol


def _bolum_imzasi(gorsel, onceki, sonraki, ilk, son, v, bilgi, ses) -> str:
    import hashlib
    h = hashlib.sha256()
    for yol in (gorsel, onceki, sonraki, ses):
        h.update(Path(yol).read_bytes() if yol and Path(yol).exists() else b"-")
    h.update(json.dumps([ilk, son, v["genislik"], v["yukseklik"], v["fps"], v["crf"], bilgi],
                        sort_keys=True, ensure_ascii=False).encode())
    return h.hexdigest()


def uzun_video_defter(gorev: dict, ayar: dict) -> Path:
    """Uzun video Seyir Defteri modunda: parça başına bir bölüm (paralel süreçler), concat, master ses eklenir."""
    v = ayar["video"]
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    fps = v["fps"]
    ara = out / "ara"
    ara.mkdir(exist_ok=True)
    ses = out / "ses.m4a"
    isler = []
    for i, (bas, son) in enumerate(bolum_kesimleri(bolumler)):  # kare ızgarasına oturur: toplam kayma olmaz
        isler.append((gorev, i, round(bas * fps), round(son * fps), v, ses, str(ara / f"bolum_{i + 1:02d}.mp4"),
                      float(bolumler["capraz_gecis_sn"])))
    with ProcessPoolExecutor(max_workers=v["is_parcacigi"]) as ex:
        parcalar = list(ex.map(_defter_bolumu, isler))
    liste = ara / "liste.txt"
    liste.write_text("".join(f"file '{Path(p).name}'\n" for p in parcalar), encoding="utf-8")
    hedef = out / "video.mp4"
    # Bölümler yalnız birleştirme başarılı olunca silinir; hata olursa saatlerce kodlanmış bölümler kalır ve
    # bir sonraki çalıştırma kaldığı yerden devam eder (imzası tutan bölüm yeniden kodlanmaz).
    calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(liste),
              "-i", str(ses), "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart", str(hedef)])
    for p in [*parcalar, liste]:
        Path(p).unlink(missing_ok=True)
        Path(p).with_suffix(".imza").unlink(missing_ok=True)
    return hedef


def uzun_video(gorev: dict, ayar: dict) -> Path:
    if ayar["video"].get("mod") == "defter":
        return uzun_video_defter(gorev, ayar)
    v, ks = ayar["video"], ayar["kanal"]
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    sahne_yollari = sahneler(gorev, ayar)
    fps, W, H = v["fps"], v["genislik"], v["yukseklik"]
    donguler = [ffprobe_sure(y) for y in sahne_yollari]
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
        isler.append((b, sahne_yollari, basla, donguler, v, etiketler, str(bolum_klasor / f"b{k:03d}.mp4")))
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
    """Shorts departmanına devreder (G12): plan, dikey Seyir Defteri, kapılar."""
    from . import shorts as sh
    return sh.uret(gorev, ayar)
