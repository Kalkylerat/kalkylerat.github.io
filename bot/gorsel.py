"""Günün kuponu için paylaşılabilir kart görseli (PNG). Tweet metniyle aynı bilgiyi taşır."""

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from .config import ROOT
from .kayit import kar, kupon_ayaklari, kupon_durumu, kupon_kar, kupon_olasilik, kupon_oran, kuponlar
from .kayit import kupon_bakiyesi
from .analiz import fark_puani
from .tweets import gun_donen, kupon_oran_metni

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
    return f"{'-' if round(x, 2) < 0 else ''}{birim}{abs(x):,.2f}"


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
    bakiye = kupon_bakiyesi(kupon, kasa)  # oynandığı andaki bakiyeden bu kuponun stake'i de düşülmüş
    # Yükseklik maç sayısına göre: tek maçlık kuponda boşluk kalmaz (3 maçta kare).
    yuk, bosluk, alan_ust = 170, 22, 340
    kart_alt = alan_ust + len(secimler) * (yuk + bosluk) - bosluk
    serit_y = kart_alt + 35
    yukseklik = max(serit_y + 140 + 110, 700)
    im = Image.new("RGB", (BOYUT, yukseklik), ARKA)
    d = ImageDraw.Draw(im)
    ic = BOYUT - 2 * KENAR

    _ust(im, d, gun["tarih"], f"BALANCE {_para(bakiye, birim)}")

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

    alt = f'Virtual bank · stake {gun["yuzde"]:g}% of the balance per coupon · 18+ | Play responsibly'
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


def sonuc_gorseli(gun: dict, ozet: dict) -> bytes:
    """Sonuç kartı: maç maç skor ve ✔/✘, kupon kâr/zararı, güncel kasa. Kupon kartıyla aynı tasarım."""
    birim, secimler, liste = gun["para"], gun["secimler"], kuponlar(gun)
    bakiye = ozet.get("bakiye", ozet["kasa"])
    yuk, bosluk, alan_ust = 150, 18, 340
    kart_alt = alan_ust + len(secimler) * (yuk + bosluk) - bosluk
    serit_y = kart_alt + 35
    yukseklik = max(serit_y + 140 + 110, 700)
    im = Image.new("RGB", (BOYUT, yukseklik), ARKA)
    d = ImageDraw.Draw(im)
    ic = BOYUT - 2 * KENAR
    _ust(im, d, gun["tarih"], f"BALANCE {_para(bakiye, birim)}")
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
    # Yalnızca iki rakam: dönen para (kayıpta 0, stake kupon yapılınca zaten düşmüştü) ve yeni bakiye.
    geri = gun_donen(gun)
    kutular = [("RETURN", f"+{_para(geri, birim)}" if geri else _para(0, birim)), ("BALANCE", _para(bakiye, birim))]
    y = serit_y
    d.rounded_rectangle((KENAR, y, BOYUT - KENAR, y + 140), radius=22, outline=renk if renk != YAZI else VURGU, width=3)
    x = KENAR
    for (etiket, deger), oran in zip(kutular, [0.5, 0.5]):
        g = ic * oran
        f = _font(22, True)
        d.text((x + (g - d.textlength(etiket, font=f)) / 2, y + 24), etiket, font=f, fill=SOLUK)
        deger, f = _sigdir(d, deger, g - 30, 48, True)
        d.text((x + (g - d.textlength(deger, font=f)) / 2, y + 60), deger, font=f, fill=YAZI)
        x += g
    alt = f'Virtual bank · stake {gun["yuzde"]:g}% of the balance per coupon · 18+ | Play responsibly'
    alt, f = _sigdir(d, alt, ic, 22)
    d.text(((BOYUT - d.textlength(alt, font=f)) / 2, yukseklik - KENAR - 10), alt, font=f, fill=SOLUK)
    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()



