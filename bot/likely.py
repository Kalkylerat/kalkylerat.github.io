"""Mr. Likely: ikinci hesap (tahmin/kupon sayfası). İki mod (ayarlar.toml [likely] mod):

"otomatik": kuponu sabit kurallar seçer (otomatik_sec), bot Mr. Likely hesabında paylaşır: kupon postu (görselli),
maçlar bitince sonuç yanıtı, günde bir kupon stratejisi notu. Hesap X'te "Automated" etiketlidir. Sahibine bilgi
GitHub issue'su olarak gider; `iptal` yorumu paylaşılmamış kuponları durdurur.

"elle": Kalkylerat'ın sabah taramasını kullanır (ek API isteği yok) ve X'e HİÇBİR ŞEY paylaşmaz:
1) Sabah: yüksek ihtimalli adaylar (havuz) + hazır örnek kuponlar GitHub issue'su olarak sahibine gider.
2) Sahibi issue'ya yorumla seçer ("C" = hazır kupon, "3 7 12" = kendi kuponu, "pas" = bugün yok).
3) Bot, karakterin (Mr. Likely) ağzından kopyalanmaya hazır post metnini yoruma yazar; postu sahibi elle atar.
4) Maçlar bitince sonuç postunun taslağı ve güncel karne aynı issue'ya gelir.

Bu modül X anahtarı okumaz; X istemcisini çağıran verir (yalnızca otomatik modda). Karne paylaşılan kuponlardan
oluşur; kaybedenler de sayılır, hiçbiri silinmez."""

import itertools
import json
import math
import re
import tomllib
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import analiz, config, denetci, direktor, model
from .tweets import ANSVAR, LIMIT, uzunluk

DOSYA = config.ROOT / "data" / "likely.json"
SES_REHBERI = config.ROOT / "marka" / "MR_LIKELY.md"
ETIKET = "mr-likely"
HARFLER = "ABCDEFGHIJ"
KUPON_ADI = {"gunun-kuponu": "Günün kuponu", "ikinci-kupon": "İkinci kupon"}
MAC_SURESI = timedelta(minutes=105)   # sonuç bu kadar sonra sorulmaya başlanır
VAZGEC = timedelta(hours=30)          # sonuç bu kadar sonra da yoksa ayak iade sayılır
YETKILI = {"OWNER", "MEMBER", "COLLABORATOR"}
PAS = {"pas", "pass", "yok", "bugün yok", "bugun yok"}
IPTAL = {"iptal", "cancel", "sil"}


@dataclass(frozen=True)
class LikelyAyar:
    aktif: bool = False
    min_olasilik: float = 0.65     # havuza girmek için en düşük kazanma ihtimali
    yuksek_olasilik: float = 0.80  # "80+" etiketi
    min_deger: float = -0.05       # oran adil fiyatın en fazla bu kadar altında olabilir
    oran_min: float = 1.10
    oran_max: float = 2.60
    havuz: int = 30
    kupon: int = 10
    min_dakika_once: int = 120     # sahibinin seçip paylaşmasına vakit kalsın
    max_ayak: int = 4
    # "elle": taslak GitHub'a gelir, sahibi seçer ve postu kendisi atar. "otomatik": kuponu kurallar seçer, bot paylaşır.
    mod: str = "elle"
    oto_max_kupon: int = 2
    oto_max_ayak: int = 4
    oto_oran_min: float = 2.0      # kuponun toplam oranı bu aralıkta olur (sahibinin kararı, 6 Ekim 2026)
    oto_oran_max: float = 4.0
    oto_min_ayak: float = 0.65     # sağlam ayağın en düşük kazanma ihtimali
    oto_min_deger: float = -0.04   # ayağın oranı adil fiyatın en fazla bu kadar altında
    oto_min_tutma: float = 0.30    # kuponun en düşük tutma ihtimali; altı paylaşılmaz
    oto_min_kupon_deger: float = -0.08  # kuponun toplam fiyatı adil fiyatın en fazla bu kadar altında
    oto_once_dk: int = 180         # kupon ilk maçtan en erken bu kadar dakika önce paylaşılır
    oto_son_dk: int = 20           # ilk maça bundan az kaldıysa paylaşılmaz
    oto_ders_saati: int = 14       # günün dersi bu saatten (yerel) sonra paylaşılır


def ayar_yukle(path=config.ROOT / "ayarlar.toml") -> LikelyAyar:
    with open(path, "rb") as f:
        t = tomllib.load(f).get("likely", {})
    alanlar = LikelyAyar.__dataclass_fields__
    return LikelyAyar(**{k: type(alanlar[k].default)(v) for k, v in t.items() if k in alanlar})


def yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"gunler": []}


def kaydet(veri: dict) -> None:
    DOSYA.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---------- 1. Aday havuzu ----------

def _aile(pazar: str) -> str:
    """Aynı maçtan iki aday birbirinin tekrarı olmasın: sonuç / gol / korner aileleri."""
    if pazar.startswith("KOR"):
        return "korner"
    return "sonuc" if pazar.startswith(("MS", "CS")) or pazar in ("IY1", "IYX", "IY2") else "gol"


def havuz(analizler: list[dict], oranlar: dict, ayar, cfg: LikelyAyar, simdi: datetime) -> list[dict]:
    """Günün maçlarından yüksek ihtimalli (ve değerli) adaylar; en yüksek ihtimal önce, numaralı (1..N).
    İhtimal: keskin piyasanın marjsız fiyatı. Oran: takipçinin büyük sitelerde bulabileceği fiyat."""
    ayar2 = replace(ayar, guvenli_min_olasilik=cfg.min_olasilik, guvenli_min_deger=cfg.min_deger,
                    oran_min=cfg.oran_min, oran_max=cfg.oran_max)
    en_erken = simdi + timedelta(minutes=cfg.min_dakika_once)
    hepsi = []
    for a in analizler:
        b = oranlar.get(a["fixture_id"])
        if not b or datetime.fromisoformat(a["baslama"]) < en_erken:
            continue
        ist = model.model_olasiliklari(*a["istatistik_gol"]) if a.get("istatistik_gol") else {}
        maclik = []
        for pazar, oran, _, bahisci_oranlari, p, deger, tur, kaynak in model._piyasa_adaylari(
                b, ayar2, a.get("lig_id") in ayar.ligler):
            etiket, _ = model.etiketler(pazar, a["ev"], a["dep"])
            ist_p = ist.get(pazar)
            maclik.append({
                "aday_id": f'{a["fixture_id"]}-{pazar}', "fixture_id": a["fixture_id"], "pazar": pazar, "tur": tur,
                "ev": a["ev"], "dep": a["dep"], "lig": a.get("lig", ""), "baslama": a["baslama"],
                "etiket": etiket, "oran": oran, "site_sayisi": len(bahisci_oranlari),
                "olasilik": round(p, 3), "deger": round(deger, 3), "kaynak": kaynak,
                "istatistik": round(ist_p, 3) if ist_p is not None else None,
                # Takım istatistiği modeli piyasadan belirgin düşükse aday işaretlenir; hazır kuponlara girmez.
                "uyum": ist_p is None or ist_p >= p - ayar.model_tolerans,
                "buyuk": analiz.onemli(a),
                **{k: a[k] for k in ("odds_id", "odds_spor") if k in a},
            })
        # Maç başına en fazla iki aday, farklı ailelerden (aynı fikrin iki hali olmasın).
        maclik.sort(key=lambda c: (c["tur"] != "guvenli", -c["olasilik"]))
        secilen: list[dict] = []
        for c in maclik:
            if len(secilen) < 2 and _aile(c["pazar"]) not in {_aile(s["pazar"]) for s in secilen}:
                secilen.append(c)
        hepsi += secilen
    guvenli = sorted((c for c in hepsi if c["tur"] == "guvenli"), key=lambda c: -c["olasilik"])
    deger = sorted((c for c in hepsi if c["tur"] == "deger"), key=lambda c: -c["deger"])[:6]
    buyuk = [c for c in guvenli if c["buyuk"]][:12]  # büyük maçlar kaçmasın: önce onlara yer ayrılır
    kalan = [c for c in guvenli if c not in buyuk]
    yer = max(cfg.havuz - len(buyuk) - len(deger), 0)
    sonuc = sorted(buyuk + kalan[:yer], key=lambda c: -c["olasilik"]) + deger
    for no, c in enumerate(sonuc, 1):
        c["no"] = no
    return sonuc


