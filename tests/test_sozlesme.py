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


def test_A2_aykiri_tek_site_fiyati_kullanilmaz():
    """14 Ekim: Mr. Likely günün kuponu X2'yi bir sitedeki 2.05'ten paylaştı; Bet365 dahil diğerleri ~1.50'ydi."""
    b = {"Bet365": {"CSX2": 1.50}, "Unibet": {"CSX2": 1.48}, "Betano": {"CSX2": 1.52}, "Bwin": {"CSX2": 2.05}}
    oran, _, detay = model.piyasa_oranlari(b, list(b), "en_iyi")["CSX2"]
    assert oran == 1.52 and "Bwin" not in detay
    ikili = {"Bet365": {"CSX2": 1.50}, "Bwin": {"CSX2": 2.05}}
    assert model.piyasa_oranlari(ikili, list(ikili), "en_iyi")["CSX2"][0] == 1.50
    # Gerçek, küçük fiyat farkı korunur (en iyi fiyat ortancadan %8'e kadar yüksek olabilir)
    normal = {"Bet365": {"MS1": 2.10}, "Unibet": {"MS1": 2.05}, "Betano": {"MS1": 2.20}}
    assert model.piyasa_oranlari(normal, list(normal), "en_iyi")["MS1"][0] == 2.20


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


def test_A4_yalnizca_oranlar_takim_istatistigi_gosterilmez():
    """22 Ekim 2026: istatistik kayıtta kalır ama kartta, postta, tabloda ve maç sonunda yok; ayrışma postu yok."""
    for metin in (etkilesim.analiz_tweeti(FRA, AYAR), etkilesim.analiz_tweeti(KAZ, AYAR),
                  etkilesim.tablo_mac_sonu_tweeti(FRA, 2, 1), etkilesim.analiz_takip_tweeti(FRA, "2-1"),
                  etkilesim.tablo_tweeti({"tarih": "2026-10-03"}, [FRA, BEL], AYAR)):
        assert "stats" not in metin.lower() and "📈 Team" not in metin
    assert "team_stats_vs_market" not in etkilesim.analiz_olgulari(FRA, AYAR)
    gun = {"tarih": "2026-10-03", "konsept": "analiz", "olusturma": "2026-10-03T05:20:00+00:00",
           "kiyas": [FRA, BEL, KAZ], "ayrisma": [FRA, BEL]}
    assert "ayrisma" not in [t for t, _, _ in etkilesim._plan(gun)]
    yazilan = []
    asil = gorsel.ImageDraw.ImageDraw.text
    gorsel.ImageDraw.ImageDraw.text = lambda self, xy, t, *a, **k: (yazilan.append(t), asil(self, xy, t, *a, **k))
    try:
        gorsel.analiz_karti(FRA, "20:45")
        gorsel.analiz_tablosu([FRA, BEL], "2026-10-03", ["20:45", "20:45"])
    finally:
        gorsel.ImageDraw.ImageDraw.text = asil
    assert not [t for t in yazilan if "stat" in t.lower() or "İSTATİSTİK" in t]


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
            "durum": "paylasildi", "isabet": [n % 2 == 0] * 3, "skor": "2-0" if n % 2 == 0 else "0-1"}}
    gunler.append({"tarih": "2026-10-12", "konsept": "analiz", "analizler": [a], "etkilesim": {
        "analiz_0": {"durum": "paylasildi", "takip": {"durum": "paylasildi", "isabet": [True] * 3}}}})  # bu hafta değil
    oz = etkilesim.hafta_ozeti(gunler, "2026-10-12")
    assert (oz["ilk"], oz["son"], oz["adet"], oz["olan"]) == ("2026-10-05", "2026-10-11", 36, 18)
    assert "kiyas" not in oz and "oran_yakin" not in oz  # oran vs istatistik karnesi 22 Ekim 2026'da kalktı (A4)
    assert oz["ort_p"] == round(sum(c["p"] for c in analiz.manset(a)) / 3, 3)
    metin = etkilesim.hafta_tweeti(oz)
    assert "50% (18 of 36)" in metin and "stats" not in metin
    # Kalibrasyon (22 Ekim 2026): bütün kayıttan bantlar; az çağrılı bant yazılmaz, kötü bant gizlenmez
    bol = [{"tarih": "2026-10-01", "konsept": "analiz", "analizler": [dict(a, fixture_id=1000 + i) for i in range(60)], "etkilesim": {
        f"analiz_{i}": {"takip": {"durum": "paylasildi", "skor": "2-0"}} for i in range(60)}}]
    kal = etkilesim.kalibrasyon(bol)
    assert kal and all(b["adet"] >= etkilesim.KALIBRASYON_MIN for b in kal)
    ms1 = next(b for b in kal if b["alt"] <= 100 * a["p"]["MS1"] <= b["ust"] + 1)
    assert ms1["olan"] >= 0.5  # France 60 kez kazandı: bant yüksek çıkar ve öyle yazılır
    kmetin = etkilesim.hafta_tweeti({**oz, "kalibrasyon": kal})
    assert "said → happened" in kmetin and "calls)" in kmetin and tweets.uzunluk(kmetin) <= tweets.LIMIT
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


