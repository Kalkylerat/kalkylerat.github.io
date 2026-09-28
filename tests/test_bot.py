import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from bot import config, editor, football, kayit, model, tweets
from bot.__main__ import main

AYAR = config.yukle()
SIMDI = datetime(2026, 10, 4, tzinfo=timezone.utc)


def test_poisson_olasiliklari_tutarli():
    p = model.model_olasiliklari(1.6, 1.1)
    assert p["MS1"] + p["MSX"] + p["MS2"] == pytest.approx(1, abs=1e-4)
    assert p["UST25"] + p["ALT25"] == pytest.approx(1, abs=1e-4)
    assert p["IY1"] + p["IYX"] + p["IY2"] == pytest.approx(1, abs=1e-4)
    assert p["UST15"] > p["UST25"] > p["UST35"]
    assert p["IYU05"] + p["IYA05"] == pytest.approx(1, abs=1e-4)


def test_piyasa_marji_arindirilir():
    p = model.piyasa_olasiliklari({"MS1": 1.9, "MSX": 3.5, "MS2": 4.0, "UST25": 1.9, "ALT25": 1.9,
                                   "KORU95": 1.8, "KORA95": 2.0, "IYU05": 1.3})
    assert p["MS1"] + p["MSX"] + p["MS2"] == pytest.approx(1)
    assert p["UST25"] == pytest.approx(0.5)
    assert p["KORU95"] + p["KORA95"] == pytest.approx(1)
    assert "IYU05" not in p  # eşi (IYA05) olmadan marj arındırılamaz
    assert p["CS1X"] == pytest.approx(p["MS1"] + p["MSX"])


def test_adil_olasilik_keskin_yoksa_ortalama():
    b = {"A": {"UST25": 1.9, "ALT25": 1.9}, "B": {"UST25": 1.8, "ALT25": 2.0}, "C": {"UST25": 2.0, "ALT25": 1.8}}
    adil, kaynak = model.adil_olasiliklar(b, "Pinnacle")
    assert adil["UST25"] == pytest.approx(0.5, abs=0.01)
    assert kaynak["UST25"].startswith("average")
    b["Pinnacle"] = {"UST25": 1.5, "ALT25": 2.8}
    adil, kaynak = model.adil_olasiliklar(b, "pinnacle")
    assert kaynak["UST25"] == "Pinnacle" and adil["UST25"] > 0.6


def test_piyasa_orani_medyan_ve_sadece_listedeki_bahisciler():
    b = {"Unibet": {"MS1": 2.1}, "Bet365": {"MS1": 2.2}, "Betano": {"MS1": 2.0}, "1xBet": {"MS1": 2.6}}
    oran, bolag, detay = model.piyasa_oranlari(b, ["Unibet", "Bet365", "Betano"])["MS1"]
    assert (oran, bolag) == (2.1, "median of 3") and len(detay) == 3


def test_bet_builder_iliskiyi_hesaba_katar():
    lam = [2.2, 0.6]
    ms1 = dict(pazar="MS1", oran=1.5, adil_olasilik=0.66, beklenen_gol=lam)
    ust = dict(pazar="UST25", oran=1.9, adil_olasilik=0.52, beklenen_gol=lam)
    oran, p = model.bet_builder([ms1, ust])
    assert p > 0.66 * 0.52 and oran < 1.5 * 1.9  # ev sahibi galibiyeti ile çok gol birlikte daha olası
    kor = dict(pazar="KORU95", oran=1.8, adil_olasilik=0.55, beklenen_gol=lam)
    assert model.bet_builder([ms1, kor]) == (2.7, 0.363)  # korner için model yok: bağımsız kabul


