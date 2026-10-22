import re
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from bot import config, football, model, tweets

AYAR = config.yukle()
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
    assert model.aday_turu(0.72, -0.03, AYAR) == "guvenli"  # normal bahisçi marjı kadar altı kabul
    assert model.aday_turu(0.72, -0.05, AYAR) is None  # marjı yüksek oran alınmaz
    assert model.aday_turu(0.50, 0.05, AYAR) == "deger"
    assert model.aday_turu(0.40, 0.10, AYAR) is None


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


def test_oran_takipcinin_bulabilecegi_pazardan_olmali():
    assert model.oran_yeterli({"Bet365": 1.3, "Unibet": 1.28, "Betano": 1.27}, AYAR)
    assert not model.oran_yeterli({"Bet365": 1.3, "Unibet": 1.28}, AYAR)  # çok az site
    assert not model.oran_yeterli({"Unibet": 1.3, "Betano": 1.28, "Betsson": 1.27}, AYAR)  # zorunlu site yok


def test_keskin_bahisci_yoksa_sinir_sikilasir():
    assert model.aday_turu(0.74, 0.01, AYAR) == "guvenli"
    assert model.aday_turu(0.74, -0.02, AYAR) == "guvenli"
    assert model.aday_turu(0.74, -0.02, AYAR, AYAR.keskinsiz_ek_marj) is None
    assert model.aday_turu(0.74, 0.04, AYAR, AYAR.keskinsiz_ek_marj) == "guvenli"


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


def test_onay_karar_kelimeleri():
    from bot import onay
    assert onay.karar("OK!") == "ok" and onay.karar("iptal edelim") == "iptal" and onay.karar("belki") is None
    assert onay.karar("ok ama iptal") == "iptal" and onay.karar("Ok, paylaş") == "ok"  # iptal her zaman önce
    assert onay.karar("not ok") is None and onay.karar("ok değil") is None and onay.karar("No problem, ok") is None


def test_sabah_penceresi_ve_sponsorlu_lig_adi():
    from bot.__main__ import _sabah_penceresi, _lig_adi
    assert _sabah_penceresi(datetime(2026, 9, 29, 5, 40, tzinfo=timezone.utc), AYAR)       # Salı 07:40 CEST
    assert _sabah_penceresi(datetime(2026, 9, 29, 11, 0, tzinfo=timezone.utc), AYAR)       # geç kaldıysa gün içinde
    assert not _sabah_penceresi(datetime(2026, 9, 29, 5, 20, tzinfo=timezone.utc), AYAR)   # planlı çalışma daha yeni
    assert not _sabah_penceresi(datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc), AYAR)
    assert _lig_adi({"lig": "Betsson Superettan", "ulke": "Sweden"}, AYAR) == "Sweden league"
    assert _lig_adi({"lig": "Premier League", "ulke": "England"}, AYAR) == "Premier League"


def test_tek_calismalik_istisna(monkeypatch):
    monkeypatch.setenv("BOT_EK", "deger_min_deger=0.02 oran_min=5 zararli=1")
    ayar = config.yukle()
    assert ayar.deger_min_deger == 0.02 and ayar.oran_min == AYAR.oran_min  # yalnızca izinli alanlar
    assert set(config.istisnalar()) == {"deger_min_deger"}
    monkeypatch.delenv("BOT_EK")
    assert config.yukle().deger_min_deger == AYAR.deger_min_deger


# --- Yedek kaynak: The Odds API ---

class _OddsYanit:
    def __init__(self, veri, status=200, kalan="450", son="2"):
        self.veri, self.status_code = veri, status
        self.headers = {"x-requests-remaining": kalan, "x-requests-last": son}
        self.text = ""

    def json(self):
        return self.veri


class _OddsOturum:
    def __init__(self, yanitlar):
        self.yanitlar, self.cagrilar = yanitlar, []

    def get(self, url, params=None, timeout=None):
        self.cagrilar.append((url, dict(params or {})))
        for parca, veri in sorted(self.yanitlar.items(), key=lambda x: -len(x[0])):
            if url.endswith(parca):
                return _OddsYanit(veri, son="0" if parca in ("sports", "events") else "2")
        raise AssertionError(url)


def _odds_etkinlik(eid="abcdef1234567890", ev="Home FC", dep="Away FC"):
    def bm(key, h, d, a, o25, u25):
        return {"key": key, "title": key, "markets": [
            {"key": "h2h", "outcomes": [{"name": ev, "price": h}, {"name": "Draw", "price": d}, {"name": dep, "price": a}]},
            {"key": "totals", "outcomes": [{"name": "Over", "price": o25, "point": 2.5},
                                           {"name": "Under", "price": u25, "point": 2.5}]}]}
    return {"id": eid, "sport_key": "soccer_epl", "commence_time": "2026-09-29T19:00:00Z", "home_team": ev, "away_team": dep,
            "bookmakers": [bm("pinnacle", 1.40, 5.0, 8.5, 1.70, 2.25), bm("williamhill", 1.45, 4.6, 7.0, 1.66, 2.2),
                           bm("betsson", 1.47, 4.7, 7.2, 1.68, 2.2), bm("unibet_eu", 1.44, 4.8, 7.5, 1.69, 2.15)]}


def _ek_pazarlar(ev="Home FC", dep="Away FC"):
    return {"id": "abcdef1234567890", "home_team": ev, "away_team": dep, "bookmakers": [
        {"key": "pinnacle", "title": "Pinnacle", "markets": [
            {"key": "double_chance", "outcomes": [{"name": f"{ev}/Draw", "price": 1.08},
                                                  {"name": f"Draw/{dep}", "price": 3.2},
                                                  {"name": f"{ev}/{dep}", "price": 1.2}]},
            {"key": "alternate_totals", "outcomes": [{"name": "Over", "price": 1.25, "point": 1.5},
                                                     {"name": "Under", "price": 3.9, "point": 1.5},
                                                     {"name": "Over", "price": 3.0, "point": 4.5}]},
            {"key": "btts", "outcomes": [{"name": "Yes", "price": 2.1}, {"name": "No", "price": 1.7}]}]}]}


def test_odds_ek_pazarlar_ayristirma():
    from bot import oddsapi
    b = oddsapi.bahisci_oranlari(_ek_pazarlar())["Pinnacle"]
    assert b == {"CS1X": 1.08, "CSX2": 3.2, "CS12": 1.2, "UST15": 1.25, "ALT15": 3.9, "KGVAR": 2.1, "KGYOK": 1.7}
    assert oddsapi._cifte_sans("Draw or Away FC", "Home FC", "Away FC") == "CSX2"


def test_odds_bahisci_oranlari_ve_kimlik():
    from bot import oddsapi
    b = oddsapi.bahisci_oranlari(_odds_etkinlik())
    assert set(b) == {"Pinnacle", "William Hill", "Betsson", "Unibet"}
    assert b["Pinnacle"] == {"MS1": 1.40, "MSX": 5.0, "MS2": 8.5, "UST25": 1.70, "ALT25": 2.25}
    assert oddsapi.fixture_id("abcdef1234567890") == int("abcdef123456", 16) < 2 ** 53


def test_odds_tara_kredi_ve_yedek():
    from bot import oddsapi
    ayar = config.yukle()
    oturum = _OddsOturum({
        "sports": [{"key": "soccer_epl", "group": "Soccer", "title": "EPL", "active": True, "has_outrights": False},
                   {"key": "soccer_fifa_world_cup_winner", "group": "Soccer", "title": "WC", "active": True, "has_outrights": True}],
        "events": [{"id": "abcdef1234567890"}],
        "odds": [_odds_etkinlik()],
        "abcdef1234567890/odds": _ek_pazarlar(),
    })
    api = oddsapi.OddsApi("x", session=oturum, aralik=0)
    simdi = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    maclar, oranlar = oddsapi.tara(api, "2026-09-29", ayar, simdi)
    assert len(maclar) == 1 and maclar[0]["odds_spor"] == "soccer_epl" and maclar[0]["fixture_id"] in oranlar
    assert maclar[0]["lig_id"] in ayar.ligler
    odds = [p for u, p in oturum.cagrilar if u.endswith("/odds")][0]
    assert odds["regions"] == "eu" and odds["markets"] == "h2h,totals" and odds["commenceTimeFrom"] == "2026-09-29T12:30:00Z"
    assert api.harcanan == 4 and api.kalan == 450  # 2 lig oranı + 2 (sahte) ek pazar
    ek = [p for u, p in oturum.cagrilar if u.endswith("abcdef1234567890/odds")][0]
    assert ek["markets"] == "double_chance,alternate_totals,btts"
    assert oranlar[maclar[0]["fixture_id"]]["Pinnacle"]["CS1X"] == 1.08
    assert oranlar[maclar[0]["fixture_id"]]["Pinnacle"]["UST15"] == 1.25


def test_odds_kadinlardan_yalniz_sampiyonlar_ligi():
    from bot import oddsapi

    def s(key, title):
        return {"key": key, "group": "Soccer", "title": title, "active": True, "has_outrights": False}
    sporlar = [s("soccer_uefa_champs_league_women", "UEFA Champions League Women"),
               s("soccer_sweden_damallsvenskan", "Damallsvenskan Women"),
               s("soccer_england_wsl", "WSL Women"), s("soccer_epl", "EPL")]
    api = SimpleNamespace(get=lambda path, **k: sporlar)
    anahtarlar = [x["key"] for x in oddsapi.futbol_sporlari(api)]
    assert anahtarlar == ["soccer_epl", "soccer_uefa_champs_league_women"]  # izinli lig önce, kadın SL liste dışı
    assert "soccer_uefa_champs_league_women" not in oddsapi.IZINLI_SPORLAR  # Pinnacle şartıyla taranır


