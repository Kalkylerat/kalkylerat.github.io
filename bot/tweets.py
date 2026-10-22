"""Tweet metni yardımcıları (uzunluk, etiket, sorumluluk satırı) ve X API v2 istemcisi."""

import html
import re
import time
from datetime import datetime, timedelta, timezone

from requests_oauthlib import OAuth1Session


LIMIT = 280
# twitter-text ağırlıklandırması: bu aralıklar 1, diğer karakterler 2 sayılır.
_TEK = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))
ANSVAR = "18+ | Play responsibly"
# Yalnızca büyük turnuvalar için, gerçek etiketler (X rehberi: en fazla 1-2). Ülkeye göre doğrulanır:
# "Premier League" Kenya'da da var, "Serie A" Brezilya'da da.
_ULUSLARARASI = (("champions league women", "#UWCL"), ("uefa nations league", "#NationsLeague"),
                 ("uefa champions league", "#UCL"), ("uefa europa league", "#UEL"), ("conference league", "#UECL"))
_ULUSAL = {("premier league", "england"): "#PremierLeague", ("la liga", "spain"): "#LaLiga",
           ("serie a", "italy"): "#SerieA", ("bundesliga", "germany"): "#Bundesliga", ("ligue 1", "france"): "#Ligue1",
           ("eredivisie", "netherlands"): "#Eredivisie", ("süper lig", "turkey"): "#SuperLig",
           ("allsvenskan", "sweden"): "#Allsvenskan"}
# Liste (tablo) postunda kullanılan genel etiketler: analiz ve tahmin hesaplarının yaygın kullandığı, bahis içermeyen
# etiketler. Bahis etiketleri (#BettingTips vb.) bilerek yok: konsept analiz, bahis tavsiyesi değil.
GENEL_ETIKETLER = ("#Football", "#FootballPredictions")
IZINLI_ETIKETLER = {e for _, e in _ULUSLARARASI} | set(_ULUSAL.values())  # genel etiketler yalnızca liste postunda
LISTE_ETIKET_SINIRI = 2  # X kuralı: trend/alakasız etiket spam sayılır; otomatik postta az ve ilgili etiket

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
# Milli takımların taraftarların X'te zaten yoğun kullandığı etiketleri (uydurma kod değil). Sıra = öncelik:
# maçta iki takımın da etiketi varsa listede önce gelen kullanılır. Emin olunmayan takıma etiket konmaz.
MILLI_ETIKETLER = {
    "türkiye": "#BizimÇocuklar", "turkey": "#BizimÇocuklar", "england": "#ThreeLions", "france": "#LesBleus",
    "italy": "#Azzurri", "germany": "#DFBTeam", "portugal": "#VesteABandeira", "belgium": "#REDDEVILS",
    "croatia": "#Vatreni", "wales": "#TogetherStronger",
}
_MILLI_SIRA = list(dict.fromkeys(MILLI_ETIKETLER.values()))
# Büyük kulüplerin X'te yaygın etiketleri (yalnızca bunlar; bilinmeyen kulübe etiket uydurulmaz).
KULUP_ETIKETLERI = {
    "arsenal": "#Arsenal", "chelsea": "#Chelsea", "liverpool": "#Liverpool", "manchester united": "#MUFC",
    "manchester city": "#ManCity", "tottenham": "#COYS", "newcastle": "#NUFC", "aston villa": "#AVFC",
    "real madrid": "#RealMadrid", "barcelona": "#Barca", "atletico madrid": "#Atleti", "bayern munich": "#FCBayern",
    "bayern münchen": "#FCBayern", "borussia dortmund": "#BVB", "paris saint germain": "#PSG", "juventus": "#Juventus",
    "inter": "#Inter", "ac milan": "#ACMilan", "napoli": "#Napoli", "galatasaray": "#Galatasaray",
    "fenerbahce": "#Fenerbahce", "fenerbahçe": "#Fenerbahce", "besiktas": "#Besiktas", "beşiktaş": "#Besiktas",
    "ajax": "#Ajax", "benfica": "#Benfica", "porto": "#FCPorto", "celtic": "#CelticFC",
}