# ---------- 2. Kuponlar ----------

def kupon_kur(ayaklar: list[dict], ad: str = "") -> dict:
    """Farklı maçlardan ayaklar: oran = oranların çarpımı, tutma ihtimali = ihtimallerin çarpımı."""
    oran = round(math.prod(a["oran"] for a in ayaklar), 2)
    p = round(math.prod(a["olasilik"] for a in ayaklar), 3)
    return {"ad": ad, "ayaklar": [a["aday_id"] for a in ayaklar], "oran": oran, "olasilik": p,
            "deger": round(p * oran - 1, 3)}


def _farkli_mac(ayaklar) -> bool:
    return len({a["fixture_id"] for a in ayaklar}) == len(ayaklar)


def ornek_kuponlar(adaylar: list[dict], cfg: LikelyAyar) -> list[dict]:
    """Havuzdan en fazla cfg.kupon hazır kupon: tekli, ikili, üçlü; yüksek ihtimal, 80+, büyük maç, değer.
    Kısa kupon önceliklidir (her ayak tutma ihtimalini çarparak düşürür). Aynı kupon iki kez gelmez."""
    saglam = [a for a in adaylar if a["tur"] == "guvenli" and a["uyum"]]
    yuksek = [a for a in saglam if a["olasilik"] >= cfg.yuksek_olasilik]
    buyuk = [a for a in saglam if a["buyuk"]]
    deger = [a for a in adaylar if a["tur"] == "deger" and a["uyum"]]
    en_iyi_fiyat = sorted(saglam, key=lambda a: -a["deger"])

    def kombinasyon(liste, n, ust=8):
        return (k for k in itertools.combinations(liste[:ust], n) if _farkli_mac(k))

    tarifler = [
        ("Tek maç · en yüksek ihtimal", kombinasyon(saglam, 1)),
        ("İkili · en yüksek ihtimal", kombinasyon(saglam, 2)),
        ("Üçlü · 2 sağlam + 1 riskli", (a + (d,) for a in kombinasyon(saglam, 2, 5) for d in deger[:3] if _farkli_mac(a + (d,)))),
        ("İkili · ikisi de 80+", kombinasyon(yuksek, 2)),
        ("İkili · büyük maçlar", kombinasyon(buyuk, 2)),
        ("Üçlü · en yüksek ihtimal", kombinasyon(saglam, 3)),
        ("Tek maç · en iyi fiyat", kombinasyon(en_iyi_fiyat, 1)),
        ("İkili · en iyi fiyat", kombinasyon(en_iyi_fiyat, 2)),
        ("Tek maç · değer", kombinasyon(deger, 1)),
        ("Üçlü · büyük maçlar", kombinasyon(buyuk, 3)),
        ("İkili · sağlam + değer", (k for k in itertools.product(saglam[:4], deger[:3]) if _farkli_mac(k))),
        ("İkili · sıradaki", kombinasyon(saglam, 2)),
        ("Üçlü · sıradaki", kombinasyon(saglam, 3)),
        ("Tek maç · sıradaki", kombinasyon(saglam, 1)),
    ]
    kuponlar, gorulen, kullanim = [], set(), {}
    for ad, uretec in tarifler:
        for k in uretec:
            imza = frozenset(a["aday_id"] for a in k)
            # Aynı ayak en fazla 4 kuponda: tek bir maça bağlı on kupon olmasın.
            if imza in gorulen or any(kullanim.get(a["aday_id"], 0) >= 4 for a in k):
                continue
            gorulen.add(imza)
            for a in k:
                kullanim[a["aday_id"]] = kullanim.get(a["aday_id"], 0) + 1
            kuponlar.append(kupon_kur(list(k), ad))
            break
        if len(kuponlar) >= min(cfg.kupon, len(HARFLER)):
            break
    for harf, k in zip(HARFLER, kuponlar):
        k["harf"] = harf
    return kuponlar


def otomatik_sec(adaylar: list[dict], cfg: LikelyAyar) -> list[dict]:
    """Otomatik modun kuponları (SOZLESME E6): kurallar sabit, sağlanmazsa o gün kupon yok.
    Ayaklar: sağlam adaylar (ihtimal ≥ oto_min_ayak) ve artı değerli adaylar; hepsi istatistikle uyumlu, ihtimali keskin
    piyasadan (ortalamadan değil), oranı adil fiyatın en fazla oto_min_deger altında. Kupon: farklı maçlardan en fazla
    oto_max_ayak ayak, toplam oran oto_oran_min–oto_oran_max arasında, tutma ihtimali ≥ oto_min_tutma, toplam fiyat
    adil fiyatın en fazla oto_min_kupon_deger altında. Bu koşulları
    sağlayanlar içinde TUTMA İHTİMALİ EN YÜKSEK olan seçilir (eşitlikte fiyatı daha iyi, sonra kısa olan).
    İkinci kupon (varsa) aynı kuralla, ilkiyle maç paylaşmayan ayaklardan kurulur."""
    ayaklar = [a for a in adaylar if a["uyum"] and a["deger"] >= cfg.oto_min_deger
               and not a["kaynak"].lower().startswith("average")
               and (a["tur"] == "deger" or a["olasilik"] >= cfg.oto_min_ayak)]
    ayaklar.sort(key=lambda a: -a["olasilik"])
    secilen: list[dict] = []
    dolu: set[int] = set()
    for ad in ("gunun-kuponu", "ikinci-kupon")[:cfg.oto_max_kupon]:
        bos = [a for a in ayaklar if a["fixture_id"] not in dolu][:16]
        uygun = [kupon_kur(list(k), ad) for n in range(1, cfg.oto_max_ayak + 1)
                 for k in itertools.combinations(bos, n) if _farkli_mac(k)]
        uygun = [k for k in uygun if cfg.oto_oran_min <= k["oran"] <= cfg.oto_oran_max and k["olasilik"] >= cfg.oto_min_tutma
                 and k["deger"] >= cfg.oto_min_kupon_deger]
        if not uygun:
            break
        en_iyi = max(uygun, key=lambda k: (k["olasilik"], k["deger"], -len(k["ayaklar"])))
        secilen.append(en_iyi)
        dolu |= {a["fixture_id"] for a in ayaklar if a["aday_id"] in en_iyi["ayaklar"]}
    return secilen


