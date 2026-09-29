"""Olasılık motoru: keskin piyasanın (Pinnacle) marjı arındırılmış adil olasılığı, büyük bahisçilerdeki en iyi oran
(listedeki bahisçilerin medyan oranı) ve Poisson gol modeli. Adaylar iki türdür: "guvenli" (yüksek ihtimal) ve "deger" (oran gerçek ihtimalden yüksek)."""

import math
import statistics

MAX_GOL = 10
IY_ORANI = 0.45  # maçtaki gollerin yaklaşık %45'i ilk yarıda atılır

UC_YOLLU = (("MS1", "MSX", "MS2"), ("IY1", "IYX", "IY2"))
IKILI_ONEK = (("UST", "ALT"), ("IYU", "IYA"), ("KORU", "KORA"))
TAM_MAC = ("MS1", "MSX", "MS2", "CS1X", "CSX2", "CS12", "KGVAR", "KGYOK",
           "UST15", "ALT15", "UST25", "ALT25", "UST35", "ALT35")
ILK_YARI = ("IY1", "IYX", "IY2", "IYU05", "IYA05", "IYU15", "IYA15")


def cizgi(pazar: str) -> float:
    """UST25 -> 2.5, IYU05 -> 0.5, KORU95 -> 9.5"""
    return int("".join(c for c in pazar if c.isdigit())) / 10


def etiketler(pazar: str, ev: str, dep: str) -> tuple[str, str]:
    """(etiket, kısa) bahis sitelerindeki standart İngilizce ifade; açıklama eklenmez, herkes bu dili bilir."""
    sabit = {
        "MS1": f"{ev} to win", "MSX": "Draw", "MS2": f"{dep} to win",
        "CS1X": "Double chance 1X", "CSX2": "Double chance X2", "CS12": "Double chance 12",
        "KGVAR": "Both teams to score", "KGYOK": "Both teams to score: No",
        "IY1": f"1st half: {ev} to win", "IYX": "1st half: Draw", "IY2": f"1st half: {dep} to win",
    }
    if pazar in sabit:
        return sabit[pazar], sabit[pazar]
    c = cizgi(pazar)
    on_ek = {"IYU": "1st half Over", "IYA": "1st half Under", "KORU": "Over", "KORA": "Under",
             "UST": "Over", "ALT": "Under"}
    kod = next(k for k in on_ek if pazar.startswith(k))
    metin = f'{on_ek[kod]} {c} {"corners" if kod.startswith("KOR") else "goals"}'
    return metin, metin


def kazandi_mi(pazar: str, ev: int, dep: int, iy: tuple[int, int] | None = None,
               korner: int | None = None) -> bool | None:
    """None: sonuçlandırmak için gereken veri (ilk yarı skoru / korner) yok."""
    if pazar.startswith("KOR"):
        if korner is None:
            return None
        return korner > cizgi(pazar) if pazar.startswith("KORU") else korner < cizgi(pazar)
    if pazar.startswith("IY"):
        if iy is None:
            return None
        h, a = iy
        if pazar in ("IY1", "IYX", "IY2"):
            return {"IY1": h > a, "IYX": h == a, "IY2": a > h}[pazar]
        return h + a > cizgi(pazar) if pazar.startswith("IYU") else h + a < cizgi(pazar)
    if pazar.startswith("UST"):
        return ev + dep > cizgi(pazar)
    if pazar.startswith("ALT"):
        return ev + dep < cizgi(pazar)
    return {
        "MS1": ev > dep, "MSX": ev == dep, "MS2": dep > ev,
        "CS1X": ev >= dep, "CSX2": dep >= ev, "CS12": ev != dep,
        "KGVAR": ev > 0 and dep > 0, "KGYOK": ev == 0 or dep == 0,
    }[pazar]


