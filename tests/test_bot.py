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
    assert model.piyasa_oranlari(b, ["Unibet", "Bet365", "Betano"], "en_iyi")["MS1"][:2] == (2.2, "best of 3")
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
    assert model.aday_turu(0.72, 0.0, AYAR) == "guvenli"
    assert model.aday_turu(0.72, 0.02, AYAR) == "guvenli"
    assert model.aday_turu(0.72, -0.01, AYAR) is None  # adil fiyatın altı: uzun vadede kaybettirir
    assert model.aday_turu(0.50, 0.05, AYAR) == "deger"
    assert model.aday_turu(0.40, 0.10, AYAR) is None


def _secim(fid, oran, p, pazar="MS1", **ek):
    s = {"fixture_id": fid, "lig": "Test League", "pazar": pazar, "oran": oran, "adil_olasilik": p, "tur": "guvenli",
         "baslama": "2026-10-03T15:00:00+02:00", "saat": "15:00 CEST", "durum": "bekliyor", "stake": 100.0,
         "ev": f"Home{fid}", "dep": f"Away{fid}", "etiket": "Home to win", "kisa": f"Home{fid} win",
         "olasi_skor": "2-0", "yorum": ""}
    s.update(ek)
    return s


def _gun(gid, secimler, tweet_id="t1", kombi=None, kuponlar=None):
    """kombi: eski biçim (tekliler + tek kombine). kuponlar: yeni biçim, oyunlar yalnızca kuponlarda oynanır."""
    g = {"id": gid, "tarih": gid, "sonuc": None, "tweet_id": tweet_id, "secimler": secimler, "para": "€", "yuzde": 1.0}
    if kombi:
        g["kombi"] = {"ayaklar": kombi, "stake": 100.0, "durum": None}
    if kuponlar:
        for s in secimler:
            s["stake"] = 0
        g["kuponlar"] = [{"ayaklar": k, "stake": 100.0, "durum": None} for k in kuponlar]
    return g


def test_kupon_orani_ve_ihtimali():
    secimler = [_secim(1, 1.25, 0.76), _secim(2, 1.35, 0.706), _secim(3, 1.27, 0.739)]
    g = _gun("2026-09-28", secimler, kuponlar=[[0, 1, 2]])
    k = kayit.kuponlar(g)[0]
    assert kayit.kupon_oran(g, k) == pytest.approx(2.14, abs=0.01)
    assert kayit.kupon_olasilik(g, k) == pytest.approx(0.397, abs=0.001)
    eski = _gun("2026-09-28", [_secim(1, 1.25, 0.76), _secim(2, 1.35, 0.706)], kombi=[0, 1])
    assert len(kayit.kuponlar(eski)) == 1  # eski kayıtların kombisi kupon sayılır


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
    g = _gun("2026-10-03", [_secim(1, 2.0, 0.52, tur="deger"), _secim(2, 1.4, 0.7, "UST25", kisa="Over 2.5 goals"),
                            _secim(3, 1.3, 0.75)], kuponlar=[[0], [1, 2]])
    ana = tweets.gorselli_gun_tweeti(g)
    assert ana.startswith("TODAY'S 2 COUPONS | 3 Oct\n\n") and ana.endswith("in the thread 🧵\n18+ | Play responsibly")
    assert any(soru in ana for soru in tweets.KUPON_SORULARI) and tweets.uzunluk(ana) <= 280
    metin = tweets.gun_tweeti(g, kayit.ozet([], 10000))
    assert "💰 Bank €10,000 · 1% per coupon" in metin
    assert "🎫 Coupon 1: odds 2.00 · 52% chance\n€100 → €200\n• Home1 v Away1: Home1 win" in metin
    assert "🎫 Coupon 2: odds 1.82" in metin and "• Home2 v Away2: Over 2.5 goals" in metin
    analiz = tweets.analiz_tweetleri(g)
    assert analiz[0].startswith("1) Home1 v Away1 · 15:00 CEST · coupon 1\nPick: ") and "value pick" in analiz[0]
    assert "coupon 2" in analiz[2] and "high-chance pick" in analiz[2]
    assert tweets.gun_floodu(g, kayit.ozet([], 10000), gorselli=True)[1:] == analiz  # kasa tweeti yok


def test_sonuc_tweeti_kupon_bazinda():
    g = _gun("2026-10-03", [_secim(1, 2.0, 0.5), _secim(2, 1.5, 0.7), _secim(3, 1.4, 0.7)], kuponlar=[[0], [1, 2]])
    sonuc = {1: {"durum": "bitti", "skor": (0, 1)}, 2: {"durum": "bitti", "skor": (2, 0)}, 3: {"durum": "bitti", "skor": (1, 0)}}
    kayit.sonuclandir([g], sonuc, SIMDI)
    o = kayit.ozet([g], 10000)
    assert o["kasa"] == pytest.approx(10000 - 100 + 110)  # yalnızca kuponlar oynanır
    assert (o["kombi"], o["kombi_tuttu"]) == (2, 1) and (o["vunna"], o["forlorade"]) == (2, 1)
    metin, = tweets.sonuc_tweetleri(g, o)
    assert "❌ Home1 0–1 Away1" in metin and "🎫 Coupon 1: ❌ lost, -€100" in metin
    assert "🎫 Coupon 2: ✅ won, +€110" in metin and "💰 Bank: €10,010" in metin
    assert "📈 Record: coupons 1/2 won · picks 2–1 (67%)" in metin and "Singles" not in metin


