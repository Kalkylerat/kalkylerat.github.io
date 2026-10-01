"""Denetçi: kupon onaya gitmeden önce seçimlerle her söylenen şeyin tutarlılığını denetler.

İki katman:
1) Kural denetimi (kod, ücretsiz): gerekçedeki ihtimal ifadeleri seçimin ihtimaliyle, tahmin edilen skorlar ve
   beklenen goller seçimin yönüyle uyuşmalı.
2) Yapay zekâ denetimi (hızlı model, kupon taraması başına bir çağrı): seçim, oran, ihtimal, beklenen goller ve gerekçe
   birlikte okunur; çelişki ya da yanıltıcı ifade bulunur.

Sonuç: sorunlu cümle gerekçeden atılır; seçimin kendisi çelişkiliyse o kupon paylaşılmaz."""

import json
import re

import anthropic

from . import model

SISTEM = """You audit a football stats account's coupon before it is posted. For each pick you get the match, the pick,
the odds, our chance, the expected goals per team, the score line shown and the short explanation.

Find only real problems:
- "cumle": a sentence in the explanation that contradicts the pick or the given numbers (e.g. it forecasts a score
  or outcome that would lose the pick, gives a different chance than ours, or misstates the expected goals).
  Quote the sentence exactly as it appears.
- "secim": the pick itself contradicts our own numbers (e.g. Over 2.5 goals while the expected goals add up to 1.6,
  or a team to win while the other team has the higher expected goals).
Past results quoted as history are fine. Wording or style is not a problem. If everything is consistent, return an
empty list."""

SEMA = {
    "type": "object",
    "properties": {"sorunlar": {"type": "array", "items": {
        "type": "object",
        "properties": {"secim": {"type": "integer"}, "tur": {"type": "string", "enum": ["cumle", "secim"]},
                       "cumle": {"type": "string"}, "neden": {"type": "string"}},
        "required": ["secim", "tur", "cumle", "neden"], "additionalProperties": False}}},
    "required": ["sorunlar"],
    "additionalProperties": False,
}

_YUZDE = re.compile(r"(\d{1,3})\s*%")
_ORAN_DILI = re.compile(r"\b(\d{1,2}) in (\d{1,2})\b")
_SANS = re.compile(r"chance|likely|probab|odds of|comes out", re.IGNORECASE)
_TAHMIN = re.compile(r"likel|expect|predict|project|should end|could end|forecast|model", re.IGNORECASE)
_SKOR = re.compile(r"\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b")


def _cumleler(metin: str) -> list[str]:
    return [c for c in re.split(r"(?<=[.!?])\s+", (metin or "").strip()) if c]


def _gol_yonu_celiskili(pazar: str, ev_g: float, dep_g: float) -> bool:
    """Gol çizgisi seçimi beklenen gollerin açıkça ters tarafında mı (yarım gol pay)?"""
    if pazar[:3] in ("UST", "ALT"):
        cizgi, toplam = model.cizgi(pazar), ev_g + dep_g
        return toplam < cizgi - 0.5 if pazar.startswith("UST") else toplam > cizgi + 0.5
    if pazar[:3] in ("EVU", "EVA", "DPU", "DPA"):
        gol = ev_g if pazar.startswith("EV") else dep_g
        cizgi = model.cizgi(pazar)
        return gol < cizgi - 0.5 if pazar[2] == "U" else gol > cizgi + 0.5
    return False


def kural_denetimi(secimler: list[dict]) -> list[dict]:
    """Kodla yakalanabilen çelişkiler (ücretsiz)."""
    sorunlar = []
    for i, s in enumerate(secimler):
        pazarlar = [b["pazar"] for b in (s.get("bacaklar") or [s])]
        for cumle in _cumleler(s.get("yorum")):
            if _SANS.search(cumle):
                ifadeler = [int(y) / 100 for y in _YUZDE.findall(cumle)]
                ifadeler += [int(a) / int(b) for a, b in _ORAN_DILI.findall(cumle) if int(b) and int(a) <= int(b)]
                if ifadeler and all(abs(p - s["adil_olasilik"]) > 0.08 for p in ifadeler):
                    sorunlar.append({"secim": i, "tur": "cumle", "cumle": cumle,
                                     "neden": f"ihtimal ifadesi seçimin ihtimaliyle ({s['adil_olasilik']:.0%}) uyuşmuyor"})
                    continue
            if _TAHMIN.search(cumle) and any(
                    model.kazandi_mi(p, int(a), int(b)) is False for a, b in _SKOR.findall(cumle)
                    for p in pazarlar if not p.startswith(("IY", "YY", "KOR"))):
                sorunlar.append({"secim": i, "tur": "cumle", "cumle": cumle, "neden": "seçimi kaybettiren skor tahmini"})
        bg = s.get("beklenen_gol")
        if bg and any(_gol_yonu_celiskili(p, *bg) for p in pazarlar):
            sorunlar.append({"secim": i, "tur": "secim", "cumle": "", "neden": f"gol çizgisi beklenen gollerle ({bg}) ters"})
    return sorunlar