# ---------- 3. Karakterin sesi: post taslakları ----------

ACILIS = {
    1: ["One pick today. Keeping it simple.", "Just the one today.", "A single. Boring is underrated.",
        "One game, one opinion.", "Not forcing a double today. One pick.", "Today's pick, singular."],
    2: ["Today's double. Two legs, no heroics.", "Two picks, one coupon.", "A double today. Short and sensible.",
        "Two legs. That's the whole plan.", "Pairing these two today.", "Double for today, nothing clever."],
    3: ["Today's treble.", "Three legs today.", "A treble. One leg more than I'd like, as usual.",
        "Three picks, one coupon.", "Treble for today. Nothing fancy in it.", "Three legs. All of them dull, which is the point.",
        "Today's three."],
    4: ["Four legs today.", "A four-fold. Every leg is one more way to lose, so they're the dull sort.",
        "Today's four.", "Four picks, one coupon.", "Four-fold today. I've kept the legs boring on purpose.",
        "Four legs. Yes, I know what I say about long coupons.", "Today's four-fold."],
}
KAPANIS = ["Probably.", "No promises.", "We'll see.", "That's the maths, not a promise.", "Likely. Not certain.",
           "As ever: likely, not certain."]
TUTTU = ["That'll do.", "Landed. I'll try not to be smug about it.", "In. Nice when the maths behaves.",
         "Home. On to the next one.", "Done. Probably deserved it too."]
YATTI = ["That's the part of the percentage nobody likes.", "Annoying. Still the right kind of coupon.",
         "It happens. More often than any of us would like.", "No excuses, it lost.",
         "Football did a football. Moving on."]
SEKTI = ["One leg short. The classic.", "So close it hurts a bit.", "One out. Always one."]


def _sec(liste: list[str], tohum: str) -> str:
    """Aynı gün/kupon için hep aynı, günden güne değişen seçim (rastgele değil: önizleme ile post aynı olsun)."""
    return liste[sum(ord(c) for c in tohum) % len(liste)]


def _pct(p: float) -> str:
    return f"{round(100 * p)}%"


def _kisalt(*secenekler: str) -> str:
    """Sınıra sığan ilk seçenek; hiçbiri sığmazsa son (en kısa) seçenek."""
    return next((s for s in secenekler if uzunluk(s) <= LIMIT), secenekler[-1])


def kupon_metni(kupon: dict, ayaklar: list[dict], tohum: str, gorselli: bool = False) -> str:
    """Kupon postunun şablonu (Mr. Likely'nin sesi). Rakamlar kayıttan; tutma ihtimali ve kaybetme payı açıkça yazılır.
    gorselli: oyunlar ve oranlar kupon kartında; metne sığmazsa maç adları ve toplam oranla kısa, sesli hali kullanılır."""
    n = len(ayaklar)
    acilis = _sec(ACILIS[min(n, 4)], tohum)
    uzun = [f'⚽ {a["ev"]} v {a["dep"]}: {a["etiket"]} · {a["oran"]:.2f}' for a in ayaklar]
    kisa = [f'⚽ {a["etiket"]} ({a["ev"]} v {a["dep"]}) {a["oran"]:.2f}' for a in ayaklar]
    p = kupon["olasilik"]
    if n == 1:
        ozet = f"I make it about {_pct(p)} to land, so it loses roughly {round(10 * (1 - p))} times in 10. {_sec(KAPANIS, tohum)}"
        ozet_kisa = f"About {_pct(p)} to land."
    else:
        ozet = (f"Combined {kupon['oran']:.2f}. I make it about {_pct(p)} to land, "
                f"so it loses roughly {round(10 * (1 - p))} times in 10. {_sec(KAPANIS, tohum)}")
        ozet_kisa = f"Combined {kupon['oran']:.2f}, about {_pct(p)} to land."
    son = f"\n\n{ANSVAR}"
    maclar = ", ".join(f'{a["ev"]} v {a["dep"]}' for a in ayaklar) + "."
    return _kisalt(
        f"{acilis}\n\n" + "\n".join(uzun) + f"\n\n{ozet}{son}",
        *([f"{acilis}\n\n{maclar}\n\n{ozet}{son}", f"{acilis}\n\n{maclar}\n\n{ozet_kisa}{son}"] if gorselli else []),
        "\n".join(uzun) + f"\n\n{ozet}{son}",
        "\n".join(uzun) + f"\n\n{ozet_kisa}{son}",
        "\n".join(kisa) + f"\n\n{ozet_kisa}{son}",
    )


def _birim(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}{abs(x):.2f}"


def karne(veri: dict) -> dict:
    """Sonuçlanan seçili kuponlar: her kupon 1 birim. Tutan (oran − 1) kazandırır, yatan 1 kaybettirir, iade 0."""
    kuponlar = [k for g in veri["gunler"] for k in g.get("secilen", []) if k["durum"] in ("tuttu", "yatti", "iade")
                and (not k.get("oto") or k.get("tweet_id"))]  # otomatik kupon ancak paylaşıldıysa sayılır
    sayilan = [k for k in kuponlar if k["durum"] != "iade"]
    kar = sum(k["son_oran"] - 1 if k["durum"] == "tuttu" else -1 for k in sayilan)
    return {"kupon": len(sayilan), "tutan": sum(k["durum"] == "tuttu" for k in sayilan), "kar": round(kar, 2),
            "roi": round(kar / len(sayilan), 3) if sayilan else 0.0}


def karne_satiri(k: dict) -> str:
    return f'Record: {k["tutan"]} of {k["kupon"]} landed.'


def sonuc_metni(kupon: dict, k: dict, tohum: str) -> str:
    """Sonuç postunun şablonu: tutan da yatan da aynı açıklıkla, güncel karneyle."""
    ayaklar = kupon["ayaklar"]
    skorlar = [f'{"✅" if a["durum"] == "kazandi" else "↩️" if a["durum"] == "iade" else "❌"} '
               f'{a["ev"]} {a["skor"] or "void"} {a["dep"]}: {a["etiket"]}' for a in ayaklar]
    yatan = sum(a["durum"] == "kaybetti" for a in ayaklar)
    if kupon["durum"] == "tuttu":
        bas = f'{"Both legs in" if len(ayaklar) == 2 else "All in" if len(ayaklar) > 2 else "In"} at {kupon["son_oran"]:.2f}. {_sec(TUTTU, tohum)}'
    elif kupon["durum"] == "iade":
        bas = "Void. Game off, coupon off, nothing won and nothing lost."
    elif len(ayaklar) > 1 and yatan == 1:
        bas = f"{_sec(SEKTI, tohum)} Coupon down."
    else:
        bas = f"Coupon down. {_sec(YATTI, tohum)}"
    if kupon["durum"] == "yatti":
        bas += f" I had it at {_pct(kupon['olasilik'])}, which was never 100."
    son = f"\n\n{karne_satiri(k)}\n{ANSVAR}"
    return _kisalt(f"{bas}\n\n" + "\n".join(skorlar) + son,
                   f"{bas.split('. ')[0]}.\n\n" + "\n".join(skorlar) + son,
                   f"{bas.split('. ')[0]}.{son}")


