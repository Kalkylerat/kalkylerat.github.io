"""Mr. Likely kupon kartı (hardal zemin, krem kupon fişi). Yalnızca kayıttaki rakamlar; bahis sitesi adı yok."""

import io
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import config

FONT = config.ROOT / "marka" / "font"
LOGO = config.ROOT / "marka" / "mr_likely_logo.png"
HARDAL, KREM, MUREKKEP, DOMATES, SOLUK, YESIL = "#E2B33F", "#F4ECD8", "#1D2622", "#D4492A", "#6D6A58", "#14503C"
GENISLIK = 1200
KAT = {1: "Single", 2: "Double", 3: "Treble", 4: "Four-fold", 5: "Five-fold", 6: "Six-fold"}


@lru_cache(maxsize=64)
def _font(ad: str, boyut: int) -> ImageFont.FreeTypeFont:
    if ad == "anton":
        return ImageFont.truetype(str(FONT / "Anton-Regular.ttf"), boyut)
    if ad == "el":
        f = ImageFont.truetype(str(FONT / "Caveat.ttf"), boyut)
        f.set_variation_by_axes([700])
        return f
    f = ImageFont.truetype(str(FONT / "BricolageGrotesque.ttf"), boyut)
    f.set_variation_by_axes([96, 800 if ad == "kalin" else 500, 100])  # optik boyut, kalınlık, genişlik
    return f


def _sigdir(d: ImageDraw.ImageDraw, metin: str, ad: str, boyut: int, genislik: int) -> ImageFont.FreeTypeFont:
    """Metin genişliğe sığana kadar font küçülür (uzun takım adları kesilmesin)."""
    while boyut > 18 and d.textlength(metin, font=_font(ad, boyut)) > genislik:
        boyut -= 2
    return _font(ad, boyut)


def _logo(cap: int) -> Image.Image:
    im = Image.open(LOGO).convert("RGB").resize((cap, cap), Image.LANCZOS)
    maske = Image.new("L", (cap * 4, cap * 4), 0)
    ImageDraw.Draw(maske).ellipse((0, 0, cap * 4 - 1, cap * 4 - 1), fill=255)
    im.putalpha(maske.resize((cap, cap), Image.LANCZOS))
    return im


def kupon_karti(kupon: dict, tarih: str) -> bytes:
    """Kupon postuna eklenen görsel: maçlar, oyunlar, oranlar, toplam oran ve tutma ihtimali."""
    ayaklar = kupon["ayaklar"]
    n = len(ayaklar)
    satir = 150 if n <= 4 else 126
    k = satir / 150
    ust = 330
    alt = ust + n * satir
    yukseklik = alt + 380
    im = Image.new("RGB", (GENISLIK, yukseklik), HARDAL)
    d = ImageDraw.Draw(im)
    # Kupon fişi: alt kenarı zikzak
    zikzak = [(90 + j * 30, yukseklik - 70 if j % 2 else yukseklik - 96) for j in range(34, -1, -1)]
    d.polygon([(90, 80), (1110, 80), (1110, yukseklik - 96), *zikzak], fill=KREM)
    im.paste(_logo(132), (146, 130), _logo(132))
    d.text((304, 190), "Mr. Likely", font=_font("kalin", 64), fill=MUREKKEP, anchor="ls")
    d.text((306, 238), KAT.get(n, f"{n}-fold"), font=_font("orta", 30), fill=SOLUK, anchor="ls")
    gun = datetime.fromisoformat(tarih)
    d.text((1050, 190), gun.strftime("%a ").upper() + str(gun.day) + gun.strftime(" %b").upper(),
           font=_font("orta", 32), fill=SOLUK, anchor="rs")
    d.rectangle((150, 290, 1050, 296), fill=MUREKKEP)
    for i, a in enumerate(ayaklar):
        y = ust + i * satir
        mac = f'{a["ev"]} v {a["dep"]}'
        d.text((150, y + 58 * k), mac, font=_sigdir(d, mac, "kalin", round(46 * k), 700), fill=MUREKKEP, anchor="ls")
        d.text((150, y + 108 * k), a["etiket"], font=_sigdir(d, a["etiket"], "orta", round(34 * k), 700), fill=SOLUK, anchor="ls")
        d.text((1050, y + 92 * k), f'{a["oran"]:.2f}', font=_font("anton", round(72 * k)), fill=MUREKKEP, anchor="rs")
        for x in range(150, 1050, 14):  # noktalı ayraç
            d.ellipse((x, y + satir - 8, x + 3, y + satir - 5), fill="#B9B29C")
    if n > 1:
        d.text((150, alt + 112), "COMBINED", font=_font("orta", 34), fill=SOLUK, anchor="ls")
    d.text((1050, alt + 134), f'{kupon["oran"]:.2f}', font=_font("anton", 120), fill=DOMATES, anchor="rs")
    d.text((150, alt + 188), f'about {round(100 * kupon["olasilik"])}% to land', font=_font("el", 62), fill=MUREKKEP, anchor="ls")
    d.text((600, yukseklik - 128), "LIKELY. NEVER CERTAIN.  ·  18+ PLAY RESPONSIBLY", font=_font("orta", 26), fill=SOLUK, anchor="ms")
    cikti = io.BytesIO()
    im.save(cikti, format="PNG", optimize=True)
    return cikti.getvalue()


