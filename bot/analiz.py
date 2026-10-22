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
# Her takım kendi kategorisinde ölçülür (SÖZLEŞME A4, 13 Ekim 2026): ev sahibi bu turnuvadaki iç saha, deplasman
# takımı dış saha maçlarıyla. API'nin "son 5 maç" verisi de aynı turnuvadan geldiği için yedek olarak kullanılmaz
# (13 Ekim: Şampiyonlar Ligi'nde 1–2 maçlık ortalama Man United'a %87 verdi, piyasa %26).
MIN_KATEGORI = 3
TOPLAM_GOL_ARALIGI = (1.0, 5.0)


def istatistik_modeli(ist: dict | None) -> tuple[tuple[float, float], str] | None:
    """Güvenilir takım istatistiği modeli: (beklenen goller, "lig"). İki takımın da bu turnuvada bu sezon en az
    MIN_MAC maçı, ev sahibinin en az MIN_KATEGORI iç saha, deplasman takımının en az MIN_KATEGORI dış saha maçı
    olmalı; ortalamalar bu kategorilerden. Yetmezse ya da toplam gol makul aralıkta değilse (veri hatası) None:
    kartta yüzde verilmez, nedeni yazılır."""
    if not ist or not model.veri_yeterli(ist):
        return None
    ev, dep = ist["ev"], ist["dep"]
    if min(ev["oynanan_ic"] + ev["oynanan_dis"], dep["oynanan_ic"] + dep["oynanan_dis"]) < MIN_MAC \
            or ev["oynanan_ic"] < MIN_KATEGORI or dep["oynanan_dis"] < MIN_KATEGORI:
        return None
    goller = ((ev["atilan_ic_ort"] + dep["yenilen_dis_ort"]) / 2, (dep["atilan_dis_ort"] + ev["yenilen_ic_ort"]) / 2)
    goller = tuple(round(g, 2) for g in goller)
    if not TOPLAM_GOL_ARALIGI[0] <= sum(goller) <= TOPLAM_GOL_ARALIGI[1] or min(goller) <= 0.2 or max(goller) >= 4.0:
        return None
    return goller, "lig"


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


def toplam_gol_dagilimi(a: dict, ust: int = 5) -> list[float]:
    """0, 1, …, ust-1 ve "ust+" toplam gol olasılıkları (aynı Poisson modeli: iki takımın golleri toplamı)."""
    lam = sum(a["beklenen_gol"])
    p = [model._poisson(k, lam) for k in range(ust)]
    return p + [max(0.0, 1 - sum(p))]


def istatistik_ms(a: dict) -> tuple[float, float, float] | None:
    """Takım istatistiğinin maç sonucu üçlüsü (kayıttaki karşılaştırmadan); üçü birden yoksa None."""
    k = {c["pazar"]: c["istatistik"] for c in a.get("karsilastirma") or []}
    return (k["MS1"], k["MSX"], k["MS2"]) if all(x in k for x in ("MS1", "MSX", "MS2")) else None


HIKAYE = {
    "en": {"ayri": ("The odds lean {o}{op}.", "Team stats lean {i}{ip}."),
           "fark": ("{ad}: odds {o}, team stats {i}.", "Same game, two different reads."),
           "favori": ("{t} {p} to win.", "{d} or a draw: {q}."), "acik": ("No result above {p}.", "Wide open on paper."),
           "gol": ("4+ goals: {p}.", "Expected goals {x} – {y}."),
           "skor": ("Most likely score: {s}.", "Even that is only {p}."),
           "pazar": {"UST25": "Over 2.5 goals", "KGVAR": "Both teams score",
                                                       "MS1": "{ev} win", "MS2": "{dep} win", "MSX": "Draw"}},
    "tr": {"ayri": ("Oranlar {o} diyor{op}.", "Takım istatistiği {i} diyor{ip}."),
           "fark": ("{ad}: oran {o}, takım istatistiği {i}.", "Aynı maç, iki farklı okuma."),
           "favori": ("{t} kazanır: {p}.", "{d} ya da beraberlik: {q}."), "acik": ("Hiçbir sonuç {p} üstünde değil.", "Kâğıt üstünde açık maç."),
           "gol": ("4 ve üstü gol: {p}.", "Beklenen gol {x} – {y}."),
           "skor": ("En olası skor: {s}.", "O bile yalnızca {p}."),
           "pazar": {"UST25": "2.5 üst", "KGVAR": "Karşılıklı gol",
                                                                        "MS1": "{ev} kazanır", "MS2": "{dep} kazanır", "MSX": "Beraberlik"}},
}


