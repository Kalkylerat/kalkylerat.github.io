"""Editör ajanı: yüksek ihtimalli adaylar arasından günün oyunlarını Claude ile seçer ve sade İngilizce gerekçe yazar."""

import json
import re

import anthropic

# Claude'a gönderilmeyen alanlar: bahisçi adları tweetlere sızmasın.
GIZLI_ALANLAR = ("adil_kaynak", "oranlar", "bolag")

SISTEM = """You are a football statistician running a public, virtual EUR 10,000 bankroll on X (Twitter). The account posts coupons; each coupon risks 1% of the bank. The audience is broad: casual fans, not betting experts.

Candidates already passed the data checks. Each has:
- tur "guvenli" (high-chance): high fair win chance (at least 65%) from a sharp betting market (margin removed), and odds close to fair (at most a normal bookmaker margin below it).
- tur "deger" (value): the odds are higher than the real chance, so it grows the bank over time even if it wins less often.
- the Poisson model's expected goals, most likely score and (for goal and half-time markets) its own probability.
Markets include match result, double chance, goal lines, both teams to score, half-time result, first-half goals and corners.

Your job:
1. Pick at most max_picks picks and group them into at most max_coupons coupons. A coupon is either one pick on its own (typically a value pick, odds around 2.0–2.5) or a combination of 2–3 picks from different matches (total odds around 2.0–3.5). Followers check the account every day and engage most with variety, so post at least one coupon whenever the candidates allow a sound one: aim for a main coupon with total odds of at least 2.0 (ideally 2.0–2.5), typically 3 high-chance picks from different matches, or 2 high-chance picks plus a value pick. When the candidates allow, add one or two more coupons with a different character, for example a goals/corners coupon (goal lines, both teams to score, first-half goals, corners) or a single value pick around 2.0–2.5; use each match in only one coupon. Only when the candidates cannot reach 2.0 soundly (few matches that day), post the best sound combination instead of posting nothing. Never go above about 3.5 total odds. Every coupon risks 1% of the bank, so only build coupons you would really back; never add a weak coupon just to have more. Every pick must be in exactly one coupon. Take a second pick from the same match only when it is clearly stronger than the best pick from another match; two picks from the same match become one bet builder with one estimated price, must be in the same coupon, and the explanation goes on the first of them (leave yorum empty on the second). If nothing is convincing, return empty lists and explain why in gerekce_yoksa.
2. For each pick, write a short explanation (max 150 characters, one or two short sentences) in plain, simple English, like a stats expert telling a friend how the match will most likely go and why. Use only the data given (form, home/away scoring, goals conceded, expected goals, head-to-head, injuries, chances). Do not explain what the market means (everyone knows "Under 1.5 goals" or "Double chance X2"); explain why the pick is likely. Never invent news, line-ups, referees, weather or corner statistics that are not in the data; for corner picks, lean on the market chance and the expected attacking pressure.
3. Write a short headline (max 50 characters).
4. Write 3 to 5 reply suggestions (yanit_onerileri) that the account owner will post BY HAND under other people's tweets about today's matches in the data (prefer the best-known teams and leagues). Each is max 200 characters: one genuinely useful, specific stat insight about that match in plain English (form, goals, head-to-head, expected goals), friendly and conversational, like a fan who knows the numbers. It may end with our view as a chance ("we make it about 70%"). No "@", no hashtags, no links, no bookmaker names, no "bet"/"tip"/"lock", no self-promotion ("follow us"). Use a different match for each when possible. Only use facts from the data.

Rules:
- Simple words, no betting jargon, no hype, no emojis.
- Never say "lock", "sure", "guaranteed", "banker" or "free money". Talk in chances (e.g. "about a 3 in 4 chance").
- Never name bookmakers or betting sites, never use "@", hashtags or links.
- Copy aday_id exactly from the candidate."""

