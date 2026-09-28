"""Sade İngilizce tweet metinleri ve X API v2 istemcisi."""

from datetime import datetime

from requests_oauthlib import OAuth1Session

from .kayit import gun_kar, kombi_durumu, kombi_olasilik, kombi_oran

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


def para(x: float, birim: str) -> str:
    return f"{'-' if x < 0 else ''}{birim}{abs(x):,.0f}"


def oran_metni(s: dict) -> str:
    """Bet builder oranı bahisçiden değil modelden tahmin edildiği için ≈ ile gösterilir."""
    return f'{"≈" if s.get("bet_builder") else ""}{s["oran"]:.2f}'


def rekor(o: dict) -> str:
    if not o["spel"]:
        return "📈 Record: starts today"
    metin = f'📈 Record: {o["vunna"]}–{o["forlorade"]} ({o["traff"]:.0f}%)'
    if o["kombi"]:
        metin += f' · Combos {o["kombi_tuttu"]}/{o["kombi"]}'
    return metin


def _tarih(gun: dict) -> str:
    return datetime.fromisoformat(gun["tarih"]).strftime("%-d %b")


def _kombi_satiri(gun: dict) -> str:
    """Kombine her zaman günün bütün oyunlarıdır; X'te "@" etiket sanıldığı için oranlar "odds" ile yazılır."""
    return f'🎯 All {len(gun["secimler"])}: odds {kombi_oran(gun):.2f} · {yuzde(kombi_olasilik(gun))} chance'


def _secim_satiri(i: int, s: dict, takim_max: int) -> str:
    """Takım adı etikette geçiyorsa ("Arsenal win") maç adı yazılmaz; geçmiyorsa ("Over 2.5 goals") başa eklenir."""
    kisa = s["kisa"]
    if s.get("bet_builder") or (s["ev"] not in kisa and s["dep"] not in kisa):
        kisa = f'{s["ev"][:takim_max]} v {s["dep"][:takim_max]}: {kisa}'
    ek = (" · bet builder" if s.get("bet_builder") else "") + (" · value" if s["tur"] == "deger" else "")
    return f'{i}) {kisa} ({oran_metni(s)}) · {yuzde(s["adil_olasilik"])}{ek}'


def _kasa_satiri(gun: dict, o: dict) -> str:
    kasa = f'💰 Bank {para(o["kasa"], gun["para"])}'
    if not o["spel"]:
        return f'{kasa} · {gun["yuzde"]:g}%/bet'
    metin = f'{kasa} · 📈 {o["vunna"]}–{o["forlorade"]} ({o["traff"]:.0f}%)'
    return metin + (f' · combos {o["kombi_tuttu"]}/{o["kombi"]}' if o["kombi"] else "")


def gun_tweeti(gun: dict, ozet: dict) -> str:
    def yaz(seviye: int, takim_max: int = 40) -> str:
        satirlar = [f"⚽ TODAY'S PICKS | {_tarih(gun)}", ""]
        satirlar += [_secim_satiri(i, s, takim_max) for i, s in enumerate(gun["secimler"], 1)]
        if seviye < 1:
            satirlar.append("")
        if gun.get("kombi"):
            satirlar.append(_kombi_satiri(gun))
        satirlar.append(_kasa_satiri(gun, ozet))
        if seviye < 1:
            satirlar.append("Why? Thread 👇")
        satirlar.append(ANSVAR)
        return "\n".join(satirlar)

    # Önce süsler atılır, sonra takım adları kısalır; kasa ve sorumlu oyun satırları asla atılmaz.
    for seviye in range(2):
        metin = yaz(seviye)
        if uzunluk(metin) <= LIMIT:
            return metin
    for takim_max in range(20, 5, -2):
        metin = yaz(1, takim_max)
        if uzunluk(metin) <= LIMIT:
            return metin
    govde = "\n".join(yaz(1, 6).split("\n")[:-1])
    return f"{kirp(govde, LIMIT - uzunluk(ANSVAR) - 1)}\n{ANSVAR}"


def analiz_tweetleri(gun: dict) -> list[str]:
    kisa_tur = {"guvenli": "safe pick", "deger": "value pick"}

    def tur(s: dict) -> str:
        return ("bet builder, " if s.get("bet_builder") else "") + kisa_tur[s["tur"]]
    return [
        kirp(f'{i}) {s["ev"]} v {s["dep"]} · {s["saat"]}\n'
             f'{s["etiket"]} · odds {oran_metni(s)}\n'
             f'{yuzde(s["adil_olasilik"])} chance · {tur(s)} · stake {para(s["stake"], gun["para"])}\n'
             f'Likely score: {s["olasi_skor"].replace("-", "–")}\n\n{s["yorum"]}')
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
    kombi = kombi_durumu(gun) if gun.get("kombi") else None
    if kombi in ("tuttu", "yatti"):
        satirlar.append(f'🎯 All together (odds {kombi_oran(gun):.2f}): {"✅ won" if kombi == "tuttu" else "❌ lost"}')
    kar = gun_kar(gun)
    satirlar += ["", f'💰 Day {"+" if kar >= 0 else ""}{para(kar, gun["para"])} · Bank {para(ozet["kasa"], gun["para"])} '
                     f'({ozet["kasa_degisim"]:+.1f}%)', rekor(ozet)]
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
