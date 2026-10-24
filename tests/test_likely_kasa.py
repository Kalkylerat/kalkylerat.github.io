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
    """Sahibinin örneği: 100 € → ilk kupon 3 € (açık kalır), ikinci kupon 97 €'nun %3'ü = 2,91 €."""
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
    assert h["paylar"]["2"] == round((1000 - 30 + 75) * 0.03, 2)


def test_E8_iade_payi_getirir_iade_ayak_1_sayilir_paylasilmayan_sayilmaz():
    v = veri(("2026-10-26", [kupon(1, T0, "iade", 2.0, sonuc=T0 + timedelta(hours=2)),
                             kupon(2, T0 + timedelta(hours=3), "tuttu", 2.0, son_oran=1.5, sonuc=T0 + timedelta(hours=5)),
                             {"ad": "plan", "oto": True, "durum": "bekliyor", "oran": 2.0, "ayaklar": []}]))
    h = kasa.hesapla(v)
    assert len(h["paylar"]) == 2
    assert h["kasa"] == round(1000 + 30 * 0.5, 2)


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
        metin, png = kasa.post_hazirla(v, t)
        _metin_kurali(metin)
        assert metin.startswith(beklenen) and png[:4] == b"\x89PNG"
    metin, _ = kasa.post_hazirla(v, "2026-10-24")
    assert kasa._euro(kasa.gunluk_mumlar(kasa.hesapla(v))[0]["kapanis"]) in metin  # rakam kayıttan
    _metin_kurali(kasa.DUYURU)
    for palet in kasa.PALETLER:
        assert kasa.grafik(kasa.gunluk_mumlar(kasa.hesapla(v)), "x", kasa.gun_etiketi, palet)[:4] == b"\x89PNG"


def test_E8_kupon_postunda_pay_yazmaz():
    k = {"ad": "gunun-kuponu", "oran": 2.1, "olasilik": 0.47,
         "ayaklar": [{"ev": "A", "dep": "B", "etiket": "Over 1.5 goals", "oran": 1.45, "baslama": T0.isoformat()},
                     {"ev": "C", "dep": "D", "etiket": "Home win", "oran": 1.45, "baslama": T0.isoformat()}]}
    metin = likely.kupon_metni(k, k["ayaklar"], "t")
    assert "€" not in metin and "stake" not in metin.lower()


class SahteX:
    def __init__(self):
        self.postlar = []

    def medya_yukle(self, png):
        return "m"

    def gonder(self, metin, **k):
        self.postlar.append(metin)
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
    assert kasa.oto_kasa(AYAR, x, bugun) and x.postlar == [kasa.DUYURU]  # önce yalnızca duyuru
    assert kasa.oto_kasa(AYAR, x, bugun + timedelta(minutes=15))  # bugünün grafiği
    assert x.postlar[-1].startswith("📈") and v["gunler"][1]["kasa"]["tweet_id"] == "2"
    assert not kasa.oto_kasa(AYAR, x, bugun + timedelta(minutes=30))  # günde bir kez
    assert "kasa" not in v["gunler"][0]  # duyurudan önceki günler için grafik atılmaz
    assert len(x.postlar) == 2


def test_E8_ayarlardaki_palet_tanimli():
    assert likely.ayar_yukle().kasa_paleti in kasa.PALETLER
