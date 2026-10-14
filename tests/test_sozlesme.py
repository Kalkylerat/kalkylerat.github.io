"""SOZLESME.md'deki her madde için bir test. Bu dosyadaki bir test kırılırsa üzerinde anlaşılmış bir kural
bozulmuştur: kodu kurala uydurun (ya da önce SOZLESME.md'de kuralı birlikte değiştirin)."""

import json
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


def test_A4_istatistik_kendi_kategorisinden():
    def takim(ic, dis, a, y, s5a=None, s5y=None):
        return {"oynanan_ic": ic, "oynanan_dis": dis, "atilan_ic_ort": a, "yenilen_ic_ort": y, "atilan_dis_ort": a + 0.5,
                "yenilen_dis_ort": y + 0.5, "son5_atilan_ort": s5a or a, "son5_yenilen_ort": s5y or y}
    # Ev sahibi iç saha, deplasman takımı dış saha ortalamasıyla ölçülür
    goller, kaynak = analiz.istatistik_modeli({"ev": takim(4, 4, 2.0, 1.0), "dep": takim(4, 4, 1.0, 1.0)})
    assert kaynak == "lig" and goller == ((2.0 + 1.5) / 2, (1.5 + 1.0) / 2)
    # 13 Ekim: Şampiyonlar Ligi'nde 1–2 maç; "son 5 maç" ortalaması (aynı turnuvadan) yerine geçmez
    assert analiz.istatistik_modeli({"ev": takim(1, 1, 0.5, 3.0, 0.0, 3.0), "dep": takim(1, 1, 3.0, 0.5, 3.0, 1.0)}) is None
    # Toplam maç yetse de kategori (ev sahibinin iç saha / deplasmanın dış saha maçı) yetmezse istatistik yok
    assert analiz.istatistik_modeli({"ev": takim(2, 5, 1.5, 1.0), "dep": takim(4, 4, 1.2, 1.1)}) is None
    assert analiz.istatistik_modeli({"ev": takim(4, 4, 1.5, 1.0), "dep": takim(5, 2, 1.2, 1.1)}) is None


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


def test_A6_uzun_takim_adi_yuzdeyi_yutmaz(monkeypatch):
    yazilan = []
    asil = gorsel.ImageDraw.ImageDraw.text
    monkeypatch.setattr(gorsel.ImageDraw.ImageDraw, "text", lambda self, xy, t, *a, **k: (yazilan.append(t), asil(self, xy, t, *a, **k)))
    uzun = {**FRA, "ev": "Borussia Mönchengladbach", "dep": "Wolverhampton Wanderers"}
    gorsel.analiz_karti(uzun, "21:00 CEST")
    for k in ("MS1", "MSX", "MS2"):  # 13 Ekim: "Manchester United …" kartta yüzdeyi kesiyordu
        assert any(t.endswith(f'{round(100 * uzun["p"][k])}%') for t in yazilan), k


def test_A7_mac_sonu_olan_ve_mac_oncesi_yuzdesi():
    takip = etkilesim.analiz_takip_tweeti(FRA, "1-2")
    assert "pre-match chance of what happened" in takip and "Italy win" in takip and "Score 1-2" in takip


