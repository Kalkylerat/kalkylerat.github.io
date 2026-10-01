"""Sade İngilizce tweet floodları ve X API v2 istemcisi.

Günlük paylaşım bir flood'dur: 1) günün kupon görselleri, 2+) her maç için açıklama.
Her kupon (tek maç ya da kombine) kasanın %1'iyle oynanır. Sonuçlar ana tweetin altına gelir."""

import re
from datetime import datetime

from requests_oauthlib import OAuth1Session

from .kayit import kar, kupon_ayaklari, kupon_durumu, kupon_kar, kupon_olasilik, kupon_oran, kuponlar

LIMIT = 280
# twitter-text ağırlıklandırması: bu aralıklar 1, diğer karakterler 2 sayılır.
_TEK = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
ANSVAR = "18+ | Play responsibly"
TUR = {"guvenli": "high-chance pick", "deger": "value pick"}


# Yalnızca büyük turnuvalar için, gerçek etiketler (X rehberi: en fazla 1-2). Ülkeye göre doğrulanır:
# "Premier League" Kenya'da da var, "Serie A" Brezilya'da da.
_ULUSLARARASI = (("champions league women", "#UWCL"), ("uefa nations league", "#NationsLeague"),
                 ("uefa champions league", "#UCL"), ("uefa europa league", "#UEL"), ("conference league", "#UECL"))
_ULUSAL = {("premier league", "england"): "#PremierLeague", ("la liga", "spain"): "#LaLiga",
           ("serie a", "italy"): "#SerieA", ("bundesliga", "germany"): "#Bundesliga", ("ligue 1", "france"): "#Ligue1",
           ("eredivisie", "netherlands"): "#Eredivisie", ("süper lig", "turkey"): "#SuperLig",
           ("allsvenskan", "sweden"): "#Allsvenskan"}
IZINLI_ETIKETLER = {e for _, e in _ULUSLARARASI} | set(_ULUSAL.values())

# Milli takımlar: resmi FIFA kodları (maç etiketi #DENPOR gibi). Ad kırpılarak üretilmez: "NET" değil "NED".
FIFA_KODLARI = {
    "albania": "ALB", "andorra": "AND", "armenia": "ARM", "austria": "AUT", "azerbaijan": "AZE", "belarus": "BLR",
    "belgium": "BEL", "bosnia & herzegovina": "BIH", "bosnia and herzegovina": "BIH", "bulgaria": "BUL",
    "croatia": "CRO", "cyprus": "CYP", "czech republic": "CZE", "czechia": "CZE", "denmark": "DEN", "england": "ENG",
    "estonia": "EST", "faroe islands": "FRO", "finland": "FIN", "france": "FRA", "georgia": "GEO", "germany": "GER",
    "gibraltar": "GIB", "greece": "GRE", "hungary": "HUN", "iceland": "ISL", "israel": "ISR", "italy": "ITA",
    "kazakhstan": "KAZ", "kosovo": "KVX", "latvia": "LVA", "liechtenstein": "LIE", "lithuania": "LTU",
    "luxembourg": "LUX", "malta": "MLT", "moldova": "MDA", "montenegro": "MNE", "netherlands": "NED",
    "north macedonia": "MKD", "northern ireland": "NIR", "norway": "NOR", "poland": "POL", "portugal": "POR",
    "rep. of ireland": "IRL", "republic of ireland": "IRL", "ireland": "IRL", "romania": "ROU", "san marino": "SMR",
    "scotland": "SCO", "serbia": "SRB", "slovakia": "SVK", "slovenia": "SVN", "spain": "ESP", "sweden": "SWE",
    "switzerland": "SUI", "turkey": "TUR", "türkiye": "TUR", "ukraine": "UKR", "wales": "WAL",
    "argentina": "ARG", "brazil": "BRA", "uruguay": "URU", "colombia": "COL", "mexico": "MEX", "usa": "USA",
    "canada": "CAN", "japan": "JPN", "morocco": "MAR",
}
# Büyük kulüplerin X'te yaygın etiketleri (yalnızca bunlar; bilinmeyen kulübe etiket uydurulmaz).
KULUP_ETIKETLERI = {
    "arsenal": "#Arsenal", "chelsea": "#Chelsea", "liverpool": "#Liverpool", "manchester united": "#MUFC",
    "manchester city": "#ManCity", "tottenham": "#THFC", "newcastle": "#NUFC", "aston villa": "#AVFC",
    "real madrid": "#RealMadrid", "barcelona": "#Barca", "atletico madrid": "#Atleti", "bayern munich": "#FCBayern",
    "bayern münchen": "#FCBayern", "borussia dortmund": "#BVB", "paris saint germain": "#PSG", "juventus": "#Juventus",
    "inter": "#Inter", "ac milan": "#ACMilan", "napoli": "#Napoli", "galatasaray": "#Galatasaray",
    "fenerbahce": "#Fenerbahce", "fenerbahçe": "#Fenerbahce", "besiktas": "#Besiktas", "beşiktaş": "#Besiktas",
    "ajax": "#Ajax", "benfica": "#Benfica", "porto": "#FCPorto", "celtic": "#CelticFC",
}


