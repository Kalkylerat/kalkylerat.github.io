"""Analiz konsepti: kupon yok. Her gün taranan maçların her biri için olasılık analizi.

Beklenen goller önce piyasadan (keskin bahisçinin marjsız ihtimallerine en iyi uyan Poisson golleri), piyasa yoksa
takım istatistiklerinden hesaplanır; bütün pazarlar ve skor dağılımı aynı Poisson modelinden gelir, yani kartta
birbiriyle çelişen rakam olmaz. Veri güveni: piyasa + keskin bahisçi = yüksek, yalnızca piyasa = orta,
yalnızca istatistik = düşük. Verisi yetmeyen maç analiz edilmez (uydurma analiz yok)."""

from datetime import datetime

from . import model
from .oddsapi import ima_edilen_goller

# Piyasa ile takım istatistiklerinin karşılaştırıldığı pazarlar; bu kadar puan fark "dikkat çekici" sayılır.
KARSILASTIRMA = (("MS1", "{ev} win"), ("MSX", "Draw"), ("MS2", "{dep} win"), ("UST25", "Over 2.5 goals"), ("KGVAR", "Both teams score"))
FARK_ESIGI = 0.10
# Takım istatistiği modeli ancak bu kadar maçlık örneklemle güvenilir (Uluslar Ligi gibi turnuvalarda 1–3 maçlık
# ortalama gürültüdür); toplam beklenen gol de makul aralıkta olmalı (0,25 + 0,25 gibi uç değerler veri hatasıdır).
MIN_MAC = 5
TOPLAM_GOL_ARALIGI = (1.0, 5.0)


def istatistik_modeli(ist: dict | None) -> tuple[tuple[float, float], str] | None:
    """Güvenilir takım istatistiği modeli: (beklenen goller, kaynak). Kaynak "lig": iki takımın da bu ligde en az
    MIN_MAC maçı var, iç saha/deplasman ortalamaları. Yoksa "son5": son 5 maçın (milli takımlarda turnuva
    örneklemi küçük) attığı/yediği gol ortalaması. Toplam gol makul aralıkta değilse None (veri hatası)."""
    if not ist or not model.veri_yeterli(ist):
        return None
    ev, dep = ist["ev"], ist["dep"]
    if min(ev["oynanan_ic"] + ev["oynanan_dis"], dep["oynanan_ic"] + dep["oynanan_dis"]) >= MIN_MAC:
        goller, kaynak = model.beklenen_goller(ist), "lig"
    elif all(t["son5_atilan_ort"] + t["son5_yenilen_ort"] > 0 for t in (ev, dep)):
        goller = ((ev["son5_atilan_ort"] + dep["son5_yenilen_ort"]) / 2, (dep["son5_atilan_ort"] + ev["son5_yenilen_ort"]) / 2)
        kaynak = "son5"
    else:
        return None
    goller = tuple(round(g, 2) for g in goller)
    if not TOPLAM_GOL_ARALIGI[0] <= sum(goller) <= TOPLAM_GOL_ARALIGI[1] or min(goller) <= 0.2 or max(goller) >= 4.0:
        return None
    return goller, kaynak


def istatistik_golleri(ist: dict | None) -> tuple[float, float] | None:
    """Güvenilir takım istatistiği modeli varsa beklenen goller; yoksa None."""
    sonuc = istatistik_modeli(ist)
    return sonuc[0] if sonuc else None


def _skorlar(le: float, ld: float, adet: int = 5) -> list[tuple[str, float]]:
    dagilim: dict[str, float] = {}
    for _, (e, d), p in model._skor_dagilimi(le, ld):
        dagilim[f"{e}-{d}"] = dagilim.get(f"{e}-{d}", 0.0) + p
    return [(s, round(p, 4)) for s, p in sorted(dagilim.items(), key=lambda x: -x[1])[:adet]]