def test_eski_kayit_tekli_ve_kombi_sonucu():
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], kombi=[0, 1])
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (2, 0)}, 2: {"durum": "bitti", "skor": (1, 0)}}, SIMDI)
    o = kayit.ozet([g], 10000)
    assert o["kasa"] == pytest.approx(10000 + 50 + 40 + 110)
    metin = "\n".join(tweets.sonuc_tweetleri(g, o))
    assert "🎫 Coupon: ✅ won, +€110" in metin and "Singles: 2/2 won, +€90" in metin


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
    kotu = {"secimler": [{"aday_id": "9-MS1", "yorum": "a"}], "kuponlar": [{"aday_idler": ["9-MS1"]}],
            "baslik": "b", "gerekce_yoksa": ""}
    iyi = {"secimler": [{"aday_id": "1-MS1", "yorum": "a"}], "kuponlar": [{"aday_idler": ["1-MS1"]}],
           "baslik": "b", "gerekce_yoksa": ""}
    c = SahteClaude([kotu, iyi])
    assert editor.claude_ile_sec({1: {}, 2: {}}, _adaylar(), AYAR, client=c) == iyi
    assert len(c.cagrilar) == 2
    assert c.cagrilar[0]["model"] == AYAR.claude_model
    assert c.cagrilar[0]["output_config"]["format"]["type"] == "json_schema"
    assert "Unknown aday_id" in c.cagrilar[1]["messages"][-1]["content"]


def test_claude_pas_gecebilir():
    pas = {"secimler": [], "kuponlar": [], "baslik": "", "gerekce_yoksa": "Nothing convincing"}
    assert editor.claude_ile_sec({1: {}, 2: {}}, _adaylar(), AYAR, client=SahteClaude([pas])) == pas


def test_dogrulama_mac_basina_sinir():
    a = {x["aday_id"]: x for x in _adaylar()}
    for pazar in ("UST15", "KORU95"):
        a[f"1-{pazar}"] = {"aday_id": f"1-{pazar}", "fixture_id": 1, "oran": 1.5}
    iki = [{"aday_id": "1-MS1"}, {"aday_id": "1-UST15"}]
    assert editor.secimi_dogrula(iki, a, AYAR, [{"aday_idler": ["1-MS1", "1-UST15"]}]) is None
    uc = iki + [{"aday_id": "1-KORU95"}]
    assert "same match" in editor.secimi_dogrula(uc, a, AYAR, [{"aday_idler": ["1-MS1", "1-UST15", "1-KORU95"]}])
    assert "twice" in editor.secimi_dogrula([{"aday_id": "1-MS1"}] * 2, a, AYAR, [])


def test_kupon_dogrulama():
    a = {x["aday_id"]: x for x in _adaylar()}
    a["1-UST15"] = {"aday_id": "1-UST15", "fixture_id": 1, "oran": 1.5}
    secim = [{"aday_id": "1-MS1"}, {"aday_id": "2-MS1"}]
    assert editor.secimi_dogrula(secim, a, AYAR, [{"aday_idler": ["1-MS1"]}, {"aday_idler": ["2-MS1"]}]) is None
    assert "exactly one coupon" in editor.secimi_dogrula(secim, a, AYAR, [{"aday_idler": ["1-MS1"]}])
    ayni_mac = [{"aday_id": "1-MS1"}, {"aday_id": "1-UST15"}]
    assert "same coupon" in editor.secimi_dogrula(ayni_mac, a, AYAR, [{"aday_idler": ["1-MS1"]}, {"aday_idler": ["1-UST15"]}])
    dort = [{"aday_idler": [i]} for i in ("1-MS1", "2-MS1", "1-UST15")] + [{"aday_idler": []}]
    assert "coupons" in editor.secimi_dogrula(secim + [{"aday_id": "1-UST15"}], a, AYAR, dort)


def test_demo_uctan_uca(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["demo"]) == 0
    cikti = capsys.readouterr().out
    assert "TWEET #1 + gorsel-" in cikti and "TODAY'S COUPON" in cikti and "RESULTS | 3 Oct" in cikti
    assert "value pick" in cikti and "✅ Coupon won: +€" in cikti and "Bank: €10," in cikti
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
    g = _gun("2026-10-03", secimler, kuponlar=[[0, 1]])
    ana = tweets.gun_tweeti(g, kayit.ozet([], 10000))
    assert "• Home1 v Away1: Home1 win + Over 1.5 goals" in ana and "odds ≈" in ana
    assert "bet builder" in tweets.analiz_tweetleri(g)[0]
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (1, 0)}, 2: {"durum": "bitti", "skor": (2, 0)}}, SIMDI)
    assert bb["durum"] == "kaybetti" and [x["durum"] for x in bb["bacaklar"]] == ["kazandi", "kaybetti"]
    assert secimler[1]["durum"] == "kazandi"


def test_istek_siniri_dolarsa_toplananlarla_devam_eder(monkeypatch, capsys):
    """Toplu tarama çalışmazsa maç maç taramaya geçilir; o da sınıra takılırsa toplananlarla devam edilir."""
    from bot.__main__ import tahmin
    api = football.DemoApi(config.ROOT / "ornek" / "api_football.json")
    asil = api.get

    def sinirli(path, _sayma=False, **params):
        if path == "odds" and params.get("fixture") == 9104:
            raise football.ApiHatasi("request limit")
        return asil(path, _sayma=_sayma, **params)

    def toplu_yok(path, **params):
        raise football.ApiHatasi("request limit")

    api.get = sinirli
    api.get_body = toplu_yok
    simdi = datetime.fromisoformat(api.data["simdi"])
    gun = tahmin(AYAR, api, editor.basit_sec, [], "2026-10-03", simdi)
    cikti = capsys.readouterr().out
    assert gun and gun["secimler"] and "maç maç taramaya geçiliyor" in cikti and "Tarama erken bitti" in cikti


