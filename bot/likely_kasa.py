"""Mr. Likely sanal kasası (SOZLESME E8): 6 Ekim 2026'dan beri paylaşılan her kupon, sanal 10.000 € ile.

Kural (sahibinin kararı, 24 Ekim 2026): kupon paylaşıldığı an, boştaki bakiyenin %3'ü o kupona ayrılır ve bakiyeden
düşer; kupon açık kalır. Sonraki kuponun payı, o anda kalan boştaki bakiyeden hesaplanır (10.000 € → 300 €, sonra
9.700 €'nun %3'ü = 291 €). Tutan kupon pay × oranı, iade payı geri getirir; yatan hiçbir şey getirmez. Grafikteki kasa = boştaki
bakiye + açık kuponların payları (kupon paylaşılınca kasa düşmüş görünmesin). Gerçek para yok; rakamlar yalnızca
kayıttan (paylaşılmış kuponlar, kaybedenler dahil; veri hatasıyla iptal edilenler hariç, E5)."""

import calendar
import io
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from . import denetci, likely, likely_gorsel as g
from .tweets import ANSVAR, LIMIT, uzunluk

BASLANGIC = 10000.0
PAY = 0.03
_X_EPOK_MS = 1288834974657


def _tweet_zamani(tweet_id) -> datetime | None:
    """X kimliğinin içindeki zaman (eski kayıtlarda sonuç anı yalnızca sonuç postunun kimliğinde)."""
    try:
        return datetime.fromtimestamp(((int(tweet_id) >> 22) + _X_EPOK_MS) / 1000, timezone.utc)
    except (TypeError, ValueError):
        return None


def kapanis_zamani(k: dict) -> datetime | None:
    if k.get("sonuc_zamani"):
        return datetime.fromisoformat(k["sonuc_zamani"])
    return _tweet_zamani(k.get("sonuc_tweet_id"))


def _donus(k: dict, pay: float) -> float:
    if k["durum"] == "tuttu":
        return round(pay * (k.get("son_oran") or k["oran"]), 2)
    return pay if k["durum"] == "iade" else 0.0


def hesapla(veri: dict, baslangic: float = BASLANGIC, oran: float = PAY) -> dict:
    """Bütün paylaşılmış kuponlar zaman sırasıyla. Döner: boştaki bakiye, açık kuponlar, kasa noktaları
    (zaman, günün tarihi, kasa) ve her kuponun payı."""
    olaylar = []
    for gun in veri["gunler"]:
        for k in gun.get("secilen", []):
            if not (k.get("tweet_id") and k.get("yayin")):
                continue
            olaylar.append((datetime.fromisoformat(k["yayin"]), 0, gun["tarih"], k))
            kapanis = kapanis_zamani(k)
            if k["durum"] in ("tuttu", "yatti", "iade") and kapanis:
                olaylar.append((kapanis, 1, gun["tarih"], k))
    olaylar.sort(key=lambda o: (o[0], o[1]))
    bos, acik, noktalar, paylar = baslangic, {}, [], {}
    for zaman, tur, tarih, k in olaylar:
        anahtar = k["tweet_id"]
        if tur == 0:
            pay = round(bos * oran, 2)
            bos = round(bos - pay, 2)
            acik[anahtar] = pay
            paylar[anahtar] = pay
            continue
        bos = round(bos + _donus(k, acik.pop(anahtar)), 2)
        noktalar.append((zaman, tarih, round(bos + sum(acik.values()), 2)))
    return {"bos": bos, "acik": acik, "kasa": round(bos + sum(acik.values()), 2), "noktalar": noktalar,
            "paylar": paylar, "baslangic": baslangic}


def gunluk_mumlar(h: dict) -> list[dict]:
    """Her kupon günü bir mum: açılış önceki günün kapanışı, kapanış günün son sonucundan sonraki kasa."""
    gunler: dict[str, list[float]] = {}
    for _, tarih, kasa in h["noktalar"]:
        gunler.setdefault(tarih, []).append(kasa)
    mumlar, acilis = [], h["baslangic"]
    for tarih in sorted(gunler):
        v = gunler[tarih]
        mumlar.append({"tarih": tarih, "acilis": acilis, "yuksek": max(acilis, *v), "dusuk": min(acilis, *v),
                       "kapanis": v[-1]})
        acilis = v[-1]
    return mumlar


