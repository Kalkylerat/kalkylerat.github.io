"""Büyük maç hikayesi flood'u (SOZLESME E1, 25 Ekim 2026): olgular yalnızca API verisinden, kodla."""

from datetime import datetime, timedelta, timezone

from bot import config, likely, likely_hikaye as hk
from bot.tweets import ANSVAR, LIMIT, uzunluk

UTC = timezone.utc
SIMDI = datetime(2026, 10, 25, 15, 0, tzinfo=UTC)
M = {"fixture_id": 99, "ev": "Freiburg", "dep": "Bayern Munich", "ev_id": 160, "dep_id": 157, "lig_id": 78,
     "lig": "Bundesliga", "baslama": "2026-10-25T19:30:00+01:00"}


def mac(ev, dep, gev, gdep, gun_once, lig=78, durum="FT", ev_ad=None, dep_ad=None):
    ad = {160: "Freiburg", 157: "Bayern Munich", 91: "Monaco", 42: "Arsenal", 165: "Leverkusen", 173: "Leipzig"}
    return {"fixture": {"date": (SIMDI - timedelta(days=gun_once)).isoformat(), "status": {"short": durum}},
            "league": {"id": lig},
            "teams": {"home": {"id": ev, "name": ev_ad or ad[ev], "winner": gev > gdep if gev != gdep else None},
                      "away": {"id": dep, "name": dep_ad or ad[dep], "winner": gdep > gev if gev != gdep else None}},
            "goals": {"home": gev, "away": gdep}}


def ham():
    h2h = [mac(160, 157, 2, 1, 900)] + [mac(157, 160, 3, 1, 30 * i) for i in range(1, 17)] + \
          [mac(160, 157, 1, 1, 40 * i + 5) for i in range(1, 5)]  # 21 maç: Freiburg 1 galibiyet
    return {
        "mac": {"league": {"id": 78, "season": 2026}},
        "h2h": h2h,
        "ev_son": [mac(91, 160, 3, 0, 4, lig=2)],
        "dep_son": [mac(157, 42, 2, 2, 4, lig=2)],
        "puan": [[{"rank": 1, "points": 22, "team": {"id": 157}, "group": "Bundesliga"},
                  {"rank": 3, "points": 21, "team": {"id": 160}, "group": "Bundesliga"}]],
        "ev_ist": {"fixtures": {"played": {"home": 3}, "wins": {"home": 3}, "draws": {"home": 0}, "loses": {"home": 0}},
                   "form": "WWLW", "goals": {"for": {"total": {"total": 12},
                                                     "minute": {"76-90": {"total": 4}, "91-105": {"total": None}}}}},
        "dep_ist": {"fixtures": {"played": {"away": 3}, "wins": {"away": 1}, "draws": {"away": 2}, "loses": {"away": 0}},
                    "form": "WWWWW", "goals": {"for": {"total": {"total": 20}, "minute": {}}}},
        "sakat": [{"player": {"name": "J. Musiala", "type": "Missing Fixture"}, "team": {"id": 157}},
                  {"player": {"name": "X. Doubt", "type": "Questionable"}, "team": {"id": 160}}],
    }


def test_E1_buyuk_mac_hikayesi_olgular_kayittan():
    o = [x["metin"] for x in hk.olgular(ham(), M, SIMDI)]
    assert o[0] == "Freiburg have won 1 of the last 21 meetings with Bayern Munich."  # en ilginç önce
    assert "Bayern Munich are unbeaten in the last 20 meetings with Freiburg." in o
    assert "A top-four clash: Freiburg 3rd on 21 pts, Bayern Munich top on 22 pts." in o
    assert "Both played midweek: Freiburg lost 3-0 at Monaco, Bayern Munich drew 2-2 v Arsenal." in o
    assert "Freiburg have won all 3 home games this season." in o
    assert "Bayern Munich are unbeaten away this season (W1 D2)." in o
    assert "Bayern Munich have won their last 5 league games." in o
    assert "Freiburg have scored 4 of their 12 league goals after the 75th minute." in o
    assert hk.sakatlar(ham(), M) == "🩹 Out: J. Musiala (Bayern Munich)."  # "Questionable" yazılmaz


def test_E1_buyuk_mac_hikayesi_postlari():
    p = hk.postlar(ham(), M, SIMDI, "t")
    assert len(p) == 2 and p[0].startswith("📋 The story: Freiburg have won 1 of the last 21")
    assert p[0].count("meetings") <= 2 and "Musiala" in p[1] and "💬 " in p[1] and p[1].endswith(ANSVAR)
    for x in p:
        assert uzunluk(x) <= LIMIT and x.rstrip().splitlines()[-1].startswith("18+") and not hk.denetle(x)


