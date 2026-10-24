"""Mr. Likely sanal kasası ve grafik postu (SOZLESME E8)."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from bot import config, likely, likely_kasa as kasa
from bot.tweets import ANSVAR, LIMIT, uzunluk

UTC = timezone.utc
AYAR = config.yukle()
T0 = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)  # Pazartesi


def kupon(tid, yayin, durum="bekliyor", oran=2.0, sonuc=None, **k):
    d = {"ad": f"k{tid}", "oto": True, "tweet_id": str(tid), "yayin": yayin.isoformat(), "oran": oran,
         "durum": durum, "ayaklar": [], **k}
    if sonuc:
        d.update(sonuc_tweet_id=f"s{tid}", sonuc_zamani=sonuc.isoformat())
    return d


def veri(*gunler):
    return {"gunler": [{"tarih": t, "secilen": ks} for t, ks in gunler]}


def test_E8_pay_bostaki_bakiyeden_acik_kupon_dusulur():
    """Sahibinin örneği: 100 € → ilk kupon 3 € (açık kalır), ikinci kupon 97 €'nun %3'ü = 2,91 €. Sanal kasa 10.000 €."""
    assert kasa.BASLANGIC == 10000 and kasa.PAY == 0.03
    v = veri(("2026-10-26", [kupon(1, T0, "tuttu", 2.0, sonuc=T0 + timedelta(hours=5)),
                             kupon(2, T0 + timedelta(hours=1), "yatti", 2.0, sonuc=T0 + timedelta(hours=6))]))
    h = kasa.hesapla(v, baslangic=100)
    assert h["paylar"] == {"1": 3.0, "2": 2.91}
    assert h["bos"] == round(100 - 3 - 2.91 + 6, 2) == h["kasa"]
    # kupon paylaşılınca kasa düşmüş görünmez: grafikteki kasa = boştaki + açık paylar
    assert [n[2] for n in h["noktalar"]] == [round(100 + 3, 2), 100.09]


def test_E8_sonuc_sonrasi_kupon_guncel_bakiyeden():
    v = veri(("2026-10-26", [kupon(1, T0, "tuttu", 2.5, sonuc=T0 + timedelta(hours=2)),
                             kupon(2, T0 + timedelta(hours=3), "yatti", 2.0, sonuc=T0 + timedelta(hours=5))]))
    h = kasa.hesapla(v)
    assert h["paylar"] == {"1": 300.0, "2": round((10000 - 300 + 750) * 0.03, 2)}


def test_E8_iade_payi_getirir_iade_ayak_1_sayilir_paylasilmayan_sayilmaz():
    v = veri(("2026-10-26", [kupon(1, T0, "iade", 2.0, sonuc=T0 + timedelta(hours=2)),
                             kupon(2, T0 + timedelta(hours=3), "tuttu", 2.0, son_oran=1.5, sonuc=T0 + timedelta(hours=5)),
                             {"ad": "plan", "oto": True, "durum": "bekliyor", "oran": 2.0, "ayaklar": []}]))
    h = kasa.hesapla(v)
    assert len(h["paylar"]) == 2
    assert h["kasa"] == round(10000 + 300 * 0.5, 2)


def test_E8_eski_kayitta_sonuc_ani_tweet_kimliginden():
    z = kasa._tweet_zamani("2113911723765735519")
    assert z and z.year == 2026 and z.month == 10


def test_E8_grafik_turu_aylik_haftalik_gunluk():
    assert kasa.tur("2026-10-31") == "aylik"
    assert kasa.tur("2026-05-31") == "aylik"  # Pazar ve ay sonu: aylık
    assert kasa.tur("2026-10-25") == "haftalik"
    assert kasa.tur("2026-10-26") == "gunluk"


def test_E8_grafik_yalniz_butun_kuponlar_sonuclaninca():
    tz = kasa.ZoneInfo("Europe/Stockholm")
    a = kupon(1, T0, "tuttu", sonuc=T0 + timedelta(hours=5))
    b = kupon(2, T0 + timedelta(hours=1))
    gun = {"tarih": "2026-10-26", "secilen": [a, b]}
    sonra = T0 + timedelta(hours=8)
    assert not kasa.hazir_mi(gun, sonra, tz)  # b açık
    b.update(durum="yatti", sonuc_tweet_id="s2", sonuc_zamani=(T0 + timedelta(hours=7, minutes=55)).isoformat())
    assert not kasa.hazir_mi(gun, sonra, tz)  # son sonuçtan 10 dk geçmedi
    assert kasa.hazir_mi(gun, sonra + timedelta(minutes=10), tz)
    gun["secilen"].append({"ad": "plan", "oto": True, "durum": "bekliyor", "oran": 2.0, "ayaklar": []})
    assert not kasa.hazir_mi(gun, sonra + timedelta(minutes=10), tz)  # paylaşılacak kupon var
    # ertesi sabah 09:00 (yerel): açık kupon olsa da grafik gider
    assert kasa.hazir_mi(gun, datetime(2026, 10, 27, 9, 0, tzinfo=tz), tz)
    assert not kasa.hazir_mi({"tarih": "2026-10-26", "secilen": []}, sonra, tz)  # kupon yok, grafik yok


def _metin_kurali(metin: str):
    assert "Virtual bank" in metin and "not real money" in metin
    assert metin.endswith(ANSVAR) and uzunluk(metin) <= LIMIT
    for yasak in ("stake", "profit", "guarantee", "http", "#", "@"):
        assert yasak not in metin.lower()


def test_E8_post_metni_ve_gorsel_her_tur():
    gunler = []
    for i, t in enumerate(("2026-10-24", "2026-10-25", "2026-10-30", "2026-10-31")):
        bas = datetime.fromisoformat(t + "T10:00:00+00:00")
        gunler.append((t, [kupon(10 * i + 1, bas, "tuttu", 2.0, sonuc=bas + timedelta(hours=4)),
                           kupon(10 * i + 2, bas + timedelta(hours=1), "yatti", 3.0, sonuc=bas + timedelta(hours=5))]))
    v = veri(*gunler)
    for t, beklenen in (("2026-10-24", "📈"), ("2026-10-25", "📊"), ("2026-10-31", "🗓️")):
        metin, png, izinli = kasa.post_hazirla(v, t)
        _metin_kurali(metin)
        assert not kasa.denetle(metin, izinli)
        assert metin.startswith(beklenen) and png[:4] == b"\x89PNG"
    metin, _, _ = kasa.post_hazirla(v, "2026-10-24")
    assert kasa._euro(kasa.gunluk_mumlar(kasa.hesapla(v))[0]["kapanis"]) in metin  # rakam kayıttan
    for palet in kasa.PALETLER:
        assert kasa.grafik(kasa.gunluk_mumlar(kasa.hesapla(v)), "x", kasa.gun_etiketi, palet)[:4] == b"\x89PNG"


def test_E8_kupon_postunda_pay_yazmaz():
    k = {"ad": "gunun-kuponu", "oran": 2.1, "olasilik": 0.47,
         "ayaklar": [{"ev": "A", "dep": "B", "etiket": "Over 1.5 goals", "oran": 1.45, "baslama": T0.isoformat()},
                     {"ev": "C", "dep": "D", "etiket": "Home win", "oran": 1.45, "baslama": T0.isoformat()}]}
    metin = likely.kupon_metni(k, k["ayaklar"], "t")
    assert "€" not in metin and "stake" not in metin.lower()


class SahteX:
    def __init__(self, bozuk_sira=None):
        self.postlar, self.yanitlar, self.medyalar = [], [], []
        self.bozuk_sira = bozuk_sira

    def medya_yukle(self, png):
        return "m"

    def gonder(self, metin, yanit=None, medya=None, **k):
        if self.bozuk_sira == len(self.postlar) + 1:
            self.bozuk_sira = None
            raise RuntimeError("X API hatası 503")
        self.postlar.append(metin)
        self.yanitlar.append((metin, yanit))
        self.medyalar.append((medya, yanit))
        return str(len(self.postlar))


def test_E8_kapaliyken_post_yok_once_duyuru_sonra_gunde_bir_grafik(monkeypatch):
    bugun = datetime(2026, 10, 26, 21, 0, tzinfo=UTC)
    v = veri(("2026-10-25", [kupon(1, bugun - timedelta(days=1, hours=6), "tuttu", sonuc=bugun - timedelta(days=1))]),
             ("2026-10-26", [kupon(2, bugun - timedelta(hours=6), "tuttu", sonuc=bugun - timedelta(hours=1))]))
    cfg = likely.LikelyAyar(aktif=True, mod="otomatik")
    monkeypatch.setattr(likely, "ayar_yukle", lambda: cfg)
    monkeypatch.setattr(likely, "yukle", lambda: v)
    monkeypatch.setattr(likely, "kaydet", lambda _: None)
    x = SahteX()
    assert not kasa.oto_kasa(AYAR, x, bugun) and not x.postlar  # oto_kasa kapalı (varsayılan)
    cfg = replace(cfg, oto_kasa=True)
    monkeypatch.setattr(likely, "ayar_yukle", lambda: cfg)
    assert kasa.oto_kasa(AYAR, x, bugun) and len(x.postlar) == 4  # önce yalnızca 4 postluk duyuru
    assert [y for _, y in x.yanitlar] == [None, "1", "2", "3"]  # flood: her post bir öncekine yanıt
    assert [bool(m) for m, _ in x.medyalar] == [True, False, False, False]  # grafik ilk postta
    assert kasa.oto_kasa(AYAR, x, bugun + timedelta(minutes=15))  # bugünün grafiği
    assert x.postlar[-1].startswith("📈") and v["gunler"][1]["kasa"]["tweet_id"] == "5"
    assert not kasa.oto_kasa(AYAR, x, bugun + timedelta(minutes=30))  # günde bir kez
    assert "kasa" not in v["gunler"][0]  # duyurudan önceki günler için grafik atılmaz
    assert len(x.postlar) == 5


def test_E8_ayarlardaki_palet_tanimli():
    assert likely.ayar_yukle().kasa_paleti in kasa.PALETLER


def test_E8_duyuru_floodu_sanal_kasanin_ornegi_ve_denetci():
    """Duyurudaki örnek sanal kasanın kendisiyle: 10.000 € → 300 €, sonra 9.700 €'nun %3'ü = 291 €."""
    v = veri(("2026-10-24", [kupon(1, T0, "tuttu", 2.0, sonuc=T0 + timedelta(hours=3))]))
    metinler, png, izinli = kasa.duyuru_hazirla(v, bugun=datetime(2026, 10, 25).date())
    assert len(metinler) == 4 and png[:4] == b"\x89PNG"
    assert "€10,000" in metinler[0] and "€10,300" in metinler[0]
    assert "€300" in metinler[1] and "€9,700" in metinler[1] and "€291" in metinler[1]
    assert "30 Nov" in metinler[3]
    for m in metinler:
        assert not kasa.denetle(m, izinli), (m, kasa.denetle(m, izinli))
        assert m.rstrip().splitlines()[-1].startswith("18+")
    assert "not real money" in metinler[0] and metinler[3].endswith(ANSVAR)


def test_E8_denetci_engeller():
    izinli = {"€10,000"}
    iyi = "Virtual bank: €10,000.\n\nVirtual bank, not real money.\n" + ANSVAR
    assert not kasa.denetle(iyi, izinli)
    for kotu in (iyi.replace("€10,000", "€12,000"),           # kayıtta olmayan tutar
                 iyi.replace("Virtual", "Lock it in. Virtual", 1),
                 iyi.replace("Virtual", "Stake it. Virtual", 1),
                 iyi.replace("Virtual", "Bet365 — virtual", 1),
                 iyi.replace("Virtual", "#bank @x Virtual", 1),
                 iyi.replace(ANSVAR, "Play responsibly"),
                 "x" * 300 + "\n18+"):
        assert kasa.denetle(kotu, izinli), kotu


def test_E8_denetciden_gecmeyen_post_gitmez(monkeypatch):
    bugun = datetime(2026, 10, 26, 21, 0, tzinfo=UTC)
    v = veri(("2026-10-26", [kupon(2, bugun - timedelta(hours=6), "tuttu", sonuc=bugun - timedelta(hours=1))]))
    v["kasa_duyuru"] = {"ids": ["1", "2", "3", "4"], "tarih": "2026-10-26"}
    cfg = likely.LikelyAyar(aktif=True, mod="otomatik", oto_kasa=True)
    monkeypatch.setattr(likely, "ayar_yukle", lambda: cfg)
    monkeypatch.setattr(likely, "yukle", lambda: v)
    monkeypatch.setattr(likely, "kaydet", lambda _: None)
    monkeypatch.setattr(kasa, "post_hazirla", lambda *a, **k: ("Lock it. €5\n18+", b"", set()))
    x, uyari = SahteX(), []
    assert not kasa.oto_kasa(AYAR, x, bugun, yaz=uyari.append)
    assert not x.postlar and v["gunler"][0]["kasa"]["tweet_id"] == "denetci" and "⚠️" in uyari[0]


def test_E8_duyuru_yarida_kalirsa_kaldigi_yerden_surer(monkeypatch):
    bugun = datetime(2026, 10, 26, 21, 0, tzinfo=UTC)
    v = veri(("2026-10-26", [kupon(2, bugun - timedelta(hours=6), "bekliyor")]))
    cfg = likely.LikelyAyar(aktif=True, mod="otomatik", oto_kasa=True)
    monkeypatch.setattr(likely, "ayar_yukle", lambda: cfg)
    monkeypatch.setattr(likely, "yukle", lambda: v)
    monkeypatch.setattr(likely, "kaydet", lambda _: None)
    x = SahteX(bozuk_sira=3)
    try:
        kasa.oto_kasa(AYAR, x, bugun)
    except RuntimeError:
        pass
    assert v["kasa_duyuru"]["ids"] == ["1", "2"]
    assert kasa.oto_kasa(AYAR, x, bugun + timedelta(minutes=15))
    assert v["kasa_duyuru"]["ids"] == ["1", "2", "3", "4"] and x.yanitlar[2][1] == "2"


def _gunler(*farklar, bas=10000.0):
    m, k = [], bas
    for i, f in enumerate(farklar):
        m.append({"tarih": f"2026-10-{10 + i:02d}", "acilis": k, "yuksek": max(k, k + f), "dusuk": min(k, k + f),
                  "kapanis": k + f})
        k += f
    return m


def test_E8_gunluk_ilk_satir_kayittan_degisir():
    assert kasa.ilk_satir(_gunler(100, -50, 20, 30, 500)) == "Best day so far."
    assert kasa.ilk_satir(_gunler(100, -50, 20, 30, -500)) == "Worst day so far."
    assert kasa.ilk_satir(_gunler(100, -50, 80)) == "New high."
    assert kasa.ilk_satir(_gunler(100, -50, -20)) == "Second red day in a row."
    assert kasa.ilk_satir(_gunler(-300, 50, 20, 10, 5, 1)) == "Fifth green day in a row."
    assert kasa.ilk_satir(_gunler(100, 30, -50, 20)) == ""
