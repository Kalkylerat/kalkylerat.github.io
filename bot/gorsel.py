"""Günün kuponu için paylaşılabilir kart görseli (PNG). Tweet metniyle aynı bilgiyi taşır."""

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT
from .kayit import kombi_olasilik, kombi_oran

BOYUT = 1200
KENAR = 70
ARKA = (3, 15, 41)
KART = (22, 36, 58)
YAZI = (238, 242, 247)
SOLUK = (154, 167, 184)
VURGU = (25, 195, 125)
_FONT = ROOT / "marka" / "font"


def _font(boyut: int, kalin: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_FONT / ("DejaVuSans-Bold.ttf" if kalin else "DejaVuSans.ttf")), boyut)


def _sigdir(d: ImageDraw.ImageDraw, metin: str, genislik: int, boyut: int, kalin: bool = False, en_kucuk: int = 22):
    """Metni genişliğe sığana kadar küçültür; yine sığmazsa sonunu kısaltır."""
    while boyut > en_kucuk and d.textlength(metin, font=_font(boyut, kalin)) > genislik:
        boyut -= 2
    f = _font(boyut, kalin)
    while d.textlength(metin, font=f) > genislik and len(metin) > 4:
        metin = metin[:-2] + "…"
    return metin, f


def _para(x: float, birim: str) -> str:
    return f"{birim}{x:,.0f}"


def kupon_gorseli(gun: dict) -> bytes:
    secimler, birim = gun["secimler"], gun["para"]
    kupon = bool(gun.get("kombi"))
    im = Image.new("RGB", (BOYUT, BOYUT), ARKA)
    d = ImageDraw.Draw(im)
    ic = BOYUT - 2 * KENAR

    # Başlık: logo + marka + tarih
    logo_yolu = ROOT / "marka" / "logo.png"
    x = KENAR
    if logo_yolu.exists():
        logo = Image.open(logo_yolu).convert("RGB").resize((96, 96))
        maske = Image.new("L", (96, 96), 0)
        ImageDraw.Draw(maske).ellipse((0, 0, 95, 95), fill=255)
        im.paste(logo, (KENAR, KENAR), maske)
        x += 120
    d.text((x, KENAR + 8), "KALKYLERAT", font=_font(42, True), fill=YAZI)
    d.text((x, KENAR + 60), "Data-driven football picks", font=_font(24), fill=SOLUK)
    tarih = datetime.fromisoformat(gun["tarih"]).strftime("%-d %b %Y").upper()
    f = _font(30, True)
    d.text((BOYUT - KENAR - d.textlength(tarih, font=f), KENAR + 30), tarih, font=f, fill=VURGU)

    baslik = "TODAY'S COUPON" if kupon else ("TODAY'S PICK" if len(secimler) == 1 else "TODAY'S PICKS")
    d.text((KENAR, 230), baslik, font=_font(64, True), fill=YAZI)

    # Oyun kartları
    alan_ust, alan_alt = 340, 900
    bosluk = 22
    yuk = min(170, (alan_alt - alan_ust - bosluk * (len(secimler) - 1)) // max(len(secimler), 1))
    oran_gen = 190
    for i, s in enumerate(secimler):
        y = alan_ust + i * (yuk + bosluk)
        d.rounded_rectangle((KENAR, y, BOYUT - KENAR, y + yuk), radius=22, fill=KART)
        sol = KENAR + 34
        metin_gen = ic - 68 - oran_gen
        olcek = yuk / 170
        mac, f = _sigdir(d, f'{s["ev"]} v {s["dep"]}', metin_gen, int(38 * olcek), True)
        d.text((sol, y + 20 * olcek), mac, font=f, fill=YAZI)
        alt, f = _sigdir(d, f'{s["lig"]} · {s["saat"]}', metin_gen, int(24 * olcek))
        d.text((sol, y + 70 * olcek), alt, font=f, fill=SOLUK)
        secim, f = _sigdir(d, s["kisa"], metin_gen, int(32 * olcek), True)
        d.text((sol, y + 112 * olcek), secim, font=f, fill=VURGU)
        oran = f'{"≈" if s.get("bet_builder") else ""}{s["oran"]:.2f}'
        f = _font(int(50 * olcek), True)
        sag = BOYUT - KENAR - 34
        d.text((sag - d.textlength(oran, font=f), y + 30 * olcek), oran, font=f, fill=YAZI)
        sans = f'{100 * s["adil_olasilik"]:.0f}% chance'
        f = _font(int(24 * olcek))
        d.text((sag - d.textlength(sans, font=f), y + 104 * olcek), sans, font=f, fill=SOLUK)

    # Özet şeridi
    if kupon:
        stake, toplam, p = gun["kombi"]["stake"], kombi_oran(gun), kombi_olasilik(gun)
        kutular = [("TOTAL ODDS", f"{toplam:.2f}"), ("REAL CHANCE", f"{100 * p:.0f}%"),
                   ("STAKE → RETURN", f"{_para(stake, birim)} → {_para(stake * toplam, birim)}")]
    else:
        s = secimler[0]
        kutular = [("ODDS", f'{s["oran"]:.2f}'), ("REAL CHANCE", f'{100 * s["adil_olasilik"]:.0f}%'),
                   ("STAKE → RETURN", f'{_para(s["stake"], birim)} → {_para(s["stake"] * s["oran"], birim)}')]
    y = 935
    d.rounded_rectangle((KENAR, y, BOYUT - KENAR, y + 140), radius=22, outline=VURGU, width=3)
    genislikler = [0.27, 0.27, 0.46]
    x = KENAR
    for (etiket, deger), oran in zip(kutular, genislikler):
        g = ic * oran
        f = _font(22, True)
        d.text((x + (g - d.textlength(etiket, font=f)) / 2, y + 24), etiket, font=f, fill=SOLUK)
        deger, f = _sigdir(d, deger, g - 30, 44, True)
        d.text((x + (g - d.textlength(deger, font=f)) / 2, y + 62), deger, font=f, fill=YAZI)
        x += g

    alt = f'Virtual {_para(10000, birim)} challenge · {gun["yuzde"]:g}% per bet · 18+ | Play responsibly'
    alt, f = _sigdir(d, alt, ic, 22)
    d.text(((BOYUT - d.textlength(alt, font=f)) / 2, BOYUT - KENAR - 10), alt, font=f, fill=SOLUK)

    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()
