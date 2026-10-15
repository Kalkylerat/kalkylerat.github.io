"""Tiny Fixes denenmiş komut kütüphanesi: sitenin ve paketlerin ortak kaynağı (SOZLESME F11, F13).

İki ayrı kayıt:
- `data/flood_kutuphane.json` (herkese açık): YAYINLANMIŞ birimlerden gelen girdiler. Site bunlardan kurulur (F11).
- `data/flood_paket.enc` (şifreli): yalnızca paket için denenmiş komutlar. Depo herkese açık olduğu için düz metin
  girmez (F13); şifre X uygulamasının gizli anahtarından türetilir (`flood_yetki._kasa`).

Paket komutları da Fix/Library ile aynı yoldan geçer: komut yazılır, test modeliyle GERÇEKTEN çalıştırılır, çıktı
değerlendirilir, zayıfsa girmez (F2). Ek maliyet tek seferliktir (tema başına ~$0.04)."""

import json
import re
from datetime import datetime

from cryptography.fernet import InvalidToken

from . import config, flood_denetci, flood_dogrula, flood_yetki

DOSYA = config.ROOT / "data" / "flood_kutuphane.json"
PAKET_DOSYA = config.ROOT / "data" / "flood_paket.enc"
OZET_DOSYA = config.ROOT / "data" / "flood_paket_ozet.json"  # yalnızca sayı, kategori, model: sitedeki ürün kutusu (F13)
TEMA_MALIYETI = 0.04  # USD, komut yazma + deneme + değerlendirme (tahmin; flood_ogren.MALIYET ile aynı kaynak)

# Paket temaları (ücretli paket ve ücretsiz başlangıç paketi). Hepsi güvenli alanda (F5), günlük evergreen temalarından
# (flood_yazar.KUTUPHANE) ayrı: paketin kendine ait içeriği olsun. (kategori, tema)
PAKET_TEMALARI = [
    ("Work", "Turn a long, messy to-do list into today's top three tasks and what can wait"),
    ("Work", "Write a clear status update for your manager from rough bullet notes"),
    ("Work", "Turn a vague request from a colleague into a list of clarifying questions"),
    ("Work", "Summarize a long document into five bullet points and one open question"),
    ("Work", "Write a polite follow-up when someone has not replied for a week"),
    ("Work", "Turn meeting notes into a decision log with owner and date for each decision"),
    ("Work", "Rewrite a long Slack message so it can be read in ten seconds"),
    ("Work", "Prepare three talking points for a short meeting from background notes"),
    ("Work", "Turn a process you explain often into a simple step-by-step guide"),
    ("Work", "Find the unclear sentences in a draft and suggest a plainer version of each"),
    ("Email", "Write a friendly but firm reminder about an unpaid invoice from the facts given"),
    ("Email", "Decline a meeting invitation politely and suggest an alternative"),
    ("Email", "Turn an angry draft reply into a calm one that keeps the same points"),
    ("Email", "Write a short introduction email connecting two people"),
    ("Email", "Ask for a deadline extension with a clear reason and a new date"),
    ("Email", "Reply to a customer question using only the product facts provided"),
    ("Email", "Write a thank-you note after a job interview that mentions one specific detail"),
    ("Email", "Turn a long email into a three-line version with the request first"),
    ("Study", "Turn textbook notes into five practice questions with answers"),
    ("Study", "Explain a hard concept with an everyday analogy and one check question"),
    ("Study", "Make a two-week study plan from a list of topics and an exam date"),
    ("Study", "Find the gaps in your own explanation of a topic"),
    ("Study", "Turn a long reading into a summary, key terms and three discussion questions"),
    ("Study", "Create a memory hook for a list of terms you keep forgetting"),
    ("Study", "Check a short essay for structure and say which paragraph is weakest"),
    ("Career", "Turn a job description into a list of skills to highlight and proof for each"),
    ("Career", "Write a short LinkedIn summary from a list of past roles and results"),
    ("Career", "Prepare answers to 'tell me about yourself' in three lengths"),
    ("Career", "Turn a project you did into a STAR interview story"),
    ("Career", "Write a polite message asking for a reference"),
    ("Career", "Compare two job offers on the criteria you care about"),
    ("Writing", "Write five headline options for an article and say which is clearest"),
    ("Writing", "Shorten a paragraph by half without losing the main point"),
    ("Writing", "Turn a list of features into plain benefits for a normal reader"),
    ("Writing", "Write alt text for an image from a description of what it shows"),
    ("Writing", "Write a short product description from a list of facts, no hype words"),
    ("Writing", "Turn a talk transcript into a short blog post outline"),
    ("Writing", "Rewrite instructions so a beginner can follow them"),
    ("Home", "Plan a weekend cleaning routine that takes under two hours"),
    ("Home", "Turn a messy grocery list into a list grouped by store section"),
    ("Home", "Plan a birthday party schedule for a small group from the details given"),
    ("Home", "Write a clear message to a landlord about something that needs repair"),
    ("Home", "Make a packing list for moving house, room by room"),
    ("Home", "Plan a simple family weekly calendar from everyone's fixed activities"),
    ("Home", "Write a kind note to a neighbour about noise"),
    ("Tech help", "Explain what a setting on your phone does and when to turn it off"),
    ("Tech help", "Write a clear bug report from a description of what went wrong"),
    ("Tech help", "Turn a confusing app error into steps to try, simplest first"),
    ("Tech help", "Make a checklist for setting up a new laptop"),
    ("Tech help", "Explain a spreadsheet formula in plain words and fix a common mistake"),
    ("Tech help", "Write a simple spreadsheet formula from a description of what you need"),
    ("Tech help", "Organize a messy folder of files into a clear folder structure"),
    ("Planning", "Turn a goal into weekly steps for the next month"),
    ("Planning", "Make a pros and cons list for a decision and say what information is missing"),
    ("Planning", "Plan a one-day trip itinerary from a list of places and opening hours"),
    ("Planning", "Break a big presentation into a timeline of small tasks"),
    ("Planning", "Turn a brainstorm into three options with a first step for each"),
    ("Planning", "Write a short weekly review template and fill it in from notes"),
    ("Planning", "Plan a realistic daily routine around fixed work hours"),
    ("Planning", "Turn feedback you received into three concrete changes to try"),
]


