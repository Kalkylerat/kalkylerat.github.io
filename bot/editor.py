"""Editör ajanı: değerli adaylar arasından günün tekli oyunlarını Claude ile seçer ve İsveççe gerekçe yazar."""

import json

import anthropic

from .tweets import sayi

SISTEM = """Du är en datadriven, ärlig fotbollsanalytiker som skriver på svenska för ett X-konto (Twitter) med speltips. Kontots löfte: stabila singelspel med hög sannolikhet, inga skrällar, inga lotterikuponger, full transparens.

Du får kandidater som redan klarat kontrollerna: hög rättvis sannolikhet enligt en skarp marknad (marginal borträknad), ett odds hos ett svensklicensierat spelbolag som inte är mycket sämre än det rättvisa priset, och en Poisson-målmodell som säkerhetskontroll.

Din uppgift:
1. Välj högst det antal spel som anges (singlar, ett per match). Prioritera de spel som med störst sannolikhet går in. Välj hellre färre än att ta med osäkra spel. Om inget känns tillräckligt säkert, returnera en tom lista och förklara varför i gerekce_yoksa.
2. Skriv för varje spel en kort motivering på svenska (max 200 tecken) som bara bygger på den data du fått: form, hemma/borta-målsnitt, förväntade mål, inbördes möten, skador, sannolikhet. Hitta inte på något som inte står i datan (laguttagningar, nyheter, domare, väder).
3. Skriv en kort rubrik (max 50 tecken).

Regler:
- Använd aldrig ord som "säker", "spik", "garanterad" eller "gratis pengar". Använd sannolikhetsspråk (t.ex. "cirka 72 % chans").
- aday_id ska kopieras exakt från kandidatens aday_id."""

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
        return f"{len(secimler)} spel valda; högst {ayar.max_spel} tillåts."
    ids = [s["aday_id"] for s in secimler]
    bilinmeyen = [i for i in ids if i not in adaylar]
    if bilinmeyen:
        return f"Okänt aday_id: {bilinmeyen}"
    if len({adaylar[i]["fixture_id"] for i in ids}) != len(ids):
        return "Mer än ett spel från samma match."
    return None


def _baglam(maclar: dict[int, dict], adaylar: list[dict], ayar) -> str:
    fixture_ids = sorted({a["fixture_id"] for a in adaylar})
    return json.dumps({
        "max_antal_spel": ayar.max_spel,
        "matcher": [maclar[f] for f in fixture_ids],
        "kandidater": adaylar,
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
    messages = [{"role": "user", "content": "Dagens data:\n" + _baglam(maclar, adaylar, ayar)}]
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
            {"role": "user", "content": f"Urvalet bryter mot reglerna: {hata} Rätta och skicka igen."},
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
        "baslik": "Dagens spel",
        "gerekce_yoksa": "" if secilen else "Inga tillräckligt säkra spel idag.",
        "secimler": [{
            "aday_id": s["aday_id"],
            "yorum": (f'Förväntade mål {sayi(s["beklenen_gol"][0], 1)}–{sayi(s["beklenen_gol"][1], 1)}. '
                      f'Rättvis sannolikhet {s["adil_olasilik"] * 100:.0f} %, rättvist odds {sayi(s["adil_oran"])} '
                      f'mot {sayi(s["oran"])} hos {s["bolag"]}.'),
        } for s in secilen],
    }