def mac_etiketi(ev: str, dep: str) -> str | None:
    """Milli maçta #DENPOR; kulüp maçında bilinen büyük kulübün etiketi (önce ev sahibi); yoksa None."""
    a, b = FIFA_KODLARI.get(ev.lower().strip()), FIFA_KODLARI.get(dep.lower().strip())
    if a and b:
        return f"#{a}{b}"
    return KULUP_ETIKETLERI.get(ev.lower().strip()) or KULUP_ETIKETLERI.get(dep.lower().strip())


def izinli_etiket(e: str) -> bool:
    return (e in IZINLI_ETIKETLER or e in KULUP_ETIKETLERI.values()
            or bool(re.fullmatch(r"#[A-Z]{6}", e) and e[1:4] in FIFA_KODLARI.values() and e[4:] in FIFA_KODLARI.values()))


def hashtag(lig: str | None, ulke: str | None = "") -> str | None:
    l = (lig or "").lower().strip()
    for anahtar, etiket in _ULUSLARARASI:
        if anahtar in l:
            return etiket
    if l == "epl":
        return "#PremierLeague"
    if " - " in l:  # The Odds API: "La Liga - Spain"
        l, ulke = l.split(" - ", 1)
    return _ULUSAL.get((l.strip(), (ulke or "").lower().strip()))


def etiket_satiri(ligler: list[tuple[str, str]], maclar: list[tuple[str, str]] = (), en_fazla: int = 2) -> str:
    """En fazla iki etiket: öndeki maçın turnuvası + o maçın etiketi (#DENPOR / #Arsenal); maç etiketi yoksa
    ikinci turnuva. (lig, ülke) ve (ev, dep) listeleri aynı sıradadır (öndeki maç ilk)."""
    turnuva = []
    for lig, ulke in ligler:
        e = hashtag(lig, ulke)
        if e and e not in turnuva:
            turnuva.append(e)
    mac = next((e for e in (mac_etiketi(ev, dep) for ev, dep in maclar) if e), None)
    etiketler = turnuva[:1] + ([mac] if mac else turnuva[1:2])
    return " ".join(etiketler[:en_fazla])


def uzunluk(metin: str) -> int:
    return sum(1 if any(a <= ord(c) <= b for a, b in _TEK) else 2 for c in metin)


def kirp(metin: str, limit: int = LIMIT) -> str:
    if uzunluk(metin) <= limit:
        return metin
    while uzunluk(metin + "…") > limit:
        metin = metin[:-1]
    return metin.rstrip() + "…"


def ilk_sigan(*secenekler: str) -> str:
    """Sırayla dener; 280 karaktere ilk sığanı döndürür, hiçbiri sığmazsa sonuncuyu kırpar."""
    for metin in secenekler:
        if uzunluk(metin) <= LIMIT:
            return metin
    return kirp(secenekler[-1])


def yuzde(p: float) -> str:
    return f"{100 * p:.0f}%"


def para(x: float, birim: str) -> str:
    """Kuruşlu: yuvarlanmış tam sayılar "önce + kâr = sonra" toplamını bozuyordu (9,972 + 101 ≠ 10,074)."""
    return f"{'-' if round(x, 2) < 0 else ''}{birim}{abs(x):,.2f}"


def isaretli_para(x: float, birim: str) -> str:
    return ("+" if x >= 0 else "") + para(x, birim)


