"""Sade İngilizce tweet floodları ve X API v2 istemcisi.

Günlük paylaşım bir flood'dur: 1) günün kuponu, 2) para/kasa özeti, 3+) her maç için açıklama.
Sonuçlar da ana tweetin altına iki tweetlik bir flood olarak gelir."""

from datetime import datetime

from requests_oauthlib import OAuth1Session

from .kayit import kar, kombi_durumu, kombi_kar, kombi_olasilik, kombi_oran

LIMIT = 280
# twitter-text ağırlıklandırması: bu aralıklar 1, diğer karakterler 2 sayılır.
_TEK = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
ANSVAR = "18+ | Play responsibly"
TUR = {"guvenli": "safe pick", "deger": "value pick"}


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
    return f"{'-' if x < 0 else ''}{birim}{abs(x):,.0f}"


def isaretli_para(x: float, birim: str) -> str:
    return ("+" if x >= 0 else "") + para(x, birim)


def oran_metni(s: dict) -> str:
    """Bet builder oranı bahisçiden değil modelden tahmin edildiği için ≈ ile gösterilir.
    X "@1.25" gibi metinleri kullanıcı etiketi sandığı için oranlarda asla "@" kullanılmaz."""
    return f'{"≈" if s.get("bet_builder") else ""}{s["oran"]:.2f}'


def rekor(o: dict) -> str:
    if not o["spel"]:
        return "📈 Record: starts today"
    metin = f'📈 Record: {o["vunna"]}–{o["forlorade"]} ({o["traff"]:.0f}%)'
    if o["kombi"]:
        metin += f' · coupons {o["kombi_tuttu"]}/{o["kombi"]}'
    return metin


def _tarih(gun: dict) -> str:
    return datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")


def _mac(s: dict, takim_max: int = 40) -> str:
    return f'{s["ev"][:takim_max]} v {s["dep"][:takim_max]}'


def gun_tweeti(gun: dict, ozet: dict | None = None) -> str:
    """Ana tweet: günün kuponu (tek oyunluk günde günün oyunu), yatırım ve dönüş."""
    secimler, birim = gun["secimler"], gun["para"]
    kupon = bool(gun.get("kombi"))
    tek = len(secimler) == 1

    def yaz(odds_kelimesi: bool, takim_max: int = 40, detay: bool = True) -> str:
        o = "odds " if odds_kelimesi else ""
        baslik = "COUPON" if kupon else ("PICK" if tek else "PICKS")
        satirlar = [f"⚽ TODAY'S {baslik} | {_tarih(gun)}", ""]
        for i, s in enumerate(secimler, 1):
            satirlar.append(_mac(s, takim_max) if tek else f"{i}) {_mac(s, takim_max)}")
            satirlar.append(f'{s["kisa"]} · {o}{oran_metni(s)}' + (f' · {yuzde(s["adil_olasilik"])} chance' if tek else ""))
        satirlar.append("")
        if kupon:
            stake = gun["kombi"]["stake"]
            satirlar.append(f"Total odds {kombi_oran(gun):.2f} · real chance {yuzde(kombi_olasilik(gun))}")
            satirlar.append(f"{para(stake, birim)} stake → {para(stake * kombi_oran(gun), birim)} return")
        elif tek:
            s = secimler[0]
            satirlar.append(f'{para(s["stake"], birim)} stake → {para(s["stake"] * s["oran"], birim)} return')
        else:
            satirlar.append(f'{para(secimler[0]["stake"], birim)} stake on each pick')
        if detay:
            satirlar.append("Details 👇")
        satirlar.append(ANSVAR)
        return "\n".join(satirlar)

    # Sığmazsa sırayla: "odds" kelimesi, "Details" satırı düşer; takım adları en son çare olarak kısalır.
    return ilk_sigan(yaz(True), yaz(False), yaz(False, detay=False),
                     *(yaz(False, n, detay=False) for n in range(24, 5, -2)))


def kasa_tweeti(gun: dict, ozet: dict) -> str:
    """İkinci tweet: kasa ve hangi oyuna ne kadar yatırıldığı."""
    secimler, birim = gun["secimler"], gun["para"]

    def yaz(sanal: bool, sans: bool) -> str:
        satirlar = [f'💰 Bank {para(ozet["kasa"], birim)}{" (virtual)" if sanal else ""} · {gun["yuzde"]:g}% per bet', ""]
        if gun.get("kombi"):
            stake = gun["kombi"]["stake"]
            satirlar += [f"Coupon, all {len(secimler)} together: {para(stake, birim)} → "
                         f"{para(stake * kombi_oran(gun), birim)} if all win ({yuzde(kombi_olasilik(gun))} chance)", ""]
        if len(secimler) >= 2:
            satirlar.append(f'Singles, {para(secimler[0]["stake"], birim)} each:')
            for i, s in enumerate(secimler, 1):
                ek = f' ({yuzde(s["adil_olasilik"])})' if sans else ""
                satirlar.append(f'{i}) {s["kisa"]} → {para(s["stake"] * s["oran"], birim)}{ek}')
            satirlar.append("")
        else:
            s = secimler[0]
            satirlar += [f'Stake {para(s["stake"], birim)} → {para(s["stake"] * s["oran"], birim)} if it wins', ""]
        satirlar.append(rekor(ozet))
        return "\n".join(satirlar)

    return ilk_sigan(yaz(True, True), yaz(False, True), yaz(False, False))


