"""SOZLESME.md'deki her madde için bir test. Bu dosyadaki bir test kırılırsa üzerinde anlaşılmış bir kural
bozulmuştur: kodu kurala uydurun (ya da önce SOZLESME.md'de kuralı birlikte değiştirin)."""

import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bot import analiz, config, denetci, direktor, etkilesim, gorsel, model, saglik, tweets

AYAR = config.yukle()
ROOT = Path(__file__).resolve().parent.parent
UTC = timezone.utc


def mac(fid, ev, dep, saat="18:45", lig="UEFA Nations League", gol=(1.6, 1.0), kars=True):
    p = {k: round(v, 3) for k, v in model.model_olasiliklari(*gol).items()}
    k = [{"pazar": "UST25", "ad": "Over 2.5 goals", "piyasa": p["UST25"], "istatistik": round(p["UST25"] + 0.15, 3)},
         {"pazar": "MS1", "ad": f"{ev} win", "piyasa": p["MS1"], "istatistik": round(p["MS1"] - 0.05, 3)}] if kars else []
    return {"fixture_id": fid, "ev": ev, "dep": dep, "lig": lig, "ulke": "", "lig_id": AYAR.ligler[0], "guven": "yuksek",
            "baslama": f"2026-10-03T{saat}:00+00:00", "beklenen_gol": list(gol), "p": p,
            "skorlar": analiz._skorlar(*gol), "karsilastirma": k, "kaynak": "piyasa",
            "istatistik_kaynak": "son5" if kars else None}


FRA, BEL, KAZ = mac(1, "France", "Italy"), mac(2, "Belgium", "Türkiye"), mac(3, "Kazakhstan", "Moldova", kars=False)


# ---------- A. İçerik ----------

def test_A1_adi_gecen_her_macin_yuzdeleri_var():
    metin = etkilesim.tablo_tweeti({"tarih": "2026-10-03", "analiz_sayisi": 142}, [FRA, BEL], AYAR)
    for blok in metin.split("🆚")[1:]:
        assert blok.split("\n\n")[0].count("%") >= 2
    yuzdesiz = metin.replace("💬", "🆚 Belgium v Türkiye\n\n💬")
    assert any("yüzdeleri yok" in h for h in denetci.analiz_kontrolu("tablo", yuzdesiz, [FRA, BEL], AYAR))


def test_A2_rakamlar_kayitla_ayni_direktor_dusuremez_uyduramaz():
    sablon = etkilesim.analiz_tweeti(FRA, AYAR)
    yuzdeler = re.findall(r"\d+%", sablon)
    assert not direktor.yuzdeler_tam(sablon.replace(yuzdeler[0], ""), sablon)
    assert not direktor.sayilar_dogru("France 77% tonight", sablon)
    yanlis = sablon.replace(yuzdeler[0], "99%")
    assert any("kayıtta olmayan" in h for h in denetci.analiz_kontrolu("analiz", yanlis, [FRA], AYAR))


def test_A3_olasilik_secim_degil():
    kart = etkilesim.analiz_tweeti(FRA, AYAR)
    p = FRA["p"]
    assert f"France {round(100 * p['MS1'])}% · Draw {round(100 * p['MSX'])}% · Italy {round(100 * p['MS2'])}%" in kart
    assert f"Under {round(100 * p['ALT25'])}%" in kart and "not picks" in kart.lower()
    takip = etkilesim.analiz_takip_tweeti(FRA, "1-2")
    assert "✅" not in takip and "❌" not in takip and "not picks" in takip.lower()
    for kotu in ("❌ France win", "We got it wrong", "our pick tonight"):
        assert denetci.analiz_kontrolu("analiz_sonuc", kotu + "\n" + tweets.ANSVAR, [FRA], AYAR)
    liste = etkilesim.tablo_tweeti({"tarih": "2026-10-03"}, [FRA, BEL], AYAR)  # liste şablonu da seçim dili taşımaz
    assert not denetci._SECIM_DILI.search(liste)
    assert denetci.analiz_kontrolu("tablo", liste.replace("Which % surprises you", "Which number looks wrong"), [FRA, BEL], AYAR)


def test_A4_oran_ve_istatistik_yan_yana():
    kart = etkilesim.analiz_tweeti(FRA, AYAR)
    assert "📈" in kart and ("Odds" in kart or "odds" in kart)
    assert "📈 Team stats:" in etkilesim.analiz_tweeti(KAZ, AYAR)  # istatistik yoksa nedeni yazılır
    yanit = etkilesim.tablo_mac_sonu_tweeti(FRA, 2, 1)
    assert "odds" in yanit and "stats" in yanit


