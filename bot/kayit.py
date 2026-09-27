"""Günlük oyun kaydı, sonuçlandırma ve performans istatistikleri. Tek doğruluk kaynağı: data/spel.json
Her seçim ayrı bir tekli (singel) oyundur ve 1 birim (enhet) ile sayılır."""

import json
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
    return {
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