def mac_analizi(m: dict, bahisciler: dict | None, ist: dict | None, ayar) -> dict | None:
    """Ana rakamlar piyasadan (daha bilgili: sakatlık, kadro, haber fiyata yansır), yoksa istatistikten. İkisi de
    varsa ayrıca takım istatistiği modeli hesaplanır ve piyasayla karşılaştırılır (en büyük farklar önce)."""
    piyasa_gol = istat_gol = None
    guven = None
    if bahisciler:
        adil, _ = model.adil_olasiliklar(bahisciler, ayar.keskin_bahisci)
        piyasa_gol = ima_edilen_goller(adil)
        if piyasa_gol:
            keskin = any(x.lower() == ayar.keskin_bahisci.lower() for x in bahisciler)
            guven = "yuksek" if keskin and "UST25" in adil else "orta"
    istat = istatistik_modeli(ist)
    istat_gol, istat_kaynak = istat or (None, None)
    goller = piyasa_gol or istat_gol
    if goller is None:
        return None
    guven = guven or "dusuk"
    le, ld = round(goller[0], 2), round(goller[1], 2)
    p = {k: round(v, 3) for k, v in model.model_olasiliklari(le, ld).items()}
    karsilastirma = []
    if piyasa_gol and istat_gol:
        pi = model.model_olasiliklari(*istat_gol)
        karsilastirma = sorted(({"pazar": k, "ad": ad.format(ev=m["ev"], dep=m["dep"]), "piyasa": p[k],
                                 "istatistik": round(pi[k], 3)} for k, ad in KARSILASTIRMA),
                               key=lambda c: -abs(fark_puani(c)))
    return {"fixture_id": m["fixture_id"], "lig": m.get("lig", ""), "ulke": m.get("ulke", ""), "lig_id": m.get("lig_id"),
            "ev": m["ev"], "dep": m["dep"], "baslama": m["baslama"], "beklenen_gol": [le, ld], "p": p,
            "skorlar": _skorlar(le, ld), "guven": guven, "kaynak": "piyasa" if piyasa_gol else "istatistik",
            "istatistik_gol": list(istat_gol) if istat_gol else None, "istatistik_kaynak": istat_kaynak,
            "karsilastirma": karsilastirma,
            **{k: m[k] for k in ("odds_id", "odds_spor") if k in m}}


def fark_puani(c: dict) -> int:
    """Ekranda görünen (yuvarlanmış) yüzdeler arasındaki fark: vurgu kararı okuyucunun gördüğüyle aynı olsun."""
    return round(100 * c["istatistik"]) - round(100 * c["piyasa"])


def dikkat_cekici(a: dict) -> dict | None:
    """Takım istatistiklerinin piyasadan en çok ayrıştığı pazar (eşiği geçiyorsa)."""
    c = (a.get("karsilastirma") or [None])[0]
    return c if c and abs(fark_puani(c)) >= round(100 * FARK_ESIGI) else None


def manset(a: dict) -> list[dict]:
    """Kartın üç ana çağrısı: maç sonucu favorisi, 2.5 alt/üst, karşılıklı gol var/yok (olası taraf)."""
    p = a["p"]
    fav = max(("MS1", "MSX", "MS2"), key=lambda k: p[k])
    ad = {"MS1": f'{a["ev"]} win', "MSX": "Draw", "MS2": f'{a["dep"]} win'}[fav]
    gol = ("UST25", "Over 2.5 goals") if p["UST25"] >= 0.5 else ("ALT25", "Under 2.5 goals")
    kg = ("KGVAR", "Both teams score") if p["KGVAR"] >= 0.5 else ("KGYOK", "Not both teams score")
    return [{"pazar": fav, "ad": ad, "p": p[fav]}, {"pazar": gol[0], "ad": gol[1], "p": p[gol[0]]},
            {"pazar": kg[0], "ad": kg[1], "p": p[kg[0]]}]


def onemli(a: dict) -> bool:
    """Geniş kitlenin ilgilendiği maç: taraftar etiketi olan milli takım ya da bilinen büyük kulüp (ör. Türkiye)."""
    from .tweets import KULUP_ETIKETLERI, MILLI_ETIKETLER
    return any(t.lower().strip() in MILLI_ETIKETLER or t.lower().strip() in KULUP_ETIKETLERI for t in (a["ev"], a["dep"]))


def one_cikanlar(analizler: list[dict], izinli: list[int], adet: int = 5) -> list[dict]:
    """X'te paylaşılacak maçlar: önce günün önemli maçları (Türkiye, büyük milli takımlar ve kulüpler), sonra izinli
    (büyük) ligler ve veri güveni yüksek olanlar; aynı saate yığılmasın diye farklı başlama saatleri tercih edilir."""
    sira = {lig: i for i, lig in enumerate(izinli)}
    puan = {"yuksek": 0, "orta": 1, "dusuk": 2}
    aday = sorted((a for a in analizler if (a.get("lig_id") in sira or onemli(a)) and a["guven"] != "dusuk"
                   and _gecerli(a)),
                  key=lambda a: (not onemli(a), puan[a["guven"]], sira.get(a.get("lig_id"), 99), a["baslama"]))
    secilen: list[dict] = [a for a in aday if onemli(a)][:adet]  # önemli maçlar saat çakışsa da girer
    for a in aday:  # sonra farklı saatler
        if len(secilen) < adet and all(abs((datetime.fromisoformat(a["baslama"]) -
                                            datetime.fromisoformat(s["baslama"])).total_seconds()) >= 3600
                                       for s in secilen):
            secilen.append(a)
    for a in aday:
        if len(secilen) < adet and a not in secilen:
            secilen.append(a)
    return sorted(secilen, key=lambda a: a["baslama"])