def test_A7_mac_sonunda_gercek_xg_varsa_yazilir_yoksa_satir_yok():
    from bot import football
    xg = etkilesim.analiz_takip_tweeti(FRA, "1-2", None, (1.42, 0.87))
    assert "📐 Expected goals from shots: 1.4 – 0.9" in xg and "pre-match chance of what happened" in xg
    assert not denetci.KISALTMA.search(xg) and tweets.uzunluk(xg) <= tweets.LIMIT and xg.endswith(tweets.ANSVAR)
    assert "Expected goals from shots" not in etkilesim.analiz_takip_tweeti(FRA, "1-2")

    class Api:  # API-Football fixtures/statistics: deplasman önce gelse de ev/dep doğru eşleşir; boş değer = yok
        def __init__(self, kayit): self.kayit = kayit
        def get(self, yol, **k): return self.kayit
    st = lambda ad, v: {"team": {"name": ad}, "statistics": [{"type": "Corner Kicks", "value": 4}, {"type": "expected_goals", "value": v}]}
    assert football.mac_xg(Api([st("Italy", "0.87"), st("France", "1.42")]), 1, "France") == (1.42, 0.87)
    assert football.mac_xg(Api([st("France", None), st("Italy", "0.87")]), 1, "France") is None
    assert football.mac_xg(Api([st("France", "1.4")]), 1, "France") is None
    assert football.mac_xg(Api([st("France", "abc"), st("Italy", "0.87")]), 1, "France") is None

    class X:
        def __init__(self): self.giden = []
        def gonder(self, metin, **k): self.giden.append(metin); return "9"
    sonuc = lambda m: {m[0]["fixture_id"]: {"durum": "bitti", "skor": (1, 2)}}
    simdi = datetime(2026, 10, 3, 21, 0, tzinfo=UTC)
    for xg_getir, beklenen in ((lambda a: (1.42, 0.87), [1.42, 0.87]), (lambda a: None, None),
                               (lambda a: (_ for _ in ()).throw(RuntimeError("API")), None)):
        gun = {"analizler": [FRA], "etkilesim": {"analiz_0": {"durum": "paylasildi", "tweet_id": "5"}}}
        x = X()
        assert etkilesim.analiz_takibi(gun, AYAR, x, simdi, sonuc, yaz=lambda *_: None, xg_getir=xg_getir) == 1
        assert gun["etkilesim"]["analiz_0"]["takip"].get("xg") == beklenen  # xG alınamasa da maç sonu postu çıkar
        assert ("Expected goals from shots" in x.giden[0]) == bool(beklenen)
    # Direktör "xG" kısaltmasını yazarsa şablon gider (A5)
    gun, x = {"analizler": [FRA], "etkilesim": {"analiz_0": {"durum": "paylasildi", "tweet_id": "5"}}}, X()
    etkilesim.analiz_takibi(gun, AYAR, x, simdi, sonuc, yaz=lambda *_: None, xg_getir=lambda a: (1.42, 0.87),
                            yazar=lambda tur, olg, sablon: "France 1–2 Italy, xG 1.4 – 0.9\n18+ | Play responsibly")
    assert "xG" not in x.giden[0] and "Expected goals from shots: 1.4 – 0.9" in x.giden[0]


def test_A8_link_bahis_kesinlik_yok_18_arti_ile_biter():
    for metin in (etkilesim.analiz_tweeti(FRA, AYAR), etkilesim.tablo_tweeti({"tarih": "x"}, [FRA, BEL], AYAR),
                  etkilesim.analiz_takip_tweeti(FRA, "0-0"), etkilesim.tablo_mac_sonu_tweeti(FRA, 0, 0)):
        assert metin.rstrip().endswith(tweets.ANSVAR) and tweets.uzunluk(metin) <= 280
    for kotu in ("visit https://x.io", "a lock tonight", "bet365 odds"):
        assert denetci.analiz_kontrolu("analiz", kotu + "\n" + tweets.ANSVAR, [], AYAR)