# Günün dersi: kupon stratejisi üzerine kısa, dürüst notlar (ayrı post). Her biri 280 sınırında ve 18+ ile biter.
DERSLER = [
    "Three legs at 80% each is a 51% coupon. Four is 41%. The legs don't know about each other, they just multiply.\n\nShorter coupons. That's the whole secret.",
    "A pick that wins 80% of the time still loses one week in five. If one loss wrecks your month, the stake was the problem, not the pick.",
    "\"High odds\" and \"good odds\" are different things. Good means the price is bigger than the real chance deserves. A 1.30 can be good. A 12.00 can be terrible.",
    "The quickest way to lose a good coupon is adding one more leg \"to boost the price\". That leg is where the money goes.",
    "Same stake every coupon. Not double after a loss, not triple when you \"feel it\". Feelings are not a staking plan.",
    "If you can't say roughly how often your coupon should win, you're not placing a coupon, you're buying a raffle ticket.",
    "Chasing losses is just paying twice for the same bad evening. Close the app. The fixtures will still be there tomorrow.",
    "Two picks from the same match usually lean on the same story. If the story is wrong, both go. Spread your legs across different games.",
    "Favourites lose. A team priced at 75% to win fails one time in four, and nobody posts those screenshots.",
    "A winning week proves almost nothing. A losing week proves almost nothing. Ask me again after 200 coupons.",
    "Only stake money you'd be fine never seeing again. If that sentence stings, the stake is too big.",
    "Before you place it, check the price somewhere else. The same pick at 1.40 and at 1.50 is not the same coupon over a season.",
    "The big 10-leg winners you see online are survivors. For every one of those there's a drawer full of losers nobody shows you.",
    "Keeping a record is boring and it's the only way to know if you're any good. Every coupon, wins and losses. Mine's all here.",
    "\"It was so close\" pays the same as \"it was miles off\". Don't raise stakes because a coupon nearly landed.",
    "No good pick today is a perfectly fine day. Passing is a decision, and some days it's the smartest one on the board.",
    "Late team news moves prices for a reason. If your pick needed a striker who's now on the bench, the pick has changed.",
    "A double at 1.60 that lands six times in ten beats a 9.00 dream that lands once in fifteen. Slow is fine.",
    "Don't back your own club. You already think they'll win every week, and the price doesn't care about your scarf.",
    "Set the amount before the weekend starts and stop when it's gone. Deciding in the 80th minute never ends well.",
    "Over 1.5 goals feels safe until the 0-0. Around one top-flight game in four finishes with fewer than two goals.",
]


def ders_metni(tarih: str, atla: int = 0) -> str:
    gun = datetime.fromisoformat(tarih).timetuple().tm_yday
    return f"{DERSLER[(gun + atla) % len(DERSLER)]}\n\n{ANSVAR}"


SES_SISTEM = """You write posts for "Mr. Likely", a football coupon account on X. The coupons are picked by a numbers
model with fixed rules; Mr. Likely is the voice that presents them. You get a draft with the exact facts; rewrite it
in his voice. Never claim a human hand-picked a coupon or watched a match.

Voice: a dry, good-humoured bloke who likes numbers and never promises anything. Short sentences, everyday words,
contractions, a little self-mockery. He says "probably", "likely", "I make it about 61%". He owns his losses in plain
words and never sulks or blames referees. He is not a salesman and not a guru.

Hard rules:
- Max 280 characters (emojis count double). Keep the last line exactly "18+ | Play responsibly".
- Keep every match, every pick and every number from the draft exactly as written. Add no new numbers, stats, news,
  injuries, quotes or backstory. Never invent a past win or a track record.
- Never say or imply a pick is certain: no "lock", "banker", "sure", "guaranteed", "can't lose", "free money", "easy".
- No links, no @ mentions, no hashtags, no bookmaker or site names, no "DM me", no "join", no selling.
- Never tell people to bet more, chase losses or borrow. Never claim betting is a way to make a living.
- Sound like a person: no "Here's the thing", "The result?", "It's not X, it's Y", no hype words, at most one dash.
  Vary the opening; don't start two posts the same way."""
SES_SEMA = {"type": "object", "properties": {"metin": {"type": "string"}}, "required": ["metin"],
            "additionalProperties": False}


def ses_notlari() -> str:
    """Rehberin yalnızca karakter bölümü ("## Who he is" başlığından sonraki başlığa kadar)."""
    try:
        metin = SES_REHBERI.read_text(encoding="utf-8")
    except OSError:
        return ""
    _, _, kalan = metin.partition("## Who he is")
    return kalan.split("\n## ")[0].strip() if kalan else ""


def ses_uygun(metin: str, sablon: str, zorunlu: list[str]) -> list[str]:
    """Yazılan metin kurallara uyuyor mu? Boş liste = uygun. Uymazsa şablon kullanılır."""
    sorun = []
    if not metin or uzunluk(metin) > LIMIT:
        sorun.append("uzunluk")
    if not metin.rstrip().endswith(ANSVAR):
        sorun.append("18+ satırı yok")
    if denetci._KESINLIK.search(metin) or re.search(r"\beasy (win|money)\b|\bsafe bet\b", metin, re.IGNORECASE):
        sorun.append("kesinlik dili")
    if denetci._LINK.search(metin) or denetci._SITE.search(metin) or "#" in metin:
        sorun.append("link/site/etiket")
    if not direktor.sayilar_dogru(metin, sablon):
        sorun.append("şablonda olmayan sayı")
    if any(z not in metin for z in zorunlu):
        sorun.append("eksik maç/oyun/oran")
    if direktor.yz_izi(metin):
        sorun.append("yapay zekâ izi")
    return sorun


def ses_yaz(ayar, sablon: str, zorunlu: list[str], client=None, yaz=print) -> str:
    """Şablonu karakterin sesiyle yeniden yazdırır; hata ya da kural dışı metinde şablon döner."""
    try:
        import anthropic
        rehber = ses_notlari()
        cevap = direktor._cagir(client or anthropic.Anthropic(),
                                [(ayar.direktor_model, ayar.direktor_effort), (ayar.claude_model, "low")],
                                SES_SISTEM + ("\n\nCharacter notes from the owner:\n" + rehber if rehber else ""),
                                f"Draft with the exact facts:\n\n{sablon}", SES_SEMA, 4000)
    except Exception as e:
        yaz(f"Mr. Likely metni yazılamadı ({e}); şablon kullanıldı.")
        return sablon
    metin = (cevap.get("metin") or "").strip()
    sorun = ses_uygun(metin, sablon, zorunlu)
    if sorun:
        yaz(f"Mr. Likely metni kurala uymadı ({', '.join(sorun)}); şablon kullanıldı.")
        return sablon
    return metin


def _zorunlu(ayaklar: list[dict]) -> list[str]:
    return [x for a in ayaklar for x in (a["ev"], a["dep"], f'{a["oran"]:.2f}')]


