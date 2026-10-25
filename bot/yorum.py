"""Yorum kiti (SÖZLEŞME D3): hesabın postlarına gelen yeni yorumlar ve etiketlemeler için sahibine kopyalanmaya hazır
cevap taslakları. Günlük bir GitHub issue'su açılır, her yeni yorum oraya sahibini etiketleyen bir yorum olarak düşer
(telefona bildirim). Sahibi kopyalama sayfasından taslağı kopyalar, yorumu açar, yapıştırıp kendisi gönderir.

Bot hiçbir zaman kendisi cevap atmaz, beğenmez, takip etmez: X otomasyon kuralları başkalarına otomatik yanıtı
yasaklar (D3). Okuma ücretlidir (dönen post başına): gündüz 30 dakikada bir (gece yok), yalnızca son görülen yorumdan yenileri sorulur."""

import json
import re
from datetime import datetime, timedelta

from . import bildirim as bildirim_kanali, config, kopya

ETIKETLER = {"kalkylerat": "yorum-kiti", "likely": "yorum-kiti-likely", "flood": "yorum-kiti-flood"}  # hesap başına: günlük issue, eskisi kapanır
DOSYA = config.ROOT / "data" / "yorumlar.json"
KONTROL_DK = 30  # cevap için ilk 30–60 dk yeter; boş sorgu ücretliyse bile günde ~32 sorgu (14 Ekim)
GUNDUZ = (6, 23)  # UTC: bu saatler dışında sorulmaz; gece gelen yorum sabah ilk kontrolde gelir
ILK_GUN = 7  # ilk çalışmada bu kadar gün önceki yorumlar da gelir (cevapsız kalanlar)
EN_FAZLA = 10  # bir kontrolde en fazla bu kadar yorum bildirilir (gerisi sonraki kontrole)

# Hesap başına ses (taslak yazan model okur). Mr. Likely'nin sesi marka/MR_LIKELY.md'den.
SESLER = {
    "kalkylerat": "You are @kalkylerat: a football numbers account. Every match card gives chances for every market "
                  "(from the betting market with the margin removed, next to team stats), never picks. Friendly, "
                  "curious, short. Explain a number if asked; never argue.",
}


def _likely_sesi() -> str:
    try:
        metin = (config.ROOT / "marka" / "MR_LIKELY.md").read_text(encoding="utf-8")
    except OSError:
        return "You are Mr. Likely: a dry, self-aware football coupon account. Likely, never certain."
    bolum = metin.split("## Who he is", 1)[-1].split("\n## ", 1)[0]
    return "You are Mr. Likely (second account, English). Voice notes:\n" + bolum.strip()[:4000]


def _flood_sesi() -> str:
    """Tiny Fixes (üçüncü hesap) sesi: marka/TINY_FIXES.md."""
    try:
        metin = (config.ROOT / "marka" / "TINY_FIXES.md").read_text(encoding="utf-8")
    except OSError:
        return "You are Tiny Fixes: an AI account that only posts tested fixes. Calm, plain, specific."
    bolum = metin.split("## Who is speaking", 1)[-1].split("\n## ", 1)[0]
    return "You are Tiny Fixes (AI fixes and news, English). Voice notes:\n" + bolum.strip()[:2500]


# İnsan sesi (14 Ekim 2026, sahibinin isteği): taslaklar robot gibi değil, maçı izleyen bir taraftar gibi.
INSAN_SESI = """How to sound human (this matters as much as the rules):
- Write like a real fan typing on their phone: short, relaxed, one thought. Usually 60–140 characters.
- Contractions and casual words are good ("that's", "mad", "fair play", "no chance", "proper", "yeah").
  A fragment is fine. Normal capitalisation: start each sentence with a capital letter.
- React first, like a person would: surprise, agreement, a small joke (kind, never at anyone's expense).
- Don't summarise or repeat their post back to them. Don't explain. Don't sound like a report.
- A number only if it fits naturally, and say it the way people talk: "we had them around 45%", not
  "Our numbers have City at 45%, PSG 33%, and 22% for the draw". Never more than one number in a reply.
- The drafts must differ in shape: not every draft has a number, not every draft ends with a question.
- Never start with: "Great", "Interesting", "Fascinating", "Love this", "Absolutely", "Indeed", "This is",
  "What a great", "Wow,". No "says a lot", "speaks volumes", "a testament to", "it's worth noting".
Bad: "Only 2 of the reigning champions making the XI says a lot about this season's ratings. Our numbers have City
at 45%."  Good: "2 from PSG and they're the holders... ratings can be harsh 😅"  Good: "We had City around 45% for
tonight, so that XI isn't miles off"  Good: "Who's the first name you'd drop from that XI though?"
"""