def test_A9_haftalik_karne_kayittan_kaybedenler_dahil():
    a = mac(1, "France", "Italy")
    gunler = []
    for n in range(12):  # 12 kart, her biri 3 ana çağrı: 36; yarısı oldu
        gun = f"2026-10-{5 + n % 7:02d}"
        g = next((x for x in gunler if x["tarih"] == gun), None) or {"tarih": gun, "konsept": "analiz", "analizler": [], "etkilesim": {}}
        if g not in gunler:
            gunler.append(g)
        g["analizler"].append(a)
        g["etkilesim"][f"analiz_{len(g['analizler']) - 1}"] = {"durum": "paylasildi", "takip": {
            "durum": "paylasildi", "isabet": [n % 2 == 0] * 3,
            "brier": {"piyasa": 0.4, "istatistik": 0.5 if n < 9 else 0.3}}}
    gunler.append({"tarih": "2026-10-12", "konsept": "analiz", "analizler": [a], "etkilesim": {
        "analiz_0": {"durum": "paylasildi", "takip": {"durum": "paylasildi", "isabet": [True] * 3}}}})  # bu hafta değil
    oz = etkilesim.hafta_ozeti(gunler, "2026-10-12")
    assert (oz["ilk"], oz["son"], oz["adet"], oz["olan"]) == ("2026-10-05", "2026-10-11", 36, 18)
    assert (oz["kiyas"], oz["oran_yakin"]) == (12, 9)
    assert oz["ort_p"] == round(sum(c["p"] for c in analiz.manset(a)) / 3, 3)
    metin = etkilesim.hafta_tweeti(oz)
    assert "50% (18 of 36)" in metin and "75% of games (9 of 12)" in metin
    assert tweets.uzunluk(metin) <= tweets.LIMIT and metin.endswith(tweets.ANSVAR)
    assert not denetci._SECIM_DILI.search(metin) and not denetci._LINK.search(metin) and not denetci.KISALTMA.search(metin)
    for satir in metin.splitlines():
        if satir[:1] in "🎯📈⚖" and re.search(r"\d", satir):
            assert "%" in satir
    # Az veriyle karne yok; plan yalnızca karne varsa (direktör yazmaz: rakam kayıttan)
    assert etkilesim.hafta_ozeti(gunler[:2], "2026-10-12") is None
    pazartesi = {"tarih": "2026-10-12", "konsept": "analiz", "olusturma": "2026-10-12T05:20:00+00:00", "hafta_ozeti": oz}
    assert "hafta" in [t for t, _, _ in etkilesim._plan(pazartesi)]
    assert "hafta" not in [t for t, _, _ in etkilesim._plan({**pazartesi, "hafta_ozeti": None})]

    class X:
        def __init__(self): self.giden = []
        def gonder(self, metin, **k): self.giden.append(metin); return "1"
    x, simdi = X(), datetime(2026, 10, 12, 10, 5, tzinfo=UTC)
    gun = {**pazartesi, "etkilesim": {t: {"durum": "atlandi"} for t, _, _ in etkilesim._plan(pazartesi) if t != "hafta"}}
    yazar = lambda *a: pytest.fail("karneyi direktör yazmaz")
    assert etkilesim.paylas(gun, AYAR, x, simdi, yaz=lambda *_: None, yazar=yazar) == "hafta"
    assert x.giden == [metin]


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
    # büyük maç olmayan kartın son saati yaklaşınca akşam bilgi postu da önüne geçemez (9 Ekim: kart kaçtı)
    alt = dict(mac(2, "West Ham", "QPR", saat="19:00", lig="Championship"), lig_id=999)
    gun = dict(gun, analizler=[alt], etkilesim={})
    assert not analiz.onemli(alt)
    assert etkilesim.paylas(gun, AYAR, X(), datetime(2026, 10, 3, 18, 14, tzinfo=UTC), yaz=lambda m: None) == "analiz_0"


def test_B4_hafta_sonu_yogun_gun():
    assert config.yogun_mu(AYAR, "2026-10-03") and config.yogun_mu(AYAR, "2026-10-04")  # Cumartesi, Pazar
    assert not config.yogun_mu(AYAR, "2026-10-05")
    assert config.yogun_mu(AYAR, "2026-10-05", {"yogun": True})  # hafta içi maç çoksa da yoğun
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
    # analiz her gün 07:17 (İsveç) planlı: 05:30 UTC'de henüz alarm yok, 06:30 UTC'de var (hafta içi de)
    assert not any("sabah analizi" in m for _, m in saglik.sorunlar([], datetime(2026, 10, 5, 5, 30, tzinfo=UTC), AYAR))
    assert any("sabah analizi" in m for _, m in saglik.sorunlar([], datetime(2026, 10, 5, 6, 30, tzinfo=UTC), AYAR))
    wf = (ROOT / ".github/workflows/kalkylerat.yml").read_text()
    assert 'cron: "17 5 * * *"' in wf and config.SABAH_YEREL_DK == 7 * 60 + 17


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