def mac_etiketi(ev: str, dep: str) -> str | None:
    """Milli maçta taraftar etiketi (#BizimÇocuklar); yoksa etiket yok (kimsenin aramadığı kod uydurulmaz). Kulüp maçında
    bilinen büyük kulübün etiketi (önce ev sahibi); yoksa None."""
    a, b = FIFA_KODLARI.get(ev.lower().strip()), FIFA_KODLARI.get(dep.lower().strip())
    if a and b:
        taraftar = [MILLI_ETIKETLER[t] for t in (ev.lower().strip(), dep.lower().strip()) if t in MILLI_ETIKETLER]
        return min(taraftar, key=_MILLI_SIRA.index) if taraftar else None  # uydurma kod etiketi (#KAZMDA) yok
    return KULUP_ETIKETLERI.get(ev.lower().strip()) or KULUP_ETIKETLERI.get(dep.lower().strip())


def izinli_etiket(e: str) -> bool:
    return e in IZINLI_ETIKETLER or e in KULUP_ETIKETLERI.values() or e in MILLI_ETIKETLER.values()


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


def etiket_satiri(ligler: list[tuple[str, str]], maclar: list[tuple[str, str]] = (), en_fazla: int = 1) -> str:
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


def liste_etiketleri(ligler: list[tuple[str, str]], maclar: list[tuple[str, str]]) -> list[str]:
    """Liste postu için en fazla iki ilgili etiket: turnuva, sonra adı geçen maçın taraftar/kulüp etiketi. Genel
    etiketler (#Football gibi) otomatik postlara konmaz: X otomasyon kuralları trend ve alakasız etiketi spam sayar."""
    takim = list(dict.fromkeys(e for e in (mac_etiketi(ev, dep) for ev, dep in maclar) if e))
    turnuva = list(dict.fromkeys(e for e in (hashtag(l, u) for l, u in ligler) if e))
    return (turnuva[:1] + takim + turnuva[1:])[:LISTE_ETIKET_SINIRI]


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


class KopyaPost(RuntimeError):
    """X aynı metni reddetti (403 "duplicate content") ve post son bir günde bu hesapta yok: yeniden denemek boşuna."""


def _ayni_metin(a: str, b: str) -> bool:
    """X'in döndürdüğü metin (HTML kaçışlı, görsel/alıntı bağlantısı eklenmiş) gönderdiğimizle aynı mı?"""
    def sade(m: str) -> str:
        return " ".join(re.sub(r"https?://\S+", "", html.unescape(m)).split())
    return sade(a) == sade(b)


