import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from bot import config, editor, kayit, model, tweets
from bot.__main__ import main

AYAR = config.yukle()


def test_poisson_olasiliklari_tutarli():
    p = model.model_olasiliklari(1.6, 1.1)
    assert p["MS1"] + p["MSX"] + p["MS2"] == pytest.approx(1, abs=1e-4)
    assert p["UST25"] + p["ALT25"] == pytest.approx(1, abs=1e-4)
    assert p["CS1X"] == pytest.approx(p["MS1"] + p["MSX"], abs=1e-9)


def test_piyasa_marji_arindirilir():
    p = model.piyasa_olasiliklari({"MS1": 1.9, "MSX": 3.5, "MS2": 4.0, "UST25": 1.9, "ALT25": 1.9})
    assert p["MS1"] + p["MSX"] + p["MS2"] == pytest.approx(1)
    assert p["UST25"] == pytest.approx(0.5)
    assert "KGVAR" not in p


def test_adil_olasilik_keskin_yoksa_ortalama():
    b = {"A": {"UST25": 1.9, "ALT25": 1.9}, "B": {"UST25": 1.8, "ALT25": 2.0}, "C": {"UST25": 2.0, "ALT25": 1.8}}
    adil, kaynak = model.adil_olasiliklar(b, "Pinnacle")
    assert adil["UST25"] == pytest.approx(0.5, abs=0.01)
    assert kaynak["UST25"].startswith("ortalama")
    b["Pinnacle"] = {"UST25": 1.5, "ALT25": 2.8}
    adil, kaynak = model.adil_olasiliklar(b, "pinnacle")
    assert kaynak["UST25"] == "Pinnacle" and adil["UST25"] > 0.6


def test_en_iyi_oran_sadece_lisansli_bahisciden():
    b = {"Unibet": {"MS1": 2.1}, "Betsson": {"MS1": 2.2}, "1xBet": {"MS1": 2.6}}
    assert model.en_iyi_oranlar(b, ["Unibet", "Betsson"])["MS1"] == (2.2, "Betsson")


@pytest.mark.parametrize("pazar,ev,dep,beklenen", [
    ("MS1", 2, 1, True), ("MSX", 1, 1, True), ("CSX2", 0, 0, True), ("CS12", 1, 1, False),
    ("UST25", 2, 1, True), ("ALT25", 2, 1, False), ("KGVAR", 1, 0, False), ("KGYOK", 0, 3, True),
])
def test_kazandi_mi(pazar, ev, dep, beklenen):
    assert model.kazandi_mi(pazar, ev, dep) is beklenen


def _gun(gid, oranlar, tweet_id="t1"):
    return {"id": gid, "tarih": gid, "sonuc": None, "tweet_id": tweet_id, "secimler": [
        {"fixture_id": i, "pazar": "MS1", "oran": o, "baslama": "2026-10-03T15:00:00+02:00", "durum": "bekliyor",
         "ev": "Hammarby", "dep": "AIK", "etiket": "1 (hemmaseger)", "kisa": "1", "bolag": "Unibet",
         "deger": 0.04, "yorum": ""} for i, o in enumerate(oranlar, 1)]}


def test_sonuclandirma_ve_birim_hesabi():
    simdi = datetime(2026, 10, 4, tzinfo=timezone.utc)
    g1, g2 = _gun("a", [2.0, 1.5]), _gun("b", [1.8], tweet_id=None)
    biten = kayit.sonuclandir([g1], {1: {"durum": "bitti", "skor": (2, 0)},
                                     2: {"durum": "bekliyor", "skor": None}}, simdi)
    assert biten == [] and g1["secimler"][0]["durum"] == "kazandi"
    biten = kayit.sonuclandir([g1], {2: {"durum": "bitti", "skor": (0, 1)}}, simdi)
    assert biten == [g1] and g1["sonuc"] == "tamam"
    kayit.sonuclandir([g2], {1: {"durum": "bitti", "skor": (1, 0)}}, simdi)
    o = kayit.ozet([g1, g2])
    assert (o["spel"], o["vunna"], o["forlorade"]) == (2, 1, 1)  # yayınlanmamış g2 sayılmaz
    assert o["enheter"] == pytest.approx(1.0 - 1.0)
    assert o["snittodds"] == pytest.approx(1.75)


