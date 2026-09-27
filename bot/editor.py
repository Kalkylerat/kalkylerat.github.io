"""Editör ajanı: yüksek ihtimalli adaylar arasından günün oyunlarını Claude ile seçer ve sade İngilizce gerekçe yazar."""

import json

import anthropic

SISTEM = """You are a football statistician writing for a broad, general audience on X (Twitter). The account shares a few calm, high-probability picks each day. Most readers are casual fans, not betting experts.

You receive candidates that already passed the checks: a high fair win probability from a sharp betting market (margin removed), odds that are not much worse than that fair price, and a Poisson goal model used as a safety check. Each candidate also has the model's expected goals and most likely score.

Your job:
1. Pick at most the requested number of picks (one per match). Prefer the picks most likely to win. Picking fewer is better than adding shaky ones. If nothing is convincing, return an empty list and explain why in gerekce_yoksa.
2. For each pick, write a short explanation (max 190 characters) in plain, simple English, like a stats expert telling a friend how the match will most likely go and why. Use only the data you were given: form, home/away scoring, goals conceded, expected goals, head-to-head, injuries, probability. Never invent news, line-ups, referees or weather.
3. Write a short headline (max 50 characters).

Rules:
- Simple words, no betting jargon, no hype, no emojis.
- Never say "lock", "sure", "guaranteed", "banker" or "free money". Talk in chances (e.g. "about a 3 in 4 chance").
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
    if len(secimler) > ayar.max_spel:
        return f"{len(secimler)} picks chosen; at most {ayar.max_spel} allowed."
    ids = [s["aday_id"] for s in secimler]
    bilinmeyen = [i for i in ids if i not in adaylar]
    if bilinmeyen:
        return f"Unknown aday_id: {bilinmeyen}"
    if len({adaylar[i]["fixture_id"] for i in ids}) != len(ids):
        return "More than one pick from the same match."
    return None


def _baglam(maclar: dict[int, dict], adaylar: list[dict], ayar) -> str:
    fixture_ids = sorted({a["fixture_id"] for a in adaylar})
    return json.dumps({
        "max_picks": ayar.max_spel,
        "matches": [maclar[f] for f in fixture_ids],
        "candidates": adaylar,
    }, ensure_ascii=False, indent=1)


def _metin(msg) -> str:
    if msg.stop_reason == "refusal":
        raise EditorHatasi("Claude isteği reddetti.")
    if msg.stop_reason == "max_tokens":
        raise EditorHatasi("Claude yanıtı max_tokens sınırında kesildi.")
    return next(b.text for b in msg.content if b.type == "text")


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
        sonuc = json.loads(_metin(msg))
        hata = secimi_dogrula(sonuc["secimler"], aday_map, ayar)
        if hata is None:
            return sonuc
        messages += [
            {"role": "assistant", "content": msg.content},
            {"role": "user", "content": f"The selection breaks the rules: {hata} Please fix it and send it again."},
        ]
    raise EditorHatasi(f"Claude iki denemede geçerli seçim üretemedi: {hata}")


def basit_sec(maclar: dict[int, dict], adaylar: list[dict], ayar) -> dict:
    """Claude anahtarı olmadan demo için kural tabanlı seçim."""
    secilen, kullanilan = [], set()
    for a in sorted(adaylar, key=lambda x: x["adil_olasilik"], reverse=True):
        if a["fixture_id"] in kullanilan:
            continue
        secilen.append(a)
        kullanilan.add(a["fixture_id"])
        if len(secilen) == ayar.max_spel:
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