def test_odds_hata_mesajinda_anahtar_yok():
    from bot import oddsapi

    class Oturum:
        def get(self, url, params=None, timeout=None):
            return _OddsYanit({"message": "API key is not valid"}, status=401)
    api = oddsapi.OddsApi("GIZLI-ANAHTAR", session=Oturum(), aralik=0)
    with pytest.raises(oddsapi.OddsApiHatasi) as e:
        api.get("sports")
    assert "GIZLI" not in str(e.value) and "401" in str(e.value)


def test_odds_sonuclari():
    from bot import oddsapi
    oturum = _OddsOturum({"scores": [
        {"id": "abcdef1234567890", "completed": True, "home_team": "Home FC", "away_team": "Away FC",
         "scores": [{"name": "Home FC", "score": "2"}, {"name": "Away FC", "score": "0"}]},
        {"id": "1234567890abcdef", "completed": False, "home_team": "A", "away_team": "B", "scores": None}]})
    s = oddsapi.sonuclari_al(oddsapi.OddsApi("x", session=oturum, aralik=0), {"soccer_epl": ["abcdef1234567890", "1234567890abcdef"]})
    assert s[oddsapi.fixture_id("abcdef1234567890")] == {"durum": "bitti", "skor": (2, 0), "iy": None, "korner": None}
    assert s[oddsapi.fixture_id("1234567890abcdef")]["durum"] == "bekliyor"
    assert oturum.cagrilar[0][1]["daysFrom"] == 3


def test_api_football_kapaliyken_analiz_ve_sonuc_yedek_kaynaktan(monkeypatch, tmp_path):
    from bot import __main__ as ana, oddsapi
    ayar = config.yukle()
    monkeypatch.setenv("ODDS_API_KEY", "x")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(config, "DATA_FILE", tmp_path / "spel.json")
    monkeypatch.setattr(ana, "HATALAR", [])

    def kapali(*a, **k):
        raise football.ApiHatasi("Your account is suspended")
    monkeypatch.setattr(football, "gunun_maclari", kapali)
    monkeypatch.setattr(football, "sonuclari_al", kapali)
    oturum = _OddsOturum({
        "sports": [{"key": "soccer_epl", "group": "Soccer", "title": "EPL", "active": True, "has_outrights": False}],
        "events": [{"id": "abcdef1234567890"}], "odds": [_odds_etkinlik()], "abcdef1234567890/odds": _ek_pazarlar(),
        "scores": [{"id": "abcdef1234567890", "completed": True, "home_team": "Home FC", "away_team": "Away FC",
                    "scores": [{"name": "Home FC", "score": "3"}, {"name": "Away FC", "score": "1"}]}]})
    gercek = oddsapi.OddsApi
    monkeypatch.setattr(oddsapi, "OddsApi", lambda key, session=None: gercek(key, session=oturum, aralik=0))
    gunler = []
    simdi = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    gun = ana.analiz_gunu(ayar, gunler, "2026-09-29", simdi, api=SimpleNamespace())
    assert gun and gun["konsept"] == "analiz" and not ana.HATALAR
    tum = json.loads((tmp_path / "analiz" / "2026-09-29.json").read_text(encoding="utf-8"))
    assert tum and tum[0]["odds_id"] == "abcdef1234567890"  # maç sonu sonucu aynı kaynaktan sorulur
    sonuc = ana._mac_sonuclari(ayar, tum)
    assert sonuc[tum[0]["fixture_id"]]["skor"] == (3, 1)


def test_odds_429_tekrar_denenir():
    from bot import oddsapi
    yanitlar = [_OddsYanit({"message": "Requests are too frequent"}, status=429), _OddsYanit([{"key": "a"}])]

    class Oturum:
        def get(self, url, params=None, timeout=None):
            return yanitlar.pop(0)
    beklemeler = []
    api = oddsapi.OddsApi("x", session=Oturum(), aralik=0, uyku=beklemeler.append)
    assert api.get("sports") == [{"key": "a"}] and beklemeler == [2]


def _vitrin_gunu(**ek):
    from bot import etkilesim
    oran = lambda m1, x, m2: {"Pinnacle": {"MS1": m1, "MSX": x, "MS2": m2, "UST25": 1.9, "ALT25": 1.9}}
    maclar = [
        {"fixture_id": 1, "lig_id": -1, "lig": "X", "ev": "Small A", "dep": "Small B", "baslama": "2026-10-01T18:45:00+00:00"},
        {"fixture_id": 2, "lig_id": AYAR.ligler[0], "lig": "UNL", "ev": "Germany", "dep": "Serbia", "baslama": "2026-10-01T18:45:00+00:00"},
        {"fixture_id": 3, "lig_id": AYAR.ligler[0], "lig": "UNL", "ev": "Wales", "dep": "Norway", "baslama": "2026-10-01T18:45:00+00:00"},
    ]
    oranlar = {1: oran(2.0, 3.4, 3.8), 2: oran(1.22, 6.5, 13.0), 3: oran(5.0, 4.2, 1.6)}
    vit = etkilesim.vitrin(maclar, oranlar, AYAR, datetime(2026, 10, 1, 8, tzinfo=timezone.utc))
    return {"id": "2026-10-01", "tarih": "2026-10-01", "olusturma": "2026-10-01T10:55:00+00:00", "konsept": "analiz",
            "vitrin": vit, "etkilesim": {"bilgi": {"durum": "paylasildi", "zaman": "2026-10-01T09:00:00+00:00"}}, **ek}


def test_vitrin_izinli_ligler_once_anket_dengeli_maca():
    from bot import etkilesim
    gun = _vitrin_gunu()
    assert [v["fixture_id"] for v in gun["vitrin"]][-1] == 1  # liste dışı lig sonda
    assert etkilesim.anket_maci(gun["vitrin"])["ev"] == "Wales"  # Almanya %80 favori: oylamaya değmez
    for v in gun["vitrin"]:
        assert sum(v["p"].values()) == pytest.approx(1, abs=0.01)


def test_etkilesim_paylasimlari_sirayla_aralikli_ve_birer_kez():
    from bot import etkilesim
    gun = _vitrin_gunu()
    x = tweets.KonsolClient()
    t = lambda s, d: datetime(2026, 10, 1, s, d, tzinfo=timezone.utc)
    assert etkilesim.paylas(gun, AYAR, x, t(13, 0)) is None  # günün maçları maçtan 5 saat önce açılır
    assert etkilesim.paylas(gun, AYAR, x, t(13, 50)) == "maclar"
    assert etkilesim.paylas(gun, AYAR, x, t(14, 0)) is None  # 45 dk aralık
    assert etkilesim.paylas(gun, AYAR, x, t(14, 40)) is None  # anket maçtan 3 saat önce
    assert etkilesim.paylas(gun, AYAR, x, t(15, 50)) == "anket"
    assert etkilesim.paylas(gun, AYAR, x, t(16, 20)) is None  # 45 dk aralık
    assert etkilesim.paylas(gun, AYAR, x, t(18, 10)) == "bilgi_aksam"
    assert etkilesim.paylas(gun, AYAR, x, t(19, 30)) is None  # her tür bir kez
    assert x.sayac == 3
    assert all(e["durum"] == "paylasildi" for e in gun["etkilesim"].values())  # bilgi testte önceden atıldı


def test_etkilesim_metinleri_kurallara_uyar():
    from bot import etkilesim
    gun = _vitrin_gunu()
    metin, secenekler, dakika = etkilesim.anket({**gun, "_simdi": "2026-10-01T15:50:00+00:00"}, AYAR)
    assert secenekler == ["Wales", "Draw", "Norway"] and dakika == 175
    for m in (metin, etkilesim.maclar_tweeti(gun, AYAR)):
        assert tweets.uzunluk(m) <= 280 and "@" not in m and "http" not in m


def test_takim_golu_ve_ikinci_yari_pazarlari():
    p = model.model_olasiliklari(1.6, 1.0)
    for a, b in (("EVU05", "EVA05"), ("DPU15", "DPA15"), ("YYU05", "YYA05")):
        assert p[a] + p[b] == pytest.approx(1, abs=1e-4)
    assert p["EVU05"] > p["DPU05"]  # ev sahibi daha çok gol bekliyor
    assert football.pazar_kodu("Total - Home", "Over 1.5") == "EVU15"
    assert football.pazar_kodu("Total - Away", "Under 0.5") == "DPA05"
    assert football.pazar_kodu("Goals Over/Under - Second Half", "Over 0.5") == "YYU05"
    assert model.kazandi_mi("EVU15", 2, 0) and model.kazandi_mi("DPA05", 2, 0)
    assert model.kazandi_mi("YYU05", 2, 1, iy=(2, 0)) and not model.kazandi_mi("YYU05", 2, 0, iy=(2, 0))
    assert model.kazandi_mi("YYU05", 2, 1) is None  # ilk yarı skoru yoksa beklemede
    assert model.etiketler("EVU15", "Spain", "Croatia")[0] == "Spain Over 1.5 goals"
    assert model.piyasa_olasiliklari({"DPU05": 1.5, "DPA05": 2.5})["DPU05"] == pytest.approx(0.625)


def test_direktor_metni_kural_disiysa_sablon_kullanilir():
    from bot import direktor, etkilesim
    bahisciler = AYAR.oran_bahiscileri + [AYAR.keskin_bahisci]
    assert direktor.kurala_uygun("Who wins tonight? 👇", "maclar", bahisciler)
    for kotu in ("A lock tonight 👇", "Bet at Bet365 now", "Ask @someone", "x" * 300, "see https://a.b",
                 "RT if you agree", "#UCL #Football two tags"):
        assert not direktor.kurala_uygun(kotu, "maclar", bahisciler), kotu
    assert not direktor.kurala_uygun("Odds turn into chances.", "bilgi", bahisciler)  # sorumluluk satırı şart
    assert direktor.kurala_uygun(f"Odds turn into chances.\n\n{tweets.ANSVAR}", "bilgi", bahisciler)

    class Sahte:
        def __init__(self, metin):
            self.metin, self.cagri = metin, []
            self.messages = self

        def stream(self, **k):
            self.cagri.append(k["model"])
            metin = self.metin
            class S:
                def __enter__(s):
                    return s
                def __exit__(s, *a):
                    return False
                def get_final_message(s):
                    return SimpleNamespace(stop_reason="end_turn",
                                           content=[SimpleNamespace(type="text", text=json.dumps({"paylas": True, "metin": metin}))])
            return S()
    iyi = Sahte("Big night in Cardiff. Who are you backing? 👇")
    assert direktor.yazar(AYAR, iyi, yaz=lambda m: None)("maclar", {}, "SABLON") == iyi.metin
    assert iyi.cagri == [AYAR.direktor_model]
    assert direktor.yazar(AYAR, Sahte("Guaranteed win! 👇"), yaz=lambda m: None)("maclar", {}, "SABLON") == "SABLON"
    gun = _vitrin_gunu()
    x = tweets.KonsolClient()
    etkilesim.paylas(gun, AYAR, x, datetime(2026, 10, 1, 13, 50, tzinfo=timezone.utc),
                     yazar=direktor.yazar(AYAR, iyi, yaz=lambda m: None))
    assert gun["etkilesim"]["maclar"]["durum"] == "paylasildi"


