"""Hesaptaki bütün postları siler (konsept değişikliği). X silme sınırı: 15 dakikada 50; her çalışma en fazla
PARTI kadar siler, kalanını sonraki nabız sürdürür. Bitince kendini kapatır. Durum: data/temizlik.json."""

import json

from .config import ROOT

DOSYA = ROOT / "data" / "temizlik.json"
PARTI = 45


def durum() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _kaydet(d: dict) -> None:
    DOSYA.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def baslat(simdi) -> None:
    d = durum()
    _kaydet({**d, "aktif": True, "baslangic": d.get("baslangic") or simdi.isoformat(timespec="seconds"),
             "silinen": d.get("silinen", 0)})


def calistir(x, simdi, yaz=print) -> int:
    """Aktifse bir parti siler; silinen sayısını döner. Hesapta post kalmadıysa temizliği bitirir."""
    d = durum()
    if not d.get("aktif"):
        return 0
    idler = x.tum_tweet_idleri(PARTI)
    if not idler:
        _kaydet({**d, "aktif": False, "bitis": simdi.isoformat(timespec="seconds")})
        yaz(f"🧹 Temizlik bitti: toplam {d.get('silinen', 0)} post silindi.")
        return 0
    silinen = 0
    for tid in idler:
        try:
            x.sil(tid)
        except RuntimeError as e:
            if " 429" in str(e):  # silme sınırı: kalanı sonraki nabızda
                break
            raise
        silinen += 1
    _kaydet({**d, "silinen": d.get("silinen", 0) + silinen, "son": simdi.isoformat(timespec="seconds")})
    yaz(f"🧹 Temizlik: {silinen} post silindi (toplam {d.get('silinen', 0) + silinen}).")
    return silinen