# ---------- 4. Sabah paketi (issue) ----------

def _saat(iso: str, ayar) -> str:
    return datetime.fromisoformat(iso).astimezone(ZoneInfo(ayar.saat_dilimi)).strftime("%H:%M")


def _ayak_satiri(a: dict, ayar) -> str:
    return (f'{a["ev"]} v {a["dep"]} ({_saat(a["baslama"], ayar)}) · **{a["etiket"]}** · oran {a["oran"]:.2f} · '
            f'ihtimal %{round(100 * a["olasilik"])}')


def _not(a: dict, cfg: LikelyAyar) -> str:
    notlar = []
    if a["tur"] == "deger":
        notlar.append("💎 değer")
    elif a["olasilik"] >= cfg.yuksek_olasilik:
        notlar.append("🟢 80+")
    if a["buyuk"]:
        notlar.append("⭐ büyük maç")
    if not a["uyum"]:
        notlar.append(f'⚠️ istatistik %{round(100 * a["istatistik"])} diyor')
    if a["kaynak"].lower().startswith("average"):
        notlar.append("ihtimal ortalamadan")
    return ", ".join(notlar)


def paket_metni(gun: dict, veri: dict, ayar, cfg: LikelyAyar) -> str:
    adaylar, harita = gun["havuz"], {a["aday_id"]: a for a in gun["havuz"]}
    k = karne(veri)
    if gun.get("oto"):
        s = [f"Mr. Likely ({gun['tarih']}) **otomatik modda**: kuponu kurallar seçti, bot paylaşacak. Bir şey yapmana gerek yok.", ""]
        for kp in gun["secilen"]:
            s += [f'**{KUPON_ADI.get(kp["ad"], kp["ad"])}** · oran {kp["oran"]:.2f} · tutma %{round(100 * kp["olasilik"])} · '
                  f'değer {round(100 * kp["deger"]):+d}% · paylaşım **{_saat(kp["paylas"], ayar)}**']
            s += [f"- {_ayak_satiri(a, ayar)}" for a in kp["ayaklar"]] + [""]
        if not gun["secilen"]:
            s += ["Bugün kurallara uyan kupon çıkmadı; kupon paylaşılmayacak (günün dersi yine çıkar).", ""]
        s += ["Bugünün paylaşılmamış kuponlarını durdurmak için bu issue'ya `iptal` yaz.", ""]
        t = gun.get("tani")
        if t:
            s += [f"Tarama: {t['mac']} maç, {t['oranli']} tanesinin oranı var. Büyük maç: {t['buyuk']}, oranı olan {t['buyuk_oranli']}, "
                  f"adayı çıkan {t['buyuk_aday']}.", ""]
            if t.get("buyukler"):
                s += ["<details><summary>Büyük maçların durumu</summary>", "",
                      "| Maç | Bahisçi | Keskin | Zorunlu | En olası oyun | İhtimal | Oran | Değer | Site |", "|---|---|---|---|---|---|---|---|---|"]
                s += [f"| {b['mac']} | {b['bahisci']} | {'var' if b['keskin'] else 'yok'} | {'var' if b['zorunlu'] else 'yok'} | "
                      + (f"{b['oyun']} | %{round(100 * b['olasilik'])} | {b['oran']:.2f} | {round(100 * b['deger']):+d}% | "
                         f"{b['site']}{'' if b['zorunlu_oyunda'] else ' (zorunlu yok)'} |" if "oyun" in b else "- | - | - | - | - |")
                      for b in t["buyukler"]]
                s += ["", "</details>", ""]
    else:
        s = [f"Mr. Likely günün paketi ({gun['tarih']}). **Bu issue'ya yorum yazarak seç:**",
             "- Hazır kupon: harfini yaz → `C`",
             "- Kendi kuponun: aday numaraları → `3 7 12`",
             "- Birden fazla kupon: araya `/` koy → `C / 3 7`",
             "- Bugün kupon yok: `pas`",
             "",
             "Birkaç dakika içinde kopyalanacak post metni buraya gelir; postu X'te **sen** atarsın (ilk maçtan önce). "
             "Seçtiğin her kupon karneye yazılır, kaybeden de. Vazgeçersen maç başlamadan `iptal` yaz.",
             ""]
    s += [
         f"**Karne:** {k['kupon']} kupon, {k['tutan']} tuttu."
         if k["kupon"] else "**Karne:** henüz sonuçlanan kupon yok.",
         "", "## Hazır kuponlar" + (" (bilgi için; otomatik modda seçilmez)" if gun.get("oto") else ""),
         "Tutma ihtimali ayakların ihtimallerinin çarpımıdır. Değer: artıysa oran ihtimale göre iyi, eksiyse bahisçi payı kadar pahalı."]
    for kp in gun["kuponlar"]:
        s += ["", f'**{kp["harf"]} · {kp["ad"]}** · oran {kp["oran"]:.2f} · tutma %{round(100 * kp["olasilik"])} · '
                  f'değer {round(100 * kp["deger"]):+d}%']
        s += [f"- {_ayak_satiri(harita[i], ayar)}" for i in kp["ayaklar"]]
    if not gun["kuponlar"]:
        s += ["", "Bugün hazır kupon çıkmadı (ölçütü geçen aday yok ya da az). `pas` yazabilirsin."]
    s += ["", f"## Adaylar ({len(adaylar)})", "",
          "| # | Maç | Saat | Oyun | Oran | İhtimal | Değer | Not |", "|---|---|---|---|---|---|---|---|"]
    s += [f'| {a["no"]} | {a["ev"]} v {a["dep"]} | {_saat(a["baslama"], ayar)} | {a["etiket"]} | {a["oran"]:.2f} | '
          f'%{round(100 * a["olasilik"])} | {round(100 * a["deger"]):+d}% | {_not(a, cfg)} |' for a in adaylar]
    s += ["", "## Günün dersi (ayrı post, istersen)", "```", gun["ders"], "```"]
    return "\n".join(s)


def _buyuk_tani(a: dict, b: dict, ayar, cfg: LikelyAyar) -> dict:
    """Büyük maçın adayı neden çıktı/çıkmadı: kaç bahisçi var, keskin ve zorunlu bahisçi var mı, en yüksek ihtimalli
    oyunun fiyatı nasıl. Günlük bildirimde görünür (büyük maç kaçıyorsa nedeni belli olsun)."""
    adil, _ = model.adil_olasiliklar(b, ayar.keskin_bahisci) if b else ({}, {})
    fiyat = model.piyasa_oranlari(b, ayar.oran_bahiscileri, ayar.oran_yontemi) if b else {}
    en_iyi = max(((p, pz) for pz, p in adil.items() if pz in fiyat and cfg.oran_min <= fiyat[pz][0] <= cfg.oran_max),
                 default=None)
    kayit = {"mac": f'{a["ev"]} v {a["dep"]}', "bahisci": len(b),
             "keskin": any(ad.lower() == ayar.keskin_bahisci.lower() for ad in b),
             "zorunlu": all(any(ad.lower() == z.lower() for ad in b) for z in ayar.zorunlu_bahisciler)}
    if en_iyi:
        p_, pz = en_iyi
        oran, _, siteler = fiyat[pz]
        kayit.update(oyun=model.etiketler(pz, a["ev"], a["dep"])[0], olasilik=round(p_, 3), oran=oran,
                     deger=round(p_ * oran - 1, 3), site=len(siteler),
                     zorunlu_oyunda=all(any(ad.lower() == z.lower() for ad in siteler) for z in ayar.zorunlu_bahisciler))
    return kayit


