"""Günlük oyun kaydı, sonuçlandırma, sanal kasa ve performans istatistikleri.
Tek doğruluk kaynağı: data/spel.json. Her tekli oyun ve kombine, yayınlandığı andaki kasanın belirli yüzdesiyle oynanır."""

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


def kombi_ayaklari(gun: dict) -> list[dict]:
    kombi = gun.get("kombi")
    return [gun["secimler"][i] for i in kombi["ayaklar"]] if kombi else []


def kombi_durumu(gun: dict) -> str | None:
    """"tuttu" / "yatti" / "iptal" / None (kombine yok ya da sonuçlanmadı). İptal ayaklar kombineden düşer."""
    ayaklar = kombi_ayaklari(gun)
    if not ayaklar or any(s["durum"] == "bekliyor" for s in ayaklar):
        return None
    gecerli = [s for s in ayaklar if s["durum"] != "iptal"]
    if not gecerli:
        return "iptal"
    return "tuttu" if all(s["durum"] == "kazandi" for s in gecerli) else "yatti"


def kombi_oran(gun: dict) -> float:
    return math.prod(s["oran"] for s in kombi_ayaklari(gun) if s["durum"] != "iptal")


def kombi_olasilik(gun: dict) -> float:
    return math.prod(s["adil_olasilik"] for s in kombi_ayaklari(gun) if s["durum"] != "iptal")


def kar(secim: dict) -> float:
    return {"kazandi": secim["stake"] * (secim["oran"] - 1), "kaybetti": -secim["stake"]}.get(secim["durum"], 0.0)


def kombi_kar(gun: dict) -> float:
    durum = kombi_durumu(gun)
    if durum == "tuttu":
        return gun["kombi"]["stake"] * (kombi_oran(gun) - 1)
    return -gun["kombi"]["stake"] if durum == "yatti" else 0.0


def gun_kar(gun: dict) -> float:
    return sum(kar(s) for s in gun["secimler"]) + (kombi_kar(gun) if gun.get("kombi") else 0.0)


def kasa(gunler: list[dict], baslangic: float) -> float:
    """Yayınlanmış ve sonuçlanmış oyunlara göre güncel kasa."""
    return baslangic + sum(gun_kar(g) for g in gunler if g.get("tweet_id"))


def bekleyen_fixturelar(gunler: list[dict], simdi: datetime) -> list[int]:
    return sorted({
        s["fixture_id"]
        for g in gunler if g["sonuc"] is None
        for s in g["secimler"]
        if s["durum"] == "bekliyor" and datetime.fromisoformat(s["baslama"]) < simdi
    })


def korner_fixturelari(gunler: list[dict]) -> set[int]:
    return {s["fixture_id"] for g in gunler if g["sonuc"] is None for s in g["secimler"]
            if s["durum"] == "bekliyor" and any(b["pazar"].startswith("KOR") for b in s.get("bacaklar") or [s])}


def _durum(s: dict, ev: int, dep: int, iy, korner) -> str:
    """Tekli oyun ya da bet builder için kazandi / kaybetti / iptal (veri yoksa iptal)."""
    bacaklar = s.get("bacaklar") or [s]
    sonuclar = [kazandi_mi(b["pazar"], ev, dep, iy, korner) for b in bacaklar]
    if s.get("bacaklar"):
        for b, r in zip(s["bacaklar"], sonuclar):
            b["durum"] = "iptal" if r is None else ("kazandi" if r else "kaybetti")
    if any(r is False for r in sonuclar):
        return "kaybetti"  # bir ayak kaybettiyse, verisi olmayan ayak olsa bile oyun kaybedilmiştir
    if any(r is None for r in sonuclar):
        return "iptal"
    return "kazandi"


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
                s["durum"] = _durum(s, ev, dep, r.get("iy"), r.get("korner"))
            elif (r and r["durum"] == "iptal") or datetime.fromisoformat(s["baslama"]) < simdi - timedelta(days=3):
                s["durum"] = "iptal"
        if all(s["durum"] != "bekliyor" for s in g["secimler"]):
            g["sonuc"] = "tamam"
            g["sonuclanma"] = simdi.isoformat(timespec="seconds")
            if g.get("kombi"):
                g["kombi"]["durum"] = kombi_durumu(g)
            biten.append(g)
    return biten


def ozet(gunler: list[dict], baslangic: float = 10000.0) -> dict:
    """Yalnızca X'te yayınlanmış oyunlar sayılır; taslaklar istatistiğe girmez."""
    yayinlanan = [g for g in gunler if g.get("tweet_id")]
    oyunlar = [s for g in yayinlanan for s in g["secimler"]]
    biten = [s for s in oyunlar if s["durum"] in ("kazandi", "kaybetti")]
    kazanan = [s for s in biten if s["durum"] == "kazandi"]
    kombiler = [kombi_durumu(g) for g in yayinlanan if g.get("kombi")]
    kombiler = [d for d in kombiler if d in ("tuttu", "yatti")]
    guncel = kasa(gunler, baslangic)
    return {
        "spel": len(biten),
        "vunna": len(kazanan),
        "forlorade": len(biten) - len(kazanan),
        "traff": round(100 * len(kazanan) / len(biten), 1) if biten else 0.0,
        "kombi": len(kombiler),
        "kombi_tuttu": kombiler.count("tuttu"),
        "kasa": round(guncel, 2),
        "kasa_degisim": round(100 * (guncel - baslangic) / baslangic, 1),
        "snittodds": round(sum(s["oran"] for s in biten) / len(biten), 2) if biten else 0.0,
        "vantande": len([s for s in oyunlar if s["durum"] == "bekliyor"]),
    }


def simdi_utc() -> datetime:
    return datetime.now(timezone.utc)


def hafta_ozeti(gunler: list[dict], bitis: str) -> dict:
    """bitis dahil son 7 günün yayınlanmış oyunları."""
    son = datetime.fromisoformat(bitis).date()
    bas = son - timedelta(days=6)
    hafta = [g for g in gunler if g.get("tweet_id") and bas <= datetime.fromisoformat(g["tarih"]).date() <= son]
    biten = [s for g in hafta for s in g["secimler"] if s["durum"] in ("kazandi", "kaybetti")]
    kazanan = sum(s["durum"] == "kazandi" for s in biten)
    kuponlar = [kombi_durumu(g) for g in hafta if g.get("kombi")]
    kuponlar = [d for d in kuponlar if d in ("tuttu", "yatti")]
    return {
        "baslangic": bas.isoformat(), "bitis": son.isoformat(),
        "gun": len(hafta), "oyun": len(biten), "kazanan": kazanan,
        "bekleyen": sum(s["durum"] == "bekliyor" for g in hafta for s in g["secimler"]), "kaybeden": len(biten) - kazanan,
        "isabet": 100 * kazanan / len(biten) if biten else 0.0,
        "kupon": len(kuponlar), "kupon_tuttu": kuponlar.count("tuttu"),
        "kar": sum(gun_kar(g) for g in hafta),
    }