def _cumleler(metin: str) -> list[str]:
    """Açıklamayı cümle sonlarından kısaltma adayları: tam metin, sonra sondan birer cümle eksik."""
    parcalar = [p for p in metin.replace(". ", ".\n").split("\n") if p]
    return [" ".join(parcalar[:n]) for n in range(len(parcalar), 0, -1)]


def analiz_tweetleri(gun: dict) -> list[str]:
    """Her oyun için bir tweet. Sığmazsa önce skor satırı düşer, sonra açıklama cümle cümle kısalır;
    cümle ortasından kesilmez."""
    def tweet(i: int, s: dict) -> str:
        tur = ("bet builder, " if s.get("bet_builder") else "") + TUR[s["tur"]]
        bas = (f'{i}) {_mac(s)} · {s["saat"]}\nPick: {s["etiket"]}\n'
               f'Odds {oran_metni(s)} · chance {yuzde(s["adil_olasilik"])} · {tur}')
        skor = f'\nMost likely score: {s["olasi_skor"].replace("-", "–")}'
        yorumlar = _cumleler(s["yorum"]) if s["yorum"] else [""]
        adaylar = [bas + skor + (f"\n\n{y}" if y else "") for y in yorumlar[:1]]
        adaylar += [bas + (f"\n\n{y}" if y else "") for y in yorumlar]
        adaylar.append(bas + skor)
        return ilk_sigan(*adaylar)
    return [tweet(i, s) for i, s in enumerate(gun["secimler"], 1)]


def gun_floodu(gun: dict, ozet: dict) -> list[str]:
    return [gun_tweeti(gun, ozet), kasa_tweeti(gun, ozet)] + analiz_tweetleri(gun)


def sonuc_tweetleri(gun: dict, ozet: dict) -> list[str]:
    ikon = {"kazandi": "✅", "kaybetti": "❌", "iptal": "➖"}
    birim = gun["para"]
    satirlar = [f"📊 RESULTS | {_tarih(gun)}", ""]
    for s in gun["secimler"]:
        skor = (s.get("skor") or "postponed").replace("-", "–")
        satirlar.append(f'{ikon[s["durum"]]} {s["ev"]} {skor} {s["dep"]}')
        satirlar.append(f'   {s["kisa"]}')
    kombi = kombi_durumu(gun) if gun.get("kombi") else None
    if kombi in ("tuttu", "yatti"):
        satirlar += ["", f'🎯 Coupon: {"✅ won" if kombi == "tuttu" else "❌ lost"}']
    ilk = kirp("\n".join(satirlar))

    biten = [s for s in gun["secimler"] if s["durum"] in ("kazandi", "kaybetti")]
    tekli_kar = sum(kar(s) for s in gun["secimler"])
    para_satirlari = []
    if kombi in ("tuttu", "yatti"):
        para_satirlari.append(f"🎯 Coupon: {isaretli_para(kombi_kar(gun), birim)}")
    para_satirlari.append(f'Singles: {sum(s["durum"] == "kazandi" for s in biten)}/{len(biten)} won, '
                          f'{isaretli_para(tekli_kar, birim)}')
    para_satirlari += [f'💰 Bank: {para(ozet["kasa"], birim)} ({ozet["kasa_degisim"]:+.1f}%)', rekor(ozet)]
    return [ilk, kirp("\n".join(para_satirlari))]


SABIT_TWEETLER = [
    """Day 1 of the €10,000 challenge 📊

A public, virtual €10,000 bank run on data:
• Each pick = 1% of the current bank
• Safe picks + value picks
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

    def gonder(self, metin: str, yanit: str | None = None) -> str:
        body: dict = {"text": metin}
        if yanit:
            body["reply"] = {"in_reply_to_tweet_id": yanit}
        r = self.session.post(self.URL, json=body, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"X API hatası {r.status_code}: {r.text}")
        return r.json()["data"]["id"]

    def son_tweetler(self, adet: int = 30) -> list[dict]:
        me = self.session.get("https://api.x.com/2/users/me", timeout=30).json()["data"]["id"]
        r = self.session.get(f"https://api.x.com/2/users/{me}/tweets", params={"max_results": adet}, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text}")
        return r.json().get("data", [])

    def sil(self, tweet_id: str) -> None:
        r = self.session.delete(f"{self.URL}/{tweet_id}", timeout=30)
        if r.status_code >= 400 and r.status_code != 404:
            raise RuntimeError(f"X API silme hatası {r.status_code}: {r.text}")


class KonsolClient:
    """Paylaşmadan ekrana yazar (demo / taslak önizleme)."""

    def __init__(self):
        self.sayac = 0

    def gonder(self, metin: str, yanit: str | None = None) -> str:
        self.sayac += 1
        print(f"\n----- TWEET #{self.sayac}{' (yanıt)' if yanit else ''} [{uzunluk(metin)}/280] -----\n{metin}")
        return f"demo-{self.sayac}"

    def sil(self, tweet_id: str) -> None:
        print(f"----- SİLİNDİ: {tweet_id} -----")
