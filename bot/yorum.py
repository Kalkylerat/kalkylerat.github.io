"""Yorum kiti (SÖZLEŞME D3): hesabın postlarına gelen yeni yorumlar ve etiketlemeler için sahibine kopyalanmaya hazır
cevap taslakları. Günlük bir GitHub issue'su açılır, her yeni yorum oraya sahibini etiketleyen bir yorum olarak düşer
(telefona bildirim). Sahibi bağlantıdan yorumu açar, taslaklardan birini kendi cümlesiyle düzeltip elle atar.

Bot hiçbir zaman kendisi cevap atmaz, beğenmez, takip etmez: X otomasyon kuralları başkalarına otomatik yanıtı
yasaklar (D3). Okuma ücretlidir (dönen post başına): 15 dakikada bir, yalnızca son görülen yorumdan yenileri sorulur."""

import json
import re
from urllib.parse import quote
from datetime import datetime, timedelta

from . import config

ETIKETLER = {"kalkylerat": "yorum-kiti", "likely": "yorum-kiti-likely"}  # hesap başına: günlük issue, eskisi kapanır
DOSYA = config.ROOT / "data" / "yorumlar.json"
KONTROL_DK = 15
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
    return "You are Mr. Likely (second account, English). Voice notes:\n" + bolum.strip()[:2500]


# İnsan sesi (14 Ekim 2026, sahibinin isteği): taslaklar robot gibi değil, maçı izleyen bir taraftar gibi.
INSAN_SESI = """How to sound human (this matters as much as the rules):
- Write like a real fan typing on their phone: short, relaxed, one thought. Usually 60–140 characters.
- Contractions and casual words are good ("that's", "mad", "fair play", "no chance", "proper", "yeah").
  A fragment is fine. Starting lowercase is fine sometimes.
- React first, like a person would: surprise, agreement, a small joke (kind, never at anyone's expense).
- Don't summarise or repeat their post back to them. Don't explain. Don't sound like a report.
- A number only if it fits naturally, and say it the way people talk: "we had them around 45%", not
  "Our numbers have City at 45%, PSG 33%, and 22% for the draw". Never more than one number in a reply.
- The drafts must differ in shape: not every draft has a number, not every draft ends with a question.
- Never start with: "Great", "Interesting", "Fascinating", "Love this", "Absolutely", "Indeed", "This is",
  "What a great", "Wow,". No "says a lot", "speaks volumes", "a testament to", "it's worth noting".
Bad: "Only 2 of the reigning champions making the XI says a lot about this season's ratings. Our numbers have City
at 45%."  Good: "2 from PSG and they're the holders... ratings can be harsh 😅"  Good: "we had City around 45% for
tonight, so that XI isn't miles off"  Good: "who's the first name you'd drop from that XI though?"
"""

LIKELY_NOTU = """Replying as Mr. Likely: speak as "I" ("I make it about 60%"), light dry humour mostly at his own
expense (dull legs, coupons one leg short), never smug, no exclamation marks. Never tell anyone to bet, stake, tail
or copy a coupon. If someone asks about a coupon, answer plainly: a numbers model picks it on fixed rules, losers
are posted too."""