# Mr. Likely cevapları (15 Ekim 2026, sahibinin isteği: "çok robotik"): humanizer skill'inin (.claude/skills/humanizer)
# kısa tweet'e uyan maddeleri + her taslak bizim tahminimize bağlanır + hakaretsiz sevimli takılma (SÖZLEŞME D3/D6/D7).
LIKELY_INSAN = """Mr. Likely's replies (the owner said they sound robotic; fix that; where this differs from the
general notes above, this wins):
- He runs a coupon page, so every reply points back to HIS numbers. If match facts are given for the match in the
  conversation, at least one draft uses our chance for it, said like a person: "I've got Italy at 31%", "my model
  makes the draw 27%". That works even when the match is not in today's coupon. One number per draft, no more.
- Cheeky is good: a small, friendly tease about the post, the hype or the fans' confidence, set against his number
  ("Brave XI. I've still got them at 41%, no pressure"). Tease like a mate at the pub, then move on. Never an insult,
  never mocking a person, club, player, fan or manager, never "embarrassing", "clown", "shambles", "flop", "bottle".
  No teasing at all on sad news, injuries, controversy or a hostile comment: there he is just warm and short.
- Write it like one quick thought typed on a phone. Vary the shape: a fragment, a short sentence, sometimes a
  question. Contractions. Understatement over adjectives.
- AI tells to avoid (they give the game away): "not X, it's Y" or "not just X but Y" contrasts; a closing line that
  repeats the point ("That's the story."); openers like "Honestly,", "Look,", "Here's the thing", "Real talk";
  lists of three; dashes (use a comma or a full stop); words like crucial, testament, showcase, delve, vibrant,
  pivotal, landscape, underscore; summarising their post back to them; exclamation marks.
Good: "Bold XI. I've still got Italy at 31% tonight, so no pressure"  Good: "You lot are confident. My model has the
draw at 27%, just saying"  Good: "It's one of my legs today, so I'd quite like you to be right"  Bad: "Not just a team
news update, it's a statement. My numbers show a crucial 47% chance for France!"  Bad: "Italy fans, prepare to be
embarrassed: 31%"."""

LIKELY_NOTU = """Replying as Mr. Likely: speak as "I" ("I make it about 60%"). A little cocky but charming and funny
(owner's wish, 25 Oct 2026): confident in his numbers with a wink, playful, invites the next reply; never hurtful, no
insult or mockery of anyone, nothing that could sting (tease himself if in doubt), no exclamation marks. Never tell anyone to bet, stake, tail
or copy a coupon. If someone asks about a coupon, answer plainly: a numbers model chooses it on fixed rules, losers
are posted too. (Don't use the words "pick", "picks" or "tip": we give chances, not picks.)"""

SISTEM = f"""You draft replies that the account owner will read, edit and post BY HAND on X. You never post anything.
Write 2 different short reply drafts to the comment below, in the account's voice, in plain English.

First read the whole conversation in order: what the original post said, what WE said, and what THEY are
answering. Your reply must make sense as the next message in that exact thread:
- Answer what they actually said. If they push back on something we said, take it gracefully (agree where fair,
  soften if we were too harsh: "fair, that was a bit harsh from me"). Never double down, never argue.
- Respect time: check "now_utc" and the match status. Never ask whether they watched a match that hasn't been
  played, never talk about a result that doesn't exist yet.
- If they talk about another account (e.g. the original poster), don't judge that account either way.

Hard rules:
- Max 200 characters each. No links, no "@" mentions, no hashtags, no emojis except at most one.
- Use only facts from our post and the comment. Never invent stats, news, line-ups or results. Never name a
  player or manager who isn't in our post or the comment (squads change; your knowledge may be out of date). If a number is needed
  and it is not in our post, don't use a number.
- We give chances, not picks: never say pick, tip, lock, guaranteed, sure, bet now, or that we were right or wrong.
- No betting advice, no bookmaker names. Never argue, never mock. If the comment is hostile, stay calm and short.
- Kind and respectful to everyone: no sarcasm, no digs or negative judgments about any club, player, fan or person.
  Never claim something you can't see in the facts.
- Sound like a person: no "Great question!", no "Here's", no "Honestly,", no corporate words.
- Draft 1: answers the comment directly (one detail from our post if it helps). Draft 2: shorter, warm, and keeps
  the chat going (often a question back). Both must be ready to post as they are.
  Replying to someone talking to us: warm, like a friend replying, never like customer support.

{INSAN_SESI}

Also set "not" to ONE short sentence in Turkish for the owner: what the comment says, and "cevap vermesen de olur" if
it is spam, a bot, abuse or a scam link. Set "spam" true in that case."""
# Mr. Likely: hakaretsiz sevimli takılma serbest (SÖZLEŞME D7, 15 Ekim 2026); @kalkylerat'ta takılma yok.
SISTEM_LIKELY = SISTEM.replace("""- Kind and respectful to everyone: no sarcasm, no digs or negative judgments about any club, player, fan or person.
  Never claim something you can't see in the facts.""", """- Kind: a friendly tease is fine when they are playful, but no insults, no mocking, no negative judgments about
  any club, player, fan or person. Never claim something you can't see in the facts.""") + "\n" + LIKELY_INSAN

