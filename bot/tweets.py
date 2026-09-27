"""Sade İngilizce tweet metinleri ve X API v2 istemcisi."""

from datetime import datetime

from requests_oauthlib import OAuth1Session

from .kayit import kombi_durumu, kombi_olasilik, kombi_oran

LIMIT = 280
# twitter-text ağırlıklandırması: bu aralıklar 1, diğer karakterler 2 sayılır.
_TEK = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
ANSVAR = "18+ | Play responsibly"


def uzunluk(metin: str) -> int:
    return sum(1 if any(a <= ord(c) <= b for a, b in _TEK) else 2 for c in metin)


def kirp(metin: str, limit: int = LIMIT) -> str:
    if uzunluk(metin) <= limit:
        return metin
    while uzunluk(metin + "…") > limit:
        metin = metin[:-1]
    return metin.rstrip() + "…"


def yuzde(p: float) -> str:
    return f"{100 * p:.0f}%"


def rekor(o: dict) -> str:
    if not o["spel"]:
        return "📈 Record: starts today"
    metin = f'📈 Record: {o["vunna"]}–{o["forlorade"]} ({o["traff"]:.0f}%)'
    if o["kombi"]:
        metin += f' · Combos {o["kombi_tuttu"]}/{o["kombi"]}'
    return metin


def _tarih(gun: dict) -> str:
    return datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")


def gun_tweeti(gun: dict, ozet: dict) -> str:
    def yaz(seviye: int, takim_max: int = 40) -> str:
        satirlar = [f"⚽ TODAY'S PICKS | {_tarih(gun)}", ""]
        for i, s in enumerate(gun["secimler"], 1):
            saat = s["saat"] if seviye < 2 else s["saat"].split()[0]
            sans = f'{yuzde(s["adil_olasilik"])} chance' if seviye < 3 else yuzde(s["adil_olasilik"])
            satirlar.append(f'{i}) {s["ev"][:takim_max]} v {s["dep"][:takim_max]} · {saat}')
            satirlar.append(f'   {s["kisa"]} @{s["oran"]:.2f} · {sans}')
        satirlar.append("")
        if len(gun["secimler"]) >= 2:
            satirlar.append(f'🎯 Combo @{kombi_oran(gun):.2f} · all win: {yuzde(kombi_olasilik(gun))}')
        satirlar.append(rekor(ozet))
        if seviye < 1:
            satirlar.append("Why these picks? 👇")
        satirlar.append(ANSVAR)
        return "\n".join(satirlar)

    # Önce süsler atılır; sorumlu oyun satırı asla kesilmez.
    for seviye in range(4):
        metin = yaz(seviye)
        if uzunluk(metin) <= LIMIT:
            return metin
    for takim_max in range(24, 3, -2):
        metin = yaz(3, takim_max)
        if uzunluk(metin) <= LIMIT:
            return metin
    return kirp(metin)


def analiz_tweetleri(gun: dict) -> list[str]:
    return [
        kirp(f'{i}) {s["ev"]} v {s["dep"]}\n'
             f'Pick: {s["etiket"]} @{s["oran"]:.2f} ({yuzde(s["adil_olasilik"])} chance)\n'
             f'Most likely score: {s["olasi_skor"].replace("-", "–")}\n\n{s["yorum"]}')
        for i, s in enumerate(gun["secimler"], 1)
    ]


def sonuc_tweeti(gun: dict, ozet: dict) -> str:
    ikon = {"kazandi": "✅", "kaybetti": "❌", "iptal": "➖"}
    biten = [s for s in gun["secimler"] if s["durum"] in ("kazandi", "kaybetti")]
    vunna = sum(s["durum"] == "kazandi" for s in biten)
    satirlar = [f"📊 Results {_tarih(gun)}: {vunna}/{len(biten)} won", ""]
    for s in gun["secimler"]:
        skor = (s.get("skor") or "postponed").replace("-", "–")
        satirlar.append(f'{ikon[s["durum"]]} {s["ev"]} {skor} {s["dep"]} · {s["kisa"]}')
    kombi = kombi_durumu(gun)
    if kombi:
        satirlar.append(f'🎯 Combo @{kombi_oran(gun):.2f}: {"✅ won" if kombi == "tuttu" else "❌ lost"}')
    satirlar += ["", rekor(ozet)]
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