def oran_metni(s: dict) -> str:
    """Bet builder oranı bahisçiden değil modelden tahmin edildiği için ≈ ile gösterilir.
    X "@1.25" gibi metinleri kullanıcı etiketi sandığı için oranlarda asla "@" kullanılmaz."""
    return f'{"≈" if s.get("bet_builder") else ""}{s["oran"]:.2f}'


def kupon_oran_metni(gun: dict, kupon: dict) -> str:
    """Kuponda bet builder varsa toplam oran da tahminidir: ≈ ile gösterilir."""
    tahmini = any(s.get("bet_builder") for s in kupon_ayaklari(gun, kupon))
    return f'{"≈" if tahmini else ""}{kupon_oran(gun, kupon):.2f}'


def rekor(o: dict) -> str:
    if not o["spel"] and not o["kombi"]:
        return "📈 Record: starts today"
    parcalar = []
    if o["kombi"]:
        parcalar.append(f'coupons {o["kombi_tuttu"]}/{o["kombi"]} won')
    if o["spel"]:
        parcalar.append(f'picks {o["vunna"]}–{o["forlorade"]} ({o["traff"]:.0f}%)')
    return "📈 Record: " + " · ".join(parcalar)


def _tarih(gun: dict) -> str:
    return datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")


def _mac(s: dict, takim_max: int = 40) -> str:
    return f'{s["ev"][:takim_max]} v {s["dep"][:takim_max]}'


def _baslik(gun: dict) -> str:
    n = len(kuponlar(gun))
    if gun.get("ek"):
        return "BONUS COUPON" if n <= 1 else f"{n} BONUS COUPONS"
    return "TODAY'S COUPON" if n <= 1 else f"TODAY'S {n} COUPONS"


def kupon_no(gun: dict, secim_sira: int) -> int | None:
    """Oyunun kaçıncı kuponda olduğu (1'den başlar); tek kuponlu günde None."""
    liste = kuponlar(gun)
    if len(liste) < 2:
        return None
    return next((n for n, k in enumerate(liste, 1) if secim_sira in k["ayaklar"]), None)


# Yorum yapmaya davet eden sorular (etkileşim algoritmada öne çıkarır). Her gün sırayla biri seçilir;
# "RT yap / beğen" gibi X'in cezalandırdığı etkileşim tuzakları kullanılmaz, gerçek bir fikir sorulur.
KUPON_SORULARI = [
    "Which pick do you trust most? Tell us below 👇",
    "Would you back this coupon? Reply with your take 👇",
    "Which leg worries you most? 👇",
    "What would you add or change? Drop your pick below 👇",
    "Agree with the picks? Tell us why (or why not) 👇",
    "Which match are you watching today? 👇",
    "Would you play this one? Let us know below 👇",
]
# Tek maçlık kuponda tekil dil ("the picks" değil "the pick").
KUPON_SORULARI_TEK = [
    "Do you trust this pick? Tell us below 👇",
    "Would you back this one? Reply with your take 👇",
    "Agree with the pick? Tell us why (or why not) 👇",
    "Which way do you see this match going? 👇",
    "Would you play it? Let us know below 👇",
]
# Tek maçta karşılaştırma sorulmaz ("hangisi şaşırttı" gibi): soru o maçın kendisi hakkındadır.
SONUC_SORULARI_TEK = {
    "tuttu": ["Did you have {mac} going this way too? 👇", "Who else read {mac} like this? 👇",
              "How did you call {mac}? 👇"],
    "yatti": ["Not our day. How did you read {mac}? 👇", "Did you see that {mac} result coming? 👇",
              "What did we miss in {mac}? Tell us below 👇"],
    None: ["How did you call {mac}? 👇"],
}
SONUC_SORULARI = {  # kazanan ve kaybeden kuponda farklı: ikisinde de yoruma davet
    "tuttu": ["Did you follow it? 👇", "Who else had this one? 👇", "Which leg did you trust most? 👇"],
    "yatti": ["Tough one. Which result surprised you most? 👇", "Not our day. How did your picks go? 👇",
              "What did we miss? Tell us below 👇"],
    None: ["How did your picks do? 👇"],
}


def _gunun(sorular: list[str], gun: dict) -> str:
    return sorular[datetime.fromisoformat(gun["tarih"]).toordinal() % len(sorular)]