# Analiz kartı (analiz konsepti). Dil ve palet hesap başına: İngilizce hesap yeşil, Türkçe hesap altın.
PALETLER = {
    "en": {"arka": ARKA, "kart": KART, "vurgu": VURGU, "yazi": YAZI, "soluk": SOLUK, "iyi": VURGU,
           "bar2": (70, 86, 112), "bar3": (52, 66, 90)},
    "tr": {"arka": (17, 20, 24), "kart": (29, 33, 41), "vurgu": (245, 183, 0), "yazi": (242, 244, 247),
           "soluk": (150, 158, 170), "iyi": (25, 195, 125), "bar2": (90, 98, 112), "bar3": (70, 78, 92)},
}
ETIKETLER = {
    "en": {"baslik": "MATCH ANALYSIS", "ms": "MATCH RESULT", "beraberlik": "Draw", "gol": "GOALS",
           "iy": "FIRST HALF", "takim": "TEAM GOALS", "cs": "DOUBLE CHANCE", "skor": "MOST LIKELY SCORES",
           "ust": "Over", "kg": "Both teams score", "iy_ev": "{ev} ahead at half-time", "iy_x": "Level at half-time",
           "iy_u05": "Goal in 1st half", "iy_u15": "2+ goals in 1st half",
           "gol15": "Over 1.5 goals", "gol25": "Over 2.5 goals", "gol35": "Over 3.5 goals",
           "takim15": "{t}: 2+ goals", "cs1x": "{ev} or draw", "cs12": "Either team wins", "csx2": "{dep} or draw",
           "atar": "{t} to score", "bg": "Expected goals", "guven": "Data confidence",
           "g": {"yuksek": "High", "orta": "Medium", "dusuk": "Low"},
           "not": "Even the most likely score is only {p}: think in ranges, not one score.",
           "kars": "TEAM STATS vs ODDS", "piyasa": "odds", "ist": "stats",
           "kaynak": {"lig": "this season", "son5": "last 5 games"},
           "yok": "Team stats: not enough recent games to compare with the market.",
           "sadece": "No market price: every chance above comes from team stats.",
           "pazar": {"MS1": "{ev} win", "MSX": "Draw", "MS2": "{dep} win", "UST25": "Over 2.5 goals", "KGVAR": "Both teams score"},
           "alt": "Chances, not picks · not betting advice · 18+"},
    "tr": {"baslik": "MAÇ ANALİZİ", "ms": "MAÇ SONUCU", "beraberlik": "Beraberlik", "gol": "GOL ALT / ÜST",
           "iy": "İLK YARI", "takim": "TAKIM GOLLERİ", "cs": "ÇİFTE ŞANS", "skor": "EN OLASI SKORLAR",
           "ust": "Üst", "kg": "Karşılıklı gol", "iy_ev": "İlk yarı {ev} önde", "iy_x": "İlk yarı berabere",
           "iy_u05": "İlk yarıda gol olur", "iy_u15": "İlk yarıda 2+ gol",
           "gol15": "1.5 üst (2+ gol)", "gol25": "2.5 üst (3+ gol)", "gol35": "3.5 üst (4+ gol)",
           "takim15": "{t} 2+ gol", "cs1x": "{ev} ya da beraberlik", "cs12": "Kazanan çıkar", "csx2": "{dep} ya da beraberlik",
           "atar": "{t} gol atar", "bg": "Beklenen gol", "guven": "Veri güveni",
           "g": {"yuksek": "Yüksek", "orta": "Orta", "dusuk": "Düşük"},
           "not": "En olası skor bile yalnızca {p}: tek skora değil, gol aralığına bakın.",
           "kars": "TAKIM İSTATİSTİĞİ vs PİYASA", "piyasa": "piyasa", "ist": "istatistik",
           "kaynak": {"lig": "bu sezon", "son5": "son 5 maç"},
           "yok": "Takım istatistiği: piyasayla karşılaştırmaya yetecek kadar maç yok.",
           "sadece": "Piyasa fiyatı yok: yukarıdaki bütün yüzdeler takım istatistiğinden.",
           "pazar": {"MS1": "{ev} kazanır", "MSX": "Beraberlik", "MS2": "{dep} kazanır", "UST25": "2.5 Üst", "KGVAR": "KG Var"},
           "alt": "Olasılık, tahmin değil · bahis tavsiyesi değildir · 18+"},
}