def test_toplu_tarama_az_istekle_cok_mac(capsys):
    from bot.__main__ import tahmin
    api = football.DemoApi(config.ROOT / "ornek" / "api_football.json")
    simdi = datetime.fromisoformat(api.data["simdi"])
    gun = tahmin(AYAR, api, editor.basit_sec, [], "2026-10-03", simdi)
    assert gun and gun["secimler"] and "oranı okundu" in capsys.readouterr().out


def test_liste_disi_ligde_keskin_fiyat_sart():
    b = {"Bet365": {"MS1": 1.40, "MSX": 4.5, "MS2": 8.0}, "Unibet": {"MS1": 1.41, "MSX": 4.6, "MS2": 8.2},
         "Betano": {"MS1": 1.42, "MSX": 4.4, "MS2": 7.9}}
    assert model.on_eleme_puani(b, AYAR, guvenilir_lig=False) is None  # Pinnacle yok: güvenilmez lig elenir

def test_metin_kuponda_her_macin_adi_var():
    ms = [("Bulgaria", "Estonia", "Under 3.5 goals", 1.20, 0.79), ("Czechia", "England", "Over 1.5 goals", 1.22, 0.78),
          ("Spain", "Croatia", "1st-half goal", 1.25, 0.76)]
    secimler = [_secim(i, o, p, "UST15", ev=e, dep=d, kisa=k) for i, (e, d, k, o, p) in enumerate(ms, 1)]
    flood = tweets.gun_floodu(_gun("2026-09-29", secimler, kuponlar=[[0, 1, 2]]), kayit.ozet([], 10000))
    assert all(f"{e} v {d}" in flood[0] for e, d, *_ in ms)  # her oyunda maç adı olmalı
    assert "💰 Bank" in flood[0] and all(tweets.uzunluk(t) <= 280 for t in flood)


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
    ms = [("Georgia", "Ukraine", "Under 3.5 goals"), ("Leganes", "Castellón", "Double chance X2"),
          ("Northern Ireland", "Hungary", "1st half Under 1.5 goals")]
    secimler = [_secim(i, 1.27, 0.74, "IYA15", ev=e, dep=d, kisa=k, yorum=yorum, etiket="1st half Under 1.5 goals")
                for i, (e, d, k) in enumerate(ms, 1)]
    flood = tweets.gun_floodu(_gun("2026-09-28", secimler, kuponlar=[[0, 1, 2]]), kayit.ozet([], 10000))
    assert "• Northern Ireland v Hungary: 1st half Under 1.5 goals" in flood[0]
    assert not any("…" in t for t in flood) and all(tweets.uzunluk(t) <= 280 for t in flood)


def test_oran_takipcinin_bulabilecegi_pazardan_olmali():
    assert model.oran_yeterli({"Bet365": 1.3, "Unibet": 1.28, "Betano": 1.27}, AYAR)
    assert not model.oran_yeterli({"Bet365": 1.3, "Unibet": 1.28}, AYAR)  # çok az site
    assert not model.oran_yeterli({"Unibet": 1.3, "Betano": 1.28, "Betsson": 1.27}, AYAR)  # zorunlu site yok


def test_keskin_bahisci_yoksa_sinir_sikilasir():
    assert model.aday_turu(0.74, 0.01, AYAR) == "guvenli"
    assert model.aday_turu(0.74, 0.01, AYAR, AYAR.keskinsiz_ek_marj) is None
    assert model.aday_turu(0.74, 0.04, AYAR, AYAR.keskinsiz_ek_marj) == "guvenli"


def test_kupon_gorseli_png():
    from bot import gorsel
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7, "UST25", kisa="Over 2.5 goals",
                                                        ev="Borussia Mönchengladbach", dep="Wolverhampton Wanderers")],
             kuponlar=[[0, 1]])
    png = gorsel.kupon_gorseli(g, kayit.kuponlar(g)[0], 10123.45, 1, 1)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) < 5_000_000


def test_yayinla_her_kupon_icin_gorsel_ekler(capsys):
    from bot.__main__ import yayinla
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7), _secim(3, 2.0, 0.52)], tweet_id=None,
             kuponlar=[[0, 1], [2]])
    assert yayinla(AYAR, g, tweets.KonsolClient(), [g], datetime(2026, 10, 3, 8, tzinfo=timezone.utc))
    cikti = capsys.readouterr().out
    ana = cikti.split("TWEET #1")[1].split("TWEET #2")[0]
    assert ana.count("gorsel-") == 2 and "TODAY'S 2 COUPONS | 3 Oct" in ana and "in the thread 🧵" in ana
    assert len(g["analiz_tweet_idleri"]) == 3 and g["gorselli"]


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
    assert "WEEKLY RECAP | 21–27 Sep" in metin and "✅ Picks: 5 won · ❌ 1 lost (83%)" in metin
    assert "Coupons: 2 of 3 won" in metin and tweets.uzunluk(metin) <= 280 and "@" not in metin


def test_gorsel_yukleme_tekrar_dener():
    from bot.__main__ import _gorsel_yukle
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], kuponlar=[[0], [1]])
    hatalar = [RuntimeError("503"), RuntimeError("timeout")]

    class X:
        def medya_yukle(self, png):
            if hatalar:
                raise hatalar.pop(0)
            return "m"

    bekleme = []
    assert _gorsel_yukle(X(), g, 10000, bekleme.append) == ["m", "m"] and len(bekleme) == 2 and "gorsel_eksik" not in g
    hatalar.extend(RuntimeError("x") for _ in range(9))
    assert _gorsel_yukle(X(), g, 10000, bekleme.append) is None and g["gorsel_eksik"]