@pytest.mark.parametrize("pazar,ev,dep,iy,korner,beklenen", [
    ("MS1", 2, 1, None, None, True), ("CSX2", 0, 0, None, None, True), ("CS12", 1, 1, None, None, False),
    ("UST15", 1, 1, None, None, True), ("ALT35", 2, 2, None, None, False), ("KGYOK", 0, 3, None, None, True),
    ("IY1", 2, 1, (0, 0), None, False), ("IYX", 2, 1, (0, 0), None, True), ("IYU05", 1, 0, (1, 0), None, True),
    ("IYA15", 3, 2, (1, 1), None, False), ("KORU95", 0, 0, None, 10, True), ("KORA85", 0, 0, None, 9, False),
    ("KORU95", 1, 0, None, None, None), ("IY2", 0, 1, None, None, None),
])
def test_kazandi_mi(pazar, ev, dep, iy, korner, beklenen):
    assert model.kazandi_mi(pazar, ev, dep, iy, korner) is beklenen


def test_pazar_kodlari_ve_etiketler():
    assert football.pazar_kodu("Goals Over/Under", "Over 1.5") == "UST15"
    assert football.pazar_kodu("Corners Over Under", "Under 10.5") == "KORA105"
    assert football.pazar_kodu("Goals Over/Under First Half", "Over 0.5") == "IYU05"
    assert football.pazar_kodu("Goals Over/Under", "Over 5.5") is None
    assert football.pazar_kodu("Asian Handicap", "Home -1") is None
    assert model.etiketler("KORA105", "A", "B")[1] == "Under 10.5 corners"
    assert model.etiketler("UST35", "A", "B") == ("Over 3.5 goals", "Over 3.5 goals")
    assert model.etiketler("ALT15", "A", "B")[0] == "Under 1.5 goals"
    assert model.etiketler("IYA15", "A", "B")[0] == "1st half Under 1.5 goals"
    assert model.etiketler("KORU85", "A", "B")[0] == "Over 8.5 corners"
    assert model.etiketler("CSX2", "A", "B")[0] == "Double chance X2"
    assert not any("(" in model.etiketler(k, "A", "B")[0] for k in ("IYU05", "KGYOK", "MS1", "ALT25"))


def test_aday_turu():
    assert model.aday_turu(0.72, -0.03, AYAR) == "guvenli"
    assert model.aday_turu(0.72, -0.06, AYAR) == "guvenli"
    assert model.aday_turu(0.72, -0.08, AYAR) is None
    assert model.aday_turu(0.50, 0.05, AYAR) == "deger"
    assert model.aday_turu(0.40, 0.10, AYAR) is None


def _secim(fid, oran, p, pazar="MS1", **ek):
    s = {"fixture_id": fid, "lig": "Test League", "pazar": pazar, "oran": oran, "adil_olasilik": p, "tur": "guvenli",
         "baslama": "2026-10-03T15:00:00+02:00", "saat": "15:00 CEST", "durum": "bekliyor", "stake": 100.0,
         "ev": f"Home{fid}", "dep": f"Away{fid}", "etiket": "Home to win", "kisa": f"Home{fid} win",
         "olasi_skor": "2-0", "yorum": ""}
    s.update(ek)
    return s


def _gun(gid, secimler, tweet_id="t1", kombi=None):
    g = {"id": gid, "tarih": gid, "sonuc": None, "tweet_id": tweet_id, "secimler": secimler, "para": "€", "yuzde": 1.0}
    if kombi:
        g["kombi"] = {"ayaklar": kombi, "stake": 100.0, "durum": None}
    return g


def test_kombi_gunun_butun_oyunlari():
    secimler = [_secim(1, 1.25, 0.76), _secim(2, 1.35, 0.706), _secim(3, 1.27, 0.739)]
    assert model.kombi_kur(secimler) == [0, 1, 2]
    assert model.kombi_kur([_secim(1, 1.3, 0.8)]) is None
    g = _gun("2026-09-28", secimler, kombi=[0, 1, 2])
    assert kayit.kombi_oran(g) == pytest.approx(2.14, abs=0.01)
    assert kayit.kombi_olasilik(g) == pytest.approx(0.397, abs=0.001)


