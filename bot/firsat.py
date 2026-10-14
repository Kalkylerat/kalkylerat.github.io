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
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import config

ETIKET = "yorum-firsatlari"
DOSYA = config.ROOT / "data" / "firsatlar.json"
ARAMA_ADET = 25  # bir aramada en fazla bu kadar post okunur (maliyet ~$0.13)
TAZE_SAAT = 3  # yalnızca son bu kadar saatte atılmış postlar (eski posta yanıt görünmez)


@dataclass
class BuyumeAyar:
    aktif: bool = True
    gunluk_yorum: int = 10
    saatler: list = field(default_factory=lambda: [10, 13, 16, 18])  # UTC, aramaların yapıldığı saatler
    hesaplar: list = field(default_factory=lambda: [
        "OptaJoe", "OptaAnalyst", "Squawka", "ESPNFC", "brfootball", "FabrizioRomano", "FootballTweet", "433",
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
               "inter": ["inter milan"], "ac milan": ["milan"], "wolves": ["wolverhampton"]}


def _konum(takim: str, metin: str) -> int | None:
    """Takımın postta ilk geçtiği yer (resmi ad ya da bilinen kısa adı, tam kelime); geçmiyorsa None."""
    yerler = [m.start() for ad in [takim.lower(), *TAKMA_ADLAR.get(takim.lower(), [])]
              for m in [re.search(rf"(?<!\w){re.escape(ad)}(?!\w)", metin.lower())] if m]
    return min(yerler) if yerler else None


def eslesen_mac(metin: str, maclar: list[dict]) -> dict | None:
    """Postun konusu olan bugünkü maç: önce iki takımı da geçen, yoksa postta EN ÖNCE adı geçen takımın maçı
    (14 Ekim: Man City–PSG postunda sonradan anılan "Real Madrid" yüzünden Roma–Real kartı eşleşmişti)."""
    adaylar = []
    for a in maclar:
        ev, dep = _konum(a["ev"], metin), _konum(a["dep"], metin)
        if ev is not None or dep is not None:
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
    c = (a.get("karsilastirma") or [None])[0]
    if c:
        olg["odds_vs_team_stats"] = f'{c["ad"]}: odds {_pct(c["piyasa"])}, team stats {_pct(c["istatistik"])}'
    return olg


SISTEM = """You draft replies that the owner of @kalkylerat (a football numbers account: chances for every market,
never picks) will paste BY HAND under a big football account's post on X. You never post anything.
Write 2 different reply drafts to the post below.

Hard rules:
- Max 200 characters. No links, no "@", no hashtags, at most one emoji. Plain, natural English.
- Add something to THEIR post: react to what it says, then (if match facts are given AND they are about the same
  match their post is about) one number from our facts. If our facts are about a different match, use no numbers
  and never bring that other match up.
  Never invent stats, news or line-ups; use only numbers from our facts or the post itself.
- Not promotional: never "check our page", "follow us", "see our card", never mention our account.
- Kind and respectful to everyone: no sarcasm, no digs, no negative judgments about any club, player, fan, manager
  or the account (never "strange look", "embarrassing", "struggling"). On controversies (discipline, fines,
  contracts, referees, fan trouble, politics) take no side; if the post is mainly a controversy, set "uygun" false.
- Say only what is in their post or our facts; if unsure, leave it out. Open and friendly, like talking to a mate.
- Chances, not picks: never pick, tip, lock, guaranteed, sure, bet. No bookmaker names. Never argue or mock.
- Sound like a fan who loves numbers: no "Great post!", no "Here's", no "Honestly,", no corporate words.
- Draft 2 ends with a short, specific question (replies that start a conversation get seen).
Set "uygun" false (and drafts empty) if the post is not about football matches or players, is sad news (injury,
death, tragedy), politics, an ad or a giveaway: a numbers reply there would look tone-deaf."""

SEMA = {"type": "object", "additionalProperties": False, "required": ["uygun", "taslaklar"],
        "properties": {"uygun": {"type": "boolean"}, "taslaklar": {"type": "array", "items": {"type": "string"}}}}


def taslaklar(post: dict, mac: dict | None, client, ayar) -> list[str]:
    """Posta 2 cevap taslağı; uygun değilse ya da kurala uyan taslak yoksa boş liste (o post gönderilmez)."""
    from .direktor import _cagir
    from .yorum import uygun
    olg = mac_olgulari(mac) if mac else None
    icerik = json.dumps({"their_post": post["metin"], "account": post.get("kullanici"),
                         "our_match_facts": olg or "(no match of ours in this post: react without numbers)"},
                        ensure_ascii=False, indent=1)
    cevap = _cagir(client, [(ayar.direktor_model, "low"), (ayar.claude_model, "low")], SISTEM, icerik, SEMA, 2000)
    if not cevap.get("uygun"):
        return []
    kaynak = post["metin"] + "\n" + json.dumps(olg or {}, ensure_ascii=False)
    return [t.strip() for t in cevap.get("taslaklar") or [] if uygun(t.strip(), kaynak) and "@" not in t][:2]


def kart_postu(gun: dict | None, mac: dict | None) -> str | None:
    """Bu maçın bizim paylaşılmış kart postunun adresi (cevaba eklenirse X onu kart olarak gösterir); yoksa None."""
    if not gun or not mac:
        return None
    for i, a in enumerate(gun.get("analizler") or []):
        e = (gun.get("etkilesim") or {}).get(f"analiz_{i}") or {}
        if a is mac or a.get("fixture_id") == mac.get("fixture_id"):
            return f"https://x.com/kalkylerat/status/{e['tweet_id']}" if e.get("durum") == "paylasildi" and e.get("tweet_id") else None
    return None


def bildirim(post: dict, mac: dict | None, taslak: list[str], sira: int, kart: str | None = None) -> str:
    from .yorum import taslak_satirlari
    m = post.get("metrik") or {}
    satirlar = [f"### {sira}. @{post.get('kullanici') or '?'} · 💬 {m.get('reply_count', 0)} · ❤️ {m.get('like_count', 0)}",
                f"> {post['metin'].strip()[:280]}".replace("\n", "\n> "), "",
                f"👀 [Postu gör](https://x.com/{post.get('kullanici') or 'i'}/status/{post['id']})"
                + (f" · bizim kart: {mac['ev']} v {mac['dep']}" if mac else ""), ""]
    ekler = [("🖼️ Kartımızla (1. taslak + bu maçın kart postumuz):", f"{taslak[0]}\n\n{kart}")] if kart and taslak else []
    satirlar += taslak_satirlari(post["id"], taslak, ekler)
    return "\n".join(satirlar).rstrip()


def kontrol(x, gh, ayar, gun: dict | None, simdi: datetime, client, yaz=print) -> int:
    """Arama saati geldiyse büyük hesapların yeni postlarını bulur, taslaklarla sahibine gönderir. Gönderilen sayısı.
    Hiçbir şey paylaşmaz (D3). Claude yoksa çalışmaz (taslaksız fırsat göndermek işe yaramaz)."""
    cfg = ayar_yukle()
    if not cfg.aktif or client is None or cfg.gunluk_yorum <= 0:
        return 0
    veri = yukle()
    tarih = simdi.date().isoformat()
    if veri.get("tarih") != tarih:
        veri = {"tarih": tarih, "gonderilen": 0, "aramalar": [], "gorulen": veri.get("gorulen", [])[-300:]}
    saat = max((s for s in cfg.saatler if s <= simdi.hour), default=None)
    if saat is None or saat in veri["aramalar"] or veri["gonderilen"] >= cfg.gunluk_yorum:
        return 0
    kalan_arama = len([s for s in cfg.saatler if s >= saat])
    hedef = min(math.ceil((cfg.gunluk_yorum - veri["gonderilen"]) / kalan_arama), cfg.gunluk_yorum - veri["gonderilen"])
    veri["aramalar"].append(saat)
    kaydet(veri)  # arama sayıldı: hata olsa da bu saatte tekrar okunmaz (maliyet)
    baslangic = (simdi - timedelta(hours=TAZE_SAAT)).isoformat(timespec="seconds")
    postlar = [p for p in x.ara(sorgu(cfg.hesaplar), baslangic, ARAMA_ADET) if p["id"] not in veri["gorulen"]]
    maclar = [a for a in (gun or {}).get("analizler") or [] if datetime.fromisoformat(a["baslama"]) > simdi]
    adaylar = sorted(postlar, key=lambda p: (eslesen_mac(p["metin"], maclar) is not None, puan(p, simdi)), reverse=True)
    gonderilen = []
    for p in adaylar:
        if len(gonderilen) >= hedef:
            break
        veri["gorulen"].append(p["id"])
        mac = eslesen_mac(p["metin"], maclar)
        try:
            t = taslaklar(p, mac, client, ayar)
        except Exception as e:
            yaz(f"Yorum fırsatları: taslak yazılamadı ({e}).")
            break
        if t:
            gonderilen.append((p, mac, t))
    if gonderilen:
        if (veri.get("issue") or {}).get("tarih") != tarih:
            govde = ((f"@{ayar.alarm_kime} " if getattr(ayar, "alarm_kime", "") else "")
                     + f"Bugünün yorum fırsatları (günde {cfg.gunluk_yorum}, ayar: `ayarlar.toml` → `[buyume] gunluk_yorum`). "
                     "Büyük hesapların son saatlerdeki postları ve her birine 2 taslak. **✍️ Bu cevapla aç**'a dokun: "
                     "X'te cevap hazır açılır, istersen düzelt, Gönder'e sen basarsın. **🖼️ Kartımızla** seçeneği "
                     "cevaba o maçın kart postumuzu ekler; günde birkaç kez kullan, her cevapta değil (reklam gibi "
                     "görünmesin). Fırsat gelir gelmez cevaplamak en iyisi (ilk 30–60 dakika); yanıtları aralıklı at.")
            veri["issue"] = {"tarih": tarih, "no": gh.issue_ac(f"🚀 Yorum fırsatları {tarih}", govde, ETIKET)}
        bas = veri["gonderilen"]
        gh.yorum(veri["issue"]["no"], (f"@{ayar.alarm_kime} " if getattr(ayar, "alarm_kime", "") else "")
                 + f"**{saat}:00 UTC fırsatları**\n\n"
                 + "\n\n".join(bildirim(p, mac, t, bas + i, kart_postu(gun, mac))
                                 for i, (p, mac, t) in enumerate(gonderilen, 1)))
        veri["gonderilen"] += len(gonderilen)
    kaydet(veri)
    yaz(f"Yorum fırsatları: {len(postlar)} post okundu, {len(gonderilen)} fırsat gönderildi.")
    return len(gonderilen)
