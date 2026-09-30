"""Suno'dan indirilen şarkıları klasörlere düzenler.

    python duzenle.py isaret
    python duzenle.py tasi --proje "Yaz Albümü" --baslik "Gece Yolu" --stil "synthwave" ...
    python duzenle.py liste
"""
import argparse
import csv
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

SES_UZANTILARI = {".mp3", ".wav", ".m4a", ".flac", ".mp4"}
YARIM_UZANTILAR = {".crdownload", ".part", ".tmp", ".download"}
KATALOG_ALANLARI = ["tarih", "proje", "baslik", "stil", "sarkici_modu", "suno_link", "klasor", "dosyalar"]


def kok_klasor(arg):
    return Path(arg or os.environ.get("SUNO_KLASOR") or Path.home() / "Music" / "Suno").expanduser()


def indirilenler(arg):
    return Path(arg or os.environ.get("SUNO_INDIRILENLER") or Path.home() / "Downloads").expanduser()


def guvenli_ad(metin):
    temiz = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", metin).strip().rstrip(".")
    return re.sub(r"\s+", " ", temiz)[:80] or "adsiz"


def isaret_dosyasi(kok):
    return kok / ".son_isaret"


def isaret(kok):
    kok.mkdir(parents=True, exist_ok=True)
    isaret_dosyasi(kok).write_text(str(time.time()), encoding="utf-8")
    print(f"İşaret konuldu: bundan sonra indirilen şarkılar taşınacak ({kok})")


def yeni_dosyalar(klasor, baslangic):
    return sorted(
        (p for p in klasor.iterdir()
         if p.is_file() and p.suffix.lower() in SES_UZANTILARI and p.stat().st_mtime >= baslangic),
        key=lambda p: p.stat().st_mtime,
    )


def indirmeleri_bekle(klasor, bekleme_sn):
    bitis = time.time() + bekleme_sn
    while time.time() < bitis:
        if not any(p.suffix.lower() in YARIM_UZANTILAR for p in klasor.iterdir()):
            return True
        time.sleep(2)
    return False


def hedef_yol(klasor, ad):
    yol = klasor / ad
    sayac = 2
    while yol.exists():
        yol = klasor / f"{Path(ad).stem} ({sayac}){Path(ad).suffix}"
        sayac += 1
    return yol


def tasi(a):
    kok = kok_klasor(a.kok)
    kaynak = indirilenler(a.indirilenler)
    if not isaret_dosyasi(kok).exists():
        sys.exit("Önce 'isaret' komutunu çalıştırın (indirmeye başlamadan hemen önce).")
    # Bazı dosya sistemleri mtime'ı yuvarlıyor; 2 sn pay bırak.
    baslangic = float(isaret_dosyasi(kok).read_text(encoding="utf-8")) - 2

    if not indirmeleri_bekle(kaynak, a.bekle):
        print("Uyarı: bazı indirmeler hâlâ sürüyor; biten dosyalar taşınıyor.")
    dosyalar = yeni_dosyalar(kaynak, baslangic)
    if not dosyalar:
        sys.exit(f"İşaretten sonra {kaynak} içinde yeni ses dosyası bulunamadı.")

    tarih = datetime.now()
    hedef = kok / guvenli_ad(a.proje) / f"{tarih:%Y-%m-%d}_{guvenli_ad(a.baslik)}"
    hedef.mkdir(parents=True, exist_ok=True)
    tasinan = [shutil.move(str(d), hedef_yol(hedef, d.name)) for d in dosyalar]
    adlar = [Path(t).name for t in tasinan]

    sozler = Path(a.sozler_dosyasi).read_text(encoding="utf-8") if a.sozler_dosyasi else ""
    if sozler:
        (hedef / "sozler.txt").write_text(sozler, encoding="utf-8")
    bilgi = {
        "baslik": a.baslik,
        "proje": a.proje,
        "tarih": tarih.isoformat(timespec="seconds"),
        "stil": a.stil,
        "sarkici_modu": a.mod,
        "suno_link": a.link,
        "not": a.notlar,
        "sozler": sozler,
        "dosyalar": adlar,
    }
    (hedef / "bilgi.json").write_text(json.dumps(bilgi, ensure_ascii=False, indent=2), encoding="utf-8")

    katalog = kok / "katalog.csv"
    yeni = not katalog.exists()
    with katalog.open("a", newline="", encoding="utf-8-sig") as f:
        yazici = csv.DictWriter(f, fieldnames=KATALOG_ALANLARI)
        if yeni:
            yazici.writeheader()
        yazici.writerow({
            "tarih": tarih.strftime("%Y-%m-%d %H:%M"), "proje": a.proje, "baslik": a.baslik,
            "stil": a.stil, "sarkici_modu": a.mod, "suno_link": a.link,
            "klasor": str(hedef.relative_to(kok)), "dosyalar": " | ".join(adlar),
        })
    isaret(kok)
    print(f"{len(adlar)} dosya taşındı → {hedef}")
    for ad in adlar:
        print(f"  - {ad}")


def liste(a):
    katalog = kok_klasor(a.kok) / "katalog.csv"
    if not katalog.exists():
        print("Henüz şarkı yok.")
        return
    with katalog.open(encoding="utf-8-sig") as f:
        for satir in list(csv.DictReader(f))[-a.son:]:
            print(f"{satir['tarih']}  [{satir['proje']}]  {satir['baslik']}  —  {satir['stil']}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Suno şarkılarını klasörlere düzenler")
    p.add_argument("--kok", help="Şarkıların saklanacağı ana klasör (varsayılan ~/Music/Suno)")
    p.add_argument("--indirilenler", help="Chrome'un indirme klasörü (varsayılan ~/Downloads)")
    alt = p.add_subparsers(dest="komut", required=True)

    alt.add_parser("isaret", help="İndirmeye başlamadan önce çalıştırın")

    t = alt.add_parser("tasi", help="İşaretten sonra inen şarkıları taşı")
    t.add_argument("--proje", default="Genel")
    t.add_argument("--baslik", required=True)
    t.add_argument("--stil", default="")
    t.add_argument("--mod", default="", help="vokal / enstrümantal")
    t.add_argument("--link", default="", help="Suno şarkı linki")
    t.add_argument("--sozler-dosyasi", help="Şarkı sözlerinin bulunduğu metin dosyası")
    t.add_argument("--notlar", default="")
    t.add_argument("--bekle", type=int, default=90, help="Süren indirmeler için en fazla bekleme (sn)")

    l = alt.add_parser("liste", help="Son şarkıları göster")
    l.add_argument("--son", type=int, default=20)

    a = p.parse_args(argv)
    if a.komut == "isaret":
        isaret(kok_klasor(a.kok))
    elif a.komut == "tasi":
        tasi(a)
    else:
        liste(a)


if __name__ == "__main__":
    main()
