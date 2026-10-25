"""Yorum fırsatları (büyüme ajanı, SÖZLEŞME D3): büyük futbol hesaplarının yeni ve etkileşim alan postlarını bulur,
her birine bizim kartımızdan rakamla 2 cevap taslağı yazar ve sahibine bağlantılarıyla gönderir (günlük GitHub
issue'su, telefona bildirim). Sahibi bağlantıyı açar, taslağı yapıştırıp elle atar.

Bot hiçbir zaman kendisi cevap atmaz, beğenmez, takip etmez (X otomasyon kuralı). Okuma ücretlidir (dönen post
başına ~$0.005): günde birkaç arama, her biri en fazla ARAMA_ADET post. Günde kaç fırsat geleceği ayarlar.toml →
[buyume] gunluk_yorum."""

import json
import math
import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import config, kopya
from .yorum import INSAN_SESI, LIKELY_INSAN

ETIKET = "yorum-firsatlari"
DOSYA = config.ROOT / "data" / "firsatlar.json"
ARAMA_ADET = 40  # bir aramada en fazla bu kadar post okunur (~$0.20); aynı saatteki arama iki hesaba yeter.
# Yalnızca kartımız olan maçların postları seçildiği için 25 yetmiyordu (14 Ekim).
TAZE_SAAT = 3  # yalnızca son bu kadar saatte atılmış postlar (eski posta yanıt görünmez)
KULUP_ADET = 25  # bugünkü büyük maçların kulüp hesaplarından ikinci arama (25 Ekim 2026: daha çok, daha isabetli fırsat)

# Büyük kulüplerin resmi (İngilizce) X hesapları: maç günü postları ("Matchday", kadro, ön izleme) en isabetli
# fırsatlar; analizdeki takım adı → hesap. Yanlış ya da eksik hesap yalnızca boş sonuç verir (ücret post başına).
KULUP_HESAPLARI = {
    "arsenal": "Arsenal", "chelsea": "ChelseaFC", "liverpool": "LFC", "manchester united": "ManUtd",
    "manchester city": "ManCity", "tottenham": "SpursOfficial", "newcastle": "NUFC", "aston villa": "AVFCOfficial",
    "everton": "Everton", "west ham": "WestHam", "barcelona": "FCBarcelona", "real madrid": "realmadriden",
    "atletico madrid": "atletienglish", "sevilla": "SevillaFC_ENG", "bayern münchen": "FCBayernEN",
    "borussia dortmund": "BlackYellow", "bayer leverkusen": "bayer04_en", "juventus": "juventusfcen",
    "inter": "Inter_en", "ac milan": "acmilan", "napoli": "en_sscnapoli", "as roma": "ASRomaEN",
    "paris saint germain": "PSG_English", "marseille": "OM_English", "galatasaray": "GalatasaraySK",
    "fenerbahce": "Fenerbahce", "besiktas": "Besiktas", "celtic": "CelticFC", "rangers": "RangersFC",
    "ajax": "AFCAjax", "benfica": "SLBenfica", "porto": "FCPorto", "sporting cp": "SportingCP_en"}


def kulup_hesaplari(maclar: list[dict]) -> list[str]:
    """Bugünkü (başlamamış) maçlarda oynayan büyük kulüplerin hesapları, tekrarsız."""
    return list(dict.fromkeys(KULUP_HESAPLARI[t.lower().strip()] for a in maclar for t in (a["ev"], a["dep"])
                              if t.lower().strip() in KULUP_HESAPLARI))


@dataclass
class BuyumeAyar:
    aktif: bool = True
    gunluk_yorum: int = 20
    saatler: list = field(default_factory=lambda: [10, 12, 14, 16, 18, 20])  # UTC, aramaların yapıldığı saatler
    likely_gunluk_yorum: int = 15  # Mr. Likely hesabı için (0 = kapalı)
    likely_saatler: list = field(default_factory=lambda: [10, 12, 14, 16, 18, 20])  # aynı saatler: tek arama iki hesaba
    hesaplar: list = field(default_factory=lambda: [
        "OptaJoe", "OptaAnalyst", "Squawka", "ESPNFC", "brfootball", "FootballTweet", "433",
        "goal", "SkySportsPL", "SkySportsNews", "BBCSport", "TheAthleticFC", "ChampionsLeague", "premierleague",
        "LaLigaEN", "SerieA_EN", "Bundesliga_EN", "Ligue1_ENG", "EuropaLeague", "WhoScored", "StatsZone"])


