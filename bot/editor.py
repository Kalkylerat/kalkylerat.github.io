"""Editör ajanı: yüksek ihtimalli adaylar arasından günün oyunlarını Claude ile seçer ve sade İngilizce gerekçe yazar."""

import json
import re

import anthropic

# Claude'a gönderilmeyen alanlar: bahisçi adları tweetlere sızmasın.
GIZLI_ALANLAR = ("adil_kaynak", "oranlar", "bolag")

SISTEM = """You are a football statistician running a public, virtual EUR 10,000 bankroll on X (Twitter). Each pick risks 1% of the bank. The audience is broad: casual fans, not betting experts.

Candidates already passed the data checks. Each has:
- tur "guvenli" (safe): high fair win chance from a sharp betting market (margin removed), odds close to fair.
- tur "deger" (value): the odds are higher than the real chance, so it grows the bank over time even if it wins less often.
- the Poisson model's expected goals, most likely score and (for goal and half-time markets) its own probability.
Markets include match result, double chance, goal lines, both teams to score, half-time result, first-half goals and corners.

Your job:
1. Pick at most the requested number of picks. Mix safe and value picks when both are good; prefer quality over quantity. Spread picks across different matches (this also allows a combo); take a second pick from the same match only when it is clearly stronger than the best pick from another match. Two picks from the same match are shown together as one bet builder with one estimated price; in that case write the explanation on the first of them and leave yorum empty on the second. If nothing is convincing, return an empty list and explain why in gerekce_yoksa.
2. For each pick, write a short explanation (max 150 characters, one or two short sentences) in plain, simple English, like a stats expert telling a friend how the match will most likely go and why. Use only the data given (form, home/away scoring, goals conceded, expected goals, head-to-head, injuries, chances). Do not explain what the market means (everyone knows "Under 1.5 goals" or "Double chance X2"); explain why the pick is likely. Never invent news, line-ups, referees, weather or corner statistics that are not in the data; for corner picks, lean on the market chance and the expected attacking pressure.
3. Write a short headline (max 50 characters).

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
        "baslik": {"type": "string"},
        "gerekce_yoksa": {"type": "string"},
    },
    "required": ["secimler", "baslik", "gerekce_yoksa"],
    "additionalProperties": False,
}


class EditorHatasi(RuntimeError):
    pass


def secimi_dogrula(secimler: list[dict], adaylar: dict[str, dict], ayar) -> str | None:
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
    return None


def _baglam(maclar: dict[int, dict], adaylar: list[dict], ayar) -> str:
    fixture_ids = sorted({a["fixture_id"] for a in adaylar})
    return json.dumps({
        "max_picks": ayar.max_oyun,
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
        hata = secimi_dogrula(sonuc["secimler"], aday_map, ayar)
        if hata is None:
            return sonuc
        messages += [
            {"role": "assistant", "content": msg.content},
            {"role": "user", "content": f"The selection breaks the rules: {hata} Please fix it and send it again."},
        ]
    raise EditorHatasi(f"Claude iki denemede geçerli seçim üretemedi: {hata}")


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
        "secimler": [{
            "aday_id": s["aday_id"],
            "yorum": (f'Expected goals {s["beklenen_gol"][0]:.1f}–{s["beklenen_gol"][1]:.1f}, most likely score '
                      f'{s["olasi_skor"]}. The market gives this about a {100 * s["adil_olasilik"]:.0f}% chance.'),
        } for s in secilen],
    }