def _tek_mac(gun: dict) -> bool:
    return len(gun.get("secimler") or []) == 1


def _kupon_sorusu(gun: dict) -> str:
    return _gunun(KUPON_SORULARI_TEK if _tek_mac(gun) else KUPON_SORULARI, gun)


def _sonuc_sorusu(gun: dict, genel) -> str:
    if _tek_mac(gun):
        return _gunun(SONUC_SORULARI_TEK[genel], gun).format(mac=_mac(gun["secimler"][0], 20))
    return _gunun(SONUC_SORULARI[genel], gun)


def gorselli_gun_tweeti(gun: dict) -> str:
    """Kupon görselleriyle giden ana tweet. Tek başına anlaşılır olsun (X Direktörü): öndeki maç, seçim ve
    ihtimal başlıkta; bir soru yorumlara davet eder, gerekçeler yanıtlarda."""
    bas, soru = f"{_baslik(gun)} | {_tarih(gun)}", _kupon_sorusu(gun)
    etiket = etiket_satiri([(s.get("lig"), s.get("ulke")) for s in gun.get("secimler") or []],
                           [(s["ev"], s["dep"]) for s in gun.get("secimler") or []])
    neden = "Why this pick" if _tek_mac(gun) else "Why these picks"
    kuyruk = f"{neden}: in the thread 🧵{' ' + etiket if etiket else ''}\n{ANSVAR}"
    sade = f"{bas}\n\n{soru}\n\n{kuyruk}"
    if not gun.get("secimler"):
        return sade
    s = gun["secimler"][0]
    diger = len(gun["secimler"]) - 1
    on = (f'⚽ {_mac(s, 30)}: {s["kisa"]} · {yuzde(s["adil_olasilik"])} chance'
          + (f'\n+ {diger} more leg{"s" if diger > 1 else ""}' if diger else ""))
    return ilk_sigan(f"{bas}\n\n{on}\n\n{soru}\n\n{kuyruk}", sade)


def gun_tweeti(gun: dict, ozet: dict | None = None) -> str:
    """Görsel yüklenemezse ana tweet: kuponlar metin olarak."""
    birim = gun["para"]
    liste = kuponlar(gun)

    def yaz(kasa_satiri: bool, takim_max: int = 40) -> str:
        satirlar = [f"⚽ {_baslik(gun)} | {_tarih(gun)}"]
        if kasa_satiri and ozet:
            banka = round(next((k["kasa"] for k in kuponlar(gun) if k.get("kasa") is not None), ozet["kasa"])
                          - sum(k["stake"] for k in kuponlar(gun)), 2)
            satirlar.append(f'💰 Balance {para(banka, birim)} · {gun["yuzde"]:g}% per coupon')
        for n, k in enumerate(liste, 1):
            ad = f"Coupon {n}" if len(liste) > 1 else "Coupon"
            satirlar += ["", f'🎫 {ad}: odds {kupon_oran_metni(gun, k)} · {yuzde(kupon_olasilik(gun, k))} chance',
                         f'{para(k["stake"], birim)} → {para(k["stake"] * kupon_oran(gun, k), birim)}']
            satirlar += [f'• {_mac(s, takim_max)}: {s["kisa"]}' for s in kupon_ayaklari(gun, k)]
        return "\n".join(satirlar)

    son = f"\n\n{ANSVAR}"
    for govde in (yaz(True), yaz(False), *(yaz(False, n) for n in range(24, 5, -2))):
        if uzunluk(govde + son) <= LIMIT:
            return govde + son
    # Hiçbiri sığmazsa kuponlar kısalır ama sorumluluk satırı her zaman kalır.
    return kirp(govde, LIMIT - uzunluk(son)) + son


def _cumleler(metin: str) -> list[str]:
    """Açıklamayı cümle sonlarından kısaltma adayları: tam metin, sonra sondan birer cümle eksik."""
    parcalar = [p for p in metin.replace(". ", ".\n").split("\n") if p]
    return [" ".join(parcalar[:n]) for n in range(len(parcalar), 0, -1)]


