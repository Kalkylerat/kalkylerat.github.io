"""Tiny Fixes viral puanı (SOZLESME F): hangi konu flood'a değer?

Puan dört parçadan oluşur: kaç bağımsız kaynakta göründüğü, tazelik, yükselme hızı ve nişe (yapay zekâ) uygunluk.
Daha önce işlenmiş konu elenir. Haber (news) adayı yapay zekâ ile ilgili değilse hiç girmez: alakasız trende girmek
X'in trend manipülasyonu kuralına girer (sosyal-medya skill'i)."""

import math
import re
from datetime import datetime

from . import flood_denetci
from .flood_kaynak import benzerlik

AI_KELIME = re.compile(
    r"\b(ai|a\.i\.|artificial intelligence|llms?|gpt[\w.-]*|chatgpt|openai|anthropic|claude|gemini|copilot|deepmind|"
    r"deepseek|mistral|llama|grok|midjourney|sora|stable diffusion|hugging ?face|machine learning|neural net\w*|"
    r"chatbots?|agentic|ai agents?|prompts?|prompting|perplexity|codex|transformer models?|diffusion models?|"
    r"foundation models?|generative|nvidia|gpu|robotaxi|waymo|humanoid)\b", re.IGNORECASE)
PUAN_ESIGI = 0.35
YINELENEN_ESIK = 0.6


def nis(aday: dict) -> float:
    """0..1 yapay zekâ uygunluğu: başlıkta ve kaynak özetlerinde anahtar kelime."""
    metin = aday["baslik"] + " " + " ".join(k.get("baslik", "") + " " + k.get("ozet", "") for k in aday["kaynaklar"])
    n = len({m.group(0).lower() for m in AI_KELIME.finditer(metin)})
    return min(1.0, n / 3)


def _yas_saat(tarih: str | None, simdi: datetime) -> float | None:
    if not tarih:
        return None
    return max(0.0, (simdi - datetime.fromisoformat(tarih)).total_seconds() / 3600)


def tazelik(aday: dict, simdi: datetime, yari_omur_sa: float = 8.0) -> float:
    yaslar = [y for y in (_yas_saat(k.get("tarih"), simdi) for k in aday["kaynaklar"]) if y is not None]
    return 0.5 ** (min(yaslar) / yari_omur_sa) if yaslar else 0.3


def hiz(aday: dict, simdi: datetime) -> float:
    """Saatte puan + yorum artışı (Hacker News) ve arama trafiği (Google Trends) tek bir 0..1 değere indirilir."""
    en = 0.0
    for k in aday["kaynaklar"]:
        y = _yas_saat(k.get("tarih"), simdi)
        if y is not None and (k.get("skor") or k.get("yorum")):
            en = max(en, (k.get("skor", 0) + 2 * k.get("yorum", 0)) / max(y, 1.0))
    trafik = math.log10(aday["trafik"] + 1) / 6 if aday.get("trafik") else 0.0  # 1M arama = 1.0
    return max(math.tanh(en / 60), min(1.0, trafik))


def yinelenen(baslik: str, gecmis) -> bool:
    return any(benzerlik(baslik, g) >= YINELENEN_ESIK for g in gecmis)


def puan(aday: dict, simdi: datetime) -> dict:
    alanlar = {flood_denetci.alan_adi(k["url"]) for k in aday["kaynaklar"] if k.get("url")}
    parca = {"cok_kaynak": min(len(alanlar), 4) / 4, "tazelik": tazelik(aday, simdi), "hiz": hiz(aday, simdi),
             "nis": nis(aday)}
    parca["toplam"] = round(0.35 * parca["cok_kaynak"] + 0.2 * parca["tazelik"] + 0.25 * parca["hiz"] + 0.2 * parca["nis"], 3)
    return parca


def sirala(adaylar: list[dict], simdi: datetime, gecmis=(), esik: float = PUAN_ESIGI) -> list[dict]:
    """Elenmeyen adaylar puanıyla, en yüksek önce. Elenenler: işlenmiş konu, güvensiz alan (F5), nişsiz haber, eşik altı."""
    sonuc = []
    for a in adaylar:
        if yinelenen(a["baslik"], gecmis):
            continue
        tum = a["baslik"] + " " + " ".join(k.get("baslik", "") + " " + k.get("ozet", "") for k in a["kaynaklar"])
        if flood_denetci.guvensiz_alan(tum):
            continue
        p = puan(a, simdi)
        if a["tur_ipucu"] == "news" and p["nis"] == 0:
            continue
        if p["toplam"] >= esik or (a["tur_ipucu"] == "trend" and p["toplam"] >= esik - 0.1):
            sonuc.append({**a, "puan": p})
    return sorted(sonuc, key=lambda a: a["puan"]["toplam"], reverse=True)