def analiz_karti(a: dict, saat: str, dil: str = "en") -> bytes:
    """Tek maçın analiz kartı (1080×1350): maç sonucu çubuğu, alt/üst, ilk yarı, takım golleri, çifte şans,
    en olası 5 skor. Bütün rakamlar aynı Poisson modelinden (çelişki yok)."""
    r, e, p = PALETLER[dil], ETIKETLER[dil], a["p"]
    W, H, K = 1080, 1350, 60
    im = Image.new("RGB", (W, H), r["arka"])
    d = ImageDraw.Draw(im)
    yuzde = (lambda x: f"%{100 * x:.0f}") if dil == "tr" else (lambda x: f"{100 * x:.0f}%")
    d.text((K, 52), f"KALKYLERAT · {e['baslik']}", font=_font(26, True), fill=r["vurgu"])
    tarih = datetime.fromisoformat(a["baslama"]).strftime("%-d %b").upper()
    sag = f"{tarih} · {saat}"
    d.text((W - K - d.textlength(sag, font=_font(24, True)), 54), sag, font=_font(24, True), fill=r["soluk"])
    mac, f = _sigdir(d, f'{a["ev"]} – {a["dep"]}', W - 2 * K, 60, True, 34)
    d.text((K, 100), mac, font=f, fill=r["yazi"])
    alt_baslik, f = _sigdir(d, f'{a["lig"]}  ·  {e["bg"]} {a["beklenen_gol"][0]:.1f} – {a["beklenen_gol"][1]:.1f}',
                            W - 2 * K, 26)
    d.text((K, 182), alt_baslik, font=f, fill=r["soluk"])
    y = 240
    d.text((K, y), e["ms"], font=_font(21, True), fill=r["soluk"])
    y += 34
    x, tw = K, W - 2 * K
    for k, renk in zip(("MS1", "MSX", "MS2"), (r["vurgu"], r["bar2"], r["bar3"])):
        w = tw * p[k]
        if w > 6:
            d.rounded_rectangle((x, y, x + w - 4, y + 52), radius=10, fill=renk)
        x += w
    y += 66
    x = K
    for t, renk in ((f'{a["ev"]} {yuzde(p["MS1"])}', r["vurgu"]), (f'{e["beraberlik"]} {yuzde(p["MSX"])}', r["soluk"]),
                    (f'{a["dep"]} {yuzde(p["MS2"])}', r["soluk"])):
        t, f = _sigdir(d, t, (W - 2 * K) // 3 - 40, 24, True)
        d.ellipse((x, y + 6, x + 16, y + 22), fill=renk)
        d.text((x + 26, y), t, font=f, fill=r["yazi"])
        x += (W - 2 * K) // 3
    y += 56

    def tablo(y0, baslik, satirlar, x0, gen):
        d.rounded_rectangle((x0, y0, x0 + gen, y0 + 50 + 46 * len(satirlar)), radius=18, fill=r["kart"])
        d.text((x0 + 24, y0 + 16), baslik, font=_font(21, True), fill=r["vurgu"])
        for i, (ad, v) in enumerate(satirlar):
            yy = y0 + 58 + 46 * i
            ad, f = _sigdir(d, ad, gen - 130, 25)
            d.text((x0 + 24, yy), ad, font=f, fill=r["yazi"])
            deger = yuzde(v)
            fb = _font(25, True)
            d.text((x0 + gen - 24 - d.textlength(deger, font=fb), yy), deger, font=fb,
                   fill=r["iyi"] if v >= 0.65 else r["yazi"])
        return y0 + 50 + 46 * len(satirlar)
    g = (W - 2 * K - 24) // 2
    s1 = tablo(y, e["gol"], [(e["gol15"], p["UST15"]), (e["gol25"], p["UST25"]), (e["gol35"], p["UST35"]),
                             (e["kg"], p["KGVAR"])], K, g)
    s2 = tablo(y, e["iy"], [(e["iy_ev"].format(ev=a["ev"]), p["IY1"]), (e["iy_x"], p["IYX"]),
                            (e["iy_u05"], p["IYU05"]), (e["iy_u15"], p["IYU15"])], K + g + 24, g)
    y = max(s1, s2) + 22
    s1 = tablo(y, e["takim"], [(e["takim15"].format(t=a["ev"]), p["EVU15"]), (e["takim15"].format(t=a["dep"]), p["DPU15"]),
                               (e["atar"].format(t=a["dep"]), p["DPU05"])], K, g)
    s2 = tablo(y, e["cs"], [(e["cs1x"].format(ev=a["ev"]), p["CS1X"]), (e["cs12"], p["CS12"]),
                            (e["csx2"].format(dep=a["dep"]), p["CSX2"])], K + g + 24, g)
    y = max(s1, s2) + 22
    d.rounded_rectangle((K, y, W - K, y + 150), radius=18, fill=r["kart"])
    d.text((K + 24, y + 16), e["skor"], font=_font(21, True), fill=r["vurgu"])
    cw = (W - 2 * K - 48) / len(a["skorlar"])
    for i, (s, v) in enumerate(a["skorlar"]):
        cx = K + 24 + cw * i + cw / 2
        fs, fp = _font(38, True), _font(22)
        d.text((cx - d.textlength(s, font=fs) / 2, y + 52), s, font=fs, fill=r["yazi"])
        d.text((cx - d.textlength(yuzde(v), font=fp) / 2, y + 104), yuzde(v), font=fp, fill=r["soluk"])
    y += 172
    kars = (a.get("karsilastirma") or [])[:3]
    if kars:
        # Piyasa (oranlardan) ile takım istatistiklerinden (gol ortalamaları) çıkan ihtimal yan yana; fark büyükse vurgulu.
        d.rounded_rectangle((K, y, W - K, y + 50 + 44 * len(kars)), radius=18, fill=r["kart"])
        baslik = e["kars"] + (f' · {e["kaynak"][a["istatistik_kaynak"]]}' if a.get("istatistik_kaynak") else "")
        d.text((K + 24, y + 16), baslik, font=_font(21, True), fill=r["vurgu"])
        for i, c in enumerate(kars):
            yy = y + 56 + 44 * i
            ad, f = _sigdir(d, e["pazar"][c["pazar"]].format(ev=a["ev"], dep=a["dep"]), 380, 24)
            d.text((K + 24, yy), ad, font=f, fill=r["yazi"])
            fark = abs(fark_puani(c)) / 100
            sag = f'{e["piyasa"]} {yuzde(c["piyasa"])} · {e["ist"]} {yuzde(c["istatistik"])}'
            fs = _font(23, abs(fark) >= 0.10)
            d.text((W - K - 24 - d.textlength(sag, font=fs), yy), sag, font=fs,
                   fill=r["vurgu"] if abs(fark) >= 0.10 else r["soluk"])
        y += 50 + 44 * len(kars) + 20
    else:  # karşılaştırma yoksa nedeni açıkça yazılır (istatistik yüzdesi yok demek, saklamak değil)
        not_, f = _sigdir(d, e["sadece" if a.get("kaynak") == "istatistik" else "yok"], W - 2 * K, 24)
        d.text((K, y), not_, font=f, fill=r["yazi"])
        y += 40
        not_, f = _sigdir(d, e["not"].format(p=yuzde(a["skorlar"][0][1])), W - 2 * K, 24)
        d.text((K, y), not_, font=f, fill=r["soluk"])
        y += 40
    guven = f'{e["guven"]}: {e["g"][a["guven"]]}'
    d.text((K, y), guven, font=_font(22, True), fill=r["soluk"])
    alt, f = _sigdir(d, e["alt"], W - 2 * K, 21)
    d.text(((W - d.textlength(alt, font=f)) / 2, H - 60), alt, font=f, fill=r["soluk"])
    tampon = io.BytesIO()
    im.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()


TABLO_ETIKETLERI = {
    "en": {"baslik": "TODAY'S ANALYSIS BOARD", "mac": "MATCH",
           "sutun": ["HOME\nWIN", "DRAW", "AWAY\nWIN", "OVER 1.5\nGOALS", "OVER 2.5\nGOALS", "OVER 3.5\nGOALS",
                     "BOTH\nSCORE", "GOAL IN\n1ST HALF", "LIKELY\nSCORE"],
           "alt": "Top row: market-based chances · bottom row: team stats · not betting advice · 18+",
           "ist_baslik": "TEAM STATS{k}:", "ist_pazar": {"MS1": "{ev} win", "MS2": "{dep} win",
                                                            "UST25": "Over 2.5 goals", "KGVAR": "Both score"},
           "kaynak": {"lig": "this season", "son5": "last 5 games"},
           "ist_yok": "Team stats: not enough recent games to compare",
           "ist_sadece": "No market price: chances above come from team stats"},
    "tr": {"baslik": "GÜNÜN ANALİZ TABLOSU", "mac": "MAÇ",
           "sutun": ["EV\nKAZANIR", "BERA-\nBERLİK", "DEPLASMAN\nKAZANIR", "1.5 ÜST\n(2+ GOL)", "2.5 ÜST\n(3+ GOL)",
                     "3.5 ÜST\n(4+ GOL)", "KARŞILIKLI\nGOL", "İLK YARI\nGOL", "OLASI\nSKOR"],
           "alt": "Üst satır: piyasaya göre · alt satır: takım istatistiği · bahis tavsiyesi değildir · 18+",
           "ist_baslik": "TAKIM İSTATİSTİĞİ{k}:", "ist_pazar": {"MS1": "{ev} kazanır", "MS2": "{dep} kazanır",
                                                                    "UST25": "2.5 üst", "KGVAR": "Karşılıklı gol"},
           "kaynak": {"lig": "bu sezon", "son5": "son 5 maç"},
           "ist_yok": "Takım istatistiği: karşılaştırmaya yetecek maç yok",
           "ist_sadece": "Piyasa fiyatı yok: yüzdeler takım istatistiğinden"},
}


def analiz_tablosu(liste: list[dict], tarih_iso: str, saatler: list[str], dil: str = "en") -> bytes:
    """Günün analiz tablosu (1080 genişlik): her maç iki satır: üstte maç, lig ve saat; altta dokuz pazarın yüzdesi
    (1/X/2, 1.5/2.5/3.5 üst, karşılıklı gol, ilk yarıda gol, en olası skor ve yüzdesi). Yüzdesiz rakam yok."""
    r, e = PALETLER[dil], TABLO_ETIKETLERI[dil]
    W, K = 1080, 40
    satir = 142
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
        # Takım istatistiği satırı: piyasadan gelen rakamların istatistikteki karşılığı (10+ puan fark vurgulu)
        kars = {c["pazar"]: c for c in a.get("karsilastirma") or []}
        fs = _font(17)
        if kars:
            kaynak = e["kaynak"].get(a.get("istatistik_kaynak"))
            parcalar = [(e["ist_baslik"].format(k=f" ({kaynak})" if kaynak else ""), r["soluk"])]
            for kod in ("MS1", "MS2", "UST25", "KGVAR"):
                if kod in kars:
                    c = kars[kod]
                    ad = e["ist_pazar"][kod].format(ev=a["ev"], dep=a["dep"])
                    parcalar.append((f'{ad} {yuzde(c["istatistik"])}', r["vurgu"] if abs(fark_puani(c)) >= 10 else r["yazi"]))
            metin_ = "  ·  ".join(t for t, _ in parcalar)
            while d.textlength(metin_, font=fs) > W - 2 * K and fs.size > 12:
                fs = _font(fs.size - 1)
            xx = K
            for j, (t, renk) in enumerate(parcalar):
                t = ("", " ", "  ·  ")[min(j, 2)] + t
                d.text((xx, yy + 96), t, font=fs, fill=renk)
                xx += d.textlength(t, font=fs)
        else:
            t = e["ist_sadece"] if a.get("kaynak") == "istatistik" else e["ist_yok"]
            d.text((K, yy + 96), t, font=fs, fill=r["soluk"])
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
