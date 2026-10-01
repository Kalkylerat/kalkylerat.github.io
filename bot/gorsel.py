"""Günün kuponu için paylaşılabilir kart görseli (PNG). Tweet metniyle aynı bilgiyi taşır."""

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT
from .kayit import kar, kupon_ayaklari, kupon_durumu, kupon_kar, kupon_olasilik, kupon_oran, kuponlar
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


def _ust(im, d, tarih_iso: str, sag_alt: str) -> None:
    """Ortak başlık: logo + marka solda, tarih ve (kasa gibi) bir bilgi sağda."""
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
    tarih = datetime.fromisoformat(tarih_iso).strftime("%-d %b %Y").upper()
    f = _font(30, True)
    d.text((BOYUT - KENAR - d.textlength(tarih, font=f), KENAR + 8), tarih, font=f, fill=VURGU)
    d.text((BOYUT - KENAR - d.textlength(sag_alt, font=f), KENAR + 56), sag_alt, font=f, fill=YAZI)


def kupon_gorseli(gun: dict, kupon: dict, kasa: float, sira: int = 1, toplam: int = 1) -> bytes:
    """Bir kuponun kartı. Kasa bakiyesi başlıkta, "kupon başına %1" altta yazar."""
    secimler, birim = kupon_ayaklari(gun, kupon), gun["para"]
    kasa = kupon.get("kasa", kasa)  # kuponun oynandığı andaki kasa (önceki kuponlar düşülmüş)
    # Yükseklik maç sayısına göre: tek maçlık kuponda boşluk kalmaz (3 maçta kare).
    yuk, bosluk, alan_ust = 170, 22, 340
    kart_alt = alan_ust + len(secimler) * (yuk + bosluk) - bosluk
    serit_y = kart_alt + 35
    yukseklik = max(serit_y + 140 + 110, 700)
    im = Image.new("RGB", (BOYUT, yukseklik), ARKA)
    d = ImageDraw.Draw(im)
    ic = BOYUT - 2 * KENAR

    _ust(im, d, gun["tarih"], f"BANK {_para(kasa, birim)}")

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


