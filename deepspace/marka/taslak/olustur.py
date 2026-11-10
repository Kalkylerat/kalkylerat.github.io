"""Marka kiti taslağı: A2 (banner/profil) ve B3 (001 kapağı) üstüne marka yazıları. Sahibinin tek seferlik onayı için."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, r"C:\Users\atici\Desktop\DeepSpaceLog\depo")
from deepspace.renk import marka_filtresi, uygula  # noqa: E402
from deepspace.sahne import probe_sprite  # noqa: E402

D = Path(sys.argv[1])
FONT = r"C:\Users\atici\Desktop\DeepSpaceLog\depo\deepspace\font"
AMBER, YAZI, ARKA = (232, 196, 138), (240, 240, 245), (5, 7, 15)


def f(boy, kalin=False):
    return ImageFont.truetype(FONT + ("\\SpaceMono-Bold.ttf" if kalin else "\\SpaceMono-Regular.ttf"), boy)


def filtrele(img):
    t = marka_filtresi()
    return Image.fromarray(uygula(np.asarray(img.convert("RGB")), t)) if t else img.convert("RGB")


def aralikli(dr, metin, font, iz, cx, y, renk, golge=True):
    gen = sum(font.getlength(c) for c in metin) + iz * (len(metin) - 1)
    x = cx - gen / 2
    for c in metin:
        if golge:
            dr.text((x + 2, y + 2), c, font=font, fill=(0, 0, 0, 160))
        dr.text((x, y), c, font=font, fill=renk)
        x += font.getlength(c) + iz
    return gen


def probe(img, x, y, boy):
    rgb, alfa = probe_sprite(boy)
    s = Image.fromarray((np.concatenate([rgb, alfa], axis=2) * 255).astype(np.uint8), "RGBA")
    img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))


def baslik_blogu(img, ust, alt, y, boy, iz, alt_boy, alt_iz, cizgi):
    katman = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(katman)
    W = img.width
    aralikli(dr, ust, f(boy), iz, W / 2, y, YAZI)
    cy = y + boy * 1.45
    dr.line([(W / 2 - cizgi / 2, cy), (W / 2 + cizgi / 2, cy)], fill=AMBER, width=max(2, boy // 30))
    aralikli(dr, alt, f(alt_boy, True), alt_iz, W / 2, cy + alt_boy * 0.6, AMBER)
    img.alpha_composite(katman)


# 1) 001 kapağı (1280x720)
b3 = Image.open(D / "B3.png").convert("RGB")
b3 = b3.crop((0, 0, 1360, 765)).resize((1280, 720), Image.LANCZOS)
kapak = filtrele(b3).convert("RGBA")
baslik_blogu(kapak, "TRAPPIST-1", "MISSION 001  ·  DEEP FOCUS", 46, 70, 20, 22, 7, 280)
probe(kapak, 1280 * 0.84, 720 * 0.40, 54)
kapak.convert("RGB").save(D / "kapak_001.jpg", quality=90)

# 2) banner (2560x1440; yazı ortadaki 1546x423 güvenli alanda)
a2 = Image.open(D / "A2.png").convert("RGB").crop((0, 0, 1360, 765)).resize((2560, 1440), Image.LANCZOS)
banner = filtrele(a2).convert("RGBA")
baslik_blogu(banner, "DEEP SPACE LOG", "SPACE AMBIENT FOR FOCUS & SLEEP  ·  NEW MISSION WEEKLY",
             540, 120, 32, 34, 5, 560)
probe(banner, 2560 * 0.5, 1440 * 0.715, 70)
banner.convert("RGB").save(D / "banner.jpg", quality=92)
# güvenli alan kontrolü için çerçeveli kopya
g = banner.copy()
ImageDraw.Draw(g).rectangle([(2560 - 1546) / 2, (1440 - 423) / 2, (2560 + 1546) / 2, (1440 + 423) / 2],
                            outline=(255, 80, 80), width=4)
g.convert("RGB").resize((1280, 720)).save(D / "banner_guvenli_alan.jpg", quality=85)

# 3) profil (800x800): ufuk kemerinin ortası, ortada PROBE-7
a2_tam = filtrele(Image.open(D / "A2.png").convert("RGB"))
kare = a2_tam.crop((680 - 300, 0, 680 + 300, 600)).resize((800, 800), Image.LANCZOS).convert("RGBA")
karart = Image.new("RGBA", (800, 800), (5, 7, 15, 90))
kare.alpha_composite(karart)
probe(kare, 400, 330, 360)
kare.convert("RGB").save(D / "profil.png")

# 4) filigran (150x150, şeffaf): PROBE-7 + ince kehribar halka
fil = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
dr = ImageDraw.Draw(fil)
dr.ellipse([6, 6, 144, 144], fill=(5, 7, 15, 150), outline=AMBER + (230,), width=3)
probe(fil, 75, 75, 96)
fil.save(D / "filigran.png")

# 5) marka kitabı (tek sayfa)
S = Image.new("RGB", (1600, 1500), (10, 12, 20))
dr = ImageDraw.Draw(S)
aralikli(dr, "DEEP SPACE LOG  ·  BRAND KIT", f(34, True), 6, 800, 40, YAZI, golge=False)
S.paste(banner.convert("RGB").resize((1000, 562)), (40, 120))
dr.text((40, 690), "Banner 2560x1440 (yazı güvenli alanda)", font=f(18), fill=(170, 175, 190))
S.paste(kare.convert("RGB").resize((240, 240)), (1100, 120))
av = kare.convert("RGB").resize((98, 98))
m = Image.new("L", (98, 98), 0)
ImageDraw.Draw(m).ellipse([0, 0, 97, 97], fill=255)
S.paste(av, (1370, 120), m)
dr.text((1100, 370), "Profil 800x800 · 98 px daire", font=f(18), fill=(170, 175, 190))
S.paste(fil.resize((150, 150)), (1100, 420), fil)
dr.text((1270, 480), "Filigran 150x150", font=f(18), fill=(170, 175, 190))
S.paste(kapak.convert("RGB").resize((760, 428)), (40, 740))
S.paste(kapak.convert("RGB").resize((168, 94)), (820, 740))
dr.text((40, 1178), "Kapak 1280x720 (Mission 001) · sağda 168x94", font=f(18), fill=(170, 175, 190))
renkler = [("#05070f", "arka"), ("#121a2e", "gölge"), ("#3d6fb8", "ana"), ("#e8c48a", "vurgu"),
           ("#f0f0f5", "yazı"), ("#b8c0d0", "yazı 2")]
for i, (h, ad) in enumerate(renkler):
    x = 1100 + (i % 3) * 160
    y = 640 + (i // 3) * 150
    dr.rectangle([x, y, x + 130, y + 90], fill=h, outline=(60, 64, 80))
    dr.text((x, y + 98), f"{ad} {h}", font=f(16), fill=(170, 175, 190))
dr.text((1100, 960), "Yazı: Space Mono (OFL)", font=f(22, True), fill=YAZI)
dr.text((1100, 995), "Film tonu: bal_kehribar 0.55", font=f(18), fill=(170, 175, 190))
dr.text((1100, 1030), "İmza: sinyal çizgisi · görev saati", font=f(18), fill=(170, 175, 190))
dr.text((1100, 1060), "MISSION 00N · PROBE-7 ufukta", font=f(18), fill=(170, 175, 190))
dr.text((40, 1230), "Görsel dili: karanlık durgun ufuk, gökyüzünü kaplayan tek galaksi/bulutsu, bol boşluk,",
        font=f(20), fill=YAZI)
dr.text((40, 1262), "üstte ince harf aralıklı başlık. Her sahne uzayda; insan figürü yok ya da çok küçük.",
        font=f(20), fill=YAZI)
S.save(D / "marka_kitabi.jpg", quality=90)
for n in ["kapak_001.jpg", "banner.jpg", "profil.png", "filigran.png", "marka_kitabi.jpg"]:
    print(n, (D / n).stat().st_size // 1024, "KB")

# 6) film tonu karşılaştırması: tonsuz | bal_kehribar 0.55
ham = b3.convert("RGBA")
baslik_blogu(ham, "TRAPPIST-1", "MISSION 001  ·  DEEP FOCUS", 46, 70, 20, 22, 7, 280)
probe(ham, 1280 * 0.84, 720 * 0.40, 54)
K = Image.new("RGB", (1300, 380), (10, 12, 20))
K.paste(ham.convert("RGB").resize((640, 360)), (0, 0))
K.paste(kapak.convert("RGB").resize((640, 360)), (660, 0))
ImageDraw.Draw(K).text((10, 362), "A: film tonu yok", font=f(14), fill=(200, 200, 210))
ImageDraw.Draw(K).text((670, 362), "B: bal_kehribar 0.55 (bugünkü marka ayarı)", font=f(14), fill=(200, 200, 210))
K.save(D / "ton_karsilastirma.jpg", quality=90)