def test_bet_builder_kaybeden_ayak_varsa_kaybeder():
    """Korner verisi yok ama gol ayağı kaybetti: oyun iptal değil, kayıp sayılmalı."""
    bb = _secim(1, 3.0, 0.3, "BB", bet_builder=True,
                bacaklar=[{"pazar": "UST25", "durum": "bekliyor"}, {"pazar": "KORU95", "durum": "bekliyor"}])
    g = _gun("2026-10-03", [bb])
    kayit.sonuclandir([g], {1: {"durum": "bitti", "skor": (0, 0), "korner": None}}, SIMDI)
    assert bb["durum"] == "kaybetti"


def test_sonuc_floodu_x_hatasinda_sonra_tamamlanir(monkeypatch):
    from bot.__main__ import sonuc
    uzun = dict(ev="Borussia Mönchengladbach", dep="Wolverhampton Wanderers", kisa="1st half Under 1.5 goals")
    g = _gun("2026-10-03", [_secim(i, 1.3, 0.8, **uzun) for i in (1, 2, 3)], kuponlar=[[0, 1, 2]])
    monkeypatch.setattr(football, "sonuclari_al",
                        lambda api, ids, korner: {i: {"durum": "bitti", "skor": (2, 0)} for i in ids})

    class X:
        def __init__(self, hata_sirasi=None):
            self.atilan, self.hata_sirasi = [], hata_sirasi

        def gonder(self, metin, yanit=None, medya=None, alinti=None):
            if len(self.atilan) == self.hata_sirasi:
                raise RuntimeError("X 503")
            self.atilan.append((metin, yanit))
            return f"s{len(self.atilan)}"

    with pytest.raises(RuntimeError):
        sonuc(AYAR, object(), X(hata_sirasi=1), [g], SIMDI)  # uzun: iki tweet; ikincisi başarısız
    assert g["sonuc"] == "tamam" and not g.get("sonuc_tweet_id") and g["sonuc_tweet_idleri"] == ["s1"]
    x2 = X()
    sonuc(AYAR, object(), x2, [g], SIMDI)  # yalnızca eksik ikinci tweet, ilkinin altına
    assert len(x2.atilan) == 1 and x2.atilan[0][1] == "s1" and g["sonuc_tweet_id"] == "s1"
    sonuc(AYAR, object(), X(), [g], SIMDI)
    assert len(g["sonuc_tweet_idleri"]) == 2


def test_yarim_flood_tamamlanir():
    from bot.__main__ import yayinla
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id="ana", kuponlar=[[0, 1]])
    g["analiz_tweet_idleri"] = ["k1"]
    x = tweets.KonsolClient()
    simdi = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
    assert yayinla(AYAR, g, x, [g], simdi) and len(g["analiz_tweet_idleri"]) == 2  # 2 analiz
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
    g = _gun("2026-10-03", [bb, _secim(2, 1.4, 0.7)], kuponlar=[[0, 1]])
    assert "odds ≈2.80" in tweets.gun_tweeti(g)


def test_x_okuma_hatasi_kuponu_engellemez(monkeypatch, tmp_path):
    import bot.__main__ as ana
    monkeypatch.setattr(config, "DATA_FILE", tmp_path / "spel.json")
    monkeypatch.setattr(config, "PANEL_FILE", tmp_path / "index.html")
    monkeypatch.setattr(ana, "HATALAR", [])
    cagrilar = []
    monkeypatch.setattr(ana, "sonuc", lambda *a: None)
    monkeypatch.setattr(ana, "haftalik", lambda *a, **k: False)
    monkeypatch.setattr(ana, "zaten_paylasildi", lambda x, t: (_ for _ in ()).throw(RuntimeError("403")))
    monkeypatch.setattr(ana, "tahmin", lambda *a: cagrilar.append("tahmin"))
    monkeypatch.setattr(ana, "_api", lambda ayar: None)
    monkeypatch.setattr(ana, "_x_client", lambda: None)
    monkeypatch.setattr(ana, "_secici", lambda: None)
    assert ana.main(["otomatik"]) == 0 and cagrilar == ["tahmin"]


def test_yenile_bugunu_silip_yeniden_secer(monkeypatch):
    import bot.__main__ as ana
    eski = _gun("2026-10-03", [_secim(1, 1.25, 0.76)], tweet_id="t1", kuponlar=[[0]])
    eski["analiz_tweet_idleri"] = ["a1"]
    gunler = [eski]
    silinen = []
    x = SimpleNamespace(sil=silinen.append)
    yeni = _gun("2026-10-03", [_secim(2, 1.9, 0.56)], tweet_id=None, kuponlar=[[0]])
    monkeypatch.setattr(ana, "tahmin", lambda ayar, api, sec, g, bugun, simdi: g.append(yeni) or yeni)
    hatali = []
    monkeypatch.setattr(ana, "yayinla", lambda *a: True)
    # önce: seçim başarısızsa (kayıt yok) hiçbir şey silinmez
    orijinal = ana.tahmin
    monkeypatch.setattr(ana, "tahmin", lambda *a: None)
    assert not ana.yenile(AYAR, None, None, x, gunler, "2026-10-03", datetime(2026, 10, 3, 8, tzinfo=timezone.utc))
    assert silinen == [] and gunler == [eski]
    monkeypatch.setattr(ana, "tahmin", orijinal)
    monkeypatch.setattr(ana, "yayinla", lambda *a: True)
    monkeypatch.setattr(ana.onay, "onay_iste", lambda *a: None)  # testte gerçek onay dosyası yazılmasın
    assert ana.yenile(AYAR, None, None, x, gunler, "2026-10-03", datetime(2026, 10, 3, 8, tzinfo=timezone.utc))
    assert silinen == ["a1", "t1"] and gunler == [yeni]
    # maç başladıysa hiçbir şey silinmez
    assert not ana.yenile(AYAR, None, None, x, gunler, "2026-10-03", datetime(2026, 10, 3, 14, tzinfo=timezone.utc))
    assert silinen == ["a1", "t1"]


