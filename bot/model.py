"""Değer (value) tespiti: keskin piyasanın adil olasılığı × İsveç lisanslı bahisçideki en iyi oran.
Poisson gol modeli yalnızca güvenlik kontrolü olarak kullanılır."""

import math

ETIKET = {
    "MS1": "1 (hemmaseger)", "MSX": "X (oavgjort)", "MS2": "2 (bortaseger)",
    "CS1X": "1X", "CSX2": "X2", "CS12": "12",
    "UST25": "Över 2,5 mål", "ALT25": "Under 2,5 mål",
    "KGVAR": "Båda lagen gör mål", "KGYOK": "Inte båda lagen gör mål",
}

KISA = {
    "MS1": "1", "MSX": "X", "MS2": "2", "CS1X": "1X", "CSX2": "X2", "CS12": "12",
    "UST25": "Över 2,5", "ALT25": "Under 2,5", "KGVAR": "BLGM Ja", "KGYOK": "BLGM Nej",
}

MAX_GOL = 10
UC_YOLLU = ("MS1", "MSX", "MS2")


def kazandi_mi(pazar: str, ev: int, dep: int) -> bool:
    return {
        "MS1": ev > dep, "MSX": ev == dep, "MS2": dep > ev,
        "CS1X": ev >= dep, "CSX2": dep >= ev, "CS12": ev != dep,
        "UST25": ev + dep > 2.5, "ALT25": ev + dep < 2.5,
        "KGVAR": ev > 0 and dep > 0, "KGYOK": ev == 0 or dep == 0,
    }[pazar]


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def beklenen_goller(ist: dict) -> tuple[float, float]:
    ev, dep = ist["ev"], ist["dep"]
    if ev["oynanan_ic"] >= 3 and dep["oynanan_dis"] >= 3:
        lam_ev = (ev["atilan_ic_ort"] + dep["yenilen_dis_ort"]) / 2
        lam_dep = (dep["atilan_dis_ort"] + ev["yenilen_ic_ort"]) / 2
    else:
        lam_ev = (ev["son5_atilan_ort"] + dep["son5_yenilen_ort"]) / 2
        lam_dep = (dep["son5_atilan_ort"] + ev["son5_yenilen_ort"]) / 2
    kirp = lambda x: min(max(x, 0.2), 4.0)
    return kirp(lam_ev), kirp(lam_dep)


def model_olasiliklari(lam_ev: float, lam_dep: float) -> dict[str, float]:
    p = {k: 0.0 for k in ETIKET}
    for i in range(MAX_GOL + 1):
        for j in range(MAX_GOL + 1):
            olas = _poisson(i, lam_ev) * _poisson(j, lam_dep)
            for pazar in p:
                if kazandi_mi(pazar, i, j):
                    p[pazar] += olas
    return p


def piyasa_olasiliklari(oranlar: dict[str, float]) -> dict[str, float]:
    """Bir bahisçinin oranlarından marjı gruplar içinde normalize ederek adil olasılık çıkarır."""
    adil: dict[str, float] = {}
    for grup in (UC_YOLLU, ("UST25", "ALT25"), ("KGVAR", "KGYOK")):
        if all(k in oranlar for k in grup):
            ters = {k: 1 / oranlar[k] for k in grup}
            toplam = sum(ters.values())
            adil.update({k: v / toplam for k, v in ters.items()})
    if all(k in adil for k in UC_YOLLU):
        adil["CS1X"] = adil["MS1"] + adil["MSX"]
        adil["CSX2"] = adil["MSX"] + adil["MS2"]
        adil["CS12"] = adil["MS1"] + adil["MS2"]
    return adil


def adil_olasiliklar(bahisciler: dict[str, dict[str, float]], keskin: str) -> tuple[dict[str, float], dict[str, str]]:
    """Her pazar için keskin bahisçiyi, yoksa tüm bahisçilerin ortalamasını kullanır. (olasılık, kaynak) döner."""
    keskin_ad = next((ad for ad in bahisciler if ad.lower() == keskin.lower()), None)
    keskin_p = piyasa_olasiliklari(bahisciler[keskin_ad]) if keskin_ad else {}
    tum = [piyasa_olasiliklari(o) for o in bahisciler.values()]
    adil, kaynak = {}, {}
    for pazar in ETIKET:
        if pazar in keskin_p:
            adil[pazar], kaynak[pazar] = keskin_p[pazar], keskin_ad
        else:
            degerler = [p[pazar] for p in tum if pazar in p]
            if len(degerler) >= 3:
                adil[pazar], kaynak[pazar] = sum(degerler) / len(degerler), f"ortalama ({len(degerler)})"
    return adil, kaynak


def en_iyi_oranlar(bahisciler: dict[str, dict[str, float]], izinli: list[str]) -> dict[str, tuple[float, str]]:
    izin = {ad.lower() for ad in izinli}
    en_iyi: dict[str, tuple[float, str]] = {}
    for ad, oranlar in bahisciler.items():
        if ad.lower() not in izin:
            continue
        for pazar, oran in oranlar.items():
            if pazar not in en_iyi or oran > en_iyi[pazar][0]:
                en_iyi[pazar] = (oran, ad)
    return en_iyi


def adaylari_uret(mac: dict, bahisciler: dict[str, dict[str, float]], ist: dict, ayar) -> list[dict]:
    adil, kaynak = adil_olasiliklar(bahisciler, ayar.keskin_bahisci)
    lam_ev, lam_dep = beklenen_goller(ist)
    model = model_olasiliklari(lam_ev, lam_dep)
    adaylar = []
    for pazar, (oran, bolag) in en_iyi_oranlar(bahisciler, ayar.isvec_bahisciler).items():
        if pazar not in adil or not (ayar.oran_min <= oran <= ayar.oran_max):
            continue
        p = adil[pazar]
        deger = p * oran - 1
        if p < ayar.min_olasilik or deger < ayar.min_deger or model[pazar] < p - ayar.model_tolerans:
            continue
        adaylar.append({
            "aday_id": f'{mac["fixture_id"]}-{pazar}',
            "fixture_id": mac["fixture_id"],
            "pazar": pazar,
            "etiket": ETIKET[pazar],
            "kisa": KISA[pazar],
            "oran": oran,
            "bolag": bolag,
            "adil_olasilik": round(p, 3),
            "adil_oran": round(1 / p, 2),
            "adil_kaynak": kaynak[pazar],
            "model_olasilik": round(model[pazar], 3),
            "deger": round(deger, 3),
            "beklenen_gol": [round(lam_ev, 2), round(lam_dep, 2)],
        })
    adaylar.sort(key=lambda a: a["deger"], reverse=True)
    return adaylar[:2]
