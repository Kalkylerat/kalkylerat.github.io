"""X Direktörü: hesabın içerik ve büyüme uzmanı.

İki görevi var:
1) Günlük (hızlı model): kupon dışı paylaşımların (günün maçları, anket, skor tahmini, günün istatistiği, radar,
   doğru tahmin/kötü fiyat, pas günü)
   metnini o haftanın stratejisine göre yazar. Her metin kod tarafından denetlenir; kurala uymazsa şablon paylaşılır.
2) Haftalık (en güçlü model): hesabın son tweetlerinin etkileşim rakamlarını ve kupon rekorunu inceler, gelecek haftanın
   stratejisini belirler (günlük yazarın kullandığı ton, soru tarzı, kaçınılacaklar) ve sahibine Türkçe rapor yazar.

X otomasyon kuralları kodda sabittir ve direktör bunları değiştiremez: başkalarına otomatik yanıt, etiketleme (@), DM,
beğeni, takip yok; link yok; bahis sitesi adı yok; kesinlik dili yok."""

import json
import re
from datetime import datetime, timedelta

import anthropic

from . import config, kayit
from .tweets import GENEL_ETIKETLER, LISTE_ETIKET_SINIRI, ANSVAR, LIMIT, izinli_etiket, uzunluk

DOSYA = config.ROOT / "data" / "direktor.json"
REHBER_DOSYASI = config.ROOT / ".claude" / "skills" / "sosyal-medya" / "SKILL.md"


def _rehber() -> str:
    """Projenin X uzmanlık rehberi (algoritma gerçekleri, hesap kuralları, işe yarayanlar): direktörün bilgi temeli."""
    try:
        metin = REHBER_DOSYASI.read_text(encoding="utf-8")
    except OSError:
        return ""
    metin = metin.split("---", 2)[-1] if metin.startswith("---") else metin
    return "\n\nAccount playbook (written by the owner's team, in Turkish; follow it):\n" + metin.strip()

KURALLAR = """Hard rules (never break them):
- Plain, friendly English for a broad football audience. Max 280 characters (emojis count double).
- Use only the facts given. Never invent stats, news, line-ups, injuries or quotes.
- No "@" mentions, no links, no bookmaker or betting-site names.
- Layout: easy to scan at a glance. Short lines; put each number on its own line, started by ONE emoji that marks
  what it is (🏆 result, ⚽ goals, 🥅 both teams score, 🎯 score, 📈 stats, 💹 market, 🕗 kick-off, 🆚 match,
  💡 tip, 💬 question); blank line between blocks; never two emojis in a row, never a wall of them.
- Numbers: always write chances with a % sign (66%), never decimals like 0.66; no abbreviations like O2.5 or BTTS
  in running text ("Over 2.5 goals", "Both teams score").
- Hashtags: only from "allowed_hashtags" in the facts (real tags fans already use), at most two; none if the list is
  empty. Exception: the "tablo" (analysis board) post ends with a line carrying ALL its allowed_hashtags.
- Never say "lock", "guaranteed", "sure thing", "banker", "free money" or promise wins. Talk in chances.
- No engagement bait ("RT", "like if", "follow for"). Ask one real question people want to answer.
- No betting tips: posts are about football and our numbers (analysis, never advice to bet).

Voice: sound like a person who loves football and numbers, not a bot. Vary how posts open and flow; don't reuse
stock phrases or the same layout every day; contractions are fine; short sentences; no hype. The template is only
a reference for the facts: rewrite it in your own words."""

GUNLUK_SISTEM = f"""You are the X (Twitter) director of @kalkylerat, a football stats account that publishes data-driven
match analysis every day (probabilities for every market, most likely scores) and checks every call in public after
full time. No coupons, no stakes, no betting advice. You write one post at a time for the account's daily schedule. Goal: replies and real conversation
(replies weigh far more than likes in the algorithm), steady growth, and a trustworthy voice.

{KURALLAR}

Follow this week's strategy notes when they are given. Return the post text in "metin". Set "paylas" to false (and
"metin" empty) only if this post would add nothing today or go against the playbook; otherwise true.
"radar" posts list games we deliberately left out of our coupon with our chance for one market each: they are
information for the reader, never a recommendation; keep the "not in our coupon" framing and the 18+ line.
"deger" posts ("good call, poor price") show games we expect to go our way but skipped because the odds are below our
fair price: explain that a likely outcome at a too-short price is not worth it for the bank, give our chance, the odds and
the fair odds from the facts, ask whether skipping was right, keep the 18+ line. Never tell people to play them.
"deger_sonuc" quotes that post after the games: give each score and whether our call came in, be honest (right or
wrong), say in one short line why the price still mattered, keep the 18+ line.
"bilgi" is the daily knowledge post (odds, probability, staking, models): explain the given facts in a lively,
plain way with a real-life angle and end with one open question. Use exactly the numbers in "facts_to_use" and no
others; never add stats, history or claims of your own. Keep the 18+ line.
"analiz" introduces our match analysis card (image attached): mention the headline chances and the most likely
score from the facts, invite opinions; analysis only, never tell people to bet. "analiz_sonuc" quotes that card after
full time: the score and which calls came in, honest either way. Use only numbers from the facts.
"tablo" introduces the image of today's analysis board (many matches, lower leagues too). "ayrisma" lists games
where team stats and the market disagree and asks who is right: explain briefly what each side is, no advice.""" + _rehber()