def test_sonuclandirma_ve_kasa():
    g1 = _gun("a", [_secim(1, 2.0, 0.5), _secim(2, 1.5, 0.7)], kombi=[0, 1])
    g2 = _gun("b", [_secim(1, 1.8, 0.6)], tweet_id=None)
    biten = kayit.sonuclandir([g1], {1: {"durum": "bitti", "skor": (2, 0)}, 2: {"durum": "bekliyor", "skor": None}}, SIMDI)
    assert biten == [] and g1["secimler"][0]["durum"] == "kazandi"
    biten = kayit.sonuclandir([g1], {2: {"durum": "bitti", "skor": (0, 1)}}, SIMDI)
    assert biten == [g1] and g1["kombi"]["durum"] == "yatti"
    kayit.sonuclandir([g2], {1: {"durum": "bitti", "skor": (1, 0)}}, SIMDI)
    o = kayit.ozet([g1, g2], 10000)
    assert (o["spel"], o["vunna"], o["forlorade"]) == (2, 1, 1)  # yayınlanmamış g2 sayılmaz
    assert (o["kombi"], o["kombi_tuttu"]) == (1, 0)
    assert o["kasa"] == pytest.approx(10000 + 100 - 100 - 100)


def test_korner_verisi_yoksa_iptal_ve_kasa_etkilenmez():
    g = _gun("a", [_secim(1, 1.9, 0.55, "KORU95")])
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (1, 0), "korner": None}}, SIMDI)
    assert g["secimler"][0]["durum"] == "iptal" and kayit.ozet([g], 10000)["kasa"] == 10000


def test_uzun_bekleyen_mac_iptal_olur():
    g = _gun("a", [_secim(1, 1.5, 0.7)])
    kayit.sonuclandir([g], {}, datetime(2026, 10, 7, tzinfo=timezone.utc))
    assert g["sonuc"] == "tamam" and g["secimler"][0]["durum"] == "iptal"


def test_tweetler_sinirda_ve_ansvar_satiri_kalir():
    uzun = dict(ev="Borussia Mönchengladbach", dep="Wolverhampton Wanderers", yorum="x" * 400)
    secimler = [_secim(i, 1.5 + i / 10, 0.7, "UST15", kisa="Over 1.5 goals", tur="deger", **uzun) for i in range(1, 4)]
    g = _gun("2026-10-03", secimler, kombi=[0, 1, 2])
    ana = tweets.gun_tweeti(g, kayit.ozet([], 10000))
    assert tweets.uzunluk(ana) <= 280 and ana.endswith(tweets.ANSVAR)
    assert all(tweets.uzunluk(t) <= 280 for t in tweets.analiz_tweetleri(g))
    for s in g["secimler"]:
        s.update(durum="kazandi", skor="2-1")
    g["sonuc"] = "tamam"
    assert all(tweets.uzunluk(t) <= 280 for t in tweets.gun_floodu(g, kayit.ozet([], 10000)))
    assert all(tweets.uzunluk(t) <= 280 for t in tweets.sonuc_tweetleri(g, kayit.ozet([g], 10000)))
    assert tweets.uzunluk("⚽") == 2 and tweets.uzunluk("ö") == 1


def test_ana_tweet_icerigi():
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7, "UST25", kisa="Over 2.5 goals", tur="deger")],
             kombi=[0, 1])
    ana, kasa, *analiz = tweets.gun_floodu(g, kayit.ozet([], 10000))
    assert "⚽ TODAY'S COUPON | 3 Oct" in ana
    assert "1) Home1 v Away1\nHome1 win · odds 1.50" in ana
    assert "2) Home2 v Away2\nOver 2.5 goals · odds 1.40" in ana
    assert "Total odds 2.10 · real chance 56%" in ana and "€100 stake → €210 return" in ana
    assert "💰 Bank €10,000 (virtual) · 1% per bet" in kasa
    assert "€100 → €210 if all win" in kasa and "1) Home1 win → €150" in kasa
    assert len(analiz) == 2 and analiz[1].startswith("2) Home2 v Away2 · 15:00 CEST\nPick: ")
    assert "value pick" in analiz[1]