def test_E1_buyuk_mac_hikayesi_veri_yoksa_flood_yok():
    assert hk.postlar({}, M, SIMDI) == []
    az = {"h2h": [mac(160, 157, 1, 0, 10)]}  # 5'ten az eşleşme: geçmiş olgusu yok
    assert hk.olgular(az, M, SIMDI) == []


class SahteApi:
    def __init__(self):
        self.yollar = []

    def get(self, yol, **k):
        self.yollar.append(yol)
        h = ham()
        return {"fixtures": [h["mac"]] if "id" in k else h["ev_son"] if k.get("team") == 160 else h["dep_son"],
                "fixtures/headtohead": h["h2h"], "injuries": h["sakat"],
                "standings": [{"league": {"standings": h["puan"]}}]}[yol]

    def get_body(self, yol, **k):
        self.yollar.append(yol)
        return {"response": ham()["ev_ist" if k["team"] == 160 else "dep_ist"]}


def test_E1_buyuk_mac_hikayesi_veri_toplama_ve_puan_durumu_onbellekte():
    api, onbellek = SahteApi(), {}
    h = hk.veri_topla(api, M, onbellek)
    assert h["puan"] and h["ev_ist"]["form"] == "WWLW" and len(api.yollar) == 8
    hk.veri_topla(api, M, onbellek)
    assert api.yollar.count("standings") == 1  # aynı lig: puan durumu bir kez


class SahteX:
    def __init__(self):
        self.postlar = []

    def gonder(self, metin, yanit=None, **k):
        self.postlar.append((metin, yanit))
        return f"t{len(self.postlar)}"


def test_E1_buyuk_mac_hikayesi_flood_zinciri(monkeypatch, tmp_path):
    ayar = config.yukle()
    cfg = likely.LikelyAyar(aktif=True, mod="otomatik")
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: cfg)
    m = {**M, "buyuk": True, "hikaye": True, "saat": (SIMDI - timedelta(minutes=1)).isoformat(),
         "baslama": (SIMDI + timedelta(hours=2)).isoformat(),
         "p": {"MS1": 0.16, "MSX": 0.19, "MS2": 0.65, "UST25": 0.6, "KGVAR": 0.55},
         "aci": {"aday_id": "99-CSX2", "etiket": "Double chance X2", "olasilik": 0.84, "oran": 1.18}}
    likely.kaydet({"gunler": [{"tarih": "2026-10-25", "oto": True, "secilen": [], "maclar": [m]}]})
    x = SahteX()
    assert likely.oto_mac(ayar, x, SIMDI, hikaye=lambda m_: hk.postlar(ham(), m_, SIMDI))
    assert len(x.postlar) == 3 and "🧵" in x.postlar[0][0]
    assert [y for _, y in x.postlar] == [None, "t1", "t2"]  # her post bir öncekine yanıt
    kayit = likely.yukle()["gunler"][0]["maclar"][0]
    assert kayit["hikaye_ids"] == ["t2", "t3"]
    # hikaye verisi alınamazsa tek post, 🧵 yok
    m2 = {**m, "fixture_id": 100}
    likely.kaydet({"gunler": [{"tarih": "2026-10-25", "oto": True, "secilen": [], "maclar": [m2]}]})
    x2 = SahteX()

    def bozuk(_):
        raise RuntimeError("API")
    assert likely.oto_mac(ayar, x2, SIMDI, hikaye=bozuk, yaz=lambda *_: None)
    assert len(x2.postlar) == 1 and "🧵" not in x2.postlar[0][0]


def test_E1_buyuk_mac_hikayesi_en_fazla_4_buyuk_macta():
    from bot import analiz
    analizler, adaylar = [], []
    for i in range(7):
        a = {"fixture_id": i, "ev": f"E{i}", "dep": f"D{i}", "ev_id": 10 + i, "dep_id": 50 + i, "lig_id": 39,
             "lig": "Premier League", "kaynak": "piyasa", "guven": "yuksek",
             "baslama": (SIMDI + timedelta(hours=4 + i)).isoformat(),
             "p": {"MS1": 0.6, "MSX": 0.2, "MS2": 0.2, "UST25": 0.5, "KGVAR": 0.5}}
        analizler.append(a)
        adaylar.append({"aday_id": f"{i}-CS1X", "fixture_id": i, "tur": "guvenli", "pazar": "CS1X", "uyum": True,
                        "etiket": "Double chance 1X", "olasilik": 0.8, "oran": 1.2, "site_sayisi": 4})
    assert all(analiz.onemli(a) for a in analizler)
    cfg = likely.LikelyAyar(aktif=True, mod="otomatik")
    plan = likely.mac_planla(analizler, adaylar, [], SIMDI, cfg, config.yukle())
    assert sum(bool(m.get("hikaye")) for m in plan) == cfg.oto_hikaye_sayisi == 4
    assert all(m["ev_id"] and m["dep_id"] for m in plan if m.get("hikaye"))