def test_metin_kuponda_sorumluluk_satiri_hep_kalir():
    uzun = dict(ev="Borussia Mönchengladbach", dep="Wolverhampton Wanderers",
                kisa="1st half Under 1.5 goals + Both teams to score: No + Over 8.5 corners")
    secimler = [_secim(i, 1.9, 0.55, bet_builder=True, **uzun) for i in range(1, 4)]
    g = _gun("2026-10-03", secimler, kuponlar=[[0], [1], [2]])
    metin = tweets.gun_tweeti(g, kayit.ozet([], 10000))
    assert metin.endswith(tweets.ANSVAR) and tweets.uzunluk(metin) <= 280


def test_liste_disi_hazirlik_genc_kadin_maclari_alinmaz():
    def f(fid, lig_id, lig, ev, dep):
        return {"fixture": {"id": fid, "date": "2026-10-03T18:00:00+02:00", "status": {"short": "NS"}},
                "league": {"id": lig_id, "name": lig, "country": "X"}, "teams": {"home": {"name": ev}, "away": {"name": dep}}}
    api = SimpleNamespace(get=lambda *a, **k: [
        f(1, 999, "Club Friendlies", "A", "B"), f(2, 998, "Premier League U21", "C U21", "D U21"),
        f(3, 997, "Damallsvenskan Women", "E", "F"), f(4, 996, "Czech 3. liga", "G", "H"),
        f(5, 39, "Premier League", "Arsenal", "Everton")])
    maclar = football.gunun_maclari(api, "2026-10-03", [39], "Europe/Stockholm", 60, 100,
                                   datetime(2026, 10, 3, 8, tzinfo=timezone.utc), tum_ligler=True)
    assert [m["fixture_id"] for m in maclar] == [5, 4]  # izinli lig önce; hazırlık/genç/kadın maçları elenir


class SahteGitHub:
    def __init__(self, issues, yorumlar, yetkililer=("sahip",)):
        self.issues, self._yorumlar, self.yetkililer, self.kapatilan = issues, yorumlar, yetkililer, []

    def istekler(self):
        kapali = [k[0] for k in self.kapatilan]
        return [{**i, "state": "closed" if i["number"] in kapali else i.get("state", "open")} for i in self.issues]

    def yorumlar(self, no):
        return self._yorumlar.get(no, [])

    def yetkili(self, kullanici):
        return kullanici in self.yetkililer

    def kapat(self, no, mesaj):
        self.kapatilan.append((no, mesaj))

    def yorum(self, no, mesaj):
        self.yorumlanan = getattr(self, "yorumlanan", []) + [(no, mesaj)]


def _onayli_gun(son):
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id=None, kuponlar=[[0, 1]])
    g["onay"] = {"durum": "bekliyor", "son": son}
    return g


def test_onay_karar_kelimeleri():
    from bot import onay
    assert onay.karar("OK!") == "ok" and onay.karar("iptal edelim") == "iptal" and onay.karar("belki") is None


def test_onay_iptal_ok_ve_sure_dolumu(monkeypatch, tmp_path):
    from bot import onay
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    simdi = datetime(2026, 10, 3, 9, tzinfo=timezone.utc)
    son = "2026-10-03T10:30:00+00:00"
    yayinlanan = []

    def yayinla(ayar, gun, x, gunler, simdi, **k):
        gun["tweet_id"] = "T"
        yayinlanan.append(gun["id"])
        return True

    issue = [{"number": 7, "title": "Onay: 2026-10-03 kuponu"}]
    # yetkisiz birinin "ok"u sayılmaz, süre de dolmadı: bir şey olmaz
    g = _onayli_gun(son)
    gh = SahteGitHub(issue, {7: [{"body": "ok", "user": {"login": "yabanci"}}]})
    onay.kontrol(AYAR, gh, None, [g], simdi, yayinla)
    assert not yayinlanan and not gh.kapatilan
    # sahibin "iptal"i: paylaşım durur (hata var); süre dolsa bile otomatik paylaşılmaz
    gh = SahteGitHub(issue, {7: [{"body": "iptal", "user": {"login": "sahip"}}]})
    onay.kontrol(AYAR, gh, None, [g], simdi, yayinla)
    assert not yayinlanan and g["onay"]["durum"] == "durduruldu" and gh.yorumlanan and not gh.kapatilan
    onay.kontrol(AYAR, gh, None, [g], datetime(2026, 10, 3, 11, tzinfo=timezone.utc), yayinla)
    assert not yayinlanan and g["onay"]["durum"] == "durduruldu"
    # sonra "ok" gelirse bu haliyle paylaşılır
    gh._yorumlar[7].append({"body": "ok", "user": {"login": "sahip"}})
    onay.kontrol(AYAR, gh, None, [g], datetime(2026, 10, 3, 11, tzinfo=timezone.utc), yayinla)
    assert yayinlanan == ["2026-10-03"]
    yayinlanan.clear()
    # düzeltme maçtan 1 saat öncesine kadar gelmezse gün pas
    g = _onayli_gun(son)
    gh = SahteGitHub(issue, {7: [{"body": "iptal", "user": {"login": "sahip"}}]})
    onay.kontrol(AYAR, gh, None, [g], datetime(2026, 10, 3, 12, 5, tzinfo=timezone.utc), yayinla)
    assert not yayinlanan and g["sonuc"] == "pas" and g["onay"]["durum"] == "iptal" and gh.kapatilan
    # sahibin "ok"u: hemen paylaşılır
    g = _onayli_gun(son)
    gh = SahteGitHub(issue, {7: [{"body": "ok", "user": {"login": "sahip"}}]})
    onay.kontrol(AYAR, gh, None, [g], simdi, yayinla)
    assert yayinlanan == ["2026-10-03"] and g["onay"]["durum"] == "onaylandi"
    # cevap yok, süre doldu: otomatik paylaşılır
    g = _onayli_gun(son)
    gh = SahteGitHub(issue, {})
    onay.kontrol(AYAR, gh, None, [g], datetime(2026, 10, 3, 10, 31, tzinfo=timezone.utc), yayinla)
    assert len(yayinlanan) == 2 and g["onay"]["durum"] == "otomatik"