def sabah(ayar, analizler: list[dict], oranlar: dict, simdi: datetime, gh, yaz=print) -> dict | None:
    """Günün paketini hazırlar ve issue olarak gönderir. Bugün zaten gönderildiyse ya da kapalıysa None."""
    cfg = ayar_yukle()
    if not cfg.aktif:
        return None
    veri = yukle()
    tarih = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    if any(g["tarih"] == tarih for g in veri["gunler"]):
        return None
    adaylar = havuz(analizler, oranlar, ayar, cfg, simdi)
    gun = {"tarih": tarih, "olusturma": simdi.isoformat(timespec="seconds"), "durum": "bekliyor",
           "havuz": adaylar, "kuponlar": ornek_kuponlar(adaylar, cfg), "secilen": [], "islenen": [],
           "ders": ders_metni(tarih)}
    buyukler = [a for a in analizler if analiz.onemli(a) and datetime.fromisoformat(a["baslama"]) >= simdi + timedelta(minutes=cfg.min_dakika_once)]
    gun["tani"] = {"mac": len(analizler), "oranli": sum(1 for a in analizler if oranlar.get(a["fixture_id"])),
                   "buyuk": len(buyukler), "buyuk_oranli": sum(1 for a in buyukler if oranlar.get(a["fixture_id"])),
                   "buyuk_aday": len({a["fixture_id"] for a in adaylar if a["buyuk"]})}
    gun["tani"]["buyukler"] = [_buyuk_tani(a, oranlar.get(a["fixture_id"]) or {}, ayar, cfg) for a in buyukler][:15]
    oto = cfg.mod == "otomatik"
    if oto:
        harita = {a["aday_id"]: a for a in adaylar}
        onceki = None
        for k in otomatik_sec(adaylar, cfg):
            d = _dondur([harita[i] for i in k["ayaklar"]], k["ad"], simdi)
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in d["ayaklar"])
            # İlk maçtan oto_once_dk önce (en geç 45 dk önce); iki kupon arasında en az 40 dk.
            zaman = min(max(simdi + timedelta(minutes=5), ilk - timedelta(minutes=cfg.oto_once_dk)), ilk - timedelta(minutes=45))
            if onceki:
                zaman = max(zaman, onceki + timedelta(minutes=40))
            onceki = zaman
            d.update(oto=True, paylas=zaman.isoformat(timespec="seconds"))
            gun["secilen"].append(d)
        gun["durum"] = "secildi" if gun["secilen"] else "bekliyor"
        gun["oto"] = True
    govde = (f"@{ayar.alarm_kime} " if ayar.alarm_kime else "") + paket_metni(gun, veri, ayar, cfg)
    baslik = (f"🎩 Mr. Likely {tarih}: otomatik, {len(gun['secilen'])} kupon paylaşılacak" if oto
              else f"🎩 Mr. Likely {tarih}: {len(adaylar)} aday, {len(gun['kuponlar'])} kupon")
    gun["issue"] = gh.issue_ac(baslik, govde, ETIKET)
    veri["gunler"].append(gun)
    for eski in veri["gunler"][:-14]:  # eski günlerde yalnızca seçilen kuponlar (karne) kalır; dosya büyümesin
        eski.pop("havuz", None)
        eski.pop("kuponlar", None)
    kaydet(veri)
    yaz(f"Mr. Likely paketi gönderildi (issue #{gun['issue']}): {len(adaylar)} aday, {len(gun['kuponlar'])} kupon.")
    return gun


# ---------- 5. Sahibinin seçimi (yorum) ----------

def secim_coz(metin: str) -> list | str | None:
    """Yorumu komuta çevirir: "pas", "iptal", ya da kupon listesi (harf = hazır kupon, sayı listesi = kendi kuponu).
    Komut gibi görünmeyen yorum None döner (sohbet/not olabilir)."""
    temiz = metin.strip().lower().strip(".!")
    if temiz in PAS:
        return "pas"
    if temiz in IPTAL:
        return "iptal"
    kuponlar = []
    for parca in re.split(r"[/\n]+", metin):
        parca = parca.strip().strip(".")
        if not parca:
            continue
        if re.fullmatch(r"[A-Ja-j]", parca):
            kuponlar.append(parca.upper())
        elif re.fullmatch(r"\d{1,2}([\s,+]+\d{1,2})*", parca):
            kuponlar.append([int(x) for x in re.findall(r"\d+", parca)])
        else:
            return None
    return kuponlar or None


def _kupon_olustur(gun: dict, istek, cfg: LikelyAyar, simdi: datetime) -> tuple[dict | None, str]:
    """(kupon, hata). Hazır kuponun ya da numaralardan kurulan kuponun, ayak ayrıntılarıyla dondurulmuş kaydı."""
    harita = {a["aday_id"]: a for a in gun["havuz"]}
    if isinstance(istek, str):
        hazir = next((k for k in gun["kuponlar"] if k["harf"] == istek), None)
        if not hazir:
            return None, f"`{istek}` diye bir hazır kupon yok."
        ayaklar, ad = [harita[i] for i in hazir["ayaklar"]], istek
    else:
        nolar = {a["no"]: a for a in gun["havuz"]}
        eksik = [n for n in istek if n not in nolar]
        if eksik:
            return None, f"Aday numarası yok: {', '.join(map(str, eksik))}."
        ayaklar, ad = [nolar[n] for n in dict.fromkeys(istek)], "+".join(map(str, dict.fromkeys(istek)))
        if not _farkli_mac(ayaklar):
            return None, f"`{ad}`: aynı maçtan iki oyun var. Aynı maçın oyunları birbirine bağlıdır, tutma ihtimali doğru hesaplanamaz; her maçtan tek oyun seç."
        if len(ayaklar) > cfg.max_ayak:
            return None, f"`{ad}`: en fazla {cfg.max_ayak} maç. Uzun kuponun tutma ihtimali hızla düşer."
    baslamis = [a for a in ayaklar if datetime.fromisoformat(a["baslama"]) <= simdi]
    if baslamis:
        return None, f"`{ad}`: {baslamis[0]['ev']} v {baslamis[0]['dep']} başlamış; maç başladıktan sonra kupon paylaşılmaz."
    return _dondur(ayaklar, ad, simdi), ""


def _dondur(ayaklar: list[dict], ad: str, simdi: datetime) -> dict:
    """Kuponun, ayak ayrıntılarıyla dondurulmuş kaydı (havuz sonradan silinse de sonuçlandırılabilsin)."""
    k = kupon_kur(ayaklar, ad)
    k.update(ayaklar=[{**{x: a[x] for x in ("aday_id", "fixture_id", "pazar", "ev", "dep", "lig", "baslama", "etiket",
                                             "oran", "olasilik", "deger") if x in a},
                       **{x: a[x] for x in ("odds_id", "odds_spor") if x in a},
                       "durum": "bekliyor", "skor": None} for a in ayaklar],
             durum="bekliyor", secim=simdi.isoformat(timespec="seconds"))
    return k