def test_B7_hesap_sessiz_kalmaz():
    from dataclasses import replace
    ayar = replace(AYAR, yogun_gunler=(), yogun_hafta_sonu=False, yogun_ek_ligler=(128, 71, 239, 253))
    sakin = "2026-10-07"  # çarşamba, büyük maç yok

    def m(fid, saat, lig_id=128, lig="Liga Profesional"):
        return dict(mac(fid, f"Club{fid}", f"Rival{fid}", saat=saat, lig=lig), lig_id=lig_id,
                    baslama=f"{sakin}T{saat}:00+00:00")
    tum = [m(i, "19:00", lig, f"L{lig}") for i, lig in enumerate((128, 128, 71, 71, 239, 239, 253, 253), 1)] \
        + [m(20 + i, "19:30", 999, f"Alt{i}") for i in range(4)]
    gun = {"id": sakin, "tarih": sakin, "konsept": "analiz", "secimler": [], "analizler": [], "vitrin": [],
           "etkilesim": {"bilgi": {"durum": "paylasildi", "zaman": f"{sakin}T09:46:00+00:00"}}}
    # büyük maç olmayan günde de ek lig kartları (en fazla 6), alt lig kartı yok
    assert etkilesim.yogun_kartlari_ekle(gun, tum, ayar, datetime(2026, 10, 7, 9, 0, tzinfo=UTC)) == etkilesim.SAKIN_KART == 6
    assert all(a["lig_id"] != 999 for a in gun["analizler"])
    # akşam tablosu sakin günde 12:00 UTC'den
    assert etkilesim.aksam_tablosu_ekle(gun, tum, ayar, datetime(2026, 10, 7, 11, 0, tzinfo=UTC)) == 0
    assert etkilesim.aksam_tablosu_ekle(gun, tum, ayar, datetime(2026, 10, 7, 12, 30, tzinfo=UTC)) >= 4
    assert any(t == "tablo_aksam" for t, _, _ in etkilesim._plan(gun))
    # 16:00 UTC'den sonra, sabah/akşam tablosunda olmayan gece maçlarıyla ikinci tablo (akşam sessiz kalmasın)
    gece = [m(40 + i, "20:30", lig, f"G{lig}") for i, lig in enumerate((128, 71, 239, 253, 262))]
    assert etkilesim.gece_tablosu_ekle(gun, tum + gece, ayar, datetime(2026, 10, 7, 15, 0, tzinfo=UTC)) == 0
    assert etkilesim.gece_tablosu_ekle(gun, tum + gece, ayar, datetime(2026, 10, 7, 17, 0, tzinfo=UTC)) >= 4
    assert not {a["fixture_id"] for a in gun["tablo_gece"]} & {a["fixture_id"] for a in gun["tablo_aksam"]}
    assert any(t == "tablo_gece" for t, _, _ in etkilesim._plan(gun))
    assert etkilesim.gece_tablosu_ekle(gun, tum + gece, ayar, datetime(2026, 10, 7, 18, 0, tzinfo=UTC)) == 0  # bir kez
    # akşam ikinci bilgi postu (18:00–20:30 UTC), sabahkinden farklı konu
    bp = {t: (e, l) for t, e, l in etkilesim._plan(gun)}
    assert bp["bilgi_aksam"][0].hour == 18 and (bp["bilgi_aksam"][1].hour, bp["bilgi_aksam"][1].minute) == (20, 30)
    assert etkilesim.bilgi_tweeti(gun) != etkilesim.bilgi_tweeti(gun, kayma=1)
    # 3 saat sessizlik alarmı (gün yoğun olmasa da); gece alarm yok, yanıtlar da hareket sayılır
    def sessiz(saat, dakika=0):
        return [m for k, m in saglik.sorunlar([gun], datetime(2026, 10, 7, saat, dakika, tzinfo=UTC), ayar) if ":sessiz:" in k]
    assert not sessiz(12, 30) and sessiz(12, 50) and not sessiz(22, 0)
    gun["etkilesim"]["tablo_2"] = {"durum": "paylasildi", "zaman": f"{sakin}T08:08:00+00:00",
                                   "sonuclar": {"1": {"durum": "paylasildi", "zaman": f"{sakin}T12:40:00+00:00"}}}
    assert not sessiz(12, 50)

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