def kasa_grafigi(seyir: list[tuple[str, float]], baslangic: float, birim: str) -> bytes:
    """Haftalık özet için kasa grafiği: tek seri (başlığı kendisi adlandırır), başlangıç çizgisi, son değer etiketi."""
    G_, Y_ = 1200, 675
    im = Image.new("RGB", (G_, Y_), ARKA)
    d = ImageDraw.Draw(im)
    son = seyir[-1][1]
    degisim = 100 * (son - baslangic) / baslangic
    d.text((KENAR, 48), "KALKYLERAT · VIRTUAL BANK", font=_font(26, True), fill=SOLUK)
    d.text((KENAR, 86), f"{_para(son, birim)}", font=_font(64, True), fill=YAZI)
    f = _font(34, True)
    x0 = KENAR + d.textlength(_para(son, birim), font=_font(64, True)) + 24
    d.text((x0, 110), f"{degisim:+.1f}% since start", font=f, fill=VURGU if degisim >= 0 else (255, 107, 97))

    sol, sag, ust, alt = KENAR + 110, G_ - KENAR - 150, 210, Y_ - 110
    degerler = [k for _, k in seyir] + [baslangic]
    aralik = max(max(degerler) - min(degerler), baslangic * 0.01)
    adim_y = next(a for a in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000) if aralik / a <= 4)
    lo = (min(degerler) // adim_y) * adim_y
    hi = -(-max(degerler) // adim_y) * adim_y
    if hi - lo < 2 * adim_y:
        hi += adim_y
    cizgiler = [lo + adim_y * k for k in range(int((hi - lo) / adim_y) + 1)]

    def y(v):
        return alt - (v - lo) / (hi - lo) * (alt - ust)

    def x(i):
        return sol + (sag - sol) * (i / max(len(seyir) - 1, 1))

    izgara = (27, 44, 70)
    fk = _font(22)
    for v in cizgiler:  # sessiz ızgara, yuvarlak eksen değerleri
        d.line((sol, y(v), sag, y(v)), fill=izgara, width=1)
        etiket = _para(v, birim)
        d.text((sol - 16 - d.textlength(etiket, font=fk), y(v) - 13), etiket, font=fk, fill=SOLUK)
    # başlangıç çizgisi (kesikli)
    yb = y(baslangic)
    for xx in range(int(sol), int(sag), 18):
        d.line((xx, yb, min(xx + 9, sag), yb), fill=SOLUK, width=2)
    d.text((sag + 12, yb - 13), "start", font=fk, fill=SOLUK)
    noktalar = [(x(i), y(k)) for i, (_, k) in enumerate(seyir)]
    d.line(noktalar, fill=VURGU, width=5, joint="curve")
    for px, py in noktalar:
        d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=VURGU, outline=ARKA, width=3)
    px, py = noktalar[-1]
    d.text((px + 14, py - 16), _para(son, birim), font=_font(26, True), fill=YAZI)
    # tarih etiketleri: ilk, son ve arada birkaç tane
    adim = max(1, len(seyir) // 6)
    for i, (t, _) in enumerate(seyir):
        if i % adim == 0 or i == len(seyir) - 1:
            e = datetime.fromisoformat(t).strftime("%-d %b")
            d.text((x(i) - d.textlength(e, font=fk) / 2, alt + 14), e, font=fk, fill=SOLUK)
    altyazi = "Every coupon posted before kick-off · all results counted · 18+ | Play responsibly"
    altyazi, f = _sigdir(d, altyazi, G_ - 2 * KENAR, 22)
    d.text(((G_ - d.textlength(altyazi, font=f)) / 2, Y_ - 48), altyazi, font=f, fill=SOLUK)
    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()


KAYIP = (255, 107, 97)


def sonuc_gorseli(gun: dict, kasa: float, kasa_degisim: float) -> bytes:
    """Sonuç kartı: maç maç skor ve ✔/✘, kupon kâr/zararı, güncel kasa. Kupon kartıyla aynı tasarım."""
    birim, secimler, liste = gun["para"], gun["secimler"], kuponlar(gun)
    yuk, bosluk, alan_ust = 150, 18, 340
    kart_alt = alan_ust + len(secimler) * (yuk + bosluk) - bosluk
    serit_y = kart_alt + 35
    yukseklik = max(serit_y + 140 + 110, 700)
    im = Image.new("RGB", (BOYUT, yukseklik), ARKA)
    d = ImageDraw.Draw(im)
    ic = BOYUT - 2 * KENAR
    _ust(im, d, gun["tarih"], f"BANK {_para(kasa, birim)}")
    durumlar = [kupon_durumu(gun, k) for k in liste]
    if len(liste) == 1:
        baslik = {"tuttu": "COUPON WON", "yatti": "COUPON LOST", "iptal": "COUPON VOID"}.get(durumlar[0], "RESULTS")
    else:
        baslik = f"RESULTS · {durumlar.count('tuttu')} OF {len(liste)} COUPONS WON"
    renk = VURGU if "tuttu" in durumlar else (KAYIP if "yatti" in durumlar else YAZI)
    b, f = _sigdir(d, baslik, ic, 64, True)
    d.text((KENAR, 230), b, font=f, fill=renk)
    isaret = {"kazandi": ("✔", VURGU), "kaybetti": ("✘", KAYIP), "iptal": ("–", SOLUK), "bekliyor": ("…", SOLUK)}
    for i, s in enumerate(secimler):
        y = alan_ust + i * (yuk + bosluk)
        d.rounded_rectangle((KENAR, y, BOYUT - KENAR, y + yuk), radius=22, fill=KART)
        sol, sag = KENAR + 34, BOYUT - KENAR - 34
        skor = (s.get("skor") or "–").replace("-", " – ")
        f_skor = _font(46, True)
        skor_gen = d.textlength(skor, font=f_skor)
        metin_gen = ic - 68 - skor_gen - 90
        mac, f = _sigdir(d, f'{s["ev"]} v {s["dep"]}', metin_gen, 34, True)
        d.text((sol, y + 22), mac, font=f, fill=YAZI)
        secim, f = _sigdir(d, s["kisa"], metin_gen, 28)
        d.text((sol, y + 82), secim, font=f, fill=SOLUK)
        k, r = isaret[s["durum"]]
        fk = _font(54, True)
        d.text((sag - d.textlength(k, font=fk), y + 40), k, font=fk, fill=r)
        d.text((sag - 80 - skor_gen, y + 46), skor, font=f_skor, fill=YAZI)
    toplam_kar = sum(kupon_kar(gun, k_) for k_ in liste) + sum(kar(s_) for s_ in secimler)
    kutular = [("COUPON" if len(liste) == 1 else "COUPONS", f'{"+" if toplam_kar >= 0 else "-"}{_para(abs(toplam_kar), birim)}'),
               ("BANK", _para(kasa, birim)), ("SINCE START", f"{kasa_degisim:+.1f}%")]
    y = serit_y
    d.rounded_rectangle((KENAR, y, BOYUT - KENAR, y + 140), radius=22, outline=renk if renk != YAZI else VURGU, width=3)
    x = KENAR
    for (etiket, deger), oran in zip(kutular, [0.33, 0.37, 0.30]):
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

