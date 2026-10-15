"""Yorum kiti (SÖZLEŞME D3): hesabın postlarına gelen yeni yorumlar ve etiketlemeler için sahibine kopyalanmaya hazır
cevap taslakları. Günlük bir GitHub issue'su açılır, her yeni yorum oraya sahibini etiketleyen bir yorum olarak düşer
(telefona bildirim). Sahibi bağlantıdan yorumu açar, taslaklardan birini kendi cümlesiyle düzeltip elle atar.

Bot hiçbir zaman kendisi cevap atmaz, beğenmez, takip etmez: X otomasyon kuralları başkalarına otomatik yanıtı
yasaklar (D3). Okuma ücretlidir (dönen post başına): 15 dakikada bir, yalnızca son görülen yorumdan yenileri sorulur."""

import json
import re
from datetime import datetime, timedelta

from . import config

ETIKETLER = {"kalkylerat": "yorum-kiti", "likely": "yorum-kiti-likely", "flood": "yorum-kiti-flood"}  # hesap başına: günlük issue, eskisi kapanır
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


def _flood_sesi() -> str:
    """Prompt Proof (üçüncü hesap) sesi: marka/PROMPT_PROOF.md."""
    try:
        metin = (config.ROOT / "marka" / "PROMPT_PROOF.md").read_text(encoding="utf-8")
    except OSError:
        return "You are Prompt Proof: an AI account that only posts tested fixes. Calm, plain, specific."
    bolum = metin.split("## Who is speaking", 1)[-1].split("\n## ", 1)[0]
    return "You are Prompt Proof (AI fixes and news, English). Voice notes:\n" + bolum.strip()[:2500]


SISTEM = """You draft replies that the account owner will read, edit and post BY HAND on X. You never post anything.
Write 3 different short reply drafts to the comment below, in the account's voice, in plain English.

Hard rules:
- Max 200 characters each. No links, no "@" mentions, no hashtags, no emojis except at most one.
- Use only facts from our post and the comment. Never invent stats, news, line-ups or results. If a number is needed
  and it is not in our post, don't use a number.
- We give chances, not picks: never say pick, tip, lock, guaranteed, sure, bet now, or that we were right or wrong.
- No betting advice, no bookmaker names. Never argue, never mock. If the comment is hostile, stay calm and short.
- Sound like a person: no "Great question!", no "Here's", no "Honestly,", no corporate words.
- Draft 1: answers the comment directly. Draft 2: adds one number or detail from our post. Draft 3: asks the person a
  specific question back (replies keep the conversation going).

Also set "not" to ONE short sentence in Turkish for the owner: what the comment says, and "cevap vermesen de olur" if
it is spam, a bot, abuse or a scam link. Set "spam" true in that case."""

SEMA = {"type": "object", "additionalProperties": False, "required": ["taslaklar", "not", "spam"],
        "properties": {"taslaklar": {"type": "array", "items": {"type": "string"}},
                       "not": {"type": "string"}, "spam": {"type": "boolean"}}}

YEDEK = ["Thanks for reading! Which number on the card surprised you most?",
         "Appreciate it. All the chances are on the card, and we quote the result under it after full time.",
         "Good point. How would you read this one?"]


def yukle() -> dict:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def kaydet(veri: dict) -> None:
    DOSYA.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def uygun(taslak: str, kaynak: str) -> bool:
    """Taslak kurala uyuyor mu: kısa, linksiz, etiketsiz, seçim/kesinlik dili yok, kaynakta olmayan sayı yok."""
    from .denetci import _KESINLIK, _LINK, _SECIM_DILI
    from .direktor import sayilar_dogru, yz_izi
    return bool(taslak) and len(taslak) <= 240 and not _LINK.search(taslak) and "#" not in taslak \
        and not _SECIM_DILI.search(taslak) and not _KESINLIK.search(taslak) and not yz_izi(taslak) \
        and not re.search(r"\b(picks?|tips?|bet now|for sure|were right|right about)\b", taslak, re.IGNORECASE) and sayilar_dogru(taslak, kaynak)


def taslaklar(yorum: dict, hesap: str, client=None, ayar=None, yaz=print) -> tuple[list[str], str, bool]:
    """(taslaklar, sahibine not, spam mı). Claude yoksa ya da taslaklar kurala uymazsa hazır kalıplar."""
    kaynak = (yorum.get("bizim") or "") + "\n" + (yorum.get("metin") or "")
    if client is None or ayar is None:
        return YEDEK, "", False
    from .direktor import _cagir
    ses = {"likely": _likely_sesi, "flood": _flood_sesi}.get(hesap, lambda: SESLER["kalkylerat"])()
    icerik = json.dumps({"our_post": yorum.get("bizim") or "(not available: the comment may be a mention)",
                         "comment": yorum.get("metin"), "commenter": yorum.get("kullanici")}, ensure_ascii=False, indent=1)
    try:
        cevap = _cagir(client, [(ayar.direktor_model, "low"), (ayar.claude_model, "low")], ses + "\n\n" + SISTEM,
                       icerik, SEMA, 2000)
    except Exception as e:
        yaz(f"Yorum kiti: taslak yazılamadı ({e}); hazır kalıplar kullanıldı.")
        return YEDEK, "", False
    iyi = [t.strip() for t in cevap.get("taslaklar") or [] if uygun(t.strip(), kaynak)][:3]
    return (iyi or YEDEK), (cevap.get("not") or "").strip(), bool(cevap.get("spam"))


def bildirim(yorum: dict, taslak: list[str], not_: str, spam: bool, hesap_adi: str) -> str:
    satirlar = [f"### 💬 @{yorum.get('kullanici') or '?'} → @{hesap_adi}",
                f"> {(yorum.get('metin') or '').strip()}".replace("\n", "\n> "), ""]
    if yorum.get("bizim"):
        satirlar += [f"<sub>Bizim post: {yorum['bizim'][:160].replace(chr(10), ' ')}…</sub>", ""]
    if not_:
        satirlar += [f"📝 {not_}" + (" (spam gibi)" if spam and "cevap vermesen" not in not_ else ""), ""]
    satirlar += [f"👉 [Yorumu X'te aç ve elle cevapla](https://x.com/i/web/status/{yorum['id']})", "",
                 "Taslaklar (kopyala, kendi cümlenle değiştir):"]
    satirlar += [f"```\n{t}\n```" for t in taslak]
    return "\n".join(satirlar)


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
                 + f"Bugün @{h['kullanici']} postlarına gelen yorumlar ve etiketlemeler. Her biri için 3 cevap taslağı: "
                 "bağlantıdan yorumu aç, birini kendi cümlenle düzeltip **elle** cevapla. Bot hiçbir zaman kendisi "
                 "cevap atmaz (X kuralı). Aynı metni iki kez yapıştırma.")
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
