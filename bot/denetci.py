"""Denetçi: kupon onaya gitmeden önce seçimlerle her söylenen şeyin tutarlılığını denetler.

İki katman:
1) Kural denetimi (kod, ücretsiz): gerekçedeki ihtimal ifadeleri seçimin ihtimaliyle, tahmin edilen skorlar ve
   beklenen goller seçimin yönüyle uyuşmalı.
2) Yapay zekâ denetimi (hızlı model, kupon taraması başına bir çağrı): seçim, oran, ihtimal, beklenen goller ve gerekçe
   birlikte okunur; çelişki ya da yanıltıcı ifade bulunur.

Sonuç: sorunlu cümle gerekçeden atılır; seçimin kendisi çelişkiliyse o kupon paylaşılmaz."""

import json
import re
from datetime import datetime

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


# ---- Yayın öncesi denetim: paylaşılacak postun kendisi (metinler, kasa/yatırılan, görseller) ----

_KESINLIK = re.compile(r"\block(ed)?\b|guarantee|sure (thing|win|bet)|\bbanker\b|dead cert|can'?t (lose|miss)|"
                       r"free money|100\s*%", re.IGNORECASE)
_LINK = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(com|net|org|io|co|se|uk|tr|bet|app|gg|ly|me|tv)\b|@")
_SITE = re.compile(r"bet\s*365|betfair|unibet|betway|bwin|1xbet|pinnacle|betsson|nordicbet|william\s*hill|\b888|"
                   r"betano|betvictor|comeon|marathonbet|coolbet", re.IGNORECASE)


def yayin_kontrolu(gun: dict, metinler: list[str], gunler: list[dict], ayar, simdi, pngler: list[bytes] = ()) -> list[str]:
    """Paylaşılacak kupon postunun kod denetimi. Dönen her madde engelleyicidir (post çıkmaz)."""
    from .tweets import ANSVAR, LIMIT, oran_metni, skor_celiskili, uzunluk, yuzde
    from . import kayit
    hata = []
    for i, m in enumerate(metinler, 1):
        if uzunluk(m) > LIMIT:
            hata.append(f"Tweet {i} 280 karakteri aşıyor ({uzunluk(m)}).")
        if _LINK.search(m):
            hata.append(f"Tweet {i} link ya da @ içeriyor.")
        if _SITE.search(m) or any(b.lower() in m.lower() for b in ayar.oran_bahiscileri + [ayar.keskin_bahisci]):
            hata.append(f"Tweet {i} bahis sitesi adı içeriyor.")
        if _KESINLIK.search(m):
            hata.append(f"Tweet {i} kesinlik dili içeriyor.")
    if metinler and not metinler[0].rstrip().endswith(ANSVAR):
        hata.append("Ana tweette '18+ | Play responsibly' satırı yok.")
    for n, k in enumerate(kayit.kuponlar(gun), 1):
        if k.get("stake") is None or k["stake"] <= 0:
            hata.append(f"Kupon {n}: yatırılan tutar yok.")
        elif k.get("kasa") is not None and abs(k["stake"] - round(k["kasa"] * ayar.oyun_yuzdesi / 100, 2)) > 0.011:
            hata.append(f"Kupon {n}: yatırılan ({k['stake']}) kasanın %{ayar.oyun_yuzdesi:g}'i ({k['kasa']}) değil.")
    yanitlar = metinler[1:]
    if len(yanitlar) != len(gun["secimler"]):
        hata.append(f"Gerekçe tweeti sayısı ({len(yanitlar)}) seçim sayısıyla ({len(gun['secimler'])}) uyuşmuyor.")
    for i, s in enumerate(gun["secimler"]):
        ad = f'{s["ev"]} v {s["dep"]}'
        if datetime.fromisoformat(s["baslama"]) <= simdi:
            hata.append(f"{ad}: maç başlamış.")
        if i < len(yanitlar):
            m = yanitlar[i]
            for beklenen in (f'Pick: {s["etiket"]}', f"Odds {oran_metni(s)}", f'chance {yuzde(s["adil_olasilik"])}'):
                if beklenen not in m:
                    hata.append(f"{ad}: gerekçe tweetinde '{beklenen}' yok (kayıtla uyuşmuyor).")
            if skor_celiskili(s) and "Most likely score" in m:
                hata.append(f"{ad}: en olası skor seçimle çelişiyor.")
    baska = {s["fixture_id"] for g in gunler if g["tarih"] == gun["tarih"] and g["id"] != gun["id"]
             and g.get("sonuc") != "pas" for s in g["secimler"]}
    for s in gun["secimler"]:
        if s["fixture_id"] in baska:
            hata.append(f'{s["ev"]} v {s["dep"]}: aynı maç bugün başka bir kuponda da var.')
    if pngler:
        from io import BytesIO
        from PIL import Image
        if len(pngler) != len(kayit.kuponlar(gun)):
            hata.append(f"Görsel sayısı ({len(pngler)}) kupon sayısıyla uyuşmuyor.")
        for n, png in enumerate(pngler, 1):
            try:
                with Image.open(BytesIO(png)) as im:
                    if min(im.size) < 600:
                        hata.append(f"Görsel {n} çok küçük ({im.size}).")
            except Exception as e:
                hata.append(f"Görsel {n} açılamıyor: {e}")
    return hata


GORSEL_SISTEM = """You check coupon images before they are posted on X. For each image you get the values it must show.
Report only real problems: a number on the image that differs from the expected value (bank, stake, potential return,
odds, total odds, chance), a missing or wrong match or pick, or text that is cut off, overlapping or unreadable.
If the image is correct and readable, return an empty list. Write each problem as one short sentence."""
GORSEL_SEMA = {"type": "object", "properties": {"sorunlar": {"type": "array", "items": {"type": "string"}}},
               "required": ["sorunlar"], "additionalProperties": False}


def gorsel_denetimi(gun: dict, pngler: list[bytes], ayar, client=None) -> list[str]:
    """Hızlı modelle görsel denetimi (uyarı): görseldeki rakamlar kayıtla aynı ve okunaklı mı?"""
    import base64
    from . import kayit
    icerik = []
    for n, (k, png) in enumerate(zip(kayit.kuponlar(gun), pngler), 1):
        beklenen = {"bank": k.get("kasa"), "stake": k.get("stake"),
                    "potential_return": round(k["stake"] * kayit.kupon_oran(gun, k), 2) if k.get("stake") else None,
                    "total_odds": round(kayit.kupon_oran(gun, k), 2),
                    "legs": [{"match": f'{s["ev"]} v {s["dep"]}', "pick": s["kisa"], "odds": s["oran"],
                              "chance": round(s["adil_olasilik"], 2)} for s in kayit.kupon_ayaklari(gun, k)]}
        icerik += [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                "data": base64.standard_b64encode(png).decode()}},
                   {"type": "text", "text": f"Image {n} must show: " + json.dumps(beklenen, ensure_ascii=False)}]
    client = client or anthropic.Anthropic()
    with client.messages.stream(model=ayar.direktor_model, max_tokens=8000, system=GORSEL_SISTEM,
                                messages=[{"role": "user", "content": icerik}],
                                output_config={"effort": "low", "format": {"type": "json_schema", "schema": GORSEL_SEMA}}
                                ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"görsel denetimi: {msg.stop_reason}")
    return json.loads(next(b.text for b in msg.content if b.type == "text"))["sorunlar"]
