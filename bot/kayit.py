"""Günlük oyun kaydı, sonuçlandırma ve performans istatistikleri. Tek doğruluk kaynağı: data/spel.json
Her seçim ayrı bir tekli (singel) oyundur ve 1 birim (enhet) ile sayılır."""

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .model import kazandi_mi


def yukle(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def kaydet(path: Path, gunler: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gunler, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bul(gunler: list[dict], gun_id: str) -> dict | None:
    return next((g for g in gunler if g["id"] == gun_id), None)


def kombi_durumu(gun: dict) -> str | None:
    """"tuttu" / "yatti" / None (kombine yok ya da sonuçlanmadı). İptal seçimler kombineden düşer."""
    if len(gun["secimler"]) < 2 or any(s["durum"] == "bekliyor" for s in gun["secimler"]):
        return None
    gecerli = [s for s in gun["secimler"] if s["durum"] != "iptal"]
    if len(gecerli) < 2:
        return None
    return "tuttu" if all(s["durum"] == "kazandi" for s in gecerli) else "yatti"


def kombi_oran(gun: dict) -> float:
    return math.prod(s["oran"] for s in gun["secimler"] if s["durum"] != "iptal")


def kombi_olasilik(gun: dict) -> float:
    return math.prod(s["adil_olasilik"] for s in gun["secimler"] if s["durum"] != "iptal")


def kar(secim: dict) -> float:
    return {"kazandi": secim["oran"] - 1, "kaybetti": -1.0}.get(secim["durum"], 0.0)


def bekleyen_fixturelar(gunler: list[dict], simdi: datetime) -> list[int]:
    return sorted({
        s["fixture_id"]
        for g in gunler if g["sonuc"] is None
        for s in g["secimler"]
        if s["durum"] == "bekliyor" and datetime.fromisoformat(s["baslama"]) < simdi
    })


def sonuclandir(gunler: list[dict], sonuclar: dict[int, dict], simdi: datetime) -> list[dict]:
    """Oyunları günceller; tüm oyunları sonuçlanan günleri döndürür."""
    biten = []
    for g in gunler:
        if g["sonuc"] is not None:
            continue
        for s in g["secimler"]:
            if s["durum"] != "bekliyor":
                continue
            r = sonuclar.get(s["fixture_id"])
            if r and r["durum"] == "bitti":
                ev, dep = r["skor"]
                s["skor"] = f"{ev}-{dep}"
                s["durum"] = "kazandi" if kazandi_mi(s["pazar"], ev, dep) else "kaybetti"
            elif (r and r["durum"] == "iptal") or datetime.fromisoformat(s["baslama"]) < simdi - timedelta(days=3):
                s["durum"] = "iptal"
        if all(s["durum"] != "bekliyor" for s in g["secimler"]):
            g["sonuc"] = "tamam"
            g["sonuclanma"] = simdi.isoformat(timespec="seconds")
            biten.append(g)
    return biten


def ozet(gunler: list[dict]) -> dict:
    """Yalnızca X'te yayınlanmış oyunlar sayılır; taslaklar istatistiğe girmez."""
    oyunlar = [s for g in gunler if g.get("tweet_id") for s in g["secimler"]]
    biten = [s for s in oyunlar if s["durum"] in ("kazandi", "kaybetti")]
    kazanan = [s for s in biten if s["durum"] == "kazandi"]
    toplam_kar = sum(kar(s) for s in biten)
    kombiler = [(g, kombi_durumu(g)) for g in gunler if g.get("tweet_id")]
    kombiler = [(g, d) for g, d in kombiler if d]
    kombi_tuttu = [g for g, d in kombiler if d == "tuttu"]
    return {
        "kombi": len(kombiler),
        "kombi_tuttu": len(kombi_tuttu),
        "kombi_birim": round(sum(kombi_oran(g) - 1 for g in kombi_tuttu) - (len(kombiler) - len(kombi_tuttu)), 2),
        "spel": len(biten),
        "vunna": len(kazanan),
        "forlorade": len(biten) - len(kazanan),
        "traff": round(100 * len(kazanan) / len(biten), 1) if biten else 0.0,
        "enheter": round(toplam_kar, 2),
        "roi": round(100 * toplam_kar / len(biten), 1) if biten else 0.0,
        "snittodds": round(sum(s["oran"] for s in biten) / len(biten), 2) if biten else 0.0,
        "vantande": len([s for s in oyunlar if s["durum"] == "bekliyor"]),
    }


def simdi_utc() -> datetime:
    return datetime.now(timezone.utc)
