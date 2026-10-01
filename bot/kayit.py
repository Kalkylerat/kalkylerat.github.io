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


def kuponlar(gun: dict) -> list[dict]:
    """Günün kuponları. Her kupon (tek maç ya da kombine) kasanın %1'iyle oynanır.
    Eski kayıtlarda tek "kombi" alanı kupon sayılır (o günlerde tekliler de ayrıca oynanmıştı)."""
    if gun.get("kuponlar"):
        return gun["kuponlar"]
    return [gun["kombi"]] if gun.get("kombi") else []


def kuponlara_bol(gun: dict, gunler: list[dict]) -> list[dict]:
    """Çok kuponlu kaydı kupon başına ayrı kayda böler (her kupon ayrı paylaşım = daha çok etkileşim).
    İlk kupon kaydın kimliğini korur; diğerleri aynı tarihin boş ilk kimliklerini alır (2026-10-01-2, -3 …)."""
    liste = kuponlar(gun)
    if len(liste) <= 1:
        return [gun]
    alinan = {g["id"] for g in gunler} | {gun["id"]}
    parcalar = []
    for n, kupon in enumerate(liste):
        yeni = {k: v for k, v in gun.items() if k not in ("secimler", "kuponlar", "vitrin", "taranan", "yanit_onerileri")}
        yeni["secimler"] = [gun["secimler"][i] for i in kupon["ayaklar"]]
        yeni["kuponlar"] = [{**kupon, "ayaklar": list(range(len(kupon["ayaklar"])))}]
        if n == 0:
            yeni.update({k: gun[k] for k in ("vitrin", "taranan", "yanit_onerileri") if k in gun})
        else:
            sira = 2
            while f'{gun["tarih"]}-{sira}' in alinan:
                sira += 1
            yeni["id"], yeni["ek"] = f'{gun["tarih"]}-{sira}', True
            alinan.add(yeni["id"])
        for s in yeni["secimler"]:
            s.pop("kupon_no", None)
        parcalar.append(yeni)
    return parcalar


def kupon_ayaklari(gun: dict, kupon: dict) -> list[dict]:
    return [gun["secimler"][i] for i in kupon["ayaklar"]]


def kupon_durumu(gun: dict, kupon: dict) -> str | None:
    """"tuttu" / "yatti" / "iptal" / None (sonuçlanmadı). İptal ayaklar kupondan düşer."""
    ayaklar = kupon_ayaklari(gun, kupon)
    if any(s["durum"] == "kaybetti" for s in ayaklar):
        return "yatti"
    if not ayaklar or any(s["durum"] == "bekliyor" for s in ayaklar):
        return None
    return "tuttu" if any(s["durum"] == "kazandi" for s in ayaklar) else "iptal"


def kupon_oran(gun: dict, kupon: dict) -> float:
    return math.prod(s["oran"] for s in kupon_ayaklari(gun, kupon) if s["durum"] != "iptal")


def kupon_olasilik(gun: dict, kupon: dict) -> float:
    return math.prod(s["adil_olasilik"] for s in kupon_ayaklari(gun, kupon) if s["durum"] != "iptal")


def kar(secim: dict) -> float:
    """Tekli oyunun kârı. Yeni günlerde oyunlar yalnızca kuponlarda oynanır (stake 0)."""
    return {"kazandi": secim["stake"] * (secim["oran"] - 1), "kaybetti": -secim["stake"]}.get(secim["durum"], 0.0)


def kupon_kar(gun: dict, kupon: dict) -> float:
    durum = kupon_durumu(gun, kupon)
    if durum == "tuttu":
        return kupon["stake"] * (kupon_oran(gun, kupon) - 1)
    return -kupon["stake"] if durum == "yatti" else 0.0


def gun_kar(gun: dict) -> float:
    return sum(kar(s) for s in gun["secimler"]) + sum(kupon_kar(gun, k) for k in kuponlar(gun))


def kasa(gunler: list[dict], baslangic: float) -> float:
    """Yayınlanmış ve sonuçlanmış oyunlara göre güncel kasa."""
    return baslangic + sum(gun_kar(g) for g in gunler if g.get("tweet_id"))


def acik_stake(gunler: list[dict]) -> float:
    """Paylaşılmış ama henüz sonuçlanmamış kuponlara yatırılan para (kasadan çıkmış sayılır)."""
    return sum(k["stake"] for g in gunler if g.get("tweet_id")
               for k in kuponlar(g) if kupon_durumu(g, k) is None)