def test_iptal_edilen_mac_birim_etkilemez():
    g = _gun("a", [2.0])
    kayit.sonuclandir([g], {1: {"durum": "iptal", "skor": None}}, datetime(2026, 10, 4, tzinfo=timezone.utc))
    assert g["secimler"][0]["durum"] == "iptal" and kayit.ozet([g])["spel"] == 0


def test_uzun_bekleyen_mac_iptal_olur():
    g = _gun("a", [1.5])
    kayit.sonuclandir([g], {}, datetime(2026, 10, 7, tzinfo=timezone.utc))
    assert g["sonuc"] == "tamam" and g["secimler"][0]["durum"] == "iptal"


def test_tweetler_sinirda_ve_ansvar_satiri_kalir():
    g = _gun("2026-10-03", [1.5, 1.6, 1.7])
    for s in g["secimler"]:
        s.update(ev="Borussia Mönchengladbach", dep="Wolverhampton Wanderers", kisa="BLGM Nej", yorum="x" * 400)
    ana = tweets.gun_tweeti(g, kayit.ozet([]))
    assert tweets.uzunluk(ana) <= 280 and ana.endswith(tweets.ANSVAR)
    assert all(tweets.uzunluk(t) <= 280 for t in tweets.analiz_tweetleri(g))
    for s in g["secimler"]:
        s.update(durum="kazandi", skor="2-1")
    g["sonuc"] = "tamam"
    assert tweets.uzunluk(tweets.sonuc_tweeti(g, kayit.ozet([g]))) <= 280
    assert tweets.uzunluk("⚽") == 2 and tweets.uzunluk("ö") == 1
    assert tweets.sayi(1.5) == "1,50" and tweets.isaretli(-2.345, 2) == "−2,35"


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
    return [{"aday_id": f"{i}-MS1", "fixture_id": i, "oran": o, "deger": 0.03} for i, o in [(1, 1.8), (2, 1.9)]]


def test_claude_hatali_secimi_duzeltir():
    kotu = {"secimler": [{"aday_id": "9-MS1", "yorum": "a"}], "baslik": "b", "gerekce_yoksa": ""}
    iyi = {"secimler": [{"aday_id": "1-MS1", "yorum": "a"}], "baslik": "b", "gerekce_yoksa": ""}
    c = SahteClaude([kotu, iyi])
    assert editor.claude_ile_sec({1: {}, 2: {}}, _adaylar(), AYAR, client=c) == iyi
    assert len(c.cagrilar) == 2
    assert c.cagrilar[0]["model"] == AYAR.claude_model
    assert c.cagrilar[0]["output_config"]["format"]["type"] == "json_schema"
    assert "Okänt aday_id" in c.cagrilar[1]["messages"][-1]["content"]


def test_claude_pas_gecebilir():
    pas = {"secimler": [], "baslik": "", "gerekce_yoksa": "Inget värde"}
    assert editor.claude_ile_sec({1: {}, 2: {}}, _adaylar(), AYAR, client=SahteClaude([pas])) == pas


def test_dogrulama():
    a = {x["aday_id"]: x for x in _adaylar()}
    a["1-UST25"] = {"aday_id": "1-UST25", "fixture_id": 1, "oran": 1.8}
    assert "samma match" in editor.secimi_dogrula([{"aday_id": "1-MS1"}, {"aday_id": "1-UST25"}], a, AYAR)
    assert editor.secimi_dogrula([{"aday_id": "1-MS1"}, {"aday_id": "2-MS1"}], a, AYAR) is None


def test_demo_uctan_uca(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["demo"]) == 0
    cikti = capsys.readouterr().out
    assert "DAGENS SPEL" in cikti and "Resultat: 2 av 3 vann" in cikti
    assert "1xBet" not in cikti  # lisanssız bahisçi asla önerilmez
    assert "Djurgården" not in cikti.split("TWEET #1")[1]  # değersiz maç seçilmez
