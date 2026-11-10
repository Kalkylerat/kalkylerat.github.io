"""Deep Space Log komut satırı. Bir görev = bir video. Kullanım:

    python -m deepspace.gorev istemler deepspace/gorevler/001-trappist   # sahibine Suno istem dosyası (SUNO.md)
    python -m deepspace.gorev gorseller deepspace/gorevler/001-trappist  # görsel istem listesi (GORSEL.md)
    python -m deepspace.gorev hepsi    deepspace/gorevler/001-trappist   # ses -> sahne -> video -> kapak -> metin -> shorts -> kontrol
    python -m deepspace.gorev kontrol  deepspace/gorevler/001-trappist   # yalnızca kapılar (rapor.json)
    python -m deepspace.gorev kaydet   deepspace/gorevler/001-trappist   # sahibin "ok"undan sonra: kayit.json'a işle
    python -m deepspace.gorev kanal                                      # banner ve profil resmi

Google (deepspace/KURULUM.md):
    python -m deepspace.gorev al      <klasör> --drive DeepSpaceLog/001  # Drive'dan ses/ ve gorsel/ dosyaları
    python -m deepspace.gorev teslim  <klasör> --drive DeepSpaceLog/001  # bitmiş paketi Drive'a (cikti alt klasörü)
    python -m deepspace.gorev onay    <klasör> --yayin 2026-11-20T17:00:00Z  # denetçinin kararı (G8), en az 24 sa sonra
    python -m deepspace.gorev iptal   <klasör> [--neden ...]           # sahibinin acil freni (G8)
    python -m deepspace.gorev yukle   <klasör>                           # YouTube'a gizli/planlı yükleme

Tek tek istasyonlar: ses, sahneler, video, kapak, metin, shorts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

from . import kapak, kapilar, metin, ses, video
from .ortak import KAYIT_DOSYASI, ayar_yukle, cikti, gorev_yukle, kayit_yukle, sure_oku


def istemler(gorev: dict, ayar: dict) -> Path:
    """Sahibinin Suno'ya kopyalayacağı istemler. Her parça için Style, Exclude, Lyrics ayrı kod bloğunda."""
    kirmizi = [k for k in kapilar.gorev_dosyasi(gorev, ayar) if not k["gecti"]]
    if kirmizi:
        raise SystemExit("görev dosyası kapıdan geçmedi: " + "; ".join(f"{k['ad']} {k['ayrinti']}" for k in kirmizi))
    satir = [f"# Mission {gorev['no']:03d} · {gorev['hedef']}: Suno istemleri", "",
             "Her parça için: Suno'da **Custom** modu aç, aşağıdaki üç bloğu ilgili kutulara yapıştır, **Create**.",
             "Beğendiğin varyasyonu indir ve **dosya adını tam olarak** aşağıdaki gibi koy, `ses/` klasörüne at.",
             "Parça hedef süreden kısa çıkarsa son 30 saniyesinden **Extend** ile tamamla. Vokal gelirse "
             "**Instrumental**'ı açıp yeniden üret.", ""]
    toplam = 0.0
    for i, p in enumerate(gorev["parca"], 1):
        toplam += sure_oku(p["hedef_sure"])
        satir += [f"## {i:02d}. {p['ad']} · {p['hedef_sure']} · {p['anahtar']} · {p['bpm']} BPM", "",
                  f"Dosya adı: `{p['dosya']}`", ""]
        if p.get("motif"):
            satir += [f"Motif: {p['motif']}", ""]
        for baslik, alan in (("Style", "style"), ("Exclude", "exclude"), ("Lyrics", "lyrics")):
            satir += [f"**{baslik}**", "```", p[alan].strip(), "```", ""]
    net = toplam - ayar["ses"]["capraz_gecis_sn"] * (len(gorev["parca"]) - 1)
    satir += [f"Toplam hedef: {len(gorev['parca'])} parça, ~{net / 60:.0f} dk (çapraz geçişler düşülmüş).", ""]
    yol = Path(gorev["klasor"]) / "SUNO.md"
    yol.write_text("\n".join(satir), encoding="utf-8")
    return yol


