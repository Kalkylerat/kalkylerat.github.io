"""Kupon dışı, etkileşime açık günlük paylaşımlar: günün maçları, günün istatistiği, anket, skor tahmini, pas günü.

Veri sabah taramasından gelir (gun["vitrin"]): ek API isteği yapılmaz. Her tür günde bir kez, kendi paylaşımlarımız
arasında en az ARALIK_DK olacak şekilde ve maç saatine göre zamanlanır; 15 dakikalık nabız çalıştırır."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import model
from .oddsapi import ima_edilen_goller
from .tweets import ANSVAR, LIMIT, uzunluk

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
        liste.append(((izinli, len(b)), {
            "fixture_id": m["fixture_id"], "lig": m.get("lig", ""), "izinli": izinli, "ev": m["ev"], "dep": m["dep"],
            "baslama": m["baslama"], "p": {k: round(adil[k], 3) for k in ("MS1", "MSX", "MS2")},
            "beklenen_gol": [round(g, 2) for g in goller], "olasi_skor": skor,
        }))
    liste.sort(key=lambda x: x[0], reverse=True)
    return [v for _, v in liste[:VITRIN_MAX]]


def _saat(v: dict, ayar) -> str:
    return datetime.fromisoformat(v["baslama"]).astimezone(ZoneInfo(ayar.saat_dilimi)).strftime("%H:%M %Z")


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
        metin = (f"TODAY'S BIG GAMES | {tarih}\n\n" + "\n".join(satirlar[:n]) +
                 "\n\nWhich one are you watching? 👇")
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
    metin = (f'MATCH POLL | {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n\nWho wins? Vote below 👇\n\n'
             f'Our numbers: {v["ev"]} {_pct(p["MS1"])} · draw {_pct(p["MSX"])} · {v["dep"]} {_pct(p["MS2"])}\n'
             f'Agree or not? Tell us why in the replies.')
    sure = datetime.fromisoformat(v["baslama"]) - datetime.fromisoformat(gun["_simdi"])
    dakika = max(5, min(10080, int(sure.total_seconds() // 60)))
    return metin, [_secenek(v["ev"]), "Draw", _secenek(v["dep"])], dakika


def skor_tweeti(gun: dict, ayar) -> str | None:
    v = skor_maci(gun["vitrin"])
    if not v:
        return None
    ev_g, dep_g = v["beklenen_gol"]
    return (f'SCORE PREDICTION | {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n\n'
            f'Our model\'s most likely score: {v["olasi_skor"].replace("-", "–")}\n'
            f'Expected goals: {ev_g:.1f} – {dep_g:.1f}\n\n'
            f"What's your score? Reply below 👇")


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
    return (f'STAT OF THE DAY | {v["ev"]} v {v["dep"]} · {_saat(v, ayar)}\n\n'
            f'Our model expects {ev_g + dep_g:.1f} goals tonight ({ev_g:.1f} – {dep_g:.1f}).\n'
            f'Most likely score: {v["olasi_skor"].replace("-", "–")}\n\n'
            f'Goals or a tight one? Tell us below 👇')


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
    return {"date": gun["tarih"], "games_checked": gun.get("taranan"), "reason": gun.get("pas_nedeni")}


def pas_tweeti(gun: dict) -> str:
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")
    n = gun.get("taranan")
    bakilan = f"We checked {n} games today." if n else "We checked today's games."
    return (f"NO COUPON TODAY | {tarih}\n\n{bakilan} None had odds good enough for their real chances, "
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
    if vit:
        ilk = min(datetime.fromisoformat(v["baslama"]) for v in vit)
        plan.append(("maclar", ilk - timedelta(hours=5), ilk - timedelta(minutes=15)))
        i = datetime.fromisoformat(istatistik_maci(vit)["baslama"])
        plan.append(("istatistik", i - timedelta(hours=4), i - timedelta(minutes=45)))
        a = datetime.fromisoformat(anket_maci(vit)["baslama"])
        plan.append(("anket", a - timedelta(hours=3), a - timedelta(minutes=30)))
        s = datetime.fromisoformat(skor_maci(vit)["baslama"])
        plan.append(("skor", s - timedelta(minutes=75), s - timedelta(minutes=10)))
    return plan


def paylas(gun: dict, ayar, x, simdi: datetime, yaz=print, yazar=None, diger_paylasimlar: tuple[str, ...] = ()) -> str | None:
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
            return None
        zaman = simdi.isoformat(timespec="seconds")
        try:
            if tur == "anket":
                metin, secenekler, dakika = anket({**gun, "_simdi": zaman}, ayar)
                metin = yazar(tur, olgular(tur, gun, ayar), metin) if yazar else metin
                tid = x.gonder(metin, anket={"options": secenekler, "duration_minutes": dakika})
            else:
                metin = {"pas": lambda: pas_tweeti(gun), "maclar": lambda: maclar_tweeti(gun, ayar),
                         "skor": lambda: skor_tweeti(gun, ayar),
                         "istatistik": lambda: istatistik_tweeti(gun, ayar)}[tur]()
                metin = yazar(tur, olgular(tur, gun, ayar), metin) if yazar else metin
                tid = x.gonder(metin)
        except Exception as e:
            # Tekrar tekrar denenip hata yağmasın: bu tür bugün atlanır.
            durum[tur] = {"durum": "hata", "hata": str(e)[:300], "zaman": zaman}
            yaz(f"⚠️ Etkileşim paylaşımı ({tur}) başarısız: {e}")
            return None
        durum[tur] = {"durum": "paylasildi", "tweet_id": tid, "zaman": zaman}
        yaz(f"Etkileşim paylaşımı ({tur}):\n```\n{metin}\n```")
        return tur
    return None