def test_direktor_haftalik_strateji_ve_rapor(monkeypatch, tmp_path):
    from bot import direktor
    monkeypatch.setattr(direktor, "DOSYA", tmp_path / "direktor.json")
    yerel = datetime(2026, 10, 5, 10, 0)
    assert direktor.haftalik_gerekli(yerel)  # hiç strateji yok
    cikti = {"strateji": {"ton": "warm", "soru_ornekleri": ["Who wins?"], "kacinilacaklar": [], "odak": "polls"},
             "rapor": "Bu hafta anketler iyi gitti."}

    class Model:
        messages = None

        def __init__(self):
            self.messages = self

        def stream(self, **k):
            assert k["model"] == AYAR.direktor_strateji_model
            class S:
                def __enter__(s):
                    return s
                def __exit__(s, *a):
                    return False
                def get_final_message(s):
                    return SimpleNamespace(stop_reason="end_turn",
                                           content=[SimpleNamespace(type="text", text=json.dumps(cikti))])
            return S()
    acilan = []
    gh = SimpleNamespace(issue_ac=lambda b, g, e: acilan.append((b, g, e)) or 7)
    veri = direktor.haftalik(AYAR, [], [{"text": "x", "public_metrics": {"reply_count": 3}}], gh, yerel, Model(),
                             yaz=lambda m: None)
    assert veri["rapor_issue"] == 7 and acilan[0][2] == "rapor" and "2026-W41" in acilan[0][0]
    assert direktor.yukle()["strateji"]["odak"] == "polls"
    assert not direktor.haftalik_gerekli(yerel)  # bu hafta yapıldı
    assert direktor.haftalik_gerekli(datetime(2026, 10, 12, 9, 30))  # sonraki Pazartesi
    (tmp_path / "direktor.json").write_text(json.dumps({"son_deneme": "2026-10-05T10:00:00"}))
    assert not direktor.haftalik_gerekli(datetime(2026, 10, 5, 12, 0))  # başarısız deneme: 6 saat beklenir
    assert direktor.haftalik_gerekli(datetime(2026, 10, 5, 16, 30))


def test_denetim_dogrulayici_bahis_dili_link_ve_siteleri_yakalar():
    from bot import direktor
    b = AYAR.oran_bahiscileri + [AYAR.keskin_bahisci]
    for kotu in ("100% certain home win", "Dead cert", "sure win tonight", "Locked in 👇", "Smash the over",
                 "Stake big on the home win", "Over 2.5 is the bet tonight", "Bet 365 has it", "Betfair price",
                 "kalkylerat.se for more", "t.co/abc", "DM us", "Join our Telegram for VIP tips"):
        assert not direktor.kurala_uygun(kotu, "maclar", b), kotu
    for iyi in ("Denmark v Portugal tonight. Who are you backing? 👇", "Our model: 2.9 goals. Goals or a tight one?",
                "Germany 80% · draw 14% · Serbia 6%. Agree?", "Far from certain in Cardiff tonight.",
                "A smash-and-grab win for Spurs.Me? 👇", "St. Pauli v 1. FC Köln, 2.1 goals expected"):
        assert direktor.kurala_uygun(iyi, "maclar", b), iyi


def test_hashtag_yalniz_gercek_turnuvalar_ulkeye_gore():
    assert tweets.hashtag("UEFA Nations League") == "#NationsLeague"
    assert tweets.hashtag("UEFA Champions League Women") == "#UWCL"
    assert tweets.hashtag("Premier League", "England") == "#PremierLeague"
    assert tweets.hashtag("Premier League", "Kenya") is None and tweets.hashtag("Serie A", "Brazil") is None
    assert tweets.hashtag("La Liga - Spain") == "#LaLiga" and tweets.hashtag("EPL") == "#PremierLeague"
    assert tweets.hashtag("CONCACAF Nations League") is None
    from bot import direktor
    b = AYAR.oran_bahiscileri + [AYAR.keskin_bahisci]
    assert direktor.kurala_uygun("Big night ⚽ Who wins? 👇 #NationsLeague", "maclar", b)
    assert not direktor.kurala_uygun("Big night #football #bets", "maclar", b)
    assert not direktor.kurala_uygun("#UCL #NationsLeague #PremierLeague", "maclar", b)


def test_takim_ve_mac_etiketleri_yaygin_olanlar():
    """Taraftarların zaten kullandığı etiketler; uydurma kod etiketi (#DENPOR, #KAZMDA) yok."""
    assert tweets.mac_etiketi("Belgium", "Türkiye") == "#BizimÇocuklar"  # iki etiket varsa öncelikli olan
    assert tweets.mac_etiketi("Denmark", "Portugal") == "#VesteABandeira"
    assert tweets.mac_etiketi("France", "Italy") == "#LesBleus"
    assert tweets.mac_etiketi("Kazakhstan", "Moldova") is None
    assert tweets.mac_etiketi("Brentford", "Arsenal") == "#Arsenal"
    assert tweets.mac_etiketi("Tottenham", "Wolves") == "#COYS"
    assert tweets.mac_etiketi("Bastia", "Orleans") is None
    assert tweets.etiket_satiri([("UEFA Nations League", "")], [("Belgium", "Türkiye")]) == "#NationsLeague"  # kartta tek etiket
    assert tweets.etiket_satiri([("UEFA Nations League", "")], [("Kazakhstan", "Moldova")]) == "#NationsLeague"
    assert tweets.etiket_satiri([("Ligue 2", "France")], [("Bastia", "Orleans")]) == ""
    assert tweets.izinli_etiket("#BizimÇocuklar") and not tweets.izinli_etiket("#DENPOR")
    assert not tweets.izinli_etiket("#ABCDEF") and not tweets.izinli_etiket("#bets")
    from bot import direktor
    b = AYAR.oran_bahiscileri + [AYAR.keskin_bahisci]
    assert direktor.kurala_uygun("Big one ⚽ #NationsLeague", "maclar", b, {"#NationsLeague", "#BizimÇocuklar"})
    assert not direktor.kurala_uygun("Big one ⚽ #NationsLeague #BizimÇocuklar", "maclar", b,
                                     {"#NationsLeague", "#BizimÇocuklar"})  # otomatik postta en fazla bir etiket
    assert not direktor.kurala_uygun("Big one #Azzurri", "maclar", b, {"#NationsLeague", "#BizimÇocuklar"})  # şablonda yok


def test_bilgi_postu_gunluk_dogru_ve_sayi_uydurulamaz():
    import math
    from bot import bilgi, direktor, etkilesim
    # her konu kurallara uyar, 280'e sığar; hesaplanan sayılar matematiksel olarak doğru
    for k in bilgi.KONULAR:
        metin = f'💡 {k["baslik"]}\n\n{k["govde"]}\n\n{k["soru"]}\n\n{tweets.ANSVAR}'
        assert tweets.uzunluk(metin) <= 280, k["id"]
        assert direktor.kurala_uygun(metin, "bilgi", AYAR.oran_bahiscileri), k["id"]
    konu = {k["id"]: k["govde"] for k in bilgi.KONULAR}
    assert "34.3%" in konu["kombine"] and "32.8%" in konu["kombine"] and "83.3%" in konu["basabas"]
    assert "25.7%" in konu["yuzde1"] and "8.2%" in konu["kelly"] and "1-1 at just 12.6%" in konu["skor"]
    assert not any(re.search(r"\b(stake|bank|bet|pick|tipster|chase)", k["govde"] + k["soru"], re.I) for k in bilgi.KONULAR)
    assert abs(bilgi._en_az_bir_seri(5, 5, 0.4) - 0.4 ** 5) < 1e-12  # 5 bahiste 5'li seri = hepsi kayıp
    assert abs(bilgi._binom_en_fazla(10, 10, 0.3) - 1) < 1e-12 and abs(math.exp(-1.5) - 0.2231) < 1e-4
    # 20 konu her gün sırayla döner
    gunler_ = {bilgi.gunun_konusu(f"2026-10-{g:02d}")["id"] for g in range(1, 21)}
    assert len(gunler_) == len(bilgi.KONULAR) == 20
    # günlük plan: 09:00 UTC'den sonra, gün içinde bir kez (vitrin olmasa da)
    gun = {"id": "2026-10-02", "tarih": "2026-10-02"}
    x = tweets.KonsolClient()
    t = lambda s, d: datetime(2026, 10, 2, s, d, tzinfo=timezone.utc)
    assert etkilesim.paylas(gun, AYAR, x, t(8, 50)) is None
    assert etkilesim.paylas(gun, AYAR, x, t(11, 40)) == "bilgi" and x.sayac == 1
    assert etkilesim.paylas(gun, AYAR, x, t(14, 0)) is None  # günde bir kez
    # direktör olgularda olmayan sayı yazarsa şablon gider
    olg = etkilesim.olgular("bilgi", gun, AYAR)
    assert direktor.sayilar_dogru("Take 1.25: that's 80% implied. 18+ | Play responsibly",
                                  json.dumps(olg) + etkilesim.bilgi_tweeti(gun)) is (
        "1.25" in json.dumps(olg))
    assert not direktor.sayilar_dogru("Home sides win 46% of games", "2.00 means 50%")


