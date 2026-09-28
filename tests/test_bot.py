import json
from datetime import datetime, timezone
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
    assert model.piyasa_oranlari(b, ["Unibet", "Bet365", "Betano"])["MS1"] == (2.1, "median of 3")


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
    assert model.etiketler("UST35", "A", "B") == ("Over 3.5 goals (4 or more goals)", "Over 3.5 goals")
    assert model.etiketler("IYA15", "A", "B")[0] == "Under 1.5 goals in 1st half (0 or 1 goal before half-time)"
    assert model.etiketler("CSX2", "A", "B")[1] == "B win or draw"


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
                       etiket="Under 1.5 goals in 1st half (0 or 1 goal before half-time)")
                for i, (e, d, k) in enumerate(ms, 1)]
    flood = tweets.gun_floodu(_gun("2026-09-28", secimler, kombi=[0, 1, 2]), kayit.ozet([], 10000))
    assert "3) Northern Ireland v Hungary" in flood[0]
    assert not any("…" in t for t in flood) and all(tweets.uzunluk(t) <= 280 for t in flood)