def birlestir(mumlar: list[dict], anahtar) -> list[dict]:
    """Günlük mumları haftaya/aya toplar (anahtar: tarih → grup)."""
    gruplar: dict = {}
    for m in mumlar:
        gruplar.setdefault(anahtar(date.fromisoformat(m["tarih"])), []).append(m)
    return [{"tarih": v[0]["tarih"], "acilis": v[0]["acilis"], "yuksek": max(m["yuksek"] for m in v),
             "dusuk": min(m["dusuk"] for m in v), "kapanis": v[-1]["kapanis"]} for _, v in sorted(gruplar.items())]


def hafta(d: date):
    return d.isocalendar()[:2]


# ---------- Görsel ----------

# Marka renkleri (likely_gorsel): hardal, krem, mürekkep, domates, soluk, yeşil.
PALETLER = {
    "fis": {"zemin": g.HARDAL, "kart": g.KREM, "yazi": g.MUREKKEP, "soluk": g.SOLUK, "izgara": "#E4DAC2",
            "yukselis": g.YESIL, "dusus": g.DOMATES},
    "hardal": {"zemin": g.HARDAL, "kart": g.HARDAL, "yazi": g.MUREKKEP, "soluk": "#6B5418", "izgara": "#D3A535",
               "yukselis": g.MUREKKEP, "dusus": g.DOMATES},
    "murekkep": {"zemin": g.MUREKKEP, "kart": g.MUREKKEP, "yazi": g.KREM, "soluk": "#8E8E7E", "izgara": "#2C3632",
                 "yukselis": g.HARDAL, "dusus": g.DOMATES},
    "orman": {"zemin": g.YESIL, "kart": g.YESIL, "yazi": g.KREM, "soluk": "#9DB5A8", "izgara": "#1E6049",
              "yukselis": g.KREM, "dusus": "#F07A55"},
    "gece": {"zemin": g.MUREKKEP, "kart": "#151C19", "yazi": g.KREM, "soluk": "#8E8E7E", "izgara": "#25302B",
             "yukselis": "#3FA77C", "dusus": g.DOMATES},
}
VARSAYILAN_PALET = "fis"


def _euro(x: float, isaret: bool = False) -> str:
    s = f"€{abs(x):,.2f}".removesuffix(".00")
    return ("+" if x >= 0 else "−") + s if isaret else ("−" if x < 0 else "") + s


