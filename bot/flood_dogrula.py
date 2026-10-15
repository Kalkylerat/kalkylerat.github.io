"""Prompt Proof doğrulama (SOZLESME F1, F2): olgular web aramasıyla doğrulanır, komutlar gerçekten çalıştırılır.

F1: Claude'un web arama aracı kaynak bulur; yalnızca aramanın GERÇEKTEN döndürdüğü adresler sayılır (uydurulmuş adres
sayılmaz), her olgu en az 2 bağımsız alan adından gelmelidir. Doğrulanamayan olgu kayda girmez.
F2: Fix komutu `test_model` ile gerçekten çalıştırılır; çıktı, süre ve sınır kayda yazılır. Zayıf çıktı paylaşılmaz."""

import re
import time

from .direktor import _cagir
from .flood_denetci import alan_adi

ARAMA_ARACI = {"type": "web_search_20260209", "name": "web_search", "max_uses": 6}

ARASTIRMA_SISTEMI = """You are a careful fact checker for a social media account that publishes sourced AI and tech content.
Use web search. Report ONLY facts that at least two independent websites (different domains, not mirrors of one
press release) state. No opinions, predictions, rumours or marketing claims. Copy numbers exactly as the sources
write them; never round or convert. Prefer the primary source plus one independent report.

Output format, one fact per line, nothing else:
FACT: <one plain sentence> || SOURCES: <url1>, <url2>[, <url3>]
If you cannot confirm anything, output exactly: UNCONFIRMED"""

KOMUT_SEMASI = {"type": "object", "additionalProperties": False, "required": ["komut", "ornek_girdi", "gosterim"],
                "properties": {"komut": {"type": "string"}, "ornek_girdi": {"type": "string"}, "gosterim": {"type": "string"}}}
KOMUT_SISTEMI = """You write one reusable prompt that a person can paste into an AI assistant to solve the everyday problem below.
Rules: the prompt must work with the person's own input, so put the placeholder {INPUT} exactly once where they paste their
material. Keep it under 700 characters, plain English, no jargon, no role-play fluff beyond one short sentence.
Also give a short, realistic SAMPLE input ("ornek_girdi") that clearly is made up (never a real person, company, or a
real data claim), under 400 characters, so the prompt can be tested. Finally "gosterim": the same prompt with {INPUT}
replaced by a short human placeholder like <paste your battery stats here>."""

DEGERLENDIRME_SEMASI = {"type": "object", "additionalProperties": False, "required": ["kalite", "sinir"],
                        "properties": {"kalite": {"type": "string", "enum": ["iyi", "zayif"]}, "sinir": {"type": "string"}}}
DEGERLENDIRME_SISTEMI = """You review one tested prompt and its real output for a social media account that only posts tested fixes.
"kalite": "iyi" only if the output is correct, concrete, and useful for the problem; otherwise "zayif".
"sinir": ONE plain sentence (max 140 chars) stating honestly when this prompt fails or what it cannot do. Never leave it empty."""


def _ara(client, model: str, effort: str, sistem: str, soru: str, max_tokens: int = 8000):
    """Web arama aracıyla tek soru. (metin, {url: başlık}) döner; pause_turn'de kaldığı yerden sürdürür."""
    mesajlar = [{"role": "user", "content": soru}]
    metin, kaynaklar = [], {}
    for _ in range(4):
        with client.messages.stream(model=model, max_tokens=max_tokens, system=sistem, tools=[ARAMA_ARACI],
                                    messages=mesajlar, output_config={"effort": effort}) as st:
            msg = st.get_final_message()
        for b in msg.content:
            if b.type == "text":
                metin.append(b.text)
            elif b.type == "web_search_tool_result" and isinstance(b.content, list):
                for r in b.content:
                    if getattr(r, "url", None):
                        kaynaklar[r.url] = getattr(r, "title", "") or ""
        if msg.stop_reason == "pause_turn":
            mesajlar.append({"role": "assistant", "content": msg.content})
            continue
        if msg.stop_reason in ("refusal", "max_tokens"):
            raise RuntimeError(f"araştırma {msg.stop_reason}")
        break
    return "\n".join(metin), kaynaklar


def olgulari_ayikla(metin: str, bilinen: dict) -> list[dict]:
    """'FACT: ... || SOURCES: ...' satırları. Aramanın döndürmediği adres atılır; 2 bağımsız alan adı kalmayan olgu düşer."""
    olgular = []
    for satir in metin.splitlines():
        m = re.match(r"\s*FACT:\s*(.+?)\s*\|\|\s*SOURCES:\s*(.+)$", satir)
        if not m:
            continue
        urller = [u.strip().rstrip(".,)") for u in re.findall(r"https?://[^\s,|]+", m.group(2))]
        gercek = [u for u in dict.fromkeys(urller) if u in bilinen]
        if len({alan_adi(u) for u in gercek}) >= 2:
            olgular.append({"metin": m.group(1).strip(), "kaynaklar": gercek})
    return olgular