def test_A10_durust_fiyat_her_sonuc_esit_secim_yok(monkeypatch):
    """22 Ekim 2026: kartta her sonucun adil oranı (1/ihtimal) ve bahisçi payı; tek sonuç öne çıkmaz, bahis çağrısı yok;
    gerçeklik notu kayıttan; ilk satır oranların hikâyesi."""
    yazilan = []
    asil = gorsel.ImageDraw.ImageDraw.text
    monkeypatch.setattr(gorsel.ImageDraw.ImageDraw, "text", lambda self, xy, t, *a, **k: (yazilan.append(t), asil(self, xy, t, *a, **k)))
    a = {**FRA, "marj": 0.052}
    gorsel.analiz_karti(a, "20:45")
    for k in ("MS1", "MSX", "MS2"):  # üç sonuç aynı biçimde, okunur boyda kendi kutusunda (25 Ekim 2026)
        assert analiz.adil_oran(a['p'][k]) in yazilan
    assert "FAIR ODDS" in yazilan and "Bookmakers' cut on this game: 5%" in yazilan
    yazilan.clear()
    gorsel.analiz_karti(FRA, "20:45")  # marj yoksa uydurulmaz
    assert "Bookmakers' cut: not available" in yazilan and not any("cut on this game" in t for t in yazilan)
    assert any(t.startswith("Fair odds = 1 ÷ chance") for t in yazilan)
    assert any(t.startswith("Reality check:") for t in yazilan)
    yasak = re.compile(r"\b(value|back|bet|play)\b", re.IGNORECASE)
    assert not [t for t in yazilan if yasak.search(t) and "not betting advice" not in t]
    assert analiz.adil_oran(0.43) == "2.33" and analiz.adil_oran(0.25) == "4.00"
    # bahisçi payı: o sabahki maç sonucu oranlarının ortancası
    assert analiz.bahisci_marji({"A": {"MS1": 2.0, "MSX": 3.4, "MS2": 3.8}, "B": {"MS1": 2.1, "MSX": 3.5, "MS2": 3.9},
                                 "C": {"MS1": 1.9}}) == round(sorted([1/2.0 + 1/3.4 + 1/3.8 - 1, 1/2.1 + 1/3.5 + 1/3.9 - 1])[0] / 2
                                                             + sorted([1/2.0 + 1/3.4 + 1/3.8 - 1, 1/2.1 + 1/3.5 + 1/3.9 - 1])[1] / 2, 4)
    assert analiz.bahisci_marji(None) is None
    metin = etkilesim.analiz_tweeti(FRA, AYAR)
    assert metin.startswith((analiz.hikaye(FRA)[1], analiz.hikaye_tek(FRA))) and not yasak.search(metin.replace(tweets.ANSVAR, ""))


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
    assert 13 <= AYAR.yogun_aralik_dk <= 15 and AYAR.gunluk_post_siniri <= 40 and AYAR.yogun_kart == 10
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
    # elle cevap taslakları: fırsatlar açıkken yorum fırsatları, kapalıyken yanıt kiti (ikisi birden gelmez)
    kod = (ROOT / "bot/__main__.py").read_text(encoding="utf-8")
    assert "not (firsat.ayar_yukle().aktif and firsat.ayar_yukle().gunluk_yorum > 0)" in kod and "kit.gonder(" in kod


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
    # 22 Ekim 2026: günde en fazla 10 kart; büyük maç fazlaysa önce taraftar etiketli kulüplerin maçları
    sakin = [dict(mac(70 + i, f"Calm{i}", f"Quiet{i}", saat="19:00", kars=False), lig_id=2) for i in range(12)]
    ayrisan = dict(mac(90, "Galatasaray", "Read", saat="20:00"), lig_id=2)
    assert analiz.populer(ayrisan) and not analiz.populer(sakin[0])
    assert 90 in {a["fixture_id"] for a in analiz.one_cikanlar(sakin + [ayrisan], AYAR.ligler)}  # sabah 5 kartında
    assert analiz.ek_kart_secimi(sakin + [ayrisan], AYAR.ligler, [], set(), "2026-10-03T08:00:00+00:00", adet=1)[0]["fixture_id"] == 90
    gun10 = {"tarih": "2026-10-03", "konsept": "analiz", "analizler": analiz.one_cikanlar(sakin + [ayrisan], AYAR.ligler)}
    etkilesim.yogun_kartlari_ekle(gun10, sakin + [ayrisan] + uluslar, AYAR, datetime(2026, 10, 3, 8, 0, tzinfo=UTC))
    assert len(gun10["analizler"]) == 10  # yoğun gün (Cumartesi): 21 büyük maçtan 10 kart
    assert len(analiz.tablo_secimi(sakin + uluslar, AYAR.ligler)) == 15  # kartı olmayan büyük maçlar tabloda
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