# Tiny Fixes (SOZLESME F): futbol sesi ve maç kuralları değil; yalnızca denenmiş olanı söyleyen sakin bir ses (F1–F3, F7).
FLOOD_SISTEM = """You draft replies that the account owner will read, edit and post BY HAND on X or Instagram. You never
post anything. Write 2 different short reply drafts to the comment below, in the account's voice, in plain English.

First read the whole conversation in order: what our post said and what THEY are answering. Answer what they said.
If they push back or say the prompt didn't work for them, take it gracefully: thank them, ask what they saw, never
argue and never insist it works for everyone.

Hard rules:
- Max 200 characters each. No links, no "@" mentions, no hashtags, at most one emoji.
- Use only facts from our post and the comment. Never invent results, numbers, model versions, prices or news.
- No fake experience: never "I've used this for months", "my clients", "we tested 50 tools". Only what our post says.
- No medical, legal or financial advice. If asked, say kindly that it's outside what we test.
- Sound like a person: no "Great question!", no "Here's", no "Honestly,", no hype words (game-changer, insane).
- Draft 1 answers the comment directly. Draft 2 is shorter and keeps the chat going (often a question back).

Also set "not" to ONE short sentence in Turkish for the owner: what the comment says, and "cevap vermesen de olur" if
it is spam, a bot, abuse or a scam link. Set "spam" true in that case."""

SEMA = {"type": "object", "additionalProperties": False, "required": ["taslaklar", "not", "spam"],
        "properties": {"taslaklar": {"type": "array", "items": {"type": "string"}},
                       "not": {"type": "string"}, "spam": {"type": "boolean"}}}

YEDEK = ["Cheers for reading. Which number on the card surprised you most?",
         "Fair point. How would you read this one?"]
YEDEK_FLOOD = ["Thanks for trying it. What did the output look like on your side?",
               "Fair point. Which part broke for you? Happy to test that case next."]
YEDEK_LIKELY = ["Fair point. I only go where the numbers send me, and they don't always treat me kindly.",
                "Noted. How would you have built it?"]


def yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def kaydet(veri: dict) -> None:
    DOSYA.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_ROBOT = re.compile(r"^(great|interesting|fascinating|love this|absolutely|indeed|certainly|this is a|what a great|"
                    r"wow,|look,|real talk)\b|\b(says a lot|speaks volumes|a testament to|it'?s worth noting|our numbers have|"
                    r"not just\b[^.]{0,40}\bbut|let'?s dive|here'?s the thing|at its core|the real question)\b",
                    re.IGNORECASE)
# Takılma serbest, hakaret değil (15 Ekim 2026): bu kelimelerle taslak elenir.
_HAKARET = re.compile(r"\b(idiot\w*|stupid|clowns?|embarrass\w*|pathetic|shambles|disgrace\w*|flops?|bottl(e|ed|ers?|ing)|"
                      r"trash|rubbish|useless|joke of|laughing ?stock|deluded|dumb|losers)\b", re.IGNORECASE)


def temizle(t: str) -> str:
    """Yapay zekâ izi bırakan noktalama koddan düzelir (humanizer §8, §21): uzun/kısa tire virgül olur, kıvrık tırnak düz."""
    t = re.sub(r"\s*[—–]\s*|\s+--\s+", ", ", t)
    return t.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")