def test_analiz_konsepti_kupon_hazirlamaz_ve_temizlik_partilerle_siler(monkeypatch, tmp_path):
    import bot.__main__ as ana
    from bot import temizlik
    monkeypatch.setattr(config, "DATA_FILE", tmp_path / "spel.json")
    monkeypatch.setattr(config, "PANEL_FILE", tmp_path / "index.html")
    monkeypatch.setattr(temizlik, "DOSYA", tmp_path / "temizlik.json")
    monkeypatch.setattr(ana, "HATALAR", [])
    cagrilar = []
    monkeypatch.setattr(ana, "_api", lambda ayar: None)
    monkeypatch.setattr(ana, "analiz_gunu", lambda *a: cagrilar.append("analiz"))
    ana.main(["otomatik"])
    assert cagrilar == ["analiz"]  # sabah çalışması günün analizini hazırlar

    class X:
        def __init__(self):
            self.kalan = [str(i) for i in range(100)]
            self.silinen = []

        def tum_tweet_idleri(self, adet=100):
            return self.kalan[:adet]

        def sil(self, tid):
            if len(self.silinen) == 50:
                raise RuntimeError("X API silme hatası 429: Too Many Requests")
            self.kalan.remove(tid)
            self.silinen.append(tid)
    x = X()
    simdi = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    assert temizlik.calistir(x, simdi) == 0  # aktif değil
    temizlik.baslat(simdi)
    assert temizlik.calistir(x, simdi) == temizlik.PARTI
    assert temizlik.calistir(x, simdi) == 50 - temizlik.PARTI  # 429: kalanı sonraki nabız
    x.silinen = []
    assert temizlik.calistir(x, simdi) == temizlik.PARTI
    while x.kalan:
        x.silinen = []
        temizlik.calistir(x, simdi)
    assert temizlik.calistir(x, simdi) == 0 and not temizlik.durum()["aktif"] and temizlik.durum()["silinen"] == 100


def test_analiz_gunu_kartlar_ve_mac_sonu_takibi(monkeypatch, tmp_path):
    import bot.__main__ as ana
    from bot import direktor, etkilesim, football, gorsel, panel
    monkeypatch.setattr(config, "DATA_FILE", tmp_path / "spel.json")
    pin = lambda m1, x, m2, u: {"Pinnacle": {"MS1": m1, "MSX": x, "MS2": m2, "UST25": u, "ALT25": 1 / (1 - 1 / u) + 0.05}}
    lig = AYAR.ligler[0]
    maclar = [
        {"fixture_id": 1, "lig_id": lig, "lig": "Premier League", "ev": "Arsenal", "dep": "Fulham", "baslama": "2026-10-03T14:00:00+00:00"},
        {"fixture_id": 2, "lig_id": lig, "lig": "Premier League", "ev": "Leeds", "dep": "Everton", "baslama": "2026-10-03T16:30:00+00:00"},
        {"fixture_id": 3, "lig_id": lig, "lig": "Premier League", "ev": "Spurs", "dep": "Wolves", "baslama": "2026-10-03T19:00:00+00:00"},
        {"fixture_id": 4, "lig_id": 9999, "lig": "Lower League", "ev": "Small A", "dep": "Small B", "baslama": "2026-10-03T13:00:00+00:00"},
        {"fixture_id": 5, "lig_id": 9999, "lig": "Lower League", "ev": "No Data", "dep": "Team", "baslama": "2026-10-03T13:00:00+00:00"},
    ]
    oranlar = {1: pin(1.45, 4.6, 7.0, 1.6), 2: pin(2.4, 3.3, 3.0, 2.0), 3: pin(1.9, 3.7, 4.0, 1.75)}
    ist = {"ev": {"oynanan_ic": 4, "oynanan_dis": 4, "atilan_ic_ort": 1.5, "yenilen_ic_ort": 1.0, "son5_atilan_ort": 1.4,
                  "son5_yenilen_ort": 1.1}, "dep": {"oynanan_ic": 4, "oynanan_dis": 4, "atilan_dis_ort": 1.0,
                  "yenilen_dis_ort": 1.4, "son5_atilan_ort": 1.0, "son5_yenilen_ort": 1.3}}
    monkeypatch.setattr(football, "gunun_maclari", lambda *a, **k: maclar)
    monkeypatch.setattr(football, "toplu_oranlar", lambda *a, **k: oranlar)
    monkeypatch.setattr(football, "istatistik_al", lambda api, fid: ist if fid == 4 else None)
    gunler = []
    simdi = datetime(2026, 10, 3, 8, 50, tzinfo=timezone.utc)
    gun = ana.analiz_gunu(AYAR, gunler, "2026-10-03", simdi, api=object())
    tum = json.loads((tmp_path / "analiz" / "2026-10-03.json").read_text())
    assert gun["analiz_sayisi"] == 4 and len(tum) == 4  # verisi olmayan maç analiz edilmez
    assert {a["fixture_id"]: a["guven"] for a in tum}[4] == "dusuk" and {a["fixture_id"]: a["guven"] for a in tum}[1] == "yuksek"
    assert [a["ev"] for a in gun["analizler"]] == ["Arsenal", "Leeds", "Spurs"]  # alt lig öne çıkmaz
    assert "tablo" in gun and {1, 2} <= {a["fixture_id"] for a in gun["tablo"]}  # kartlı büyük maç tabloda da var (B6)
    for a in tum:  # tek modelden: tutarlı olasılıklar
        p = a["p"]
        assert abs(p["MS1"] + p["MSX"] + p["MS2"] - 1) < 0.01 and abs(p["UST25"] + p["ALT25"] - 1) < 0.01
        assert p["CS1X"] >= p["MS1"] and a["skorlar"][0][1] >= a["skorlar"][1][1]
    assert ana.analiz_gunu(AYAR, gunler, "2026-10-03", simdi, api=object()) is None  # günde bir kez
    panel.olustur(gunler, tmp_path / "p.html", AYAR)  # panel analiz günüyle bozulmaz
    # gün içi paylaşımlar: kupon/radar/değer yok; analiz kartları görselli
    x = tweets.KonsolClient()
    turler = []
    for dk in range(0, 12 * 60, 15):
        t = simdi + timedelta(minutes=dk)
        r = etkilesim.paylas(gun, AYAR, x, t, yaz=lambda m: None)
        if r:
            turler.append(r)
    assert {"analiz_0", "analiz_1", "analiz_2", "bilgi"} <= set(turler)
    assert not {"radar", "deger", "istatistik", "skor", "pas"} & set(turler)
    metin = etkilesim.analiz_tweeti(gun["analizler"][0], AYAR)
    assert "🆚 Arsenal v Fulham" in metin and "Most likely score" in metin and "📈 Team stats" in metin
    assert tweets.uzunluk(metin) <= 280 and direktor.kurala_uygun(metin, "analiz", AYAR.oran_bahiscileri)
    assert gorsel.analiz_karti(gun["analizler"][0], "16:00", "tr")[:4] == b"\x89PNG"
    # maç sonu: skor ve üç çağrı, alıntıyla; bir kez
    sonuclar = {1: {"durum": "bitti", "skor": (2, 0)}, 2: {"durum": "bitti", "skor": (1, 1)}, 3: {"durum": "bekliyor"}}
    once = x.sayac
    n = etkilesim.analiz_takibi(gun, AYAR, x, datetime(2026, 10, 3, 19, 30, tzinfo=timezone.utc),
                                lambda m: {m[0]["fixture_id"]: sonuclar[m[0]["fixture_id"]]}, yaz=lambda m: None)
    assert n == 2 and x.sayac == once + 2
    takip = gun["etkilesim"]["analiz_0"]["takip"]
    assert takip["skor"] == "2-0" and takip["isabet"][0] is True and len(takip["isabet"]) == 3
    assert etkilesim.analiz_takibi(gun, AYAR, x, datetime(2026, 10, 3, 19, 45, tzinfo=timezone.utc),
                                   lambda m: {m[0]["fixture_id"]: sonuclar[m[0]["fixture_id"]]}, yaz=lambda m: None) == 0
    t = etkilesim.analiz_takip_tweeti(gun["analizler"][0], "2-0", takip["isabet"])
    assert t.startswith("🔁 FULL TIME\n⚽ Arsenal 2–0 Fulham") and tweets.uzunluk(t) <= 280 and t.endswith(tweets.ANSVAR)


def test_analiz_istatistik_ile_piyasayi_karsilastirir():
    from bot import analiz, etkilesim, gorsel, direktor
    m = {"fixture_id": 9, "lig_id": AYAR.ligler[0], "lig": "UEFA Nations League", "ev": "France", "dep": "Italy",
         "baslama": "2026-10-02T18:45:00+00:00"}
    b = {"Pinnacle": {"MS1": 1.95, "MSX": 3.5, "MS2": 4.2, "UST25": 1.9, "ALT25": 1.95}}
    ist = {"ev": {"oynanan_ic": 5, "oynanan_dis": 5, "atilan_ic_ort": 2.6, "yenilen_ic_ort": 0.8, "son5_atilan_ort": 2.4,
                  "son5_yenilen_ort": 0.8}, "dep": {"oynanan_ic": 5, "oynanan_dis": 5, "atilan_dis_ort": 1.6,
                  "yenilen_dis_ort": 1.8, "son5_atilan_ort": 1.5, "son5_yenilen_ort": 1.6}}
    a = analiz.mac_analizi(m, b, ist, AYAR)
    assert a["kaynak"] == "piyasa" and a["guven"] == "yuksek" and len(a["karsilastirma"]) == 5
    farklar = [abs(c["istatistik"] - c["piyasa"]) for c in a["karsilastirma"]]
    assert farklar == sorted(farklar, reverse=True)  # en büyük fark önce
    c = analiz.dikkat_cekici(a)
    assert c and c["istatistik"] > c["piyasa"]  # istatistik daha çok gol görüyor
    assert all(c["piyasa"] == a["p"][c["pazar"]] for c in a["karsilastirma"])  # karttaki ana rakamla aynı
    metin = etkilesim.analiz_tweeti(a, AYAR)
    assert "📈 Team stats: Over 2.5 goals 66%\n💹 Odds: 51%" in metin and tweets.uzunluk(metin) <= 280
    assert direktor.kurala_uygun(metin, "analiz", AYAR.oran_bahiscileri)
    for dil in ("en", "tr"):
        assert gorsel.analiz_karti(a, "20:45", dil)[:4] == b"\x89PNG"
    # oranı olmayan maç: yalnızca istatistik, karşılaştırma yok, güven düşük
    s = analiz.mac_analizi(m, None, ist, AYAR)
    assert s["kaynak"] == "istatistik" and s["guven"] == "dusuk" and s["karsilastirma"] == [] and not analiz.dikkat_cekici(s)