def gorsel_istemleri(gorev: dict) -> Path:
    """Görsel üretim listesi (GORSEL.md): her parça için sahne + marka stil eki; hazır olanlar işaretli."""
    from .ortak import marka_yukle
    g = marka_yukle()["gorsel"]
    satir = [f"# Mission {gorev['no']:03d} · {gorev['hedef']}: görsel istemleri", "",
             f"Model: `{g['model']}` (16:9). Her görsel `gorsel/NN.png` olarak kaydedilir (NN = parça no).",
             "Renk tonu sonradan marka filtresiyle verilir; istemdeki ışık tarifi yeterli.", ""]
    for i, p in enumerate(gorev["parca"], 1):
        durum = f"üretildi: `{p['gorsel_uretim']}`" if p.get("gorsel_uretim") else "üretilecek"
        satir += [f"## {i:02d}. {p['ad']} · {durum}", "", "```", f"{p['gorsel_istem']} {g['stil_eki']}", "```", ""]
    yol = Path(gorev["klasor"]) / "GORSEL.md"
    yol.write_text("\n".join(satir), encoding="utf-8")
    return yol


def ses_ozetleri(gorev: dict) -> list[str]:
    return [hashlib.sha256(d.read_bytes()).hexdigest() for d in ses.ses_dosyalari(gorev) if d.exists()]


