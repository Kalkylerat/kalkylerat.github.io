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