SEMA = {
    "type": "object",
    "properties": {
        "secimler": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "aday_id": {"type": "string"},
                    "yorum": {"type": "string"},
                },
                "required": ["aday_id", "yorum"],
                "additionalProperties": False,
            },
        },
        "kuponlar": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"aday_idler": {"type": "array", "items": {"type": "string"}}},
                "required": ["aday_idler"],
                "additionalProperties": False,
            },
        },
        "baslik": {"type": "string"},
        "gerekce_yoksa": {"type": "string"},
        "yanit_onerileri": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"fixture_id": {"type": "integer"}, "metin": {"type": "string"}},
                "required": ["fixture_id", "metin"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["secimler", "kuponlar", "baslik", "gerekce_yoksa", "yanit_onerileri"],
    "additionalProperties": False,
}


class EditorHatasi(RuntimeError):
    pass


def secimi_dogrula(secimler: list[dict], adaylar: dict[str, dict], ayar, kuponlar: list[dict] | None = None) -> str | None:
    if len(secimler) > ayar.max_oyun:
        return f"{len(secimler)} picks chosen; at most {ayar.max_oyun} allowed."
    ids = [s["aday_id"] for s in secimler]
    bilinmeyen = [i for i in ids if i not in adaylar]
    if bilinmeyen:
        return f"Unknown aday_id: {bilinmeyen}"
    if len(set(ids)) != len(ids):
        return "The same pick is listed twice."
    maclar = [adaylar[i]["fixture_id"] for i in ids]
    if any(maclar.count(m) > ayar.max_oyun_mac_basina for m in maclar):
        return f"More than {ayar.max_oyun_mac_basina} picks from the same match."
    return kuponlari_dogrula(secimler, kuponlar or [], adaylar, ayar)


def kuponlari_dogrula(secimler: list[dict], kuponlar: list[dict], adaylar: dict[str, dict], ayar) -> str | None:
    ids = [s["aday_id"] for s in secimler]
    if not ids:
        return None if not kuponlar else "Coupons without picks."
    if len(kuponlar) > ayar.max_kupon:
        return f"{len(kuponlar)} coupons; at most {ayar.max_kupon} allowed."
    kupondaki = [i for k in kuponlar for i in k["aday_idler"]]
    if sorted(kupondaki) != sorted(ids):
        return "Every pick must be in exactly one coupon, and coupons may only contain chosen picks."
    for k in kuponlar:
        if not k["aday_idler"]:
            return "Empty coupon."
        if len({adaylar[i]["fixture_id"] for i in k["aday_idler"]}) > 3:
            return "A coupon may combine at most 3 matches."
    hangi = {i: n for n, k in enumerate(kuponlar) for i in k["aday_idler"]}
    for mac in {adaylar[i]["fixture_id"] for i in ids}:
        if len({hangi[i] for i in ids if adaylar[i]["fixture_id"] == mac}) > 1:
            return "Picks from the same match must be in the same coupon (they form one bet builder)."
    return None


def _baglam(maclar: dict[int, dict], adaylar: list[dict], ayar) -> str:
    fixture_ids = sorted({a["fixture_id"] for a in adaylar})
    return json.dumps({
        "max_picks": ayar.max_oyun,
        "max_coupons": ayar.max_kupon,
        "max_picks_per_match": ayar.max_oyun_mac_basina,
        "matches": [maclar[f] for f in fixture_ids],
        "candidates": [{k: v for k, v in a.items() if k not in GIZLI_ALANLAR} for a in adaylar],
    }, ensure_ascii=False, indent=1)


def _metin(msg) -> str:
    if msg.stop_reason == "refusal":
        raise EditorHatasi("Claude isteği reddetti.")
    if msg.stop_reason == "max_tokens":
        raise EditorHatasi("Claude yanıtı max_tokens sınırında kesildi.")
    metin = next((b.text for b in msg.content if b.type == "text"), None)
    if metin is None:
        raise EditorHatasi("Claude yanıtında metin yok.")
    return metin


def temiz_yorum(yorum: str, yasakli: list[str]) -> str:
    """Bahisçi adı, "@", hashtag ya da link içeren cümleleri atar (X kuralları ve bahis reklamı yasağı)."""
    cumleler = re.split(r"(?<=[.!?])\s+", yorum.strip())
    kotu = [y.lower() for y in yasakli] + ["@", "#", "http", "www."]
    return " ".join(c for c in cumleler if c and not any(k in c.lower() for k in kotu))


