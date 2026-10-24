"""Mr. Likely: ikinci hesap (tahmin/kupon sayfası). İki mod (ayarlar.toml [likely] mod):

"otomatik": kuponu sabit kurallar seçer (otomatik_sec), bot Mr. Likely hesabında paylaşır: kupon postu (görselli),
maçlar bitince kupon postunu alıntılayan sonuç postu, günde en fazla 4 bilgi postu. Hesap X'te "Automated" etiketlidir. Sahibine bilgi
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
from .tweets import ANSVAR, LIMIT, KopyaPost, uzunluk

DOSYA = config.ROOT / "data" / "likely.json"
SES_REHBERI = config.ROOT / "marka" / "MR_LIKELY.md"
ETIKET = "mr-likely"
HARFLER = "ABCDEFGHIJ"
KUPON_ADI = {"gunun-kuponu": "Günün kuponu", "long-shot": "Long shot (yüksek oran)", "buyuk-maclar": "Büyük maçlar",
             **{f"gunun-kuponu-{n}": f"Günün kuponu {n}" for n in range(2, 6)}}
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
    oto_max_kupon: int = 5         # üç türden sonra kalan yer günün kuponu sınırlarıyla dolar (E6, 18 Ekim 2026)
    oto_tazele_saati: int = 11     # sabah eksik kalan kuponlar bu saatte (yerel) güncel oranlarla bir kez tamamlanır
    oto_max_ayak: int = 4
    oto_oran_min: float = 2.0      # kuponun toplam oranı bu aralıkta olur (sahibinin kararı, 6 Ekim 2026)
    oto_oran_max: float = 4.0
    oto_min_ayak: float = 0.65     # sağlam ayağın en düşük kazanma ihtimali
    oto_min_deger: float = -0.04   # ayağın oranı adil fiyatın en fazla bu kadar altında
    # Otomatik kupona hiç girmeyen pazarlar (E6). "Double chance 12" (ev ya da deplasman kazanır): gölge testte
    # 12'siz günün kuponu 8'de 6, 12'li 9'da 4 tuttu; sahibinin kararıyla çıkarıldı (14 Ekim 2026).
    oto_yasak_pazarlar: tuple = ("CS12",)
    # Ayak oranı yalnızca bu siteden (E6, sahibinin kararı 24 Ekim 2026): kombinenin toplam oranı tek sitede bulunur.
    # Boş: listedeki sitelerin en iyi fiyatı (eski davranış).
    oran_sitesi: str = "Bet365"
    # Keskin piyasaya göre bundan fazla "değer" gerçek dışıdır (hatalı/bayat fiyat): ayak kupona girmez (14 Ekim:
    # +%35 görünen 2.05, Bet365'te 1.50'ydi).
    oto_max_ayak_deger: float = 0.15
    oto_min_tutma: float = 0.30    # kuponun en düşük tutma ihtimali; altı paylaşılmaz
    oto_min_kupon_deger: float = -0.08  # kuponun toplam fiyatı adil fiyatın en fazla bu kadar altında
    oto_buyuk_tolerans: float = 0.03    # en olası kupona bu kadar yakın kuponlar içinde büyük maçı çok olan seçilir
    # İkinci kupon "long shot": daha yüksek oran, daha düşük tutma ihtimali (sahibinin kararı, 6 Ekim 2026)
    oto_uzun_oran_min: float = 3.0
    oto_uzun_oran_max: float = 4.0
    oto_uzun_min_tutma: float = 0.22
    oto_uzun_min_kupon_deger: float = -0.10
    oto_uzun_min_ayak_oran: float = 1.30  # long shot ayakları: oranı en az bu kadar (çok düşük oranlı maçla 3.00'a çıkılmaz)
    oto_once_dk: int = 180         # kupon ilk maçtan en erken bu kadar dakika önce paylaşılır
    oto_son_dk: int = 20           # ilk maça bundan az kaldıysa paylaşılmaz
    oto_ders_saati: int = 14       # (eski kayıtlar için) günün dersi bu saatten sonra
    oto_bilgi_sayisi: int = 4      # günde en fazla kaç bilgi postu (strateji notu, günün rakamları)
    oto_bilgi_aralik_dk: int = 40  # bilgi postu, başka bir posttan en az bu kadar dakika uzakta
    oto_haftalik_karne: bool = False  # Pazartesi 10:00 dersinin yerine haftalık karne postu (SOZLESME E1)
    # Sanal kasa grafiği (SOZLESME E8): açılınca önce bir kez duyuru, sonra her gün kuponlar sonuçlanınca grafik.
    oto_kasa: bool = False
    kasa_paleti: str = "fis"


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


# Havuzda ve otomatik kupon aramasında oran bantlarına ayrılan yer: (alt, üst, aday sayısı).
BANTLAR = ((1.19, 1.35, 20), (1.35, 9.99, 15))
ARAMA_BANTLARI = ((0.0, 1.19, 8), (1.19, 1.35, 12), (1.35, 9.99, 10))


def _oran_yontemi(ayar, cfg: LikelyAyar) -> str:
    return f"site:{cfg.oran_sitesi}" if cfg.oran_sitesi else ayar.oran_yontemi


def havuz(analizler: list[dict], oranlar: dict, ayar, cfg: LikelyAyar, simdi: datetime) -> list[dict]:
    """Günün maçlarından yüksek ihtimalli (ve değerli) adaylar; en yüksek ihtimal önce, numaralı (1..N).
    İhtimal: keskin piyasanın marjsız fiyatı. Oran: cfg.oran_sitesi'nin fiyatı (boşsa büyük sitelerin en iyisi)."""
    ayar2 = replace(ayar, guvenli_min_olasilik=cfg.min_olasilik, guvenli_min_deger=cfg.min_deger,
                    oran_min=cfg.oran_min, oran_max=cfg.oran_max, oran_yontemi=_oran_yontemi(ayar, cfg))
    en_erken = simdi + timedelta(minutes=cfg.min_dakika_once)
    hepsi = []
    for a in analizler:
        b = oranlar.get(a["fixture_id"])
        if not b or datetime.fromisoformat(a["baslama"]) < en_erken:
            continue
        ist = model.model_olasiliklari(*a["istatistik_gol"]) if a.get("istatistik_gol") else {}
        maclik = []
        for pazar, oran, bolag, bahisci_oranlari, p, deger, tur, kaynak in model._piyasa_adaylari(
                b, ayar2, a.get("lig_id") in ayar.ligler):
            etiket, _ = model.etiketler(pazar, a["ev"], a["dep"])
            ist_p = ist.get(pazar)
            maclik.append({
                "aday_id": f'{a["fixture_id"]}-{pazar}', "fixture_id": a["fixture_id"], "pazar": pazar, "tur": tur,
                "ev": a["ev"], "dep": a["dep"], "lig": a.get("lig", ""), "baslama": a["baslama"],
                "etiket": etiket, "oran": oran, "oran_kaynagi": bolag, "site_sayisi": len(bahisci_oranlari),
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
    # Oran bantlarına da yer ayrılır: yoğun günlerde en olası 80 aday hep 1.10–1.15 oluyor ve en fazla 4 ayakla
    # 2.00'a ulaşılamıyordu (9–10 Ekim 2026'da günün kuponu çıkmadı). Her bantta en olası adaylar.
    bantlar = []
    for alt, ust, adet in BANTLAR:
        bantlar += [c for c in guvenli if alt <= c["oran"] < ust and c not in buyuk][:adet]
    ayrilan = buyuk + bantlar
    kalan = [c for c in guvenli if c not in ayrilan]
    yer = max(cfg.havuz - len(ayrilan) - len(deger), 0)
    sonuc = sorted(ayrilan + kalan[:yer], key=lambda c: -c["olasilik"]) + deger
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
    """Otomatik modun kuponları (SOZLESME E6): kurallar sabit, sağlanmazsa o kupon o gün çıkmaz.
    Ayaklar: sağlam adaylar (ihtimal ≥ oto_min_ayak) ve artı değerli adaylar; hepsi istatistikle uyumlu, ihtimali keskin
    piyasadan (ortalamadan değil), oranı adil fiyatın en fazla oto_min_deger altında; kupon farklı maçlardan en fazla
    oto_max_ayak ayak.
    1) Günün kuponu: toplam oran oto_oran_min–oto_oran_max, tutma ≥ oto_min_tutma, fiyat ≥ oto_min_kupon_deger.
    2) Long shot (ilkiyle maç paylaşmaz): toplam oran oto_uzun_oran_min–oto_uzun_oran_max, tutma ≥ oto_uzun_min_tutma,
       fiyat ≥ oto_uzun_min_kupon_deger; ayak oranı ≥ oto_uzun_min_ayak_oran.
    3) Büyük maçlar (öncekilerle maç paylaşmaz): yalnızca büyük maçlardan, günün kuponuyla aynı sınırlarla.
    4) Ek kuponlar (gunun-kuponu-2, -3, ...): kalan yer, kalan maçlardan günün kuponuyla aynı sınırlarla dolar.
    Her birinde koşulu sağlayanlar içinde tutma ihtimali en yüksek olana oto_buyuk_tolerans kadar yakın kuponlardan
    BÜYÜK MAÇI EN ÇOK olan seçilir (eşitlikte tutma ihtimali, sonra fiyat, sonra kısa kupon)."""
    ayaklar = [a for a in adaylar if kupona_uygun(a, cfg)]
    ayaklar.sort(key=lambda a: -a["olasilik"])
    buyuk = {a["aday_id"]: bool(a.get("buyuk")) for a in ayaklar}
    # (ad, oran aralığı, en düşük tutma, en düşük fiyat, en düşük ayak oranı, yalnız büyük maç mı)
    tarifler = [("gunun-kuponu", cfg.oto_oran_min, cfg.oto_oran_max, cfg.oto_min_tutma, cfg.oto_min_kupon_deger, 0.0, False),
                ("long-shot", cfg.oto_uzun_oran_min, cfg.oto_uzun_oran_max, cfg.oto_uzun_min_tutma,
                 cfg.oto_uzun_min_kupon_deger, cfg.oto_uzun_min_ayak_oran, False),
                ("buyuk-maclar", cfg.oto_oran_min, cfg.oto_oran_max, cfg.oto_min_tutma, cfg.oto_min_kupon_deger, 0.0, True)]
    tarifler += [(f"gunun-kuponu-{n}",) + tarifler[0][1:] for n in range(2, cfg.oto_max_kupon + 1)]
    secilen: list[dict] = []
    dolu: set[int] = set()
    for ad, oran_min, oran_max, min_tutma, min_deger, min_ayak_oran, yalniz_buyuk in tarifler:
        if len(secilen) >= cfg.oto_max_kupon:
            break
        bos = [a for a in ayaklar if a["fixture_id"] not in dolu and a["oran"] >= min_ayak_oran
               and (buyuk[a["aday_id"]] or not yalniz_buyuk)]
        # Arama her oran bandından en olası adayları alır (yalnızca en olası 16 aday değil: onlar yoğun günlerde
        # hep ~1.10 olur ve 4 ayakla aralığa ulaşılamaz). Bantlar ayrık; sıralama ihtimale göre kalır.
        bos = sorted((a for alt, ust, adet in ARAMA_BANTLARI for a in [b for b in bos if alt <= b["oran"] < ust][:adet]),
                     key=lambda a: -a["olasilik"])
        uygun = [kupon_kur(list(k), ad) for n in range(1, cfg.oto_max_ayak + 1)
                 for k in itertools.combinations(bos, n) if _farkli_mac(k)]
        uygun = [k for k in uygun if oran_min <= k["oran"] <= oran_max and k["olasilik"] >= min_tutma and k["deger"] >= min_deger]
        if not uygun:
            continue
        esik = max(k["olasilik"] for k in uygun) - cfg.oto_buyuk_tolerans
        en_iyi = max((k for k in uygun if k["olasilik"] >= esik),
                     key=lambda k: (sum(buyuk[i] for i in k["ayaklar"]), k["olasilik"], k["deger"], -len(k["ayaklar"])))
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
UZUN_ACILIS = ["The long shot. Small stakes only.", "Today's long shot. It loses more often than it lands.",
               "Long shot of the day. Pocket money stuff.", "The ambitious one. Treat it like a lottery ticket with better manners.",
               "Long shot. I'd be surprised, pleasantly.", "Today's outsider. Stake accordingly."]
BUYUK_ACILIS = ["Big games only.", "The headline fixtures, one coupon.", "Just the big ones today.",
                "The games everyone's watching anyway.", "Tonight's main events."]
SORULAR = ["Which leg lets me down?", "Which one would you drop?", "Would you take it at this price?",
           "Which leg is the weak one?", "Anyone on the other side of one of these?", "What would you swap in?",
           "Which of these do you trust least?", "Too cautious or about right?"]
KAPANIS = ["Probably.", "No promises.", "We'll see.", "That's the maths, not a promise.", "Likely. Not certain.",
           "As ever: likely, not certain."]
TUTTU = ["That'll do.", "Landed. I'll try not to be smug about it.", "In. Nice when the maths behaves.",
         "Home. On to the next one.", "Done. Probably deserved it too.", "Lovely. Quietly lovely.",
         "No drama, which is exactly how I like them."]
YATTI = ["That's the part of the percentage nobody likes.", "Annoying. Still the right kind of coupon.",
         "It happens. More often than any of us would like.", "No excuses, it lost.",
         "Football did a football. Moving on.", "Not today. Kettle's on.", "Well, that didn't go to plan."]
SEKTI = ["One leg short. The classic.", "So close it hurts a bit.", "One out. Always one.",
         "Everything landed bar one. You know the feeling."]

# Ayağın kaderini belirleyen geç an (SOZLESME E2): yalnızca sonuç kaydındaki gerçek gollerden.
GEC_DAKIKA = 80   # kaderi belirleyen gol bu dakikadan sonraysa anlatılır
ONCEKI_DAKIKA = 70  # ondan önceki gol de bu dakikadan sonraysa hikâyeye girer ("88'de 2-0, 90+3'te 3-0")
YIKIM = [  # belirleyici golden hemen önce bir geç gol daha var
    "{M}. {odk}': {once}. Still fine. {dk}': {sonra}. Of course it was.",
    "{M}. {once} on {odk}' and I was fine with that. Then {dk}': {sonra}. {E} gone, coupon gone.",
    "{M} went {once} on {odk}'. Nervy, but fine. Then {sonra} on {dk}'. That's {E}, and that's the coupon.",
]
YIKIM_SON = [  # uzatma dakikalarında
    "{M}. {once} going into stoppage time. {dk}': {sonra}. That's the coupon.",
    "{M}. {once} with the board up. {dk}': {sonra}. Football, eh.",
    "Had {E} in {M} right up to {dk}'. Then {sonra}. I'm going for a walk.",
]
YIKIM_TEK = [
    "{M} sat at {once} until {dk}'. Then {sonra}. {E} gone, coupon with it.",
    "{M}. {dk}': {once} becomes {sonra}, and {E} goes with it. Football, eh.",
    "Had {E} in {M} right up to {dk}'. Then {sonra}. I'm going for a walk.",
]
KURTARIS = [
    "{M} left it late. {once} until {dk}', then {sonra}. {E} came good.",
    "{M}. {dk}': {sonra}. {E} in, just. Not great for the heart.",
    "{M} looked gone at {once}. Then {sonra} on {dk}'. I'll take it.",
]


def _dk(g: list) -> str:
    return f"{g[0]}+{g[1]}" if g[1] else str(g[0])


def an(a: dict) -> dict | None:
    """Ayağın kaderini belirleyen gerçek an: son gol ayağı kazanandan kaybedene (ya da tersine) çevirdiyse ve
    GEC_DAKIKA'dan sonra geldiyse. Gol listesi yoksa ya da skorla tutmuyorsa, pazar ilk yarı/korner gibi skordan
    çözülmüyorsa, ayak hiç el değiştirmediyse ya da an erken geldiyse None (uydurma an yok)."""
    goller = a.get("goller")
    if not goller or a.get("durum") not in ("kazandi", "kaybetti") or a["pazar"].startswith(("IY", "YY", "KOR")):
        return None
    ev = dep = 0
    durum, kritik, skorlar = model.kazandi_mi(a["pazar"], 0, 0), None, ["0-0"]
    for i, g in enumerate(goller):
        ev, dep = ev + (g[2] == "ev"), dep + (g[2] == "dep")
        yeni = model.kazandi_mi(a["pazar"], ev, dep)
        if yeni != durum:
            kritik = i
        durum = yeni
        skorlar.append(f"{ev}-{dep}")
    if kritik is None or durum != (a["durum"] == "kazandi") or a.get("skor") not in (None, skorlar[-1]):
        return None
    g = goller[kritik]
    if g[0] < GEC_DAKIKA:
        return None
    onceki = goller[kritik - 1] if kritik and goller[kritik - 1][0] >= ONCEKI_DAKIKA else None
    return {"tur": "kurtaris" if durum else "yikim", "dk": _dk(g), "once": skorlar[kritik], "sonra": skorlar[kritik + 1],
            "odk": _dk(onceki) if onceki else None, "uzatma": g[0] >= 90 and g[1] > 0,
            "M": f'{a["ev"]} v {a["dep"]}', "E": a["etiket"]}


def an_metni(x: dict, tohum: str) -> str:
    liste = (KURTARIS if x["tur"] == "kurtaris" else YIKIM if x["odk"] else YIKIM_SON if x["uzatma"] else YIKIM_TEK)
    return _sec(liste, tohum).format(**x)


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
    acilis = _sec({"long-shot": UZUN_ACILIS, "buyuk-maclar": BUYUK_ACILIS}.get(kupon.get("ad"), ACILIS[min(n, 4)]), tohum)
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
    if gorselli:
        # Görselli post (otomatik mod): oyunlar ve oranlar kartta. Metin taranabilir: emoji başlıklı satırlar, maç adları,
        # toplam oran ve tutma ihtimali, sonda yanıt çağıran tek bir soru (etkileşim tuzağı değil).
        liste = "\n".join(f'⚽ {a["ev"]} v {a["dep"]}' for a in ayaklar)
        sayi = (f"📊 Combined {kupon['oran']:.2f}. I make it about {_pct(p)} to land." if n > 1
                else f"📊 {ayaklar[0]['oran']:.2f}. I make it about {_pct(p)} to land.")
        soru = f"💬 {_sec(SORULAR, tohum + 's')}"
        return _kisalt(f"🎩 {acilis}\n\n{liste}\n\n{sayi}\n\n{soru}{son}", f"🎩 {acilis}\n\n{liste}\n\n{sayi}{son}",
                       f"🎩 {acilis}\n\n{maclar}\n\n{sayi}{son}", f"🎩 {acilis}\n\n{sayi} The legs are on the card.{son}")
    return _kisalt(
        f"{acilis}\n\n" + "\n".join(uzun) + f"\n\n{ozet}{son}",
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
    """Sonuç postunun şablonu: tutan da yatan da aynı açıklıkla, güncel karneyle. Kuponun kaderi geç bir golle
    belirlendiyse o an (dakika, skor; yalnızca sonuç kaydındaki gollerden) insan diliyle anlatılır."""
    ayaklar = kupon["ayaklar"]
    skorlar = [f'{"✅" if a["durum"] == "kazandi" else "↩️" if a["durum"] == "iade" else "❌"} '
               f'{a["ev"]} {a["skor"] or "void"} {a["dep"]}: {a["etiket"]}' for a in ayaklar]
    yatan = sum(a["durum"] == "kaybetti" for a in ayaklar)
    anlar = [x for x in (an(a) for a in ayaklar) if x]
    hikaye = next((x for x in anlar if x["tur"] == ("kurtaris" if kupon["durum"] == "tuttu" else "yikim")), None)
    if kupon["durum"] == "tuttu":
        bas = f'{"Both legs in" if len(ayaklar) == 2 else "All in" if len(ayaklar) > 2 else "In"} at {kupon["son_oran"]:.2f}. {_sec(TUTTU, tohum)}'
    elif kupon["durum"] == "iade":
        bas = "Void. Game off, coupon off, nothing won and nothing lost."
    elif len(ayaklar) > 1 and yatan == 1:
        bas = f"{_sec(SEKTI, tohum)} Coupon down."
    else:
        bas = f"Coupon down. {_sec(YATTI, tohum)}"
    kisa_bas = bas.split(". ")[0] + "."
    if kupon["durum"] == "yatti":
        bas += f" I had it at {_pct(kupon['olasilik'])}, which was never 100."
    isaret = {"tuttu": "✅ ", "iade": "↩️ "}.get(kupon["durum"], "❌ ")  # akışta ilk bakışta sonuç
    son = f"\n\n{karne_satiri(k)}\n{ANSVAR}"
    satirlar = "\n".join(skorlar)
    secenekler = []
    if hikaye:
        anlati = an_metni(hikaye, tohum)
        ek = (f" In at {kupon['son_oran']:.2f}." if kupon["durum"] == "tuttu"
              else " Not the only leg to go, mind." if yatan > 1 else "")
        secenekler += [f"{isaret}{anlati}{ek}\n\n{satirlar}{son}", f"{isaret}{anlati}{ek}{son}", f"{isaret}{anlati}{son}"]
    secenekler += [f"{isaret}{bas}\n\n{satirlar}{son}", f"{isaret}{kisa_bas}\n\n{satirlar}{son}", f"{isaret}{kisa_bas}{son}"]
    return _kisalt(*secenekler)


# Günün dersi: kupon stratejisi üzerine kısa, dürüst notlar (ayrı post). Her biri 280 sınırında ve 18+ ile biter.
DERSLER = [
    "Three legs at 80% each is a 51% coupon. Four is 41%. The legs don't know about each other, they just multiply.\n\nIt's why mine stop at four, and why every leg is the dull sort.",
    "The 90th-minute equaliser isn't aimed at you personally. Late goals happen every weekend. Your coupon just happened to be watching.",
    "A pick that wins 80% of the time still loses one week in five. If one loss wrecks your month, the stake was the problem, not the pick.",
    "Three legs in, one to go, and the last one lets you down. Feels personal. It isn't. The last leg loses as often as the first, you just notice it more.",
    "Same stake every coupon. Not double after a loss, not triple when you \"feel it\". Feelings are not a staking plan.",
    "Nobody posts the six-leg coupon that died in the 12th minute. That's why it looks like everyone else is winning.",
    "Chasing losses is just paying twice for the same bad evening. Close the app. The fixtures will still be there tomorrow.",
    "Your mate who \"always wins\" has a very selective memory. Ask for the full list, losers included. Mine's all on this page.",
    "Favourites lose. A team at 75% to win fails one time in four, and nobody posts those screenshots.",
    "A winning week proves almost nothing. A losing week proves almost nothing. Ask me again after 200 coupons.",
    "Only stake money you'd be fine never seeing again. If that sentence stings, the stake is too big.",
    "The worst coupon of the weekend is usually the one placed at 11pm to win back the afternoon.",
    "The big 10-leg winners you see online are survivors. For every one of those there's a drawer full of losers nobody shows you.",
    "Keeping a record is boring and it's the only way to know if you're any good. Every coupon, wins and losses. Mine's all here.",
    "\"It was so close\" pays the same as \"it was miles off\". Don't raise stakes because a coupon nearly landed.",
    "No good pick today is a perfectly fine day. Passing is a decision, and some days it's the smartest one on the board.",
    "Friday-night confidence and Sunday-morning regret are the same person, two days apart. Set the amount on Thursday.",
    "My coupons sit around 2.00 and lose about half the time. That's the deal at that price. Anyone promising you a 2.00 that lands eight times in ten is selling something.",
    "Don't back your own club. You already think they'll win every week, and the odds don't care about your scarf.",
    "Set the amount before the weekend starts and stop when it's gone. Deciding in the 80th minute never ends well.",
    "A red card in the 5th minute isn't the referee hating you. Football is random enough that a sensible coupon still loses. Often.",
    "Why odds between 2 and 4? Below that there's little to talk about, above it you're buying a lottery ticket. In between you still lose about as often as you win, so the stake stays small.",
    "Four boring legs beat two exciting ones. I'd rather build a 2.00 out of things that usually happen than out of one thing that rarely does.",
    "\"They're due a win\" isn't a thing. The team doesn't know it's due. Neither does the coupon.",
    "Odds are just chances wearing a costume. 2.00 says about 50%, 1.50 about 67%, 4.00 about 25%. Divide 1 by the odds and you can see what you're actually being offered.",
    "Bored on a Tuesday is not a reason. If the only reason for a coupon is that there's a match on, there's always a match on.",
    "Double chance looks cowardly and wins a lot. You're buying two of the three results. The odds are small because the risk is small, not because it's a bad pick.",
    "Derbies, cup ties, last day of the season. The games you care most about are the ones you think least clearly about. Enjoy those without a coupon.",
    "Form over five games is mostly noise. Five games is a mood, not a trend.",
    "A big win early on is the most dangerous thing that can happen to a beginner. It teaches exactly the wrong lesson.",
    "The draw is the result nobody fancies, and it keeps turning up anyway. If your coupons keep dying 1-1, that's not a curse, it's football.",
    "One leg at a time: would you back each one on its own? If not, why is it holding up the other three?",
    "Cup games and dead rubbers are where rotation lives. Check who's actually starting before trusting a favourite in a match that doesn't matter to them.",
    "You'll remember the coupon that nearly landed for weeks and forget the ten that missed by miles. That's memory, not form.",
    "Refreshing the live score every two minutes doesn't help the striker. Put the phone down. Full-time comes either way.",
    "Cashing out early feels clever and usually costs you. Decide your coupon before kick-off, not during.",
    "Watching a game with money on it and watching it for fun are different hobbies. Pick the one you actually enjoy.",
    "If you'd be embarrassed to explain a pick to someone sober, don't make it. \"I had a feeling\" is not a reason, it's a confession.",
]


def ders_metni(tarih: str, atla: int = 0) -> str:
    gun = datetime.fromisoformat(tarih).timetuple().tm_yday
    return f"💡 {DERSLER[(gun + atla) % len(DERSLER)]}\n\n{ANSVAR}"


def _kac_kezde_bir(p: float) -> int:
    return max(2, round(1 / max(1 - p, 0.01)))


def haftalik_karne(veri: dict, tarih: str, cfg: LikelyAyar) -> dict | None:
    """Pazartesi: geçen 7 günün paylaşılmış ve sonuçlanmış kuponları (karnenin kendisi, kaybedenler dahil). Beklenen:
    kuponların tutma ihtimallerinin toplamı. 3 kupondan azsa, Pazartesi değilse ya da ayar kapalıysa None."""
    gun = datetime.fromisoformat(tarih)
    if not cfg.oto_haftalik_karne or gun.weekday() != 0:
        return None
    bas = (gun - timedelta(days=7)).date().isoformat()
    kuponlar = [k for g in veri["gunler"] if bas <= g["tarih"] < tarih for k in g.get("secilen", [])
                if k["durum"] in ("tuttu", "yatti") and (not k.get("oto") or k.get("tweet_id"))]
    if len(kuponlar) < 3:
        return None
    return {"kupon": len(kuponlar), "tutan": sum(k["durum"] == "tuttu" for k in kuponlar),
            "beklenen": sum(k["olasilik"] for k in kuponlar)}


def hafta_metni(h: dict) -> str:
    """Haftalık karne postu: kaç kupon, kaç tuttu, ihtimallere göre kaç tutmalıydı. Sayıların hepsi karneden."""
    n, m, e = h["kupon"], h["tutan"], round(h["beklenen"])
    yorum = ("A bit ahead of the maths. That evens out too." if m - h["beklenen"] >= 1 else
             "Behind the maths. A week is a tiny sample, so nothing changes over it." if h["beklenen"] - m >= 1 else
             "Right about where the maths said.")
    soru = "Which one hurt most?" if m < n else "Enjoy it while it lasts?"
    return (f"📒 Last week: {n} coupons, {m} landed.\n\nGoing by the chances I gave them, about {e} should have. {yorum}\n\n"
            f"Every coupon counts here, the losers too.\n\n💬 {soru}\n\n{ANSVAR}")


ANKET_SECENEK = 25  # X: anket seçeneği en fazla 25 karakter


def _anket(secenekler: list[str], baslama: str) -> dict | None:
    """Bilgi postuna anket: maç başlayınca kapanır (paylaşımda süre hesaplanır). Seçenek sığmazsa anket yok."""
    if any(len(s) > ANKET_SECENEK for s in secenekler):
        return None
    return {"options": secenekler, "bitis": baslama}


def bilgi_hazirla(analizler: list[dict], tarih: str, simdi: datetime, cfg: LikelyAyar,
                  hafta: dict | None = None) -> list[dict]:
    """Günün bilgi postları (kupon dışı): kupon stratejisi notları, günün büyük maçlarından rakamlar (anketli) ve
    Pazartesi haftalık karne. Rakamlar analiz kaydından ve karneden; bahis tavsiyesi ya da kesinlik dili yok.
    Her biri {"tur", "metin", "saat"} (+ "anket"). Sayı sabit: ek post, ek maliyet yok."""
    buyuk = [a for a in analizler if analiz.onemli(a) and a.get("kaynak") == "piyasa" and a.get("guven") == "yuksek"
             and datetime.fromisoformat(a["baslama"]) >= simdi + timedelta(hours=2)]
    son = f"\n\n{ANSVAR}"
    postlar = [{"tur": "hafta", "metin": hafta_metni(hafta), "saat": 10.0} if hafta
               else {"tur": "ders", "metin": ders_metni(tarih), "saat": 10.0}]
    if buyuk:
        f = max(buyuk, key=lambda a: max(a["p"]["MS1"], a["p"]["MS2"]))
        ev_favori = f["p"]["MS1"] >= f["p"]["MS2"]
        p = max(f["p"]["MS1"], f["p"]["MS2"])
        takim, rakip = (f["ev"], f["dep"]) if ev_favori else (f["dep"], f["ev"])
        if p >= 0.60:
            postlar.append({"tur": "favori", "saat": 13.0, "baslama": f["baslama"], "metin":
                            f"📈 Biggest favourite on today's card: {takim}, about {_pct(p)} to beat {rakip}.\n\n"
                            f"Sounds safe. It still fails roughly one time in {_kac_kezde_bir(p)}.\n\n"
                            f"💬 Does it hold today? Vote below.{son}",
                            "anket": _anket(["It holds", "Upset incoming"], f["baslama"])})
        kalan = [a for a in buyuk if a is not f] or buyuk
        g = max(kalan, key=lambda a: a["p"]["UST25"])
        d = min(kalan, key=lambda a: max(a["p"]["MS1"], a["p"]["MS2"]) - min(a["p"]["MS1"], a["p"]["MS2"]))
        if g["p"]["UST25"] >= 0.58:
            pg = g["p"]["UST25"]
            postlar.append({"tur": "gol", "saat": 16.0, "baslama": g["baslama"], "metin":
                            f"⚽ Likeliest goals game today: {g['ev']} v {g['dep']}, about {_pct(pg)} for over 2.5 goals.\n\n"
                            f"Which also means roughly {10 - round(10 * pg)} times in 10 it stays under.\n\n"
                            f"💬 Over or under? Vote below.{son}",
                            "anket": _anket(["Over 2.5 goals", "Under 2.5 goals"], g["baslama"])})
        else:
            postlar.append({"tur": "denk", "saat": 16.0, "baslama": d["baslama"], "metin":
                            f"⚖️ Closest call today: {d['ev']} v {d['dep']}.\n\n"
                            f"{d['ev']} {_pct(d['p']['MS1'])} · Draw {_pct(d['p']['MSX'])} · {d['dep']} {_pct(d['p']['MS2'])}\n\n"
                            f"Nobody knows, and the prices admit it.\n\n💬 Who edges it? Vote below.{son}",
                            "anket": _anket([d["ev"], "Draw", d["dep"]], d["baslama"])})
    postlar.append({"tur": "ders", "metin": ders_metni(tarih, atla=len(DERSLER) // 2), "saat": 21.0})
    postlar = [{k: v for k, v in b.items() if v is not None} for b in postlar if uzunluk(b["metin"]) <= LIMIT]
    return sorted(postlar[:cfg.oto_bilgi_sayisi], key=lambda b: b["saat"])


SES_SISTEM = """You write posts for "Mr. Likely", a football coupon account on X. The coupons are picked by a numbers
model with fixed rules; Mr. Likely is the voice that presents them. You get a draft with the exact facts; rewrite it
in his voice. Never claim a human hand-picked a coupon or watched a match.

Voice: a dry, good-humoured bloke who likes numbers and never promises anything. Short sentences, everyday words,
contractions, a little self-mockery. He says "probably", "likely", "I make it about 61%". He owns his losses in plain
words and never sulks or blames referees. He is not a salesman and not a guru.

Sound like a real fan typing on his phone at full-time, not like a brand or an assistant:
- Fragments are fine. "Of course." "Lovely." "Gutted, briefly." Vary sentence length; one-word lines are allowed.
- If the draft tells the moment that decided it (a minute and a score), that moment is the post. Tell it the way a mate
  would in the pub, in time order, with the minute and score exactly as given. Never add a moment, a scorer, a VAR
  call or anything else that is not in the draft.
- Understatement over drama. Gallows humour over complaint. No exclamation marks, no "absolutely", no "unreal".
- Don't explain the joke and don't moralise. One feeling per post.
- Never sound like a template: don't reuse the draft's opening words if you can say it better in your own.

Hard rules:
- Max 280 characters (emojis count double). Keep the last line exactly "18+ | Play responsibly".
- Keep every match, every pick and every number from the draft exactly as written. Add no new numbers, stats, news,
  injuries, quotes or backstory. Never invent a past win or a track record.
- Never say or imply a pick is certain: no "lock", "banker", "sure", "guaranteed", "can't lose", "free money", "easy".
- No links, no @ mentions, no hashtags, no bookmaker or site names, no "DM me", no "join", no selling.
- Never tell people to bet more, chase losses or borrow. Never claim betting is a way to make a living.
- Sound like a person: no "Here's the thing", "The result?", "It's not X, it's Y", no hype words, at most one dash.
  Vary the opening; don't start two posts the same way.
- Layout: keep the draft's layout and emojis exactly as markers, one at the start of a line (🎩 opener, ⚽ each match,
  📊 the numbers, 💬 the question, ✅/❌ results). No other emojis, never two in a row.
- If the draft ends with a 💬 question, keep one short, specific question there that invites a reply. You may reword
  it. No engagement bait: never ask for likes, reposts or follows."""
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
    if re.search(r"\b(RT|retweet|repost|like if|follow (me|us|for))\b", metin, re.IGNORECASE):
        sorun.append("etkileşim tuzağı")
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
    s += ["", f"## Adaylar ({len(adaylar)})", *(["<details><summary>Listeyi aç</summary>"] if gun.get("oto") else []), "",
          "| # | Maç | Saat | Oyun | Oran | İhtimal | Değer | Not |", "|---|---|---|---|---|---|---|---|"]
    s += [f'| {a["no"]} | {a["ev"]} v {a["dep"]} | {_saat(a["baslama"], ayar)} | {a["etiket"]} | {a["oran"]:.2f} | '
          f'%{round(100 * a["olasilik"])} | {round(100 * a["deger"]):+d}% | {_not(a, cfg)} |' for a in adaylar]
    s += [*(["", "</details>"] if gun.get("oto") else [])]
    if gun.get("oto") and gun.get("bilgi"):
        s += ["", f"## Bilgi postları ({len(gun['bilgi'])})"]
        for b in gun["bilgi"]:
            s += [f"**{int(b['saat']):02d}:{round(60 * (b['saat'] % 1)):02d}'den sonra** ({b['tur']}"
                  + (f", anket: {' / '.join(b['anket']['options'])}" if b.get("anket") else "") + ")", "```", b["metin"], "```"]
    else:
        s += ["", "## Günün dersi", "```", gun["ders"], "```"]
    if gun.get("oto"):
        s += ["", "<details><summary>Ölçüm (gölge test, paylaşılmaz)</summary>", "", olcum_raporu(cfg), "", "</details>"]
    return "\n".join(s)


def _buyuk_tani(a: dict, b: dict, ayar, cfg: LikelyAyar) -> dict:
    """Büyük maçın adayı neden çıktı/çıkmadı: kaç bahisçi var, keskin ve zorunlu bahisçi var mı, en yüksek ihtimalli
    oyunun fiyatı nasıl. Günlük bildirimde görünür (büyük maç kaçıyorsa nedeni belli olsun)."""
    adil, _ = model.adil_olasiliklar(b, ayar.keskin_bahisci) if b else ({}, {})
    fiyat = model.piyasa_oranlari(b, ayar.oran_bahiscileri, _oran_yontemi(ayar, cfg)) if b else {}
    en_iyi = max(((p, pz) for pz, p in adil.items() if pz in fiyat and cfg.oran_min <= fiyat[pz][0] <= cfg.oran_max),
                 default=None)
    kayit = {"mac": f'{a["ev"]} v {a["dep"]}', "bahisci": len(b), "bahisciler": sorted(b),
             "keskin": any(ad.lower() == ayar.keskin_bahisci.lower() for ad in b),
             "zorunlu": all(any(ad.lower() == z.lower() for ad in b) for z in ayar.zorunlu_bahisciler)}
    if en_iyi:
        p_, pz = en_iyi
        oran, _, siteler = fiyat[pz]
        kayit.update(oyun=model.etiketler(pz, a["ev"], a["dep"])[0], olasilik=round(p_, 3), oran=oran,
                     deger=round(p_ * oran - 1, 3), site=len(siteler),
                     zorunlu_oyunda=all(any(ad.lower() == z.lower() for ad in siteler) for z in ayar.zorunlu_bahisciler))
    return kayit


def paylasim_zamanlari(kuponlar: list[dict], simdi: datetime, cfg, onceki: list[datetime] = ()) -> list[datetime]:
    """Her kuponun paylaşım anı: ilk maçından oto_once_dk önce, en geç 45 dk önce; kuponlar arasında en az 40 dk.
    Aralık, son saati (ilk maçı) en yakın kupondan başlayarak verilir ve hiçbir kuponu kendi son saatinin ötesine
    itemez (14 Ekim: aralık seçim sırasıyla verilince akşam kuponu önce geldi, öğle maçlı long-shot ve büyük maçlar
    kuponu kendi maçlarının sonrasına itildi; biri kaçtı). Aralık ancak son saat izin verirse uygulanır."""
    def son(d):
        return min(datetime.fromisoformat(a["baslama"]) for a in d["ayaklar"]) - timedelta(minutes=45)
    zamanlar: dict[int, datetime] = {}
    dolu = sorted(onceki)
    for i in sorted(range(len(kuponlar)), key=lambda i: son(kuponlar[i])):
        ilk = son(kuponlar[i]) + timedelta(minutes=45)
        t = min(max(simdi + timedelta(minutes=5), ilk - timedelta(minutes=cfg.oto_once_dk)), son(kuponlar[i]))
        while any(abs((t - z).total_seconds()) < 40 * 60 for z in dolu) and t + timedelta(minutes=5) <= son(kuponlar[i]):
            t += timedelta(minutes=5)  # bir öncekiyle çakışıyorsa son saati aşmadan biraz ileri
        zamanlar[i] = t
        dolu.append(t)
    return [zamanlar[i] for i in range(len(kuponlar))]


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
    gun["bilgi"] = bilgi_hazirla(analizler, tarih, simdi, cfg, hafta=haftalik_karne(veri, tarih, cfg))
    gun["tani"]["buyukler"] = [_buyuk_tani(a, oranlar.get(a["fixture_id"]) or {}, ayar, cfg) for a in buyukler][:15]
    oto = cfg.mod == "otomatik"
    if oto:
        harita = {a["aday_id"]: a for a in adaylar}
        secilen = [_dondur([harita[i] for i in k["ayaklar"]], k["ad"], simdi) for k in otomatik_sec(adaylar, cfg)]
        for d, zaman in zip(secilen, paylasim_zamanlari(secilen, simdi, cfg)):
            d.update(oto=True, paylas=zaman.isoformat(timespec="seconds"))
            gun["secilen"].append(d)
        gun["durum"] = "secildi" if gun["secilen"] else "bekliyor"
        gun["oto"] = True
    govde = (f"@{ayar.alarm_kime} " if ayar.alarm_kime else "") + paket_metni(gun, veri, ayar, cfg)
    baslik = ((f"🎩 Mr. Likely {tarih}: otomatik, {len(gun['secilen'])} kupon paylaşılacak" if gun["secilen"]
               else f"⚠️ Mr. Likely {tarih}: otomatik, BUGÜN KUPON ÇIKMADI (kural sağlanmadı)") if oto
              else f"🎩 Mr. Likely {tarih}: {len(adaylar)} aday, {len(gun['kuponlar'])} kupon")
    gun["issue"] = gh.issue_ac(baslik, govde, ETIKET)
    veri["gunler"].append(gun)
    for eski in veri["gunler"][:-14]:  # eski günlerde yalnızca seçilen kuponlar (karne) kalır; dosya büyümesin
        eski.pop("havuz", None)
        eski.pop("kuponlar", None)
    kaydet(veri)
    yaz(f"Mr. Likely paketi gönderildi (issue #{gun['issue']}): {len(adaylar)} aday, {len(gun['kuponlar'])} kupon.")
    return gun


def tazeleme_zamani(ayar, simdi: datetime) -> bool:
    """Öğlen tazeleme (E6): otomatik modda bugünün kayıtlı günü varsa, kupon sayısı sınırın altındaysa, yerel saat
    oto_tazele_saati'ni geçtiyse ve bugün henüz tazelenmediyse True döner ve günü işaretler (hata olsa da bir kez)."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return False
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    veri = yukle()
    gun = next((g for g in veri["gunler"] if g["tarih"] == yerel.date().isoformat() and g.get("oto")), None)
    if gun is None or gun.get("tazeleme") or yerel.hour < cfg.oto_tazele_saati or len(gun["secilen"]) >= cfg.oto_max_kupon:
        return False
    gun["tazeleme"] = simdi.isoformat(timespec="seconds")
    kaydet(veri)
    return True


def ek_kupon(ayar, analizler: list[dict], oranlar: dict, simdi: datetime, gh=None, yaz=print) -> int:
    """Otomatik modda gün içinde eksik kalan kupon türünü (ör. sabah long shot çıkmadıysa) güncel oranlarla tamamlar.
    Mevcut kuponlara dokunmaz; yeni kupon onlarla maç paylaşmaz. Eklenen kupon sayısını döndürür."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return 0
    veri = yukle()
    tarih = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    gun = next((g for g in veri["gunler"] if g["tarih"] == tarih and g.get("oto")), None)
    if gun is None:
        return 0
    if "bilgi" not in gun:  # eski kayıt: günün bilgi postları da hazırlanır
        gun["bilgi"] = bilgi_hazirla(analizler, tarih, simdi, cfg, hafta=haftalik_karne(veri, tarih, cfg))
    var = {k["ad"] for k in gun["secilen"]}
    dolu = {a["fixture_id"] for k in gun["secilen"] for a in k["ayaklar"]}
    adaylar = [a for a in havuz(analizler, oranlar, ayar, cfg, simdi) if a["fixture_id"] not in dolu]
    harita = {a["aday_id"]: a for a in adaylar}
    eklenen = 0
    for k in otomatik_sec(adaylar, cfg):
        if len(gun["secilen"]) >= cfg.oto_max_kupon:
            break
        if k["ad"] in var:
            if not k["ad"].startswith("gunun-kuponu"):
                continue  # long shot ve büyük maçlar günde bir kez
            # günün kuponu sınırlarındaki kupon: sıradaki boş ek kupon adıyla girer
            k["ad"] = next((a for a in [f"gunun-kuponu-{n}" for n in range(2, cfg.oto_max_kupon + 1)] if a not in var), None)
            if k["ad"] is None:
                continue
        var.add(k["ad"])
        d = _dondur([harita[i] for i in k["ayaklar"]], k["ad"], simdi)
        mevcut = [datetime.fromisoformat(m.get("yayin") or m["paylas"]) for m in gun["secilen"] if m.get("yayin") or m.get("paylas")]
        zaman = paylasim_zamanlari([d], simdi, cfg, mevcut)[0]
        d.update(oto=True, paylas=zaman.isoformat(timespec="seconds"))
        gun["secilen"].append(d)
        gun["durum"] = "secildi"
        eklenen += 1
        if gh and gun.get("issue"):
            gh.yorum(gun["issue"], f'Ek kupon: **{KUPON_ADI.get(d["ad"], d["ad"])}** · oran {d["oran"]:.2f} · tutma %{round(100 * d["olasilik"])} · '
                                   f'paylaşım **{_saat(d["paylas"], ayar)}**\n' + "\n".join(f"- {_ayak_satiri(a, ayar)}" for a in d["ayaklar"]))
    kaydet(veri)
    yaz(f"Mr. Likely: {eklenen} ek kupon eklendi.")
    return eklenen


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
                                             "oran", "oran_kaynagi", "olasilik", "deger") if x in a},
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
                    if r.get("goller") is not None:  # gerçek gol dakikaları: sonuç postunda anlatılabilir (E2)
                        a["goller"] = r["goller"]
                elif r["durum"] == "iptal" or gec:
                    a["durum"] = "iade"
            _kupon_sonucu(k)
            # Yatan kupon da bütün maçları bitince duyurulur (sonuç postunda hepsinin skoru olsun).
            if k["durum"] != "bekliyor" and all(a["durum"] != "bekliyor" for a in k["ayaklar"]) and not k.get("sonuc_metni"):
                biten += 1
                sablon = sonuc_metni(k, karne(veri), gun["tarih"] + k["ad"])
                # Sesli yazımda maç adları ve (anlatı varsa) belirleyici dakika korunur
                k["sonuc_metni"] = yazici(sablon, [x for a in k["ayaklar"] for x in (a["ev"], a["dep"])]
                                          + [x["dk"] for x in filter(None, map(an, k["ayaklar"])) if x["dk"] in sablon])
                if gun.get("issue"):
                    gh.yorum(gun["issue"], f"### Sonuç: kupon `{k['ad']}` "
                                           f"{'✅ tuttu' if k['durum'] == 'tuttu' else '↩️ iade' if k['durum'] == 'iade' else '❌ yattı'}\n"
                                           "Sonuç postu (kupon postunu alıntılayarak):\n```\n" + k["sonuc_metni"] + "\n```")
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
            if uzunluk(sablon) > LIMIT:  # olağan dışı uzun adlar: en kısa güvenli metin
                metin = f"🎩 Combined {k['oran']:.2f}. I make it about {_pct(k['olasilik'])} to land. The legs are on the card.\n\n{ANSVAR}"
            else:  # sesli yazımda şablondaki maç adları ve toplam oran korunmalı
                metin = yazici(sablon, [z for z in _zorunlu(k["ayaklar"]) + [f'{k["oran"]:.2f}'] if z in sablon])
            medya = [x.medya_yukle(kart(k, gun["tarih"]))] if kart else None
            k["tweet_id"] = x.gonder(metin, medya=medya)
            k["metin"], k["yayin"] = metin, simdi.isoformat(timespec="seconds")
            paylasilan += 1
            kaydet(veri)  # post atıldı: kayıt hemen yazılır (ikinci kez atılmasın)
            yaz(f"Mr. Likely: {k['ad']} paylaşıldı (tweet {k['tweet_id']}).")
    kaydet(veri)
    return paylasilan


def oto_sonuc_paylas(ayar, x, simdi: datetime, kart=None, yaz=print) -> int:
    """Sonuçlanan, paylaşılmış kuponun sonuç postunu atar (bir kez): kupon postunu ALINTILAR, sonuç kartı eklenir.
    Yanıt olarak değil: yanıtlar takipçilerin akışında görünmez, alıntı ayrı bir post olarak görünür (SOZLESME E1)."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return 0
    veri = yukle()
    adet = 0
    for gun in veri["gunler"][-6:]:
        for k in gun.get("secilen", []):
            if k.get("tweet_id") and k.get("sonuc_metni") and not k.get("sonuc_tweet_id"):
                medya = None
                if kart:
                    try:
                        medya = [x.medya_yukle(kart(k, gun["tarih"]))]
                    except Exception as e:  # görsel yüklenemezse sonuç yine de gider (kaybeden de yazılır, E5)
                        yaz(f"⚠️ Mr. Likely: sonuç kartı eklenemedi ({e}); post görselsiz atılıyor.")
                k["sonuc_tweet_id"] = x.gonder(k["sonuc_metni"], alinti=k["tweet_id"], medya=medya)
                k["sonuc_zamani"] = simdi.isoformat(timespec="seconds")  # sanal kasanın sırası (E8)
                adet += 1
                kaydet(veri)
                yaz(f"Mr. Likely: {gun['tarih']} {k['ad']} sonucu paylaşıldı.")
    return adet


def _post_zamanlari(gun: dict) -> list[datetime]:
    """Günün atılmış ve planlı post zamanları (kupon postları ve bilgi postları)."""
    z = [datetime.fromisoformat(k.get("yayin") or k["paylas"]) for k in gun.get("secilen", []) if k.get("oto") and (k.get("yayin") or k.get("paylas"))]
    return z + [datetime.fromisoformat(b["zaman"]) for b in gun.get("bilgi", []) if b.get("zaman")]


def oto_bilgi(ayar, x, simdi: datetime, yaz=print) -> bool:
    """Sırası gelen bilgi postunu atar: saati geldiyse ve başka bir posttan (atılmış ya da yakında atılacak kupon,
    önceki bilgi postu) en az oto_bilgi_aralik_dk uzaktaysa. Çalışma başına en fazla bir post; 23:00'ten sonra atılmaz."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return False
    veri = yukle()
    yerel = simdi.astimezone(ZoneInfo(ayar.saat_dilimi))
    gun = next((g for g in veri["gunler"][-2:] if g["tarih"] == yerel.date().isoformat()), None)
    if not gun or not gun.get("oto") or yerel.hour >= 23:
        return False
    if "bilgi" not in gun:  # eski kayıt: bilgi postları henüz hazırlanmamış (likely_ek hazırlar)
        return False
    siradaki = next((b for b in gun["bilgi"] if not b.get("tweet_id") and yerel.hour + yerel.minute / 60 >= b["saat"]), None)
    if not siradaki:
        return False
    if siradaki.get("baslama") and simdi >= datetime.fromisoformat(siradaki["baslama"]) - timedelta(minutes=10):
        siradaki["tweet_id"] = "gecti"  # maç başladı (ya da başlamak üzere): maç öncesi rakam artık paylaşılmaz
        kaydet(veri)
        return False
    if any(abs((simdi - z).total_seconds()) < 60 * cfg.oto_bilgi_aralik_dk for z in _post_zamanlari(gun)):
        return False
    if any(b.get("zaman") and b["metin"] == siradaki["metin"] for b in gun["bilgi"]):  # aynı metin aynı gün iki kez gitmez
        siradaki["tweet_id"] = "tekrar"
        kaydet(veri)
        return False
    anket = None
    if siradaki.get("anket"):  # anket maç başlayınca kapanır (X: en az 5 dakika)
        kalan = (datetime.fromisoformat(siradaki["anket"]["bitis"]) - simdi).total_seconds() // 60
        anket = {"options": siradaki["anket"]["options"], "duration_minutes": int(max(5, min(kalan, 24 * 60)))}
    try:
        siradaki["tweet_id"] = x.gonder(siradaki["metin"], anket=anket) if anket else x.gonder(siradaki["metin"])
    except KopyaPost:  # X bu metni eski bir posttan tanıyor: yeniden denenmez, alarm da açılmaz
        siradaki["tweet_id"] = "tekrar"
        kaydet(veri)
        yaz(f"Mr. Likely: bilgi postu ({siradaki['tur']}) atlandı; X aynı metni daha önce görmüş.")
        return False
    siradaki["zaman"] = simdi.isoformat(timespec="seconds")
    kaydet(veri)
    yaz(f"Mr. Likely: bilgi postu paylaşıldı ({siradaki['tur']}).")
    return True


def veri_hatasi_iptal(ayar, x, simdi: datetime, ad: str, neden: str, yaz=print) -> bool:
    """SÖZLEŞME E5 istisnası: veri hatası (ör. aykırı fiyat) olan bugünkü kupon, ilk maçı başlamadan sahibinin komutuyla
    (likely_iptal) silinir ve karneye girmez; kayıtta "iptal_edilen" altında nedeniyle kalır, sahibine raporlanır."""
    veri = yukle()
    tarih = simdi.astimezone(ZoneInfo(ayar.saat_dilimi)).date().isoformat()
    gun = next((g for g in veri["gunler"] if g["tarih"] == tarih), None)
    k = next((k for k in (gun or {}).get("secilen", []) if k["ad"] == ad), None)
    if k is None or k["durum"] != "bekliyor":
        yaz(f"Mr. Likely: bugün iptal edilecek '{ad}' kuponu yok (ya da sonuçlandı).")
        return False
    ilk = min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"])
    if simdi >= ilk - timedelta(minutes=5):
        yaz(f"Mr. Likely: '{ad}' kuponunun ilk maçı başladı (ya da başlamak üzere); geri alınamaz (E5).")
        return False
    if k.get("tweet_id"):
        x.sil(k["tweet_id"])
    gun["secilen"].remove(k)
    gun.setdefault("iptal_edilen", []).append({**k, "iptal": {"neden": neden, "zaman": simdi.isoformat(timespec="seconds")}})
    kaydet(veri)
    yaz(f"Mr. Likely: '{ad}' kuponu iptal edildi ({neden}); post silindi, karneye girmez.")
    return True


def yeniden_paylas(ayar, x, simdi: datetime, yaz=print) -> int:
    """Bugün paylaşılmış, maçı başlamamış kupon postlarını siler ve hemen yeniden paylaşılacak şekilde sıraya koyar
    (aynı kupon, güncel post düzeniyle). Maçı başlamış ya da sonuçlanmış kupona dokunulmaz."""
    cfg = ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik":
        return 0
    veri = yukle()
    adet = 0
    for gun in veri["gunler"][-1:]:
        for n, k in enumerate(gun.get("secilen", [])):
            ilk = min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"])
            if not (k.get("oto") and k.get("tweet_id") and k["durum"] == "bekliyor" and simdi < ilk - timedelta(minutes=cfg.oto_son_dk + 10)):
                continue
            x.sil(k["tweet_id"])
            k.setdefault("silinen", []).append(k.pop("tweet_id"))
            k.pop("yayin", None)
            k["paylas"] = (simdi + timedelta(minutes=40 * adet)).isoformat(timespec="seconds")
            adet += 1
            kaydet(veri)
    yaz(f"Mr. Likely: {adet} kupon postu silindi, yeniden paylaşılacak.")
    return adet


# ---------- 8. Ölçüm (gölge test): hiçbir şey paylaşılmaz ----------
# Sabah havuzundaki BÜTÜN ayakların sonucu kaydedilir (yalnızca seçilen kuponlarınki değil): kuralları gerçek sonuçla
# sınamak için haftada yüzlerce ayak. Maliyet: API-Football toplu istek (20 maç/istek), günde ~3-4 istek; X'e post,
# Claude çağrısı, The Odds API kredisi yok. Rapor kayıtlı havuzda kural varyantlarını yeniden oynatır.

OLCUM = config.ROOT / "data" / "likely_olcum"  # gün başına bir dosya
OLCUM_ARALIK = timedelta(minutes=55)            # bir günün sonuçları en fazla saatte bir sorulur
OLCUM_ALANLARI = ("aday_id", "fixture_id", "pazar", "tur", "oran", "olasilik", "deger", "kaynak", "uyum", "buyuk", "baslama")


def olcum_guncelle(sonuc_al, simdi: datetime, yaz=print) -> int:
    """Havuzdaki ayakların sonuçları. sonuc_al(fixture_ids) -> {fixture_id: {"durum", "skor", "iy"}} (toplu istek).
    The Odds API'den gelen (kredi harcar) ve korner (ayrı istek) ayakları ölçülmez. Sonuçlanan ayak sayısını döndürür."""
    veri = yukle()
    sorulacak: dict[str, list[dict]] = {}
    for gun in veri["gunler"]:
        if not gun.get("havuz") or gun.get("olcum_bitti"):
            continue
        if gun.get("olcum_sorgu") and simdi - datetime.fromisoformat(gun["olcum_sorgu"]) < OLCUM_ARALIK:
            continue
        for a in gun["havuz"]:
            if "sonuc" in a:
                continue
            if a.get("odds_id") or a["pazar"].startswith("KOR"):
                a["sonuc"] = "yok"
            elif datetime.fromisoformat(a["baslama"]) + MAC_SURESI <= simdi:
                sorulacak.setdefault(gun["tarih"], []).append(a)
    idler = sorted({a["fixture_id"] for ayaklar in sorulacak.values() for a in ayaklar})
    cevap = sonuc_al(idler) if idler else {}
    adet = 0
    for gun in veri["gunler"]:
        if gun["tarih"] in sorulacak:
            gun["olcum_sorgu"] = simdi.isoformat(timespec="seconds")
            for a in sorulacak[gun["tarih"]]:
                r = cevap.get(a["fixture_id"]) or {"durum": "bekliyor"}
                sonuc = None
                if r["durum"] == "bitti":
                    k = model.kazandi_mi(a["pazar"], *r["skor"], iy=r.get("iy"))
                    sonuc = "iade" if k is None else "kazandi" if k else "kaybetti"
                elif r["durum"] == "iptal":
                    sonuc = "iade"
                elif datetime.fromisoformat(a["baslama"]) + VAZGEC <= simdi:
                    sonuc = "yok"  # sonuç gelmedi: ölçüme girmez
                if sonuc:
                    a["sonuc"] = sonuc
                    adet += sonuc != "yok"
        biten = bool(gun.get("havuz")) and not gun.get("olcum_bitti") and all("sonuc" in a for a in gun["havuz"])
        if biten:
            gun["olcum_bitti"] = True
        if gun["tarih"] in sorulacak or biten:
            _olcum_yaz(gun)
    kaydet(veri)
    if adet:
        yaz(f"Mr. Likely ölçümü: {adet} havuz ayağı sonuçlandı ({len(idler)} maç).")
    return adet


def _olcum_yaz(gun: dict) -> None:
    satirlar = [{**{k: a[k] for k in OLCUM_ALANLARI if k in a}, "sonuc": a["sonuc"]}
                for a in gun["havuz"] if a.get("sonuc") in ("kazandi", "kaybetti", "iade")]
    OLCUM.mkdir(parents=True, exist_ok=True)
    (OLCUM / f'{gun["tarih"]}.json').write_text(json.dumps({"tarih": gun["tarih"], "tam": bool(gun.get("olcum_bitti")),
                                                            "ayaklar": satirlar}, ensure_ascii=False) + "\n", encoding="utf-8")


def olcum_oku() -> list[dict]:
    try:
        return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(OLCUM.glob("*.json"))]
    except (OSError, ValueError):
        return []


GRUPLAR = (("Ev ya da deplasman (12)", ("CS12",)), ("Çifte şans 1X / X2", ("CS1X", "CSX2")),
           ("Maç sonucu", ("MS",)), ("Toplam gol", ("UST", "ALT")), ("İlk yarı", ("IY",)),
           ("Takım golü", ("EVU", "EVA", "DPU", "DPA")), ("Diğer", ("",)))


def _grup(pazar: str) -> str:
    return next(ad for ad, onekler in GRUPLAR if pazar.startswith(onekler))


def kupona_uygun(a: dict, cfg: LikelyAyar) -> bool:
    """otomatik_sec'in ayak süzgeci (E6): istatistikle uyumlu, keskin piyasa, oran adil fiyata yakın, sağlam ya da değerli."""
    return (a["pazar"] not in cfg.oto_yasak_pazarlar and a["deger"] <= cfg.oto_max_ayak_deger
            and a["uyum"] and a["deger"] >= cfg.oto_min_deger and not a["kaynak"].lower().startswith("average")
            and (a["tur"] == "deger" or a["olasilik"] >= cfg.oto_min_ayak))


def kalibrasyon(gunler: list[dict], cfg: LikelyAyar) -> list[dict]:
    """Kupona girebilen ayaklar, pazar grubuna göre: kaç ayak, ihtimale göre kaçı tutmalıydı, kaçı tuttu, sapma (z).
    |z| ≥ 2: fark tesadüfle açıklanması zor (yaklaşık %5). Daha küçük fark örneklem gürültüsüdür."""
    toplam: dict[str, list] = {}
    for g in gunler:
        for a in g["ayaklar"]:
            if a["sonuc"] == "iade" or not kupona_uygun(a, cfg):
                continue
            for ad in (_grup(a["pazar"]), "Toplam"):
                t = toplam.setdefault(ad, [0, 0.0, 0, 0.0])
                t[0] += 1
                t[1] += a["olasilik"]
                t[2] += a["sonuc"] == "kazandi"
                t[3] += a["olasilik"] * (1 - a["olasilik"])
    return [{"grup": ad, "ayak": n, "beklenen": round(e, 1), "tutan": m, "z": round((m - e) / math.sqrt(v), 1) if v else 0.0}
            for ad, (n, e, m, v) in sorted(toplam.items(), key=lambda x: (x[0] == "Toplam", -x[1][0]))]


# Yeniden oynatılan kural varyantları: (ad, ayak süzgeci, ayar değişikliği). İlki bugünkü kurallar (E6).
VARYANTLAR = (
    ("Bugünkü kurallar", lambda a: True, {}),
    ("12 (ev ya da deplasman) dahil (14 Ekim'e kadarki kural)", lambda a: True, {"oto_yasak_pazarlar": ()}),
    ("Büyük maç önceliği olmadan", lambda a: True, {"oto_buyuk_tolerans": 0.0}),
    ("Long shot ayak oranı sınırı olmadan", lambda a: True, {"oto_uzun_min_ayak_oran": 0.0}),
    # Büyük maç kuponu fiyattan takılıyor (4 ayakta bahisçi payı ~%11 birikiyor): sınır gevşerse ne olur?
    ("Kupon fiyat sınırı −%12 (günün + büyük maçlar)", lambda a: True, {"oto_min_kupon_deger": -0.12}),
)


def golge_kuponlar(gunler: list[dict], cfg: LikelyAyar) -> list[dict]:
    """Her varyant, sonuçları tam olan her günün sabah havuzunda otomatik_sec ile yeniden oynatılır (paylaşılmaz).
    Kupon türü başına: kaç kupon, kaçı tuttu, ihtimallere göre kaçı tutmalıydı, ortalama oran."""
    sonuc = []
    for ad, suzgec, degisiklik in VARYANTLAR:
        c = replace(cfg, **degisiklik)
        tur: dict[str, list] = {}
        for g in gunler:
            if not g.get("tam"):
                continue
            ayaklar = [a for a in g["ayaklar"] if suzgec(a)]
            harita = {a["aday_id"]: a for a in ayaklar}
            for k in otomatik_sec(ayaklar, c):
                durumlar = [harita[i]["sonuc"] for i in k["ayaklar"]]
                if all(d == "iade" for d in durumlar):
                    continue
                tuttu = "kaybetti" not in durumlar
                t = tur.setdefault(k["ad"], [0, 0, 0.0, 0.0, 0.0])
                t[0] += 1
                t[1] += tuttu
                t[2] += k["olasilik"]
                t[3] += k["oran"]
                # Her kupon 1 birim; iade ayak 1.00 sayılır (karne ile aynı)
                t[4] += math.prod(harita[i]["oran"] for i in k["ayaklar"] if harita[i]["sonuc"] == "kazandi") - 1 if tuttu else -1
        sonuc.append({"varyant": ad, "turler": {k: {"kupon": n, "tutan": m, "beklenen": round(e, 1), "oran": round(o / n, 2),
                                                    "kar": round(kr, 2)} for k, (n, m, e, o, kr) in tur.items()}})
    return sonuc


def olcum_raporu(cfg: LikelyAyar, gunler: list[dict] | None = None) -> str:
    """Sahibine Türkçe ölçüm raporu (sabah bildiriminde ve `python -m bot.likely`)."""
    gunler = olcum_oku() if gunler is None else gunler
    if not gunler:
        return "Henüz ölçüm yok: havuz ayaklarının sonuçları maçlar bittikçe gelir."
    tam = sum(1 for g in gunler if g.get("tam"))
    s = [f"{len(gunler)} gün ({tam} tanesi tam), {sum(len(g['ayaklar']) for g in gunler)} ayak. Kaynak: sabah havuzu, paylaşılmaz.", "",
         "**Ayaklar (kupona girebilenler):** ihtimale göre beklenen ve gerçek. |z| ≥ 2 ise fark gerçek olabilir; altı gürültü.", "",
         "| Pazar | Ayak | Beklenen | Tutan | z |", "|---|---|---|---|---|"]
    s += [f"| {r['grup']} | {r['ayak']} | {r['beklenen']} | {r['tutan']} | {r['z']:+.1f} |" for r in kalibrasyon(gunler, cfg)]
    s += ["", "**Kural varyantları (aynı havuzda yeniden oynatma):**", "",
          "| Varyant | Kupon | Tutan | Beklenen | Ort. oran | Kâr (birim) |", "|---|---|---|---|---|---|"]
    for v in golge_kuponlar(gunler, cfg):
        for tur, r in sorted(v["turler"].items()):
            s.append(f"| {v['varyant']} · {KUPON_ADI.get(tur, tur)} | {r['kupon']} | {r['tutan']} | {r['beklenen']} | "
                     f"{r['oran']:.2f} | {_birim(r['kar'])} |")
    return "\n".join(s)


if __name__ == "__main__":
    print(olcum_raporu(ayar_yukle()))