@pytest.mark.parametrize("a", [FRA, BEL, KAZ])
def test_A5_yuzde_isareti_kisaltma_yok(a):
    for metin in (etkilesim.analiz_tweeti(a, AYAR), etkilesim.analiz_takip_tweeti(a, "2-2"),
                  etkilesim.tablo_tweeti({"tarih": "2026-10-03"}, [a, FRA], AYAR), etkilesim.tablo_mac_sonu_tweeti(a, 0, 0)):
        assert not re.search(r"\b(O|U)\d\.\d\b|\bBTTS\b", metin)
        for satir in metin.splitlines():
            if satir[:1] in "🏆⚽🥅" and re.search(r"\d", satir) and not re.search(r"\d–\d", satir):  # skor satırı hariç
                assert "%" in satir


def test_A5_bilgi_postlarinda_kisaltma_yok():
    for k in __import__("bot.bilgi", fromlist=["KONULAR"]).KONULAR:
        metin = " ".join(str(v) for v in k.values())
        assert not denetci.KISALTMA.search(metin), k["id"]
        assert not re.search(r"\b0\.\d+\b", metin), k["id"]  # olasılık ondalıkla değil yüzdeyle


def test_A6_gorselde_yuzdesiz_rakam_yok(monkeypatch):
    yazilan = []
    asil = gorsel.ImageDraw.ImageDraw.text
    monkeypatch.setattr(gorsel.ImageDraw.ImageDraw, "text", lambda self, xy, t, *a, **k: (yazilan.append(t), asil(self, xy, t, *a, **k)))
    gorsel.analiz_tablosu([FRA, BEL], "2026-10-03", ["20:45", "20:45"])
    for a in (FRA, BEL):
        assert f'{round(100 * a["skorlar"][0][1])}%' in yazilan  # en olası skorun yüzdesi de var
    assert not [t for t in yazilan if re.fullmatch(r"\d{1,3}", t.strip())]  # çıplak sayı yok


def test_A7_mac_sonu_olan_ve_mac_oncesi_yuzdesi():
    takip = etkilesim.analiz_takip_tweeti(FRA, "1-2")
    assert "pre-match chance of what happened" in takip and "Italy win" in takip and "Score 1-2" in takip


def test_A8_link_bahis_kesinlik_yok_18_arti_ile_biter():
    for metin in (etkilesim.analiz_tweeti(FRA, AYAR), etkilesim.tablo_tweeti({"tarih": "x"}, [FRA, BEL], AYAR),
                  etkilesim.analiz_takip_tweeti(FRA, "0-0"), etkilesim.tablo_mac_sonu_tweeti(FRA, 0, 0)):
        assert metin.rstrip().endswith(tweets.ANSVAR) and tweets.uzunluk(metin) <= 280
    for kotu in ("visit https://x.io", "a lock tonight", "bet365 odds"):
        assert denetci.analiz_kontrolu("analiz", kotu + "\n" + tweets.ANSVAR, [], AYAR)


# ---------- B. Zamanlama ----------

def test_B1_mac_sonu_dudukten_5_15_dk_sonra():
    assert etkilesim.TAKIP_GECIKME <= timedelta(hours=1, minutes=45)
    nobet = (ROOT / ".github/workflows/nobet.yml").read_text()
    assert '-ge 420 ]' in nobet  # nöbetçi botu 7 dakikada bir çalıştırır
    assert saglik.TAKIP_GECIKME <= timedelta(hours=2, minutes=20)  # geç kalırsa alarm


def test_B2_tablodaki_mac_bittikce_yanit():
    gun = {"tarih": "2026-10-03", "tablo": [FRA, mac(5, "Spain", "Czechia", saat="20:00")],
           "etkilesim": {"tablo": {"durum": "paylasildi", "tweet_id": "9", "zaman": "2026-10-03T08:00:00+00:00",
                                   "maclar": [1, 5]}}}

    class X:
        giden = []

        def gonder(self, metin, **k):
            self.giden.append(k)
            return "1"
    x = X()
    n = etkilesim.tablo_takibi(gun, AYAR, x, datetime(2026, 10, 3, 20, 45, tzinfo=UTC),
                               lambda l: {1: {"durum": "bitti", "skor": (2, 1)}})
    assert n == 1 and x.giden[0] == {"yanit": "9"}  # biten maç hemen, diğeri bitince