def test_D3_yorum_kiti_yalnizca_taslak(tmp_path, monkeypatch):
    from bot import yorum
    monkeypatch.setattr(yorum, "DOSYA", tmp_path / "yorumlar.json")

    class X:
        def __init__(self): self.sorular = []
        def ben(self): return "1", "kalkylerat"
        def bahsedenler(self, me, since_id=None, baslangic=None):
            self.sorular.append(since_id)
            return [t for t in ({"id": "11", "metin": "Why only 26% for United?", "yazar": "9", "kullanici": "fan",
                                 "bizim": "Atletico Madrid 52% · Draw 22% · Manchester United 26%"},
                                {"id": "10", "metin": "kendi yanıtımız", "yazar": "1", "kullanici": "kalkylerat", "bizim": None})
                    if since_id is None or int(t["id"]) > int(since_id)]
        def gonder(self, *a, **k): pytest.fail("yorum kiti hiçbir şey paylaşmaz")
        def sil(self, *a, **k): pytest.fail("yorum kiti hiçbir şey silmez")

    class GH:
        def __init__(self): self.issue, self.yorumlar = [], []
        def issue_ac(self, baslik, govde, etiket): self.issue.append((baslik, etiket)); return 7
        def yorum(self, no, mesaj): self.yorumlar.append((no, mesaj))

    x, gh, simdi = X(), GH(), datetime(2026, 10, 13, 14, 0, tzinfo=UTC)
    assert yorum.kontrol(x, gh, AYAR, simdi) == 1  # kendi postumuz bildirilmez
    assert gh.issue == [("💬 Yorumlar @kalkylerat 2026-10-13", "yorum-kiti")]
    no, mesaj = gh.yorumlar[0]
    assert no == 7 and "Why only 26% for United?" in mesaj and "https://x.com/i/web/status/11" in mesaj
    assert all(t in mesaj for t in yorum.YEDEK)  # Claude yoksa hazır kalıplar
    assert yorum.kontrol(x, gh, AYAR, simdi + timedelta(minutes=20)) == 0 and x.sorular == [None]  # 30 dk dolmadan sorulmaz
    assert yorum.kontrol(x, gh, AYAR, simdi + timedelta(minutes=35)) == 0 and x.sorular[-1] == "11"  # aynı yorum bir kez
    assert yorum.kontrol(x, gh, AYAR, simdi.replace(hour=23, minute=30)) == 0 and len(x.sorular) == 2  # gece sorulmaz
    # Taslak denetimi: link, etiket, seçim/kesinlik dili ve kaynakta olmayan sayı elenir
    kaynak = "Atletico Madrid 52% · Draw 22% · Manchester United 26%\nWhy only 26%?"
    assert yorum.uygun("Fair question. The market has United at 26%. How would you price it?", kaynak)
    for kotu in ("Our pick is United, trust me", "Lock it in: United 26%", "See kalkylerat.com", "United 61% for sure",
                 "#UCL United 26%", "We were right about it",
                 "Great point! The market has United at 26%.", "Interesting take on United",
                 "Our numbers have United at 26%.", "That says a lot about United"):  # robot gibi kalıplar da elenir
        assert not yorum.uygun(kotu, kaynak), kotu
    # Claude taslakları da aynı denetimden geçer; kurala uymayan düşer
    monkeypatch.setattr(direktor, "_cagir", lambda *a, **k: {"taslaklar": ["Our pick: United", "x" * 300,
                        "The market has United at 26%. How would you price it?"], "not": "Oranı soruyor.", "spam": False})
    t, not_, spam = yorum.taslaklar({"metin": "Why only 26%?", "bizim": kaynak}, "kalkylerat", client=object(), ayar=AYAR)
    assert t == ["The market has United at 26%. How would you price it?"] and not_ == "Oranı soruyor." and not spam


