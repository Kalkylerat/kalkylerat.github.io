"""Tiny Fixes görselleri: Instagram carousel slaytları (JPEG, 4:5), X için kart, logo, kapaklar ve öne çıkan kapakları.

Marka (15 Ekim 2026): sıcak krem zemin, mürekkep laciverti yazı, nane yeşili ve mercan vurgu; işaret küçük bir yara bandı
("tiny fix") ve bir pırıltı. Karakter yok. Her görsel yalnızca kayıttaki metni taşır; ek rakam üretmez.
Instagram yayın API'si yalnızca JPEG kabul eder (SOZLESME F8), bu yüzden slaytlar JPEG'dir."""

import io
import math
import textwrap
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import config

FONT = config.ROOT / "marka" / "font"
MARKA = config.ROOT / "marka"
KREM, MUREKKEP, NANE, MERCAN, GUNES, SOLUK, BEYAZ = "#FFF6EA", "#22223B", "#5ED3A8", "#FF7A6B", "#FFC94D", "#6E7191", "#FFFFFF"
NANE_ACIK, MERCAN_ACIK = "#DDF5EC", "#FFE3DE"
G, Y = 1080, 1350  # Instagram 4:5
AD = "Tiny Fixes"
SLOGAN = "Small AI fixes for real problems."
ALT_SLOGAN = "Every prompt tested before we post it."
SS = 4  # kenar yumuşatma için büyük çizip küçültme katsayısı


@lru_cache(maxsize=64)
def _font(ad: str, boyut: int) -> ImageFont.FreeTypeFont:
    if ad == "mono":
        return ImageFont.truetype(str(FONT / "DejaVuSansMono.ttf"), boyut)
    if ad == "el":
        return ImageFont.truetype(str(FONT / "Caveat.ttf"), boyut)
    f = ImageFont.truetype(str(FONT / "BricolageGrotesque.ttf"), boyut)
    f.set_variation_by_axes([96, {"kalin": 800, "orta": 650}.get(ad, 450), 100])
    return f


# ---------- Marka işaretleri ----------

def _pirilti(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, renk: str) -> None:
    """Dört köşeli pırıltı (✦): ince bel, yuvarlak uçlar yerine sivri; küçük boyda da okunur."""
    ince = r * 0.28
    noktalar = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        u = r if i % 2 == 0 else ince
        noktalar.append((cx + u * math.cos(a), cy + u * math.sin(a)))
    d.polygon(noktalar, fill=renk)