def _yetkili(gh, y: dict) -> bool:
    if (y.get("user") or {}).get("type") == "Bot":
        return False
    return y.get("author_association") in YETKILI or gh.yetkili(y["user"]["login"])


YARDIM = ("Anlayamadım. Örnekler: `C` (hazır kupon), `3 7 12` (kendi kuponun), `C / 3 7` (iki kupon), "
          "`pas` (bugün yok), `iptal` (seçimi geri al).")


def kontrol(ayar, gh, simdi: datetime, yazici=None, yaz=print) -> int:
    """Açık paketlerdeki yeni yorumları işler. İşlenen komut sayısını döndürür."""
    cfg = ayar_yukle()
    if not cfg.aktif:
        return 0
    veri = yukle()
    yazici = yazici or (lambda sablon, zorunlu: sablon)
    islenen = 0
    for gun in veri["gunler"][-4:]:
        if gun["durum"] not in ("bekliyor", "secildi") or not gun.get("issue"):
            continue
        for y in gh.yorumlar(gun["issue"]):
            if y["id"] in gun["islenen"] or not _yetkili(gh, y):
                continue
            gun["islenen"].append(y["id"])
            komut = secim_coz(y.get("body") or "")
            islenen += 1
            if gun.get("oto"):
                # Otomatik mod: kuponu kurallar seçer; sahibi yalnızca paylaşılmamış kuponları durdurabilir.
                if komut in ("iptal", "pas"):
                    kalan = [k for k in gun["secilen"] if k.get("tweet_id")]
                    silinen = len(gun["secilen"]) - len(kalan)
                    gun["secilen"] = kalan
                    gh.yorum(gun["issue"], f"{silinen} kupon durduruldu, paylaşılmayacak."
                                           + (" Paylaşılmış kuponlar karnede kalır." if kalan else ""))
                else:
                    gh.yorum(gun["issue"], "Otomatik modda kuponu kurallar seçer. Bugünün paylaşılmamış kuponlarını durdurmak "
                                           "için `iptal` yaz; elle seçime dönmek için Claude'a söyle.")
            elif komut is None:
                gh.yorum(gun["issue"], YARDIM)
            elif komut == "pas":
                if gun["secilen"]:
                    gh.yorum(gun["issue"], "Bugün zaten kupon seçtin. Geri almak için `iptal` yaz.")
                else:
                    gun["durum"] = "pas"
                    gh.kapat(gun["issue"], "Tamam, bugün kupon yok. Pas da bir karardır; karneye bir şey yazılmadı.")
            elif komut == "iptal":
                kalan = [k for k in gun["secilen"] if k["durum"] != "bekliyor"
                         or min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"]) <= simdi]
                silinen = len(gun["secilen"]) - len(kalan)
                gun["secilen"] = kalan
                gun["durum"] = "secildi" if kalan else "bekliyor"
                gh.yorum(gun["issue"], f"{silinen} kupon geri alındı, karneye yazılmayacak. "
                                       + ("Maçı başlamış kuponlar geri alınamaz, onlar karnede kalır. " if kalan else "")
                                       + "X'e attıysan postu da silmeyi unutma. Yeniden seçebilirsin.")
            else:
                cevap = []
                for istek in komut:
                    kupon, hata = _kupon_olustur(gun, istek, cfg, simdi)
                    if not kupon:
                        cevap.append(f"⚠️ {hata}")
                        continue
                    if any({a["aday_id"] for a in k["ayaklar"]} == {a["aday_id"] for a in kupon["ayaklar"]}
                           for k in gun["secilen"]):
                        cevap.append(f"`{kupon['ad']}` zaten seçili.")
                        continue
                    sablon = kupon_metni(kupon, kupon["ayaklar"], gun["tarih"] + kupon["ad"])
                    kupon["metin"] = yazici(sablon, _zorunlu(kupon["ayaklar"]))
                    gun["secilen"].append(kupon)
                    gun["durum"] = "secildi"
                    ilk = min(a["baslama"] for a in kupon["ayaklar"])
                    cevap += [f"### Kupon `{kupon['ad']}` · oran {kupon['oran']:.2f} · tutma %{round(100 * kupon['olasilik'])}",
                              f"En geç **{_saat(ilk, ayar)}**'den (ilk maç) önce at. Metni kendi cümlenle değiştirebilirsin; "
                              "maçları, oyunları ve oranları değiştirme.",
                              "```", kupon["metin"], "```"]
                    if kupon["olasilik"] < 0.35:
                        cevap.append(f"Not: bu kupon 10 denemenin yaklaşık {round(10 * (1 - kupon['olasilik']))}'inde yatar. Yine de senin kararın.")
                gh.yorum(gun["issue"], "\n".join(cevap))
    kaydet(veri)
    if islenen:
        yaz(f"Mr. Likely: {islenen} yorum işlendi.")
    return islenen


# ---------- 6. Sonuçlar ----------

def _kupon_sonucu(kupon: dict) -> None:
    durumlar = [a["durum"] for a in kupon["ayaklar"]]
    if "kaybetti" in durumlar:
        kupon["durum"] = "yatti"
    elif "bekliyor" in durumlar:
        return
    elif all(d == "iade" for d in durumlar):
        kupon["durum"] = "iade"
    else:
        kupon["durum"] = "tuttu"
    # İade edilen ayak 1.00 sayılır (bahis sitelerinin kuralı).
    kupon["son_oran"] = round(math.prod(a["oran"] for a in kupon["ayaklar"] if a["durum"] == "kazandi"), 2)


def sonuclar(ayar, sonuc_al, gh, simdi: datetime, yazici=None, yaz=print) -> int:
    """Seçili kuponların biten maçlarını sonuçlandırır; kupon bitince sonuç postunun taslağını issue'ya yazar.
    sonuc_al(maclar, korner_idleri) -> {fixture_id: {"durum", "skor", "iy", "korner"}}. Biten kupon sayısını döndürür."""
    if not ayar_yukle().aktif:
        return 0
    veri = yukle()
    yazici = yazici or (lambda sablon, zorunlu: sablon)
    biten = 0
    for gun in veri["gunler"][-6:]:
        acik = [k for k in gun.get("secilen", []) if not k.get("sonuc_metni")]  # yatan kuponun kalan maçları da beklenir
        sorulacak = {a["fixture_id"]: a for k in acik for a in k["ayaklar"]
                     if a["durum"] == "bekliyor" and datetime.fromisoformat(a["baslama"]) + MAC_SURESI <= simdi}
        if not sorulacak:
            continue
        cevap = sonuc_al(list(sorulacak.values()),
                         {a["fixture_id"] for k in acik for a in k["ayaklar"] if a["pazar"].startswith("KOR")})
        for k in acik:
            for a in k["ayaklar"]:
                r = cevap.get(a["fixture_id"]) or {"durum": "bekliyor"}
                if a["durum"] != "bekliyor":
                    continue
                gec = datetime.fromisoformat(a["baslama"]) + VAZGEC <= simdi
                if r["durum"] == "bitti":
                    kazandi = model.kazandi_mi(a["pazar"], *r["skor"], iy=r.get("iy"), korner=r.get("korner"))
                    if kazandi is None and not gec:
                        continue  # ilk yarı skoru / korner sayısı henüz yok: sonraki kontrolde
                    a["skor"] = f'{r["skor"][0]}-{r["skor"][1]}'
                    a["durum"] = "iade" if kazandi is None else "kazandi" if kazandi else "kaybetti"
                elif r["durum"] == "iptal" or gec:
                    a["durum"] = "iade"
            _kupon_sonucu(k)
            # Yatan kupon da bütün maçları bitince duyurulur (sonuç postunda hepsinin skoru olsun).
            if k["durum"] != "bekliyor" and all(a["durum"] != "bekliyor" for a in k["ayaklar"]) and not k.get("sonuc_metni"):
                biten += 1
                sablon = sonuc_metni(k, karne(veri), gun["tarih"] + k["ad"])
                k["sonuc_metni"] = yazici(sablon, [x for a in k["ayaklar"] for x in (a["ev"], a["dep"])])
                if gun.get("issue"):
                    gh.yorum(gun["issue"], f"### Sonuç: kupon `{k['ad']}` "
                                           f"{'✅ tuttu' if k['durum'] == 'tuttu' else '↩️ iade' if k['durum'] == 'iade' else '❌ yattı'}\n"
                                           "Sonuç postu (kupon postunun altına yanıt olarak at):\n```\n" + k["sonuc_metni"] + "\n```")
        if gun["durum"] == "secildi" and all(k.get("sonuc_metni") for k in gun["secilen"]):
            gun["durum"] = "bitti"
            kr = karne(veri)
            if gun.get("issue"):
                gh.kapat(gun["issue"], f"Günün kuponları sonuçlandı. Karne: {kr['kupon']} kupon, {kr['tutan']} tuttu.")
    kaydet(veri)
    if biten:
        yaz(f"Mr. Likely: {biten} kupon sonuçlandı.")
    return biten


def eskileri_kapat(gh, simdi: datetime) -> None:
    """İki günden eski, cevapsız paketler kapatılır (karneye bir şey yazılmaz)."""
    veri = yukle()
    for gun in veri["gunler"][-6:]:
        if gun["durum"] == "bekliyor" and gun.get("issue") and \
                datetime.fromisoformat(gun["olusturma"]) + timedelta(hours=40) <= simdi:
            gun["durum"] = "pas"
            gh.kapat(gun["issue"], "Gün kapandı." if gun.get("oto") else "Cevap gelmedi; paket kapatıldı. Karneye bir şey yazılmadı.")
    kaydet(veri)



# ---------- 7. Otomatik mod: paylaşım (SOZLESME E1, E4, E6) ----------

def oto_paylas(ayar, x, simdi: datetime, yazici=None, kart=None, yaz=print) -> int:
    """Zamanı gelen otomatik kuponu Mr. Likely hesabında paylaşır (çalışma başına en fazla bir kupon).
    İlk maça oto_son_dk'dan az kaldıysa kupon paylaşılmaz ve kayıttan çıkar (karneye girmez)."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return 0
    veri = yukle()
    yazici = yazici or (lambda sablon, zorunlu: sablon)
    paylasilan = 0
    for gun in veri["gunler"][-2:]:
        for k in list(gun.get("secilen", [])):
            if not k.get("oto") or k.get("tweet_id") or k["durum"] != "bekliyor":
                continue
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"])
            if simdi >= ilk - timedelta(minutes=cfg.oto_son_dk):
                gun["secilen"].remove(k)
                gun.setdefault("kacan", []).append({"ad": k["ad"], "zaman": simdi.isoformat(timespec="seconds")})
                yaz(f"⚠️ Mr. Likely: {gun['tarih']} {k['ad']} zamanında paylaşılamadı; ilk maça az kaldığı için atlandı.")
                continue
            if simdi < datetime.fromisoformat(k["paylas"]) or paylasilan:
                continue
            sablon = kupon_metni(k, k["ayaklar"], gun["tarih"] + k["ad"], gorselli=bool(kart))
            if uzunluk(sablon) > LIMIT:
                # Çok uzun takım adları: maçlar görselde; metin kısa kalır (tutma ihtimali ve 18+ yine yazar).
                metin = (f"{_sec(ACILIS[min(len(k['ayaklar']), 4)], gun['tarih'] + k['ad'])}\n\nCombined {k['oran']:.2f}. "
                         f"I make it about {_pct(k['olasilik'])} to land. The legs are on the card.\n\n{ANSVAR}")
            else:  # sesli yazımda şablondaki maç adları ve oranlar korunmalı
                metin = yazici(sablon, [z for z in _zorunlu(k["ayaklar"]) + [f'{k["oran"]:.2f}'] if z in sablon])
            medya = [x.medya_yukle(kart(k, gun["tarih"]))] if kart else None
            k["tweet_id"] = x.gonder(metin, medya=medya)
            k["metin"], k["yayin"] = metin, simdi.isoformat(timespec="seconds")
            paylasilan += 1
            kaydet(veri)  # post atıldı: kayıt hemen yazılır (ikinci kez atılmasın)
            yaz(f"Mr. Likely: {k['ad']} paylaşıldı (tweet {k['tweet_id']}).")
    kaydet(veri)
    return paylasilan


def oto_sonuc_paylas(ayar, x, simdi: datetime, yaz=print) -> int:
    """Sonuçlanan, paylaşılmış kuponun sonuç postunu kupon postunun altına yanıt olarak atar (bir kez)."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return 0
    veri = yukle()
    adet = 0
    for gun in veri["gunler"][-6:]:
        for k in gun.get("secilen", []):
            if k.get("tweet_id") and k.get("sonuc_metni") and not k.get("sonuc_tweet_id"):
                k["sonuc_tweet_id"] = x.gonder(k["sonuc_metni"], yanit=k["tweet_id"])
                adet += 1
                kaydet(veri)
                yaz(f"Mr. Likely: {gun['tarih']} {k['ad']} sonucu paylaşıldı.")
    return adet


def oto_ders(ayar, x, simdi: datetime, yaz=print) -> bool:
    """Günün dersi (kupon stratejisi notu): günde bir kez, oto_ders_saati'nden sonra, kupon postlarından en az 60 dk uzakta."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return False
    veri = yukle()
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    gun = next((g for g in veri["gunler"][-2:] if g["tarih"] == yerel.date().isoformat()), None)
    if not gun or not gun.get("oto") or gun.get("ders_tweet_id") or yerel.hour < cfg.oto_ders_saati or yerel.hour >= 23:
        return False
    for k in gun.get("secilen", []):
        zaman = datetime.fromisoformat(k.get("yayin") or k.get("paylas") or gun["olusturma"])
        if k.get("oto") and abs((simdi - zaman).total_seconds()) < 3600 and k["durum"] == "bekliyor":
            return False
    gun["ders_tweet_id"] = x.gonder(gun["ders"])
    kaydet(veri)
    yaz("Mr. Likely: günün dersi paylaşıldı.")
    return True