def hikaye(a: dict, dil: str = "en", yuzdeli: bool = True) -> tuple[str, str, str]:
    """Kartın ve postun ilk satırı: maçın tek cümlelik hikâyesi (tür, satır 1, satır 2). Bütün yüzdeler kayıttan
    (denetçi kayıtta olmayan yüzdeyi engeller); seçim ve kesinlik dili yok. Öncelik: oranla istatistiğin favorisi
    ayrışıyorsa o, sonra en büyük fark (eşiği geçiyorsa), sonra güçlü favori, gollü maç, açık maç, en olası skor.
    yuzdeli=False: karttaki çubuklar yüzdeyi zaten gösterdiği için "ayri" türünde yüzde yazılmaz."""
    e, p = HIKAYE[dil], a["p"]
    y = (lambda x: f"%{100 * x:.0f}") if dil == "tr" else (lambda x: f"{100 * x:.0f}%")
    takim = {"MS1": a["ev"], "MS2": a["dep"]}
    ist = istatistik_ms(a)
    if ist:
        fav_o = "MS1" if p["MS1"] >= p["MS2"] else "MS2"
        fav_i = "MS1" if ist[0] >= ist[2] else "MS2"
        if fav_o != fav_i and abs(ist[0] - ist[2]) >= 0.05 and abs(p["MS1"] - p["MS2"]) >= 0.05:
            ip = ist[0] if fav_i == "MS1" else ist[2]
            op, ip = (f" ({y(p[fav_o])})", f" ({y(ip)})") if yuzdeli else ("", "")
            return "ayri", e["ayri"][0].format(o=takim[fav_o], op=op), e["ayri"][1].format(i=takim[fav_i], ip=ip)
    c = dikkat_cekici(a)
    if c:
        ad = e["pazar"][c["pazar"]].format(ev=a["ev"], dep=a["dep"])
        return "fark", e["fark"][0].format(ad=ad, o=y(c["piyasa"]), i=y(c["istatistik"])), e["fark"][1]
    fav = max(("MS1", "MS2"), key=lambda k: p[k])
    if p[fav] >= 0.62:
        diger, cs = ("MS2", "CSX2") if fav == "MS1" else ("MS1", "CS1X")
        return "favori", e["favori"][0].format(t=takim[fav], p=y(p[fav])), e["favori"][1].format(d=takim[diger], q=y(p[cs]))
    if p["UST25"] >= 0.62 and p["KGVAR"] >= 0.55:
        x, z = a["beklenen_gol"]
        return "gol", e["gol"][0].format(p=y(p["UST35"])), e["gol"][1].format(x=f"{x:.1f}", y=f"{z:.1f}")
    en = max(p["MS1"], p["MSX"], p["MS2"])
    if en < 0.42:
        return "acik", e["acik"][0].format(p=y(en)), e["acik"][1]
    s, v = a["skorlar"][0]
    return "skor", e["skor"][0].format(s=s), e["skor"][1].format(p=y(v))


