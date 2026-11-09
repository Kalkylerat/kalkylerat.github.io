"""Deep Space Log komut satırı. Bir görev = bir video. Kullanım:

    python -m deepspace.gorev istemler deepspace/gorevler/001-trappist   # sahibine Suno istem dosyası (SUNO.md)
    python -m deepspace.gorev hepsi    deepspace/gorevler/001-trappist   # ses -> sahne -> video -> kapak -> metin -> shorts -> kontrol
    python -m deepspace.gorev kontrol  deepspace/gorevler/001-trappist   # yalnızca kapılar (rapor.json)
    python -m deepspace.gorev kaydet   deepspace/gorevler/001-trappist   # sahibin "ok"undan sonra: kayit.json'a işle
    python -m deepspace.gorev kanal                                      # banner ve profil resmi

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
    satir += [f"Toplam hedef: {toplam / 60:.0f} dk ({len(gorev['parca'])} parça).", ""]
    yol = Path(gorev["klasor"]) / "SUNO.md"
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="deepspace.gorev")
    ap.add_argument("komut", choices=["istemler", "ses", "sahneler", "video", "kapak", "metin", "shorts", "kontrol",
                                      "hepsi", "kaydet", "kanal"])
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
