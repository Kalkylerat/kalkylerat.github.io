"""Analiz kartı, analiz tablosu ve kıyas tablosu görselleri (PNG). Kupon ve kasa görselleri 22 Ekim 2026'da kaldırıldı."""

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT
from .analiz import fark_puani

ARKA = (3, 15, 41)
KART = (22, 36, 58)
YAZI = (238, 242, 247)
SOLUK = (154, 167, 184)
VURGU = (25, 195, 125)
_FONT = ROOT / "marka" / "font"


def _font(boyut: int, kalin: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_FONT / ("DejaVuSans-Bold.ttf" if kalin else "DejaVuSans.ttf")), boyut)


def _sigdir(d: ImageDraw.ImageDraw, metin: str, genislik: int, boyut: int, kalin: bool = False, en_kucuk: int = 22,
            son: str = ""):
    """Metni genişliğe sığana kadar küçültür; yine sığmazsa sonunu kısaltır. son (ör. yüzde) hiç kısaltılmaz: takım
    adı kısalır, rakam kalır (13 Ekim: "Manchester United …" yüzdeyi yutuyordu, SÖZLEŞME A6)."""
    tam = lambda m: f"{m} {son}" if son else m
    while boyut > en_kucuk and d.textlength(tam(metin), font=_font(boyut, kalin)) > genislik:
        boyut -= 2
    f = _font(boyut, kalin)
    while d.textlength(tam(metin), font=f) > genislik and len(metin) > 4:
        metin = metin[:-2] + "…"
    return tam(metin), f


# Analiz kartı (analiz konsepti). Dil ve palet hesap başına: İngilizce hesap yeşil, Türkçe hesap altın.
# Renk anlamı sabit (22 Ekim 2026): ev sahibi ve deplasman her yerde kendi rengiyle, ikisi de eşit doygunlukta (eski
# kartta ev hep yeşil, deplasman gri çıkıyor, favori deplasmanken göz yeşili favori sanıyordu). Vurgu rengi takım rengi
# değildir: yalnızca marka ve "en olası" işareti; bölüm başlıkları soluk.
PALETLER = {
    "en": {"arka": ARKA, "kart": KART, "vurgu": VURGU, "yazi": YAZI, "soluk": SOLUK, "iyi": VURGU,
           "bar2": (70, 86, 112), "bar3": (52, 66, 90), "ev": (64, 182, 247), "dep": (255, 176, 59), "ber": (104, 118, 142)},
    "tr": {"arka": (17, 20, 24), "kart": (29, 33, 41), "vurgu": (245, 183, 0), "yazi": (242, 244, 247),
           "soluk": (150, 158, 170), "iyi": (25, 195, 125), "bar2": (90, 98, 112), "bar3": (70, 78, 92),
           "ev": (77, 166, 255), "dep": (240, 112, 92), "ber": (110, 118, 132)},
}
ETIKETLER = {
    "en": {"baslik": "MATCH ANALYSIS", "kazanan": "WHO WINS?", "beraberlik": "Draw", "fiyat": "FAIR ODDS",
           "marj": "Bookmakers' cut on this game: {m}", "marjsiz": "Bookmakers' cut: not available",
           "adil_not": "Fair odds = 1 ÷ chance, with no bookmaker margin. A lower price means paying for that margin.",
           "gol": "HOW MANY GOALS?", "gol_eksen": "total goals in the match",
           "ust": "Over 2.5 goals {p} · Under {q}", "kg": "Both teams score {p} · Not both {q}",
           "skor": "MOST LIKELY SCORES", "iy": "FIRST HALF", "iy_satir": "Goal in 1st half {p} · Level at half-time {q}",
           "not_fav": "Reality check: even at {p}, {t} fail to win about 1 time in {m}.",
           "not_skor": "Reality check: the likeliest score is only {p}. Think in ranges, not one score.",
           "bg": "Expected goals", "guven": "Data confidence", "g": {"yuksek": "High", "orta": "Medium", "dusuk": "Low"},
           "alt": "Chances, not picks · not betting advice · 18+"},
    "tr": {"baslik": "MAÇ ANALİZİ", "kazanan": "KİM KAZANIR?", "beraberlik": "Beraberlik", "fiyat": "ADİL ORAN",
           "marj": "Bahisçilerin bu maçtaki payı: {m}", "marjsiz": "Bahisçi payı: veri yok",
           "adil_not": "Adil oran = 1 ÷ ihtimal, bahisçi payı olmadan. Daha düşük oran, o payı ödemek demek.",
           "gol": "KAÇ GOL?", "gol_eksen": "maçtaki toplam gol",
           "ust": "2.5 üst {p} · 2.5 alt {q}", "kg": "Karşılıklı gol {p} · Yok {q}",
           "skor": "EN OLASI SKORLAR", "iy": "İLK YARI", "iy_satir": "İlk yarıda gol {p} · İlk yarı berabere {q}",
           "not_fav": "Gerçeklik notu: {p} ile bile {t} kabaca {m} maçta 1 kazanamıyor.",
           "not_skor": "Gerçeklik notu: en olası skor bile yalnızca {p}. Tek skora değil, aralığa bakın.",
           "bg": "Beklenen gol", "guven": "Veri güveni", "g": {"yuksek": "Yüksek", "orta": "Orta", "dusuk": "Düşük"},
           "alt": "Olasılık, tahmin değil · bahis tavsiyesi değildir · 18+"},
}


