"""Tiny Fixes konu toplayıcı (SOZLESME F): trend konuları ücretsiz dış kaynaklardan toplar.

X'ten OKUMA YAPMAZ: X API okuması post başına ücretlidir. Kaynaklar: Google Trends (günün aranan konuları),
Hacker News (Algolia), yapay zekâ haber ve laboratuvar RSS akışları. Her kaynak bağımsızdır; biri çökerse
diğerleri çalışır. Ağ çağrısı `get(url) -> str` ile enjekte edilir (testler ağa çıkmaz)."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

UA = {"User-Agent": "TinyFixesBot/1.0 (+https://github.com)"}
DURAK = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are", "with", "by", "at", "from", "as",
         "its", "it", "new", "how", "why", "what", "this", "that", "be", "vs"}


def http_al(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return r.text


def _yerel(etiket: str) -> str:
    return etiket.rsplit("}", 1)[-1]


def _tarih(metin: str | None) -> str | None:
    """RSS (RFC 2822) ya da Atom/ISO tarihi -> UTC ISO; çözülemezse None."""
    if not metin:
        return None
    metin = metin.strip()
    try:
        d = parsedate_to_datetime(metin)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(metin.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat(timespec="seconds")


def _alt(el, ad: str) -> str:
    for c in el:
        if _yerel(c.tag) == ad:
            return (c.text or "").strip()
    return ""


def trends_ayristir(xml: str) -> list[dict]:
    """Google Trends 'trending now' RSS'i -> aday listesi (ad uzay alanından bağımsız ayrıştırılır)."""
    sonuc = []
    for it in ET.fromstring(xml).iter():
        if _yerel(it.tag) != "item":
            continue
        baslik = _alt(it, "title")
        trafik = re.sub(r"\D", "", _alt(it, "approx_traffic").split("+")[0]) or "0"
        tarih = _tarih(_alt(it, "pubDate"))
        kaynaklar = []
        for c in it:
            if _yerel(c.tag) == "news_item":
                url, kaynak = _alt(c, "news_item_url"), _alt(c, "news_item_source")
                if url:
                    kaynaklar.append({"ad": kaynak or "news", "url": url, "baslik": _alt(c, "news_item_title"),
                                      "ozet": _alt(c, "news_item_snippet"), "tarih": tarih, "skor": 0, "yorum": 0})
        if baslik:
            sonuc.append({"baslik": baslik, "kaynaklar": kaynaklar, "tur_ipucu": "trend", "trafik": int(trafik)})
    return sonuc


def rss_ayristir(xml: str, ad: str, tur: str = "news") -> list[dict]:
    """Genel RSS 2.0 ya da Atom akışı -> aday listesi. tur "sorun": insanların sorun sorduğu topluluk (Reddit gibi);
    başlık bir konu sinyalidir, olgu değildir (olgular F1 ile ayrıca doğrulanır)."""
    sonuc = []
    for it in ET.fromstring(xml).iter():
        yerel = _yerel(it.tag)
        if yerel not in ("item", "entry"):
            continue
        baslik = _alt(it, "title")
        link = _alt(it, "link")
        if not link:  # Atom: <link href="...">
            for c in it:
                if _yerel(c.tag) == "link" and c.get("href"):
                    link = c.get("href")
                    break
        tarih = _tarih(_alt(it, "pubDate") or _alt(it, "published") or _alt(it, "updated"))
        if baslik and link:
            ozet = _alt(it, "description") or _alt(it, "summary") or _alt(it, "content")
            sonuc.append({"baslik": baslik, "tur_ipucu": tur, "trafik": 0,
                          "kaynaklar": [{"ad": ad, "url": link, "baslik": baslik, "ozet": re.sub(r"<[^>]+>", "", ozet)[:300],
                                         "tarih": tarih, "skor": 0, "yorum": 0}]})
    return sonuc


def hn_ayristir(json_metin: str) -> list[dict]:
    """Hacker News (Algolia) ön sayfa yanıtı -> aday listesi."""
    import json
    sonuc = []
    for h in json.loads(json_metin).get("hits", []):
        baslik, url = h.get("title") or "", h.get("url") or ""
        if not baslik or not url:
            continue
        tarih = datetime.fromtimestamp(h["created_at_i"], timezone.utc).isoformat(timespec="seconds") if h.get("created_at_i") else None
        sonuc.append({"baslik": baslik, "tur_ipucu": "news", "trafik": 0,
                      "kaynaklar": [{"ad": "Hacker News", "url": url, "baslik": baslik, "ozet": "", "tarih": tarih,
                                     "skor": int(h.get("points") or 0), "yorum": int(h.get("num_comments") or 0)}]})
    return sonuc


def belirtec(baslik: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", baslik.lower()) if t not in DURAK and len(t) > 1}


def benzerlik(a: str, b: str) -> float:
    x, y = belirtec(a), belirtec(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def birlestir(adaylar: list[dict], esik: float = 0.5) -> list[dict]:
    """Aynı konuyu anlatan adaylar tek adayda toplanır; çok kaynakta görünmek viral puanını artırır."""
    grup: list[dict] = []
    for a in adaylar:
        hedef = next((g for g in grup if benzerlik(g["baslik"], a["baslik"]) >= esik), None)
        if hedef is None:
            grup.append({**a, "kaynaklar": list(a["kaynaklar"])})
            continue
        urller = {k["url"] for k in hedef["kaynaklar"]}
        hedef["kaynaklar"] += [k for k in a["kaynaklar"] if k["url"] not in urller]
        hedef["trafik"] = max(hedef["trafik"], a["trafik"])
        if a["tur_ipucu"] == "news" and hedef["tur_ipucu"] != "sorun":
            hedef["tur_ipucu"] = "news"
    return grup


def topla(ayar, get=http_al, yaz=print) -> list[dict]:
    """Bütün kaynaklardan adaylar. `ayar`: FloodAyar (geo, rss listesi, hn). Çöken kaynak atlanır ve bildirilir."""
    adaylar: list[dict] = []
    isler = [("Google Trends", f"https://trends.google.com/trending/rss?geo={ayar.geo}", trends_ayristir)]
    if ayar.hacker_news:
        isler.append(("Hacker News", "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=40", hn_ayristir))
    for ad, url, *tur in ayar.rss:
        isler.append((ad, url, lambda xml, ad=ad, tur=tur: rss_ayristir(xml, ad, *tur)))
    basarili = 0
    for ad, url, ayristir in isler:
        try:
            adaylar += ayristir(get(url))
            basarili += 1
        except Exception as e:  # tek kaynak çökerse diğerleri devam eder
            yaz(f"Konu kaynağı alınamadı ({ad}): {e}")
    if not basarili:
        raise RuntimeError("hiçbir konu kaynağı alınamadı")
    return birlestir(adaylar)
