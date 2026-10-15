"""Prompt Proof yazarı (SOZLESME F): konu seçimi (triage) ve aynı doğrulanmış kayıttan iki ayrı parça yazma.

X uzmanı: 5-9 postluk flood, ilk post tek başına durur. Instagram uzmanı: 5-8 slaytlık carousel ve caption
(kaydetme ve gönderme hedefi). İkisi de YALNIZCA olgu kaydındaki rakam ve isimleri kullanabilir; kural dışı
metin `flood_denetci` tarafından geri çevrilir ve yazara sorunlarla birlikte geri gönderilir."""

import json
import re

from . import config, flood_denetci
from .direktor import _cagir

SES_REHBERI = config.ROOT / "marka" / "PROMPT_PROOF.md"
DENEME = 3

# Evergreen (Library) temaları: sırayla, son 30 günde işlenmeyenden seçilir. Hepsi güvenli alanda, gerçek bir iş sorunu.
KUTUPHANE = [
    "Turn a messy meeting transcript into a short list of action items with owners",
    "Summarize a long email thread into what was decided and what is still open",
    "Rewrite a rambling message so it is clear and polite in three sentences",
    "Prepare for a job interview: turn a job post into the five questions most likely to be asked",
    "Turn a long article into a one-page study sheet with the key points",
    "Compare two product pages and list the real differences in plain words",
    "Draft a firm but friendly reply to a customer complaint using the facts provided",
    "Turn rough notes into a clear agenda for a 30 minute meeting",
    "Explain a confusing contract clause in plain English and list the questions to ask the other side",
    "Plan a week of meals around a budget and the ingredients already at home",
    "Turn a spreadsheet column of free-text feedback into the top five themes",
    "Rewrite a CV bullet list so each line shows a result instead of a duty",
    "Break a big project into a first-week checklist with the smallest next step highlighted",
    "Check a text for tone problems before sending it to your boss",
    "Create a packing checklist for a trip from the destination and the length of stay",
    "Explain a technical error message and list the first three things to check",
    "Turn a lecture transcript into ten flashcards",
    "Draft three subject lines for an email and explain why each might work",
    "Rewrite a paragraph for a ten year old without losing the main point",
    "Make a decision table for a choice between two options with weighted criteria",
]

TRIAGE_SEMASI = {"type": "object", "additionalProperties": False, "required": ["secimler"],
                 "properties": {"secimler": {"type": "array", "items": {
                     "type": "object", "additionalProperties": False, "required": ["indeks", "tur", "problem", "fikir"],
                     "properties": {"indeks": {"type": "integer"}, "tur": {"type": "string", "enum": ["fix", "news", "atla"]},
                                    "problem": {"type": "string"}, "fikir": {"type": "string"}}}}}}
TRIAGE_SISTEMI = """You pick topics for an AI-focused social media account ("Prompt Proof"). You get numbered trending items.
For each item decide:
- "news": it is real AI or AI-adjacent news (models, products, research, policy for AI tools) worth explaining.
- "fix": the item points to an everyday problem a person could solve with an AI assistant (a prompt they paste). Write
  "problem" as the plain question people search ("why is my phone battery draining after the update") and "fikir" as one
  line on how an AI assistant helps.
- "atla": anything else.
Always "atla" topics about health or medicine, law, investing or money advice, politics or elections, deaths, attacks,
disasters, or allegations about named people. Pick at most 3 items that are not "atla". For "news" leave problem and fikir empty."""

YAZAR_SEMASI = {"type": "object", "additionalProperties": False,
                "required": ["hook_a", "hook_b", "devam", "ig_slaytlar", "ig_caption", "ig_etiketler"],
                "properties": {
                    "hook_a": {"type": "string"}, "hook_b": {"type": "string"},
                    "devam": {"type": "array", "items": {"type": "string"}},
                    "ig_slaytlar": {"type": "array", "items": {
                        "type": "object", "additionalProperties": False, "required": ["baslik", "metin", "tur", "komut"],
                        "properties": {"baslik": {"type": "string"}, "metin": {"type": "string"},
                                       "tur": {"type": "string", "enum": ["icerik", "komut"]}, "komut": {"type": "string"}}}},
                    "ig_caption": {"type": "string"}, "ig_etiketler": {"type": "array", "items": {"type": "string"}}}}

YAZAR_SISTEMI = """You write for the X and Instagram accounts "Prompt Proof" from ONE verified record. You write TWO different pieces:
X: a flood. "hook_a" is the first post (problem first), "hook_b" is an alternative first post (result first). "devam" are the
following 4-8 posts. Every post stands alone, max 270 characters, plain text.
Instagram: a carousel of 5-8 slides ("ig_slaytlar": a short title max 60 chars and a text max 220 chars each; slide 1 is the
cover hook, the slide that shows the prompt has tur "komut" and the prompt in "komut"; the last slide asks to save or send
it to a friend who has this problem) plus "ig_caption" (max 600 chars; the first line has the plain words people search for;
no hashtags in the caption) and up to 3 relevant "ig_etiketler" (each starts with #).

Hard rules:
- Use ONLY facts, names and numbers from the record. Never add a number, date, price, version or name that is not in it.
  List sizes like "5 steps" are fine. If the record has no fact for a claim, do not make the claim.
- If the record has a "tested" block, say plainly it was tested: one X post contains "Tested with <model name>" and the
  Instagram cover or caption says "Tested". State the limit honestly. Show the prompt compactly in one X post (max 260 chars,
  you may shorten it, keep its meaning) and in full on the Instagram slide. Quote at most two short lines of the real output.
- No links, no "@", no emojis, no hashtags in X posts except at most one in the last post if clearly relevant.
- No hype ("game-changer", "insane", "mind-blowing", "changes everything"), no engagement bait ("RT if", "reply YES"),
  no AI-sounding patterns ("Here's what", "It's not X, it's Y", "Let that sink in", "The result?"), at most one long dash.
- Never claim personal experience, clients, or authority. Say "we ran it", never "I have used this for months".
- End the X flood with ONE specific ask: save it, or follow for the next tested fix. Not both.
- Sound like a person: short sentences, plain words, one honest limit per piece.
"""