HAFTALIK_SISTEM = f"""You are the X (Twitter) growth director of @kalkylerat, a football stats account that publishes
data-driven match analysis every day (probabilities for every market, most likely scores) and checks every call in public
after full time (no coupons, no stakes). A paid tier with the full daily analysis of every match is planned. Each week you review how the account's posts
performed and set the strategy for the coming week. You also advise the owner on growth and on earning money from the
account within X's rules and the law (e.g. X Premium creator revenue sharing, sponsorships, a paid newsletter later),
being honest when a step is not possible yet. Affiliate links to betting sites are not allowed before month 3 and only with
licensed operators; never recommend breaking X's automation rules (no automated replies, mentions, DMs, likes or follows).

The account posts automatically every day: today's big games, 3 match analysis cards (image) before kick-off, a
"full time" quote of each card with which calls came in, a match poll and a daily knowledge post. The owner replies by hand.

{KURALLAR}

Base every claim on the numbers given. "strateji" guides the daily writer next week: keep it short and concrete.
"gunluk_max_kupon" is how many coupons per day (1-3) the bot may post next week; the owner follows your call.
"rapor" is for the owner, in Turkish, plain and practical (what worked, what to change, what the owner should do by hand).""" + _rehber()

GUNLUK_SEMA = {"type": "object", "properties": {"paylas": {"type": "boolean"}, "metin": {"type": "string"}},
               "required": ["paylas", "metin"], "additionalProperties": False}
HAFTALIK_SEMA = {
    "type": "object",
    "properties": {
        "strateji": {
            "type": "object",
            "properties": {
                "ton": {"type": "string"},
                "soru_ornekleri": {"type": "array", "items": {"type": "string"}},
                "kacinilacaklar": {"type": "array", "items": {"type": "string"}},
                "odak": {"type": "string"},
                "gunluk_max_kupon": {"type": "integer"},
            },
            "required": ["ton", "soru_ornekleri", "kacinilacaklar", "odak", "gunluk_max_kupon"],
            "additionalProperties": False,
        },
        "rapor": {"type": "string"},
    },
    "required": ["strateji", "rapor"],
    "additionalProperties": False,
}

# Kupon dışı paylaşımlar bahis tavsiyesi, kesinlik dili, link, yönlendirme ve bahis sitesi adı içeremez.
_YASAK = re.compile(
    r"\block(ed|s)?\b|guarantee|sure (thing|win|bet)|dead cert|\bcert\b|certain (win|winner|to win)|"
    r"can'?t (lose|miss)|100\s*%|\bbanker\b|free money|smash (it|the)|\bstake\b|\bbets?\b|\bbetting\b|"
    r"\btips?\b|\btipster\b|\bwager|\bRT\b|retweet|like if|follow (us|for)|\bDM\b|telegram|whatsapp|discord|\bvip\b|"
    r"https?://|www\.|@|"
    r"bet\s*365|betfair|unibet|betway|bwin|1xbet|pinnacle|betsson|nordicbet|william\s*hill|\b888|betano|"
    r"betvictor|comeon|marathonbet|coolbet|paddy\s*power|sky\s*bet|stake\.com", re.IGNORECASE)


# Alan adı (küçük harfle yazılır; "Spurs.Me" gibi büyük harfli kısaltmalar yakalanmaz).
_ALAN_ADI = re.compile(r"\b[a-z0-9-]+\.(com|net|org|io|co|se|uk|tr|bet|app|gg|ly|me|tv)\b")