def _isaret(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, durum: str) -> None:
    """Ayağın sonucu: yeşil daire içinde tik, domates daire içinde çarpı, iade için soluk daire içinde çizgi."""
    renk = {"kazandi": YESIL, "kaybetti": DOMATES}.get(durum, SOLUK)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=renk)
    w = max(6, r // 4)
    if durum == "kazandi":
        d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.36), (cx + r * 0.48, cy - r * 0.32)], fill=KREM, width=w, joint="curve")
    elif durum == "kaybetti":
        d.line([(cx - r * 0.36, cy - r * 0.36), (cx + r * 0.36, cy + r * 0.36)], fill=KREM, width=w)
        d.line([(cx - r * 0.36, cy + r * 0.36), (cx + r * 0.36, cy - r * 0.36)], fill=KREM, width=w)
    else:
        d.line([(cx - r * 0.4, cy), (cx + r * 0.4, cy)], fill=KREM, width=w)


def _damga(metin: str, renk: str) -> Image.Image:
    """Eğik lastik damga (çerçeveli yazı), saydam zeminde."""
    f = _font("anton", 84)
    olcu = ImageDraw.Draw(Image.new("L", (1, 1)))
    gen = int(olcu.textlength(metin, font=f)) + 76
    im = Image.new("RGBA", (gen, 156), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, gen - 7, 149), radius=16, outline=renk, width=10)
    d.text((gen // 2, 80), metin, font=f, fill=renk, anchor="mm")
    return im.rotate(9, expand=True, resample=Image.BICUBIC)


def sonuc_karti(kupon: dict, tarih: str) -> bytes:
    """Sonuç postuna eklenen görsel: aynı kupon fişi, her maçın skoru ve ✓/✗ işareti, üstünde LANDED / DOWN / VOID damgası.
    Yalnızca kayıttaki rakamlar; kaybeden kupon da aynı açıklıkla gösterilir."""
    ayaklar = kupon["ayaklar"]
    n = len(ayaklar)
    satir = 150 if n <= 4 else 126
    k = satir / 150
    ust = 330
    alt = ust + n * satir
    yukseklik = alt + 380
    tuttu, iade = kupon["durum"] == "tuttu", kupon["durum"] == "iade"
    im = Image.new("RGB", (GENISLIK, yukseklik), HARDAL)
    d = ImageDraw.Draw(im)
    zikzak = [(90 + j * 30, yukseklik - 70 if j % 2 else yukseklik - 96) for j in range(34, -1, -1)]
    d.polygon([(90, 80), (1110, 80), (1110, yukseklik - 96), *zikzak], fill=KREM)
    im.paste(_logo(132), (146, 130), _logo(132))
    d.text((304, 190), "Mr. Likely", font=_font("kalin", 64), fill=MUREKKEP, anchor="ls")
    d.text((306, 238), f'{KAT.get(n, f"{n}-fold")} · result', font=_font("orta", 30), fill=SOLUK, anchor="ls")
    gun = datetime.fromisoformat(tarih)
    d.text((1050, 190), gun.strftime("%a ").upper() + str(gun.day) + gun.strftime(" %b").upper(),
           font=_font("orta", 32), fill=SOLUK, anchor="rs")
    d.rectangle((150, 290, 1050, 296), fill=MUREKKEP)
    for i, a in enumerate(ayaklar):
        y = ust + i * satir
        mac = f'{a["ev"]} {a.get("skor") or "v"} {a["dep"]}'
        d.text((150, y + 58 * k), mac, font=_sigdir(d, mac, "kalin", round(46 * k), 640), fill=MUREKKEP, anchor="ls")
        etiket = f'{a["etiket"]} · {a["oran"]:.2f}'
        d.text((150, y + 108 * k), etiket, font=_sigdir(d, etiket, "orta", round(34 * k), 640), fill=SOLUK, anchor="ls")
        _isaret(d, 1002, round(y + 68 * k), round(46 * k), a.get("durum", "iade"))
        for x in range(150, 1050, 14):
            d.ellipse((x, y + satir - 8, x + 3, y + satir - 5), fill="#B9B29C")
    kazanan = sum(a.get("durum") == "kazandi" for a in ayaklar)
    if n > 1:
        d.text((150, alt + 112), "COMBINED", font=_font("orta", 34), fill=SOLUK, anchor="ls")
    oran = f'{(kupon.get("son_oran") if tuttu else None) or kupon["oran"]:.2f}'
    f_oran = _font("anton", 120)
    d.text((1050, alt + 134), oran, font=f_oran, fill=YESIL if tuttu else SOLUK, anchor="rs")
    if not tuttu:  # tutmayan kuponun oranı üstü çizili
        gen = d.textlength(oran, font=f_oran)
        d.line([(1050 - gen - 10, alt + 86), (1060, alt + 86)], fill=DOMATES, width=10)
    not_ = ("void. stake back." if iade else f"{kazanan} of {n} legs in." if n > 1 else ("in." if tuttu else "not this time."))
    d.text((150, alt + 188), not_, font=_font("el", 62), fill=MUREKKEP, anchor="ls")
    damga = _damga("VOID" if iade else "LANDED" if tuttu else "DOWN", SOLUK if iade else YESIL if tuttu else DOMATES)
    im.paste(damga, (640 - damga.width // 2, alt + 100 - damga.height // 2), damga)
    d.text((600, yukseklik - 128), "EVERY COUPON COUNTED, WINS AND LOSSES  ·  18+ PLAY RESPONSIBLY", font=_font("orta", 26), fill=SOLUK, anchor="ms")
    cikti = io.BytesIO()
    im.save(cikti, format="PNG", optimize=True)
    return cikti.getvalue()