def test_D3_yorum_kiti_konusmanin_tamamini_ve_zamani_bilir(tmp_path, monkeypatch):
    """14 Ekim: taslak yalnızca bizim post + yorumu görünce oynanmamış maç için "izledin mi?" diye sordu."""
    from bot import yorum
    monkeypatch.setattr(yorum, "DOSYA", tmp_path / "yorumlar.json")

    class X:
        def __init__(self): self.post_okuma = []
        def ben(self): return "1", "kalkylerat"
        def bahsedenler(self, me, since_id=None, baslangic=None):
            return [{"id": "30", "metin": "They are just lying, all their tweets are City bashing", "yazar": "9",
                     "kullanici": "fan", "bizim": "Empty seats against the holders for France tonight", "ust_id": "20"}]
        def postlar(self, idler): self.post_okuma.append(idler); return {"20": {"metin": "France struggling to sell out v Italy", "kullanici": "Footballtweet"}}
        def gonder(self, *a, **k): pytest.fail("yorum kiti hiçbir şey paylaşmaz")

    class GH:
        def __init__(self): self.yorumlar = []
        def issue_ac(self, *a): return 1
        def yorum(self, no, mesaj): self.yorumlar.append(mesaj)

    giden = []
    def cagir(client, modeller, sistem, icerik, sema, max_tokens):
        giden.append((sistem, json.loads(icerik)))
        return {"taslaklar": ["Fair, that was a bit harsh from me. Hope it's a full house tonight"], "not": "itiraz", "spam": False}
    monkeypatch.setattr(direktor, "_cagir", cagir)
    simdi = datetime(2026, 10, 3, 14, 0, tzinfo=UTC)
    gun = {"analizler": [mac(1, "France", "Italy", saat="19:00")]}
    x, gh = X(), GH()
    assert yorum.kontrol(x, gh, AYAR, simdi, client=object(), gun=gun) == 1 and x.post_okuma == [["20"]]
    sistem, icerik = giden[0]
    kim = [a["who"] for a in icerik["conversation_in_order"]]
    assert kim == ["@Footballtweet (the post we replied to)", "@kalkylerat (us)", "@fan (the comment to answer now)"]
    assert icerik["now_utc"] == "2026-10-03 14:00" and icerik["match_in_this_conversation"]["status"] == "not started yet"
    assert "Never ask whether they watched a match that hasn't been" in sistem and "Never double down" in sistem
    assert "Asıl post (@Footballtweet)" in gh.yorumlar[0] and "harsh from me" in gh.yorumlar[0]


def test_D3_yorum_kiti_mr_likely_sesi_ve_kendi_postlarimiz(tmp_path, monkeypatch):
    from bot import yorum
    monkeypatch.setattr(yorum, "DOSYA", tmp_path / "yorumlar.json")
    # Mr. Likely'nin talimatı filtrenin elediği kelimeyi istemez; yedek cevaplar onun sesiyle ve kurala uygun
    assert not re.search(r"\bpicks?\b", yorum.LIKELY_NOTU.split("(Don't")[0])
    assert all(yorum.uygun(t, "") for t in yorum.YEDEK + yorum.YEDEK_LIKELY)
    assert yorum.taslaklar({"metin": "nice"}, "likely")[0] == yorum.YEDEK_LIKELY

    class X:
        def __init__(self): self.sorular = []
        def ben(self): return "1", "Mrlikelyx"
        def bahsedenler(self, me, since_id=None, baslangic=None):
            self.sorular.append(since_id)
            return [] if since_id == "40" else [{"id": "40", "metin": "kendi postumuz", "yazar": "1", "kullanici": "Mrlikelyx"}]
    x, simdi = X(), datetime(2026, 10, 3, 14, 0, tzinfo=UTC)
    assert yorum.kontrol(x, None, AYAR, simdi, hesap="likely") == 0
    assert yorum.kontrol(x, None, AYAR, simdi + timedelta(minutes=35), hesap="likely") == 0
    assert x.sorular == [None, "40"]  # kendi postumuz bir kez okunur, işaret ilerler


