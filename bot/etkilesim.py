"""Kupon dışı, etkileşime açık günlük paylaşımlar: günün maçları, günün istatistiği, doğru tahmin/kötü fiyat, anket,
radar, skor tahmini, pas günü.

Veri sabah taramasından gelir (gun["vitrin"]): ek API isteği yapılmaz. Her tür günde bir kez, kendi paylaşımlarımız
arasında en az ARALIK_DK olacak şekilde ve maç saatine göre zamanlanır; 15 dakikalık nabız çalıştırır."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import analiz, bilgi, gorsel, model
from .oddsapi import ima_edilen_goller
from .tweets import ANSVAR, LIMIT, etiket_satiri, uzunluk

VITRIN_MAX = 6
ARALIK_DK = 45


def vitrin(maclar: list[dict], oranlar: dict, ayar, simdi: datetime) -> list[dict]:
    """Günün en çok ilgi çekecek maçları: önce izinli ligler, sonra en çok bahisçinin fiyatladığı (likit) maçlar."""
    liste = []
    for m in maclar:
        b = oranlar.get(m["fixture_id"])
        if not b or datetime.fromisoformat(m["baslama"]) <= simdi:
            continue
        adil, _ = model.adil_olasiliklar(b, ayar.keskin_bahisci)
        if not all(k in adil for k in ("MS1", "MSX", "MS2")):
            continue
        goller = ima_edilen_goller(adil)
        if goller is None:
            continue
        skor, _ = model.en_olasi_skor(*goller)
        izinli = m["lig_id"] in ayar.ligler
        fiyat = {k: o for k, (o, _, _d) in model.piyasa_oranlari(b, ayar.oran_bahiscileri, ayar.oran_yontemi).items()}
        liste.append(((izinli, len(b)), {
            "fixture_id": m["fixture_id"], "lig": m.get("lig", ""), "ulke": m.get("ulke", ""), "izinli": izinli, "ev": m["ev"], "dep": m["dep"],
            "baslama": m["baslama"], "p": {k: round(adil[k], 3) for k in ("MS1", "MSX", "MS2")},
            "beklenen_gol": [round(g, 2) for g in goller], "olasi_skor": skor,
            "kisa": kisa_fiyat(m["ev"], m["dep"], adil, fiyat),
            **{k: m[k] for k in ("odds_id", "odds_spor") if k in m},  # sonuç bu kaynaktan sorulur
        }))
    liste.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in liste[:VITRIN_MAX]]


KISA_MIN_P = 0.65
KISA_PAZARLAR = (("MS1", None), ("MS2", None), ("UST15", "Over 1.5 goals"), ("UST25", "Over 2.5 goals"),
                 ("KGVAR", "Both teams to score"))


def kisa_fiyat(ev: str, dep: str, adil: dict, fiyat: dict) -> dict | None:
    """Tahminimiz güçlü ama fiyat adil oranın altında (değer yok, bu yüzden kuponda değil): en olası böyle pazar.
    "Doğru tahmin, kötü fiyat" paylaşımının malzemesi."""
    adaylar = []
    for kod, ad in KISA_PAZARLAR:
        p, o = adil.get(kod), fiyat.get(kod)
        if p and o and p >= KISA_MIN_P and p * o - 1 < 0:
            adaylar.append({"pazar": kod, "ad": ad or f"{ev if kod == 'MS1' else dep} to win",
                            "p": round(p, 3), "oran": round(o, 2)})
    return max(adaylar, key=lambda a: a["p"]) if adaylar else None



def _saat(v: dict, ayar) -> str:
    return datetime.fromisoformat(v["baslama"]).astimezone(ZoneInfo(ayar.saat_dilimi)).strftime("%H:%M %Z")


def _etiket(v: dict) -> str:
    e = etiket_satiri([(v.get("lig"), v.get("ulke"))], [(v["ev"], v["dep"])])
    return f"\n{e}" if e else ""


def _pct(p: float) -> str:
    return f"{100 * p:.0f}%"


def _favori(v: dict) -> tuple[str, float]:
    p = v["p"]
    return (v["ev"], p["MS1"]) if p["MS1"] >= p["MS2"] else (v["dep"], p["MS2"])


def anket_maci(vit: list[dict]) -> dict | None:
    """Anket en dengeli büyük maça: herkesin bildiği sonucu oylatmak etkileşim getirmez."""
    adaylar = [v for v in vit[:4] if v.get("izinli")] or vit[:4]
    return max(adaylar, key=lambda v: min(v["p"]["MS1"], v["p"]["MS2"])) if adaylar else None


def skor_maci(vit: list[dict]) -> dict | None:
    anket = anket_maci(vit)
    return next((v for v in vit if v is not anket), anket)


def maclar_tweeti(gun: dict, ayar) -> str:
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")
    satirlar = []
    for v in gun["vitrin"][:4]:
        fav, p = _favori(v)
        satirlar.append(f'⚽ {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n   our numbers: {fav} {_pct(p)}')
    for n in range(len(satirlar), 0, -1):
        etiket = etiket_satiri([(v.get("lig"), v.get("ulke")) for v in gun["vitrin"][:n]],
                               [(v["ev"], v["dep"]) for v in gun["vitrin"][:n]])
        metin = (f"🔥 TODAY'S BIG GAMES | {tarih}\n\n" + "\n".join(satirlar[:n]) +
                 "\n\nWhich one are you watching? 👇" + (f"\n{etiket}" if etiket else ""))
        if uzunluk(metin) <= LIMIT:
            return metin
    return metin


def _secenek(ad: str) -> str:
    return ad if len(ad) <= 25 else ad[:24] + "…"


def anket(gun: dict, ayar) -> tuple[str, list[str], int] | None:
    v = anket_maci(gun["vitrin"])
    if not v:
        return None
    p = v["p"]
    metin = (f'🗳️ MATCH POLL | {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n\nWho wins? Vote below 👇\n\n'
             f'Our numbers: {v["ev"]} {_pct(p["MS1"])} · draw {_pct(p["MSX"])} · {v["dep"]} {_pct(p["MS2"])}\n'
             f'Agree or not? Tell us why in the replies.' + _etiket(v))
    sure = datetime.fromisoformat(v["baslama"]) - datetime.fromisoformat(gun["_simdi"])
    dakika = max(5, min(10080, int(sure.total_seconds() // 60)))
    return metin, [_secenek(v["ev"]), "Draw", _secenek(v["dep"])], dakika


def skor_tweeti(gun: dict, ayar) -> str | None:
    v = skor_maci(gun["vitrin"])
    if not v:
        return None
    ev_g, dep_g = v["beklenen_gol"]
    return (f'🎯 SCORE PREDICTION | {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n\n'
            f'Our model\'s most likely score: {v["olasi_skor"].replace("-", "–")}\n'
            f'Expected goals: {ev_g:.1f} – {dep_g:.1f}\n\n'
            f"What's your score? Reply below 👇" + _etiket(v))


def istatistik_maci(vit: list[dict]) -> dict | None:
    """Günün istatistiği: anket ve skor tahmininde kullanılmayan, gol beklentisi en yüksek büyük maç."""
    kullanilan = {id(anket_maci(vit)), id(skor_maci(vit))}
    kalan = [v for v in vit if id(v) not in kullanilan] or vit
    return max(kalan, key=lambda v: sum(v["beklenen_gol"])) if kalan else None


def istatistik_tweeti(gun: dict, ayar) -> str | None:
    v = istatistik_maci(gun["vitrin"])
    if not v:
        return None
    ev_g, dep_g = v["beklenen_gol"]
    return (f'📊 STAT OF THE DAY | {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n\n'
            f'Our model expects {ev_g + dep_g:.1f} goals tonight ({ev_g:.1f} – {dep_g:.1f}).\n'
            f'Most likely score: {v["olasi_skor"].replace("-", "–")}\n\n'
            f'Goals or a tight one? Tell us below 👇' + _etiket(v))


def olgular(tur: str, gun: dict, ayar) -> dict:
    """Direktöre verilen gerçekler: yalnızca bunlardan yazar."""
    def mac(v):
        return {"home": v["ev"], "away": v["dep"], "competition": v.get("lig"), "kickoff": _saat(v, ayar),
                "chances_home_draw_away": [round(v["p"][k], 2) for k in ("MS1", "MSX", "MS2")],
                "expected_goals_home_away": v["beklenen_gol"], "most_likely_score": v["olasi_skor"]}
    vit = gun.get("vitrin") or []
    if tur == "maclar":
        return {"date": gun["tarih"], "games": [mac(v) for v in vit[:4]]}
    if tur == "anket":
        return {"poll_options_fixed": ["home", "Draw", "away"], "game": mac(anket_maci(vit))}
    if tur == "skor":
        return {"game": mac(skor_maci(vit))}
    if tur == "istatistik":
        return {"game": mac(istatistik_maci(vit))}
    if tur == "ayrisma":
        return {"games": [{"home": a["ev"], "away": a["dep"], "kickoff": _saat(a, ayar), "market": c["ad"],
                           "market_chance": _pct(c["piyasa"]), "team_stats_chance": _pct(c["istatistik"])}
                          for a in gun.get("ayrisma") or [] for c in [analiz.dikkat_cekici(a)] if c],
                "note": "market = bookmaker prices with the margin removed; team stats = home/away scoring "
                        "averages. Ask who is right; no betting advice."}
    if tur == "bilgi":
        k = bilgi.gunun_konusu(gun["tarih"])
        return {"topic": k["baslik"], "facts_to_use": k["govde"], "question_idea": k["soru"],
                "accuracy_rule": "use only these facts and exactly these numbers; add no other number or claim"}
    if tur == "deger":
        return {"date": gun["tarih"], "not_in_our_coupon_on_purpose": True,
                "games": [{**mac(v), "our_call": v["kisa"]["ad"], "our_chance": v["kisa"]["p"],
                           "best_odds": v["kisa"]["oran"], "fair_odds": round(1 / v["kisa"]["p"], 2)}
                          for v in deger_maclari(vit, gun.get("_haric", frozenset()))],
                "why_left_out": "we expect it, but the odds are below the fair price (no value), so we skip it; "
                                "patience with the price is how the bank grows"}
    if tur == "radar":
        return {"date": gun["tarih"], "not_in_our_coupon_on_purpose": True,
                "games": [{**mac(v), "our_number": f'{v["radar"]} {round(100 * v["radar_p"])}%'}
                          for v in radar_maclari(vit, gun.get("_haric", frozenset()))],
                "why_left_out": "the odds don't pay enough for the risk"}
    return {"date": gun["tarih"], "games_checked": gun.get("taranan"), "reason": gun.get("pas_nedeni")}


RADAR_PAZARLARI = (("UST25", "Over 2.5 goals"), ("KGVAR", "Both teams to score"))


def radar_maclari(vit: list[dict], haric_takimlar: set[str] = frozenset()) -> list[dict]:
    """Kuponda olmayan büyük maçlar ve her biri için bizim rakamlarla en ilgi çekici pazar (en az %50 ihtimal)."""
    sonuc = []
    for v in vit:
        if {v["ev"].lower(), v["dep"].lower()} & haric_takimlar or v.get("kisa"):
            continue  # kupondaki ve "doğru tahmin, kötü fiyat" paylaşımındaki maçlar tekrar edilmez
        p_model = model.model_olasiliklari(*v["beklenen_gol"])
        fav, p_fav = _favori(v)
        secenekler = [(p_fav, f"{fav} to win")] + [(p_model[k], ad) for k, ad in RADAR_PAZARLARI]
        uygun = [x for x in secenekler if 0.5 <= x[0] <= 0.85]
        p, ad = max(uygun or [(p_fav, f"{fav} to win")], key=lambda x: x[0])
        sonuc.append({**v, "radar": ad, "radar_p": round(p, 3)})
    return sonuc[:3]


def radar_tweeti(gun: dict, ayar, haric_takimlar: set[str] = frozenset()) -> str | None:
    liste = radar_maclari(gun.get("vitrin") or [], haric_takimlar)
    if len(liste) < 2:
        return None
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")
    satirlar = [f'- {v["ev"]} v {v["dep"]}: {v["radar"]} {_pct(v["radar_p"])}' for v in liste]
    metin = None
    for n in range(len(liste), 1, -1):  # sığmazsa son maç düşer
        etiket = etiket_satiri([(v.get("lig"), v.get("ulke")) for v in liste[:n]], [(v["ev"], v["dep"]) for v in liste[:n]])
        metin = (f"📡 OUR RADAR | {tarih}\n\nNot in our coupon, but our numbers say:\n" + "\n".join(satirlar[:n]) +
                 "\n\nLeft out: the price doesn't pay for the risk. How do you read them? 👇\n\n" +
                 (f"{etiket}\n" if etiket else "") + ANSVAR)
        if uzunluk(metin) <= LIMIT:
            return metin
    return None


def deger_maclari(vit: list[dict], haric_takimlar: set[str] = frozenset()) -> list[dict]:
    """Kuponda olmayan, tahminimiz güçlü ama fiyatı düşük olduğu için oynamadığımız maçlar (en olasıdan)."""
    liste = [v for v in vit if v.get("kisa") and not {v["ev"].lower(), v["dep"].lower()} & haric_takimlar]
    return sorted(liste, key=lambda v: v["kisa"]["p"], reverse=True)[:3]


def deger_tweeti(gun: dict, ayar, haric_takimlar: set[str] = frozenset()) -> str | None:
    liste = deger_maclari(gun.get("vitrin") or [], haric_takimlar)
    if not liste:
        return None
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")

    def satir(v):
        k = v["kisa"]
        return f'- {v["ev"]} v {v["dep"]}: {k["ad"]} {_pct(k["p"])}, odds {k["oran"]:.2f} (fair {1 / k["p"]:.2f})'
    for n in range(len(liste), 0, -1):  # sığmazsa son maç düşer
        etiket = etiket_satiri([(v.get("lig"), v.get("ulke")) for v in liste[:n]], [(v["ev"], v["dep"]) for v in liste[:n]])
        metin = (f"🧐 GOOD CALL, POOR PRICE | {tarih}\n\n" + "\n".join(satir(v) for v in liste[:n])
                 + "\n\nLikely, but no value at these odds, so no coupon. Right call? 👇\n\n"
                 + (f"{etiket}\n" if etiket else "") + ANSVAR)
        if uzunluk(metin) <= LIMIT:
            return metin
    return None


def bilgi_tweeti(gun: dict) -> str:
    k = bilgi.gunun_konusu(gun["tarih"])
    return f'💡 {k["baslik"]}\n\n{k["govde"]}\n\n{k["soru"]}\n\n{ANSVAR}'


def pas_tweeti(gun: dict) -> str:
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")
    n = gun.get("taranan")
    bakilan = f"We checked {n} games today." if n else "We checked today's games."
    return (f"⏸️ NO COUPON TODAY | {tarih}\n\n{bakilan} None had odds good enough for their real chances, "
            f"so we pass. Passing protects the bank.\n\nWhich game would you have played? 👇\n\n{ANSVAR}")


def _son_paylasim(gun: dict, diger: tuple[str, ...] = ()) -> datetime | None:
    zamanlar = [gun.get("yayin"), *diger] + [e.get("zaman") for e in (gun.get("etkilesim") or {}).values()
                                             if e.get("durum") == "paylasildi"]
    zamanlar = [datetime.fromisoformat(z) for z in zamanlar if z]
    return max(zamanlar) if zamanlar else None


def _plan(gun: dict) -> list[tuple[str, datetime, datetime]]:
    """(tür, en erken, en geç) — sırayla; en geç geçtiyse o tür o gün atlanır."""
    plan = []
    vit = gun.get("vitrin") or []
    if gun.get("sonuc") == "pas":
        olusturma = datetime.fromisoformat(gun["olusturma"])
        plan.append(("pas", olusturma, olusturma + timedelta(hours=8)))
    gun_bas = datetime.fromisoformat(gun["tarih"] + "T00:00:00+00:00")
    plan.append(("bilgi", gun_bas + timedelta(hours=9), gun_bas + timedelta(hours=19, minutes=30)))  # günlük bilgi
    if gun.get("konsept") == "analiz":
        # Kupon yok: günün maçları, öne çıkan maçların analiz kartları (maçtan ~4 saat – 35 dk önce), anket.
        if gun.get("tablo"):  # günün analiz tablosu (görsel): sabah, tablodaki ilk maçtan önce
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in gun["tablo"])
            plan.append(("tablo", gun_bas + timedelta(hours=8), ilk - timedelta(minutes=10)))
        elif vit:
            ilk = min(datetime.fromisoformat(v["baslama"]) for v in vit)
            plan.append(("maclar", ilk - timedelta(hours=5), ilk - timedelta(minutes=15)))
        if len(gun.get("ayrisma") or []) >= 2:  # istatistik piyasaya katılmıyor: kim haklı?
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in gun["ayrisma"])
            plan.append(("ayrisma", gun_bas + timedelta(hours=10), ilk - timedelta(minutes=30)))
        for i, a in enumerate(gun.get("analizler") or []):
            b = datetime.fromisoformat(a["baslama"])
            plan.append((f"analiz_{i}", b - timedelta(hours=4), b - timedelta(minutes=35)))
        if vit:
            a = datetime.fromisoformat(anket_maci(vit)["baslama"])
            plan.append(("anket", a - timedelta(hours=3), a - timedelta(minutes=30)))
        return plan
    if vit:
        ilk = min(datetime.fromisoformat(v["baslama"]) for v in vit)
        plan.append(("maclar", ilk - timedelta(hours=5), ilk - timedelta(minutes=15)))
        i = datetime.fromisoformat(istatistik_maci(vit)["baslama"])
        plan.append(("istatistik", i - timedelta(hours=4), i - timedelta(minutes=45)))
        a = datetime.fromisoformat(anket_maci(vit)["baslama"])
        plan.append(("deger", ilk - timedelta(hours=3, minutes=30), ilk - timedelta(minutes=30)))
        plan.append(("anket", a - timedelta(hours=3), a - timedelta(minutes=30)))
        s = datetime.fromisoformat(skor_maci(vit)["baslama"])
        plan.append(("radar", ilk - timedelta(hours=2, minutes=15), ilk - timedelta(minutes=40)))
        plan.append(("skor", s - timedelta(minutes=75), s - timedelta(minutes=10)))
    return plan


def paylas(gun: dict, ayar, x, simdi: datetime, yaz=print, yazar=None, diger_paylasimlar: tuple[str, ...] = (),
           haric_takimlar: set[str] = frozenset()) -> str | None:
    """Sıradaki etkileşim paylaşımını zamanı geldiyse atar (nabız başına en fazla bir tane).
    yazar: (tür, olgular, şablon) -> metin (X Direktörü); yoksa şablon. diger_paylasimlar: aynı günün diğer
    kupon paylaşımlarının zamanları (aralık kuralı hepsine göre)."""
    if gun.get("secimler") and not gun.get("tweet_id"):
        return None  # kupon henüz paylaşılmadı (onay bekliyor): önce kupon
    durum = gun.setdefault("etkilesim", {})
    son = _son_paylasim(gun, diger_paylasimlar)
    if son and simdi < son + timedelta(minutes=ARALIK_DK):
        return None
    for tur, erken, gec in _plan(gun):
        if tur in durum:
            continue
        if simdi > gec:
            durum[tur] = {"durum": "atlandi"}
            continue
        if simdi < erken:
            continue  # sıradaki türün saati gelmediyse, saati gelmiş bir sonraki tür beklemesin
        zaman = simdi.isoformat(timespec="seconds")
        try:
            if tur.startswith("analiz_"):
                a = gun["analizler"][int(tur.split("_")[1])]
                metin = analiz_tweeti(a, ayar)
                metin = yazar("analiz", analiz_olgulari(a, ayar), metin) if yazar else metin
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "direktör"}
                    continue
                medya = x.medya_yukle(gorsel.analiz_karti(a, _saat(a, ayar), "en"))
                tid = x.gonder(metin, medya=[medya])
            elif tur == "tablo":
                liste = [a for a in gun["tablo"] if datetime.fromisoformat(a["baslama"]) > simdi]
                if len(liste) < 4:
                    durum[tur] = {"durum": "atlandi", "neden": "yeterli maç kalmadı"}
                    continue
                metin = tablo_tweeti(gun, liste)
                metin = yazar("tablo", tablo_olgulari(gun, liste, ayar), metin) if yazar else metin
                if not metin:
                    durum[tur] = {"durum": "atlandi", "neden": "direktör"}
                    continue
                png = gorsel.analiz_tablosu(liste, gun["tarih"], [_saat(a, ayar) for a in liste], "en")
                tid = x.gonder(metin, medya=[x.medya_yukle(png)])
            elif tur == "anket":
                metin, secenekler, dakika = anket({**gun, "_simdi": zaman}, ayar)
                metin = yazar(tur, olgular(tur, gun, ayar), metin) if yazar else metin
                tid = x.gonder(metin, anket={"options": secenekler, "duration_minutes": dakika})
            else:
                metin = {"pas": lambda: pas_tweeti(gun), "bilgi": lambda: bilgi_tweeti(gun),
                         "ayrisma": lambda: ayrisma_tweeti(gun, ayar, simdi), "maclar": lambda: maclar_tweeti(gun, ayar),
                         "skor": lambda: skor_tweeti(gun, ayar),
                         "istatistik": lambda: istatistik_tweeti(gun, ayar),
                         "radar": lambda: radar_tweeti(gun, ayar, haric_takimlar),
                         "deger": lambda: deger_tweeti(gun, ayar, haric_takimlar)}[tur]()
                if metin is None:  # içerik yok (ör. kupon dışı yeterli maç yok)
                    durum[tur] = {"durum": "atlandi"}
                    continue
                metin = yazar(tur, olgular(tur, {**gun, "_haric": haric_takimlar}, ayar), metin) if yazar else metin
                if not metin:  # X Direktörü bugün bu paylaşımı uygun görmedi
                    durum[tur] = {"durum": "atlandi", "neden": "direktör"}
                    yaz(f"Etkileşim paylaşımı ({tur}): direktör bugün atlamayı seçti.")
                    continue
                tid = x.gonder(metin)
        except Exception as e:
            # Tekrar tekrar denenip hata yağmasın: bu tür bugün atlanır.
            durum[tur] = {"durum": "hata", "hata": str(e)[:300], "zaman": zaman}
            yaz(f"⚠️ Etkileşim paylaşımı ({tur}) başarısız: {e}")
            return None
        durum[tur] = {"durum": "paylasildi", "tweet_id": tid, "zaman": zaman}
        if tur == "deger":  # maçlar bitince bu post alıntılanıp nasıl bittikleri yazılır
            durum[tur]["maclar"] = [{k: v[k] for k in ("fixture_id", "odds_id", "odds_spor", "ev", "dep", "lig", "ulke",
                                                       "baslama", "kisa") if k in v}
                                    for v in deger_maclari(gun.get("vitrin") or [], haric_takimlar)]
        yaz(f"Etkileşim paylaşımı ({tur}):\n```\n{metin}\n```")
        return tur
    return None


TAKIP_GECIKME = timedelta(hours=2, minutes=15)  # son maçın başlamasından sonra (bitmiş ve sonuç girilmiş olur)
ORNEK_TUTAR = 100


def deger_takip_tweeti(gun: dict, maclar: list[dict], birim: str) -> str | None:
    """"Good call, poor price" postunun alıntısı: maçlar nasıl bitti ve kısa oranın neden değmediği.
    Yalnızca sonuçlanan maçlar (skor ve kazandı/kaybetti) yazılır."""
    biten = [m for m in maclar if m.get("sonuc") in ("kazandi", "kaybetti")]
    if not biten:
        return None
    tutan = [m for m in biten if m["sonuc"] == "kazandi"]
    net = sum(ORNEK_TUTAR * (m["kisa"]["oran"] - 1) for m in tutan) - ORNEK_TUTAR * (len(biten) - len(tutan))
    if len(tutan) == len(biten):
        yorum = (("Our read was right" if len(biten) == 1 else "Our reads were right")
                 + f", but €{ORNEK_TUTAR} on {'it' if len(biten) == 1 else 'each'} made just {'+' if net >= 0 else '-'}€{abs(net):.0f}."
                 + " Likely isn't the same as good value.")
    elif not tutan:
        yorum = (f"{'It' if len(biten) == 1 else 'None of them'} came in. "
                 "Even big favourites lose; at short odds there's no cushion for that.")
    else:
        yorum = (f"{len(tutan)} of {len(biten)} came in, and €{ORNEK_TUTAR} on each ends at "
                 f"{'+' if net >= 0 else '-'}€{abs(net):.0f}. One miss wipes out the short-odds wins.")
    yorum = yorum.replace("€", birim)
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")

    def satir(m):
        isaret = "✅" if m["sonuc"] == "kazandi" else "❌"
        return f'{isaret} {m["ev"]} {m["skor"].replace("-", "–")} {m["dep"]} · {m["kisa"]["ad"]}'
    tek = len(biten) == 1
    bas = f"🔁 HOW {'IT' if tek else 'THEY'} ENDED | {tarih}\n\n"
    soru = f"\n\nRight call to skip {'it' if tek else 'them'}? 👇\n{ANSVAR}"
    for n in range(len(biten), 0, -1):  # sığmazsa son maç satırı düşer (yorum tüm maçlara göre kalır)
        metin = bas + "\n".join(satir(m) for m in biten[:n]) + f"\n\n{yorum}" + soru
        if uzunluk(metin) <= LIMIT:
            return metin
    return None


def deger_takibi(gun: dict, ayar, x, simdi: datetime, sonuc_getir, yaz=print, yazar=None) -> bool:
    """Maçlar bitince "Good call, poor price" postunu alıntılayıp nasıl bittiklerini paylaşır (bir kez).
    sonuc_getir(maclar) -> {fixture_id: {"durum", "skor"}}."""
    e = (gun.get("etkilesim") or {}).get("deger") or {}
    if e.get("durum") != "paylasildi" or not e.get("maclar") or e.get("takip"):
        return False
    son = max(datetime.fromisoformat(m["baslama"]) for m in e["maclar"])
    if simdi < son + TAKIP_GECIKME:
        return False
    if simdi > son + timedelta(days=2):
        e["takip"] = {"durum": "atlandi", "neden": "sonuç gelmedi"}
        return False
    sonuclar = sonuc_getir(e["maclar"])
    if any((sonuclar.get(m["fixture_id"]) or {}).get("durum") not in ("bitti", "iptal") for m in e["maclar"]):
        return False  # henüz hepsi bitmedi: sonraki nabız
    for m in e["maclar"]:
        r = sonuclar[m["fixture_id"]]
        if r["durum"] == "bitti":
            ev, dep = r["skor"]
            m["skor"] = f"{ev}-{dep}"
            sonuc = model.kazandi_mi(m["kisa"]["pazar"], ev, dep)
            m["sonuc"] = None if sonuc is None else ("kazandi" if sonuc else "kaybetti")
        else:
            m["sonuc"] = "iptal"
    metin = deger_takip_tweeti(gun, e["maclar"], ayar.para_birimi)
    if not metin:
        e["takip"] = {"durum": "atlandi", "neden": "sonuçlanan maç yok"}
        return False
    biten = [m for m in e["maclar"] if m.get("sonuc") in ("kazandi", "kaybetti")]
    olgular = {"date": gun["tarih"], "our_earlier_post": "games we expected but skipped because the odds were too short",
               "results": [{"home": m["ev"], "away": m["dep"], "score": m["skor"], "our_call": m["kisa"]["ad"],
                            "came_in": m["sonuc"] == "kazandi", "odds": m["kisa"]["oran"],
                            "our_chance": m["kisa"]["p"]} for m in biten],
               "note": "this post quotes our earlier post; be honest whether we were right, and why the price still "
                       "mattered; no advice to play"}
    if yazar:
        metin = yazar("deger_sonuc", olgular, metin) or metin  # takip her zaman gider (şeffaflık)
    try:
        tid = x.gonder(metin, alinti=e["tweet_id"])
    except Exception as hata:
        e["takip"] = {"durum": "hata", "hata": str(hata)[:300]}
        yaz(f"⚠️ Değer takibi paylaşılamadı: {hata}")
        return False
    e["takip"] = {"durum": "paylasildi", "tweet_id": tid, "zaman": simdi.isoformat(timespec="seconds")}
    yaz(f"Değer takibi (alıntı):\n```\n{metin}\n```")
    return True


def analiz_tweeti(a: dict, ayar) -> str:
    """Analiz kartıyla giden metin: üç ana çağrı ve en olası skor; ayrıntı görselde."""
    m = analiz.manset(a)
    skor, p_skor = a["skorlar"][0]
    bas = (f'📊 MATCH ANALYSIS | {a["ev"]} v {a["dep"]} · {_saat(a, ayar)}\n\n'
           + "\n".join(f'• {c["ad"]}: {_pct(c["p"])}' for c in m) + f'\n• Most likely score: {skor} ({_pct(p_skor)})')
    c = analiz.dikkat_cekici(a)
    fark = (f'\n\n📈 Team stats see {c["ad"]} at {_pct(c["istatistik"])}, the market {_pct(c["piyasa"])}.'
            if c else "")
    son = "\n\nFull breakdown in the card. How do you see it? 👇"
    etiket = _etiket(a)
    for metin in (bas + fark + son + etiket + f"\n{ANSVAR}", bas + fark + son + f"\n{ANSVAR}",
                  bas + son + etiket + f"\n{ANSVAR}", bas + son + f"\n{ANSVAR}"):
        if uzunluk(metin) <= LIMIT:
            return metin
    govde = bas + son
    return govde[:LIMIT - len(ANSVAR) - 1] + f"\n{ANSVAR}"


def analiz_olgulari(a: dict, ayar) -> dict:
    return {"home": a["ev"], "away": a["dep"], "competition": a.get("lig"), "kickoff": _saat(a, ayar),
            "headline_calls": [{"call": c["ad"], "chance": _pct(c["p"])} for c in analiz.manset(a)],
            "most_likely_score": f'{a["skorlar"][0][0]} ({_pct(a["skorlar"][0][1])})',
            "expected_goals": a["beklenen_gol"], "data_confidence": a["guven"],
            "team_stats_vs_market": [{"market": c["ad"], "market_chance": _pct(c["piyasa"]),
                                      "team_stats_chance": _pct(c["istatistik"])} for c in (a.get("karsilastirma") or [])[:2]],
            "note": "the image card shows every market; this text introduces it. No betting advice."}


def analiz_takip_tweeti(a: dict, skor: str, isabet: list) -> str:
    satirlar = [f'{"✅" if ok else "❌"} {c["ad"]} ({_pct(c["p"])})' for c, ok in zip(analiz.manset(a), isabet)]
    tahmin, p_tahmin = a["skorlar"][0]
    tuttu = sum(isabet)
    yorum = (f"Spot on: the exact score was our most likely one." if skor == tahmin else
             f"Our most likely score was {tahmin} ({_pct(p_tahmin)}).")
    return (f'🔁 FULL TIME | {a["ev"]} {skor.replace("-", "–")} {a["dep"]}\n\n' + "\n".join(satirlar) +
            f"\n\n{yorum} {tuttu} of 3 headline calls came in. How did you read it? 👇\n{ANSVAR}")


def analiz_takibi(gun: dict, ayar, x, simdi: datetime, sonuc_getir, yaz=print, yazar=None) -> int:
    """Analiz kartı paylaşılan maç bitince kart postu alıntılanır: skor ve üç ana çağrının tutup tutmadığı
    (iyi de kötü de paylaşılır). İsabet kaydı haftalık karne için saklanır."""
    paylasilan = 0
    for tur, e in (gun.get("etkilesim") or {}).items():
        if not tur.startswith("analiz_") or e.get("durum") != "paylasildi" or e.get("takip"):
            continue
        a = gun["analizler"][int(tur.split("_")[1])]
        baslama = datetime.fromisoformat(a["baslama"])
        if simdi < baslama + TAKIP_GECIKME:
            continue
        if simdi > baslama + timedelta(days=2):
            e["takip"] = {"durum": "atlandi", "neden": "sonuç gelmedi"}
            continue
        r = sonuc_getir([a]).get(a["fixture_id"]) or {}
        if r.get("durum") == "iptal":
            e["takip"] = {"durum": "atlandi", "neden": "maç oynanmadı"}
            continue
        if r.get("durum") != "bitti":
            continue
        ev, dep = r["skor"]
        skor = f"{ev}-{dep}"
        isabet = [bool(model.kazandi_mi(c["pazar"], ev, dep)) for c in analiz.manset(a)]
        metin = analiz_takip_tweeti(a, skor, isabet)
        if yazar:
            olg = {"score": skor, "home": a["ev"], "away": a["dep"],
                   "calls": [{"call": c["ad"], "chance": _pct(c["p"]), "came_in": ok}
                             for c, ok in zip(analiz.manset(a), isabet)],
                   "our_most_likely_score": f'{a["skorlar"][0][0]} ({_pct(a["skorlar"][0][1])})',
                   "note": "quote of our pre-match card; be honest, right or wrong"}
            metin = yazar("analiz_sonuc", olg, metin) or metin
        try:
            tid = x.gonder(metin, alinti=e["tweet_id"])
        except Exception as hata:
            e["takip"] = {"durum": "hata", "hata": str(hata)[:300]}
            yaz(f"⚠️ Analiz takibi paylaşılamadı: {hata}")
            continue
        brier = {"piyasa": 0.0, "istatistik": 0.0}
        for c in a.get("karsilastirma") or []:
            oldu = 1.0 if model.kazandi_mi(c["pazar"], ev, dep) else 0.0
            brier["piyasa"] += (c["piyasa"] - oldu) ** 2
            brier["istatistik"] += (c["istatistik"] - oldu) ** 2
        e["takip"] = {"durum": "paylasildi", "tweet_id": tid, "skor": skor, "isabet": isabet,
                      "zaman": simdi.isoformat(timespec="seconds"),
                      **({"brier": {k: round(v, 4) for k, v in brier.items()}} if a.get("karsilastirma") else {})}
        yaz(f"Analiz takibi (alıntı):\n```\n{metin}\n```")
        paylasilan += 1
    return paylasilan


def tablo_tweeti(gun: dict, liste: list[dict]) -> str:
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")
    ligler = len({a["lig"] for a in liste})
    n = gun.get("analiz_sayisi")
    kapsam = f"{n} matches analysed today. " if n else ""
    return (f"📋 TODAY'S ANALYSIS BOARD | {tarih}\n\n{kapsam}Here are {len(liste)} of them from {ligler} competitions: "
            f"win/draw/win, over 2.5, both teams to score and the most likely score.\n\n"
            f"Which one would you pick out? 👇\n{ANSVAR}")


def tablo_olgulari(gun: dict, liste: list[dict], ayar) -> dict:
    return {"date": gun["tarih"], "matches_analysed_today": gun.get("analiz_sayisi"), "on_the_board": len(liste),
            "competitions": len({a["lig"] for a in liste}),
            "games": [{"match": f'{a["ev"]} v {a["dep"]}', "competition": a["lig"], "kickoff": _saat(a, ayar),
                       "home_draw_away": [_pct(a["p"][k]) for k in ("MS1", "MSX", "MS2")],
                       "over_2_5": _pct(a["p"]["UST25"]), "btts": _pct(a["p"]["KGVAR"]),
                       "most_likely_score": a["skorlar"][0][0]} for a in liste],
            "note": "the image shows the board; the text introduces it"}


def ayrisma_tweeti(gun: dict, ayar, simdi: datetime) -> str | None:
    liste = [(a, analiz.dikkat_cekici(a)) for a in gun.get("ayrisma") or []
             if datetime.fromisoformat(a["baslama"]) > simdi and analiz.dikkat_cekici(a)]
    if len(liste) < 2:
        return None
    satirlar = [f'- {a["ev"]} v {a["dep"]}: {c["ad"]}, market {_pct(c["piyasa"])} vs stats {_pct(c["istatistik"])}'
                for a, c in liste]
    for n in range(len(satirlar), 1, -1):
        metin = ("📈 WHERE STATS DISAGREE\n\nThe market and the team stats don't agree on these:\n"
                 + "\n".join(satirlar[:n]) + "\n\nWho's right? 👇\n" + ANSVAR)
        if uzunluk(metin) <= LIMIT:
            return metin
    return None