def test_sonuc_tweeti_kasa_ve_kombine():
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], kombi=[0, 1])
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (2, 0)}, 2: {"durum": "bitti", "skor": (1, 0)}}, SIMDI)
    o = kayit.ozet([g], 10000)
    assert o["kasa"] == pytest.approx(10000 + 50 + 40 + 110)
    sonuclar, para = tweets.sonuc_tweetleri(g, o)
    assert "✅ Home1 2–0 Away1" in sonuclar and "🎯 Coupon: ✅ won" in sonuclar
    assert "🎯 Coupon: +€110" in para and "Singles: 2/2 won, +€90" in para
    assert "💰 Bank: €10,200" in para and "coupons 1/1" in para


class _Ctx:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return SimpleNamespace(get_final_message=lambda: self.msg)

    def __exit__(self, *a):
        return False


class SahteClaude:
    def __init__(self, yanitlar):
        self.yanitlar = list(yanitlar)
        self.cagrilar = []
        self.messages = self

    def stream(self, **kw):
        self.cagrilar.append(kw)
        metin = json.dumps(self.yanitlar.pop(0), ensure_ascii=False)
        return _Ctx(SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=metin)]))


def _adaylar():
    return [{"aday_id": f"{i}-MS1", "fixture_id": i, "oran": o, "deger": 0.03, "adil_olasilik": 0.7}
            for i, o in [(1, 1.8), (2, 1.9)]]


def test_claude_hatali_secimi_duzeltir():
    kotu = {"secimler": [{"aday_id": "9-MS1", "yorum": "a"}], "baslik": "b", "gerekce_yoksa": ""}
    iyi = {"secimler": [{"aday_id": "1-MS1", "yorum": "a"}], "baslik": "b", "gerekce_yoksa": ""}
    c = SahteClaude([kotu, iyi])
    assert editor.claude_ile_sec({1: {}, 2: {}}, _adaylar(), AYAR, client=c) == iyi
    assert len(c.cagrilar) == 2
    assert c.cagrilar[0]["model"] == AYAR.claude_model
    assert c.cagrilar[0]["output_config"]["format"]["type"] == "json_schema"
    assert "Unknown aday_id" in c.cagrilar[1]["messages"][-1]["content"]


def test_claude_pas_gecebilir():
    pas = {"secimler": [], "baslik": "", "gerekce_yoksa": "Nothing convincing"}
    assert editor.claude_ile_sec({1: {}, 2: {}}, _adaylar(), AYAR, client=SahteClaude([pas])) == pas


def test_dogrulama_mac_basina_sinir():
    a = {x["aday_id"]: x for x in _adaylar()}
    for pazar in ("UST15", "KORU95"):
        a[f"1-{pazar}"] = {"aday_id": f"1-{pazar}", "fixture_id": 1, "oran": 1.5}
    iki = [{"aday_id": "1-MS1"}, {"aday_id": "1-UST15"}]
    assert editor.secimi_dogrula(iki, a, AYAR) is None
    uc = iki + [{"aday_id": "1-KORU95"}]
    assert "same match" in editor.secimi_dogrula(uc, a, AYAR)
    assert "twice" in editor.secimi_dogrula([{"aday_id": "1-MS1"}] * 2, a, AYAR)


def test_demo_uctan_uca(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["demo"]) == 0
    cikti = capsys.readouterr().out
    assert "TODAY'S COUPON" in cikti and "RESULTS | 3 Oct" in cikti
    assert "value pick" in cikti and "Total odds" in cikti and "Bank €10," in cikti
    assert "1xBet" not in cikti  # listede olmayan bahisçi asla kullanılmaz
    assert "Djurgården" not in cikti.split("TWEET #1")[1]  # kriteri geçmeyen maç seçilmez


def test_api_istek_siniri_bekler_ve_tekrar_dener(monkeypatch):
    beklemeler = []
    monkeypatch.setattr(football.time, "sleep", beklemeler.append)

    class Yanit:
        def __init__(self, kod, govde):
            self.status_code, self._govde = kod, govde

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(self.status_code)

        def json(self):
            return self._govde

    yanitlar = [Yanit(429, {}), Yanit(200, {"errors": [], "response": [1, 2]}), Yanit(200, {"errors": [], "response": [3]})]
    oturum = SimpleNamespace(headers={}, get=lambda *a, **k: yanitlar.pop(0))
    api = football.ApiFootball("anahtar", session=oturum, aralik=6.5)
    assert api.get("fixtures") == [1, 2]
    assert 60 in beklemeler
    assert api.get("odds") == [3]
    assert any(0 < b <= 6.5 for b in beklemeler)


