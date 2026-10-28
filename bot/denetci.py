"""Denetçi: Kalkylerat analiz postlarının yayın öncesi kod denetimi (analiz_kontrolu) ve ortak dil kuralları
(kesinlik dili, link, bahis sitesi adı, seçim dili, kısaltma); Mr. Likely ve yorum taslakları da bu kuralları kullanır."""

import re

# SÖZLEŞME A5: kısaltma yok ("Over 2.5 goals", "Both teams score", "expected goals")
KISALTMA = re.compile(r"\b(O|U)\d\.\d\b|\bBTTS\b|\bxG\b")

# ---- Ortak dil kuralları ----

_KESINLIK = re.compile(r"\block(ed)?\b|guarantee|sure (thing|win|bet)|\bbanker\b|dead cert|can'?t (lose|miss)|"
                       r"free money|100\s*%", re.IGNORECASE)
_LINK = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(com|net|org|io|co|se|uk|tr|bet|app|gg|ly|me|tv)\b|@")
_SITE = re.compile(r"bet\s*365|betfair|unibet|betway|bwin|1xbet|pinnacle|betsson|nordicbet|william\s*hill|\b888|"
                   r"betano|betvictor|comeon|marathonbet|coolbet", re.IGNORECASE)


# Analiz kartı olasılık verir, seçim yapmaz: maç sonu postunda "yanıldık/tuttu" dili yok.
_SECIM_DILI = re.compile(r"❌|✅|\bwrong\b|\bcalls? (came|come) in\b|\bcalled it\b|\bwe (got|called)\b|"
                         r"\bour (pick|call|prediction|tip)s?\b|\bheadline calls?\b", re.IGNORECASE)
_ANALIZ_PAZARLARI = ("MS1", "MSX", "MS2", "UST15", "UST25", "UST35", "KGVAR", "IYU05")


def analiz_kontrolu(tur: str, metin: str, analizler: list[dict], ayar, png: bytes | None = None) -> list[str]:
    """Analiz konsepti postlarının (kart, liste, ayrışma, maç sonu) yayın öncesi kod denetimi. Dönen her madde
    engelleyicidir. Sabit tweetin sözü: adı geçen her maçın yüzdeleri yazılır ve kayıttaki rakamlarla aynıdır;
    görsel açılır, yeterince büyüktür ve çizildiği verinin her pazarı vardır."""
    from .tweets import ANSVAR, LIMIT, LISTE_ETIKET_SINIRI, izinli_etiket, uzunluk
    hata = []
    if uzunluk(metin) > LIMIT:
        hata.append(f"280 karakteri aşıyor ({uzunluk(metin)}).")
    if _LINK.search(metin):
        hata.append("Link ya da @ içeriyor.")
    if _SITE.search(metin) or any(b.lower() in metin.lower() for b in ayar.oran_bahiscileri + [ayar.keskin_bahisci]):
        hata.append("Bahis sitesi adı içeriyor.")
    if _KESINLIK.search(metin):
        hata.append("Kesinlik dili içeriyor.")
    if not metin.rstrip().endswith(ANSVAR):
        hata.append(f"'{ANSVAR}' satırıyla bitmiyor.")
    etiketler = re.findall(r"#\w+", metin)
    liste = tur == "tablo"
    if len(etiketler) > (LISTE_ETIKET_SINIRI if liste else 1) or any(
            not izinli_etiket(e) for e in etiketler):
        hata.append(f"İzin verilmeyen ya da fazla hashtag ({' '.join(etiketler)}).")
    if tur in ("analiz", "analiz_sonuc", "tablo_sonuc", "tablo", "ayrisma", "gun_sonu") and _SECIM_DILI.search(metin):
        hata.append("Olasılığı seçim/tahmin gibi yazıyor (doğru/yanlış, ✅/❌, 'our pick'): kart seçim değil.")
    for a in analizler:
        ad = f'{a["ev"]} v {a["dep"]}'
        if ad not in metin or tur not in ("analiz", "tablo", "ayrisma"):
            continue
        # Kart postunda maç başlıkta, rakamlar alttaki blokta: bütün metin; listede ve ayrışmada maçın adının geçtiği
        # HER yerin kendi bloğu (ikinci, yüzdesiz bir anılış da yakalanır)
        bloklar = [metin] if tur == "analiz" else [metin[i:].split("\n\n")[0] for i in
                                                   (m.start() for m in re.finditer(re.escape(ad), metin))]
        yuzdeler = [y for blok in bloklar for y in re.findall(r"(\d+)%", blok)]
        if any(len(re.findall(r"\d+%", blok)) < 2 for blok in bloklar):
            hata.append(f"{ad}: adı geçiyor ama yüzdeleri yok (en az iki yüzde gerekir).")
        gecerli = {round(100 * v) for v in a["p"].values()} | {round(100 * p) for _, p in a.get("skorlar") or []}
        gecerli |= {round(100 * c[k]) for c in a.get("karsilastirma") or [] for k in ("piyasa", "istatistik")}
        yanlis = [y for y in yuzdeler if int(y) not in gecerli]
        if yanlis:
            hata.append(f"{ad}: kayıtta olmayan yüzde ({', '.join(y + '%' for y in yanlis)}).")
    if tur == "tablo" and analizler:  # SÖZLEŞME B6: listede büyük maç varsa metin onu anar (alt lig maçını değil)
        from . import analiz as _analiz
        buyukler = [a for a in analizler if _analiz.onemli(a)]
        if buyukler and not any(f'{a["ev"]} v {a["dep"]}' in metin for a in buyukler):
            hata.append("Listede büyük maç var ama metin yalnızca küçük maçları anıyor.")
    if tur == "analiz" and analizler:
        from . import analiz
        a = analizler[0]
        for c in analiz.manset(a):
            if f'{round(100 * c["p"])}%' not in metin:
                hata.append(f'{a["ev"]} v {a["dep"]}: ana çağrı "{c["ad"]}" yüzdesiyle yazılmamış.')
    for a in analizler if png is not None else []:
        eksik = [k for k in _ANALIZ_PAZARLARI if not 0 <= (a.get("p") or {}).get(k, -1) <= 1]
        if eksik or not a.get("skorlar"):
            hata.append(f'{a["ev"]} v {a["dep"]}: görselin verisi eksik ({", ".join(eksik) or "skor"}).')
    if png is not None:
        from io import BytesIO
        from PIL import Image
        try:
            with Image.open(BytesIO(png)) as im:
                if im.size[0] < 1000:
                    hata.append(f"Görsel çok küçük ({im.size}).")
        except Exception as e:
            hata.append(f"Görsel açılamıyor: {e}")
    return hata