def stakeler(gunler: list[dict], baslangic: float, yuzde: float, adet: int) -> list[float]:
    """Yeni kuponların her biri, o ana kadar ortaya konan paralar düşüldükten sonra kalan kasanın yüzdesiyle oynanır."""
    kalan = kasa(gunler, baslangic) - acik_stake(gunler)
    sonuc = []
    for _ in range(adet):
        sonuc.append(round(kalan * yuzde / 100, 2))
        kalan -= sonuc[-1]
    return sonuc


# Başlama + bu kadar dakika sonra maçın bitmiş olması beklenir (90 + devre arası + uzatmalar).
MAC_BITIS_DK = 110


def bekleyen_fixturelar(gunler: list[dict], simdi: datetime) -> list[int]:
    """Sonucu sorulacak maçlar: yayınlanmış günlerin, bitmiş olması gereken ve henüz sonuçlanmamış oyunları.
    Devam eden maçlar sorulmaz (günlük API hakkı boşa harcanmasın)."""
    return sorted({
        s["fixture_id"]
        for g in gunler if g["sonuc"] is None and g.get("tweet_id")
        for s in g["secimler"]
        if s["durum"] == "bekliyor"
        and _sorulmali(datetime.fromisoformat(s["baslama"]), simdi,
                       datetime.fromisoformat(s["son_sorgu"]) if s.get("son_sorgu") else None)
    })


def _sorulmali(baslama: datetime, simdi: datetime, son_sorgu: datetime | None = None) -> bool:
    """Bitişten sonra ilk kez hemen; başlamadan 3 saat sonrasına kadar her kontrolde; daha sonra
    (ertelenen/askıya alınan maç) son sorgudan en az 1 saat geçtiyse, hak boşa gitmesin."""
    gecen = simdi - baslama
    if gecen < timedelta(minutes=MAC_BITIS_DK):
        return False
    if son_sorgu is None or gecen < timedelta(hours=3):
        return True
    return simdi - son_sorgu >= timedelta(minutes=55)


def sorgulandi(gunler: list[dict], fixture_ids: list[int], simdi: datetime) -> None:
    """Sonucu sorulan (ama henüz bitmemiş) oyunlara sorgu zamanı yazılır."""
    ids = set(fixture_ids)
    for g in gunler:
        for s in g["secimler"]:
            if s["fixture_id"] in ids and s["durum"] == "bekliyor":
                s["son_sorgu"] = simdi.isoformat(timespec="seconds")


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
            for k in kuponlar(g):
                k["durum"] = kupon_durumu(g, k)
            biten.append(g)
    return biten


def ozet(gunler: list[dict], baslangic: float = 10000.0) -> dict:
    """Yalnızca X'te yayınlanmış oyunlar sayılır; taslaklar istatistiğe girmez."""
    yayinlanan = [g for g in gunler if g.get("tweet_id")]
    oyunlar = [s for g in yayinlanan for s in g["secimler"]]
    biten = [s for s in oyunlar if s["durum"] in ("kazandi", "kaybetti")]
    kazanan = [s for s in biten if s["durum"] == "kazandi"]
    kombiler = [kupon_durumu(g, k) for g in yayinlanan for k in kuponlar(g)]
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
    durumlar = [kupon_durumu(g, k) for g in hafta for k in kuponlar(g)]
    durumlar = [d for d in durumlar if d in ("tuttu", "yatti")]
    return {
        "baslangic": bas.isoformat(), "bitis": son.isoformat(),
        "gun": len(hafta), "oyun": len(biten), "kazanan": kazanan,
        "bekleyen": sum(s["durum"] == "bekliyor" for g in hafta for s in g["secimler"]), "kaybeden": len(biten) - kazanan,
        "isabet": 100 * kazanan / len(biten) if biten else 0.0,
        "kupon": len(durumlar), "kupon_tuttu": durumlar.count("tuttu"),
        "kar": sum(gun_kar(g) for g in hafta),
    }


def kasa_seyri(gunler: list[dict], baslangic: float, bitis: str | None = None) -> list[tuple[str, float]]:
    """(tarih, o günün sonundaki kasa): başlangıç noktası + sonuçlanmış her yayın günü."""
    gunler_ = sorted((g for g in gunler if g.get("tweet_id") and g["sonuc"] == "tamam"
                      and (bitis is None or g["tarih"] <= bitis)), key=lambda g: g["tarih"])
    if not gunler_:
        return []
    ilk = (datetime.fromisoformat(gunler_[0]["tarih"]) - timedelta(days=1)).date().isoformat()
    seyir, kasa_ = [(ilk, baslangic)], baslangic
    for g in gunler_:
        kasa_ += gun_kar(g)
        seyir.append((g["tarih"], round(kasa_, 2)))
    return seyir