def _poisson(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def veri_yeterli(ist: dict) -> bool:
    ev, dep = ist["ev"], ist["dep"]
    lig = ev["oynanan_ic"] + ev["oynanan_dis"] >= 3 and dep["oynanan_ic"] + dep["oynanan_dis"] >= 3
    son5 = ev["son5_atilan_ort"] + ev["son5_yenilen_ort"] > 0 and dep["son5_atilan_ort"] + dep["son5_yenilen_ort"] > 0
    return lig or son5


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


def en_olasi_skor(lam_ev: float, lam_dep: float) -> tuple[str, float]:
    i, j = max(((i, j) for i in range(6) for j in range(6)),
               key=lambda s: _poisson(s[0], lam_ev) * _poisson(s[1], lam_dep))
    return f"{i}-{j}", _poisson(i, lam_ev) * _poisson(j, lam_dep)


def _skor_dagilimi(lam_ev: float, lam_dep: float, ust: int = 8):
    """İlk yarı ve ikinci yarı gollerini ayrı Poisson olarak dolaşır: (ilk yarı skoru, maç sonu skoru, olasılık)."""
    iy_ev, iy_dep = lam_ev * IY_ORANI, lam_dep * IY_ORANI
    iky_ev, iky_dep = lam_ev - iy_ev, lam_dep - iy_dep
    iy = [(i, j, _poisson(i, iy_ev) * _poisson(j, iy_dep)) for i in range(ust) for j in range(ust)]
    iky = [(k, l, _poisson(k, iky_ev) * _poisson(l, iky_dep)) for k in range(ust) for l in range(ust)]
    for i, j, p1 in iy:
        for k, l, p2 in iky:
            yield (i, j), (i + k, j + l), p1 * p2


def model_olasiliklari(lam_ev: float, lam_dep: float) -> dict[str, float]:
    """Tam maç ve ilk yarı pazarları için Poisson olasılıkları. Korner için model yok."""
    p = {k: 0.0 for k in TAM_MAC + ILK_YARI}
    for iy, (ev, dep), olas in _skor_dagilimi(lam_ev, lam_dep):
        for pazar in p:
            if kazandi_mi(pazar, ev, dep, iy=iy):
                p[pazar] += olas
    return p


def ortak_olasilik(pazarlar: list[str], lam_ev: float, lam_dep: float) -> float:
    """Aynı maçtaki gol/ilk yarı pazarlarının birlikte gerçekleşme olasılığı (korner hariç)."""
    return sum(olas for iy, (ev, dep), olas in _skor_dagilimi(lam_ev, lam_dep)
               if all(kazandi_mi(pz, ev, dep, iy=iy) for pz in pazarlar))


def bet_builder(bacaklar: list[dict]) -> tuple[float, float]:
    """Aynı maçtaki seçimler için (tahmini oran, tahmini adil olasılık).
    Piyasa olasılıkları çarpılır, gol modelinin gösterdiği ilişki (korelasyon) oranıyla düzeltilir."""
    gol = [b for b in bacaklar if not b["pazar"].startswith("KOR")]
    carpan = 1.0
    if len(gol) >= 2:
        lam_ev, lam_dep = gol[0]["beklenen_gol"]
        tekil = math.prod(model_olasiliklari(lam_ev, lam_dep)[b["pazar"]] for b in gol)
        if tekil > 0:
            carpan = min(max(ortak_olasilik([b["pazar"] for b in gol], lam_ev, lam_dep) / tekil, 0.5), 2.0)
    olasilik = min(math.prod(b["adil_olasilik"] for b in bacaklar) * carpan, 0.99)
    oran = math.prod(b["oran"] for b in bacaklar) / carpan
    return round(oran, 2), round(olasilik, 3)


def piyasa_olasiliklari(oranlar: dict[str, float]) -> dict[str, float]:
    """Bir bahisçinin oranlarından marjı gruplar içinde normalize ederek adil olasılık çıkarır."""
    gruplar = [g for g in UC_YOLLU if all(k in oranlar for k in g)]
    if "KGVAR" in oranlar and "KGYOK" in oranlar:
        gruplar.append(("KGVAR", "KGYOK"))
    for ust, alt in IKILI_ONEK:
        for kod in oranlar:
            eslik = alt + kod[len(ust):]
            if kod.startswith(ust) and eslik in oranlar:
                gruplar.append((kod, eslik))
    adil: dict[str, float] = {}
    for grup in gruplar:
        ters = {k: 1 / oranlar[k] for k in grup}
        toplam = sum(ters.values())
        adil.update({k: v / toplam for k, v in ters.items()})
    if all(k in adil for k in ("MS1", "MSX", "MS2")):
        adil["CS1X"] = adil["MS1"] + adil["MSX"]
        adil["CSX2"] = adil["MSX"] + adil["MS2"]
        adil["CS12"] = adil["MS1"] + adil["MS2"]
    return adil


def adil_olasiliklar(bahisciler: dict[str, dict[str, float]], keskin: str) -> tuple[dict[str, float], dict[str, str]]:
    """Her pazar için keskin bahisçiyi, yoksa en az 3 bahisçinin ortalamasını kullanır. (olasılık, kaynak) döner."""
    keskin_ad = next((ad for ad in bahisciler if ad.lower() == keskin.lower()), None)
    keskin_p = piyasa_olasiliklari(bahisciler[keskin_ad]) if keskin_ad else {}
    tum = [piyasa_olasiliklari(o) for o in bahisciler.values()]
    pazarlar = {k for p in tum for k in p}
    adil, kaynak = {}, {}
    for pazar in pazarlar:
        if pazar in keskin_p:
            adil[pazar], kaynak[pazar] = keskin_p[pazar], keskin_ad
        else:
            degerler = [p[pazar] for p in tum if pazar in p]
            if len(degerler) >= 3:
                adil[pazar], kaynak[pazar] = sum(degerler) / len(degerler), f"average of {len(degerler)}"
    return adil, kaynak


def piyasa_oranlari(bahisciler: dict[str, dict[str, float]], izinli: list[str],
                    yontem: str = "medyan") -> dict[str, tuple[float, str, dict[str, float]]]:
    """Listedeki büyük bahisçilerin oranı: "en_iyi" = içlerindeki en yüksek fiyat (takipçi o sitede gerçekten
    bulabilir; değer bahsinde standart yöntem), "medyan" = ortanca. Bahisçi bahisçi oranlar da döner."""
    izin = {ad.lower() for ad in izinli}
    oranlar: dict[str, dict[str, float]] = {}
    for ad, o in bahisciler.items():
        if ad.lower() in izin:
            for pazar, oran in o.items():
                oranlar.setdefault(pazar, {})[ad] = oran
    if yontem == "en_iyi":
        return {pazar: (round(max(d.values()), 2), f"best of {len(d)}", d) for pazar, d in oranlar.items()}
    return {pazar: (round(statistics.median(d.values()), 2), f"median of {len(d)}", d) for pazar, d in oranlar.items()}


def oran_yeterli(bahisci_oranlari: dict[str, float], ayar) -> bool:
    """Seçim takipçinin gerçekten bulabileceği bir pazar olmalı: zorunlu bahisçide ve yeterince sitede var."""
    adlar = {ad.lower() for ad in bahisci_oranlari}
    return (len(adlar) >= ayar.min_oran_bahiscisi
            and all(z.lower() in adlar for z in ayar.zorunlu_bahisciler))


def aday_turu(p: float, deger: float, ayar, ek_marj: float = 0.0) -> str | None:
    """ek_marj: keskin bahisçinin fiyatlamadığı pazarlarda ihtimal daha az güvenilir, sınırlar bu kadar sıkılaşır."""
    if p >= ayar.guvenli_min_olasilik and deger >= ayar.guvenli_min_deger + ek_marj:
        return "guvenli"
    if p >= ayar.deger_min_olasilik and deger >= ayar.deger_min_deger + ek_marj:
        return "deger"
    return None


def _piyasa_adaylari(bahisciler: dict[str, dict[str, float]], ayar, guvenilir_lig: bool):
    """İstatistiksiz, yalnızca piyasadan: (pazar, oran, bolag, bahisçi oranları, p, değer, tür, kaynak).
    İzinli liste dışındaki liglerde keskin bahisçinin o pazarı fiyatlaması şarttır (likit, güvenilir piyasa)."""
    adil, kaynak = adil_olasiliklar(bahisciler, ayar.keskin_bahisci)
    for pazar, (oran, bolag, bahisci_oranlari) in piyasa_oranlari(bahisciler, ayar.oran_bahiscileri, ayar.oran_yontemi).items():
        if pazar not in adil or not (ayar.oran_min <= oran <= ayar.oran_max) or not oran_yeterli(bahisci_oranlari, ayar):
            continue
        keskin_var = kaynak[pazar].lower() == ayar.keskin_bahisci.lower()
        if not guvenilir_lig and not keskin_var:
            continue
        p = adil[pazar]
        deger = p * oran - 1
        tur = aday_turu(p, deger, ayar, 0.0 if keskin_var else ayar.keskinsiz_ek_marj)
        if tur:
            yield pazar, oran, bolag, bahisci_oranlari, p, deger, tur, kaynak[pazar]


def on_eleme_puani(bahisciler: dict[str, dict[str, float]], ayar, guvenilir_lig: bool) -> float | None:
    """Toplu taramada detaylı incelemeye (istatistik isteği) değer maçları sıralamak için puan; aday yoksa None."""
    puanlar = [p + 2 * deger for _, _, _, _, p, deger, _, _ in _piyasa_adaylari(bahisciler, ayar, guvenilir_lig)]
    return max(puanlar) if puanlar else None


def adaylari_uret(mac: dict, bahisciler: dict[str, dict[str, float]], ist: dict, ayar,
                  guvenilir_lig: bool = True) -> list[dict]:
    if not veri_yeterli(ist):
        return []
    lam_ev, lam_dep = beklenen_goller(ist)
    model = model_olasiliklari(lam_ev, lam_dep)
    skor, skor_p = en_olasi_skor(lam_ev, lam_dep)
    adaylar = []
    for pazar, oran, bolag, bahisci_oranlari, p, deger, tur, adil_kaynak in _piyasa_adaylari(bahisciler, ayar, guvenilir_lig):
        if pazar in model and model[pazar] < p - ayar.model_tolerans:
            continue
        uzun, kisa = etiketler(pazar, mac["ev"], mac["dep"])
        adaylar.append({
            "aday_id": f'{mac["fixture_id"]}-{pazar}',
            "fixture_id": mac["fixture_id"],
            "pazar": pazar,
            "tur": tur,
            "etiket": uzun,
            "kisa": kisa,
            "oran": oran,
            "bolag": bolag,
            "oranlar": bahisci_oranlari,
            "adil_olasilik": round(p, 3),
            "adil_oran": round(1 / p, 2),
            "adil_kaynak": adil_kaynak,
            "model_olasilik": round(model[pazar], 3) if pazar in model else None,
            "deger": round(deger, 3),
            "beklenen_gol": [round(lam_ev, 2), round(lam_dep, 2)],
            "olasi_skor": skor,
            "olasi_skor_olasilik": round(skor_p, 3),
        })
    adaylar.sort(key=lambda a: (a["tur"] == "deger", a["deger"] if a["tur"] == "deger" else a["adil_olasilik"]),
                 reverse=True)
    return adaylar[:4]