def gerceklik_notu(a: dict, dil: str = "en") -> str:
    """Kartın tek satırlık gerçeklik notu (SÖZLEŞME A10): tek maç olgusu, rakamlar kayıttan; hikâyeyi tekrar etmez."""
    from .analiz import hikaye
    e, p = ETIKETLER[dil], a["p"]
    yuzde = (lambda x: f"%{100 * x:.0f}") if dil == "tr" else (lambda x: f"{100 * x:.0f}%")
    fav = max(("MS1", "MS2"), key=lambda k: p[k])
    if p[fav] >= 0.5 and hikaye(a, dil)[0] != "favori":
        return e["not_fav"].format(p=yuzde(p[fav]), t=a["ev"] if fav == "MS1" else a["dep"], m=round(1 / (1 - p[fav])))
    return e["not_skor"].format(p=yuzde(a["skorlar"][0][1]))


def analiz_karti(a: dict, saat: str, dil: str = "en") -> bytes:
    """Tek maçın analiz kartı (1080×1350), yukarıdan aşağı: oranların hikâyesi (analiz.hikaye; postun ilk satırıyla
    aynı), kim kazanır (her sonucun yüzdesi ve adil oranı, bahisçi payı), kaç gol (toplam gol dağılımı, 2.5 alt/üst ve
    karşılıklı gol iki tarafıyla), en olası skorlar, ilk yarı, gerçeklik notu. Yalnızca oranlardan (takım istatistiği
    yok, A4); bütün rakamlar aynı Poisson modelinden ve kayıttan (A3, A6, A10)."""
    from .analiz import adil_oran, hikaye, toplam_gol_dagilimi
    r, e, p = PALETLER[dil], ETIKETLER[dil], a["p"]
    W, H, K = 1080, 1350, 60
    im = Image.new("RGB", (W, H), r["arka"])
    d = ImageDraw.Draw(im)
    yuzde = (lambda x: f"%{100 * x:.0f}") if dil == "tr" else (lambda x: f"{100 * x:.0f}%")
    d.text((K, 50), f"KALKYLERAT · {e['baslik']}", font=_font(24, True), fill=r["vurgu"])
    tarih = datetime.fromisoformat(a["baslama"]).strftime("%-d %b").upper()
    sag, f = _sigdir(d, f"{tarih} · {saat}", 360, 22, True, 16)
    d.text((W - K - d.textlength(sag, font=f), 52), sag, font=f, fill=r["soluk"])
    # Maç: takım adları kendi renklerinin noktasıyla (aşağıdaki çubukla aynı renk)
    fm = _font(50, True)
    while fm.size > 30 and d.textlength(f'{a["ev"]}  v  {a["dep"]}', font=fm) > W - 2 * K - 60:
        fm = _font(fm.size - 2, True)
    x = K
    for ad, renk, ayrac in ((a["ev"], r["ev"], "  v  "), (a["dep"], r["dep"], "")):
        t, _ = _sigdir(d, ad, (W - 2 * K - 60) // 2, fm.size, True, fm.size)
        orta = 96 + fm.size * 0.62  # nokta, küçülen yazıyla da satırın ortasında
        d.ellipse((x, orta - 9, x + 18, orta + 9), fill=renk)
        d.text((x + 28, 96), t, font=fm, fill=r["yazi"])
        x += 28 + d.textlength(t, font=fm)
        if ayrac:
            d.text((x, 96), ayrac, font=fm, fill=r["soluk"])
            x += d.textlength(ayrac, font=fm)
    lig, f = _sigdir(d, f'{a["lig"]}  ·  {e["bg"]} {a["beklenen_gol"][0]:.1f} – {a["beklenen_gol"][1]:.1f}', W - 2 * K, 24)
    d.text((K, 168), lig, font=f, fill=r["soluk"])
    # Hikâye: kartın ilk okunan cümlesi
    _, h1, h2 = hikaye(a, dil)
    for i, satir in enumerate((h1, h2)):
        t, f = _sigdir(d, satir, W - 2 * K, 38, True, 26)
        d.text((K, 222 + 50 * i), t, font=f, fill=r["yazi"] if i == 0 else r["soluk"])
    # Kim kazanır: üç sonuç aynı biçimde (yüzde çubukta, altında adı ve adil oranı); tek sonuç öne çıkmaz (A10)
    y = 350
    d.text((K, y), e["kazanan"], font=_font(21, True), fill=r["soluk"])
    y += 40
    x, cw = K, W - 2 * K
    for v, renk in zip((p["MS1"], p["MSX"], p["MS2"]), (r["ev"], r["ber"], r["dep"])):
        w = cw * v
        if w > 6:
            d.rounded_rectangle((x, y, x + w - 4, y + 64), radius=12, fill=renk)
        t = yuzde(v)
        f = _font(28, True)
        while f.size > 15 and d.textlength(t, font=f) > w - 10:
            f = _font(f.size - 2, True)
        yazi = (12, 18, 30) if renk != r["ber"] else (255, 255, 255)
        if d.textlength(t, font=f) <= w - 10:
            d.text((x + (w - 4 - d.textlength(t, font=f)) / 2, y + (64 - f.size) / 2 - 2), t, font=f, fill=yazi)
        else:  # dilim yüzdeye dar: yüzde çubuğun üstüne (yüzdesiz dilim yok, A6)
            f = _font(15, True)
            d.text((x + (w - d.textlength(t, font=f)) / 2, y - 18), t, font=f, fill=r["soluk"])
        x += w
    # Fiyat kontrolü (A10): her sonucun adil oranı büyük ve aynı biçimde; bahisçi payı kutunun köşesinde, okunur boyda
    y += 82
    d.rounded_rectangle((K, y, W - K, y + 150), radius=18, fill=r["kart"])
    d.text((K + 24, y + 18), e["fiyat"], font=_font(21, True), fill=r["soluk"])
    marj = a.get("marj")
    t = e["marj"].format(m=yuzde(marj)) if marj else e["marjsiz"]
    fm_ = _font(22, True)
    d.text((W - K - 24 - d.textlength(t, font=fm_), y + 17), t, font=fm_, fill=r["yazi"] if marj else r["soluk"])
    anahtar = ((a["ev"], r["ev"], p["MS1"]), (e["beraberlik"], r["ber"], p["MSX"]), (a["dep"], r["dep"], p["MS2"]))
    sw = (W - 2 * K - 48) // 3
    boy = min(_sigdir(d, ad, sw - 34, 22, True, 14)[1].size for ad, _, _ in anahtar)
    for i, (ad, renk, v) in enumerate(anahtar):
        x = K + 24 + i * sw
        t, f = _sigdir(d, ad, sw - 34, boy, True, boy)
        d.ellipse((x, y + 62, x + 14, y + 76), fill=renk)
        d.text((x + 22, y + 57), t, font=f, fill=r["yazi"])
        d.text((x + 22, y + 92), adil_oran(v), font=_font(38, True), fill=r["yazi"])
    t = e["adil_not"]
    y += 166
    t, f = _sigdir(d, t, W - 2 * K, 19, en_kucuk=14)
    d.text((K, y - 4), t, font=f, fill=r["soluk"])
    # Kaç gol: toplam gol dağılımı (sütunlar), en olası sütun vurgulu
    y += 30
    d.rounded_rectangle((K, y, W - K, y + 300), radius=18, fill=r["kart"])
    d.text((K + 24, y + 18), e["gol"], font=_font(21, True), fill=r["soluk"])
    t = e["gol_eksen"]
    d.text((W - K - 24 - d.textlength(t, font=_font(19)), y + 20), t, font=_font(19), fill=r["soluk"])
    dag = toplam_gol_dagilimi(a, 6)
    en = max(dag[:-1])  # "6+" birden çok sayının toplamı: en olası işareti yalnızca tek bir gol sayısına
    gx, gw, taban, boy = K + 30, (W - 2 * K - 60) / len(dag), y + 216, 130
    for i, v in enumerate(dag):
        h = max(4, boy * v / max(dag))
        renk = r["vurgu"] if v == en else r["bar2"]
        cx = gx + gw * i
        d.rounded_rectangle((cx + 12, taban - h, cx + gw - 12, taban), radius=8, fill=renk)
        t = yuzde(v)
        f = _font(22, v == en)
        d.text((cx + (gw - d.textlength(t, font=f)) / 2, taban - h - 30), t, font=f, fill=r["yazi"] if v == en else r["soluk"])
        t = str(i) if i < len(dag) - 1 else f"{i}+"
        f = _font(22, True)
        d.text((cx + (gw - d.textlength(t, font=f)) / 2, taban + 10), t, font=f, fill=r["yazi"])
    for i, satir in enumerate((e["ust"].format(p=yuzde(p["UST25"]), q=yuzde(p["ALT25"])),
                               e["kg"].format(p=yuzde(p["KGVAR"]), q=yuzde(p["KGYOK"])))):
        t, f = _sigdir(d, satir, (W - 2 * K - 72) // 2, 21)
        d.text((K + 24 + i * ((W - 2 * K - 48) // 2), y + 262), t, font=f, fill=r["yazi"])
    y += 322
    # En olası skorlar
    d.text((K, y), e["skor"], font=_font(21, True), fill=r["soluk"])
    cw = (W - 2 * K) / len(a["skorlar"])
    for i, (s_, v) in enumerate(a["skorlar"]):
        cx = K + cw * i + cw / 2
        fs, fp = _font(42 if i == 0 else 34, True), _font(22, i == 0)
        d.text((cx - d.textlength(s_, font=fs) / 2, y + 38 + (0 if i == 0 else 6)), s_, font=fs,
               fill=r["vurgu"] if i == 0 else r["yazi"])
        d.text((cx - d.textlength(yuzde(v), font=fp) / 2, y + 94), yuzde(v), font=fp, fill=r["soluk"])
    y += 140
    d.text((K, y), e["iy"], font=_font(21, True), fill=r["soluk"])
    ix = K + d.textlength(e["iy"], font=_font(21, True)) + 24
    t, f = _sigdir(d, e["iy_satir"].format(p=yuzde(p["IYU05"]), q=yuzde(p["IYX"])), W - K - ix, 22)
    d.text((ix, y - 1), t, font=f, fill=r["yazi"])
    y += 44
    t, f = _sigdir(d, gerceklik_notu(a, dil), W - 2 * K, 22, True, 16)
    d.text((K, y), t, font=f, fill=r["yazi"])
    y += 40
    t, f = _sigdir(d, f'{e["guven"]}: {e["g"][a["guven"]]}', W - 2 * K, 20)
    d.text((K, y), t, font=f, fill=r["soluk"])
    alt, f = _sigdir(d, e["alt"], W - 2 * K, 21)
    d.text(((W - d.textlength(alt, font=f)) / 2, H - 58), alt, font=f, fill=r["soluk"])
    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()


TABLO_ETIKETLERI = {
    "en": {"baslik": "TODAY'S ANALYSIS BOARD", "mac": "MATCH",
           "sutun": ["HOME\nWIN", "DRAW", "AWAY\nWIN", "OVER 1.5\nGOALS", "OVER 2.5\nGOALS", "OVER 3.5\nGOALS",
                     "BOTH\nSCORE", "GOAL IN\n1ST HALF", "LIKELY\nSCORE"],
           "alt": "Chances from the odds, margin removed · not betting advice · 18+"},
    "tr": {"baslik": "GÜNÜN ANALİZ TABLOSU", "mac": "MAÇ",
           "sutun": ["EV\nKAZANIR", "BERA-\nBERLİK", "DEPLASMAN\nKAZANIR", "1.5 ÜST\n(2+ GOL)", "2.5 ÜST\n(3+ GOL)",
                     "3.5 ÜST\n(4+ GOL)", "KARŞILIKLI\nGOL", "İLK YARI\nGOL", "OLASI\nSKOR"],
           "alt": "Oranlardan, marjı çıkarılmış ihtimaller · bahis tavsiyesi değildir · 18+"},
}


def analiz_tablosu(liste: list[dict], tarih_iso: str, saatler: list[str], dil: str = "en") -> bytes:
    """Günün analiz tablosu (1080 genişlik): her maç iki satır: üstte maç, lig ve saat; altta dokuz pazarın yüzdesi
    (1/X/2, 1.5/2.5/3.5 üst, karşılıklı gol, ilk yarıda gol, en olası skor ve yüzdesi). Yüzdesiz rakam yok."""
    r, e = PALETLER[dil], TABLO_ETIKETLERI[dil]
    W, K = 1080, 40
    satir = 112  # takım istatistiği satırı 22 Ekim 2026'da kalktı (SÖZLEŞME A4)
    H = 200 + satir * len(liste) + 80
    im = Image.new("RGB", (W, H), r["arka"])
    d = ImageDraw.Draw(im)
    yuzde = (lambda x: f"%{100 * x:.0f}") if dil == "tr" else (lambda x: f"{100 * x:.0f}%")
    d.text((K, 44), f"KALKYLERAT · {e['baslik']}", font=_font(26, True), fill=r["vurgu"])
    tarih = datetime.fromisoformat(tarih_iso).strftime("%-d %b %Y").upper()
    d.text((W - K - d.textlength(tarih, font=_font(24, True)), 46), tarih, font=_font(24, True), fill=r["soluk"])
    adim = (W - 2 * K) / len(e["sutun"])
    sutunlar = [(ad, K + adim * i + adim / 2) for i, ad in enumerate(e["sutun"])]
    y = 104
    fb = _font(15, True)
    for ad, x in sutunlar:  # iki satırlı, kısaltmasız sütun başlıkları
        for j, parca in enumerate(ad.split("\n")):
            d.text((x - d.textlength(parca, font=fb) / 2, y + j * 19), parca, font=fb, fill=r["soluk"])
    y += 64
    for i, (a, saat) in enumerate(zip(liste, saatler)):
        yy = y + satir * i
        if i % 2 == 0:
            d.rounded_rectangle((K - 14, yy - 8, W - K + 14, yy + satir - 14), radius=14, fill=r["kart"])
        alt = f'{a["lig"]} · {saat}'
        fa = _font(18)
        alt_gen = min(d.textlength(alt, font=fa), 420)
        alt, fa = _sigdir(d, alt, 420, 18, en_kucuk=13)
        d.text((W - K - d.textlength(alt, font=fa), yy + 6), alt, font=fa, fill=r["soluk"])
        mac, f = _sigdir(d, f'{a["ev"]} – {a["dep"]}', W - 2 * K - alt_gen - 30, 25, True, 16)
        d.text((K, yy + 2), mac, font=f, fill=r["yazi"])
        p = a["p"]
        fav = max(("MS1", "MSX", "MS2"), key=lambda k: p[k])
        kodlar = ("MS1", "MSX", "MS2", "UST15", "UST25", "UST35", "KGVAR", "IYU05")
        for kod, (_, x) in zip(kodlar, sutunlar):
            v = p[kod]
            t = yuzde(v)
            renk = r["vurgu"] if kod == fav or (kod not in ("MS1", "MSX", "MS2") and v >= 0.65) else r["yazi"]
            fv = _font(24, kod == fav)
            d.text((x - d.textlength(t, font=fv) / 2, yy + 46), t, font=fv, fill=renk)
        skor, p_skor = a["skorlar"][0]
        x = sutunlar[-1][1]
        d.text((x - d.textlength(skor, font=_font(24, True)) / 2, yy + 38), skor, font=_font(24, True), fill=r["yazi"])
        t = yuzde(p_skor)  # skorun da yüzdesi: tabloda yüzdesiz rakam olmasın
        d.text((x - d.textlength(t, font=_font(15)) / 2, yy + 68), t, font=_font(15), fill=r["soluk"])
    alt, f = _sigdir(d, e["alt"], W - 2 * K, 20)
    d.text(((W - d.textlength(alt, font=f)) / 2, H - 56), alt, font=f, fill=r["soluk"])
    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()


KIYAS_ETIKETLERI = {
    "en": {"baslik": "ODDS vs TEAM STATS", "sutun": ["HOME\nWIN", "DRAW", "AWAY\nWIN", "OVER 2.5\nGOALS", "BOTH\nSCORE"],
           "oran": "ODDS", "ist": "STATS", "kaynak": {"lig": "this season", "son5": "last 5 games"},
           "alt": "Odds: prices, margin removed · Stats: scoring averages · 10+ point gaps highlighted · 18+"},
    "tr": {"baslik": "ORANLAR vs TAKIM İSTATİSTİĞİ", "sutun": ["EV\nKAZANIR", "BERA-\nBERLİK", "DEPLASMAN\nKAZANIR",
                                                             "2.5 ÜST\n(3+ GOL)", "KARŞILIKLI\nGOL"],
           "oran": "ORAN", "ist": "İSTATİSTİK", "kaynak": {"lig": "bu sezon", "son5": "son 5 maç"},
           "alt": "Oran: marjı çıkarılmış fiyatlar · İstatistik: takımların gol ortalamaları · 10+ puan fark vurgulu · 18+"},
}


def kiyas_tablosu(liste: list[dict], tarih_iso: str, saatler: list[str], dil: str = "en") -> bytes:
    """İkinci tablo: her maçta aynı pazarın orandan ve takım istatistiğinden çıkan yüzdesi alt alta. 10 puan ve
    üstü fark vurgulu. Karşılaştırması olmayan pazar "–" (uydurma rakam yok)."""
    r, e = PALETLER[dil], KIYAS_ETIKETLERI[dil]
    W, K = 1080, 40
    satir = 136
    H = 200 + satir * len(liste) + 80
    im = Image.new("RGB", (W, H), r["arka"])
    d = ImageDraw.Draw(im)
    yuzde = (lambda x: f"%{100 * x:.0f}") if dil == "tr" else (lambda x: f"{100 * x:.0f}%")
    d.text((K, 44), f"KALKYLERAT · {e['baslik']}", font=_font(26, True), fill=r["vurgu"])
    tarih = datetime.fromisoformat(tarih_iso).strftime("%-d %b %Y").upper()
    d.text((W - K - d.textlength(tarih, font=_font(24, True)), 46), tarih, font=_font(24, True), fill=r["soluk"])
    x0 = K + 170  # solda ODDS / STATS etiketleri
    adim = (W - K - x0) / len(e["sutun"])
    sutunlar = [x0 + adim * i + adim / 2 for i in range(len(e["sutun"]))]
    fb = _font(15, True)
    for ad, x in zip(e["sutun"], sutunlar):
        for j, parca in enumerate(ad.split("\n")):
            d.text((x - d.textlength(parca, font=fb) / 2, 104 + j * 19), parca, font=fb, fill=r["soluk"])
    y = 168
    for i, (a, saat) in enumerate(zip(liste, saatler)):
        yy = y + satir * i
        if i % 2 == 0:
            d.rounded_rectangle((K - 14, yy - 8, W - K + 14, yy + satir - 14), radius=14, fill=r["kart"])
        kaynak = e["kaynak"].get(a.get("istatistik_kaynak"))
        alt = f'{a["lig"]} · {saat}'
        alt, fa = _sigdir(d, alt, 420, 18, en_kucuk=13)
        d.text((W - K - d.textlength(alt, font=fa), yy + 6), alt, font=fa, fill=r["soluk"])
        mac, f = _sigdir(d, f'{a["ev"]} – {a["dep"]}', W - 2 * K - d.textlength(alt, font=fa) - 30, 25, True, 16)
        d.text((K, yy + 2), mac, font=f, fill=r["yazi"])
        d.text((K, yy + 46), e["oran"], font=_font(17, True), fill=r["soluk"])
        etiket_ist = e["ist"] + (f" ({kaynak})" if kaynak else "")
        etiket_ist, fe = _sigdir(d, etiket_ist, x0 - K - 10, 17, True, 12)
        d.text((K, yy + 82), etiket_ist, font=fe, fill=r["soluk"])
        kars = {c["pazar"]: c for c in a.get("karsilastirma") or []}
        for kod, x in zip(("MS1", "MSX", "MS2", "UST25", "KGVAR"), sutunlar):
            c = kars.get(kod)
            oran = yuzde(c["piyasa"]) if c else yuzde(a["p"][kod])
            ist = yuzde(c["istatistik"]) if c else "–"
            fark = c and abs(fark_puani(c)) >= 10
            fo, fi = _font(23), _font(23, bool(fark))
            d.text((x - d.textlength(oran, font=fo) / 2, yy + 40), oran, font=fo, fill=r["yazi"])
            d.text((x - d.textlength(ist, font=fi) / 2, yy + 76), ist, font=fi, fill=r["vurgu"] if fark else r["soluk"])
    alt, f = _sigdir(d, e["alt"], W - 2 * K, 19)
    d.text(((W - d.textlength(alt, font=f)) / 2, H - 56), alt, font=f, fill=r["soluk"])
    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()