def test_D3_yorum_firsatlari_yalnizca_taslak(tmp_path, monkeypatch):
    from bot import firsat
    monkeypatch.setattr(firsat, "DOSYA", tmp_path / "firsatlar.json")
    monkeypatch.setattr(firsat, "ayar_yukle", lambda: firsat.BuyumeAyar(gunluk_yorum=3, saatler=[10, 16]))
    simdi = datetime(2026, 10, 3, 10, 5, tzinfo=UTC)
    zaman = lambda dk: (simdi - timedelta(minutes=dk)).isoformat().replace("+00:00", "Z")
    postlar = [
        {"id": "1", "metin": "France have won 9 of their last 10 at home ahead of tonight.", "kullanici": "OptaJoe", "zaman": zaman(30),
         "metrik": {"like_count": 900, "reply_count": 80, "retweet_count": 100}},
        {"id": "2", "metin": "Transfer news: big deal close", "kullanici": "FabrizioRomano", "zaman": zaman(20),
         "metrik": {"like_count": 5000, "reply_count": 400, "retweet_count": 800}},
        {"id": "3", "metin": "Sad news about a former player", "kullanici": "BBCSport", "zaman": zaman(10),
         "metrik": {"like_count": 100, "reply_count": 5, "retweet_count": 1}},
        {"id": "4", "metin": "Internationale fans in the stands", "kullanici": "goal", "zaman": zaman(10),
         "metrik": {"like_count": 50, "reply_count": 2, "retweet_count": 1}},
        {"id": "5", "metin": "Italy arrive in Paris for tonight's game against France", "kullanici": "goal", "zaman": zaman(10),
         "metrik": {"like_count": 60, "reply_count": 3, "retweet_count": 1}}]

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
    # 14 Ekim (sahibi): Kalkylerat yalnızca kartını paylaştığımız maçların postlarına cevap verir. Kart yoksa arama
    # da yapılmaz (ücret yok) ve saat sayılmaz.
    assert firsat.kontrol(x, gh, AYAR, gun, simdi, client=object()) == 0 and x.aramalar == 0 and not gh.yorumlar
    gun["etkilesim"] = {"analiz_0": {"durum": "paylasildi", "tweet_id": "777"}}
    kart = "https://x.com/kalkylerat/status/777"
    assert firsat.kontrol(x, gh, AYAR, gun, simdi, client=object()) == 2  # 3/2 arama → bu saatte 2
    assert gh.issue == ["yorum-firsatlari"] and len(gh.yorumlar) == 1
    m = gh.yorumlar[0]
    assert m.index("x.com/OptaJoe/status/1") < m.index("x.com/goal/status/5")
    assert "France 47% to win" in m and "99%" not in m and "follow us" not in m
    assert "status/2" not in m and "status/3" not in m and "status/4" not in m  # kartımızın maçı değil → yok
    # Kopyalama sayfası: her hazır cevap kart postumuzla; X intent yok (14 Ekim: Android cevabı ayrı post attı)
    from bot import kopya
    assert "intent/tweet" not in m and "https://kalkylerat.github.io/kit/2026-10-03/firsat-kalkylerat-10.html" in m
    sayfa = (kopya.KLASOR / "2026-10-03" / "firsat-kalkylerat-10.html").read_text(encoding="utf-8")
    veri = json.loads(re.search(r"const V = (\[.*?\]);", sayfa, re.S).group(1))
    assert veri[0] == {"metin": f"Fits our numbers too: France 47% to win this one. Strong home record.\n\n{kart}",
                       "url": "https://x.com/OptaJoe/status/1"}
    assert len(veri) == 4 and all(v["metin"].endswith(f"\n\n{kart}") for v in veri)  # 2 post × 2 taslak, hepsi kartlı
    assert "navigator.clipboard" in sayfa and "<script>alert" not in sayfa
    assert firsat.kontrol(x, gh, AYAR, gun, simdi + timedelta(minutes=30), client=object()) == 0 and x.aramalar == 1
    # 16:00: görülenler (1, 5) tekrar gelmez; kalanlar (transfer, üzücü haber, Internationale) kartımızın maçı değil
    assert firsat.kontrol(x, gh, AYAR, gun, simdi.replace(hour=16), client=object()) == 0
    assert x.aramalar == 2 and len(gh.yorumlar) == 1
    del gun["etkilesim"]
    assert firsat.eslesen_mac("Internationale fans", [mac(2, "Inter", "Milan")]) is None
    # 14 Ekim: postun konusu Man City–PSG; sonradan anılan "Real Madrid" Roma–Real kartını eşleştirmemeli
    kartlar = [mac(3, "AS Roma", "Real Madrid"), mac(4, "Manchester City", "Paris Saint Germain")]
    metin = "Manchester City are struggling to sell out their clash against PSG, despite revenues above Real Madrid."
    assert firsat.eslesen_mac(metin, kartlar)["ev"] == "Manchester City"
    assert firsat.eslesen_mac("Real Madrid travel to Rome tonight", kartlar)["ev"] == "AS Roma"
    # 14 Ekim 16:00: maçtan söz etmeyen postlar (Ballon d'Or, transfer) yan anılan takımla eşleşmez
    assert firsat.eslesen_mac("Natalie Portman held up four fingers after Barcelona's 4-0 win over Real Madrid", kartlar) is None
    assert firsat.eslesen_mac("Mastantuono scoring for River Plate. Real Madrid bought him for €45M after this.", kartlar) is None
    liverpool = [mac(5, "Lask Linz", "Liverpool")]
    assert firsat.eslesen_mac("Liverpool's starting XI against LASK has an average age of 24", liverpool)["ev"] == "Lask Linz"
    assert firsat.kontrol(x, gh, AYAR, gun, simdi, client=None) == 0  # Claude yoksa taslaksız fırsat gönderilmez
    # Kart postumuz paylaşıldıysa "🖼️ Kartımızla" seçeneği o postun adresini cevaba ekler
    gun["etkilesim"] = {"analiz_0": {"durum": "paylasildi", "tweet_id": "777"}}
    assert firsat.kart_postu(gun, gun["analizler"][0]) == "https://x.com/kalkylerat/status/777"
    kartli = firsat.bildirim(postlar[0], gun["analizler"][0], ["Nice stat."], 1, firsat.kart_postu(gun, gun["analizler"][0]))
    assert "🖼️ Kartımızla" in kartli and "(+ post bağlantısı)" in kartli
    from bot.yorum import sayfa_ogesi
    yorum_ = sayfa_ogesi("k", "p", "u", ["Nice stat."], [("🖼️", "Nice stat.\n\nhttps://x.com/kalkylerat/status/777")])
    assert yorum_["taslaklar"][-1][1] == "Nice stat.\n\nhttps://x.com/kalkylerat/status/777"  # kopyalanan metinde bağlantı var
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
               {"id": "2", "metin": "France look sharp in training before tonight", "kullanici": "goal", "zaman": z, "metrik": {"like_count": 50}},
               {"id": "3", "metin": "Belgium fans arrive for tonight's game", "kullanici": "433", "zaman": z, "metrik": {"like_count": 40}},
               # 25 Ekim 2026 (sahibinin isteği): videolu post ve bugünkü maçımızla eşleşmeyen post fırsat olmaz
               {"id": "4", "metin": "France v Italy: watch the training clip", "kullanici": "goal", "zaman": z,
                "metrik": {"like_count": 5000}, "video": True},
               {"id": "5", "metin": "Ballon d'Or shortlist is out", "kullanici": "goal", "zaman": z, "metrik": {"like_count": 9000}}]

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
    from bot import kopya
    sayfa = __import__("html").unescape((kopya.KLASOR / "2026-10-03" / "firsat-likely-11.html").read_text(encoding="utf-8"))
    assert "https://x.com/Mrlikelyx/status/555" in sayfa and "Önce X'te Mr. Likely hesabına geç" in sayfa  # kupon postu kopyalanan metinde
    assert m.count("🎩 Kuponla") == 1  # kupon ayağı olmayan maçta (Belçika) kuponla seçeneği yok
    assert all('Mr. Likely speaks as "I"' in s_ for s_ in sistemler)
    veri = firsat.yukle()
    assert veri["kalkylerat"]["issue"]["no"] == 63 and veri["likely"]["gonderilen"] == 2 and {"1", "2", "3"} <= set(veri["gorulen"])
    assert "status/4" not in m and "status/5" not in m  # videolu ve maçımızla eşleşmeyen post yok
    kutu = __import__("json").loads((kopya.KLASOR / "kutu.json").read_text(encoding="utf-8"))  # gelen kutusuna da düştü
    assert {o["url"] for o in kutu["ogeler"]} >= {"https://x.com/goal/status/2", "https://x.com/433/status/3"}
    assert all(o["hesap"] == "likely" and o["tur"] == "firsat" for o in kutu["ogeler"]) and "📥" in m