def test_B3_kart_bilgi_postundan_once():
    gun = {"id": "d", "tarih": "2026-10-03", "konsept": "analiz", "secimler": [], "sonuc": "analiz",
           "analizler": [mac(1, "Albacete", "Eibar", saat="12:00")], "vitrin": [], "etkilesim": {}}

    class X:
        def medya_yukle(self, png):
            return "m"

        def gonder(self, metin, **k):
            return "1"
    assert etkilesim.paylas(gun, AYAR, X(), datetime(2026, 10, 3, 9, 30, tzinfo=UTC), yaz=lambda m: None) == "analiz_0"


def test_B4_hafta_sonu_yogun_gun():
    assert config.yogun_mu(AYAR, "2026-10-03") and config.yogun_mu(AYAR, "2026-10-04")  # Cumartesi, Pazar
    assert not config.yogun_mu(AYAR, "2026-10-05")
    assert 13 <= AYAR.yogun_aralik_dk <= 15 and AYAR.gunluk_post_siniri <= 40 and AYAR.yogun_kart >= 20
    # kart penceresi 8 saat: öğle boşluğunda akşam maçının kartı paylaşılabilir
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "analizler": [mac(1, "France", "Italy", saat="18:45")]}
    erken, gec = next((e, l) for t, e, l in etkilesim._plan(gun) if t == "analiz_0")
    assert erken == datetime(2026, 10, 3, 10, 45, tzinfo=UTC) and gec == datetime(2026, 10, 3, 18, 10, tzinfo=UTC)
    # az post kaldıysa günün geri kalanına yayılır (en fazla 45 dk); son saati yakın post varken en kısa aralık
    gun["etkilesim"] = {}
    assert AYAR.yogun_aralik_dk < etkilesim.aralik_dk(gun, AYAR, datetime(2026, 10, 3, 11, 0, tzinfo=UTC)) <= 45
    assert etkilesim.aralik_dk(gun, AYAR, datetime(2026, 10, 3, 17, 30, tzinfo=UTC)) == AYAR.yogun_aralik_dk


def test_B5_sabah_analizi_yoksa_alarm():
    bulunan = dict(saglik.sorunlar([], datetime(2026, 10, 4, 10, 30, tzinfo=UTC), AYAR))
    assert any("sabah analizi" in m for m in bulunan.values())
    # hafta içi analiz 12:47 (İsveç) planlı: 10:30 UTC'de henüz alarm yok, 12:00 UTC'de var
    assert not any("sabah analizi" in m for _, m in saglik.sorunlar([], datetime(2026, 10, 5, 10, 30, tzinfo=UTC), AYAR))
    assert any("sabah analizi" in m for _, m in saglik.sorunlar([], datetime(2026, 10, 5, 12, 0, tzinfo=UTC), AYAR))


def test_B6_buyuk_maclar_kart_ve_tabloda():
    uluslar = [dict(mac(10 + i, f"Nation{i}", f"Rival{i}", saat="18:45"), lig_id=5) for i in range(8)]
    alt = [dict(mac(30 + i, f"Astur{i}", f"Mosconia{i}", saat="15:00", lig="Tercera"), lig_id=999) for i in range(4)]
    assert all(analiz.onemli(a) for a in uluslar) and not any(analiz.onemli(a) for a in alt)
    tablo = {a["fixture_id"] for a in analiz.tablo_secimi(alt + uluslar, AYAR.ligler)}
    assert tablo == {a["fixture_id"] for a in uluslar}  # Uluslar Ligi'nin hepsi; alt lig yer kalmadığı için yok
    kartlar = {a["fixture_id"] for a in analiz.one_cikanlar(alt + uluslar, AYAR.ligler, adet=10)}
    assert {a["fixture_id"] for a in uluslar} <= kartlar
    ek = analiz.ek_kart_secimi(uluslar, AYAR.ligler, [], set(), "2026-10-03T08:00:00+00:00", adet=20)
    assert len(ek) == 8  # yoğun günde lig sınırı büyük maçı dışarıda bırakmaz
    pl = [dict(mac(50 + i, f"Club{i}", f"Other{i}", saat="16:00", lig="Premier League"), lig_id=39) for i in range(6)]
    assert len(analiz.tablo_secimi(pl, AYAR.ligler)) == 6  # büyük ligde "lig başına 2" sınırı yok
    assert len(analiz.tablo_secimi(pl + uluslar + [dict(a, fixture_id=a["fixture_id"] + 100) for a in uluslar],
                                   AYAR.ligler)) == 15  # tablo en fazla 15 maç
    # liste metni büyük maçı anar; yalnızca alt lig maçını anan metni denetçi durdurur
    secilen = analiz.tablo_secimi(alt[:1] + uluslar[:2], AYAR.ligler)
    metin = etkilesim.tablo_tweeti({"tarih": "2026-10-03"}, secilen, AYAR)
    assert "Nation0 v Rival0" in metin and not denetci.analiz_kontrolu("tablo", metin, secilen, AYAR)
    kucuk = etkilesim.tablo_tweeti({"tarih": "2026-10-03"}, alt[:1], AYAR)
    assert any("büyük maç" in h for h in denetci.analiz_kontrolu("tablo", kucuk, secilen, AYAR))
    # sıralama: alt lig kartı büyük maç kartının önüne geçmez
    gun = {"id": "d", "tarih": "2026-10-03", "konsept": "analiz", "secimler": [], "sonuc": "analiz", "vitrin": [],
           "analizler": [dict(alt[0], baslama="2026-10-03T17:00:00+00:00"), uluslar[0]], "etkilesim": {}}

    class X:
        def medya_yukle(self, png):
            return "m"

        def gonder(self, metin, **k):
            return "1"
    assert etkilesim.paylas(gun, AYAR, X(), datetime(2026, 10, 3, 15, 0, tzinfo=UTC), yaz=lambda m: None) == "analiz_1"
    # kaçan büyük maç kartı alarm olur
    gun["etkilesim"] = {"analiz_1": {"durum": "atlandi"}}
    assert any("penceresi geçti" in m for _, m in saglik.sorunlar([gun], datetime(2026, 10, 3, 21, 0, tzinfo=UTC), AYAR))


