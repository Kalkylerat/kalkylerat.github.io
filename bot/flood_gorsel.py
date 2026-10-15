"""Prompt Proof görselleri: Instagram carousel slaytları (JPEG, 4:5), X için PNG kartı, logo ve kapak.

Marka: koyu lacivert zemin, elektrik yeşili vurgu. Her görsel yalnızca kayıttaki metni taşır; ek rakam üretmez.
Instagram yayın API'si yalnızca JPEG kabul eder (SOZLESME F8), bu yüzden slaytlar JPEG'dir."""

import io
import textwrap
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import config

FONT = config.ROOT / "marka" / "font"
MARKA = config.ROOT / "marka"
ZEMIN, YESIL, BEYAZ, SOLUK, KART = "#0B1220", "#35E0A1", "#F3F5F7", "#8FA0B5", "#142038"
G, Y = 1080, 1350  # Instagram 4:5
AD = "Prompt Proof"


@lru_cache(maxsize=64)
def _font(ad: str, boyut: int) -> ImageFont.FreeTypeFont:
    if ad == "mono":
        return ImageFont.truetype(str(FONT / "DejaVuSansMono.ttf"), boyut)
    if ad == "monokalin":
        return ImageFont.truetype(str(FONT / "DejaVuSansMono-Bold.ttf"), boyut)
    if ad == "anton":
        return ImageFont.truetype(str(FONT / "Anton-Regular.ttf"), boyut)
    f = ImageFont.truetype(str(FONT / "BricolageGrotesque.ttf"), boyut)
    f.set_variation_by_axes([96, 800 if ad == "kalin" else 500, 100])
    return f


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


def logo(cap: int = 800) -> Image.Image:
    """Profil fotoğrafı: koyu zemin, yeşil 'P' ve onay işareti. Dairesel kırpmada kesilmeyecek kadar içeride."""
    im = Image.new("RGB", (cap, cap), ZEMIN)
    d = ImageDraw.Draw(im)
    f = _font("anton", int(cap * 0.62))
    kutu = d.textbbox((0, 0), "P", font=f)
    px = (cap - (kutu[2] - kutu[0])) // 2 - kutu[0] - int(cap * 0.04)
    py = (cap - (kutu[3] - kutu[1])) // 2 - kutu[1]
    d.text((px, py), "P", font=f, fill=YESIL)
    t = cap / 800  # onay işareti, P'nin sağ altında
    d.line([(cap * 0.58, cap * 0.60), (cap * 0.66, cap * 0.69), (cap * 0.82, cap * 0.47)], fill=BEYAZ, width=int(34 * t), joint="curve")
    return im


def kapak(g: int = 1500, y: int = 500) -> Image.Image:
    """X başlık görseli 1500x500: sol güvenli bölgede ad ve slogan (profil fotoğrafı sol altı kapatır)."""
    im = Image.new("RGB", (g, y), ZEMIN)
    d = ImageDraw.Draw(im)
    for i in range(0, g, 60):  # ince ızgara
        d.line([(i, 0), (i, y)], fill="#0F1A2E", width=1)
    for j in range(0, y, 60):
        d.line([(0, j), (g, j)], fill="#0F1A2E", width=1)
    d.rectangle((520, 110, 530, 380), fill=YESIL)
    d.text((570, 90), AD, font=_font("anton", 128), fill=BEYAZ)
    d.text((574, 275), "Trending problems, fixed with AI.", font=_font("kalin", 44), fill=YESIL)
    d.text((574, 340), "Every prompt tested before it's posted.", font=_font("normal", 38), fill=SOLUK)
    return im


def _jpeg(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.save(b, "JPEG", quality=88, optimize=True, subsampling=0)
    return b.getvalue()


def _png(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def _cerceve(im: Image.Image, d: ImageDraw.ImageDraw, no: int, toplam: int) -> None:
    d.text((72, 64), AD, font=_font("kalin", 34), fill=YESIL)
    if toplam > 1:
        t = f"{no}/{toplam}"
        d.text((G - 72 - d.textlength(t, font=_font("kalin", 30)), 66), t, font=_font("kalin", 30), fill=SOLUK)
    im.paste(logo(64).resize((64, 64)), (G - 72 - 64, Y - 64 - 64))


def slayt(baslik: str, metin: str, no: int, toplam: int, tur: str = "icerik", komut: str | None = None) -> Image.Image:
    """tur: 'kapak' (büyük kanca), 'icerik' (başlık + metin), 'komut' (mono komut kartı), 'son' (kaydet/gönder çağrısı)."""
    im = Image.new("RGB", (G, Y), ZEMIN)
    d = ImageDraw.Draw(im)
    _cerceve(im, d, no, toplam)
    genis = G - 144
    if tur == "kapak":
        f, s = _sar(d, baslik, "anton", 118, genis, 6, 64)
        y = max(220, (Y - len(s) * int(f.size * 1.15)) // 2 - 60)
        y = _yaz(d, (72, y), s, f, BEYAZ, 1.15)
        d.rectangle((72, y + 24, 72 + 140, y + 34), fill=YESIL)
        if metin:
            f2, s2 = _sar(d, metin, "normal", 40, genis, 3)
            _yaz(d, (72, y + 70), s2, f2, SOLUK)
        d.text((72, Y - 120), "Swipe →", font=_font("kalin", 38), fill=YESIL)
        return im
    f, s = _sar(d, baslik, "kalin", 64, genis, 3, 40)
    y = _yaz(d, (72, 190), s, f, YESIL if tur != "son" else BEYAZ, 1.2) + 30
    if tur == "komut" and komut:
        d.rounded_rectangle((72, y, G - 72, y + 20), radius=0, fill=ZEMIN)
        fk, sk = _sar(d, komut, "mono", 34, genis - 80, 15, 22)
        alt = y + 56 + len(sk) * int(fk.size * 1.4)
        d.rounded_rectangle((72, y, G - 72, alt), radius=24, fill=KART, outline=YESIL, width=3)
        _yaz(d, (112, y + 36), sk, fk, BEYAZ, 1.4)
        y = alt + 40
    if metin:
        f2, s2 = _sar(d, metin, "normal", 46, genis, 11, 30)
        _yaz(d, (72, y), s2, f2, BEYAZ, 1.35)
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
    """X'te ilk posta eklenen kart (PNG, yatay-ağırlıklı değil 4:5; X zaten kırpmadan gösterir)."""
    return _png(slayt(baslik, metin, 1, 1, "komut" if komut else "kapak", komut))


def marka_uret(klasor=MARKA) -> list[str]:
    """Profil fotoğrafı ve kapak; X ve Instagram aynı logoyu kullanır."""
    yollar = {"prompt_proof_logo.png": logo(800), "prompt_proof_kapak.png": kapak()}
    for ad, im in yollar.items():
        im.save(klasor / ad, "PNG", optimize=True)
    return list(yollar)


if __name__ == "__main__":
    print("Marka görselleri:", marka_uret())