def slug(metin: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", metin.lower()).strip("-")
    return s[:70].rstrip("-") or "fix"


def girdi(kayit: dict, kaynak: str, tarih: str, kategori: str = "", birim_id: str | None = None) -> dict:
    """Olgu kaydından kütüphane girdisi. Yalnızca kayıttaki alanlar (F1, F2)."""
    d = kayit.get("denendi") or {}
    return {"slug": slug(kayit["konu"]), "baslik": kayit["konu"], "tur": kayit["tur"], "kategori": kategori,
            "kaynak": kaynak, "tarih": tarih, "birim": birim_id,
            "komut": d.get("komut", ""), "ornek_girdi": d.get("ornek_girdi", ""), "cikti": (d.get("cikti") or "")[:1500],
            "model": flood_denetci.model_adi(d.get("model", "")) if d else "", "sinir": d.get("sinir", ""),
            "olgular": [{"metin": o["metin"], "kaynaklar": list(o.get("kaynaklar") or [])} for o in kayit.get("olgular") or []]}


def yukle() -> list[dict]:
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8")).get("girdiler", [])
    except (FileNotFoundError, ValueError):
        return []


def kaydet(girdiler: list[dict]) -> None:
    DOSYA.write_text(json.dumps({"girdiler": girdiler}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def ekle_birim(b: dict, simdi: datetime) -> bool:
    """Yayınlanmış birimi siteye (herkese açık kütüphaneye) ekler. Yalnızca 'yayinlandi' (F11). Eklendiyse True."""
    if b.get("durum") != "yayinlandi":
        return False
    girdiler = yukle()
    g = girdi(b["kayit"], "post", simdi.date().isoformat(), birim_id=b["id"])
    if any(x["slug"] == g["slug"] for x in girdiler):
        g["slug"] = f"{g['slug']}-{simdi.strftime('%Y%m%d')}"
        if any(x["slug"] == g["slug"] for x in girdiler):
            return False
    if flood_denetci.guvensiz_alan(" ".join([g["baslik"], g["komut"], g["cikti"], g["sinir"]])):
        return False  # F5: siteye de girmez
    girdiler.append(g)
    kaydet(girdiler)
    return True


# ---------- Paket (şifreli) ----------

def paket_yukle(api_secret: str) -> list[dict]:
    try:
        return json.loads(flood_yetki._kasa(api_secret).decrypt(PAKET_DOSYA.read_bytes().strip())).get("girdiler", [])
    except (FileNotFoundError, InvalidToken, ValueError):
        return []


def paket_kaydet(api_secret: str, girdiler: list[dict]) -> None:
    veri = json.dumps({"girdiler": girdiler}, ensure_ascii=False).encode()
    PAKET_DOSYA.write_bytes(flood_yetki._kasa(api_secret).encrypt(veri) + b"\n")


def paket_uret(client, ayar, api_secret: str, simdi: datetime, en_fazla: int = len(PAKET_TEMALARI), yaz=print) -> list[dict]:
    """Henüz denenmemiş paket temalarını sırayla dener (F2) ve şifreli kaydeder. Bütün paket girdilerini döndürür.
    Her tema bir kez denenir; zayıf çıkan tema 'atlandi' olarak işaretlenir, bir sonraki çalışmada yeniden denenmez."""
    girdiler = paket_yukle(api_secret)
    bilinen = {g["baslik"] for g in girdiler}
    yeni = 0
    for kategori, tema in PAKET_TEMALARI:
        if yeni >= en_fazla or tema in bilinen:
            continue
        yeni += 1
        try:
            kayit = flood_dogrula.kutuphane_kaydi(client, ayar, tema, yaz)
        except Exception as e:  # tek temanın hatası paketi durdurmaz
            yaz(f"Paket teması denenemedi ({tema}): {e}")
            continue
        if kayit and not flood_denetci.kayit_kontrol(kayit):
            girdiler.append(girdi(kayit, "paket", simdi.date().isoformat(), kategori))
        else:
            girdiler.append({"baslik": tema, "kategori": kategori, "kaynak": "atlandi", "tarih": simdi.date().isoformat()})
        paket_kaydet(api_secret, girdiler)  # her temadan sonra: yarıda kesilirse yapılan iş kaybolmaz
    return girdiler


def paket_girdileri(girdiler: list[dict]) -> list[dict]:
    """Pakete girebilecek (gerçekten denenmiş, sınırı yazılı) girdiler (F13)."""
    return [g for g in girdiler if g.get("kaynak") != "atlandi" and g.get("komut") and g.get("cikti") and g.get("model")
            and (g.get("sinir") or "").strip()]


def ucretsiz_sec(girdiler: list[dict], n: int) -> list[dict]:
    """Ücretsiz başlangıç paketi: kategorilerden sırayla birer komut (her alandan tadımlık)."""
    gruplar: dict = {}
    for g in girdiler:
        gruplar.setdefault(g.get("kategori") or "", []).append(g)
    secilen, i = [], 0
    while len(secilen) < n and any(i < len(v) for v in gruplar.values()):
        for v in gruplar.values():
            if i < len(v) and len(secilen) < n:
                secilen.append(v[i])
        i += 1
    return secilen


def ozet(girdiler: list[dict], simdi: datetime) -> dict:
    return {"sayi": len(girdiler), "kategoriler": sorted({g.get("kategori") or "More" for g in girdiler}),
            "modeller": sorted({g["model"] for g in girdiler if g.get("model")}), "tarih": simdi.date().isoformat()}


def ozet_yaz(o: dict) -> None:
    OZET_DOSYA.write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def ozet_oku() -> dict | None:
    try:
        return json.loads(OZET_DOSYA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None