def manset(a: dict) -> list[dict]:
    """Kartın üç ana çağrısı: maç sonucu favorisi, 2.5 alt/üst, karşılıklı gol var/yok (olası taraf)."""
    p = a["p"]
    fav = max(("MS1", "MSX", "MS2"), key=lambda k: p[k])
    ad = {"MS1": f'{a["ev"]} win', "MSX": "Draw", "MS2": f'{a["dep"]} win'}[fav]
    gol = ("UST25", "Over 2.5 goals") if p["UST25"] >= 0.5 else ("ALT25", "Under 2.5 goals")
    kg = ("KGVAR", "Both teams score") if p["KGVAR"] >= 0.5 else ("KGYOK", "Not both teams score")
    return [{"pazar": fav, "ad": ad, "p": p[fav]}, {"pazar": gol[0], "ad": gol[1], "p": p[gol[0]]},
            {"pazar": kg[0], "ad": kg[1], "p": p[kg[0]]}]


# SÖZLEŞME B6: herkesin takip ettiği turnuvalar (API-Football lig kimlikleri). Bu liglerin her maçı "büyük maç".
ONEMLI_LIGLER = {
    1, 4, 5, 6, 9, 10,          # Dünya Kupası, Avrupa Şampiyonası, Uluslar Ligi, Afrika Kupası, Copa América, hazırlık
    29, 30, 31, 32, 33, 34,     # Dünya Kupası elemeleri (Afrika, Asya, CONCACAF, Avrupa, Okyanusya, Güney Amerika)
    960,                        # Avrupa Şampiyonası elemeleri
    2, 3, 848, 531,             # Şampiyonlar Ligi, Avrupa Ligi, Konferans Ligi, Süper Kupa
    39, 140, 135, 78, 61, 203,  # Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Süper Lig
}


def onemli(a: dict) -> bool:
    """Geniş kitlenin ilgilendiği maç: büyük turnuva/lig (Uluslar Ligi, Avrupa kupaları, büyük 5 lig, Süper Lig...)
    ya da taraftar etiketi olan milli takım veya bilinen büyük kulüp."""
    from .tweets import KULUP_ETIKETLERI, MILLI_ETIKETLER
    return a.get("lig_id") in ONEMLI_LIGLER or any(
        t.lower().strip() in MILLI_ETIKETLER or t.lower().strip() in KULUP_ETIKETLERI for t in (a["ev"], a["dep"]))


def ayrisiyor(a: dict) -> bool:
    """Oranla takım istatistiği ayrışıyor (kartın en güçlü hikâyesi): günlük kart sınırı dolarken önce bunlar (B6)."""
    return hikaye(a)[0] in ("ayri", "fark")


def one_cikanlar(analizler: list[dict], izinli: list[int], adet: int = 5) -> list[dict]:
    """X'te paylaşılacak maçlar: önce günün önemli maçları (Türkiye, büyük milli takımlar ve kulüpler), sonra izinli
    (büyük) ligler ve veri güveni yüksek olanlar; aynı saate yığılmasın diye farklı başlama saatleri tercih edilir."""
    sira = {lig: i for i, lig in enumerate(izinli)}
    puan = {"yuksek": 0, "orta": 1, "dusuk": 2}
    aday = sorted((a for a in analizler if (a.get("lig_id") in sira or onemli(a)) and a["guven"] != "dusuk"
                   and _gecerli(a)),
                  key=lambda a: (not onemli(a), not ayrisiyor(a), puan[a["guven"]], sira.get(a.get("lig_id"), 99),
                                 a["baslama"]))
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


def ek_kart_secimi(analizler: list[dict], izinli: list[int], ek_ligler, haric: set, en_erken: str,
                   adet: int) -> list[dict]:
    """Yoğun gün: henüz kartı olmayan, en_erken'den sonra başlayan maçlardan önemli maçlar, büyük ligler ve ek
    ligler (veri güveni yüksek/orta); yalnızca ek liglerde lig başına en fazla 2; saat sırasıyla. Alt ligler
    (ör. 4. lig) kart almaz: maç iyi olmalı."""
    sira = {lig: i for i, lig in enumerate(list(izinli) + list(ek_ligler))}
    aday = [a for a in analizler if a["fixture_id"] not in haric and _gecerli(a) and a["guven"] != "dusuk"
            and (a.get("lig_id") in sira or onemli(a))
            and datetime.fromisoformat(a["baslama"]) > datetime.fromisoformat(en_erken)]
    aday.sort(key=lambda a: (not onemli(a), not ayrisiyor(a), sira.get(a.get("lig_id"), 999), a["baslama"]))
    secilen, sayac = [], {}
    for a in aday:  # büyük ve izinli liglerde lig sınırı yok (SÖZLEŞME B6); ek liglerde en fazla 2
        if len(secilen) < adet and (onemli(a) or a.get("lig_id") in izinli or sayac.get(a["lig"], 0) < 2):
            secilen.append(a)
            sayac[a["lig"]] = sayac.get(a["lig"], 0) + 1
    return sorted(secilen, key=lambda a: a["baslama"])