def buyuk_harfle(t: str) -> str:
    """Taslak büyük harfle başlar (14 Ekim: sahibi küçük harfle başlayanları hata sandı)."""
    t = temizle(t.strip())
    return t[:1].upper() + t[1:] if t[:1].islower() else t


def uygun(taslak: str, kaynak: str) -> bool:
    """Taslak kurala uyuyor mu: kısa, linksiz, etiketsiz, seçim/kesinlik dili yok, kaynakta olmayan sayı yok."""
    from .denetci import _KESINLIK, _LINK, _SECIM_DILI
    from .direktor import sayilar_dogru, yz_izi
    return bool(taslak) and len(taslak) <= 240 and not _LINK.search(taslak) and "#" not in taslak \
        and not _SECIM_DILI.search(taslak) and not _KESINLIK.search(taslak) and not yz_izi(taslak) and not _ROBOT.search(taslak) \
        and not _HAKARET.search(taslak) and not re.search(r"\b(picks?|tips?|bet now|for sure|were right|right about)\b", taslak, re.IGNORECASE) and sayilar_dogru(taslak, kaynak)


def konusma(yorum: dict, hesap_adi: str) -> list[dict]:
    """Konuşma sırayla: (varsa) bizim cevap verdiğimiz post, bizim post, gelen yorum. Taslak bütün konuşmaya uymalı
    (14 Ekim: yalnızca bizim post + yorum görülünce oynanmamış maç için "izledin mi?" diye soruldu)."""
    adimlar = []
    if yorum.get("ust"):
        adimlar.append({"who": f"@{yorum.get('ust_kullanici') or '?'} (the post we replied to)", "text": yorum["ust"]})
    adimlar.append({"who": f"@{hesap_adi} (us)", "text": yorum.get("bizim") or "(not available: they may have mentioned us)"})
    adimlar.append({"who": f"@{yorum.get('kullanici') or '?'} (the comment to answer now)", "text": yorum.get("metin") or ""})
    return adimlar


def mac_bilgisi(metin: str, gun: dict | None, simdi: datetime) -> dict | None:
    """Konuşmada adı geçen bugünkü maç: başlama saati, oynandı mı, bizim yüzdeler (taslak "maçı izledin mi?" gibi
    zamana aykırı bir şey sormasın; rakam gerekiyorsa buradan)."""
    from .firsat import eslesen_mac, mac_olgulari
    maclar = (gun or {}).get("analizler") or []
    a = eslesen_mac(metin, maclar)
    if not a:
        return None
    bas = datetime.fromisoformat(a["baslama"])
    durum = ("not started yet" if simdi < bas else "probably finished" if simdi > bas + timedelta(hours=2)
             else "in play right now")
    return {**mac_olgulari(a), "kickoff_utc": bas.astimezone(simdi.tzinfo).strftime("%H:%M"), "status": durum}


def taslaklar(yorum: dict, hesap: str, client=None, ayar=None, yaz=print, gun: dict | None = None,
              simdi: datetime | None = None, hesap_adi: str = "kalkylerat") -> tuple[list[str], str, bool]:
    """(taslaklar, sahibine not, spam mı). Claude yoksa ya da taslaklar kurala uymazsa hazır kalıplar."""
    adimlar = konusma(yorum, hesap_adi)
    mac = mac_bilgisi(" ".join(a["text"] for a in adimlar), gun, simdi) if simdi and hesap != "flood" else None
    kaynak = "\n".join(a["text"] for a in adimlar) + "\n" + json.dumps(mac or {}, ensure_ascii=False)
    yedek = {"likely": YEDEK_LIKELY, "flood": YEDEK_FLOOD}.get(hesap, YEDEK)
    if client is None or ayar is None:
        return yedek, "", False
    from .direktor import _cagir
    ses = {"likely": lambda: _likely_sesi() + "\n" + LIKELY_NOTU, "flood": _flood_sesi}.get(
        hesap, lambda: SESLER["kalkylerat"])()
    sistem = {"flood": FLOOD_SISTEM, "likely": SISTEM_LIKELY}.get(hesap, SISTEM)
    icerik = json.dumps({"conversation_in_order": adimlar,
                         "now_utc": simdi.strftime("%Y-%m-%d %H:%M") if simdi else None,
                         "match_in_this_conversation": mac or "(no match of ours found in this conversation)"},
                        ensure_ascii=False, indent=1)
    try:
        cevap = _cagir(client, [(ayar.direktor_model, "low"), (ayar.claude_model, "low")], ses + "\n\n" + sistem,
                       icerik, SEMA, 2000)
    except Exception as e:
        yaz(f"Yorum kiti: taslak yazılamadı ({e}); hazır kalıplar kullanıldı.")
        return yedek, "", False
    iyi = [buyuk_harfle(t) for t in cevap.get("taslaklar") or [] if uygun(temizle(t.strip()), kaynak)][:2]
    return (iyi or yedek), (cevap.get("not") or "").strip(), bool(cevap.get("spam"))