def test_onay_testi_hicbir_sey_paylasmaz(monkeypatch, tmp_path):
    from bot import onay
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    gh = SahteGitHub([{"number": 3, "title": "TEST – Onay: 2026-09-28 kuponu"}],
                     {3: [{"body": "iptal", "user": {"login": "sahip"}}]})
    onay.kontrol(AYAR, gh, None, [], SIMDI, lambda *a: pytest.fail("test paylaşım yapmamalı"))
    assert gh.kapatilan and "Hiçbir şey paylaşılmadı" in gh.kapatilan[0][1]


def test_otomatik_onay_istegi_acar(monkeypatch, tmp_path):
    from bot import onay
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    monkeypatch.setattr(onay, "ISTEK_DOSYASI", tmp_path / "istek.md")
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id=None, kuponlar=[[0, 1]])
    simdi = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
    onay.onay_iste(g, [g], AYAR, simdi)
    metin = (tmp_path / "istek.md").read_text()
    assert metin.startswith("Onay: 2026-10-03 kuponu\n") and "`ok`" in metin and "TODAY'S COUPON" in metin
    assert "raw.githubusercontent.com" in metin and (tmp_path / "2026-10-03-1-v1.png").exists()
    # son: en fazla 90 dk sonra, en geç ilk maçtan (13:00 UTC) 2 saat önce
    assert g["onay"]["son"] == "2026-10-03T09:30:00+00:00"


def test_onayli_paylasim_onizlemenin_aynisi(monkeypatch, tmp_path):
    """Önizleme ile paylaşım arasında kasa değişse bile gönderilen tweetler ve görsel önizlemedekiyle aynı olmalı."""
    from bot import onay, gorsel
    from bot.__main__ import yayinla
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    monkeypatch.setattr(onay, "ISTEK_DOSYASI", tmp_path / "istek.md")
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id=None, kuponlar=[[0, 1]])
    simdi = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
    onay.onay_iste(g, [g], AYAR, simdi)
    onizleme_png = (tmp_path / "2026-10-03-1-v1.png").read_bytes()
    beklenen = list(g["onay"]["metinler"])
    # arada başka bir gün sonuçlandı, kasa değişti
    eski = _gun("2026-10-02", [_secim(9, 2.0, 0.5)], kuponlar=[[0]])
    eski["secimler"][0].update(durum="kazandi", skor="1-0")
    eski["sonuc"] = "tamam"
    atilan, pngler = [], []

    class X:
        def medya_yukle(self, png):
            pngler.append(png)
            return "m"

        def gonder(self, metin, yanit=None, medya=None, alinti=None):
            atilan.append(metin)
            return f"t{len(atilan)}"

    assert yayinla(AYAR, g, X(), [eski, g], simdi + timedelta(minutes=30))
    assert atilan == beklenen and pngler == [onizleme_png]


def test_onay_hata_ve_kacirma_durumlari(monkeypatch, tmp_path):
    from bot import onay
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    assert onay.karar("ok ama iptal") == "iptal" and onay.karar("Ok, paylaş") == "ok"
    # olumsuzluk ya da "ok" ile başlamayan mesaj onay sayılmaz (yanlışlıkla paylaşmaktansa beklemek)
    assert onay.karar("not ok") is None and onay.karar("ok değil") is None and onay.karar("No problem, ok") is None
    issue = [{"number": 7, "title": "Onay: 2026-10-03 kuponu"}]
    ok = {7: [{"body": "ok", "user": {"login": "biri"}, "author_association": "MEMBER"}]}
    simdi = datetime(2026, 10, 3, 9, tzinfo=timezone.utc)
    # X hatası: durum "bekliyor" kalır, sonraki kontrol tekrar dener
    g = _onayli_gun("2026-10-03T10:30:00+00:00")
    def hatali(*a, **k):
        raise RuntimeError("X 503")
    with pytest.raises(RuntimeError):
        onay.kontrol(AYAR, SahteGitHub(issue, ok), None, [g], simdi, hatali)
    assert g["onay"]["durum"] == "bekliyor"
    # ana tweet atıldı ama flood yarım kaldı: sonraki kontrol tamamlar ve kapatır
    g["tweet_id"] = "T"
    tamamlanan = []
    gh = SahteGitHub(issue, ok)
    onay.kontrol(AYAR, gh, None, [g], simdi, lambda *a, **k: tamamlanan.append(1) or True)
    assert tamamlanan and g["onay"]["durum"] == "onaylandi" and gh.kapatilan
    # maç başlamış, paylaşılamıyor: gün pas, hata bildirilir
    g = _onayli_gun("2026-10-03T10:30:00+00:00")
    with pytest.raises(RuntimeError):
        onay.kontrol(AYAR, SahteGitHub(issue, ok), None, [g], simdi, lambda *a, **k: False)
    assert g["onay"]["durum"] == "kacirildi" and g["sonuc"] == "pas"