def arastir(client, ayar, konu: str, ozet: str = "", amac: str = "news") -> tuple[list[dict], list[dict]]:
    """(olgular, kaynaklar). amac 'news': konu hakkında en önemli doğrulanmış olgular; 'fix': sorunun neden gündemde olduğu."""
    istek = {"news": "What are the most important, newest verified facts about this AI news item? Give up to 5.",
             "fix": "Why is this topic trending right now, and what is the everyday problem people have? Give up to 3 verified facts."}[amac]
    soru = f"{istek}\n\nTopic: {konu}\nContext from our feed: {ozet[:600]}"
    metin, bilinen = _ara(client, ayar.model, ayar.effort, ARASTIRMA_SISTEMI, soru)
    olgular = olgulari_ayikla(metin, bilinen)
    kullanilan = {u for o in olgular for u in o["kaynaklar"]}
    return olgular, [{"url": u, "baslik": bilinen[u]} for u in bilinen if u in kullanilan]


def komut_yaz(client, ayar, problem: str, fikir: str = "") -> dict:
    """{"komut" ({INPUT} içerir), "ornek_girdi", "gosterim"}; komutta {INPUT} yoksa hata."""
    k = _cagir(client, [(ayar.model, ayar.effort)], KOMUT_SISTEMI, f"Problem: {problem}\nIdea: {fikir}", KOMUT_SEMASI, 3000)
    if k["komut"].count("{INPUT}") != 1:
        raise RuntimeError("komutta {INPUT} tam bir kez olmalı")
    return k


def dene(client, ayar, k: dict) -> dict:
    """Komutu `test_model` ile gerçekten çalıştırır (F2). Kayıt: model, komut, çıktı, süre ('9 seconds')."""
    metin = k["komut"].replace("{INPUT}", k["ornek_girdi"])
    t0 = time.monotonic()
    msg = client.messages.create(model=ayar.test_model, max_tokens=2000, messages=[{"role": "user", "content": metin}],
                                 output_config={"effort": "low"})
    sure = max(1, round(time.monotonic() - t0))
    if msg.stop_reason in ("refusal", "max_tokens"):
        raise RuntimeError(f"deneme {msg.stop_reason}")
    cikti = next((b.text for b in msg.content if b.type == "text"), "").strip()
    if not cikti:
        raise RuntimeError("deneme boş çıktı verdi")
    return {"model": ayar.test_model, "komut": k["gosterim"], "ornek_girdi": k["ornek_girdi"], "cikti": cikti,
            "sure": f"{sure} seconds"}


def degerlendir(client, ayar, d: dict) -> dict:
    """{"kalite", "sinir"}: zayıf çıktı paylaşılmaz; sınır cümlesi kayda yazılır (F2)."""
    icerik = f"Prompt:\n{d['komut']}\n\nSample input:\n{d['ornek_girdi']}\n\nReal output:\n{d['cikti'][:3000]}"
    return _cagir(client, [(ayar.hafif_model, "low")], DEGERLENDIRME_SISTEMI, icerik, DEGERLENDIRME_SEMASI, 600)


def fix_kaydi(client, ayar, aday: dict, problem: str, fikir: str, yaz=print) -> dict | None:
    """Bir Fix için tam olgu kaydı: bağlam olguları (F1) + gerçekten denenmiş komut (F2). Yetersizse None."""
    olgular, kaynaklar = arastir(client, ayar, aday["baslik"], " ".join(k.get("ozet", "") for k in aday["kaynaklar"]), "fix")
    if not olgular:
        yaz(f"Fix atlandı (bağlam doğrulanamadı): {aday['baslik']}")
        return None
    k = komut_yaz(client, ayar, problem, fikir)
    d = dene(client, ayar, k)
    v = degerlendir(client, ayar, d)
    if v["kalite"] != "iyi" or not v["sinir"].strip():
        yaz(f"Fix atlandı (denenen çıktı zayıf): {aday['baslik']}")
        return None
    d["sinir"] = v["sinir"].strip()
    return {"tur": "fix", "konu": problem, "olgular": olgular, "kaynaklar": kaynaklar, "denendi": d, "arac": None}


def haber_kaydi(client, ayar, aday: dict, yaz=print) -> dict | None:
    """Bir News için olgu kaydı (F1): en az 2 doğrulanmış olgu, her biri 2 bağımsız alan adından."""
    olgular, kaynaklar = arastir(client, ayar, aday["baslik"], " ".join(k.get("ozet", "") for k in aday["kaynaklar"]), "news")
    if len(olgular) < 2:
        yaz(f"Haber atlandı (yeterli doğrulanmış olgu yok): {aday['baslik']}")
        return None
    return {"tur": "news", "konu": aday["baslik"], "olgular": olgular, "kaynaklar": kaynaklar, "denendi": None, "arac": None}


def kutuphane_kaydi(client, ayar, tema: str, yaz=print) -> dict | None:
    """Evergreen (Library): olgu iddiası yok; komut yine gerçekten denenir (F2)."""
    k = komut_yaz(client, ayar, tema)
    d = dene(client, ayar, k)
    v = degerlendir(client, ayar, d)
    if v["kalite"] != "iyi" or not v["sinir"].strip():
        yaz(f"Library atlandı (denenen çıktı zayıf): {tema}")
        return None
    d["sinir"] = v["sinir"].strip()
    return {"tur": "library", "konu": tema, "olgular": [], "kaynaklar": [], "denendi": d, "arac": None}