def test_en_olasi_skor():
    skor, p = model.en_olasi_skor(2.2, 0.6)
    assert skor == "2-0" and 0 < p < 1


def test_bet_builder_birlestirme_ve_sonuclandirma():
    from bot.__main__ import bet_builder_birlestir
    lam = [1.8, 0.9]
    a = _secim(1, 1.5, 0.66, "MS1", beklenen_gol=lam, yorum="Home are strong.")
    b = _secim(1, 1.3, 0.75, "UST15", kisa="Over 1.5 goals", etiket="2+ goals", beklenen_gol=lam, yorum="")
    c = _secim(2, 1.4, 0.7, "MS1", beklenen_gol=lam)
    secimler = bet_builder_birlestir([a, b, c])
    assert len(secimler) == 2
    bb = secimler[0]
    assert bb["bet_builder"] and bb["kisa"] == "Home1 win + Over 1.5 goals" and bb["yorum"] == "Home are strong."
    g = _gun("2026-10-03", secimler, kombi=model.kombi_kur(secimler))
    ana = tweets.gun_tweeti(g, kayit.ozet([], 10000))
    assert f"1) Home1 v Away1\nHome1 win + Over 1.5 goals · odds ≈{bb['oran']:.2f}" in ana
    assert "bet builder" in tweets.analiz_tweetleri(g)[0]
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (1, 0)}, 2: {"durum": "bitti", "skor": (2, 0)}}, SIMDI)
    assert bb["durum"] == "kaybetti" and [x["durum"] for x in bb["bacaklar"]] == ["kazandi", "kaybetti"]
    assert secimler[1]["durum"] == "kazandi"


def test_istek_siniri_dolarsa_toplananlarla_devam_eder(monkeypatch, capsys):
    from bot.__main__ import tahmin
    api = football.DemoApi(config.ROOT / "ornek" / "api_football.json")
    asil = api.get

    def sinirli(path, **params):
        if path == "odds" and params.get("fixture") == 9104:
            raise football.ApiHatasi("request limit")
        return asil(path, **params)

    api.get = sinirli
    simdi = datetime.fromisoformat(api.data["simdi"])
    gun = tahmin(AYAR, api, editor.basit_sec, [], "2026-10-03", simdi)
    assert gun and gun["secimler"] and "Tarama erken bitti" in capsys.readouterr().out


def test_uc_oyunlu_gunde_kasa_satiri_kalir():
    ms = [("Bulgaria", "Estonia", "Under 3.5 goals", 1.20, 0.79), ("Czechia", "England", "Over 1.5 goals", 1.22, 0.78),
          ("Spain", "Croatia", "1st-half goal", 1.25, 0.76)]
    secimler = [_secim(i, o, p, "UST15", ev=e, dep=d, kisa=k) for i, (e, d, k, o, p) in enumerate(ms, 1)]
    flood = tweets.gun_floodu(_gun("2026-09-29", secimler, kombi=[0, 1, 2]), kayit.ozet([], 10000))
    assert all(f"{e} v {d}" in flood[0] for e, d, *_ in ms)  # her oyunda maç adı olmalı
    assert "💰 Bank" in flood[1] and all(tweets.uzunluk(t) <= 280 for t in flood)


def test_tweetlerde_at_isareti_yok():
    """X "@" ile başlayan her şeyi kullanıcı etiketi sanar; oranlar asla "@1.25" gibi yazılmamalı."""
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7, "UST25", kisa="Over 2.5 goals")], kombi=[0, 1])
    metinler = tweets.gun_floodu(g, kayit.ozet([], 10000))
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (2, 0)}, 2: {"durum": "bitti", "skor": (1, 2)}}, SIMDI)
    metinler += tweets.sonuc_tweetleri(g, kayit.ozet([g], 10000))
    assert not any("@" in m for m in metinler)