def skor_celiskili(s: dict) -> bool:
    """En olası tek skor seçimle çelişiyor mu (ör. "2.5 üst" ama en olası skor 0-1)? Tek skor, beklenen golden
    azını sık gösterir; seçimin yanında çelişki gibi okunur."""
    from .model import kazandi_mi
    try:
        ev, dep = map(int, (s.get("olasi_skor") or "").split("-"))
    except ValueError:
        return False
    return any(kazandi_mi(b["pazar"], ev, dep) is False for b in (s.get("bacaklar") or [s])
               if not b["pazar"].startswith(("IY", "YY", "KOR")))


def _skor_satiri(s: dict) -> str:
    """Çelişkide en olası skor yerine beklenen goller yazılır (seçimle ve gerekçeyle tutarlı)."""
    if skor_celiskili(s):
        bg = s.get("beklenen_gol")
        return f"\nExpected goals: {bg[0]:.1f} – {bg[1]:.1f}" if bg else ""
    return f'\nMost likely score: {s["olasi_skor"].replace("-", "–")}' if s.get("olasi_skor") else ""


def analiz_tweetleri(gun: dict) -> list[str]:
    """Her oyun için bir tweet. Sığmazsa önce skor satırı düşer, sonra açıklama cümle cümle kısalır;
    cümle ortasından kesilmez."""
    def tweet(i: int, s: dict) -> str:
        tur = ("bet builder, " if s.get("bet_builder") else "") + TUR[s["tur"]]
        no = kupon_no(gun, i - 1)
        bas = (f'{i}) {_mac(s)} · {s["saat"]}{f" · coupon {no}" if no else ""}\n🎯 Pick: {s["etiket"]}\n'
               f'📊 Odds {oran_metni(s)} · chance {yuzde(s["adil_olasilik"])} · {tur}')
        skor = _skor_satiri(s)
        yorumlar = _cumleler(s["yorum"]) if s["yorum"] else [""]
        adaylar = [bas + skor + (f"\n\n{y}" if y else "") for y in yorumlar[:1]]
        adaylar += [bas + (f"\n\n{y}" if y else "") for y in yorumlar]
        adaylar.append(bas + skor)
        return ilk_sigan(*adaylar)
    return [tweet(i, s) for i, s in enumerate(gun["secimler"], 1)]


def gun_floodu(gun: dict, ozet: dict, gorselli: bool = False) -> list[str]:
    ana = gorselli_gun_tweeti(gun) if gorselli else gun_tweeti(gun, ozet)
    return [ana] + analiz_tweetleri(gun)


def sonuc_tweetleri(gun: dict, ozet: dict) -> list[str]:
    """Sığarsa tek tweet, sığmazsa iki: önce maç maç sonuçlar, sonra kupon kâr/zararı ve kasa."""
    ikon = {"kazandi": "✅", "kaybetti": "❌", "iptal": "➖"}
    kupon_ikon = {"tuttu": "✅ won", "yatti": "❌ lost", "iptal": "➖ void"}
    birim = gun["para"]
    liste = kuponlar(gun)
    satirlar = [f"📊 RESULTS | {_tarih(gun)}", ""]
    for s in gun["secimler"]:
        skor = (s.get("skor") or "postponed").replace("-", "–")
        satirlar.append(f'{ikon[s["durum"]]} {s["ev"]} {skor} {s["dep"]}')
        satirlar.append(f'   {s["kisa"]}')

    para_satirlari = []
    for n, k in enumerate(liste, 1):
        durum = kupon_durumu(gun, k)
        ad = f"Coupon {n}" if len(liste) > 1 else "Coupon"
        if durum:
            para_satirlari.append(f"🎫 {ad}: {kupon_ikon[durum]}"
                                  + (f", +{para(donen(gun, k), birim)} back" if donen(gun, k) else ""))
    tekliler = [s for s in gun["secimler"] if s.get("stake") and s["durum"] in ("kazandi", "kaybetti")]
    if tekliler:  # eski kayıtlar: tekliler de oynanmıştı
        para_satirlari.append(f'Singles: {sum(s["durum"] == "kazandi" for s in tekliler)}/{len(tekliler)} won, '
                              f'{isaretli_para(sum(kar(s) for s in tekliler), birim)}')
    para_satirlari += [f'💰 Balance: {para(ozet.get("bakiye", ozet["kasa"]), birim)}', rekor(ozet)]

    durumlar = [kupon_durumu(gun, k) for k in liste]
    genel = "tuttu" if "tuttu" in durumlar else ("yatti" if "yatti" in durumlar else None)
    soru = _sonuc_sorusu(gun, genel)
    para_satirlari.append(ANSVAR)
    for tek in ("\n".join(satirlar + [""] + para_satirlari[:-1] + ["", soru, ANSVAR]),
                "\n".join(satirlar + [""] + para_satirlari)):
        if uzunluk(tek) <= LIMIT:
            return [tek]
    ikinci = "\n".join(para_satirlari[:-1] + ["", soru, ANSVAR])
    return [kirp("\n".join(satirlar)), ikinci if uzunluk(ikinci) <= LIMIT else kirp("\n".join(para_satirlari))]