def ayar_yukle(path=config.ROOT / "ayarlar.toml") -> BuyumeAyar:
    with open(path, "rb") as f:
        t = tomllib.load(f).get("buyume", {})
    alanlar = BuyumeAyar.__dataclass_fields__
    return BuyumeAyar(**{k: v for k, v in t.items() if k in alanlar})


def yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def kaydet(veri: dict) -> None:
    DOSYA.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def sorgu(hesaplar: list[str]) -> str:
    """X arama sorgusu: listedeki hesapların kendi postları (yanıt ve RT değil), İngilizce. X sınırı 512 karakter."""
    kuyruk = " -is:retweet -is:reply lang:en"
    secili = []
    for h in hesaplar:
        aday = "(" + " OR ".join(f"from:{x}" for x in secili + [h]) + ")" + kuyruk
        if len(aday) > 500:
            break
        secili.append(h)
    return "(" + " OR ".join(f"from:{x}" for x in secili) + ")" + kuyruk


# Postlarda sık geçen kısa adlar (kayıttaki resmi ad → postta yazılış)
TAKMA_ADLAR = {"paris saint germain": ["psg"], "manchester united": ["man united", "man utd"],
               "manchester city": ["man city"], "tottenham": ["spurs"], "bayern münchen": ["bayern", "bayern munich"],
               "borussia dortmund": ["dortmund", "bvb"], "atletico madrid": ["atletico", "atleti"],
               "inter": ["inter milan"], "ac milan": ["milan"], "wolves": ["wolverhampton"],
               "lask linz": ["lask"], "bodo/glimt": ["bodø/glimt", "bodo glimt", "bodø glimt"]}


# Tek takım adı geçen postun bugünkü maçtan söz ettiğini gösteren sözcükler
MAC_DILI = re.compile(r"\b(tonight|today|v|vs|versus|against|clash|fixture|kick-?off|line-?ups?|starting xi|xi|"
                      r"preview|team news|matchday|travel to|host|face)\b", re.IGNORECASE)