HESAP_UYARISI = "⚠️ Önce X'te {ad} hesabına geç: post X'te açık olan hesapla açılır."


def taslak_satirlari(taslaklar: list[str], ekler: list[tuple[str, str]] = ()) -> list[str]:
    """Bildirimde taslakların görünür hali (kopyalama sayfaya: 📋 bağlantısı). ekler: (etiket, metin) ek seçenekler;
    ekteki bağlantı (ör. kart postumuz) metinde gösterilmez, kopyalanan metinde vardır."""
    satirlar = [f"**{n}.** {t}" for n, t in enumerate(taslaklar, 1)]
    satirlar += [f"**{etiket}** {t.split(chr(10) + chr(10))[0]} *(+ post bağlantısı)*" for etiket, t in ekler]
    return [x for s in satirlar for x in (s, "")]


def sayfa_ogesi(kim: str, post: str, url: str, taslaklar: list[str], ekler=(), not_: str = "") -> dict:
    return {"kim": kim, "post": post, "url": url, "not": not_,
            "taslaklar": [(f"{n}. taslak", t) for n, t in enumerate(taslaklar, 1)] + list(ekler)}


def bildirim(yorum: dict, taslak: list[str], not_: str, spam: bool, hesap_adi: str, sayfa: str | None = None,
             instagram_url: str | None = None) -> str:
    """instagram_url verilirse Instagram yorumu (Tiny Fixes): uyarı ve "gör" bağlantısı Instagram'a göre yazılır."""
    uyari = (f"⚠️ Önce Instagram'da @{hesap_adi} hesabına geç: cevap açık olan hesapla gider." if instagram_url
             else HESAP_UYARISI.format(ad="@" + hesap_adi))
    satirlar = ([uyari, ""] if hesap_adi.lower() != "kalkylerat" else []) + [
                f"### 💬 @{yorum.get('kullanici') or '?'} → @{hesap_adi}",
                f"> {(yorum.get('metin') or '').strip()}".replace("\n", "\n> "), ""]
    if yorum.get("ust"):
        satirlar += [f"<sub>Asıl post (@{yorum.get('ust_kullanici') or '?'}): {yorum['ust'][:140].replace(chr(10), ' ')}…</sub>", ""]
    if yorum.get("bizim"):
        satirlar += [f"<sub>Bizim cevabımız: {yorum['bizim'][:160].replace(chr(10), ' ')}…</sub>", ""]
    if not_:
        satirlar += [f"📝 {not_}" + (" (spam gibi)" if spam and "cevap vermesen" not in not_ else ""), ""]
    if sayfa:
        satirlar += [f"📋 **[Kopyala ve yorumu aç]({sayfa})** (sayfa 1–2 dakikada hazır olur)", ""]
    satirlar += [f"👀 [Postu Instagram'da gör]({instagram_url})" if instagram_url
                 else f"👀 [Yorumu X'te gör](https://x.com/i/web/status/{yorum['id']})", ""]
    satirlar += taslak_satirlari(taslak)
    return "\n".join(satirlar).rstrip()