def test_D3_ayni_saatin_aramasi_iki_hesaba_bir_kez(tmp_path, monkeypatch):
    from bot import firsat
    monkeypatch.setattr(firsat, "DOSYA", tmp_path / "firsatlar.json")
    monkeypatch.setattr(firsat, "ayar_yukle", lambda: firsat.BuyumeAyar(gunluk_yorum=4, likely_gunluk_yorum=4, saatler=[10], likely_saatler=[10]))
    simdi = datetime(2026, 10, 3, 10, 5, tzinfo=UTC)
    z = (simdi - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    postlar = [{"id": str(i), "metin": f"France v Italy tonight, note {i}", "kullanici": "goal", "zaman": z,
                "metrik": {"like_count": 100 - i}} for i in range(6)]
    gun = {"analizler": [mac(1, "France", "Italy", saat="19:00")],
           "etkilesim": {"analiz_0": {"durum": "paylasildi", "tweet_id": "777"}}}

    class X:
        aramalar = 0
        def ara(self, *a, **k): X.aramalar += 1; return postlar

    class GH:
        def issue_ac(self, *a): return 1
        def yorum(self, no, mesaj): self.mesaj = mesaj
    monkeypatch.setattr(direktor, "_cagir", lambda *a, **k: {"uygun": True, "taslaklar": ["fair play to them"]})
    gh1, gh2 = GH(), GH()
    assert firsat.kontrol(X(), gh1, AYAR, gun, simdi, client=object()) == 4
    assert firsat.kontrol(X(), gh2, AYAR, gun, simdi, client=object(), hesap="likely") == 2  # kalan 2 post
    assert X.aramalar == 1  # ücret bir kez
    assert "**1.** Fair play to them" in gh1.mesaj  # taslak büyük harfle başlar
    assert "Önce X'te Mr. Likely hesabına geç" in gh2.mesaj and "hesabına geç" not in gh1.mesaj
    assert not set(re.findall(r"status/(\d)\)", gh1.mesaj)) & set(re.findall(r"status/(\d)\)", gh2.mesaj))


def test_D6_yorum_firsati_sayilari_ve_saatleri_sozlesmedeki_gibi():
    """Sahibiyle anlaşılan sayılar (14 Ekim): değiştirmek için önce SOZLESME.md D6."""
    from bot import firsat
    cfg = firsat.ayar_yukle()
    assert cfg.aktif and cfg.gunluk_yorum == 20 and cfg.likely_gunluk_yorum == 15  # sahibinin isteği 25 Ekim 2026
    assert cfg.saatler == [10, 12, 14, 16, 18, 20] and cfg.likely_saatler == cfg.saatler  # tek arama iki hesaba
    assert firsat.TAZE_SAAT == 3


def test_D4_topluluga_yalnizca_tablo_ve_kiyas():
    kaynak = (ROOT / "bot/etkilesim.py").read_text()
    assert kaynak.count("_gonder(x, ayar, metin, yaz") == 2  # tablo ve ayrışma (kıyas) postları


def test_D6_mr_likely_insan_sesi_yuzde_ve_takilma(monkeypatch):
    """15 Ekim 2026 (sahibinin isteği): Mr. Likely taslakları robotik değil (humanizer), bizim yüzdemize bağlı (kupona
    girmeyen maçta da), hakaretsiz sevimli takılma serbest; @kalkylerat takılmasız kalır."""
    from bot import firsat, yorum
    ln, kk = firsat.SISTEMLER["likely"], firsat.SISTEMLER["kalkylerat"]
    for s_ in (ln, yorum.SISTEM_LIKELY):
        assert "friendly tease" in s_ and "never an insult" in s_.lower()
        assert "even when the match is not in today's coupon" in s_ and "no sarcasm" not in s_
    for s_ in (kk, yorum.SISTEM):
        assert "no sarcasm" in s_ and "tease" not in s_
    # yapay zekâ noktalaması koddan düzelir, hakaret ve yapay zekâ kalıbı elenir
    assert yorum.buyuk_harfle("bold XI — still 31% – “no pressure”") == 'Bold XI, still 31%, "no pressure"'
    kaynak = "Italy 31%"
    assert yorum.uygun("Bold XI. I've still got Italy at 31% tonight, so no pressure", kaynak)
    for kotu in ("Italy fans, prepare to be embarrassed: 31%", "Clowns. Italy 31%", "Proper bottlers, 31%",
                 "Not just team news but a statement, 31%", "Here's the thing: 31%"):
        assert not yorum.uygun(kotu, kaynak), kotu

    # kupona girmeyen maçın postu da bizim yüzdelerimizle yazılır (kupon seçeneği yok)
    icerikler = []
    def cagir(client, modeller, sistem, icerik, sema, max_tokens):
        icerikler.append(icerik)
        return {"uygun": True, "taslaklar": ["Brave call — I've still got Italy at 31%", "Italy fans are clowns"]}
    monkeypatch.setattr(direktor, "_cagir", cagir)
    ita = mac(1, "France", "Italy")
    ita["p"]["MS2"] = 0.31
    t = firsat.taslaklar({"metin": "Italy XI tonight", "kullanici": "433"}, ita, object(), AYAR, "likely", None)
    assert "our_chances" in icerikler[0] and "in_my_coupon_today" not in icerikler[0]
    assert t == ["Brave call, I've still got Italy at 31%"]


def test_C2_tek_kanal_x_postu_atip_hata_dondururse_paylasilmis_sayilir(monkeypatch):
    """16 Ekim (sahibinin isteği: "aynı şey için ikili üçlü e-posta"): X postu atıp 5xx dönerse ya da sonraki deneme
    "duplicate content" alırsa bot hesabın son postlarına bakar; post oradaysa kimliği döner, yeniden atılmaz."""
    monkeypatch.setattr(tweets.time, "sleep", lambda sn: None)

    class Yanit:
        def __init__(self, kod, veri=None, metin=""):
            self.status_code, self._veri, self.text = kod, veri or {}, metin

        def json(self):
            return self._veri

    simdi = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    metin = "💡 Three legs in & one to go.\n\n18+ | Play responsibly"

    class Oturum:
        def __init__(self, kod, govde, var):
            self.kod, self.govde, self.var, self.okuma = kod, govde, var, 0

        def post(self, url, **k):
            return Yanit(self.kod, metin=self.govde)

        def get(self, url, **k):
            self.okuma += 1
            if url.endswith("/users/me"):
                return Yanit(200, {"data": {"id": "42"}})
            data = [{"id": "777", "created_at": simdi, "text": metin.replace("&", "&amp;") + " https://t.co/x"}] if self.var else []
            return Yanit(200, {"data": data})

    x = tweets.XClient.__new__(tweets.XClient)
    x.session = Oturum(503, '{"detail":"Service Unavailable"}', var=True)
    assert x.gonder(metin) == "777"  # 503 ama post X'te: paylaşılmış sayılır
    x = tweets.XClient.__new__(tweets.XClient)
    x.session = Oturum(403, '{"detail":"You are not allowed to create a Tweet with duplicate content."}', var=True)
    assert x.gonder(metin) == "777"  # önceki 503'ün postu: kimliği bulunur
    x = tweets.XClient.__new__(tweets.XClient)
    x.session = Oturum(403, '{"detail":"You are not allowed to create a Tweet with duplicate content."}', var=False)
    with pytest.raises(tweets.KopyaPost):
        x.gonder(metin)  # eski bir postun kopyası: yeniden denemek boşuna
    x = tweets.XClient.__new__(tweets.XClient)
    x.session = Oturum(400, '{"detail":"Invalid"}', var=True)
    with pytest.raises(RuntimeError):
        x.gonder(metin)
    assert x.session.okuma == 0  # olağan hatada okuma (ücret) yok


def test_C2_tek_kanal_alarm_iletildiyse_calisma_basarisiz_sayilmaz():
    """Bot hatayı alarm issue'suna yazdıysa iş başarısız işaretlenmez (GitHub 'Run failed' e-postası ve nöbetçi alarmı
    aynı hatayı tekrarlamaz); yazamadıysa başarısız (nöbetçi alarm açar). Nöbetçi hata dizisi başına bir alarm açar."""
    from bot.__main__ import cikis_kodu
    assert cikis_kodu(["Mr. Likely bilgi postu: X API hatası 503"], alarm_iletildi=True) == 0
    assert cikis_kodu(["Mr. Likely bilgi postu: X API hatası 503"], alarm_iletildi=False) == 1
    assert cikis_kodu([], alarm_iletildi=False) == 0
    nobet = (ROOT / ".github/workflows/nobet.yml").read_text()
    assert 'hata_bildirildi=1' in nobet and 'hata_bildirildi=""' in nobet and '= "success" ]' in nobet


def test_B2_ayni_anda_biten_cok_mac_uc_nabizda_biter():
    """15 Ekim: tablodaki 12 maç 21:00'de başladı, 3'er 3'er çıkınca sonuncusu 2,5 saat sınırını geçti (alarm)."""
    maclar = [mac(i, f"Ev{i}", f"Dep{i}", saat="19:00") for i in range(1, 16)]
    gun = {"tarih": "2026-10-03", "tablo": maclar,
           "etkilesim": {"tablo": {"durum": "paylasildi", "tweet_id": "9", "zaman": "2026-10-03T08:00:00+00:00",
                                   "maclar": [a["fixture_id"] for a in maclar]}}}

    class X:
        def gonder(self, metin, **k):
            return "1"
    bitti = lambda l: {a["fixture_id"]: {"durum": "bitti", "skor": (1, 0)} for a in l}
    t = datetime(2026, 10, 3, 20, 55, tzinfo=UTC)
    adetler = [etkilesim.tablo_takibi(gun, AYAR, X(), t + timedelta(minutes=7 * i), bitti) for i in range(3)]
    assert sum(adetler) == 15 and gun["etkilesim"]["tablo"]["takip"]["durum"] == "tamam"
    assert max(adetler) <= 5  # yine de art arda yığılmaz


def test_D6_kulup_hesabi_takim_adi_sayilir():
    """15 Ekim: "@SunderlandAFC" etiketli post Sunderland kartına eşleşmiyordu. Kulübün @hesabı takım adı sayılır;
    başka bir kulübün ya da kadın takımının hesabı eşleşmez."""
    from bot import firsat
    kartlar = [mac(1, "Torreense", "Sunderland"), mac(2, "AC Milan", "Inter"), mac(3, "Arsenal", "Chelsea")]
    assert firsat.eslesen_mac("Block after block 🧱 tonight #UEL | @SunderlandAFC", kartlar)["dep"] == "Sunderland"
    assert firsat.eslesen_mac("The talent in this squad v Inter 😮‍💨 | @acmilan", kartlar)["ev"] == "AC Milan"
    assert firsat.eslesen_mac("@ChelseaFC travel to face @Arsenal tonight", kartlar)["ev"] == "Arsenal"
    assert firsat.eslesen_mac("@InterMiamiCF win tonight", kartlar) is None
    assert firsat.eslesen_mac("@Arsenal_Women face City tonight", kartlar) is None


def test_D6_kulup_hesaplari_ikinci_arama_ve_onbellek(tmp_path, monkeypatch):
    """25 Ekim 2026 (sahibinin isteği): bugünkü büyük maçların resmi kulüp hesapları da aranır; aynı saatin araması
    iki hesaba bir kez (ücret bir kez)."""
    from bot import firsat
    assert firsat.kulup_hesaplari([mac(1, "Barcelona", "Real Madrid", saat="20:00"), mac(2, "Sabadell", "Tenerife")]) \
        == ["FCBarcelona", "realmadriden"]
    monkeypatch.setattr(firsat, "DOSYA", tmp_path / "firsatlar.json")
    monkeypatch.setattr(firsat, "ayar_yukle", lambda: firsat.BuyumeAyar(gunluk_yorum=4, likely_gunluk_yorum=4, saatler=[10], likely_saatler=[10]))
    simdi = datetime(2026, 10, 3, 10, 5, tzinfo=UTC)
    z = (simdi - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    gun = {"analizler": [mac(1, "Barcelona", "Real Madrid", saat="19:00")],
           "etkilesim": {"analiz_0": {"durum": "paylasildi", "tweet_id": "777"}}}

    class X:
        sorgular = []
        def ara(self, sorgu, *a, **k):
            X.sorgular.append(sorgu)
            return [{"id": "9", "metin": "Matchday. Barcelona v Real Madrid tonight", "kullanici": "FCBarcelona", "zaman": z,
                     "metrik": {"like_count": 50}}] if "FCBarcelona" in sorgu else []

    class GH:
        def issue_ac(self, *a): return 1
        def yorum(self, *a): pass
    monkeypatch.setattr(firsat, "taslaklar", lambda *a, **k: ["Big one tonight"])
    assert firsat.kontrol(X(), GH(), AYAR, gun, simdi, client=object(), hesap="likely") == 1
    assert len(X.sorgular) == 2 and "from:realmadriden" in X.sorgular[1]
    firsat.kontrol(X(), GH(), AYAR, gun, simdi, client=object(), hesap="kalkylerat")
    assert len(X.sorgular) == 2  # aynı saatin araması öbür hesaba önbellekten
