"""Analiz konsepti: kupon yok. Her gün taranan maçların her biri için olasılık analizi.

Beklenen goller önce piyasadan (keskin bahisçinin marjsız ihtimallerine en iyi uyan Poisson golleri), piyasa yoksa
takım istatistiklerinden hesaplanır; bütün pazarlar ve skor dağılımı aynı Poisson modelinden gelir, yani kartta
birbiriyle çelişen rakam olmaz. Veri güveni: piyasa + keskin bahisçi = yüksek, yalnızca piyasa = orta,
yalnızca istatistik = düşük. Verisi yetmeyen maç analiz edilmez (uydurma analiz yok)."""

from datetime import datetime

from . import model
from .oddsapi import ima_edilen_goller

# Kartın manşetindeki üç çağrı (maç sonu bunlar tutup tutmadı diye takip edilir).
MANSET = ("1x2", "gol", "kg")


def _skorlar(le: float, ld: float, adet: int = 5) -> list[tuple[str, float]]:
    dagilim: dict[str, float] = {}
    for _, (e, d), p in model._skor_dagilimi(le, ld):
        dagilim[f"{e}-{d}"] = dagilim.get(f"{e}-{d}", 0.0) + p
    return [(s, round(p, 4)) for s, p in sorted(dagilim.items(), key=lambda x: -x[1])[:adet]]


def mac_analizi(m: dict, bahisciler: dict | None, ist: dict | None, ayar) -> dict | None:
    goller, guven = None, None
    if bahisciler:
        adil, _ = model.adil_olasiliklar(bahisciler, ayar.keskin_bahisci)
        goller = ima_edilen_goller(adil)
        if goller:
            keskin = any(a.lower() == ayar.keskin_bahisci.lower() for a in bahisciler)
            guven = "yuksek" if keskin and "UST25" in adil else "orta"
    if goller is None and ist and model.veri_yeterli(ist):
        goller, guven = model.beklenen_goller(ist), "dusuk"
    if goller is None:
        return None
    le, ld = round(goller[0], 2), round(goller[1], 2)
    p = {k: round(v, 3) for k, v in model.model_olasiliklari(le, ld).items()}
    return {"fixture_id": m["fixture_id"], "lig": m.get("lig", ""), "ulke": m.get("ulke", ""), "lig_id": m.get("lig_id"),
            "ev": m["ev"], "dep": m["dep"], "baslama": m["baslama"], "beklenen_gol": [le, ld], "p": p,
            "skorlar": _skorlar(le, ld), "guven": guven,
            **{k: m[k] for k in ("odds_id", "odds_spor") if k in m}}


def manset(a: dict) -> list[dict]:
    """Kartın üç ana çağrısı: maç sonucu favorisi, 2.5 alt/üst, karşılıklı gol var/yok (olası taraf)."""
    p = a["p"]
    fav = max(("MS1", "MSX", "MS2"), key=lambda k: p[k])
    ad = {"MS1": f'{a["ev"]} win', "MSX": "Draw", "MS2": f'{a["dep"]} win'}[fav]
    gol = ("UST25", "Over 2.5 goals") if p["UST25"] >= 0.5 else ("ALT25", "Under 2.5 goals")
    kg = ("KGVAR", "Both teams score") if p["KGVAR"] >= 0.5 else ("KGYOK", "Not both teams score")
    return [{"pazar": fav, "ad": ad, "p": p[fav]}, {"pazar": gol[0], "ad": gol[1], "p": p[gol[0]]},
            {"pazar": kg[0], "ad": kg[1], "p": p[kg[0]]}]


def one_cikanlar(analizler: list[dict], izinli: list[int], adet: int = 3) -> list[dict]:
    """X'te paylaşılacak maçlar: önce izinli (büyük) ligler, veri güveni yüksek olanlar; aynı saate yığılmasın diye
    farklı başlama saatleri tercih edilir."""
    sira = {lig: i for i, lig in enumerate(izinli)}
    puan = {"yuksek": 0, "orta": 1, "dusuk": 2}
    aday = sorted((a for a in analizler if a.get("lig_id") in sira and a["guven"] != "dusuk"),
                  key=lambda a: (puan[a["guven"]], sira[a["lig_id"]], a["baslama"]))
    secilen: list[dict] = []
    for a in aday:  # önce farklı saatler
        if len(secilen) < adet and all(abs((datetime.fromisoformat(a["baslama"]) -
                                            datetime.fromisoformat(s["baslama"])).total_seconds()) >= 3600
                                       for s in secilen):
            secilen.append(a)
    for a in aday:
        if len(secilen) < adet and a not in secilen:
            secilen.append(a)
    return sorted(secilen, key=lambda a: a["baslama"])