# Bilgi postu oran/stake/kasa yönetimini anlatır: "stake", "bet" gibi sözcükler serbest, gerisi aynı.
_YASAK_BILGI = re.compile(_YASAK.pattern.replace(r"\bstake\b|\bbets?\b|\bbetting\b|", "")
                          .replace(r"\btips?\b|\btipster\b|\bwager|", "")
                          .replace(r"100\s*%|", ""), re.IGNORECASE)  # "toplam %100" bir olgu, kesinlik değil
_SAYI = re.compile(r"(?<![\w.])[−-]?\d+(?:[.,]\d+)?")


def sayilar_dogru(metin: str, kaynak: str) -> bool:
    """Metindeki her sayı kaynakta (olgularda ya da şablonda) geçmeli: direktör yeni rakam uyduramaz."""
    izinli = {s.replace("−", "-") for s in _SAYI.findall(kaynak)} | {"18", "1", "0"}
    return all(s.replace("−", "-") in izinli for s in _SAYI.findall(metin))


def kurala_uygun(metin: str, tur: str, bahisciler: list[str], izinli: set[str] | None = None) -> bool:
    yasak = _YASAK_BILGI if tur == "bilgi" else _YASAK
    if not metin or uzunluk(metin) > LIMIT or yasak.search(metin) or _ALAN_ADI.search(metin):
        return False
    etiketler = re.findall(r"#\w+", metin)
    liste = tur == "tablo"  # liste postu: daha çok etiket ve genel etiketler serbest
    if len(etiketler) > (LISTE_ETIKET_SINIRI if liste else 2) or any(
            not (izinli_etiket(e) or (liste and e in GENEL_ETIKETLER)) or (izinli is not None and e not in izinli) for e in etiketler):
        return False  # yalnızca gerçek turnuva etiketleri, en fazla iki
    if any(b.lower() in metin.lower() for b in bahisciler):
        return False
    return tur not in ("pas", "radar", "deger", "deger_sonuc", "bilgi", "analiz", "analiz_sonuc", "tablo", "ayrisma") or metin.rstrip().endswith(ANSVAR)


def yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _kaydet(veri: dict) -> None:
    DOSYA.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _cagir(client, modeller: list[tuple[str, str]], sistem: str, icerik: str, sema: dict, max_tokens: int) -> dict:
    """Sırayla modelleri dener (biri erişilemez ya da reddederse sıradaki); geçerli JSON döner."""
    hata = None
    for model, effort in modeller:
        try:
            # Sistem metni (kurallar + X rehberi) her çağrıda aynı: önbelleğe alınır. Günlük çağrılar 45–60 dk arayla
            # geldiği için 1 saatlik önbellek; tekrar okumalar ~%90 ucuz.
            with client.messages.stream(model=model, max_tokens=max_tokens,
                                        system=[{"type": "text", "text": sistem,
                                                 "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
                                        messages=[{"role": "user", "content": icerik}],
                                        output_config={"effort": effort, "format": {"type": "json_schema", "schema": sema}}
                                        ) as stream:
                msg = stream.get_final_message()
            if msg.stop_reason in ("refusal", "max_tokens"):
                raise RuntimeError(f"{model}: {msg.stop_reason}")
            return json.loads(next(b.text for b in msg.content if b.type == "text"))
        except (anthropic.APIError, RuntimeError, StopIteration, ValueError) as e:
            hata = e
    raise RuntimeError(f"Direktör çağrısı başarısız: {hata}")


def yazar(ayar, client=None, yaz=print):
    """etkilesim.paylas için metin yazıcı: (tür, olgular, şablon) -> metin. Hata ya da kural dışı metinde şablon."""
    def yazici(tur: str, olgular: dict, sablon: str) -> str:
        strateji = yukle().get("strateji") or {}
        etiketler = sorted(set(re.findall(r"#\w+", sablon)))  # yalnızca şablonun (kodun doğruladığı) etiketleri
        icerik = json.dumps({"post_type": tur, "facts": olgular, "template_for_reference": sablon,
                             "allowed_hashtags": etiketler, "this_week_strategy": strateji}, ensure_ascii=False, indent=1)
        if tur in ("pas", "radar", "deger", "deger_sonuc", "bilgi", "analiz", "analiz_sonuc", "tablo", "ayrisma"):
            icerik += f'\nThe post must end with the line "{ANSVAR}".'
        try:
            cevap = _cagir(client or anthropic.Anthropic(), [(ayar.direktor_model, ayar.direktor_effort),
                                                             (ayar.claude_model, "low")],
                           GUNLUK_SISTEM, icerik, GUNLUK_SEMA, 8000)
        except Exception as e:
            yaz(f"Direktör metni yazamadı ({tur}): {e}; şablon kullanıldı.")
            return sablon
        if cevap.get("paylas") is False and tur != "pas":
            return ""  # direktör bugün bu paylaşımı uygun görmedi (pas açıklaması her zaman gider)
        metin = (cevap.get("metin") or "").strip()
        if tur in ("bilgi", "analiz", "analiz_sonuc", "tablo", "ayrisma") and not sayilar_dogru(metin, json.dumps(olgular, ensure_ascii=False) + sablon):
            yaz("Direktör bilgi metninde olgularda olmayan bir sayı kullandı; şablon kullanıldı.")
            return sablon
        if not kurala_uygun(metin, tur, ayar.oran_bahiscileri + [ayar.keskin_bahisci], set(etiketler)):
            yaz(f"Direktör metni kurala uymadı ({tur}); şablon kullanıldı.")
            return sablon
        return metin
    return yazici


def _hafta(simdi: datetime) -> str:
    y, w, _ = simdi.isocalendar()
    return f"{y}-W{w:02d}"


def haftalik_gerekli(simdi_yerel: datetime) -> bool:
    """Haftada bir (Pazartesi 09:00'dan sonra) ya da hiç strateji yoksa ilk fırsatta."""
    veri = yukle()
    deneme = veri.get("son_deneme")
    bekleme = timedelta(hours=6 if veri.get("deneme_sayisi", 0) < 2 else 24)
    if deneme and simdi_yerel < datetime.fromisoformat(deneme) + bekleme:
        return False  # başarısız deneme her 15 dakikada bir (ücretli model) tekrarlanmasın; 2 hatadan sonra günde bir
    if not veri.get("strateji"):
        return True
    return simdi_yerel.weekday() == 0 and simdi_yerel.hour >= 9 and veri.get("hafta") != _hafta(simdi_yerel)


def haftalik(ayar, gunler: list[dict], tweetler: list[dict], gh, simdi_yerel: datetime, client=None, yaz=print) -> dict:
    """Haftalık inceleme: strateji kaydedilir, sahibine rapor issue'su açılır."""
    onceki = yukle()
    _kaydet({**onceki, "son_deneme": simdi_yerel.isoformat(timespec="seconds"),
             "deneme_sayisi": onceki.get("deneme_sayisi", 0) + 1})
    hafta_once = (simdi_yerel - timedelta(days=7)).date().isoformat()
    son = [g for g in gunler if g["tarih"] >= hafta_once]
    veri_kupon = [{"tarih": g["tarih"], "kupon": g["id"], "sonuc": [kayit.kupon_durumu(g, k) for k in kayit.kuponlar(g)],
                   "secimler": [s["kisa"] for s in g["secimler"]]} for g in son]
    icerik = json.dumps({
        "today": simdi_yerel.date().isoformat(),
        "bank_summary": kayit.ozet(gunler, ayar.kasa_baslangic),
        "last_7_days_coupons": veri_kupon,
        "own_recent_tweets_with_metrics": [{"text": t.get("text", "")[:200], "created_at": t.get("created_at"),
                                            "metrics": t.get("public_metrics")} for t in tweetler],
        "previous_strategy": yukle().get("strateji"),
    }, ensure_ascii=False, indent=1, default=str)
    sonuc = _cagir(client or anthropic.Anthropic(), [(ayar.direktor_strateji_model, ayar.direktor_strateji_effort),
                                                     (ayar.claude_model, "high")],
                   HAFTALIK_SISTEM, icerik, HAFTALIK_SEMA, 64000)
    hafta = _hafta(simdi_yerel)
    veri = {"hafta": hafta, "guncelleme": simdi_yerel.isoformat(timespec="seconds"), "strateji": sonuc["strateji"]}
    try:
        veri["rapor_issue"] = gh.issue_ac(f"X Direktörü haftalık rapor – {hafta}", sonuc["rapor"], "rapor")
    except Exception as e:
        yaz(f"Rapor issue'su açılamadı: {e}")
    _kaydet(veri)
    yaz(f"### X Direktörü ({hafta})\n{sonuc['rapor']}")
    return veri


def gunluk_max_kupon(ayar) -> int:
    """Direktörün belirlediği günlük kupon sınırı (1-3); yoksa ayarlar.toml'daki."""
    deger = (yukle().get("strateji") or {}).get("gunluk_max_kupon")
    return max(1, min(3, int(deger))) if isinstance(deger, (int, float)) else ayar.max_kupon