def test_istatistik_modeli_kucuk_orneklemde_kullanilmaz():
    from bot import analiz
    takim = lambda ic, dis, a, y: {"oynanan_ic": ic, "oynanan_dis": dis, "atilan_ic_ort": a, "yenilen_ic_ort": y,
                                   "atilan_dis_ort": a, "yenilen_dis_ort": y, "son5_atilan_ort": a, "son5_yenilen_ort": y}
    assert analiz.istatistik_golleri({"ev": takim(3, 3, 1.6, 1.0), "dep": takim(3, 3, 1.2, 1.3)})  # 6 maç: yeterli
    assert analiz.istatistik_golleri({"ev": takim(1, 1, 3.0, 0.0), "dep": takim(1, 2, 0.0, 2.0)}) is None  # 2-3 maç
    assert analiz.istatistik_golleri({"ev": takim(4, 4, 0.1, 0.2), "dep": takim(4, 4, 0.2, 0.1)}) is None  # uç değer
    m = {"fixture_id": 1, "lig": "X", "ev": "A", "dep": "B", "baslama": "2026-10-02T18:00:00+00:00"}
    kucuk = {"ev": takim(1, 1, 3.0, 0.0), "dep": takim(1, 2, 0.0, 2.0)}
    assert analiz.mac_analizi(m, None, kucuk, AYAR) is None  # oranı yok, istatistik güvenilmez: analiz yok


def test_analiz_tablosu_ve_ayrisma_postu():
    from bot import analiz, etkilesim, gorsel
    def a(fid, lig_id, lig, ev, saat, guven="yuksek", kars=None):
        p = {"MS1": 0.5, "MSX": 0.25, "MS2": 0.25, "UST15": 0.75, "UST25": 0.55, "UST35": 0.3, "KGVAR": 0.5,
             "IYU05": 0.7}
        return {"fixture_id": fid, "lig_id": lig_id, "lig": lig, "ev": ev, "dep": ev + " B", "guven": guven,
                "baslama": f"2026-10-03T{saat}:00+00:00", "p": p, "skorlar": [["1-0", 0.11]],
                "karsilastirma": kars or []}
    lig = AYAR.ligler[0]
    tum = [a(1, lig, "PL", "Arsenal", "14:00"), a(2, lig, "PL", "Leeds", "16:00"), a(3, lig, "PL", "Spurs", "18:00"),
           a(4, 999, "Low", "Small", "09:00"), a(5, 999, "Low", "Tiny", "13:00"), a(6, 998, "Low2", "Team", "13:00"),
           a(7, 997, "Low3", "Weak", "13:00", guven="dusuk")]
    t = analiz.tablo_secimi(tum, AYAR.ligler, en_erken="2026-10-03T10:00:00+00:00")
    ids = [x["fixture_id"] for x in t]
    assert 4 not in ids and 7 not in ids and 6 not in ids  # erken, güveni düşük, adı bozuk
    assert {1, 2, 3} <= set(ids) and 5 in ids  # büyük ligde sınır yok (B6), tablo zayıfsa alt lig de girer
    orta = AYAR.ligler[AYAR.ligler.index(40)]  # izinli ligde de lig sınırı yok; alt lig en fazla 2
    t2 = analiz.tablo_secimi([a(40 + i, orta, "Championship", f"Mid{i}", "15:00") for i in range(4)], AYAR.ligler)
    t3 = analiz.tablo_secimi([a(60 + i, 999, "Low", f"Low{i}", "15:00") for i in range(4)], AYAR.ligler)
    assert len(t2) == 4 and len(t3) == 2
    png = gorsel.analiz_tablosu(t, "2026-10-03", ["16:00"] * len(t), "en")
    assert png[:4] == b"\x89PNG"
    kars = lambda pi, ist: [{"pazar": "UST25", "ad": "Over 2.5 goals", "piyasa": pi, "istatistik": ist}]
    gun = {"tarih": "2026-10-03", "ayrisma": [a(8, 1, "X", "Alpha", "19:00", kars=kars(0.5, 0.7)),
                                              a(9, 1, "X", "Beta", "19:00", kars=kars(0.6, 0.45))]}
    m = etkilesim.ayrisma_tweeti(gun, AYAR, datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc))
    assert "ODDS vs TEAM STATS" in m and "⚽ Over 2.5 goals: 💹 odds 50% · 📈 stats 70%" in m and tweets.uzunluk(m) <= 280
    assert etkilesim.ayrisma_tweeti(gun, AYAR, datetime(2026, 10, 3, 20, 0, tzinfo=timezone.utc)) is None  # başladı
    # İkinci tablo: istatistiği olan büyük maçlar, oran ve istatistik yüzdesi yan yana (görsel + metin)
    k5 = lambda pi, ist: [{"pazar": "MS1", "ad": "x win", "piyasa": 0.5, "istatistik": 0.52},
                          {"pazar": "UST25", "ad": "Over 2.5 goals", "piyasa": pi, "istatistik": ist}]
    tum2 = [a(20 + i, lig, "PL", f"Club{i}", f"{14 + i}:00", kars=sorted(k5(0.53, 0.53 + 0.05 * i),
            key=lambda c: -abs(analiz.fark_puani(c)))) for i in range(5)] + [a(30, 999, "Low", "Nostat", "15:00")]
    kiyas = analiz.kiyas_secimi(tum2, AYAR.ligler, en_erken="2026-10-03T10:00:00+00:00")
    assert len(kiyas) == 5 and 30 not in [k["fixture_id"] for k in kiyas]  # büyük ligde sınır yok, istatistiksiz yok
    kiyas = [k for k in kiyas if k["fixture_id"] in (22, 23, 24)]
    gun2 = {"tarih": "2026-10-03", "kiyas": kiyas}
    m = etkilesim.ayrisma_tweeti(gun2, AYAR, datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc))
    assert "📸 3 matches side by side in the image" in m and "💹 odds 53% · 📈 stats 73%" in m
    png = gorsel.kiyas_tablosu(kiyas, "2026-10-03", ["16:00"] * 3)
    from bot import denetci
    assert denetci.analiz_kontrolu("ayrisma", m, kiyas, AYAR, png) == []


def test_liste_postu_butun_mac_etiketlerini_tasir():
    """Liste postu: adı geçen HER maçın yüzdeleri yazılır (sabit tweetin sözü); rakamı olmayan maç anılmaz.
    Etiketler yalnızca metinde adı geçen maçlardan, + turnuva ve genel etiketler; 280 sınırı."""
    from bot import direktor, etkilesim
    def a(ev, dep, lig, ulke="", p=None):
        d = {"ev": ev, "dep": dep, "lig": lig, "ulke": ulke, "baslama": "2026-10-03T18:45:00+00:00"}
        if p:
            d.update(p={"MS1": p[0], "MSX": 0.19, "MS2": 0.81 - p[0], "UST25": p[1], "ALT25": 1 - p[1], "KGVAR": 0.59,
                        "KGYOK": 0.41}, skorlar=[["2-1", 0.10]])
        return d
    liste = [a("France", "Italy", "UEFA Nations League", p=(0.66, 0.66)), a("Small", "Club", "Division 2", "Sweden"),
             a("Belgium", "Türkiye", "UEFA Nations League", p=(0.63, 0.67)), a("Germany", "Wales", "UEFA Nations League")]
    metin = etkilesim.tablo_tweeti({"tarih": "2026-10-03", "analiz_sayisi": 142}, liste, AYAR)
    assert "🆚 France v Italy\n🏆 France 66% · Draw 19% · Italy 15%" in metin  # bütün taraflar: seçim değil
    assert "🆚 Belgium v Türkiye\n🏆 Belgium 63% · Draw 19% · Türkiye 18%" in metin and "not picks" in metin
    assert "Germany" not in metin and "Also" not in metin  # rakamı olmayan maç adıyla anılmaz
    for blok in metin.split("🆚")[1:]:  # her maç bloğunda en az iki yüzde
        assert blok.split("\n\n")[0].count("%") >= 2
    assert "Which % surprises you?" in metin and "Small" not in metin
    etiketler = re.findall(r"#\w+", metin)
    assert etiketler == ["#NationsLeague", "#LesBleus"]  # turnuva + adı geçen maç; en fazla iki, genel etiket yok
    assert tweets.uzunluk(metin) <= 280 and metin.endswith(tweets.ANSVAR)
    tek = etkilesim.tablo_tweeti({"tarih": "2026-10-03", "analiz_sayisi": 142}, liste[:2], AYAR)
    assert "⚽ Over 2.5 goals 66% · Under 34%" in tek and "🥅 Both teams score 59% · Not both 41%" in tek
    assert "🎯 Likeliest score 2-1 (10%)" in tek  # yer varsa bütün rakamlar
    b = AYAR.oran_bahiscileri
    assert direktor.kurala_uygun(metin, "tablo", b, set(etiketler))
    assert not direktor.kurala_uygun("x #Football #Arsenal\n" + tweets.ANSVAR, "analiz", b)  # genel etiket yalnız listede
    assert not direktor.kurala_uygun(metin.replace("#LesBleus", "#BettingTips"), "tablo", b)  # bahis etiketi yok