def _gecerli(a: dict) -> bool:
    """Takım adı bozuk kayıtlar (ör. "Team") tabloya ve öne çıkanlara girmez."""
    return all(len(t.strip()) > 2 and t.strip().lower() != "team" for t in (a["ev"], a["dep"]))


def tablo_secimi(analizler: list[dict], izinli: list[int] = (), adet: int = 10, lig_basina: int = 2,
                 en_erken: str | None = None, haric: set = frozenset()) -> list[dict]:
    """Günün analiz tablosu: önce büyük (izinli) liglerin maçları, sonra alt ligler; veri güveni yüksek/orta;
    lig başına en fazla 2 maç; tablonun paylaşılacağı saatten sonra başlayanlar; saat sırasıyla."""
    puan = {"yuksek": 0, "orta": 1}
    sira = {lig: i for i, lig in enumerate(izinli)}
    aday = [a for a in analizler if a["guven"] in puan and _gecerli(a) and a["fixture_id"] not in haric
            and (en_erken is None or datetime.fromisoformat(a["baslama"]) > datetime.fromisoformat(en_erken))]
    aday.sort(key=lambda a: (not onemli(a), a.get("lig_id") not in sira, sira.get(a.get("lig_id"), 0),
                             puan[a["guven"]], a["baslama"]))  # önce günün önemli maçları
    secilen, sayac = [], {}
    for a in aday:
        if len(secilen) < adet and sayac.get(a["lig"], 0) < lig_basina:
            secilen.append(a)
            sayac[a["lig"]] = sayac.get(a["lig"], 0) + 1
    return sorted(secilen, key=lambda a: a["baslama"])


def kiyas_secimi(analizler: list[dict], izinli: list[int] = (), adet: int = 10, lig_basina: int = 3,
                 en_erken: str | None = None) -> list[dict]:
    """İkinci tablo (oran ve takım istatistiği yan yana): istatistiği olan maçlardan önce günün önemli maçları,
    sonra büyük (izinli) ligler, sonra en çok ayrışanlar; lig başına en fazla 3; saat sırasıyla."""
    sira = {lig: i for i, lig in enumerate(izinli)}
    aday = [a for a in analizler if a.get("karsilastirma") and a["guven"] in ("yuksek", "orta") and _gecerli(a)
            and (en_erken is None or datetime.fromisoformat(a["baslama"]) > datetime.fromisoformat(en_erken))]
    aday.sort(key=lambda a: (not onemli(a), a.get("lig_id") not in sira, -abs(fark_puani(a["karsilastirma"][0]))))
    secilen, sayac = [], {}
    for a in aday:
        if len(secilen) < adet and sayac.get(a["lig"], 0) < lig_basina:
            secilen.append(a)
            sayac[a["lig"]] = sayac.get(a["lig"], 0) + 1
    return sorted(secilen, key=lambda a: a["baslama"])


def ayrisma_secimi(analizler: list[dict], adet: int = 3) -> list[dict]:
    """Takım istatistiklerinin piyasadan en çok ayrıştığı maçlar (güvenilir piyasa ve istatistik olanlar)."""
    aday = [a for a in analizler if a["guven"] in ("yuksek", "orta") and dikkat_cekici(a) and _gecerli(a)]
    return sorted(aday, key=lambda a: -abs(fark_puani(dikkat_cekici(a))))[:adet]


def ozet(a: dict) -> dict:
    """Kayıtta saklanacak kısa hali (tablo ve ayrışma postları için)."""
    return {k: a[k] for k in ("fixture_id", "lig", "ulke", "lig_id", "ev", "dep", "baslama", "p", "skorlar", "guven",
                              "karsilastirma", "beklenen_gol", "kaynak",
                                                       "istatistik_kaynak") if k in a}