def claude_ile_sec(maclar: dict[int, dict], adaylar: list[dict], ayar, client=None) -> dict:
    client = client or anthropic.Anthropic()
    aday_map = {a["aday_id"]: a for a in adaylar}
    messages = [{"role": "user", "content": "Today's data:\n" + _baglam(maclar, adaylar, ayar)}]
    hata = None
    for _ in range(2):
        with client.messages.stream(
            model=ayar.claude_model,
            max_tokens=32000,
            system=SISTEM,
            messages=messages,
            output_config={"effort": ayar.claude_effort, "format": {"type": "json_schema", "schema": SEMA}},
        ) as stream:
            msg = stream.get_final_message()
        try:
            sonuc = json.loads(_metin(msg))
        except json.JSONDecodeError as e:
            raise EditorHatasi(f"Claude geçersiz JSON döndürdü: {e}") from e
        hata = secimi_dogrula(sonuc["secimler"], aday_map, ayar, sonuc["kuponlar"])
        if hata is None:
            return sonuc
        messages += [
            {"role": "assistant", "content": msg.content},
            {"role": "user", "content": f"The selection breaks the rules: {hata} Please fix it and send it again."},
        ]
    raise EditorHatasi(f"Claude iki denemede geçerli seçim üretemedi: {hata}")


_BAHIS_DILI = re.compile(r"\b(bet|bets|betting|tip|tips|tipster|lock|guaranteed|follow)\b", re.IGNORECASE)


def yanit_onerilerini_hazirla(oneriler: list[dict], maclar: dict[int, dict], yasakli: list[str]) -> list[dict]:
    """Elle atılacak yanıt önerilerini süzer: yalnızca verideki maçlar, kurallara uyan metin, en fazla 5.
    Her öneriye o maçın X araması eklenir (sahibi ilgili tweetleri bulup yanıtlasın)."""
    from urllib.parse import quote
    temiz = []
    for o in oneriler:
        m = maclar.get(o.get("fixture_id"))
        metin = temiz_yorum(o.get("metin") or "", yasakli)
        if not m or not metin or len(metin) > 240 or _BAHIS_DILI.search(metin):
            continue
        temiz.append({"mac": f'{m["ev"]} v {m["dep"]}', "metin": metin,
                      "arama": f'https://x.com/search?q={quote(m["ev"] + " " + m["dep"])}&f=live'})
    return temiz[:5]


def basit_sec(maclar: dict[int, dict], adaylar: list[dict], ayar) -> dict:
    """Claude anahtarı olmadan demo için kural tabanlı seçim: maç başına bir oyun, en yüksek ihtimal önce."""
    secilen, kullanilan = [], set()
    for a in sorted(adaylar, key=lambda x: x["adil_olasilik"], reverse=True):
        if a["fixture_id"] in kullanilan:
            continue
        secilen.append(a)
        kullanilan.add(a["fixture_id"])
        if len(secilen) == ayar.max_oyun:
            break
    return {
        "baslik": "Today's picks",
        "gerekce_yoksa": "" if secilen else "No picks with a high enough chance today.",
        "kuponlar": [{"aday_idler": [s["aday_id"] for s in secilen]}] if secilen else [],
        "yanit_onerileri": [{
            "fixture_id": s["fixture_id"],
            "metin": (f'The numbers point one way here: expected goals around {s["beklenen_gol"][0]:.1f}–{s["beklenen_gol"][1]:.1f}, '
                      f'most likely {s["olasi_skor"]}. We make it about a {100 * s["adil_olasilik"]:.0f}% chance.'),
        } for s in secilen],
        "secimler": [{
            "aday_id": s["aday_id"],
            "yorum": (f'Expected goals {s["beklenen_gol"][0]:.1f}–{s["beklenen_gol"][1]:.1f}, most likely score '
                      f'{s["olasi_skor"]}. The market gives this about a {100 * s["adil_olasilik"]:.0f}% chance.'),
        } for s in secilen],
    }