class XClient:
    URL = "https://api.x.com/2/tweets"
    # X bazen postu atıp 5xx döndürüyor (15 Ekim 19:05: Mr. Likely bilgi postu 503 aldı ama paylaşılmıştı; sonraki her
    # nabız 403 "duplicate content" aldı, 2 saatte 18 alarm). Hata kodunda önce hesabın son postlarına bakılır.
    BEKLE_SN = (5, 15)

    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
        self.session = OAuth1Session(api_key, api_secret, access_token, access_secret)

    def medya_yukle(self, png: bytes) -> str:
        """Görseli yükler (tek başına paylaşılmaz); tweete eklemek için medya kimliği döner."""
        r = self.session.post("https://api.x.com/2/media/upload",
                              files={"media": ("gorsel.png", png, "image/png")},
                              data={"media_category": "tweet_image", "media_type": "image/png"}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"X medya yükleme hatası {r.status_code}: {r.text[:300]}")
        veri = r.json().get("data") or r.json()
        return str(veri.get("id") or veri["media_id_string"])

    def gonder(self, metin: str, yanit: str | None = None, medya: list[str] | None = None,
               alinti: str | None = None, anket: dict | None = None, topluluk: str | None = None) -> str:
        body: dict = {"text": metin}
        if topluluk:  # X Topluluğu'na post; takipçilere de gösterilir
            body["community_id"] = str(topluluk)
            body["share_with_followers"] = True
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
            kopya = r.status_code == 403 and "duplicate content" in r.text
            if kopya or r.status_code >= 500:  # post belki X'te: yalnızca hata anında okunur (~10 post, nadir)
                onceki = self.zaten_atilmis(metin, timedelta(days=1) if kopya else timedelta(minutes=10),
                                            bekle=() if kopya else self.BEKLE_SN)
                if onceki:
                    return onceki
            raise (KopyaPost if kopya else RuntimeError)(f"X API hatası {r.status_code}: {r.text}")
        return r.json()["data"]["id"]

    def zaten_atilmis(self, metin: str, sure: timedelta, bekle: tuple = ()) -> str | None:
        """Bu metin son `sure` içinde hesapta paylaşılmışsa kimliği. 5xx sonrası X postu birkaç saniye geç
        gösterebilir: `bekle` saniyelerinde tekrar bakılır. Okunamazsa None (asıl hata bildirilir)."""
        simdi = datetime.now(timezone.utc)
        for sn in (0, *bekle):
            time.sleep(sn)
            try:
                if not getattr(self, "_kimlik", None):
                    self._kimlik = self.session.get("https://api.x.com/2/users/me", timeout=30).json()["data"]["id"]
                r = self.session.get(f"https://api.x.com/2/users/{self._kimlik}/tweets", timeout=30,
                                     params={"max_results": 10, "tweet.fields": "created_at"})
                postlar = r.json().get("data", []) if r.status_code < 400 else []
            except Exception:
                postlar = []
            for t in postlar:
                zaman = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
                if simdi - zaman <= sure and _ayni_metin(t.get("text", ""), metin):
                    return t["id"]
        return None

    def tum_tweet_idleri(self, adet: int = 100) -> list[str]:
        """Hesabın en yeni postları (yanıtlar dahil), en fazla `adet` kadar kimlik."""
        me = self.session.get("https://api.x.com/2/users/me", timeout=30).json()["data"]["id"]
        r = self.session.get(f"https://api.x.com/2/users/{me}/tweets",
                             params={"max_results": max(5, min(100, adet))}, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text[:300]}")
        return [t["id"] for t in r.json().get("data", [])][:adet]

    def metrikler(self, adet: int = 100) -> list[dict]:
        """Hesabın son tweetleri ve etkileşim rakamları (görüntülenme, yanıt, beğeni, RT)."""
        me = self.session.get("https://api.x.com/2/users/me", timeout=30).json()["data"]["id"]
        r = self.session.get(f"https://api.x.com/2/users/{me}/tweets", timeout=30,
                             params={"max_results": adet, "tweet.fields": "public_metrics,created_at"})
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text[:300]}")
        return r.json().get("data", [])

    def metrikler_idle(self, idler: list[str]) -> list[dict]:
        """Yalnızca verilen postların rakamları (okuma post başına ücretli: Tiny Fixes ölçümü hesabın tüm geçmişini okumaz)."""
        if not idler:
            return []
        r = self.session.get("https://api.x.com/2/tweets", timeout=30,
                             params={"ids": ",".join(idler[:100]), "tweet.fields": "public_metrics,created_at"})
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text[:300]}")
        return r.json().get("data", [])

    def ben(self) -> tuple[str, str]:
        """Hesabın kimliği ve kullanıcı adı (yorum kiti bir kez sorar, kaydeder)."""
        r = self.session.get("https://api.x.com/2/users/me", timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text[:300]}")
        d = r.json()["data"]
        return d["id"], d["username"]

    def ara(self, sorgu: str, baslangic: str, adet: int = 25) -> list[dict]:
        """Son 7 günün postlarında arama (yalnızca okuma; yorum fırsatları, SÖZLEŞME D3). Her biri: id, metin,
        kullanici, zaman, metrik (beğeni/yanıt/RT)."""
        r = self.session.get("https://api.x.com/2/tweets/search/recent", timeout=30, params={
            "query": sorgu, "max_results": max(10, min(100, adet)), "start_time": baslangic.replace("+00:00", "Z"),
            "tweet.fields": "author_id,created_at,public_metrics", "expansions": "author_id", "user.fields": "username"})
        if r.status_code >= 400:
            raise RuntimeError(f"X API arama hatası {r.status_code}: {r.text[:300]}")
        j = r.json()
        kullanicilar = {u["id"]: u["username"] for u in (j.get("includes") or {}).get("users", [])}
        return [{"id": t["id"], "metin": t.get("text", ""), "kullanici": kullanicilar.get(t.get("author_id")),
                 "zaman": t.get("created_at") or baslangic, "metrik": t.get("public_metrics") or {}}
                for t in j.get("data", [])]

    def bahsedenler(self, me: str, since_id: str | None = None, baslangic: str | None = None) -> list[dict]:
        """Hesaba gelen yanıtlar ve etiketlemeler (yalnızca okuma; yorum kiti, SÖZLEŞME D3). Her biri: id, metin,
        yazar, kullanici, bizim (yanıtlanan kendi postumuzun metni, varsa)."""
        params = {"max_results": 20, "tweet.fields": "author_id,created_at,referenced_tweets",
                  "expansions": "author_id,referenced_tweets.id", "user.fields": "username"}  # bizim postun da üstü
        if since_id:
            params["since_id"] = since_id
        elif baslangic:
            params["start_time"] = baslangic.replace("+00:00", "Z")
        r = self.session.get(f"https://api.x.com/2/users/{me}/mentions", params=params, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text[:300]}")
        j = r.json()
        kullanicilar = {u["id"]: u["username"] for u in (j.get("includes") or {}).get("users", [])}
        postlar = {t["id"]: t for t in (j.get("includes") or {}).get("tweets", [])}
        sonuc = []
        for t in j.get("data", []):
            hedef = next((ref["id"] for ref in t.get("referenced_tweets") or [] if ref.get("type") == "replied_to"), None)
            bizim = postlar.get(hedef) if hedef else None
            bizimki = bool(bizim) and bizim.get("author_id", me) == me
            ust = next((ref["id"] for ref in (bizim or {}).get("referenced_tweets") or []
                        if ref.get("type") == "replied_to"), None) if bizimki else None
            sonuc.append({"id": t["id"], "metin": t.get("text", ""), "yazar": t.get("author_id"),
                          "kullanici": kullanicilar.get(t.get("author_id")),
                          "bizim": bizim["text"] if bizimki else None, "ust_id": ust})
        return sonuc

    def postlar(self, idler: list[str]) -> dict[str, dict]:
        """Postların metni ve yazarı, tek istekte (en fazla 100; okuma dönen post başına ücretli). {id: {metin, kullanici}}."""
        if not idler:
            return {}
        r = self.session.get("https://api.x.com/2/tweets", timeout=30, params={
            "ids": ",".join(list(dict.fromkeys(idler))[:100]), "tweet.fields": "author_id,created_at",
            "expansions": "author_id", "user.fields": "username"})
        if r.status_code >= 400:
            raise RuntimeError(f"X API okuma hatası {r.status_code}: {r.text[:300]}")
        j = r.json()
        kullanicilar = {u["id"]: u["username"] for u in (j.get("includes") or {}).get("users", [])}
        return {t["id"]: {"metin": t.get("text", ""), "kullanici": kullanicilar.get(t.get("author_id"))}
                for t in j.get("data", [])}

    def sil(self, tweet_id: str) -> None:
        r = self.session.delete(f"{self.URL}/{tweet_id}", timeout=30)
        if r.status_code >= 400 and r.status_code != 404:
            raise RuntimeError(f"X API silme hatası {r.status_code}: {r.text}")