def test_sabit_tweetler_sinirda_ve_eskileri_siler():
    from bot.__main__ import sabit_tweet
    link_farki = len("https://kalkylerat.github.io/") - 23  # X her linki 23 karakter sayar
    assert tweets.uzunluk(tweets.SABIT_TWEETLER[0]) - link_farki <= 280
    assert tweets.uzunluk(tweets.SABIT_TWEETLER[1]) <= 280

    class SahteX(tweets.KonsolClient):
        silinen = []

        def son_tweetler(self):
            return [{"id": "1", "text": "Welcome to Kalkylerat 📊 ..."}, {"id": "2", "text": "⚽ TODAY'S PICKS | 28 Sep"}]

        def sil(self, tid):
            self.silinen.append(tid)

    x = SahteX()
    sabit_tweet(x)
    assert x.silinen == ["1"] and x.sayac == 2


def test_uzun_isim_ve_aciklama_kesilmez():
    """Takım adı ve açıklama cümle ortasından kesilmemeli; sığmazsa önce gereksiz satırlar düşer."""
    yorum = "Their last meeting ended 0-1 and neither side scored more than once lately. About a 3 in 4 chance of it."
    ms = [("Georgia", "Ukraine", "Under 3.5 goals"), ("Leganes", "Castellón", "Castellón win or draw"),
          ("Northern Ireland", "Hungary", "Under 1.5 goals in 1st half")]
    secimler = [_secim(i, 1.27, 0.74, "IYA15", ev=e, dep=d, kisa=k, yorum=yorum,
                       etiket="1st half Under 1.5 goals")
                for i, (e, d, k) in enumerate(ms, 1)]
    flood = tweets.gun_floodu(_gun("2026-09-28", secimler, kombi=[0, 1, 2]), kayit.ozet([], 10000))
    assert "3) Northern Ireland v Hungary" in flood[0]
    assert not any("…" in t for t in flood) and all(tweets.uzunluk(t) <= 280 for t in flood)


def test_oran_takipcinin_bulabilecegi_pazardan_olmali():
    assert model.oran_yeterli({"Bet365": 1.3, "Unibet": 1.28, "Betano": 1.27}, AYAR)
    assert not model.oran_yeterli({"Bet365": 1.3, "Unibet": 1.28}, AYAR)  # çok az site
    assert not model.oran_yeterli({"Unibet": 1.3, "Betano": 1.28, "Betsson": 1.27}, AYAR)  # zorunlu site yok


def test_keskin_bahisci_yoksa_sinir_sikilasir():
    assert model.aday_turu(0.74, -0.062, AYAR) == "guvenli"
    assert model.aday_turu(0.74, -0.062, AYAR, AYAR.keskinsiz_ek_marj) is None
    assert model.aday_turu(0.74, -0.03, AYAR, AYAR.keskinsiz_ek_marj) == "guvenli"


def test_kupon_gorseli_png():
    from bot import gorsel
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7, "UST25", kisa="Over 2.5 goals",
                                                        ev="Borussia Mönchengladbach", dep="Wolverhampton Wanderers")],
             kombi=[0, 1])
    png = gorsel.kupon_gorseli(g)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) < 5_000_000


def test_yayinla_gorseli_ana_tweete_ekler(capsys):
    from bot.__main__ import yayinla
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id=None, kombi=[0, 1])
    assert yayinla(AYAR, g, tweets.KonsolClient(), [g], datetime(2026, 10, 3, 8, tzinfo=timezone.utc))
    cikti = capsys.readouterr().out
    assert "TWEET #1 + gorsel-" in cikti and "TWEET #2 (yanıt) [" in cikti
    ana = cikti.split("TWEET #1")[1].split("TWEET #2")[0]
    assert "Why these picks 👇" in ana and "⚽ Home1 v Away1" in ana and "Total odds 2.10" in ana