def test_onayli_kupon_gorselsiz_paylasilmaz_ama_son_saatte_metinle_gider(monkeypatch, tmp_path):
    from bot import onay
    import bot.__main__ as ana
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    monkeypatch.setattr(ana, "_gorsel_yukle", lambda x, gun, kasa: None)
    issue = [{"number": 7, "title": "Onay: 2026-10-03 kuponu"}]
    ok = {7: [{"body": "ok", "user": {"login": "biri"}, "author_association": "OWNER"}]}
    atilan = []
    x = SimpleNamespace(gonder=lambda metin, yanit=None, medya=None, alinti=None: atilan.append(metin) or f"t{len(atilan)}")
    g = _onayli_gun("2026-10-03T10:30:00+00:00")  # ilk maç 13:00 UTC
    gh = SahteGitHub(issue, ok)
    onay.kontrol(AYAR, gh, x, [g], datetime(2026, 10, 3, 9, tzinfo=timezone.utc), ana.yayinla)
    assert not atilan and g["onay"]["durum"] == "bekliyor" and not gh.kapatilan
    onay.kontrol(AYAR, gh, x, [g], datetime(2026, 10, 3, 12, 10, tzinfo=timezone.utc), ana.yayinla)
    assert atilan and atilan[0].startswith("⚽ TODAY'S COUPON") and g["onay"]["durum"] == "onaylandi"


def test_elle_kapatilan_istek_iptal_sayilmaz_sure_dolunca_paylasilir(monkeypatch, tmp_path):
    from bot import onay
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    g = _onayli_gun("2026-10-03T10:30:00+00:00")
    gh = SahteGitHub([{"number": 9, "title": "Onay: 2026-10-03 kuponu", "state": "closed"}], {})
    yayinlanan = []

    def yayinla(ayar, gun, x, gunler, simdi, **k):
        gun["tweet_id"] = "T"
        yayinlanan.append(1)
        return True

    onay.kontrol(AYAR, gh, None, [g], datetime(2026, 10, 3, 9, tzinfo=timezone.utc), yayinla)
    assert not yayinlanan and g["onay"]["durum"] == "bekliyor"
    onay.kontrol(AYAR, gh, None, [g], datetime(2026, 10, 3, 10, 31, tzinfo=timezone.utc), yayinla)
    assert yayinlanan and g["onay"]["durum"] == "otomatik"


def test_duzeltme_sonrasi_yeni_onizleme_gecerli_eskisi_kapanir(monkeypatch, tmp_path):
    from bot import onay
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    monkeypatch.setattr(onay, "ISTEK_DOSYASI", tmp_path / "istek.md")
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id=None, kuponlar=[[0, 1]])
    simdi = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
    onay.onay_iste(g, [g], AYAR, simdi)
    g["onay"]["durum"] = "durduruldu"
    onay.onay_iste(g, [g], AYAR, simdi + timedelta(minutes=20))  # düzeltildi, yeni önizleme
    assert g["onay"]["durum"] == "bekliyor" and g["onay"]["surum"] == 2 and (tmp_path / "2026-10-03-1-v2.png").exists()
    istekler = [{"number": 7, "title": "Onay: 2026-10-03 kuponu"}, {"number": 8, "title": "Onay: 2026-10-03 kuponu"}]
    gh = SahteGitHub(istekler, {7: [{"body": "iptal", "user": {"login": "sahip"}}]})
    onay.kontrol(AYAR, gh, None, [g], simdi + timedelta(minutes=25), lambda *a, **k: pytest.fail("erken paylaşım"))
    assert gh.kapatilan == [(7, "Yerine yeni önizleme açıldı.")] and g["onay"]["durum"] == "bekliyor"


def test_yanit_onerileri_suzulur_ve_onizlemede_gorunur(monkeypatch, tmp_path):
    from bot import onay
    maclar = {1: {"ev": "Arsenal", "dep": "Everton"}, 2: {"ev": "Hammarby", "dep": "AIK"}}
    oneriler = [
        {"fixture_id": 1, "metin": "Arsenal have scored in 11 straight home games, better than anyone. We make it about 80%."},
        {"fixture_id": 2, "metin": "Great bet here, follow us!"},        # bahis dili / kendini tanıtma: atılır
        {"fixture_id": 99, "metin": "Unknown match."},                     # veride yok: atılır
        {"fixture_id": 2, "metin": "Check Bet365 for this one. AIK lost 4 of 5 away."},  # bahisçi cümlesi silinir
    ]
    temiz = editor.yanit_onerilerini_hazirla(oneriler, maclar, ["Bet365"])
    assert [o["metin"] for o in temiz] == [oneriler[0]["metin"], "AIK lost 4 of 5 away."]
    assert temiz[0]["arama"] == "https://x.com/search?q=Arsenal%20Everton&f=live"
    monkeypatch.setattr(onay, "ONIZLEME_KLASORU", tmp_path)
    monkeypatch.setattr(onay, "ISTEK_DOSYASI", tmp_path / "istek.md")
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7)], tweet_id=None, kuponlar=[[0, 1]])
    g["yanit_onerileri"] = temiz
    onay.onay_iste(g, [g], AYAR, datetime(2026, 10, 3, 8, tzinfo=timezone.utc))
    metin = (tmp_path / "istek.md").read_text()
    assert "Elle yazabileceğin yanıtlar" in metin and "AIK lost 4 of 5 away." in metin and "@kalkylerat" in metin


def test_kasa_seyri_ve_grafik():
    from bot import gorsel
    g1 = _gun("2026-09-28", [_secim(1, 2.0, 0.5)], kuponlar=[[0]])
    g1["secimler"][0].update(durum="kazandi", skor="1-0")
    g1["sonuc"] = "tamam"
    g2 = _gun("2026-09-29", [_secim(2, 1.5, 0.7)], kuponlar=[[0]])
    g2["secimler"][0].update(durum="kaybetti", skor="0-1")
    g2["sonuc"] = "tamam"
    taslak = _gun("2026-09-30", [_secim(3, 1.5, 0.7)], tweet_id=None, kuponlar=[[0]])
    seyir = kayit.kasa_seyri([g2, g1, taslak], 10000)
    assert seyir == [("2026-09-27", 10000), ("2026-09-28", 10100.0), ("2026-09-29", 10000.0)]
    assert gorsel.kasa_grafigi(seyir, 10000, "€")[:4] == b"\x89PNG"