def kontrol(x, gh, ayar, simdi: datetime, hesap: str = "kalkylerat", client=None, yaz=print, gun: dict | None = None) -> int:
    """Yeni yorumları sorar ve sahibine taslaklarla bildirir; bildirilen yorum sayısı. Hiçbir şey paylaşmaz (D3)."""
    veri = yukle()
    h = veri.setdefault(hesap, {})
    if not GUNDUZ[0] <= simdi.hour < GUNDUZ[1]:
        return 0
    if h.get("son_kontrol") and simdi < datetime.fromisoformat(h["son_kontrol"]) + timedelta(minutes=KONTROL_DK):
        return 0
    if not h.get("me"):
        h["me"], h["kullanici"] = x.ben()
    ilk = (simdi - timedelta(days=ILK_GUN)).isoformat(timespec="seconds") if not h.get("since_id") else None
    ham = x.bahsedenler(h["me"], since_id=h.get("since_id"), baslangic=ilk)
    yeni = [t for t in ham if t.get("yazar") != h["me"]]
    h["son_kontrol"] = simdi.isoformat(timespec="seconds")
    if not yeni:
        if ham:  # yalnızca kendi postlarımız geldi: işaret ilerler, aynı postlar her kontrolde yeniden okunmaz (ücret)
            h["since_id"] = max(ham, key=lambda t: int(t["id"]))["id"]
        kaydet(veri)
        return 0
    yeni = sorted(yeni, key=lambda t: int(t["id"]))[:EN_FAZLA]  # eskiden yeniye; fazlası sonraki kontrole
    tarih = simdi.date().isoformat()
    if (h.get("issue") or {}).get("tarih") != tarih:
        govde = (f"Bugün @{h['kullanici']} postlarına gelen yorumlar ve etiketlemeler. Her biri için 2 hazır cevap: "
                 "**📋 Kopyala ve yorumu aç**'a dokun: cevap panoya kopyalanır, yorum X'te açılır; Yanıtla, yapıştır, gönder. Bot hiçbir zaman "
                 "kendisi cevap atmaz (X kuralı). Aynı metni iki kişiye gönderme.")
        h["issue"] = {"tarih": tarih, "no": gh.issue_ac(f"💬 Yorumlar @{h['kullanici']} {tarih}", govde,
                                                         ETIKETLER.get(hesap, "yorum-kiti"))}
    try:  # bizim postun cevap verdiği üst postlar, tek istekte (konuşmanın başı; dönen post başına ~$0.005)
        ustler = x.postlar([t["ust_id"] for t in yeni if t.get("ust_id")]) if any(t.get("ust_id") for t in yeni) else {}
    except Exception as e:
        yaz(f"Yorum kiti: üst postlar okunamadı ({e}); konuşmanın başı olmadan yazılıyor.")
        ustler = {}
    bildirim_gitti = False
    for t in yeni:
        if t.get("ust_id") in ustler:
            t["ust"], t["ust_kullanici"] = ustler[t["ust_id"]]["metin"], ustler[t["ust_id"]]["kullanici"]
        taslak, not_, spam = taslaklar(t, hesap, client, ayar, yaz, gun=gun, simdi=simdi, hesap_adi=h["kullanici"])
        url = f"https://x.com/i/web/status/{t['id']}"
        sayfa = kopya.sayfa_yaz(f"yorum-{hesap}-{t['id']}.html", f"Yorum: @{t.get('kullanici') or '?'}",
                                [sayfa_ogesi(f"@{t.get('kullanici') or '?'} → @{h['kullanici']}", t.get("metin") or "",
                                             url, taslak, not_=not_)], simdi,
                                HESAP_UYARISI.format(ad="@" + h["kullanici"]) if hesap != "kalkylerat" else "")
        if not spam and hesap in ("kalkylerat", "likely"):  # gelen kutusu: cevaplamaya değer yorumlar (24 saat)
            kopya.kutu_ekle([sayfa_ogesi(f"@{t.get('kullanici') or '?'} → @{h['kullanici']}", t.get("metin") or "",
                                         url, taslak, not_=not_)], hesap, "yorum", simdi, 24 * 60)
        # Tek bildirim (25 Ekim 2026): kontrol başına bir kez; anlık bildirim açıksa GitHub etiketi yok
        etiketle = not bildirim_gitti and not spam and getattr(ayar, "alarm_kime", "") and not bildirim_kanali.acik()
        gh.yorum(h["issue"]["no"], (f"@{ayar.alarm_kime} " if etiketle else "")
                 + bildirim(t, taslak, not_, spam, h["kullanici"], sayfa))
        if not spam and not bildirim_gitti:
            bildirim_gitti = True
            if bildirim_kanali.acik():
                bildirim_kanali.gonder(f"💬 Yeni yorum · @{h['kullanici']}",
                                       f"@{t.get('kullanici') or '?'}: {(t.get('metin') or '')[:200]}", kopya.KUTU_SAYFA)
        h["since_id"] = t["id"]
        kaydet(veri)  # bildirildi: tekrar gelmesin
    yaz(f"Yorum kiti (@{h['kullanici']}): {len(yeni)} yeni yorum bildirildi.")
    return len(yeni)