# ---------- C. Güvenilirlik ----------

def test_C1_nobetci_7_dk_nabiz_20_dk_alarm():
    nobet = (ROOT / ".github/workflows/nobet.yml").read_text()
    assert '-ge 420 ]' in nobet and '-ge 1200 ]' in nobet and 'conclusion' in nobet and "cron:" in nobet


def test_C2_saglik_alarmi_kacan_ve_geciken():
    a = mac(1, "France", "Italy", saat="18:45")
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "analizler": [a, mac(2, "Belgium", "Türkiye", saat="10:00")],
           "etkilesim": {"analiz_0": {"durum": "paylasildi", "zaman": "2026-10-03T15:00:00+00:00"},
                         "analiz_1": {"durum": "atlandi"}}}
    bulunan = " ".join(m for _, m in saglik.sorunlar([gun], datetime(2026, 10, 3, 21, 10, tzinfo=UTC), AYAR))
    assert "maç sonu postu hâlâ çıkmadı" in bulunan and "penceresi geçti" in bulunan
    gun["etkilesim"]["analiz_0"]["takip"] = {"durum": "paylasildi", "zaman": "2026-10-03T21:20:00+00:00"}
    assert "düdükten ~" in " ".join(m for _, m in saglik.sorunlar([gun], datetime(2026, 10, 3, 21, 30, tzinfo=UTC), AYAR))


# ---------- D. X kuralları ----------

def test_D1_hashtag_sinirlari():
    assert tweets.LISTE_ETIKET_SINIRI <= 2
    assert len(tweets.etiket_satiri([("UEFA Nations League", "")], [("Belgium", "Türkiye")]).split()) <= 1
    for t in tweets.GENEL_ETIKETLER:
        assert t not in tweets.liste_etiketleri([("Premier League", "England")], [("Arsenal", "Leeds")])
    for a in (FRA, BEL, KAZ):
        assert len(re.findall(r"#\w+", etkilesim.analiz_tweeti(a, AYAR))) <= 1
    assert len(re.findall(r"#\w+", etkilesim.tablo_tweeti({"tarih": "x"}, [FRA, BEL], AYAR))) <= 2


def test_D2_ayni_metin_iki_kez_gitmez():
    k = etkilesim._TekrarKorumasi(type("X", (), {"gonder": lambda self, m, **kw: "1"})(),
                                  {"etkilesim": {"a": {"metin": "aynı"}}})
    with pytest.raises(RuntimeError):
        k.gonder("aynı")


def test_D3_baskalarina_otomatik_etkilesim_yok():
    kaynak = "\n".join(p.read_text() for p in (ROOT / "bot").glob("*.py"))
    for yasak in ("/likes", "/following", "/retweets", "/dm_conversations", "/blocks", "/bookmarks"):
        assert yasak not in kaynak, yasak  # beğeni, takip, RT, DM uç noktaları hiç çağrılmaz


def test_D4_topluluga_yalnizca_tablo_ve_kiyas():
    kaynak = (ROOT / "bot/etkilesim.py").read_text()
    assert kaynak.count("_gonder(x, ayar, metin, yaz") == 2  # tablo ve ayrışma (kıyas) postları