def test_sonuc_yalnizca_bitmis_olmasi_gereken_yayinlanmis_maclar_icin_sorulur():
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8), _secim(2, 1.4, 0.7, baslama="2026-10-03T20:45:00+02:00")],
             kuponlar=[[0, 1]])
    taslak = _gun("2026-10-03", [_secim(3, 1.5, 0.8)], tweet_id=None, kuponlar=[[0]])
    # 15:00 CEST başlayan maç 16:50'de bitmiş sayılır; 20:45 maçı henüz sorulmaz, taslak hiç sorulmaz
    simdi = datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc)  # 17:00 CEST
    assert kayit.bekleyen_fixturelar([g, taslak], simdi) == [1]
    assert kayit.bekleyen_fixturelar([g, taslak], datetime(2026, 10, 3, 14, 30, tzinfo=timezone.utc)) == []


def test_sonuc_sorusu_kazanca_ve_kayba_gore():
    kazanan = _gun("2026-10-03", [_secim(1, 1.5, 0.8)], kuponlar=[[0]])
    kaybeden = _gun("2026-10-03", [_secim(1, 1.5, 0.8)], kuponlar=[[0]])
    kayit.sonuclandir([kazanan], {1: {"durum": "bitti", "skor": (1, 0)}}, SIMDI)
    kayit.sonuclandir([kaybeden], {1: {"durum": "bitti", "skor": (0, 1)}}, SIMDI)
    k = "\n".join(tweets.sonuc_tweetleri(kazanan, kayit.ozet([kazanan], 10000)))
    y = "\n".join(tweets.sonuc_tweetleri(kaybeden, kayit.ozet([kaybeden], 10000)))
    assert any(s in k for s in tweets.SONUC_SORULARI["tuttu"])
    assert any(s in y for s in tweets.SONUC_SORULARI["yatti"])


def test_takilan_mac_saatte_bir_sorulur():
    bas = datetime(2026, 10, 3, 13, 0, tzinfo=timezone.utc)
    assert not kayit._sorulmali(bas, bas + timedelta(minutes=100))
    assert kayit._sorulmali(bas, bas + timedelta(minutes=115))
    # 3 saatten sonra: hiç sorulmadıysa hemen, sonra saatte bir (saatin dakikasından bağımsız)
    assert kayit._sorulmali(bas, bas + timedelta(hours=11, minutes=24))
    assert not kayit._sorulmali(bas, bas + timedelta(hours=4, minutes=22), bas + timedelta(hours=4))
    assert kayit._sorulmali(bas, bas + timedelta(hours=5, minutes=1), bas + timedelta(hours=4))


def test_sabah_penceresi_ve_sponsorlu_lig_adi():
    from bot.__main__ import _sabah_penceresi, _lig_adi
    assert _sabah_penceresi(datetime(2026, 9, 29, 11, 20, tzinfo=timezone.utc), AYAR)      # Salı 13:20 CEST
    assert not _sabah_penceresi(datetime(2026, 9, 29, 10, 50, tzinfo=timezone.utc), AYAR)  # planlı çalışma daha yeni
    assert not _sabah_penceresi(datetime(2026, 9, 29, 15, 0, tzinfo=timezone.utc), AYAR)
    assert _lig_adi({"lig": "Betsson Superettan", "ulke": "Sweden"}, AYAR) == "Sweden league"
    assert _lig_adi({"lig": "Premier League", "ulke": "England"}, AYAR) == "Premier League"


def test_hak_yetmezse_mac_mac_taramaya_gecilmez(monkeypatch):
    import bot.__main__ as ana
    monkeypatch.setattr(ana, "HATALAR", [])
    api = football.DemoApi(config.ROOT / "ornek" / "api_football.json")
    api.session = SimpleNamespace()
    monkeypatch.setattr(football, "kalan_istek", lambda api: 30)
    monkeypatch.setattr(ana, "_mac_mac_tara", lambda *a: pytest.fail("yedek hak harcanmamalı"))
    simdi = datetime.fromisoformat(api.data["simdi"])
    assert ana.tahmin(AYAR, api, editor.basit_sec, [], "2026-10-03", simdi) is None and ana.HATALAR


def test_sonuc_kuponu_alintilayan_ayri_paylasim(monkeypatch):
    from bot.__main__ import sonuc
    g = _gun("2026-10-03", [_secim(1, 1.5, 0.8)], kuponlar=[[0]])
    monkeypatch.setattr(football, "sonuclari_al", lambda api, ids, korner: {1: {"durum": "bitti", "skor": (2, 0)}})
    atilan = []
    x = SimpleNamespace(gonder=lambda metin, yanit=None, medya=None, alinti=None:
                        atilan.append((yanit, alinti, medya, metin)) or f"s{len(atilan)}",
                        medya_yukle=lambda png: "kart")
    sonuc(AYAR, object(), x, [g], SIMDI)
    yanit, alinti, medya, metin = atilan[0]
    assert (yanit, alinti, medya) == (None, "t1", ["kart"]) and len(atilan) == 1  # tek, görselli, alıntılı paylaşım
    assert "✅ Coupon won: +€50" in metin and "💰 Bank: €10,050" in metin and metin.endswith(tweets.ANSVAR)
    assert tweets.uzunluk(metin) <= 280 and g["sonuc_tweet_id"] == "s1"