def donen(gun: dict, kupon: dict) -> float:
    """Kupondan bakiyeye geri dönen para: kazançta stake × oran, kayıpta 0, iptalde stake."""
    durum = kupon_durumu(gun, kupon)
    return round(kupon["stake"] + kupon_kar(gun, kupon), 2) if durum in ("tuttu", "iptal") else 0.0


def gun_donen(gun: dict) -> float:
    return round(sum(donen(gun, k) for k in kuponlar(gun)), 2)


def gorselli_sonuc_tweeti(gun: dict, ozet: dict) -> str:
    """Sonuç kartıyla giden kısa metin: kazançta dönen para ve yeni bakiye; kayıpta bakiye aynı kalır."""
    birim, liste = gun["para"], kuponlar(gun)
    durumlar = [kupon_durumu(gun, k) for k in liste]
    geri = gun_donen(gun)
    if len(liste) == 1:
        ust = {"tuttu": "✅ Coupon won", "yatti": "❌ Coupon lost", "iptal": "➖ Coupon void"}.get(durumlar[0], "Results")
    else:
        ust = f'🎫 {durumlar.count("tuttu")} of {len(liste)} coupons won'
    ust += f": +{para(geri, birim)} back" if geri else ""
    return (f"📊 RESULTS | {_tarih(gun)}\n\n{ust}\n💰 Balance: {para(ozet.get('bakiye', ozet['kasa']), birim)}\n\n"
            f"{_sonuc_sorusu(gun, _genel(durumlar))}\n{ANSVAR}")


def _genel(durumlar: list) -> str | None:
    return "tuttu" if "tuttu" in durumlar else ("yatti" if "yatti" in durumlar else None)


def hafta_tweeti(h: dict, ozet: dict, birim: str) -> str:
    """Haftalık özet (Pazar akşamı): haftanın kuponları, oyunları, kâr/zarar ve kasa."""
    bas = datetime.fromisoformat(h["baslangic"])
    bit = datetime.fromisoformat(h["bitis"])
    aralik = f'{bas.day}–{bit.strftime("%-d %b")}' if bas.month == bit.month else f'{bas.strftime("%-d %b")} – {bit.strftime("%-d %b")}'
    satirlar = [f"📅 WEEKLY RECAP | {aralik}", ""]
    if h["kupon"]:
        satirlar.append(f'🎫 Coupons: {h["kupon_tuttu"]} of {h["kupon"]} won')
    satirlar += [f'✅ Picks: {h["kazanan"]} won · ❌ {h["kaybeden"]} lost ({h["isabet"]:.0f}%)',
                 f'This week: {isaretli_para(h["kar"], birim)}', "",
                 f'💰 Bank: {para(ozet["kasa"], birim)} ({ozet["kasa_degisim"]:+.1f}% since start)', rekor(ozet), "",
                 "Every pick posted before kick-off.", ANSVAR]
    return kirp("\n".join(satirlar))


SABIT_TWEETLER = [
    """Day 1 of the €10,000 challenge 📊

A public, virtual €10,000 bank run on data:
• Each coupon = 1% of the current bank
• High-chance picks + value picks
• Posted before kick-off, all results counted

Live record: https://kalkylerat.github.io/
How it works 👇
18+ | Play responsibly""",
    """How it works:

• Start: €10,000 (virtual money)
• Stake = 1% of the bank at that moment. Win and stakes grow, lose and they shrink, so one bad day can't sink the bank
• Chances: sharp market, margin removed, checked by our goal model
• Odds: median of big bookmakers""",
]
ESKI_KARSILAMA = ("Welcome to Kalkylerat", "Välkommen till Kalkylerat", "Day 1 of the €10,000 challenge", "How it works:")