def bant(boy: int, aci: float = -38, govde: str = BEYAZ, ped: str = MERCAN, cizgi: str = MUREKKEP) -> Image.Image:
    """Yara bandı simgesi (RGBA, kare): yuvarlak uçlu gövde, ortada ped, delikler, kalın mürekkep kenar (çıkartma gibi)."""
    b = boy * SS
    im = Image.new("RGBA", (b, b), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    gen, yuk = b * 0.86, b * 0.34
    x0, y0 = (b - gen) / 2, (b - yuk) / 2
    kenar = max(2, int(b * 0.035))
    d.rounded_rectangle((x0, y0, x0 + gen, y0 + yuk), radius=yuk / 2, fill=govde, outline=cizgi, width=kenar)
    pg = gen * 0.30
    d.rounded_rectangle((b / 2 - pg / 2, y0 + kenar * 1.6, b / 2 + pg / 2, y0 + yuk - kenar * 1.6), radius=yuk * 0.18,
                        fill=ped, outline=cizgi, width=max(1, kenar // 2))
    nr = yuk * 0.045
    for yan in (-1, 1):  # iki kanatta küçük delikler
        mx = b / 2 + yan * (pg / 2 + (gen / 2 - pg / 2) * 0.48)
        for dx in (-1, 1):
            for dy in (-1, 1):
                cx, cy = mx + dx * yuk * 0.12, b / 2 + dy * yuk * 0.12
                d.ellipse((cx - nr, cy - nr, cx + nr, cy + nr), fill=cizgi)
    im = im.rotate(aci, resample=Image.BICUBIC, expand=False)
    return im.resize((boy, boy), Image.LANCZOS)


def logo(cap: int = 1080, zemin: str = NANE) -> Image.Image:
    """Profil fotoğrafı (X ve Instagram aynı): nane zemin, ortada yara bandı, sağ üstte güneş sarısı pırıltı.
    Daire kırpmada hiçbir parça kesilmez (her şey merkezden yarıçapın %70'i içinde)."""
    b = cap * SS
    im = Image.new("RGB", (b, b), zemin)
    d = ImageDraw.Draw(im)
    _pirilti(d, b * 0.70, b * 0.29, b * 0.085, GUNES)
    _pirilti(d, b * 0.30, b * 0.73, b * 0.045, BEYAZ)
    im = im.resize((cap, cap), Image.LANCZOS)
    simge = bant(int(cap * 0.74))
    im.paste(simge, ((cap - simge.width) // 2, (cap - simge.height) // 2 + int(cap * 0.01)), simge)
    return im


def _yazi_genisligi(d: ImageDraw.ImageDraw, metin: str, f) -> float:
    return d.textlength(metin, font=f)


def kapak(g: int = 1500, y: int = 500) -> Image.Image:
    """X başlık görseli 1500x500. Profil fotoğrafı sol altı kapatır: yazı sağ-ortada, sol alt boş."""
    im = Image.new("RGB", (g * SS, y * SS), KREM)
    d = ImageDraw.Draw(im)
    s = SS
    for i, (cx, cy) in enumerate([(130, 90), (1420, 80), (1380, 430), (300, 60), (1180, 455)]):  # dağınık noktalar
        r = (7 if i % 2 else 5) * s
        d.ellipse((cx * s - r, cy * s - r, cx * s + r, cy * s + r), fill=[NANE, MERCAN, GUNES, MERCAN, NANE][i])
    _pirilti(d, 1300 * s, 150 * s, 30 * s, GUNES)
    _pirilti(d, 1350 * s, 215 * s, 15 * s, NANE)
    f_ad = _font("kalin", 128 * s)
    x = 560 * s
    d.text((x, 92 * s), AD, font=f_ad, fill=MUREKKEP)
    alt = 92 * s + int(f_ad.size * 1.02)
    x2 = x + d.textlength("Tiny ", font=f_ad)  # çizgi yalnızca "Fixes" altında: "y"nin kuyruğuna değmez
    d.rounded_rectangle((x2 + 4 * s, alt, x2 + d.textlength("Fixes", font=f_ad) - 4 * s, alt + 14 * s), radius=7 * s, fill=NANE)
    d.text((x + 2 * s, 280 * s), SLOGAN, font=_font("orta", 44 * s), fill=MUREKKEP)
    d.text((x + 2 * s, 342 * s), ALT_SLOGAN, font=_font("normal", 36 * s), fill=SOLUK)
    im = im.resize((g, y), Image.LANCZOS)
    simge = bant(190, aci=-30)
    im.paste(simge, (int(560 + _yazi_genisligi(d, AD, f_ad) / s + 10), 40), simge)
    return im


def one_cikan(etiket: str, renk: str = NANE, cap: int = 1080, boy: int = 1920) -> Image.Image:
    """Instagram öne çıkan hikâye kapağı (9:16; daire içinde kırpılır): renkli daire, ortada simge ve kısa ad."""
    im = Image.new("RGB", (cap * SS, boy * SS), KREM)
    d = ImageDraw.Draw(im)
    r = cap * SS * 0.36
    cx, cy = cap * SS / 2, boy * SS / 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=renk)
    if etiket == "News":
        _pirilti(d, cx, cy - r * 0.18, r * 0.42, BEYAZ)
        _pirilti(d, cx + r * 0.42, cy - r * 0.5, r * 0.16, GUNES)
    elif etiket == "Library":
        for i, (dx, dy) in enumerate([(-0.3, -0.28), (0.0, -0.28), (0.3, -0.28)]):  # üç kart, raf gibi
            w, h = r * 0.24, r * 0.6
            x0, y0 = cx + dx * r - w / 2, cy + dy * r - h / 2
            d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=w * 0.18, fill=[BEYAZ, GUNES, BEYAZ][i],
                                outline=MUREKKEP, width=int(r * 0.03))
    elif etiket == "Start":
        f = _font("kalin", int(r * 0.62))
        t = "hi"
        d.text((cx - d.textlength(t, font=f) / 2, cy - r * 0.62), t, font=f, fill=MUREKKEP)
        _pirilti(d, cx + r * 0.45, cy - r * 0.45, r * 0.14, GUNES)
    im = im.resize((cap, boy), Image.LANCZOS)
    if etiket == "Fixes":
        simge = bant(int(cap * 0.5))
        im.paste(simge, ((cap - simge.width) // 2, boy // 2 - simge.height // 2 - int(cap * 0.06)), simge)
    d = ImageDraw.Draw(im)
    f = _font("kalin", 92)
    d.text(((cap - d.textlength(etiket, font=f)) / 2, boy / 2 + cap * 0.10), etiket, font=f, fill=MUREKKEP)
    return im


# ---------- Slaytlar ----------

def _sar(d: ImageDraw.ImageDraw, metin: str, ad: str, boyut: int, genislik: int, max_satir: int, alt_sinir: int = 28):
    """Metni genişliğe göre satırlara böler; sığmazsa font küçülür. (font, satırlar) döner."""
    while True:
        f = _font(ad, boyut)
        ort = max(1.0, d.textlength("abcdefghij", font=f) / 10)
        satirlar = []
        for par in metin.split("\n"):
            satirlar += textwrap.wrap(par, width=max(8, int(genislik / ort)), break_long_words=True) or [""]
        if len(satirlar) <= max_satir or boyut <= alt_sinir:
            return f, satirlar[:max_satir]
        boyut -= 2


def _yaz(d: ImageDraw.ImageDraw, xy, satirlar, f, renk, aralik: float = 1.25) -> int:
    x, y = xy
    for s in satirlar:
        d.text((x, y), s, font=f, fill=renk)
        y += int(f.size * aralik)
    return y


def _jpeg(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=90, optimize=True, subsampling=0)
    return b.getvalue()


def _png(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def _cerceve(im: Image.Image, d: ImageDraw.ImageDraw, no: int, toplam: int) -> None:
    simge = bant(66, aci=-30)
    im.paste(simge, (60, 46), simge)
    d.text((132, 60), AD, font=_font("kalin", 34), fill=MUREKKEP)
    if toplam > 1:
        t = f"{no}/{toplam}"
        f = _font("orta", 28)
        w = d.textlength(t, font=f)
        d.rounded_rectangle((G - 72 - w - 36, 56, G - 72, 104), radius=24, fill=NANE_ACIK)
        d.text((G - 72 - w - 18, 62), t, font=f, fill=MUREKKEP)


def slayt(baslik: str, metin: str, no: int, toplam: int, tur: str = "icerik", komut: str | None = None) -> Image.Image:
    """tur: 'kapak' (büyük kanca), 'icerik' (başlık + metin), 'komut' (mono komut kartı), 'son' (kaydet/gönder çağrısı)."""
    im = Image.new("RGB", (G, Y), KREM)
    d = ImageDraw.Draw(im)
    _cerceve(im, d, no, toplam)
    genis = G - 144
    if tur == "kapak":
        _pirilti(d, G - 150, 250, 34, GUNES)
        _pirilti(d, G - 210, 318, 16, NANE)
        f, s = _sar(d, baslik, "kalin", 104, genis, 6, 60)
        y = max(230, (Y - len(s) * int(f.size * 1.12)) // 2 - 70)
        y = _yaz(d, (72, y), s, f, MUREKKEP, 1.12)
        d.rounded_rectangle((76, y + 22, 76 + 170, y + 38), radius=8, fill=NANE)
        if metin:
            f2, s2 = _sar(d, metin, "normal", 40, genis, 3)
            _yaz(d, (72, y + 72), s2, f2, SOLUK)
        etiket, f3 = "Swipe  →", _font("orta", 34)
        w = d.textlength(etiket, font=f3)
        d.rounded_rectangle((72, Y - 150, 72 + w + 56, Y - 86), radius=32, fill=MERCAN)
        d.text((100, Y - 140), etiket, font=f3, fill=BEYAZ)
        return im
    if tur == "son":
        f, s = _sar(d, baslik, "kalin", 66, genis - 96, 3, 40)
        f2, s2 = _sar(d, metin, "normal", 44, genis - 96, 8, 30) if metin else (None, [])
        yuk = 300 + len(s) * int(f.size * 1.18) + 24 + (len(s2) * int(f2.size * 1.35) if s2 else 0) + 150
        ust = max(170, (Y - yuk) // 2)
        d.rounded_rectangle((72, ust, G - 72, ust + yuk), radius=48, fill=NANE_ACIK)
        simge = bant(240, aci=-30)
        im.paste(simge, ((G - simge.width) // 2, ust + 30), simge)
        y = _yaz(d, (120, ust + 290), s, f, MUREKKEP, 1.18) + 24
        if s2:
            y = _yaz(d, (120, y), s2, f2, MUREKKEP, 1.35)
        fb, x = _font("orta", 32), 120
        for etiket, renk, yazi in (("Save it", MUREKKEP, BEYAZ), ("Send to a friend", MERCAN, BEYAZ)):
            w = d.textlength(etiket, font=fb)
            d.rounded_rectangle((x, y + 36, x + w + 56, y + 100), radius=32, fill=renk)
            d.text((x + 28, y + 46), etiket, font=fb, fill=yazi)
            x += w + 76
        return im
    f, s = _sar(d, baslik, "kalin", 62, genis, 3, 40)
    y = _yaz(d, (72, 190), s, f, MUREKKEP, 1.18) + 34
    if tur == "komut" and komut:
        fk, sk = _sar(d, komut, "mono", 33, genis - 80, 15, 22)
        alt = y + 92 + len(sk) * int(fk.size * 1.4)
        d.rounded_rectangle((80, y + 8, G - 64, alt + 8), radius=28, fill=MUREKKEP)  # gölge
        d.rounded_rectangle((72, y, G - 72, alt), radius=28, fill=BEYAZ, outline=MUREKKEP, width=4)
        d.rounded_rectangle((104, y + 26, 104 + 210, y + 70), radius=22, fill=MERCAN_ACIK)
        d.text((122, y + 32), "copy this", font=_font("orta", 28), fill=MUREKKEP)
        _yaz(d, (112, y + 92), sk, fk, MUREKKEP, 1.4)
        y = alt + 48
    if metin:
        f2, s2 = _sar(d, metin, "normal", 46, genis, 11, 30)
        _yaz(d, (72, y), s2, f2, MUREKKEP, 1.35)
    return im


def carousel(slaytlar: list[dict], komut: str | None = None) -> list[bytes]:
    """Kayıttaki slayt listesi -> JPEG listesi. İlk slayt kapak, son slayt çağrı; 'komut' varsa ilk içerik sonrası komut kartı."""
    n = len(slaytlar)
    cikti = []
    for i, s in enumerate(slaytlar, 1):
        tur = "kapak" if i == 1 else ("son" if i == n and n > 2 else s.get("tur") or "icerik")
        cikti.append(_jpeg(slayt(s.get("baslik", ""), s.get("metin", ""), i, n, tur, s.get("komut") or (komut if tur == "komut" else None))))
    return cikti


def x_karti(baslik: str, metin: str = "", komut: str | None = None) -> bytes:
    """X'te ilk posta eklenen kart (PNG, 4:5; X kırpmadan gösterir)."""
    return _png(slayt(baslik, metin, 1, 1, "komut" if komut else "kapak", komut))


# Hesap açılışında elle paylaşılacak tanıtım carousel'i (Instagram'da ilk post, X'te sabit postun görseli).
TANITIM = [
    {"baslik": "Hi, we're Tiny Fixes.", "metin": "Small AI fixes for problems people are searching for right now."},
    {"baslik": "How it works", "metin": "1. We pick a problem that is trending.\n2. We write a prompt for it.\n"
                                        "3. We run it on a real AI model before posting.\n4. We tell you where it fails."},
    {"baslik": "Our promises", "metin": "Every prompt is tested. The model is named. News only runs when two "
                                        "independent sources confirm it. No hype, no fake stories."},
    {"baslik": "Save the fixes you need", "metin": "Follow for one small, tested fix a day."},
]


def marka_uret(klasor=MARKA) -> list[str]:
    """Profil fotoğrafı, X kapağı, Instagram öne çıkan kapakları ve tanıtım carousel'i."""
    yollar = {"tiny_fixes_logo.png": logo(1080), "tiny_fixes_x_kapak.png": kapak()}
    for ad, renk in (("Start", GUNES), ("Fixes", NANE), ("News", MERCAN), ("Library", NANE_ACIK)):
        yollar[f"tiny_fixes_one_cikan_{ad.lower()}.png"] = one_cikan(ad, renk)
    for ad, im in yollar.items():
        im.save(klasor / ad, "PNG", optimize=True)
    for i, j in enumerate(carousel(TANITIM), 1):
        ad = f"tiny_fixes_tanitim_{i}.jpg"
        (klasor / ad).write_bytes(j)
        yollar[ad] = None
    return list(yollar)


if __name__ == "__main__":
    print("Marka görselleri:", marka_uret())