def _ses() -> str:
    try:
        metin = SES_REHBERI.read_text(encoding="utf-8")
    except OSError:
        return "Voice: calm, plain, specific. A careful friend who tests things before recommending them."
    bolum = metin.split("## Who is speaking", 1)[-1].split("\n## ", 1)[0]
    return "Voice notes:\n" + bolum.strip()[:2500]


def triage(client, ayar, adaylar: list[dict], en_fazla: int = 12) -> list[dict]:
    """[{aday, tur ('fix'|'news'), problem, fikir}] en iyi ilk 3. Konular zaten puana göre sıralı gelir."""
    liste = adaylar[:en_fazla]
    metin = "\n".join(f"{i}. {a['baslik']} | {' / '.join(k.get('ad', '') for k in a['kaynaklar'][:3])} | "
                      f"{(a['kaynaklar'][0].get('ozet') or '')[:140]}" for i, a in enumerate(liste))
    cevap = _cagir(client, [(ayar.hafif_model, "low")], TRIAGE_SISTEMI, metin, TRIAGE_SEMASI, 2000)
    sonuc = []
    for s in cevap.get("secimler", []):
        if s["tur"] != "atla" and 0 <= s["indeks"] < len(liste):
            sonuc.append({"aday": liste[s["indeks"]], "tur": s["tur"], "problem": s["problem"].strip(), "fikir": s["fikir"].strip()})
    return sonuc[:3]


def kutuphane_temasi(islenmis) -> str | None:
    """Evergreen tema: henüz işlenmemiş ilk tema; hepsi işlendiyse en eskisi yeniden."""
    kalan = [t for t in KUTUPHANE if t not in set(islenmis)]
    return kalan[0] if kalan else (list(islenmis)[0] if islenmis else KUTUPHANE[0])


def _yukle(kayit: dict, sorunlar: list[str] | None) -> str:
    d = kayit.get("denendi")
    veri = {"type": kayit["tur"], "topic": kayit["konu"], "facts": [o["metin"] for o in kayit.get("olgular") or []]}
    if d:
        veri["tested"] = {"model_name": flood_denetci.model_adi(d["model"]), "prompt_to_show": d["komut"],
                          "sample_input": d["ornek_girdi"], "real_output": d["cikti"][:1400], "time": d["sure"],
                          "honest_limit": d["sinir"]}
    if sorunlar:
        veri["your_previous_draft_was_rejected_for"] = sorunlar[:12]
    return json.dumps(veri, ensure_ascii=False, indent=1)


def _birlestir(c: dict) -> dict:
    hook_b = (c.get("hook_b") or "").strip()
    return {"bicim": "flood",
            "x": {"postlar": [c["hook_a"].strip()] + [p.strip() for p in c["devam"]],
                  "alternatif_hook": hook_b or None, "link_yaniti": None},
            "ig": {"slaytlar": [{"baslik": s["baslik"].strip(), "metin": s["metin"].strip(), "tur": s["tur"],
                                 "komut": s["komut"].strip()} for s in c["ig_slaytlar"]],
                   "caption": c["ig_caption"].strip(), "etiketler": [e.strip() for e in c["ig_etiketler"]]}}


def yaz(client, ayar, kayit: dict, bugunku_metinler=(), bugunku_ig: int = 0, yaz_=print) -> tuple[dict | None, list[str]]:
    """(flood, sorunlar). En fazla DENEME kez yazar; her red sorunlarıyla birlikte geri gönderilir. Başaramazsa (None, sorunlar)."""
    sorunlar: list[str] = []
    sistem = YAZAR_SISTEMI + "\n" + _ses()
    for i in range(DENEME):
        try:
            c = _cagir(client, [(ayar.model, ayar.effort)], sistem, _yukle(kayit, sorunlar or None), YAZAR_SEMASI, 8000)
        except RuntimeError as e:
            sorunlar = [str(e)]
            continue
        flood = _birlestir(c)
        sorunlar = flood_denetci.denetle(flood, kayit, bugunku_metinler, bugunku_ig)
        if not sorunlar:
            alt = flood["x"]["alternatif_hook"]
            if alt:  # alternatif kanca da aynı kurallardan geçmeli; geçmezse yalnızca A sunulur
                ikinci = {**flood, "x": {**flood["x"], "postlar": [alt] + flood["x"]["postlar"][1:]}}
                if flood_denetci.x_kontrol(ikinci, kayit, bugunku_metinler):
                    flood["x"]["alternatif_hook"] = None
            return flood, []
        yaz_(f"Yazar denemesi {i + 1}/{DENEME} reddedildi: {sorunlar[0]}" + (f" (+{len(sorunlar) - 1})" if len(sorunlar) > 1 else ""))
    return None, sorunlar