def test_direktor_yuzde_dusuremez():
    """Direktör şablondaki yüzdelerden birini atarsa ya da rakamsız bir maçı anarsa şablon gider."""
    from bot import direktor
    sablon = "🆚 France v Italy\n🏆 France win 66%\n⚽ Over 2.5 goals 66%\n\n🆚 Belgium v Türkiye\n🏆 Belgium win 63%"
    olg = {"games": [{"match": "France v Italy"}, {"match": "Belgium v Türkiye"}, {"match": "Spain v Malta"}]}
    assert direktor.yuzdeler_tam("France v Italy: France win 66%, Over 2.5 goals 66%. Belgium v Türkiye: Belgium 63%",
                                 sablon, olg)
    assert not direktor.yuzdeler_tam("France win 66%, Over 2.5 goals 66%. Also Belgium v Türkiye.", sablon, olg)
    assert not direktor.yuzdeler_tam("France win 66%. Belgium win 63%", sablon, olg)  # ikinci 66% düştü
    assert not direktor.yuzdeler_tam(sablon + "\n👀 Spain v Malta tonight", sablon, olg)  # rakamsız maç


def test_denetci_analiz_postlarini_denetler():
    """Denetçi analiz postlarını da denetler: adı geçen maçın yüzdeleri olmalı ve kayıttakiyle aynı olmalı; görselin
    verisi eksiksiz olmalı. Direktör metni geçmezse şablon, o da geçmezse post çıkmaz."""
    from bot import denetci, etkilesim, gorsel, model
    def a(ev, dep):
        return {"ev": ev, "dep": dep, "lig": "UEFA Nations League", "ulke": "", "baslama": "2026-10-03T18:45:00+00:00",
                "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.9, 1.0).items()},
                "skorlar": [["2-1", 0.10], ["1-1", 0.09]], "guven": "yuksek", "beklenen_gol": [1.9, 1.0]}
    liste = [a("France", "Italy"), a("Belgium", "Türkiye"), a("Spain", "Malta")]
    metin = etkilesim.tablo_tweeti({"tarih": "2026-10-03", "analiz_sayisi": 142}, liste, AYAR)
    png = gorsel.analiz_tablosu(liste, "2026-10-03", ["20:45 CEST"] * 3)
    assert denetci.analiz_kontrolu("tablo", metin, liste, AYAR, png) == []
    fav = f'{round(100 * liste[0]["p"]["MS1"])}%'
    assert any("kayıtta olmayan" in h for h in denetci.analiz_kontrolu("tablo", metin.replace(fav, "99%"), liste, AYAR))
    yuzdesiz = metin.replace("💬", "🆚 Spain v Malta\n\n💬")
    assert any("yüzdeleri yok" in h for h in denetci.analiz_kontrolu("tablo", yuzdesiz, liste, AYAR))
    kart = etkilesim.analiz_tweeti(liste[0], AYAR)
    assert denetci.analiz_kontrolu("analiz", kart, liste[:1], AYAR, gorsel.analiz_karti(liste[0], "20:45 CEST")) == []
    eksik = {**liste[0], "p": {k: v for k, v in liste[0]["p"].items() if k != "UST35"}}
    assert any("görselin verisi" in h for h in denetci.analiz_kontrolu("analiz", kart, [eksik], AYAR, b"x"))
    # direktörün hatalı metni şablona döner; şablon da bozuksa None (post çıkmaz)
    loglar = []
    assert etkilesim._denetle("tablo", metin.replace(fav, "99%"), metin, liste, AYAR, None, loglar.append) == metin
    assert etkilesim._denetle("tablo", yuzdesiz, yuzdesiz, liste, AYAR, None, loglar.append) is None and loglar


def test_mac_sonu_postu_secim_dili_kullanmaz():
    """Kart olasılık verir, seçim yapmaz: maç sonu postu olanı ve maç öncesi yüzdesini yazar; ✅/❌, 'wrong',
    'calls came in' yok. Denetçi bu dili durdurur."""
    from bot import denetci, etkilesim, model
    a = {"ev": "Kazakhstan", "dep": "Moldova", "beklenen_gol": [1.5, 0.9], "skorlar": [["1-0", 0.14]],
         "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.5, 0.9).items()}}
    t = etkilesim.analiz_takip_tweeti(a, "1-2")
    assert f'🏆 Moldova win: {round(100 * a["p"]["MS2"])}%' in t and "⚽ Over 2.5 goals" in t
    assert "🥅 Both teams scored" in t and "🎯 Score 1-2:" in t and "Chances, not picks" in t
    assert "✅" not in t and "❌" not in t and tweets.uzunluk(t) <= 280
    assert denetci.analiz_kontrolu("analiz_sonuc", t, [a], AYAR) == []
    for kotu in ("❌ Kazakhstan win: 51%", "We got it wrong today", "0 of 3 headline calls came in"):
        assert denetci.analiz_kontrolu("analiz_sonuc", kotu + "\n" + tweets.ANSVAR, [a], AYAR)


def test_son_saati_yakin_kart_bilgi_postundan_once_cikar():
    """Nabız seyrek çalışsa da maçtan önce çıkması gereken kart, gün boyu çıkabilen bilgi postu yüzünden kaçmaz."""
    from bot import etkilesim, model
    a = {"fixture_id": 1, "ev": "Albacete", "dep": "Eibar", "lig": "Segunda División", "ulke": "Spain", "guven": "yuksek",
         "baslama": "2026-10-03T12:00:00+00:00", "beklenen_gol": [1.2, 1.0], "skorlar": [["1-1", 0.12]],
         "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.2, 1.0).items()}, "karsilastirma": []}
    gun = {"id": "2026-10-03", "tarih": "2026-10-03", "konsept": "analiz", "secimler": [], "sonuc": "analiz",
           "analizler": [a], "vitrin": [], "etkilesim": {}}

    class X:
        def __init__(self):
            self.n = 0

        def medya_yukle(self, png):
            return "m"

        def gonder(self, metin, **k):
            self.n += 1
            return str(self.n)
    tur = etkilesim.paylas(gun, AYAR, X(), datetime(2026, 10, 3, 9, 30, tzinfo=timezone.utc), yaz=lambda m: None)
    assert tur == "analiz_0" and "bilgi" not in gun["etkilesim"]  # bilgi sonra (son saati akşam)


def test_yogun_gun_yayilim_kartlari_kacirtmaz():
    """9 Ekim: aynı saatte başlayan çok sayıda kart varken postlar günün son postuna göre yayıldı ve 6 kart son
    saatini kaçırdı. Aralık, paylaşım sırasındaki her postun kendi son saatine yetişeceği kadar sık olmalı."""
    from bot import etkilesim
    def a(i, saat):
        return {"fixture_id": i, "lig_id": 999, "lig": "Eerste Divisie", "ev": f"Ev{i}", "dep": f"Dep{i}",
                "baslama": f"2026-10-03T{saat}:00+00:00", "guven": "yuksek", "p": {}, "skorlar": []}
    def gunu_oynat(gun, simdi):  # nabız 7 dakikada bir; kartların durumunu döndürür
        son = None
        while simdi < datetime(2026, 10, 3, 22, 0, tzinfo=timezone.utc):
            if son is None or simdi >= son + timedelta(minutes=etkilesim.aralik_dk(gun, AYAR, simdi)):
                for tur, erken, gec in etkilesim._paylasim_sirasi(gun, AYAR, simdi):
                    if tur in gun["etkilesim"] or simdi < erken:
                        continue
                    gun["etkilesim"][tur] = {"durum": "atlandi" if simdi > gec else "paylasildi"}
                    if simdi <= gec:
                        son = simdi
                        break
            simdi += timedelta(minutes=7)
        return {t: e["durum"] for t, e in gun["etkilesim"].items() if t.startswith("analiz_")}
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "secimler": [], "etkilesim": {},
           "analizler": [a(i, "18:00") for i in range(20)] + [a(99, "21:15")]}
    durumlar = gunu_oynat(gun, datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc))
    assert len(durumlar) == 21 and set(durumlar.values()) == {"paylasildi"}
    # 10 Ekim: son saati daha geç iki büyük maç kartı (B6) öne geçince, aynı saatte başlayan dar pencereli kartlardan
    # biri kaçacaktı. Büyük maç kartı ancak kalanların hepsi yetişiyorsa öne geçer.
    buyuk = [dict(a(50 + i, saat), lig_id=5, lig="UEFA Nations League") for i, saat in enumerate(("15:15", "16:00"))]
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "secimler": [], "etkilesim": {},
           "analizler": [a(i, "14:00") for i in range(9)] + buyuk}
    durumlar = gunu_oynat(gun, datetime(2026, 10, 3, 11, 30, tzinfo=timezone.utc))
    assert len(durumlar) == 11 and set(durumlar.values()) == {"paylasildi"}
    # 11 Ekim: aynı saatte başlayan çok kart 08:00 UTC'den önce açılmadı, 08:00–12:25 arasına sığmadı ve biri kaçtı.
    # Sığmayacaksa kart penceresi sabah analizinden itibaren (en çok maçtan 8 saat önce, B4) öne çekilir.
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "secimler": [], "etkilesim": {},
           "olusturma": "2026-10-03T05:35:00+00:00", "analizler": [a(i, "13:00") for i in range(20)]}
    durumlar = gunu_oynat(gun, datetime(2026, 10, 3, 5, 36, tzinfo=timezone.utc))
    assert len(durumlar) == 20 and set(durumlar.values()) == {"paylasildi"}