class XClient:
    URL = "https://api.x.com/2/tweets"

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
        self.session = OAuth1Session(api_key, api_secret, access_token, access_secret)

    def medya_yukle(self, png: bytes) -> str:
        """Görseli yükler (tek başına paylaşılmaz); tweete eklemek için medya kimliği döner."""
        r = self.session.post("https://api.x.com/2/media/upload",
                              files={"media": ("kupon.png", png, "image/png")},
                              data={"media_category": "tweet_image", "media_type": "image/png"}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"X medya yükleme hatası {r.status_code}: {r.text[:300]}")
        veri = r.json().get("data") or r.json()
        return str(veri.get("id") or veri["media_id_string"])

    def gonder(self, metin: str, yanit: str | None = None, medya: list[str] | None = None,
               alinti: str | None = None, anket: dict | None = None) -> str:
        body: dict = {"text": metin}
        if anket:
            body["poll"] = anket
        if yanit:
            body["reply"] = {"in_reply_to_tweet_id": yanit}
        if alinti:
            body["quote_tweet_id"] = alinti
        if medya:
            body["media"] = {"media_ids": list(medya)[:4]}
        r = self.session.post(self.URL, json=body, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"X API hatası {r.status_code}: {r.text}")
        return r.json()["data"]["id"]

    def son_tweetler(self, adet: int = 30, yanitsiz: bool = False) -> list[dict]:
        me = self.session.get("https://api.x.com/2/users/me", timeout=30).json()["data"]["id"]
        params = {"max_results": adet} | ({"exclude": "replies,retweets"} if yanitsiz else {})
        r = self.session.get(f"https://api.x.com/2/users/{me}/tweets", params=params, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text}")
        return r.json().get("data", [])

    def metrikler(self, adet: int = 100) -> list[dict]:
        """Hesabın son tweetleri ve etkileşim rakamları (görüntülenme, yanıt, beğeni, RT)."""
        me = self.session.get("https://api.x.com/2/users/me", timeout=30).json()["data"]["id"]
        r = self.session.get(f"https://api.x.com/2/users/{me}/tweets", timeout=30,
                             params={"max_results": adet, "tweet.fields": "public_metrics,created_at"})
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text[:300]}")
        return r.json().get("data", [])

    def sil(self, tweet_id: str) -> None:
        r = self.session.delete(f"{self.URL}/{tweet_id}", timeout=30)
        if r.status_code >= 400 and r.status_code != 404:
            raise RuntimeError(f"X API silme hatası {r.status_code}: {r.text}")


class KonsolClient:
    """Paylaşmadan ekrana yazar (demo / taslak önizleme)."""

    def __init__(self, gorsel_klasoru=None):
        self.sayac = 0
        self.gorsel_klasoru = gorsel_klasoru

    def medya_yukle(self, png: bytes) -> str:
        self.gorsel_sayac = getattr(self, "gorsel_sayac", 0) + 1
        if self.gorsel_klasoru:
            (self.gorsel_klasoru / f"demo_kupon{self.gorsel_sayac}.png").write_bytes(png)
        return f"gorsel-{len(png) // 1024}KB"

    def gonder(self, metin: str, yanit: str | None = None, medya: list[str] | None = None,
               alinti: str | None = None, anket: dict | None = None) -> str:
        self.sayac += 1
        ek = (f" + {', '.join(medya)}" if medya else "") + (f" (alıntı: {alinti})" if alinti else "")
        ek += f" (anket: {' / '.join(anket['options'])}, {anket['duration_minutes']} dk)" if anket else ""
        print(f"\n----- TWEET #{self.sayac}{' (yanıt)' if yanit else ''}{ek} [{uzunluk(metin)}/280] -----\n{metin}")
        return f"demo-{self.sayac}"

    def sil(self, tweet_id: str) -> None:
        print(f"----- SİLİNDİ: {tweet_id} -----")

    def son_tweetler(self, adet: int = 30, yanitsiz: bool = False) -> list[dict]:
        return []

    def metrikler(self, adet: int = 100) -> list[dict]:
        return []