def test_D3_yorum_firsatlari_yalnizca_taslak(tmp_path, monkeypatch):
    from bot import firsat
    monkeypatch.setattr(firsat, "DOSYA", tmp_path / "firsatlar.json")
    monkeypatch.setattr(firsat, "ayar_yukle", lambda: firsat.BuyumeAyar(gunluk_yorum=3, saatler=[10, 16]))
    simdi = datetime(2026, 10, 3, 10, 5, tzinfo=UTC)
    zaman = lambda dk: (simdi - timedelta(minutes=dk)).isoformat().replace("+00:00", "Z")
    postlar = [
        {"id": "1", "metin": "France have won 9 of their last 10 at home.", "kullanici": "OptaJoe", "zaman": zaman(30),
         "metrik": {"like_count": 900, "reply_count": 80, "retweet_count": 100}},
        {"id": "2", "metin": "Transfer news: big deal close", "kullanici": "FabrizioRomano", "zaman": zaman(20),
         "metrik": {"like_count": 5000, "reply_count": 400, "retweet_count": 800}},
        {"id": "3", "metin": "Sad news about a former player", "kullanici": "BBCSport", "zaman": zaman(10),
         "metrik": {"like_count": 100, "reply_count": 5, "retweet_count": 1}},
        {"id": "4", "metin": "Internationale fans in the stands", "kullanici": "goal", "zaman": zaman(10),
         "metrik": {"like_count": 50, "reply_count": 2, "retweet_count": 1}}]

    class X:
        def __init__(self): self.aramalar = 0
        def ara(self, sorgu, baslangic, adet): self.aramalar += 1; return postlar
        def gonder(self, *a, **k): pytest.fail("fırsat ajanı hiçbir şey paylaşmaz")

    class GH:
        def __init__(self): self.issue, self.yorumlar = [], []
        def issue_ac(self, baslik, govde, etiket): self.issue.append(etiket); return 3
        def yorum(self, no, mesaj): self.yorumlar.append(mesaj)

    def cagir(client, modeller, sistem, icerik, sema, max_tokens):
        post = json.loads(icerik)["their_post"]
        if post.startswith("Sad"):
            return {"uygun": False, "taslaklar": []}
        if "France" in post:  # bizim kartın rakamı geçer; uydurma rakam ve tanıtım elenir
            return {"uygun": True, "taslaklar": ["Fits our numbers too: France 47% to win this one. Strong home record.",
                                                 "France 99% for sure, follow us", "Is 47% too low for France?"]}
        return {"uygun": True, "taslaklar": ["Big one if it happens.", "Who wins more from this deal?"]}
    monkeypatch.setattr(direktor, "_cagir", cagir)
    gun = {"analizler": [mac(1, "France", "Italy", saat="19:00")]}
    gun["analizler"][0]["p"] = {**gun["analizler"][0]["p"], "MS1": 0.47}
    x, gh = X(), GH()
    assert firsat.kontrol(x, gh, AYAR, gun, simdi, client=object()) == 2  # 3/2 arama → bu saatte 2
    assert gh.issue == ["yorum-firsatlari"] and len(gh.yorumlar) == 1
    m = gh.yorumlar[0]
    assert m.index("x.com/OptaJoe/status/1") < m.index("x.com/FabrizioRomano/status/2")  # bizim maçı geçen önce
    assert "France 47% to win" in m and "99%" not in m and "follow us" not in m and "status/3" not in m
    # Tek dokunuşla cevap: X cevap penceresi taslak yazılı açılır (kopyalama yok); gönderen sahibi
    from urllib.parse import parse_qs, urlparse
    linkler = re.findall(r"\((https://x\.com/intent/tweet\?[^)]+)\)", m)
    q = parse_qs(urlparse(linkler[0]).query)
    assert q["in_reply_to"] == ["1"] and q["text"][0].startswith("Fits our numbers too: France 47%")
    assert "kalkylerat/status" not in m  # kart postu paylaşılmadıysa kartlı seçenek yok
    assert firsat.kontrol(x, gh, AYAR, gun, simdi + timedelta(minutes=30), client=object()) == 0 and x.aramalar == 1
    # 16:00: görülenler (1, 2) tekrar gelmez; 3 uygunsuz (üzücü haber); 4 gelir; günlük sınır (3) doldu
    assert firsat.kontrol(x, gh, AYAR, gun, simdi.replace(hour=16), client=object()) == 1
    assert "status/4" in gh.yorumlar[1] and "status/1" not in gh.yorumlar[1] and "status/3" not in gh.yorumlar[1]
    assert firsat.kontrol(x, gh, AYAR, gun, simdi.replace(hour=18), client=object()) == 0 and x.aramalar == 2
    assert firsat.eslesen_mac("Internationale fans", [mac(2, "Inter", "Milan")]) is None
    # 14 Ekim: postun konusu Man City–PSG; sonradan anılan "Real Madrid" Roma–Real kartını eşleştirmemeli
    kartlar = [mac(3, "AS Roma", "Real Madrid"), mac(4, "Manchester City", "Paris Saint Germain")]
    metin = "Manchester City are struggling to sell out their clash against PSG, despite revenues above Real Madrid."
    assert firsat.eslesen_mac(metin, kartlar)["ev"] == "Manchester City"
    assert firsat.eslesen_mac("Real Madrid travel to Rome tonight", kartlar)["ev"] == "AS Roma"
    assert firsat.kontrol(x, gh, AYAR, gun, simdi, client=None) == 0  # Claude yoksa taslaksız fırsat gönderilmez
    # Kart postumuz paylaşıldıysa "🖼️ Kartımızla" seçeneği o postun adresini cevaba ekler
    gun["etkilesim"] = {"analiz_0": {"durum": "paylasildi", "tweet_id": "777"}}
    assert firsat.kart_postu(gun, gun["analizler"][0]) == "https://x.com/kalkylerat/status/777"
    kartli = firsat.bildirim(postlar[0], gun["analizler"][0], ["Nice stat."], 1, firsat.kart_postu(gun, gun["analizler"][0]))
    assert "🖼️ Kartımızla" in kartli and parse_qs(urlparse(re.findall(r"\((https://x\.com/intent/tweet\?[^)]+)\)", kartli)[-1]).query)["text"] == ["Nice stat.\n\nhttps://x.com/kalkylerat/status/777"]
    assert len(firsat.sorgu(firsat.BuyumeAyar().hesaplar * 3)) <= 512