class KonsolClient:
    """Paylaşmadan ekrana yazar (testler ve taslak önizleme)."""

    def __init__(self, gorsel_klasoru=None):
        self.sayac = 0
        self.gorsel_klasoru = gorsel_klasoru

    def medya_yukle(self, png: bytes) -> str:
        self.gorsel_sayac = getattr(self, "gorsel_sayac", 0) + 1
        if self.gorsel_klasoru:
            (self.gorsel_klasoru / f"gorsel{self.gorsel_sayac}.png").write_bytes(png)
        return f"gorsel-{len(png) // 1024}KB"

    def gonder(self, metin: str, yanit: str | None = None, medya: list[str] | None = None,
               alinti: str | None = None, anket: dict | None = None, topluluk: str | None = None) -> str:
        self.sayac += 1
        ek = (f" + {', '.join(medya)}" if medya else "") + (f" (alıntı: {alinti})" if alinti else "")
        ek += f" (topluluk: {topluluk})" if topluluk else ""
        ek += f" (anket: {' / '.join(anket['options'])}, {anket['duration_minutes']} dk)" if anket else ""
        print(f"\n----- TWEET #{self.sayac}{' (yanıt)' if yanit else ''}{ek} [{uzunluk(metin)}/280] -----\n{metin}")
        return f"demo-{self.sayac}"

    def sil(self, tweet_id: str) -> None:
        print(f"----- SİLİNDİ: {tweet_id} -----")

    def tum_tweet_idleri(self, adet: int = 100) -> list[str]:
        return []

    def metrikler(self, adet: int = 100) -> list[dict]:
        return []
