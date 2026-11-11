"""Deep Space Log: "kayıt defteri" kanal kiti taslağı (banner + profil + önizleme).

Çalıştır:  py deepspace/marka/taslak/defter_kiti.py
Çıktılar (bu klasöre): banner_defter.jpg (2560x1440), profil_defter.png (800x800), onizleme_defter.jpg

Fikir: marka güzel bir galaksi fotoğrafından değil, defterin dilinden kurulur. Tek renk ince çizgi, köşe nişanları,
görev numarası, gerçek koordinat, bol siyah. Her şey kodla çizilir; ücretli görsel üretimi yok.

Kullanılan olgular (yalnız emin olunanlar):
- TRAPPIST-1, J2000: RA 23h 06m 29s, Dec -05° 02' 29"; uzaklık yaklaşık 40.7 ışık yılı.
- Yedi gezegenin yarı büyük eksenleri (AU): b 0.0115, c 0.0158, d 0.0223, e 0.0293, f 0.0385, g 0.0468, h 0.0619.
  Yörünge halkaları bu oranlarla ölçekli çizilir. Gezegenlerin halka üzerindeki yeri temsilîdir (bir an değil).
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[2]
FONT = KOK / "deepspace" / "font"
FONT_UI = KOK / "marka" / "font"

ARKA = (5, 7, 15)          # marka.toml palet.arka
GOLGE = (18, 26, 46)       # palet.golge
VURGU = (232, 196, 138)    # palet.vurgu (kehribar)
YAZI = (240, 240, 245)     # palet.yazi
IKINCIL = (184, 192, 208)  # palet.yazi_ikincil

BW, BH = 2560, 1440
GUV_W, GUV_H = 1546, 423   # her cihazda görünen orta alan
GX0, GY0 = (BW - GUV_W) // 2, (BH - GUV_H) // 2
GX1, GY1 = GX0 + GUV_W, GY0 + GUV_H

HEDEF = "TRAPPIST-1"
RA = "23h 06m 29s"
DEC = "−05° 02′ 29″"
UZAKLIK_LY = 40.7
YORUNGE_AU = [("b", 0.0115), ("c", 0.0158), ("d", 0.0223), ("e", 0.0293), ("f", 0.0385), ("g", 0.0468), ("h", 0.0619)]


def karis(a, b, t):
    """a rengi üstüne b rengini t oranında bindirir (düz zemin için saydamlık yerine)."""
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def font(boy: float, kalin: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / ("SpaceMono-Bold.ttf" if kalin else "SpaceMono-Regular.ttf")), round(boy))


def _glif_var(f: ImageFont.FreeTypeFont, ch: str) -> bool:
    return bytes(f.getmask(ch)) != bytes(f.getmask("￿")) and f.getlength(ch) > 0


def guvenli_metin(f, metin: str) -> str:
    """Fontta olmayan tipografik işaretleri düz karşılığına çevirir."""
    yedek = {"−": "-", "′": "'", "″": '"', "·": "."}
    return "".join(ch if (ch == " " or _glif_var(f, ch)) else yedek.get(ch, ch) for ch in metin)


class Tuval:
    """Kat kat büyük çizip küçülten tuval: Pillow çizgileri kenar yumuşatmasız olduğu için."""

    def __init__(self, w: int, h: int, kat: int = 2, zemin=ARKA):
        self.w, self.h, self.k = w, h, kat
        self.im = Image.new("RGB", (w * kat, h * kat), zemin)
        self.d = ImageDraw.Draw(self.im)

    def cizgi(self, x0, y0, x1, y1, renk, kalinlik=2.0):
        k = self.k
        self.d.line([(x0 * k, y0 * k), (x1 * k, y1 * k)], fill=renk, width=max(1, round(kalinlik * k)))

    def kesikli(self, x0, y0, x1, y1, renk, kalinlik=2.0, dolu=14, bos=10):
        uz = math.hypot(x1 - x0, y1 - y0)
        n = int(uz // (dolu + bos)) + 1
        for i in range(n):
            a = i * (dolu + bos)
            b = min(a + dolu, uz)
            if a >= uz:
                break
            self.cizgi(x0 + (x1 - x0) * a / uz, y0 + (y1 - y0) * a / uz,
                       x0 + (x1 - x0) * b / uz, y0 + (y1 - y0) * b / uz, renk, kalinlik)

    def halka(self, cx, cy, r, renk, kalinlik=2.0, d=None):
        k = self.k
        (d or self.d).ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], outline=renk,
                              width=max(1, round(kalinlik * k)))

    def nokta(self, cx, cy, r, renk, d=None):
        k = self.k
        (d or self.d).ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=renk)

    def nisan(self, cx, cy, kol, renk, kalinlik=2.0, bosluk=0.0):
        """Artı biçimli nişan; bosluk > 0 ise ortası açık."""
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            self.cizgi(cx + dx * bosluk, cy + dy * bosluk, cx + dx * kol, cy + dy * kol, renk, kalinlik)

    def kose(self, x, y, sx, sy, kol, renk, kalinlik=2.0):
        """L biçimli köşe işareti; sx, sy kolların yönü (+1/-1)."""
        self.cizgi(x, y, x + sx * kol, y, renk, kalinlik)
        self.cizgi(x, y, x, y + sy * kol, renk, kalinlik)

    def yazi(self, x, y, metin, boy, renk, kalin=False, aralik=0.0, hiza="sol", d=None):
        """Taban çizgisi y olan, harf aralıklı yazı. hiza: sol | sag | orta. Genişliği döndürür."""
        k = self.k
        f = font(boy * k, kalin)
        metin = guvenli_metin(f, metin)
        gen = sum(f.getlength(ch) for ch in metin) + aralik * k * (len(metin) - 1)
        cx = x * k
        if hiza == "sag":
            cx -= gen
        elif hiza == "orta":
            cx -= gen / 2
        for ch in metin:
            (d or self.d).text((cx, y * k), ch, font=f, fill=renk, anchor="ls")
            cx += f.getlength(ch) + aralik * k
        return gen / k

    def bitir(self) -> Image.Image:
        return self.im.resize((self.w, self.h), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------------------------------------------

def banner() -> Image.Image:
    t = Tuval(BW, BH, 2)
    k = t.k
    cizgi_soluk = karis(ARKA, IKINCIL, 0.07)
    cizgi_orta = karis(ARKA, IKINCIL, 0.22)
    kehribar_soluk = karis(ARKA, VURGU, 0.45)
    etiket = karis(ARKA, IKINCIL, 0.55)

    # 1) Sessiz zemin: seyrek ızgara (16x9 bölme) ve kesişimlerde küçük artılar
    adim = 160
    for x in range(adim, BW, adim):
        t.cizgi(x, 0, x, BH, cizgi_soluk, 1)
    for y in range(adim, BH, adim):
        t.cizgi(0, y, BW, y, cizgi_soluk, 1)
    for x in range(adim, BW, adim):
        for y in range(adim, BH, adim):
            t.nisan(x, y, 7, karis(ARKA, IKINCIL, 0.2), 1.5)

    # 2) Seyrek yıldızlar (sabit tohum; güvenli alanın dışında)
    rs = random.Random(7)
    for _ in range(230):
        x, y = rs.uniform(0, BW), rs.uniform(0, BH)
        if GX0 - 30 < x < GX1 + 30 and GY0 - 30 < y < GY1 + 30:
            continue
        p = rs.random()
        r = 1.0 + 1.8 * p * p
        t.nokta(x, y, r, karis(ARKA, IKINCIL, 0.18 + 0.5 * rs.random()))

    # 3) TRAPPIST-1 yörünge şeması (ölçekli), sağ üstte; güvenli alana girerken söner
    cx, cy, olcek = 1880, 330, 5600.0   # piksel / AU
    kat = Image.new("RGB", t.im.size, (0, 0, 0))
    kd = ImageDraw.Draw(kat)
    acilar = {"b": 205, "c": 320, "d": 250, "e": 150, "f": 295, "g": 225, "h": 200}   # temsilî (derece, saat yönü)
    for i, (ad, au) in enumerate(YORUNGE_AU):
        r = au * olcek
        t.halka(cx, cy, r, (255, 255, 255), 1.6, d=kd)
    maske = Image.new("L", t.im.size, 255)
    ImageDraw.Draw(maske).rectangle([(GX0 - 40) * k, (GY0 - 50) * k, (GX1 + 40) * k, (GY1 + 50) * k], fill=0)
    maske = maske.filter(ImageFilter.GaussianBlur(45 * k))
    alfa = ImageChops.multiply(kat.convert("L"), maske).point(lambda v: int(v * 0.42))
    t.im.paste(Image.new("RGB", t.im.size, VURGU), (0, 0), alfa)
    t.d = ImageDraw.Draw(t.im)

    for ad, au in YORUNGE_AU:
        r = au * olcek
        a = math.radians(acilar[ad])
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        t.nokta(px, py, 9, ARKA)
        t.nokta(px, py, 5.5, VURGU)
        t.yazi(px + 14, py - 10, ad, 24, etiket)
    # yıldız
    t.nokta(cx, cy, 13, ARKA)
    t.nokta(cx, cy, 6, VURGU)
    t.nisan(cx, cy, 34, VURGU, 1.6, bosluk=13)
    ex = cx + YORUNGE_AU[-1][1] * olcek + 26
    t.yazi(ex, cy - 28, HEDEF, 26, VURGU, kalin=True, aralik=3)
    t.yazi(ex, cy + 8, f"RA {RA}", 22, etiket, aralik=1)
    t.yazi(ex, cy + 40, f"DEC {DEC}", 22, etiket, aralik=1)
    # ölçek çubuğu
    ox, oy = ex, cy + 112
    t.cizgi(ox, oy, ox + 0.02 * olcek, oy, cizgi_orta, 1.6)
    for xx in (ox, ox + 0.01 * olcek, ox + 0.02 * olcek):
        t.cizgi(xx, oy - 8, xx, oy + 8, cizgi_orta, 1.6)
    t.yazi(ox, oy - 20, "0.02 AU", 22, etiket, aralik=1)

    # 4) Uçuş hattı: SOL'dan TRAPPIST-1'e, 10 ışık yılında bir çentik
    sx = 300
    px_ly = (cx - sx) / UZAKLIK_LY
    t.kesikli(sx + 22, cy, cx - YORUNGE_AU[-1][1] * olcek - 16, cy, kehribar_soluk, 1.6, dolu=16, bos=12)
    t.halka(sx, cy, 13, VURGU, 1.8)
    t.nokta(sx, cy, 3, VURGU)
    t.yazi(sx, cy + 62, "SOL", 26, VURGU, kalin=True, aralik=3, hiza="orta")
    t.yazi(sx, cy + 96, "0 LY", 22, etiket, aralik=1, hiza="orta")
    for ly in (10, 20, 30):
        x = sx + ly * px_ly
        t.cizgi(x, cy - 12, x, cy + 12, kehribar_soluk, 1.6)
        t.yazi(x, cy + 62, f"{ly} LY", 22, etiket, aralik=1, hiza="orta")
    # PROBE-7 işareti (küçük baklava)
    bx = sx + 25 * px_ly
    t.d.polygon([((bx - 11) * k, cy * k), (bx * k, (cy - 11) * k), ((bx + 11) * k, cy * k), (bx * k, (cy + 11) * k)],
                fill=ARKA, outline=VURGU, width=round(1.8 * k))
    t.yazi(bx, cy - 30, "PROBE-7", 22, VURGU, aralik=2, hiza="orta")

    # 5) Dış köşe nişanları ve alt kenar cetveli (TV'de görünür, kırpılınca kaybolur)
    for (x, y) in ((96, 96), (BW - 96, 96), (96, BH - 96), (BW - 96, BH - 96)):
        t.nisan(x, y, 30, cizgi_orta, 1.6, bosluk=8)
        t.halka(x, y, 15, cizgi_orta, 1.6)
    cet_y = 1210
    t.cizgi(sx, cet_y, BW - sx, cet_y, cizgi_orta, 1.4)
    n = 98
    for i in range(n + 1):
        x = sx + (BW - 2 * sx) * i / n
        boy = 20 if i % 7 == 0 else 9
        t.cizgi(x, cet_y, x, cet_y - boy, cizgi_orta, 1.4)
    t.yazi(sx, cet_y + 44, "LOG SHEET 001", 22, etiket, aralik=3)
    t.yazi(BW - sx, cet_y + 44, "EPOCH J2000", 22, etiket, aralik=3, hiza="sag")

    # 6) Güvenli alan: defter sayfası
    ic0, ic1 = GX0 + 40, GX1 - 40
    kol = 26
    for (x, y, ax, ay) in ((GX0 + 8, GY0 + 8, 1, 1), (GX1 - 8, GY0 + 8, -1, 1),
                           (GX0 + 8, GY1 - 8, 1, -1), (GX1 - 8, GY1 - 8, -1, -1)):
        t.kose(x, y, ax, ay, kol, VURGU, 2)

    # kanal adı + sağda defter etiketi
    ad_taban = GY0 + 104
    t.yazi(ic0 - 4, ad_taban, "DEEP SPACE LOG", 84, YAZI, kalin=True, aralik=15)
    t.yazi(ic1, ad_taban - 38, "PROBE-7", 30, VURGU, kalin=True, aralik=5, hiza="sag")
    t.yazi(ic1, ad_taban, "FLIGHT LOG", 30, VURGU, aralik=5, hiza="sag")
    t.cizgi(ic0, GY0 + 136, ic1, GY0 + 136, VURGU, 2.5)

    # tablo
    sut = [("NO.", 0, "sol"), ("MISSION", 112, "sol"), ("TARGET", 408, "sol"), ("RA", 668, "sol"),
           ("DEC", 938, "sol"), ("DIST", 1212, "sol"), ("DUR", ic1 - ic0, "sag")]
    bas_y = GY0 + 182
    for ad, dx, hiza in sut:
        t.yazi(ic0 + dx, bas_y, ad, 29, etiket, aralik=2, hiza=hiza)
    t.cizgi(ic0, bas_y + 18, ic1, bas_y + 18, cizgi_orta, 1.5)

    s1 = bas_y + 68
    satir = ["001", "SEVEN WORLDS", HEDEF, RA, DEC, f"{UZAKLIK_LY} LY", "2H"]
    for (ad, dx, hiza), deger in zip(sut, satir):
        renk = VURGU if ad == "NO." else YAZI
        t.yazi(ic0 + dx, s1, deger, 33, renk, kalin=ad in ("NO.", "MISSION"), hiza=hiza)
    t.cizgi(ic0, s1 + 20, ic1, s1 + 20, cizgi_orta, 1.5)

    s2 = s1 + 66
    bos = karis(ARKA, IKINCIL, 0.32)
    t.yazi(ic0, s2, "002", 33, karis(ARKA, VURGU, 0.5), kalin=True)
    for ad, dx, hiza in sut[1:]:
        gen = {"MISSION": 230, "TARGET": 192, "RA": 212, "DEC": 232, "DIST": 138, "DUR": 40}[ad]
        x0 = ic0 + dx - (gen if hiza == "sag" else 0)
        t.kesikli(x0, s2 - 11, x0 + gen, s2 - 11, bos, 1.6, dolu=6, bos=8)
    t.cizgi(ic0, s2 + 20, ic1, s2 + 20, cizgi_orta, 1.5)

    # alt satır
    t.yazi(ic0, GY1 - 34, "SPACE AMBIENT MUSIC FOR SLEEP & DEEP FOCUS", 30, IKINCIL, aralik=4)

    return t.bitir()


# ---------------------------------------------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------------------------------------------

def profil() -> Image.Image:
    P = 800
    t = Tuval(P, P, 4)
    k = t.k
    c = P / 2
    r, kal = 262, 30

    # yörünge halkası; sağ üstte sonda için açıklık
    aci = -42.0
    acik = 15.5
    kutu = [(c - r - kal / 2) * k, (c - r - kal / 2) * k, (c + r + kal / 2) * k, (c + r + kal / 2) * k]
    t.d.arc(kutu, aci + acik, aci - acik + 360, fill=VURGU, width=round(kal * k))
    a = math.radians(aci)
    t.nokta(c + r * math.cos(a), c + r * math.sin(a), 35, VURGU)

    # tek kalınlıkta "7"
    w = 36
    x0, x1, y0, y1 = 322, 490, 281, 524
    t.d.rectangle([x0 * k, y0 * k, x1 * k, (y0 + w) * k], fill=VURGU)
    egim = (385 - x1) / (y1 - (y0 + w / 2))               # x'in y'ye göre değişimi
    yatay = w * math.hypot(1, egim)                        # yatay kesit genişliği
    alt_kayma = egim * (y1 - y0)
    t.d.polygon([((x1 - yatay) * k, y0 * k), (x1 * k, y0 * k),
                 ((x1 + alt_kayma) * k, y1 * k), ((x1 - yatay + alt_kayma) * k, y1 * k)], fill=VURGU)

    # dört yönde ince çentik (büyük boyda defter hissi; küçükte kaybolur, işareti bozmaz)
    soluk = karis(ARKA, VURGU, 0.6)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        t.cizgi(c + dx * 318, c + dy * 318, c + dx * 352, c + dy * 352, soluk, 5)
    return t.bitir()


# ---------------------------------------------------------------------------------------------------------------
# Önizleme paftası
# ---------------------------------------------------------------------------------------------------------------

def _daire(im: Image.Image, boy: int) -> Image.Image:
    kucuk = im.resize((boy, boy), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (boy * 4, boy * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, boy * 4 - 1, boy * 4 - 1], fill=255)
    kucuk.putalpha(m.resize((boy, boy), Image.LANCZOS))
    return kucuk


def _yuvarlak(im: Image.Image, r: int) -> Image.Image:
    im = im.convert("RGBA")
    m = Image.new("L", (im.width * 2, im.height * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width * 2 - 1, im.height * 2 - 1], radius=r * 2, fill=255)
    im.putalpha(m.resize(im.size, Image.LANCZOS))
    return im


def onizleme(ban: Image.Image, pro: Image.Image) -> Image.Image:
    PW, PH = 2360, 1300
    sayfa = Image.new("RGB", (PW, PH * 2), (0, 0, 0))
    ui = lambda b, kalin=False: ImageFont.truetype(str(FONT_UI / ("DejaVuSans-Bold.ttf" if kalin else "DejaVuSans.ttf")), b)
    temalar = [("DARK", (15, 15, 15), (241, 241, 241), (170, 170, 170)),
               ("LIGHT", (255, 255, 255), (15, 15, 15), (96, 96, 96))]
    for i, (ad, zemin, metin, gri) in enumerate(temalar):
        p = Image.new("RGB", (PW, PH), zemin)
        d = ImageDraw.Draw(p)
        d.text((60, 36), f"{ad} THEME", font=ui(26, True), fill=gri)

        # banner, TV (tam kare)
        d.text((60, 92), "Banner · TV (2560x1440, full image)", font=ui(22), fill=gri)
        tv = ban.resize((1280, 720), Image.LANCZOS)
        p.paste(tv, (60, 130))
        # banner, mobil (güvenli alan)
        d.text((60, 880), "Banner · mobile crop (safe area 1546x423)", font=ui(22), fill=gri)
        mob = ban.crop((GX0, GY0, GX1, GY1)).resize((1280, round(1280 * GUV_H / GUV_W)), Image.LANCZOS)
        mob = _yuvarlak(mob, 14)
        p.paste(mob, (60, 918), mob)

        # profil 800
        d.text((1420, 92), "Profile · 800 px", font=ui(22), fill=gri)
        p.paste(pro, (1420, 130))
        hd = ImageDraw.Draw(p)
        hd.ellipse([1420, 130, 2219, 929], outline=(90, 90, 90), width=1)

        # 98 px daire + kanal başlığı taklidi
        d.text((1420, 970), "98 px", font=ui(22), fill=gri)
        d98 = _daire(pro, 98)
        p.paste(d98, (1420, 1010), d98)
        d.text((1540, 1018), "Deep Space Log", font=ui(34, True), fill=metin)
        d.text((1540, 1066), "@deepspacelogmusic", font=ui(20), fill=gri)

        # 40 px daire + yorum satırı taklidi
        d.text((1420, 1150), "40 px", font=ui(22), fill=gri)
        d40 = _daire(pro, 40)
        p.paste(d40, (1420, 1190), d40)
        d.text((1476, 1188), "@deepspacelogmusic", font=ui(17, True), fill=metin)
        d.text((1476, 1212), "Where should PROBE-7 go next?", font=ui(17), fill=metin)

        sayfa.paste(p, (0, i * PH))
    return sayfa


def main() -> None:
    ban = banner()
    pro = profil()
    ban.save(BURASI / "banner_defter.jpg", quality=93, subsampling=0, optimize=True)
    pro.save(BURASI / "profil_defter.png", optimize=True)
    onizleme(ban, pro).save(BURASI / "onizleme_defter.jpg", quality=92, subsampling=0)
    for ad in ("banner_defter.jpg", "profil_defter.png", "onizleme_defter.jpg"):
        yol = BURASI / ad
        print(f"{ad}: {Image.open(yol).size}, {yol.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