def _sade(ad: str) -> str:
    """Harf ve rakamlar, aksansız, küçük harf ("Bayern München" → "bayernmunchen")."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", ad.lower()).encode("ascii", "ignore").decode())


# Kulüp hesap adlarındaki ekler (@SunderlandAFC, @AS_Monaco_EN, @ChelseaFC, @FCBayernEN)
HESAP_ON = ("", "fc", "afc", "as", "ac", "ss", "ssc", "sc", "cf")
HESAP_SON = ("", "fc", "afc", "cf", "en", "eng", "official", "hq")


def _hesap_adlari(h: str) -> set[str]:
    """@hesabın ekleri atılmış olası kulüp adları."""
    return {h[len(o):len(h) - len(s)] for o in HESAP_ON for s in HESAP_SON
            if h.startswith(o) and h.endswith(s) and len(h) - len(o) - len(s) >= 3}


def _konum(takim: str, metin: str) -> int | None:
    """Takımın postta ilk geçtiği yer: resmi ad ya da bilinen kısa adı (tam kelime) ya da kulübün @hesabı
    (15 Ekim: "@SunderlandAFC" etiketli post Sunderland maçına eşleşmiyordu); geçmiyorsa None."""
    adlar = [takim.lower(), *TAKMA_ADLAR.get(takim.lower(), [])]
    yerler = [m.start() for ad in adlar for m in [re.search(rf"(?<!\w){re.escape(ad)}(?!\w)", metin.lower())] if m]
    anahtarlar = {_sade(ad) for ad in adlar} - {""}
    for m in re.finditer(r"@(\w+)", metin):
        h = _sade(m.group(1))
        if _hesap_adlari(h) & anahtarlar:
            yerler.append(m.start())
    return min(yerler) if yerler else None


def eslesen_mac(metin: str, maclar: list[dict]) -> dict | None:
    """Postun konusu olan bugünkü maç: önce iki takımı da geçen, yoksa postta EN ÖNCE adı geçen takımın maçı
    (14 Ekim: Man City–PSG postunda sonradan anılan "Real Madrid" yüzünden Roma–Real kartı eşleşmişti)."""
    adaylar = []
    mac_dili = MAC_DILI.search(metin) is not None
    for a in maclar:
        ev, dep = _konum(a["ev"], metin), _konum(a["dep"], metin)
        if ev is None and dep is None:
            continue
        if (ev is None or dep is None) and not mac_dili:
            continue  # tek takım adı ama maçtan söz yok (ör. Ballon d'Or, transfer postunda "Real Madrid", 14 Ekim)
        adaylar.append(((ev is None) + (dep is None), min(k for k in (ev, dep) if k is not None), a))
    return min(adaylar, key=lambda x: x[:2])[2] if adaylar else None


def puan(post: dict, simdi: datetime) -> float:
    """Etkileşim hızı: yanıtlar en ağır (algoritma), saat başına; çok eski post düşer."""
    m = post.get("metrik") or {}
    saat = max((simdi - datetime.fromisoformat(post["zaman"].replace("Z", "+00:00"))).total_seconds() / 3600, 0.25)
    return (m.get("like_count", 0) + 3 * m.get("reply_count", 0) + 2 * m.get("retweet_count", 0)) / saat


def _pct(p: float) -> str:
    return f"{100 * p:.0f}%"


def mac_olgulari(a: dict) -> dict:
    p = a["p"]
    olg = {"match": f'{a["ev"]} v {a["dep"]}',
           "our_chances": f'{a["ev"]} {_pct(p["MS1"])} · Draw {_pct(p["MSX"])} · {a["dep"]} {_pct(p["MS2"])}',
           "over_2_5_goals": _pct(p["UST25"]), "both_teams_score": _pct(p["KGVAR"]),
           "most_likely_score": f'{a["skorlar"][0][0]} ({_pct(a["skorlar"][0][1])})'}
    return olg


KUTU_OMUR_DK = 120  # fırsat gelen kutusunda bu kadar kalır (büyük hesaba cevap ilk 1–2 saatte işe yarar)

KURALLAR = """Hard rules:
- Max 200 characters. No links, no "@", no hashtags, at most one emoji. Plain, natural English.
- Add something to THEIR post: react to what it says, then (if match facts are given AND they are about the same
  match their post is about) one number from the facts. If the facts are about a different match, use no numbers
  and never bring that other match up.
  Never invent stats, news or line-ups; use only numbers from the facts or the post itself.
- Not promotional: never "check our page", "follow us", "see our card/coupon", never mention the account.
- Kind and respectful to everyone: no sarcasm, no digs, no negative judgments about any club, player, fan, manager
  or the account (never "strange look", "embarrassing", "struggling"). On controversies (discipline, fines,
  contracts, referees, fan trouble, politics) take no side; if the post is mainly a controversy, set "uygun" false.
- Say only what is in their post or the facts; if unsure, leave it out. Open and friendly, like talking to a mate.
- Never name a player, manager or club that isn't in their post or the facts: squads change and your knowledge may
  be out of date (a wrong name makes the reply look fake).
- Chances, not picks: never pick, tip, lock, guaranteed, sure, banker. No bookmaker names. Never argue or mock.
- One draft can end with a short, specific question (conversations get seen); the other doesn't have to.
Set "uygun" false (and drafts empty) if the post is not about football matches or players, is sad news (injury,
death, tragedy), politics, an ad or a giveaway: a numbers reply there would look tone-deaf."""

SISTEMLER = {
    "kalkylerat": f"""You draft replies that the owner of @kalkylerat (a football numbers account: chances for every
market, never picks) will paste BY HAND under a big football account's post on X. You never post anything.
Write 2 different reply drafts to the post below. "We" is the account. Our match card (an image with all our chances
for this match) is attached under every reply automatically, so the text reacts to their post like a fan and may
use at most one number; never mention the card, a link or our account.