def kaydet(gorev: dict, youtube_id: str | None) -> dict:
    kayit = kayit_yukle()
    kayit["gorevler"] = [g for g in kayit["gorevler"] if g.get("no") != gorev["no"]]
    kayit["gorevler"].append({
        "no": gorev["no"], "seri": gorev["seri"], "hedef": gorev["hedef"], "tohum": gorev["tohum"],
        "tarih": date.today().isoformat(), "youtube_id": youtube_id,
        "parcalar": [p["ad"] for p in gorev["parca"]], "ses_ozetleri": ses_ozetleri(gorev),
    })
    kayit["gorevler"].sort(key=lambda g: g["no"])
    KAYIT_DOSYASI.write_text(json.dumps(kayit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return kayit


def _adim(ad: str, is_):
    bas = time.time()
    print(f"→ {ad} ...", flush=True)
    sonuc = is_()
    print(f"  {ad} bitti ({time.time() - bas:.0f} sn)", flush=True)
    return sonuc


def _kirmizi_mi(kontroller: list[dict]) -> list[dict]:
    return [k for k in kontroller if not k["gecti"]]


def _google(a, gorev: dict) -> int:
    from . import google
    out = cikti(gorev)
    if a.komut == "onay":
        if not a.yayin:
            raise SystemExit("--yayin gerekli (planlı yayın saati, en az 24 saat sonra)")
        print(google.onay_yaz(out, a.kim or "denetci", a.yayin))
        return 0
    if a.komut == "iptal":
        print(google.iptal_yaz(out, a.neden or ""))
        yuk = out / "yukleme.json"
        if yuk.exists():
            google.youtube_planli_yayini_geri_al(json.loads(yuk.read_text(encoding="utf-8"))["video_id"])
            print("YouTube'daki planlı yayın geri alındı (video gizli kaldı)")
        return 0
    if a.komut == "yukle":
        sonuc = google.youtube_yukle(out)
        print(f"yüklendi (gizli): https://youtu.be/{sonuc['id']}  {sonuc.get('kapak_hatasi', '')}")
        return 0
    if not a.drive:
        raise SystemExit("--drive klasör yolu gerekli")
    tok = google.erisim_belirteci()
    if a.komut == "al":
        kok = google.klasor_yolu(a.drive, tok)
        istenen = {p["dosya"] for p in gorev["parca"]}
        (Path(gorev["klasor"]) / "ses").mkdir(exist_ok=True)
        for d in google.drive_listele(kok, tok):
            if d["name"] in istenen:
                print("ses:", google.drive_indir(d["id"], Path(gorev["klasor"]) / "ses" / d["name"], tok))
        gorsel_id = google.klasor_bul("gorsel", tok, kok)
        if gorsel_id:
            (Path(gorev["klasor"]) / "gorsel").mkdir(exist_ok=True)
            for d in google.drive_listele(gorsel_id, tok):
                print("görsel:", google.drive_indir(d["id"], Path(gorev["klasor"]) / "gorsel" / d["name"], tok))
        eksik = sorted(istenen - {p.name for p in (Path(gorev["klasor"]) / "ses").glob("*")})
        print("eksik ses:", ", ".join(eksik) if eksik else "yok")
        return 0 if not eksik else 1
    hedef = google.klasor_yolu(a.drive.rstrip("/") + "/cikti", tok, olustur=True)
    for ad, mime in (("video.mp4", "video/mp4"), ("kapak_1.jpg", "image/jpeg"), ("kapak_2.jpg", "image/jpeg"),
                     ("kapak_3.jpg", "image/jpeg"), ("short_1.mp4", "video/mp4"), ("short_2.mp4", "video/mp4"),
                     ("short_3.mp4", "video/mp4"), ("aciklama.txt", "text/plain"), ("youtube.json", "application/json"),
                     ("rapor.json", "application/json")):
        if (out / ad).exists():
            print("teslim:", ad, google.drive_yukle(out / ad, hedef, tok, mime))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="deepspace.gorev")
    ap.add_argument("komut", choices=["istemler", "ses", "sahneler", "video", "kapak", "metin", "shorts", "kontrol",
                                      "hepsi", "kaydet", "kanal", "al", "teslim", "onay", "iptal", "yukle",
                                      "gorseller"])
    ap.add_argument("--drive", help="Drive klasör yolu, ör. DeepSpaceLog/001")
    ap.add_argument("--kim", help="karar veren (varsayılan: denetci)")
    ap.add_argument("--neden", help="iptal nedeni")
    ap.add_argument("--yayin", help="planlı yayın zamanı, RFC3339 UTC")
    ap.add_argument("klasor", nargs="?")
    ap.add_argument("--youtube-id")
    ap.add_argument("--siyah-kontrolu-yok", action="store_true", help="hızlı deneme için siyah ekran taramasını atla")
    a = ap.parse_args(argv)

    if a.komut == "kanal":
        for y in kapak.kanal_gorselleri(ayar_yukle()):
            print(y)
        return 0
    if not a.klasor:
        ap.error("görev klasörü gerekli")
    gorev, ayar = gorev_yukle(Path(a.klasor))

    if a.komut == "istemler":
        print(istemler(gorev, ayar))
        return 0
    if a.komut == "gorseller":
        print(gorsel_istemleri(gorev))
        return 0
    if a.komut in ("al", "teslim", "onay", "iptal", "yukle"):
        return _google(a, gorev)
    if a.komut == "kaydet":
        kaydet(gorev, a.youtube_id)
        print(f"kayit.json güncellendi: görev {gorev['no']}")
        return 0

    gorev["_ses_ozetleri"] = ses_ozetleri(gorev)
    on = kapilar.ozgunluk(gorev, kayit_yukle(), gorev["_ses_ozetleri"])
    if _kirmizi_mi(on) and a.komut in ("ses", "hepsi"):
        for k in _kirmizi_mi(on):
            print(f"KAPI KAPALI: {k['ad']} {k['ayrinti']}")
        return 2

    adimlar = {
        "ses": lambda: ses.birlestir(gorev, ayar),
        "sahneler": lambda: video.sahneler(gorev, ayar),
        "video": lambda: video.uzun_video(gorev, ayar),
        "kapak": lambda: kapak.kapaklar(gorev, ayar),
        "metin": lambda: metin.uret(gorev, ayar),
        "shorts": lambda: video.shorts(gorev, ayar),
    }
    if a.komut in adimlar:
        _adim(a.komut, adimlar[a.komut])
    elif a.komut == "hepsi":
        bolumler = _adim("ses", adimlar["ses"])
        ses_k = kapilar.ses(bolumler, ayar, ayar["seri"][gorev["seri"]]["hedef_dakika"])
        if _kirmizi_mi(ses_k):
            for k in _kirmizi_mi(ses_k):
                print(f"KAPI KAPALI (ses): {k['ad']} {k['ayrinti']}")
            return 2
        for ad in ("sahneler", "video", "kapak", "metin", "shorts"):
            _adim(ad, adimlar[ad])

    r = kapilar.rapor(gorev, ayar, siyah_kontrol=not a.siyah_kontrolu_yok)
    kirmizi = _kirmizi_mi(r["kontroller"])
    print(f"\nRapor: {cikti(gorev) / 'rapor.json'}  ·  {len(r['kontroller'])} kontrol, {len(kirmizi)} kırmızı")
    for k in kirmizi:
        print(f"  ✗ {k['ad']}  {k['ayrinti']}")
    return 0 if r["gecti"] else 1


if __name__ == "__main__":
    sys.exit(main())