def grafik(mumlar: list[dict], baslik: str, etiket, palet: str = VARSAYILAN_PALET, baslangic: float = BASLANGIC,
           degisim_etiketi: str = "today", fark_baz: float | None = None) -> bytes:
    """Borsa grafiği gibi mumlar: yükseliş/düşüş renkli, sağda güncel kasa. etiket: mum → alt eksen yazısı."""
    p = PALETLER[palet]
    W, H = 1600, 1000
    im = Image.new("RGB", (W, H), p["zemin"])
    d = ImageDraw.Draw(im)
    kenar = 40 if p["kart"] != p["zemin"] else 0
    if kenar:
        d.rounded_rectangle((kenar, kenar, W - kenar, H - kenar), radius=28, fill=p["kart"])
    L, R, T, B = 110, 1330, 280, 815
    im.paste(g._logo(110), (L - 10, 74), g._logo(110))
    d.text((L + 124, 128), "Mr. Likely", font=g._font("kalin", 54), fill=p["yazi"], anchor="ls")
    d.text((L + 126, 170), baslik, font=g._font("orta", 30), fill=p["soluk"], anchor="ls")
    son = mumlar[-1]["kapanis"]
    fark = son - (mumlar[-1]["acilis"] if fark_baz is None else fark_baz)
    renk = p["yukselis"] if fark >= 0 else p["dusus"]
    d.text((W - 110, 132), _euro(son), font=g._font("anton", 92), fill=p["yazi"], anchor="rs")
    d.text((W - 110, 186), f"{_euro(fark, True)} {degisim_etiketi}  ·  {100 * (son / baslangic - 1):+.1f}% since 6 Oct",
           font=g._font("orta", 30), fill=renk, anchor="rs")
    lo = min(min(m["dusuk"] for m in mumlar), baslangic)
    hi = max(max(m["yuksek"] for m in mumlar), baslangic)
    pay = max((hi - lo) * 0.1, 10)
    lo, hi = lo - pay, hi + pay
    y = lambda v: B - (v - lo) / (hi - lo) * (B - T)
    adim = next(a for a in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000) if (hi - lo) / a <= 7)
    v = (int(lo // adim) + 1) * adim
    while v < hi:
        d.line([(L, y(v)), (R, y(v))], fill=p["izgara"], width=2)
        d.text((R + 24, y(v)), f"€{v:,}", font=g._font("orta", 26), fill=p["soluk"], anchor="lm")
        v += adim
    for x in range(L, R, 18):  # başlangıç kasası: kesik çizgi
        d.line([(x, y(baslangic)), (x + 9, y(baslangic))], fill=p["soluk"], width=2)
    d.text((L + 6, y(baslangic) - 8), f"start €{baslangic:,.0f}", font=g._font("orta", 22), fill=p["soluk"], anchor="ls")
    n = len(mumlar)
    w = (R - L) / max(n, 8)
    for i, m in enumerate(mumlar):
        x = L + w * (i + 0.5)
        r = p["yukselis"] if m["kapanis"] >= m["acilis"] else p["dusus"]
        d.line([(x, y(m["yuksek"])), (x, y(m["dusuk"]))], fill=r, width=4)
        ust, alt = y(max(m["acilis"], m["kapanis"])), y(min(m["acilis"], m["kapanis"]))
        if alt - ust < 6:
            ust, alt = ust - 3, alt + 3
        d.rounded_rectangle((x - w * 0.32, ust, x + w * 0.32, alt), radius=3, fill=r)
        if n <= 10 or i % max(1, n // 8) == 0 or i == n - 1:
            d.text((x, B + 38), etiket(m), font=g._font("orta", 24), fill=p["soluk"], anchor="mm")
    ys = y(son)
    d.rounded_rectangle((R + 8, ys - 24, W - kenar - 14, ys + 24), radius=8, fill=renk)
    d.text((R + 24, ys), _euro(son), font=g._font("kalin", 26),
           fill=p["kart"] if renk != p["kart"] else p["yazi"], anchor="lm")
    d.text((W // 2, H - kenar - 30), "VIRTUAL BANK · NOT REAL MONEY · 3% OF FREE BALANCE PER COUPON · LOSERS COUNTED · 18+",
           font=g._font("orta", 24), fill=p["soluk"], anchor="ms")
    cikti = io.BytesIO()
    im.save(cikti, format="PNG", optimize=True)
    return cikti.getvalue()


def gun_etiketi(m: dict) -> str:
    d = date.fromisoformat(m["tarih"])
    return f"{d.day} {d.strftime('%b')}"


def hafta_etiketi(m: dict) -> str:
    d = date.fromisoformat(m["tarih"])
    d -= timedelta(days=d.weekday())
    return f"w/c {d.day} {d.strftime('%b')}"


# ---------- Paylaşım (E8) ----------

SON_SAAT = 9          # açık kupon kalsa da grafik en geç ertesi sabah bu saatte (yerel)
BEKLE_DK = 10         # son sonuç postundan bu kadar dakika sonra (aynı anda iki post gitmesin)


def tur(tarih: str) -> str:
    """Ayın son günü aylık, Pazar haftalık, diğer günler günlük grafik (büyük olan küçüğün yerine geçer)."""
    d = date.fromisoformat(tarih)
    if d.day == calendar.monthrange(d.year, d.month)[1]:
        return "aylik"
    return "haftalik" if d.weekday() == 6 else "gunluk"


def _paylasilan(gun: dict) -> list[dict]:
    return [k for k in gun.get("secilen", []) if k.get("tweet_id")]


def hazir_mi(gun: dict, simdi: datetime, tz: ZoneInfo) -> bool:
    """Günün kuponları paylaşıldı ve hepsinin sonuç postu çıktı mı (ya da ertesi sabahın son saati geldi mi)?
    Kupon çıkmayan gün grafik yok; paylaşılmayı bekleyen kupon varken grafik beklenir."""
    paylasilan = _paylasilan(gun)
    if not paylasilan:
        return False
    son = datetime.combine(date.fromisoformat(gun["tarih"]) + timedelta(days=1), datetime.min.time(), tz)
    if simdi >= son.replace(hour=SON_SAAT):
        return True
    if any(k.get("oto") and not k.get("tweet_id") and k["durum"] == "bekliyor" for k in gun.get("secilen", [])):
        return False
    if not all(k.get("sonuc_tweet_id") for k in paylasilan):
        return False
    kapanislar = [kapanis_zamani(k) for k in paylasilan]
    return all(z and simdi - z >= timedelta(minutes=BEKLE_DK) for z in kapanislar)


def _gun_adi(tarih: str) -> str:
    d = date.fromisoformat(tarih)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


SIRA = {2: "Second", 3: "Third", 4: "Fourth", 5: "Fifth", 6: "Sixth", 7: "Seventh"}


def ilk_satir(gunluk: list[dict]) -> str:
    """Günlük postun kancası, yalnızca kayıttaki mumlardan (aynı kalıp her gün gitmesin, X benzerlik cezası):
    en iyi/en kötü gün, yeni zirve, art arda kırmızı ya da yeşil gün. Söylenecek bir şey yoksa boş."""
    if len(gunluk) < 2:
        return ""
    son = gunluk[-1]
    fark = son["kapanis"] - son["acilis"]
    onceki = [m["kapanis"] - m["acilis"] for m in gunluk[:-1]]
    if len(gunluk) >= 5 and fark > 0 and fark > max(onceki):
        return "Best day so far."
    if len(gunluk) >= 5 and fark < 0 and fark < min(onceki):
        return "Worst day so far."
    if fark > 0 and son["kapanis"] > max(BASLANGIC, *(m["kapanis"] for m in gunluk[:-1])):
        return "New high."
    seri = 0
    for m in reversed(gunluk):
        f = m["kapanis"] - m["acilis"]
        if f == 0 or (f < 0) != (fark < 0):
            break
        seri += 1
    if fark and seri >= (2 if fark < 0 else 3):
        return f"{SIRA.get(seri, f'{seri}th')} {'red' if fark < 0 else 'green'} day in a row."
    return ""


def post_hazirla(veri: dict, tarih: str, palet: str = VARSAYILAN_PALET) -> tuple[str, bytes, set[str]]:
    """Günün grafik postu: metin, görsel ve metinde geçebilecek tutarlar (denetçi için). Rakamlar yalnızca kayıttan."""
    h = hesapla(veri)
    gunluk = [m for m in gunluk_mumlar(h) if m["tarih"] <= tarih]
    if not gunluk or gunluk[-1]["tarih"] != tarih:  # günün hiçbir kuponu sonuçlanmadı (sabah son saati): düz mum
        k_ = gunluk[-1]["kapanis"] if gunluk else h["baslangic"]
        gunluk.append({"tarih": tarih, "acilis": k_, "yuksek": k_, "dusuk": k_, "kapanis": k_})
    kasa = gunluk[-1]["kapanis"]
    gun = next(g_ for g_ in veri["gunler"] if g_["tarih"] == tarih)
    paylasilan = _paylasilan(gun)
    tutan = sum(k["durum"] == "tuttu" for k in paylasilan)
    acik = sum(k["durum"] == "bekliyor" or not k.get("sonuc_tweet_id") for k in paylasilan)
    t = tur(tarih)
    d = date.fromisoformat(tarih)
    if t == "aylik":
        mumlar = [m for m in gunluk if m["tarih"][:7] == tarih[:7]]
        baz = mumlar[0]["acilis"]
        ay = d.strftime("%B")
        png = grafik(mumlar, f"Virtual bank · {ay}", gun_etiketi, palet, degisim_etiketi="this month", fark_baz=baz)
        kuponlar = [k for g_ in veri["gunler"] if g_["tarih"][:7] == tarih[:7] for k in _paylasilan(g_)]
        bas = f"🗓️ {ay} in the virtual bank: {_euro(baz)} → {_euro(kasa)} ({_euro(kasa - baz, True)})."
        sayi = f"{len(kuponlar)} coupons this month, {sum(k['durum'] == 'tuttu' for k in kuponlar)} landed."
    elif t == "haftalik":
        haftalar = birlestir(gunluk, hafta)
        baz = haftalar[-1]["acilis"]
        png = grafik(haftalar, "Virtual bank · weekly", hafta_etiketi, palet, degisim_etiketi="this week", fark_baz=baz)
        pazartesi = (d - timedelta(days=d.weekday())).isoformat()
        kuponlar = [k for g_ in veri["gunler"] if pazartesi <= g_["tarih"] <= tarih for k in _paylasilan(g_)]
        bas = f"📊 Week done. Virtual bank: {_euro(kasa)} ({_euro(kasa - baz, True)} this week)."
        sayi = f"{len(kuponlar)} coupons this week, {sum(k['durum'] == 'tuttu' for k in kuponlar)} landed."
    else:
        mumlar = gunluk[-30:]
        baz = mumlar[-1]["acilis"]
        png = grafik(mumlar, "Virtual bank · daily", gun_etiketi, palet, degisim_etiketi="today", fark_baz=baz)
        kanca = ilk_satir(gunluk)
        bas = (f"{'📈' if kasa >= baz else '📉'} {kanca + ' ' if kanca else ''}Virtual bank, {_gun_adi(tarih)}: "
               f"{_euro(kasa)} ({_euro(kasa - baz, True)} today).")
        sayi = f"{len(paylasilan)} coupon{'s' * (len(paylasilan) != 1)}, {tutan} landed."
    if acik:
        sayi += f" {acik} still open."
    metin = (f"{bas}\n\n🎟️ {sayi}\n🏁 Started at {_euro(BASLANGIC)} on 6 Oct, 3% of the free balance per coupon, "
             f"losers counted.\n\n⚠️ Virtual bank, not real money.\n{ANSVAR}")
    return metin, png, {_euro(abs(x)) for x in (kasa, kasa - baz, baz, BASLANGIC)}


def _ay_sonu(d: date) -> date:
    """Bir sonraki ayın son günü (duyurudaki soru: "where is the bank on 30 Nov?")."""
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, calendar.monthrange(y, m)[1])


def duyuru_hazirla(veri: dict, palet: str = VARSAYILAN_PALET, bugun: date | None = None) -> tuple[list[str], bytes, set[str]]:
    """4 postluk duyuru flood'u (E8): ilk post grafikle. Rakamlar kayıttan; örnek, sanal kasanın kendi başlangıcıyla."""
    mumlar = gunluk_mumlar(hesapla(veri))[-30:]
    kasa = mumlar[-1]["kapanis"] if mumlar else BASLANGIC
    ilk_pay = round(BASLANGIC * PAY, 2)
    kalan = BASLANGIC - ilk_pay
    ikinci = round(kalan * PAY, 2)
    son = _ay_sonu(bugun or date.today())
    metinler = [
        f"I put a virtual {_euro(BASLANGIC)} behind every coupon I've posted since 6 Oct. It's at {_euro(kasa)} now.\n\n"
        f"Here's how the bank works 🧵\n\nVirtual bank, not real money.\n18+",
        f"The rule doesn't bend. Each coupon takes 3% of the free balance when it goes up.\n\n"
        f"Bank at {_euro(BASLANGIC)}? The first coupon takes {_euro(ilk_pay)}. If that one's still open when the next "
        f"goes up, the next takes 3% of {_euro(kalan)}: {_euro(ikinci)}.\n\n18+",
        "Every posted coupon counts. Losers stay in and red days get posted. Only a coupon pulled before kick-off for a "
        "data error is left out.\n\nNo real money anywhere. It's a scoreboard.\n\n18+",
        f"From tonight: a chart once each day's coupons settle. Weekly on Sundays, monthly at month end.\n\n"
        f"Where do you reckon the bank is on {son.day} {son.strftime('%b')}?\n\n{ANSVAR}",
    ]
    png = grafik(mumlar or [{"tarih": "2026-10-06", "acilis": kasa, "yuksek": kasa, "dusuk": kasa, "kapanis": kasa}],
                 "Virtual bank · since 6 Oct", gun_etiketi, palet, degisim_etiketi="so far", fark_baz=BASLANGIC)
    return metinler, png, {_euro(x) for x in (BASLANGIC, kasa, ilk_pay, kalan, ikinci, abs(kasa - BASLANGIC))}


# ---------- Denetçi (E8) ----------

_TUTAR = re.compile(r"€[\d,]+(?:\.\d+)?")


def denetle(metin: str, izinli_tutarlar: set[str]) -> list[str]:
    """Kasa postunun yayın öncesi kod denetimi; dönen her madde engelleyicidir."""
    hata = []
    if uzunluk(metin) > LIMIT:
        hata.append(f"280 karakteri aşıyor ({uzunluk(metin)}).")
    if denetci._LINK.search(metin):
        hata.append("Link ya da @ içeriyor.")
    if "#" in metin:
        hata.append("Etiket içeriyor.")
    if denetci._SITE.search(metin):
        hata.append("Bahis sitesi adı içeriyor.")
    if denetci._KESINLIK.search(metin) or re.search(r"\beasy (win|money)\b|\bsafe bet\b", metin, re.IGNORECASE):
        hata.append("Kesinlik dili içeriyor.")
    if re.search(r"\bstakes?\b|\btail\b", metin, re.IGNORECASE):
        hata.append("Bahis çağrısı ya da pay dili içeriyor ('stake', 'tail').")
    if "—" in metin or "–" in metin:
        hata.append("Uzun tire içeriyor (yapay zekâ izi).")
    if not metin.rstrip().splitlines()[-1].startswith("18+"):
        hata.append("Son satır '18+' değil.")
    yabanci = [t for t in _TUTAR.findall(metin) if t not in izinli_tutarlar]
    if yabanci:
        hata.append(f"Kayıtta olmayan tutar: {', '.join(yabanci)}.")
    return hata


def oto_kasa(ayar, x, simdi: datetime, yaz=print) -> bool:
    """E8: önce bir kez 4 postluk duyuru (sahibinin onayıyla açılan oto_kasa), sonra günde en fazla bir grafik postu.
    Duyurudan önceki günler için grafik atılmaz. Her post denetçiden geçer; geçmezse gitmez ve sahibine yazılır."""
    cfg = likely.ayar_yukle()
    if not cfg.aktif or cfg.mod != "otomatik" or not cfg.oto_kasa:
        return False
    veri = likely.yukle()
    tz = ZoneInfo(ayar.saat_dilimi)
    duyuru = veri.get("kasa_duyuru") or {}
    ids = duyuru.get("ids", [])
    if len(ids) < 4:
        metinler, png, izinli = duyuru_hazirla(veri, cfg.kasa_paleti, simdi.astimezone(tz).date())
        hatalar = [f"{i + 1}/4: {h}" for i, m in enumerate(metinler) for h in denetle(m, izinli)]
        if hatalar:
            yaz("⚠️ Mr. Likely: kasa duyurusu denetçiden geçmedi, atılmadı: " + " ".join(hatalar))
            return False
        if not ids:
            duyuru.update(tarih=simdi.astimezone(tz).date().isoformat(), zaman=simdi.isoformat(timespec="seconds"))
        veri["kasa_duyuru"] = duyuru
        for i in range(len(ids), 4):  # yarıda kalırsa bir sonraki çalışma kaldığı yerden sürdürür
            ids.append(x.gonder(metinler[i], yanit=ids[-1] if ids else None,
                                medya=[x.medya_yukle(png)] if i == 0 else None))
            duyuru["ids"] = ids
            likely.kaydet(veri)
        yaz("Mr. Likely: sanal kasa duyurusu (4 post) paylaşıldı.")
        return True
    for gun in veri["gunler"][-3:]:
        if gun["tarih"] < duyuru["tarih"] or gun.get("kasa") or not hazir_mi(gun, simdi, tz):
            continue
        metin, png, izinli = post_hazirla(veri, gun["tarih"], cfg.kasa_paleti)
        hatalar = denetle(metin, izinli)
        if hatalar:
            gun["kasa"] = {"tweet_id": "denetci", "hata": hatalar, "zaman": simdi.isoformat(timespec="seconds")}
            likely.kaydet(veri)
            yaz(f"⚠️ Mr. Likely: {gun['tarih']} kasa postu denetçiden geçmedi, atılmadı: {' '.join(hatalar)}")
            return False
        tweet = x.gonder(metin, medya=[x.medya_yukle(png)])
        gun["kasa"] = {"tweet_id": tweet, "tur": tur(gun["tarih"]), "zaman": simdi.isoformat(timespec="seconds"),
                       "metin": metin}
        likely.kaydet(veri)
        yaz(f"Mr. Likely: {gun['tarih']} kasa grafiği paylaşıldı ({tur(gun['tarih'])}).")
        return True
    return False