def test_yogun_gun_kisa_aralik_ve_aksam_kartlari():
    """Yoğun günde postlar arası kısa, kart listesi kapanmamış akşam maçlarıyla genişler (ek ligler dahil)."""
    from dataclasses import replace
    from bot import etkilesim, model
    ayar = replace(AYAR, yogun_gunler=("2026-10-03",), yogun_aralik_dk=15, yogun_kart=4, yogun_ek_ligler=(128,))
    def a(fid, lig_id, lig, ev, saat):
        return {"fixture_id": fid, "lig_id": lig_id, "lig": lig, "ev": ev, "dep": ev + " B", "guven": "yuksek",
                "baslama": f"2026-10-03T{saat}:00+00:00", "beklenen_gol": [1.4, 1.1], "skorlar": [["1-1", 0.12]],
                "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.4, 1.1).items()}, "karsilastirma": []}
    tum = [a(1, AYAR.ligler[0], "PL", "Arsenal", "14:00"), a(2, 128, "Liga Profesional", "Newells", "20:00"),
           a(3, 128, "Liga Profesional", "Tucuman", "20:00"), a(4, 999, "Primera C", "Small", "20:00"),
           a(5, AYAR.ligler[0], "PL", "Spurs", "18:00")]
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "analizler": [tum[0]], "secimler": [], "etkilesim": {}}
    simdi = datetime(2026, 10, 3, 17, 30, tzinfo=timezone.utc)
    assert etkilesim.yogun_kartlari_ekle(gun, tum, ayar, simdi) == 2  # Spurs 18:00 penceresi kapandı, Primera C yok
    assert [x["ev"] for x in gun["analizler"]] == ["Arsenal", "Newells", "Tucuman"]  # eskiler yerinde, yeniler sonda
    assert etkilesim.yogun_kartlari_ekle(gun, tum, ayar, simdi) == 0  # eklenecek yeni maç kalmadı


def test_saglik_alarmi_kacan_ve_duran_postu_bildirir(tmp_path, monkeypatch):
    """Kaçan kart, gecikmiş maç sonu postu, hata ve yoğun günde durgunluk alarm olur; aynı sorun iki kez
    bildirilmez; aynı gün yeni sorunlar aynı issue'ya yorum olarak eklenir."""
    from dataclasses import replace
    from bot import model, saglik
    monkeypatch.setattr(saglik, "DOSYA", tmp_path / "alarm.json")
    ayar = replace(AYAR, yogun_hafta_sonu=True, yogun_aralik_dk=13)
    def a(ev, saat):
        return {"fixture_id": hash(ev), "ev": ev, "dep": ev + " B", "lig": "X", "lig_id": 5,  # Uluslar Ligi: büyük maç
                "baslama": f"2026-10-03T{saat}:00+00:00",
                "beklenen_gol": [1.3, 1.1], "skorlar": [["1-1", 0.12]], "guven": "yuksek",
                "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.3, 1.1).items()}}
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "secimler": [], "analizler":
           [a("Albacete", "12:00"), a("Almeria", "14:15"), a("Newells", "20:00"), a("Hata", "21:00")],
           "etkilesim": {"analiz_0": {"durum": "atlandi"},
                         "analiz_1": {"durum": "paylasildi", "zaman": "2026-10-03T13:28:00+00:00"},
                         "analiz_3": {"durum": "hata", "hata": "X 503"}}}
    simdi = datetime(2026, 10, 3, 18, 0, tzinfo=timezone.utc)  # Cumartesi
    bulunan = dict(saglik.sorunlar([gun], simdi, ayar, ["Etkileşim paylaşımı: boom"]))
    metin = " ".join(bulunan.values())
    assert "Albacete" in metin and "penceresi geçti" in metin  # kaçan kart
    assert "Almeria" in metin and "maç sonu postu hâlâ çıkmadı" in metin  # 14:15 + 3,5 saat geçti
    assert "X 503" in metin and "boom" in metin and "dakikadır post yok" in metin  # Newells kartı sırada, 4,5 saattir sessiz

    class GH:
        def __init__(self):
            self.acilan, self.yorumlar = [], []

        def issue_ac(self, baslik, govde, etiket):
            self.acilan.append((baslik, govde, etiket))
            return 7

        def yorum(self, no, govde):
            self.yorumlar.append((no, govde))
    gh = GH()
    n = saglik.bildir(list(bulunan.items()), gh, "Kalkylerat-desk", simdi, yaz=lambda m: None)
    assert n == len(bulunan) and gh.acilan[0][2] == "alarm" and gh.acilan[0][1].startswith("@Kalkylerat-desk")
    assert saglik.bildir(list(bulunan.items()), gh, "Kalkylerat-desk", simdi, yaz=lambda m: None) == 0  # tekrar yok
    saglik.bildir([("yeni", "🔇 yeni sorun")], gh, "Kalkylerat-desk", simdi, yaz=lambda m: None)
    assert len(gh.acilan) == 1 and gh.yorumlar == [(7, gh.yorumlar[0][1])] and "yeni sorun" in gh.yorumlar[0][1]


def test_tablodaki_mac_bittikce_tabloya_yanit():
    """Tablodaki her maç bittikçe tablo postuna yanıt: skor, olanların maç öncesi yüzdeleri, istatistik varsa
    oranla yan yana. Bitmeyen beklenir, oynanmayan atlanır, aynı maç iki kez yazılmaz."""
    from bot import denetci, etkilesim, model
    def a(fid, ev, saat, kars=None):
        return {"fixture_id": fid, "ev": ev, "dep": ev + " B", "lig": "PL", "baslama": f"2026-10-03T{saat}:00+00:00",
                "beklenen_gol": [1.5, 1.0], "skorlar": [["1-0", 0.12]], "karsilastirma": kars or [],
                "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.5, 1.0).items()}}
    kars = [{"pazar": "MSX", "ad": "Draw", "piyasa": 0.25, "istatistik": 0.31},
            {"pazar": "UST25", "ad": "Over 2.5 goals", "piyasa": 0.5, "istatistik": 0.62},
            {"pazar": "KGVAR", "ad": "Both teams score", "piyasa": 0.5, "istatistik": 0.58}]
    gun = {"tarih": "2026-10-03", "tablo": [a(1, "Burton", "12:00", kars), a(2, "Leeds", "16:30"), a(3, "Spurs", "12:00")],
           "etkilesim": {"tablo": {"durum": "paylasildi", "tweet_id": "50", "zaman": "2026-10-03T08:35:00+00:00",
                                   "maclar": [1, 2, 3]}}}
    sonuc = {1: {"durum": "bitti", "skor": (2, 2)}, 2: {"durum": "bitti", "skor": (0, 1)}, 3: {"durum": "iptal"}}

    class X:
        def __init__(self):
            self.giden = []

        def gonder(self, metin, **k):
            self.giden.append((metin, k))
            return str(len(self.giden))
    x = X()
    assert etkilesim.tablo_takibi(gun, AYAR, x, datetime(2026, 10, 3, 14, 0, tzinfo=timezone.utc), lambda l: sonuc) == 1
    metin, k = x.giden[0]
    assert k == {"yanit": "50"} and "🆚 Burton 2–2 Burton B" in metin
    assert "🏆 Draw: odds" in metin and "stats 31%" in metin and "⚽ Over 2.5 goals:" in metin and "stats 62%" in metin
    assert "🥅 Both teams scored:" in metin and "stats 58%" in metin and "🎯 Score 2-2:" in metin
    assert tweets.uzunluk(metin) <= 280 and denetci.analiz_kontrolu("tablo_sonuc", metin, [], AYAR) == []
    assert gun["etkilesim"]["tablo"]["sonuclar"]["3"]["neden"] == "maç oynanmadı" and not gun["etkilesim"]["tablo"].get("takip")
    assert etkilesim.tablo_takibi(gun, AYAR, x, datetime(2026, 10, 3, 14, 15, tzinfo=timezone.utc), lambda l: sonuc) == 0
    assert etkilesim.tablo_takibi(gun, AYAR, x, datetime(2026, 10, 3, 18, 30, tzinfo=timezone.utc), lambda l: sonuc) == 1
    assert "Leeds 0–1" in x.giden[1][0] and gun["etkilesim"]["tablo"]["takip"]["durum"] == "tamam"


def test_yanit_kiti_taslak_hazirlar_gunde_bir_kez(tmp_path, monkeypatch):
    """Yanıt kiti: büyük maçlar için arama bağlantıları ve kayıttaki rakamlarla yanıt taslakları; seçim/bahis dili
    yok; günde bir kez; sahibi etiketlenir."""
    from bot import denetci, kit, model
    monkeypatch.setattr(kit, "KLASOR", tmp_path / "kit")
    def a(fid, ev, saat):
        return {"fixture_id": fid, "ev": ev, "dep": ev + " B", "lig": "PL", "baslama": f"2026-10-04T{saat}:00+00:00",
                "beklenen_gol": [1.5, 1.0], "skorlar": [["1-0", 0.12]], "guven": "yuksek",
                "karsilastirma": [{"pazar": "UST25", "ad": "Over 2.5 goals", "piyasa": 0.5, "istatistik": 0.62}],
                "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.5, 1.0).items()}}
    gun = {"tarih": "2026-10-04", "konsept": "analiz", "analizler": [a(1, "Spain", "18:45"), a(2, "Old", "06:00")]}

    class GH:
        def __init__(self):
            self.acilan = []

        def issue_ac(self, baslik, govde, etiket):
            self.acilan.append((baslik, govde, etiket))
            return 12
    gh = GH()
    simdi = datetime(2026, 10, 4, 8, 0, tzinfo=timezone.utc)
    assert kit.gonder(gun, AYAR, gh, lambda x: "20:45 CEST", simdi, "https://raw/x") == 12
    baslik, govde, etiket = gh.acilan[0]
    assert etiket == "yanit-kiti" and "Spain v Spain B" in govde and "Old v" not in govde  # başlamış maç yok
    assert "x.com/search?q=Spain%20Spain%20B&f=top" in govde and "https://raw/x/docs/kit/2026-10-04/1.png" in govde
    assert "team stats say 62%" in govde and (tmp_path / "kit" / "2026-10-04" / "1.png").exists()
    for t in kit.yanitlar(gun["analizler"][0]):
        assert len(t) <= 280 and not denetci._SECIM_DILI.search(t) and "bet" not in t.lower()
    assert kit.gonder(gun, AYAR, gh, lambda x: "", simdi, "u") is None and len(gh.acilan) == 1  # günde bir kez


def test_x_kurallari_tekrar_ve_gunluk_sinir():
    """X spam kuralları: aynı metin aynı gün iki kez gitmez; günlük post sınırı aşılmaz; otomatik postta en fazla bir
    (listede iki) ilgili etiket, genel etiket yok."""
    from dataclasses import replace
    from bot import etkilesim
    gun = {"tarih": "2026-10-04", "etkilesim": {"bilgi": {"durum": "paylasildi", "metin": "Aynı metin\n18+"}}}

    class X:
        def gonder(self, metin, **k):
            return "1"
    k = etkilesim._TekrarKorumasi(X(), gun)
    assert k.gonder("Başka metin") == "1"
    with pytest.raises(RuntimeError, match="tekrar"):
        k.gonder("Aynı metin\n18+")
    dolu = {"tarih": "2026-10-04", "konsept": "analiz", "secimler": [], "analizler": [], "vitrin": [],
            "etkilesim": {f"x{i}": {"durum": "paylasildi", "zaman": "2026-10-04T08:00:00+00:00"} for i in range(3)}}
    assert etkilesim.paylas(dolu, replace(AYAR, gunluk_post_siniri=3), X(),
                            datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc), yaz=lambda m: None) is None
    assert tweets.liste_etiketleri([("UEFA Nations League", "")] * 3, [("France", "Italy"), ("Belgium", "Türkiye"),
                                                                     ("England", "Wales")]) == ["#NationsLeague", "#LesBleus"]
    assert "#Football" not in tweets.liste_etiketleri([("Premier League", "England")], [("Arsenal", "Leeds")])


def test_erken_ilk_macta_tablo_ve_ayrisma_penceresi_one_cekilir():
    """İlk tablo maçı 08:00 UTC'de (Asya öğle maçı): pencere sabit açılıştan önce, analizden sonra açılır; boş kalmaz."""
    from bot import etkilesim
    m = {"baslama": "2026-10-07T08:00:00+00:00"}
    gun = {"tarih": "2026-10-07", "konsept": "analiz", "olusturma": "2026-10-07T05:36:00+00:00",
           "tablo": [m], "kiyas": [m, {"baslama": "2026-10-07T12:00:00+00:00"}]}
    plan = {t: (e, l) for t, e, l in etkilesim._plan(gun)}
    for tur in ("tablo", "ayrisma"):
        e, l = plan[tur]
        assert e < l and e >= datetime(2026, 10, 7, 5, 36, tzinfo=timezone.utc)
    assert plan["tablo"][0] == datetime(2026, 10, 7, 6, 0, tzinfo=timezone.utc)
    gec = {**gun, "tablo": [{"baslama": "2026-10-07T18:45:00+00:00"}], "kiyas": None}  # akşam maçı: sabit 08:00 kalır
    assert dict((t, e) for t, e, _ in etkilesim._plan(gec))["tablo"] == datetime(2026, 10, 7, 8, 0, tzinfo=timezone.utc)


def test_aksam_tablosu_yogun_gunde_bir_kez():
    """Yoğun günde 16:00 UTC'den sonra sabah tablosunda olmayan (kartlı olsa da) akşam maçlarıyla ikinci tablo."""
    from dataclasses import replace
    from bot import etkilesim, model
    ayar = replace(AYAR, yogun_hafta_sonu=True)
    def a(fid, ev, saat, lig_id=None, lig="PL"):
        return {"fixture_id": fid, "ev": ev, "dep": ev + " B", "lig": lig, "lig_id": lig_id or AYAR.ligler[0],
                "baslama": f"2026-10-03T{saat}:00+00:00", "guven": "yuksek", "beklenen_gol": [1.4, 1.1],
                "skorlar": [["1-1", 0.12]], "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.4, 1.1).items()}}
    tum = [a(i, f"Club{i}", "19:30", lig=f"L{i % 3}") for i in range(1, 7)] + [a(9, "Early", "16:30")]
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "tablo": [a(1, "Club1", "19:30", lig="L1")], "analizler": [a(2, "Club2", "19:30", lig="L2")],
           "etkilesim": {}}
    assert etkilesim.aksam_tablosu_ekle(gun, tum, ayar, datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc)) == 0
    assert etkilesim.aksam_tablosu_ekle(gun, tum, ayar, datetime(2026, 10, 3, 17, 0, tzinfo=timezone.utc)) == 5  # kartlı maç da girer
    ids = {x["fixture_id"] for x in gun["tablo_aksam"]}
    assert ids == {2, 3, 4, 5, 6} and any(t == "tablo_aksam" for t, _, _ in etkilesim._plan(gun))
    assert etkilesim.aksam_tablosu_ekle(gun, tum, ayar, datetime(2026, 10, 3, 18, 0, tzinfo=timezone.utc)) == 0  # bir kez
    assert "from tonight's board" in etkilesim.tablo_mac_sonu_tweeti(gun["tablo_aksam"][0], 1, 0, aksam=True)