def test_haftalik_ozet_bir_kez_ve_yeterli_veriyle(monkeypatch, tmp_path):
    from bot.__main__ import haftalik
    monkeypatch.setattr(config, "HAFTA_FILE", tmp_path / "haftalik.json")
    gunler = []
    for i, gun in enumerate(["2026-09-22", "2026-09-24", "2026-09-27"]):
        g = _gun(gun, [_secim(10 * i + 1, 1.5, 0.7), _secim(10 * i + 2, 1.3, 0.75)], kombi=[0, 1])
        g["secimler"][0].update(durum="kazandi", skor="2-0")
        g["secimler"][1].update(durum="kaybetti" if i == 0 else "kazandi", skor="0-1")
        g["sonuc"] = "tamam"
        gunler.append(g)
    pazar_aksam = datetime(2026, 9, 27, 21, 30, tzinfo=timezone.utc)
    x = tweets.KonsolClient()
    assert not haftalik(AYAR, x, gunler[:1], pazar_aksam)  # tek gün: özet yok
    assert not haftalik(AYAR, x, gunler, datetime(2026, 9, 26, 21, 30, tzinfo=timezone.utc))  # Cumartesi
    assert haftalik(AYAR, x, gunler, pazar_aksam)
    assert not haftalik(AYAR, x, gunler, pazar_aksam + timedelta(hours=11))  # Pazartesi tekrar atmaz
    h = kayit.hafta_ozeti(gunler, "2026-09-27")
    metin = tweets.hafta_tweeti(h, kayit.ozet(gunler, 10000), "€")
    assert "WEEKLY RECAP | 21–27 Sep" in metin and "✅ 5 won · ❌ 1 lost (83%)" in metin
    assert "Coupons: 2 of 3 won" in metin and tweets.uzunluk(metin) <= 280 and "@" not in metin


def test_gorsel_yukleme_tekrar_dener():
    from bot.__main__ import _gorsel_yukle
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], kombi=[0, 1])
    hatalar = [RuntimeError("503"), RuntimeError("timeout")]

    class X:
        def medya_yukle(self, png):
            if hatalar:
                raise hatalar.pop(0)
            return "m1"

    bekleme = []
    assert _gorsel_yukle(X(), g, bekleme.append) == "m1" and len(bekleme) == 2 and "gorsel_eksik" not in g
    hatalar.extend(RuntimeError("x") for _ in range(9))
    assert _gorsel_yukle(X(), g, bekleme.append) is None and g["gorsel_eksik"]


def test_bet_builder_kaybeden_ayak_varsa_kaybeder():
    """Korner verisi yok ama gol ayağı kaybetti: oyun iptal değil, kayıp sayılmalı."""
    bb = _secim(1, 3.0, 0.3, "BB", bet_builder=True,
                bacaklar=[{"pazar": "UST25", "durum": "bekliyor"}, {"pazar": "KORU95", "durum": "bekliyor"}])
    g = _gun("2026-10-03", [bb])
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (0, 0), "korner": None}}, SIMDI)
    assert bb["durum"] == "kaybetti"


def test_sonuc_floodu_x_hatasinda_sonra_tamamlanir(monkeypatch):
    from bot.__main__ import sonuc
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], kombi=[0, 1])
    monkeypatch.setattr(football, "sonuclari_al",
                        lambda api, ids, korner: {1: {"durum": "bitti", "skor": (2, 0)}, 2: {"durum": "bitti", "skor": (1, 0)}})

    class X:
        def __init__(self, hata_sirasi=None):
            self.atilan, self.hata_sirasi = [], hata_sirasi

        def gonder(self, metin, yanit=None, medya=None):
            if len(self.atilan) == self.hata_sirasi:
                raise RuntimeError("X 503")
            self.atilan.append((metin, yanit))
            return f"s{len(self.atilan)}"

    x1 = X(hata_sirasi=1)
    with pytest.raises(RuntimeError):
        sonuc(AYAR, None, x1, [g], SIMDI)
    assert g["sonuc"] == "tamam" and not g.get("sonuc_tweet_id") and g["sonuc_tweet_idleri"] == ["s1"]
    x2 = X()
    sonuc(AYAR, None, x2, [g], SIMDI)  # yalnızca eksik ikinci tweet, ilkinin altına
    assert len(x2.atilan) == 1 and x2.atilan[0][1] == "s1" and g["sonuc_tweet_id"] == "s1"
    sonuc(AYAR, None, X(), [g], SIMDI)
    assert len(g["sonuc_tweet_idleri"]) == 2