def yz_denetimi(secimler: list[dict], ayar, client=None) -> list[dict]:
    from .tweets import _skor_satiri
    veri = [{"index": i, "match": f'{s["ev"]} v {s["dep"]}', "pick": s["etiket"], "odds": s["oran"],
             "our_chance": round(s["adil_olasilik"], 3), "expected_goals_home_away": s.get("beklenen_gol"),
             "score_line_shown": _skor_satiri(s).strip(), "explanation": s.get("yorum", "")}
            for i, s in enumerate(secimler)]
    client = client or anthropic.Anthropic()
    with client.messages.stream(model=ayar.direktor_model, max_tokens=8000, system=SISTEM,
                                messages=[{"role": "user", "content": json.dumps(veri, ensure_ascii=False, indent=1)}],
                                output_config={"effort": "low", "format": {"type": "json_schema", "schema": SEMA}}
                                ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"denetçi: {msg.stop_reason}")
    sorunlar = json.loads(next(b.text for b in msg.content if b.type == "text"))["sorunlar"]
    return [x for x in sorunlar if 0 <= x["secim"] < len(secimler)]


def uygula(gun: dict, sorunlar: list[dict], yaz=print) -> list[int]:
    """Sorunlu cümleleri gerekçeden atar; çelişkili seçim içeren kuponları gün kaydından çıkarır.
    Çıkarılan kupon sıralarını döner."""
    for x in sorunlar:
        s = gun["secimler"][x["secim"]]
        if x["tur"] == "cumle" and x["cumle"]:
            yeni = " ".join(c for c in _cumleler(s.get("yorum")) if c.strip() != x["cumle"].strip())
            if yeni != s.get("yorum"):
                s["yorum"] = yeni
                yaz(f"Denetçi: {s['ev']} v {s['dep']} gerekçesinden cümle atıldı ({x['neden']}): {x['cumle']}")
    kotu = {x["secim"] for x in sorunlar if x["tur"] == "secim"}
    cikan = [n for n, k in enumerate(gun.get("kuponlar") or []) if kotu & set(k["ayaklar"])]
    if cikan:
        for x in sorunlar:
            if x["tur"] == "secim":
                s = gun["secimler"][x["secim"]]
                yaz(f"Denetçi: {s['ev']} v {s['dep']} {s['etiket']} çelişkili ({x['neden']}); içindeki kupon paylaşılmayacak.")
        gun["kuponlar"] = [k for n, k in enumerate(gun["kuponlar"]) if n not in cikan]
        # Çıkan kuponların ayakları kayıttan da düşer; kalan kuponların ayak numaraları yenilenir.
        kalan = sorted({i for k in gun["kuponlar"] for i in k["ayaklar"]})
        yeni_no = {eski: yeni for yeni, eski in enumerate(kalan)}
        gun["secimler"] = [gun["secimler"][i] for i in kalan]
        for k in gun["kuponlar"]:
            k["ayaklar"] = [yeni_no[i] for i in k["ayaklar"]]
    return cikan


def denetle(gun: dict, ayar, client=None, yaz=print, yz: bool = True) -> list[int]:
    """Önce kural denetimi, sonra (anahtar varsa) yapay zekâ denetimi; bulunanlar uygulanır."""
    sorunlar = kural_denetimi(gun["secimler"])
    cikan = uygula(gun, sorunlar, yaz)
    if yz and gun.get("kuponlar"):
        try:
            cikan += uygula(gun, yz_denetimi(gun["secimler"], ayar, client), yaz)
        except Exception as e:
            yaz(f"⚠️ Yapay zekâ denetimi yapılamadı ({e}); kural denetimiyle devam ediliyor.")
    return cikan