def _gecerli(a: dict) -> bool:
    """Takım adı bozuk kayıtlar (ör. "Team") tabloya ve öne çıkanlara girmez."""
    return all(len(t.strip()) > 2 and t.strip().lower() != "team" for t in (a["ev"], a["dep"]))


def tablo_secimi(analizler: list[dict], izinli: list[int] = (), adet: int = 15, lig_basina: int = 2,
                 en_erken: str | None = None, haric: set = frozenset()) -> list[dict]:
    """Günün analiz tablosu (en fazla 15 maç): önce günün büyük maçları, sonra izinli ligler (ikisinde de lig sınırı yok;
    ölçüt veri güveni), alt ligler yalnızca tablo 6 maçtan azsa ve lig başına en fazla 2; paylaşım saatinden sonra."""
    puan = {"yuksek": 0, "orta": 1}
    sira = {lig: i for i, lig in enumerate(izinli)}
    aday = [a for a in analizler if a["guven"] in puan and _gecerli(a) and a["fixture_id"] not in haric
            and (en_erken is None or datetime.fromisoformat(a["baslama"]) > datetime.fromisoformat(en_erken))]
    aday.sort(key=lambda a: (not onemli(a), a.get("lig_id") not in sira, sira.get(a.get("lig_id"), 0),
                             puan[a["guven"]], a["baslama"]))  # önce günün önemli maçları
    secilen, sayac = [], {}
    for a in aday:  # büyük ve izinli liglerde lig sınırı yok, ölçüt maçın kalitesi (SÖZLEŞME B6); alt ligler yer kalırsa
        alt = not onemli(a) and a.get("lig_id") not in sira
        if len(secilen) < adet and (not alt or sayac.get(a["lig"], 0) < lig_basina) and not (alt and len(secilen) >= 6):
            secilen.append(a)
            sayac[a["lig"]] = sayac.get(a["lig"], 0) + 1
    return sorted(secilen, key=lambda a: a["baslama"])


def kiyas_secimi(analizler: list[dict], izinli: list[int] = (), adet: int = 10, lig_basina: int = 3,
                 en_erken: str | None = None) -> list[dict]:
    """İkinci tablo (oran ve takım istatistiği yan yana): istatistiği olan maçlardan önce günün önemli maçları,
    sonra büyük (izinli) ligler, sonra en çok ayrışanlar; yalnızca alt liglerde lig başına en fazla 3; saat sırasıyla."""
    sira = {lig: i for i, lig in enumerate(izinli)}
    aday = [a for a in analizler if a.get("karsilastirma") and a["guven"] in ("yuksek", "orta") and _gecerli(a)
            and (en_erken is None or datetime.fromisoformat(a["baslama"]) > datetime.fromisoformat(en_erken))]
    aday.sort(key=lambda a: (not onemli(a), a.get("lig_id") not in sira, -abs(fark_puani(a["karsilastirma"][0]))))
    secilen, sayac = [], {}
    for a in aday:  # büyük ve izinli liglerde lig sınırı yok, ölçüt maçın kalitesi (SÖZLEŞME B6); alt ligler yer kalırsa
        alt = not onemli(a) and a.get("lig_id") not in sira
        if len(secilen) < adet and (not alt or sayac.get(a["lig"], 0) < lig_basina) and not (alt and len(secilen) >= 6):
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
                                                       "istatistik_kaynak", "odds_id", "odds_spor") if k in a}
