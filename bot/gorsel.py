"""Günün kuponu için paylaşılabilir kart görseli (PNG). Tweet metniyle aynı bilgiyi taşır."""

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT
from .kayit import kupon_ayaklari, kupon_olasilik, kupon_oran
from .tweets import kupon_oran_metni

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


def kupon_gorseli(gun: dict, kupon: dict, kasa: float, sira: int = 1, toplam: int = 1) -> bytes:
    """Bir kuponun kartı. Kasa bakiyesi başlıkta, "kupon başına %1" altta yazar."""
    secimler, birim = kupon_ayaklari(gun, kupon), gun["para"]
    # Yükseklik maç sayısına göre: tek maçlık kuponda boşluk kalmaz (3 maçta kare).
    yuk, bosluk, alan_ust = 170, 22, 340
    kart_alt = alan_ust + len(secimler) * (yuk + bosluk) - bosluk
    serit_y = kart_alt + 35
    yukseklik = max(serit_y + 140 + 110, 700)
    im = Image.new("RGB", (BOYUT, yukseklik), ARKA)
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
    d.text((BOYUT - KENAR - d.textlength(tarih, font=f), KENAR + 8), tarih, font=f, fill=VURGU)
    bakiye = f"BANK {_para(kasa, birim)}"
    f = _font(30, True)
    d.text((BOYUT - KENAR - d.textlength(bakiye, font=f), KENAR + 56), bakiye, font=f, fill=YAZI)

    baslik = "TODAY'S COUPON" if toplam == 1 else f"COUPON {sira} OF {toplam}"
    d.text((KENAR, 230), baslik, font=_font(64, True), fill=YAZI)

    # Oyun kartları
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
    stake, oran, p = kupon["stake"], kupon_oran(gun, kupon), kupon_olasilik(gun, kupon)
    kutular = [("TOTAL ODDS" if len(secimler) > 1 else "ODDS", kupon_oran_metni(gun, kupon)),
               ("REAL CHANCE", f"{100 * p:.0f}%"),
               ("STAKE → RETURN", f"{_para(stake, birim)} → {_para(stake * oran, birim)}")]
    y = serit_y
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

    alt = f'Virtual bank · stake {gun["yuzde"]:g}% of the bank per coupon · 18+ | Play responsibly'
    alt, f = _sigdir(d, alt, ic, 22)
    d.text(((BOYUT - d.textlength(alt, font=f)) / 2, yukseklik - KENAR - 10), alt, font=f, fill=SOLUK)

    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()