{KURALLAR}
- Voice for @kalkylerat (X expert advice, 25 Oct 2026): the friendly numbers mate. Lead with the most surprising number
  in plain words ("they still fail to win 57% of the time", "about a 1-in-7 upset"), add a short human reaction to
  their post, and end one draft with a specific question about this match. Warm and curious, never teasing.

{INSAN_SESI}""",
    "likely": f"""You draft replies that the owner of Mr. Likely (a football coupon account with a dry, self-aware
voice: a numbers model picks dull coupons on fixed rules, he presents them, losers included) will paste BY HAND
under a big football account's post on X. You never post anything. Write 2 different reply drafts to the post below.

{KURALLAR}
- Mr. Likely speaks as "I". Chances the way he says them: "I make it about 60%", "probably", "loses three times in ten".
- Personality (owner's wish, 25 Oct 2026): a little cocky but charming and funny. He backs his numbers with a wink
  ("my model isn't nervous, I am"), playfully teases the hype, the bold XI or the fans' confidence against his number,
  and opens with a line that makes people want to reply. Cheeky, never mean: no insults, no mocking a person, club,
  player or fan, nothing that could sting; if a tease could hurt anyone, tease himself instead. No exclamation marks.
- Never tell anyone to bet, stake, tail or copy a coupon; never mention odds as advice. He is a fan who likes numbers.
- "in_my_coupon_today" in the facts means that match is a leg in today's coupon: he may say so once, plainly and
  with a little self-doubt ("it's one of my legs today, so naturally I'm nervous"). Never push the coupon.

{INSAN_SESI}
{LIKELY_INSAN}
More Mr. Likely examples. Good: "I make City about 45% tonight. That XI doesn't make me feel better or worse"
Good: "Dull answer from me: probably goals. 66% both score"  Bad: "Great stat! Check my coupon for tonight's best value 🔥"
""",
}
# Mr. Likely (15 Ekim 2026, sahibinin isteği, SÖZLEŞME D6): hakaretsiz sevimli takılma serbest; @kalkylerat'ta yok.
SISTEMLER["likely"] = SISTEMLER["likely"].replace(KURALLAR, KURALLAR.replace(
    """- Kind and respectful to everyone: no sarcasm, no digs, no negative judgments""",
    """- A small friendly tease is fine (see below), but no insults, no mocking, no negative judgments"""))
SISTEM = SISTEMLER["kalkylerat"]

SEMA = {"type": "object", "additionalProperties": False, "required": ["uygun", "taslaklar"],
        "properties": {"uygun": {"type": "boolean"}, "taslaklar": {"type": "array", "items": {"type": "string"}}}}
# Hesap başına: günlük issue etiketi ve ek seçenek adı
ETIKETLER = {"kalkylerat": ETIKET, "likely": "yorum-firsatlari-likely"}
ADLAR = {"kalkylerat": "@kalkylerat", "likely": "Mr. Likely"}


def taslaklar(post: dict, mac: dict | None, client, ayar, hesap: str = "kalkylerat", kupon_ayagi: str | None = None) -> list[str]:
    """Posta 2 cevap taslağı; uygun değilse ya da kurala uyan taslak yoksa boş liste (o post gönderilmez)."""
    from .direktor import _cagir
    from .yorum import uygun
    olg = mac_olgulari(mac) if mac else None
    if olg and kupon_ayagi:
        olg["in_my_coupon_today"] = kupon_ayagi
    icerik = json.dumps({"their_post": post["metin"], "account": post.get("kullanici"),
                         "match_facts": olg or "(no match of ours in this post: react without numbers)"},
                        ensure_ascii=False, indent=1)
    cevap = _cagir(client, [(ayar.direktor_model, "low"), (ayar.claude_model, "low")], SISTEMLER[hesap], icerik, SEMA, 2000)
    if not cevap.get("uygun"):
        return []
    kaynak = post["metin"] + "\n" + json.dumps(olg or {}, ensure_ascii=False)
    from .yorum import buyuk_harfle
    from .yorum import temizle
    return [buyuk_harfle(t) for t in cevap.get("taslaklar") or [] if uygun(temizle(t.strip()), kaynak) and "@" not in t
            and not re.search(r"\b(tail|stake|copy my|my coupon is|value bet)\b", t, re.IGNORECASE)][:2]


def kart_postu(gun: dict | None, mac: dict | None) -> str | None:
    """Bu maçın bizim paylaşılmış kart postunun adresi (cevaba eklenirse X onu kart olarak gösterir); yoksa None."""
    if not gun or not mac:
        return None
    for i, a in enumerate(gun.get("analizler") or []):
        e = (gun.get("etkilesim") or {}).get(f"analiz_{i}") or {}
        if a is mac or a.get("fixture_id") == mac.get("fixture_id"):
            return f"https://x.com/kalkylerat/status/{e['tweet_id']}" if e.get("durum") == "paylasildi" and e.get("tweet_id") else None
    return None


def kupon_postu(kuponlar: list[dict], mac: dict | None, kullanici: str | None) -> tuple[str, str] | None:
    """Mr. Likely: maç bugünkü paylaşılmış (ilk maçı başlamamış) bir kuponun ayağıysa (ayak etiketi, kupon postu adresi)."""
    if not mac:
        return None
    for k in kuponlar:
        for a in k.get("ayaklar") or []:
            if k.get("tweet_id") and k["tweet_id"] not in ("gecti", "tekrar") and \
                    (a.get("fixture_id") == mac.get("fixture_id") or (a.get("ev"), a.get("dep")) == (mac["ev"], mac["dep"])):
                yol = f"{kullanici}/status" if kullanici else "i/web/status"
                return a.get("etiket") or "one leg", f"https://x.com/{yol}/{k['tweet_id']}"
    return None


def bildirim(post: dict, mac: dict | None, taslak: list[str], sira: int, kart: str | None = None,
             ek_adi: str = "🖼️ Kartımızla (1. taslak + bu maçın kart postumuz):") -> str:
    from .yorum import taslak_satirlari
    m = post.get("metrik") or {}
    satirlar = [f"### {sira}. @{post.get('kullanici') or '?'} · 💬 {m.get('reply_count', 0)} · ❤️ {m.get('like_count', 0)}",
                f"> {post['metin'].strip()[:280]}".replace("\n", "\n> "), "",
                f"👀 [Postu gör](https://x.com/{post.get('kullanici') or 'i'}/status/{post['id']})"
                + (f" · maç: {mac['ev']} v {mac['dep']}" if mac else ""), ""]
    ekler = [(ek_adi, f"{taslak[0]}\n\n{kart}")] if kart and taslak else []
    satirlar += taslak_satirlari(taslak, ekler)
    return "\n".join(satirlar).rstrip()


def _hesap_durumu(veri: dict, hesap: str, tarih: str) -> dict:
    if "tarih" in veri:  # eski biçim (yalnızca @kalkylerat, 14 Ekim sabahı)
        eski = {k: veri.pop(k) for k in ("tarih", "gonderilen", "aramalar", "issue") if k in veri}
        veri["kalkylerat"] = eski
    h = veri.get(hesap) or {}
    if h.get("tarih") != tarih:
        h = {"tarih": tarih, "gonderilen": 0, "aramalar": []}
    veri[hesap] = h
    veri["gorulen"] = veri.get("gorulen", [])[-400:]
    return h


def kontrol(x, gh, ayar, gun: dict | None, simdi: datetime, client, yaz=print, hesap: str = "kalkylerat",
            kuponlar: list[dict] = (), kullanici: str | None = None) -> int:
    """Arama saati geldiyse büyük hesapların yeni postlarını bulur, taslaklarla sahibine gönderir. Gönderilen sayısı.
    Hiçbir şey paylaşmaz (D3). Claude yoksa çalışmaz (taslaksız fırsat göndermek işe yaramaz). Görülen postlar iki
    hesapta ortaktır: aynı posta iki hesabımızdan cevap önerilmez (X: koordineli davranış sayılır)."""
    cfg = ayar_yukle()
    gunluk = cfg.gunluk_yorum if hesap == "kalkylerat" else cfg.likely_gunluk_yorum
    saatler = cfg.saatler if hesap == "kalkylerat" else cfg.likely_saatler
    if not cfg.aktif or client is None or gunluk <= 0:
        return 0
    veri = yukle()
    tarih = simdi.date().isoformat()
    h = _hesap_durumu(veri, hesap, tarih)
    saat = max((s for s in saatler if s <= simdi.hour), default=None)
    if saat is None or saat in h["aramalar"] or h["gonderilen"] >= gunluk:
        return 0
    maclar = [a for a in (gun or {}).get("analizler") or [] if datetime.fromisoformat(a["baslama"]) > simdi]
    if hesap == "kalkylerat" and not any(kart_postu(gun, m) for m in maclar):
        return 0  # SÖZLEŞME D6: kartı paylaşılmış yaklaşan maç yok → arama da yok (ücret yok; saat sayılmaz)
    kalan_arama = len([s for s in saatler if s >= saat])
    hedef = min(math.ceil((gunluk - h["gonderilen"]) / kalan_arama), gunluk - h["gonderilen"])
    h["aramalar"].append(saat)
    kaydet(veri)  # arama sayıldı: hata olsa da bu saatte tekrar okunmaz (maliyet)
    baslangic = (simdi - timedelta(hours=TAZE_SAAT)).isoformat(timespec="seconds")
    onbellek = veri.get("onbellek") or {}
    if onbellek.get("tarih") == tarih and onbellek.get("saat") == saat:
        ham = onbellek["postlar"]  # bu saatin araması diğer hesap için yapıldı: tekrar ücret ödenmez
    else:
        ham = x.ara(sorgu(cfg.hesaplar), baslangic, ARAMA_ADET)
        kulupler = kulup_hesaplari(maclar)
        if kulupler:  # bugünkü büyük maçların kulüp hesapları (ayrı sorgu: X sorgu sınırı 512 karakter)
            gorulmus = {p["id"] for p in ham}
            ham += [p for p in x.ara(sorgu(kulupler), baslangic, KULUP_ADET) if p["id"] not in gorulmus]
        veri["onbellek"] = {"tarih": tarih, "saat": saat, "postlar": ham}
    # Sahibinin isteği (25 Ekim 2026, D6): videolu post yok (taslak videoyu göremez) ve yalnızca bizim rakamımızı
    # verebileceğimiz, bugünkü bir maçla eşleşen postlar
    postlar = [p for p in ham if p["id"] not in veri["gorulen"] and not p.get("video") and eslesen_mac(p["metin"], maclar)]
    if hesap == "kalkylerat":  # SÖZLEŞME D6: yalnızca kartı paylaşılmış maçların postları; cevap kartla gider
        postlar = [p for p in postlar if kart_postu(gun, eslesen_mac(p["metin"], maclar))]
    adaylar = sorted(postlar, key=lambda p: (eslesen_mac(p["metin"], maclar) is not None, puan(p, simdi)), reverse=True)
    gonderilen = []
    for p in adaylar:
        if len(gonderilen) >= hedef:
            break
        veri["gorulen"].append(p["id"])
        mac = eslesen_mac(p["metin"], maclar)
        kupon = kupon_postu(list(kuponlar), mac, kullanici) if hesap == "likely" else None
        try:
            t = taslaklar(p, mac, client, ayar, hesap, kupon[0] if kupon else None)
        except Exception as e:
            yaz(f"Yorum fırsatları ({hesap}): taslak yazılamadı ({e}).")
            break
        if t:
            ek = (kupon[1] if kupon else None) if hesap == "likely" else kart_postu(gun, mac)
            gonderilen.append((p, mac, t, ek))
    if gonderilen:
        etiket_adi = ("🖼️ Kartımızla (1. taslak + bu maçın kart postumuz):" if hesap == "kalkylerat"
                      else "🎩 Kuponla (1. taslak + bugünkü kupon postu; bu maç kuponun bir ayağı):")
        if not h.get("issue"):  # h her gün sıfırlanır: bugünün issue'su yoksa açılır
            govde = ((f"@{ayar.alarm_kime} " if getattr(ayar, "alarm_kime", "") else "")
                     + f"Bugünün {ADLAR[hesap]} yorum fırsatları (günde {gunluk}, ayar: `ayarlar.toml` → `[buyume]`). "
                     f"**Bu cevapları {ADLAR[hesap]} hesabından at.** Büyük hesapların son saatlerdeki postları ve her "
                     "birine 2 taslak. **📋 Kopyala ve postu aç** sayfasında taslağın düğmesine dokun: metin panoya kopyalanır, "
                     "post X'te açılır; Yanıtla'ya dokun, yapıştır, gönder. "
                     + ("Yalnızca kartını paylaştığımız maçların postları gelir; her cevap o maçın kart postumuzla "
                        "kopyalanır. " if hesap == "kalkylerat" else
                        "Kupon seçeneği günde birkaç kez, her cevapta değil (reklam gibi görünmesin). ")
                     + "Fırsat gelir gelmez cevaplamak en iyisi (ilk 30–60 dakika); yanıtları aralıklı at.")
            h["issue"] = {"tarih": tarih, "no": gh.issue_ac(f"🚀 Yorum fırsatları {ADLAR[hesap]} {tarih}", govde,
                                                            ETIKETLER[hesap])}
        from .yorum import HESAP_UYARISI, sayfa_ogesi
        bas = h["gonderilen"]
        uyari = HESAP_UYARISI.format(ad="Mr. Likely") if hesap == "likely" else ""
        def ogesi(sira, p, mac, t, ek):
            kim = f"{sira}. @{p.get('kullanici') or '?'}" + (f" · {mac['ev']} v {mac['dep']}" if mac else "")
            url = f"https://x.com/{p.get('kullanici') or 'i'}/status/{p['id']}"
            if hesap == "kalkylerat" and ek:  # her hazır cevap kart postumuzla (X cevapta kartı gösterir)
                return sayfa_ogesi(kim, p["metin"], url, [f"{x}\n\n{ek}" for x in t])
            return sayfa_ogesi(kim, p["metin"], url, t, [(etiket_adi, f"{t[0]}\n\n{ek}")] if ek else [])
        ogeler = [ogesi(bas + i, p, mac, t, ek) for i, (p, mac, t, ek) in enumerate(gonderilen, 1)]
        sayfa = kopya.sayfa_yaz(f"firsat-{hesap}-{saat}.html", f"Yorum fırsatları {ADLAR[hesap]} · {saat}:00 UTC",
                                ogeler, simdi, uyari)
        kutu = kopya.kutu_ekle(ogeler, hesap, "firsat", simdi, KUTU_OMUR_DK)  # tek sayfa: gelen kutusu
        gh.yorum(h["issue"]["no"], (f"@{ayar.alarm_kime} " if getattr(ayar, "alarm_kime", "") else "")
                 + f"**{saat}:00 UTC fırsatları ({ADLAR[hesap]})**\n\n"
                 + (f"{uyari}\n\n" if uyari else "")
                 + f"📥 **[Gelen kutusu]({kutu})** (iki hesabın bütün fırsatları ve yorumları tek sayfada; 1–2 dakikada güncellenir) · "
                 + f"[yalnızca bu saatin sayfası]({sayfa})\n\n"
                 + "\n\n".join(bildirim(p, mac, t, bas + i, None if hesap == "kalkylerat" else ek, etiket_adi)
                                 + ("\n\n<sub>Her iki cevap da bu maçın kart postumuzla kopyalanır.</sub>" if hesap == "kalkylerat" and ek else "")
                                 for i, (p, mac, t, ek) in enumerate(gonderilen, 1)))
        h["gonderilen"] += len(gonderilen)
    kaydet(veri)
    yaz(f"Yorum fırsatları ({hesap}): {len(postlar)} post okundu, {len(gonderilen)} fırsat gönderildi.")
    return len(gonderilen)