def test_D3_mr_likely_yorum_firsatlari(tmp_path, monkeypatch):
    from bot import firsat
    monkeypatch.setattr(firsat, "DOSYA", tmp_path / "firsatlar.json")
    # 14 Ekim sabahının eski kayıt biçimi taşınır; görülen postlar iki hesapta ortak
    firsat.kaydet({"tarih": "2026-10-03", "gonderilen": 2, "aramalar": [10], "gorulen": ["1"], "issue": {"tarih": "2026-10-03", "no": 63}})
    monkeypatch.setattr(firsat, "ayar_yukle", lambda: firsat.BuyumeAyar(likely_gunluk_yorum=2, likely_saatler=[11]))
    simdi = datetime(2026, 10, 3, 11, 5, tzinfo=UTC)
    z = (simdi - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    postlar = [{"id": "1", "metin": "France v Italy team news", "kullanici": "OptaJoe", "zaman": z, "metrik": {"like_count": 900}},
               {"id": "2", "metin": "France look sharp in training", "kullanici": "goal", "zaman": z, "metrik": {"like_count": 50}},
               {"id": "3", "metin": "Belgium fans arrive", "kullanici": "433", "zaman": z, "metrik": {"like_count": 40}}]

    class X:
        def ara(self, *a, **k): return postlar
        def gonder(self, *a, **k): pytest.fail("Mr. Likely fırsat ajanı hiçbir şey paylaşmaz")

    class GH:
        def __init__(self): self.issue, self.yorumlar = [], []
        def issue_ac(self, baslik, govde, etiket): self.issue.append((baslik, etiket, govde)); return 8
        def yorum(self, no, mesaj): self.yorumlar.append(mesaj)

    sistemler = []
    def cagir(client, modeller, sistem, icerik, sema, max_tokens):
        sistemler.append(sistem)
        if "in_my_coupon_today" in icerik:
            return {"uygun": True, "taslaklar": ["it's one of my legs today, so naturally I'm a bit nervous",
                                                 "Tail my coupon, France 47%", "Who starts up front for France?"]}
        return {"uygun": True, "taslaklar": ["Belgium fans never miss one, fair play"]}
    monkeypatch.setattr(direktor, "_cagir", cagir)
    fra = mac(1, "France", "Italy", saat="19:00")
    kupon = {"ad": "gunun-kuponu", "tweet_id": "555", "durum": "bekliyor",
             "ayaklar": [{"fixture_id": 1, "ev": "France", "dep": "Italy", "etiket": "Double chance 1X"}]}
    gh = GH()
    n = firsat.kontrol(X(), gh, AYAR, {"analizler": [fra, mac(2, "Belgium", "Türkiye", saat="19:00")]}, simdi,
                       client=object(), hesap="likely", kuponlar=[kupon], kullanici="Mrlikelyx")
    assert n == 2 and gh.issue[0][1] == "yorum-firsatlari-likely" and "Mr. Likely hesabından" in gh.issue[0][2]
    m = gh.yorumlar[0]
    assert "status/1" not in m  # @kalkylerat'a önerilmiş post Mr. Likely'ye önerilmez
    assert "nervous" in m and "Tail my coupon" not in m and "🎩 Kuponla" in m
    assert "https%3A%2F%2Fx.com%2FMrlikelyx%2Fstatus%2F555" in m  # kupon postu cevaba eklenir
    assert m.count("🎩 Kuponla") == 1  # kupon ayağı olmayan maçta (Belçika) kuponla seçeneği yok
    assert all('Mr. Likely speaks as "I"' in s_ for s_ in sistemler)
    veri = firsat.yukle()
    assert veri["kalkylerat"]["issue"]["no"] == 63 and veri["likely"]["gonderilen"] == 2 and {"1", "2", "3"} <= set(veri["gorulen"])


def test_D3_ayni_saatin_aramasi_iki_hesaba_bir_kez(tmp_path, monkeypatch):
    from bot import firsat
    monkeypatch.setattr(firsat, "DOSYA", tmp_path / "firsatlar.json")
    monkeypatch.setattr(firsat, "ayar_yukle", lambda: firsat.BuyumeAyar(gunluk_yorum=4, likely_gunluk_yorum=4, saatler=[10], likely_saatler=[10]))
    simdi = datetime(2026, 10, 3, 10, 5, tzinfo=UTC)
    z = (simdi - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    postlar = [{"id": str(i), "metin": f"post {i}", "kullanici": "goal", "zaman": z, "metrik": {"like_count": 100 - i}} for i in range(6)]

    class X:
        aramalar = 0
        def ara(self, *a, **k): X.aramalar += 1; return postlar

    class GH:
        def issue_ac(self, *a): return 1
        def yorum(self, no, mesaj): self.mesaj = mesaj
    monkeypatch.setattr(direktor, "_cagir", lambda *a, **k: {"uygun": True, "taslaklar": ["fair play to them"]})
    gh1, gh2 = GH(), GH()
    assert firsat.kontrol(X(), gh1, AYAR, None, simdi, client=object()) == 4
    assert firsat.kontrol(X(), gh2, AYAR, None, simdi, client=object(), hesap="likely") == 2  # kalan 2 post
    assert X.aramalar == 1  # ücret bir kez
    assert not set(re.findall(r"status/(\d)\)", gh1.mesaj)) & set(re.findall(r"status/(\d)\)", gh2.mesaj))


def test_D4_topluluga_yalnizca_tablo_ve_kiyas():
    kaynak = (ROOT / "bot/etkilesim.py").read_text()
    assert kaynak.count("_gonder(x, ayar, metin, yaz") == 2  # tablo ve ayrışma (kıyas) postları