SISTEM = f"""You draft replies that the account owner will read, edit and post BY HAND on X. You never post anything.
Write 2 different short reply drafts to the comment below, in the account's voice, in plain English.

Hard rules:
- Max 200 characters each. No links, no "@" mentions, no hashtags, no emojis except at most one.
- Use only facts from our post and the comment. Never invent stats, news, line-ups or results. If a number is needed
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

SEMA = {"type": "object", "additionalProperties": False, "required": ["taslaklar", "not", "spam"],
        "properties": {"taslaklar": {"type": "array", "items": {"type": "string"}},
                       "not": {"type": "string"}, "spam": {"type": "boolean"}}}

YEDEK = ["cheers for reading. which number on the card surprised you most?",
         "fair point. how would you read this one?"]


def yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def kaydet(veri: dict) -> None:
    DOSYA.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


_ROBOT = re.compile(r"^(great|interesting|fascinating|love this|absolutely|indeed|certainly|this is a|what a great|"
                    r"wow,)\b|\b(says a lot|speaks volumes|a testament to|it'?s worth noting|our numbers have)\b",
                    re.IGNORECASE)


def uygun(taslak: str, kaynak: str) -> bool:
    """Taslak kurala uyuyor mu: kısa, linksiz, etiketsiz, seçim/kesinlik dili yok, kaynakta olmayan sayı yok."""
    from .denetci import _KESINLIK, _LINK, _SECIM_DILI
    from .direktor import sayilar_dogru, yz_izi
    return bool(taslak) and len(taslak) <= 240 and not _LINK.search(taslak) and "#" not in taslak \
        and not _SECIM_DILI.search(taslak) and not _KESINLIK.search(taslak) and not yz_izi(taslak) and not _ROBOT.search(taslak) \
        and not re.search(r"\b(picks?|tips?|bet now|for sure|were right|right about)\b", taslak, re.IGNORECASE) and sayilar_dogru(taslak, kaynak)


def taslaklar(yorum: dict, hesap: str, client=None, ayar=None, yaz=print) -> tuple[list[str], str, bool]:
    """(taslaklar, sahibine not, spam mı). Claude yoksa ya da taslaklar kurala uymazsa hazır kalıplar."""
    kaynak = (yorum.get("bizim") or "") + "\n" + (yorum.get("metin") or "")
    if client is None or ayar is None:
        return YEDEK, "", False
    from .direktor import _cagir
    ses = (_likely_sesi() + "\n" + LIKELY_NOTU) if hesap == "likely" else SESLER["kalkylerat"]
    icerik = json.dumps({"our_post": yorum.get("bizim") or "(not available: the comment may be a mention)",
                         "comment": yorum.get("metin"), "commenter": yorum.get("kullanici")}, ensure_ascii=False, indent=1)
    try:
        cevap = _cagir(client, [(ayar.direktor_model, "low"), (ayar.claude_model, "low")], ses + "\n\n" + SISTEM,
                       icerik, SEMA, 2000)
    except Exception as e:
        yaz(f"Yorum kiti: taslak yazılamadı ({e}); hazır kalıplar kullanıldı.")
        return YEDEK, "", False
    iyi = [t.strip() for t in cevap.get("taslaklar") or [] if uygun(t.strip(), kaynak)][:2]
    return (iyi or YEDEK), (cevap.get("not") or "").strip(), bool(cevap.get("spam"))


def cevap_linki(tweet_id: str, metin: str) -> str:
    """X'in cevap penceresini taslak yazılmış halde açan bağlantı (web intent): telefonda tek dokunuş, kopyalama yok.
    Gönder düğmesine sahibi basar; bot hiçbir şey paylaşmaz (D3)."""
    return f"https://x.com/intent/tweet?in_reply_to={tweet_id}&text={quote(metin, safe='')}"


def taslak_satirlari(tweet_id: str, taslaklar: list[str], ekler: list[tuple[str, str]] = ()) -> list[str]:
    """Her taslak: metni görünür, altında "bu cevapla aç" bağlantısı. ekler: (etiket, metin) ek seçenekler."""
    satirlar = []
    for n, t in enumerate(taslaklar, 1):
        satirlar += [f"**{n}.** {t}", f"[✍️ Bu cevapla aç]({cevap_linki(tweet_id, t)})", ""]
    for etiket, t in ekler:  # ek seçenekte bağlantı (ör. kart postumuz) metinde gösterilmez, cevaba eklenir
        satirlar += [f"**{etiket}** {t.split(chr(10) + chr(10))[0]}", f"[✍️ Bu cevapla aç]({cevap_linki(tweet_id, t)})", ""]
    return satirlar


def bildirim(yorum: dict, taslak: list[str], not_: str, spam: bool, hesap_adi: str) -> str:
    satirlar = [f"### 💬 @{yorum.get('kullanici') or '?'} → @{hesap_adi}",
                f"> {(yorum.get('metin') or '').strip()}".replace("\n", "\n> "), ""]
    if yorum.get("bizim"):
        satirlar += [f"<sub>Bizim post: {yorum['bizim'][:160].replace(chr(10), ' ')}…</sub>", ""]
    if not_:
        satirlar += [f"📝 {not_}" + (" (spam gibi)" if spam and "cevap vermesen" not in not_ else ""), ""]
    satirlar += [f"👀 [Yorumu X'te gör](https://x.com/i/web/status/{yorum['id']})", "",
                 "Taslaklar: **✍️ Bu cevapla aç**'a dokun, X'te cevap hazır açılır; istersen düzelt, Gönder'e bas.", ""]
    satirlar += taslak_satirlari(yorum["id"], taslak)
    return "\n".join(satirlar).rstrip()


def kontrol(x, gh, ayar, simdi: datetime, hesap: str = "kalkylerat", client=None, yaz=print) -> int:
    """Yeni yorumları sorar ve sahibine taslaklarla bildirir; bildirilen yorum sayısı. Hiçbir şey paylaşmaz (D3)."""
    veri = yukle()
    h = veri.setdefault(hesap, {})
    if h.get("son_kontrol") and simdi < datetime.fromisoformat(h["son_kontrol"]) + timedelta(minutes=KONTROL_DK):
        return 0
    if not h.get("me"):
        h["me"], h["kullanici"] = x.ben()
    ilk = (simdi - timedelta(days=ILK_GUN)).isoformat(timespec="seconds") if not h.get("since_id") else None
    yeni = [t for t in x.bahsedenler(h["me"], since_id=h.get("since_id"), baslangic=ilk) if t.get("yazar") != h["me"]]
    h["son_kontrol"] = simdi.isoformat(timespec="seconds")
    if not yeni:
        kaydet(veri)
        return 0
    yeni = sorted(yeni, key=lambda t: int(t["id"]))[:EN_FAZLA]  # eskiden yeniye; fazlası sonraki kontrole
    tarih = simdi.date().isoformat()
    if (h.get("issue") or {}).get("tarih") != tarih:
        govde = ((f"@{ayar.alarm_kime} " if getattr(ayar, "alarm_kime", "") else "")
                 + f"Bugün @{h['kullanici']} postlarına gelen yorumlar ve etiketlemeler. Her biri için 2 hazır cevap: "
                 "**✍️ Bu cevapla aç**'a dokun, X'te cevap hazır açılır, Gönder'e sen basarsın. Bot hiçbir zaman "
                 "kendisi cevap atmaz (X kuralı). Aynı metni iki kişiye gönderme.")
        h["issue"] = {"tarih": tarih, "no": gh.issue_ac(f"💬 Yorumlar @{h['kullanici']} {tarih}", govde,
                                                         ETIKETLER.get(hesap, "yorum-kiti"))}
    for t in yeni:
        taslak, not_, spam = taslaklar(t, hesap, client, ayar, yaz)
        gh.yorum(h["issue"]["no"], (f"@{ayar.alarm_kime} " if getattr(ayar, "alarm_kime", "") else "")
                 + bildirim(t, taslak, not_, spam, h["kullanici"]))
        h["since_id"] = t["id"]
        kaydet(veri)  # bildirildi: tekrar gelmesin
    yaz(f"Yorum kiti (@{h['kullanici']}): {len(yeni)} yeni yorum bildirildi.")
    return len(yeni)