def test_liste_simdi_sonucsuz_sabah_tablosunu_buyuk_maclarla_degistirir(monkeypatch, tmp_path):
    """Yanlış seçilmiş (alt lig) sabah tablosu, altına sonuç gelmediyse elle listeyle silinip büyük maçlarla yenilenir;
    sonucu gelmiş tablo silinmez."""
    import bot.__main__ as ana
    monkeypatch.setattr(config, "DATA_FILE", tmp_path / "spel.json")
    (tmp_path / "analiz").mkdir()
    def a(fid, ev, lig_id, saat):
        return {"fixture_id": fid, "ev": ev, "dep": ev + " B", "lig": f"L{lig_id}", "ulke": "", "lig_id": lig_id,
                "guven": "yuksek", "baslama": f"2026-10-04T{saat}:00+00:00", "beklenen_gol": [1.4, 1.1],
                "skorlar": [["1-1", 0.12]], "p": {k: round(v, 3) for k, v in model.model_olasiliklari(1.4, 1.1).items()}}
    tum = [a(i, f"Nation{i}", 5, "18:45") for i in range(1, 7)] + [a(20, "Astur", 440, "12:15")]
    (tmp_path / "analiz" / "2026-10-04.json").write_text(json.dumps(tum))
    gun = {"id": "2026-10-04", "tarih": "2026-10-04", "konsept": "analiz", "analizler": [],
           "etkilesim": {"tablo": {"durum": "paylasildi", "tweet_id": "111", "maclar": [20]}}}

    class X:
        silinen = []
        def sil(self, tid): self.silinen.append(tid)
        def medya_yukle(self, png): return "m"
        def gonder(self, metin, **k): self.metin = metin; return "222"
    x = X()
    assert ana.liste_simdi(AYAR, [gun], "2026-10-04", datetime(2026, 10, 4, 9, 0, tzinfo=timezone.utc), x) == "222"
    assert x.silinen == ["111"] and gun["etkilesim"]["tablo"]["durum"] == "silindi"
    assert set(gun["etkilesim"]["tablo_2"]["maclar"]) == set(range(1, 7)) and "Nation" in x.metin
    gun["etkilesim"]["tablo_2"]["sonuclar"] = {"1": {"durum": "paylasildi"}}
    gun["etkilesim"]["tablo_2"]["elle"] = False
    x.silinen = []
    ana.liste_simdi(AYAR, [gun], "2026-10-04", datetime(2026, 10, 4, 9, 30, tzinfo=timezone.utc), x)
    assert x.silinen == []  # sonucu gelmiş liste korunur


def test_toplu_oranlarda_ayni_macin_kayitlari_birlestirilir():
    """Aynı maç iki kayıtta (bahisçiler bölünmüş) gelirse sonraki kayıt öncekinin bahisçilerini silmez."""
    def kayit(bahisci, oran):
        return {"fixture": {"id": 7}, "bookmakers": [{"name": bahisci, "bets": [
            {"name": "Match Winner", "values": [{"value": "Home", "odd": oran}, {"value": "Draw", "odd": "3.5"}, {"value": "Away", "odd": "4.0"}]}]}]}

    class Api:
        def get_body(self, path, **params):
            return {"response": [kayit("Pinnacle", "1.90"), kayit("Bet365", "1.85")], "paging": {"current": 1, "total": 1}}
    oranlar = football.toplu_oranlar(Api(), "2026-10-06", "Europe/Stockholm", 5)
    assert set(oranlar[7]) == {"Pinnacle", "Bet365"} and oranlar[7]["Pinnacle"]["MS1"] == 1.90


def test_yeni_issue_eski_ayni_etiketlileri_kapatir():
    """12 Ekim: günlük alarm, yanıt kiti, rapor ve Mr. Likely issue'ları birikmesin; yenisi açılınca eskiler kapanır."""
    from bot import onay

    class Cevap:
        def __init__(self, veri):
            self.veri = veri
        def raise_for_status(self):
            pass
        def json(self):
            return self.veri

    class Oturum:
        def __init__(self):
            self.kapanan = []
        def post(self, url, json, timeout):
            return Cevap({"number": 60})
        def get(self, url, params, timeout):
            return Cevap([{"number": 60}, {"number": 52}, {"number": 48, "pull_request": {}}])
        def patch(self, url, json, timeout):
            self.kapanan.append(int(url.rsplit("/", 1)[1]))
            return Cevap({})

    gh = onay.GitHub(token="x", repo="a/b")
    gh.s = Oturum()
    assert gh.issue_ac("💬 Yanıt kiti", "govde", "yanit-kiti") == 60
    assert gh.s.kapanan == [52]  # yalnızca eski issue; yenisi ve PR'lar kapanmaz
    gh.s.kapanan.clear()
    gh.issue_ac("Onay", "govde", "onay")
    assert gh.s.kapanan == []  # listede olmayan etiketlere dokunulmaz