def test_yarim_flood_tamamlanir():
    from bot.__main__ import yayinla
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id="ana", kombi=[0, 1])
    g["analiz_tweet_idleri"] = ["k1"]
    x = tweets.KonsolClient()
    simdi = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
    assert yayinla(AYAR, g, x, [g], simdi) and len(g["analiz_tweet_idleri"]) == 3  # kasa + 2 analiz
    assert not yayinla(AYAR, g, x, [g], simdi)  # tamamsa bir şey atılmaz


def test_ayni_gunun_kuponu_ikinci_kez_atilmaz():
    from bot.__main__ import zaten_paylasildi
    x = SimpleNamespace(son_tweetler=lambda adet, yanitsiz: [
        {"id": "9", "text": "📅 WEEKLY RECAP | 21–27 Sep"},
        {"id": "7", "text": "TODAY'S COUPON | 28 Sep\n\n⚽ Georgia v Ukraine"}])
    assert zaten_paylasildi(x, "2026-09-28") == "7"
    assert zaten_paylasildi(x, "2026-09-29") is None


def test_yorumda_bahisci_adi_ve_etiket_olmaz():
    y = editor.temiz_yorum("Castellón won 5 of 6. Pinnacle gives 71%. Ask @someone! Unbeaten in 4.", ["Pinnacle", "Bet365"])
    assert y == "Castellón won 5 of 6. Unbeaten in 4."
    baglam = editor._baglam({1: {}}, [{"aday_id": "1-MS1", "fixture_id": 1, "adil_kaynak": "Pinnacle",
                                      "oranlar": {"Bet365": 1.5}, "bolag": "median of 3"}], AYAR)
    assert "Pinnacle" not in baglam and "Bet365" not in baglam


def test_claude_metinsiz_yanit_editor_hatasi():
    c = SimpleNamespace(messages=SimpleNamespace(stream=lambda **kw: _Ctx(
        SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="thinking")]))))
    with pytest.raises(editor.EditorHatasi):
        editor.claude_ile_sec({1: {}, 2: {}}, _adaylar(), AYAR, client=c)


def test_sonuc_hatasi_gunun_kuponunu_engellemez(monkeypatch, tmp_path):
    import bot.__main__ as ana
    monkeypatch.setattr(config, "DATA_FILE", tmp_path / "spel.json")
    monkeypatch.setattr(config, "PANEL_FILE", tmp_path / "index.html")
    monkeypatch.setattr(ana, "HATALAR", [])
    cagrilar = []
    monkeypatch.setattr(ana, "sonuc", lambda *a: (_ for _ in ()).throw(RuntimeError("API limiti")))
    monkeypatch.setattr(ana, "haftalik", lambda *a, **k: False)
    monkeypatch.setattr(ana, "zaten_paylasildi", lambda x, t: None)
    monkeypatch.setattr(ana, "tahmin", lambda *a: cagrilar.append("tahmin"))
    monkeypatch.setattr(ana, "_api", lambda ayar: None)
    monkeypatch.setattr(ana, "_x_client", lambda: None)
    monkeypatch.setattr(ana, "_secici", lambda: None)
    assert ana.main(["otomatik"]) == 1 and cagrilar == ["tahmin"]


def test_bet_builder_kuponda_toplam_oran_tahmini():
    bb = _secim(1, 2.0, 0.5, "BB", bet_builder=True, bacaklar=[])
    g = _gun("2026-10-03", [bb, _secim(2, 1.4, 0.7)], kombi=[0, 1])
    assert "Total odds ≈2.80" in tweets.gun_tweeti(g) and "Total odds ≈2.80" in tweets.gorselli_gun_tweeti(g)
