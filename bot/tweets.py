"""İsveççe tweet metinleri ve X API v2 istemcisi."""

from datetime import datetime

from requests_oauthlib import OAuth1Session

from .kayit import kar

LIMIT = 280
# twitter-text ağırlıklandırması: bu aralıklar 1, diğer karakterler 2 sayılır.
_TEK = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
ANSVAR = "18+ | Stödlinjen 020-81 91 00"


def uzunluk(metin: str) -> int:
    return sum(1 if any(a <= ord(c) <= b for a, b in _TEK) else 2 for c in metin)


def kirp(metin: str, limit: int = LIMIT) -> str:
    if uzunluk(metin) <= limit:
        return metin
    while uzunluk(metin + "…") > limit:
        metin = metin[:-1]
    return metin.rstrip() + "…"


def sayi(x: float, basamak: int = 2) -> str:
    return f"{x:.{basamak}f}".replace(".", ",")


def isaretli(x: float, basamak: int = 1) -> str:
    return ("+" if x >= 0 else "−") + sayi(abs(x), basamak)


def _rekor(o: dict) -> str:
    if not o["spel"]:
        return "📈 Rekord: start idag"
    return f'📈 Rekord: {o["vunna"]}–{o["forlorade"]} | {isaretli(o["enheter"])} e | ROI {isaretli(o["roi"])} %'


def gun_tweeti(gun: dict, ozet: dict) -> str:
    tarih = datetime.fromisoformat(gun["tarih"])

    def yaz(seviye: int, takim_max: int = 40) -> str:
        satirlar = [f"📊 DAGENS SPEL | {tarih.day}/{tarih.month}", ""]
        for i, s in enumerate(gun["secimler"], 1):
            saat = datetime.fromisoformat(s["baslama"]).strftime("%H:%M")
            deger = f' · värde {isaretli(100 * s["deger"], 0)} %' if seviye < 1 else ""
            satirlar.append(f'{i}) {s["ev"][:takim_max]} – {s["dep"][:takim_max]} ({saat})')
            satirlar.append(f'   {s["kisa"]} @ {sayi(s["oran"])} · {s["bolag"]}{deger}')
        satirlar.append("")
        if seviye < 2:
            satirlar.append("Insats: 1 enhet per spel")
        satirlar.append(_rekor(ozet))
        if seviye < 3:
            satirlar.append("Motivering i tråden 👇")
        satirlar.append(ANSVAR)
        return "\n".join(satirlar)

    # Önce süsler atılır; ansvar (18+ / Stödlinjen) satırı asla kesilmez.
    for seviye in range(4):
        metin = yaz(seviye)
        if uzunluk(metin) <= LIMIT:
            return metin
    for takim_max in range(30, 5, -2):
        metin = yaz(3, takim_max)
        if uzunluk(metin) <= LIMIT:
            return metin
    return metin


def analiz_tweetleri(gun: dict) -> list[str]:
    return [
        kirp(f'{i}) {s["ev"]} – {s["dep"]} | {s["etiket"]} @ {sayi(s["oran"])}\n\n{s["yorum"]}')
        for i, s in enumerate(gun["secimler"], 1)
    ]


def sonuc_tweeti(gun: dict, ozet: dict) -> str:
    ikon = {"kazandi": "✅", "kaybetti": "❌", "iptal": "➖"}
    biten = [s for s in gun["secimler"] if s["durum"] in ("kazandi", "kaybetti")]
    vunna = sum(s["durum"] == "kazandi" for s in biten)
    dag = sum(kar(s) for s in gun["secimler"])
    satirlar = [f"Resultat: {vunna} av {len(biten)} vann", ""]
    for s in gun["secimler"]:
        skor = (s.get("skor") or "inställd").replace("-", "–")
        satirlar.append(f'{ikon[s["durum"]]} {s["ev"]} {skor} {s["dep"]} ({s["kisa"]}) {isaretli(kar(s), 2)} e')
    satirlar += ["", f"Dagen: {isaretli(dag, 2)} enheter",
                 f'📈 Totalt: {ozet["vunna"]}–{ozet["forlorade"]} ({sayi(ozet["traff"], 0)} %) | '
                 f'{isaretli(ozet["enheter"])} e | ROI {isaretli(ozet["roi"])} %']
    return kirp("\n".join(satirlar))


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


class KonsolClient:
    """Paylaşmadan ekrana yazar (demo / taslak önizleme)."""

    def __init__(self):
        self.sayac = 0

    def gonder(self, metin: str, yanit: str | None = None) -> str:
        self.sayac += 1
        print(f"\n----- TWEET #{self.sayac}{' (yanıt)' if yanit else ''} [{uzunluk(metin)}/280] -----\n{metin}")
        return f"demo-{self.sayac}"
