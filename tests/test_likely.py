"""Mr. Likely (elle paylaşılan ikinci hesap) testleri. SOZLESME.md E bölümündeki her madde burada denetlenir."""

import ast
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bot import config, denetci, likely, model
from bot.tweets import ANSVAR, LIMIT, uzunluk

AYAR = config.yukle()
CFG = likely.LikelyAyar(aktif=True)
UTC = timezone.utc
SIMDI = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


def oran_seti(p1: float, px: float, p_ust25: float, p_ust15: float, marj: float = 1.03):
    """Gerçek ihtimallerden %3 marjlı oranlar; dört bahisçi (Pinnacle + üç büyük site) aynı fiyatı verir.
    Adil ihtimal Pinnacle'ın marjsız fiyatıdır, yani verilen ihtimallerin kendisi."""
    o = {"MS1": p1, "MSX": px, "MS2": 1 - p1 - px, "UST25": p_ust25, "ALT25": 1 - p_ust25,
         "UST15": p_ust15, "ALT15": 1 - p_ust15}
    return {ad: {k: round(1 / (v * marj), 3) for k, v in o.items()} for ad in ("Pinnacle", "Bet365", "Unibet", "Betsson")}


def mac(fid: int, ev: str, dep: str, saat: int, lig_id: int = 39, ist=None) -> dict:
    return {"fixture_id": fid, "ev": ev, "dep": dep, "lig": "Premier League", "lig_id": lig_id,
            "baslama": (SIMDI + timedelta(hours=saat)).isoformat(), "istatistik_gol": ist}


MACLAR = [mac(1, "Arsenal", "Burnley", 6), mac(2, "Liverpool", "Luton", 6), mac(3, "Bayern", "Bochum", 8, 78),
          mac(4, "Inter", "Lecce", 9, 135), mac(5, "Sevilla", "Getafe", 10, 140), mac(6, "Lens", "Nice", 1, 61)]
ORANLAR = {1: oran_seti(0.78, 0.14, 0.62, 0.82), 2: oran_seti(0.81, 0.12, 0.66, 0.85),
           3: oran_seti(0.80, 0.13, 0.69, 0.87), 4: oran_seti(0.72, 0.18, 0.55, 0.77),
           5: oran_seti(0.42, 0.30, 0.37, 0.61), 6: oran_seti(0.76, 0.15, 0.64, 0.83)}


class SahteGH:
    def __init__(self):
        self.acilan, self.yorum_kutusu, self.gelen, self.kapali, self._id = [], [], [], [], 100

    def issue_ac(self, baslik, govde, etiket):
        self.acilan.append((baslik, govde, etiket))
        return 7

    def yaz(self, metin, kim="OWNER", tur="User"):
        self._id += 1
        self.gelen.append({"id": self._id, "body": metin, "author_association": kim,
                           "user": {"login": "sahip", "type": tur}})

    def yorumlar(self, no):
        return list(self.gelen)

    def yetkili(self, kullanici):
        return False

    def yorum(self, no, mesaj):
        self.yorum_kutusu.append(mesaj)

    def kapat(self, no, mesaj):
        self.yorum_kutusu.append(mesaj)
        self.kapali.append(no)


@pytest.fixture
def ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: CFG)
    gh = SahteGH()
    likely.sabah(AYAR, MACLAR, ORANLAR, SIMDI, gh)
    return gh


def bitir(skorlar: dict):
    return lambda maclar, korner: {m["fixture_id"]: {"durum": "bitti", "skor": skorlar[m["fixture_id"]], "iy": (0, 0),
                                                     "korner": None} for m in maclar}


# ---------- Havuz ve kuponlar ----------

def test_havuz_yuksek_ihtimalli_ve_numarali():
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, CFG, SIMDI)
    assert adaylar and [a["no"] for a in adaylar] == list(range(1, len(adaylar) + 1))
    saglam = [a for a in adaylar if a["tur"] == "guvenli"]
    assert all(a["olasilik"] >= CFG.min_olasilik and CFG.oran_min <= a["oran"] <= CFG.oran_max for a in saglam)
    assert saglam == sorted(saglam, key=lambda a: -a["olasilik"])  # en yüksek ihtimal önce
    assert all(a["deger"] >= CFG.min_deger for a in saglam)       # bahisçi payından pahalı oyun yok
    assert 6 not in {a["fixture_id"] for a in adaylar}             # 1 saat sonra başlayan maç: seçmeye vakit yok
    for fid in {a["fixture_id"] for a in adaylar}:                 # maç başına en fazla iki aday, farklı ailelerden
        aileler = [likely._aile(a["pazar"]) for a in adaylar if a["fixture_id"] == fid]
        assert len(aileler) <= 2 and len(set(aileler)) == len(aileler)


def test_ihtimal_keskin_piyasanin_marjsiz_fiyati():
    a = next(a for a in likely.havuz(MACLAR, ORANLAR, AYAR, CFG, SIMDI) if a["aday_id"] == "1-MS1")
    adil = model.piyasa_olasiliklari(ORANLAR[1]["Pinnacle"])["MS1"]
    assert a["olasilik"] == round(adil, 3) == 0.78 and a["deger"] == round(adil * a["oran"] - 1, 3) < 0


def test_istatistik_ayrisan_aday_isaretlenir_ve_hazir_kupona_girmez():
    maclar = [dict(m, istatistik_gol=[0.6, 1.9]) if m["fixture_id"] == 1 else m for m in MACLAR]
    adaylar = likely.havuz(maclar, ORANLAR, AYAR, CFG, SIMDI)
    arsenal = next(a for a in adaylar if a["aday_id"] == "1-MS1")
    assert not arsenal["uyum"] and arsenal["istatistik"] < arsenal["olasilik"]
    assert all("1-MS1" not in k["ayaklar"] for k in likely.ornek_kuponlar(adaylar, CFG))


def test_E3_kupon_orani_ve_tutma_ihtimali_carpimdir_ve_maclar_farkli():
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, CFG, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    kuponlar = likely.ornek_kuponlar(adaylar, CFG)
    assert 3 <= len(kuponlar) <= CFG.kupon and [k["harf"] for k in kuponlar] == list(likely.HARFLER[:len(kuponlar)])
    assert len({frozenset(k["ayaklar"]) for k in kuponlar}) == len(kuponlar)  # aynı kupon iki kez gelmez
    for k in kuponlar:
        ayaklar = [harita[i] for i in k["ayaklar"]]
        assert len({a["fixture_id"] for a in ayaklar}) == len(ayaklar) <= 3
        assert k["oran"] == round(math.prod(a["oran"] for a in ayaklar), 2)
        assert k["olasilik"] == round(math.prod(a["olasilik"] for a in ayaklar), 3)
    assert len(kuponlar[0]["ayaklar"]) == 1  # ilk kupon tek maç: kısa kupon önce


# ---------- Metinler ----------

def test_E2_kupon_postu_tutma_ihtimalini_yazar_kesinlik_dili_yok():
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, CFG, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    for k in likely.ornek_kuponlar(adaylar, CFG):
        ayaklar = [harita[i] for i in k["ayaklar"]]
        metin = likely.kupon_metni(k, ayaklar, "2026-10-10" + k["harf"])
        assert uzunluk(metin) <= LIMIT and metin.endswith(ANSVAR)
        assert f"{round(100 * k['olasilik'])}% to land" in metin        # kupon kaç kez tutar: açıkça
        assert all(a["ev"] in metin and f'{a["oran"]:.2f}' in metin for a in ayaklar)
        assert not denetci._KESINLIK.search(metin) and not denetci._LINK.search(metin) and not denetci._SITE.search(metin)
        assert likely.ses_uygun(metin, metin, likely._zorunlu(ayaklar)) == []


def test_uzun_isimli_dortlu_kupon_da_sinira_sigar():
    ayaklar = [{"ev": "Borussia Monchengladbach", "dep": "Eintracht Frankfurt", "etiket": "Borussia Monchengladbach Over 0.5 goals",
                "oran": 1.2, "olasilik": 0.8, "fixture_id": i} for i in range(4)]
    k = {"oran": 2.07, "olasilik": 0.41}
    metin = likely.kupon_metni(k, ayaklar, "x")
    assert metin.endswith(ANSVAR) and "41% to land" in metin


@pytest.mark.parametrize("kotu", [
    "This one is a lock. France v Italy 1.28\n\n" + ANSVAR,          # kesinlik dili
    "France v Italy 1.28, join at example.com\n\n" + ANSVAR,        # link
    "France v Italy 1.28 #football\n\n" + ANSVAR,                   # etiket
    "France v Italy 1.28, I'm 9 from 10 this month\n\n" + ANSVAR,   # şablonda olmayan sayı (uydurma karne)
    "France v Italy 1.28",                                           # 18+ satırı yok
    "France 1.28\n\n" + ANSVAR,                                      # maç adı eksik
])
def test_E2_karakter_metni_kural_disiysa_reddedilir(kotu):
    sablon = "France v Italy: Over 1.5 goals · 1.28\n\n" + ANSVAR
    assert likely.ses_uygun(kotu, sablon, ["France", "Italy", "1.28"])


def test_dersler_sinirda_ve_18_ile_biter():
    for i in range(len(likely.DERSLER)):
        metin = likely.ders_metni("2026-01-01", i)
        assert uzunluk(metin) <= LIMIT and metin.endswith(ANSVAR)
        assert not denetci._KESINLIK.search(metin.replace("never 100", "")) and not denetci._LINK.search(metin)
    assert likely.ders_metni("2026-10-10") != likely.ders_metni("2026-10-11")


# ---------- Seçim ----------

@pytest.mark.parametrize("metin,beklenen", [
    ("C", ["C"]), ("c", ["C"]), ("3 7 12", [[3, 7, 12]]), ("3,7", [[3, 7]]), ("C / 3 7", ["C", [3, 7]]),
    ("A\nB", ["A", "B"]), ("pas", "pas"), ("Pas.", "pas"), ("iptal", "iptal"),
    ("teşekkürler", None), ("C kuponu olsun", None), ("", None),
])
def test_secim_coz(metin, beklenen):
    assert likely.secim_coz(metin) == beklenen


def test_sabah_paketi_issue_olarak_gider_ve_bir_kez(ortam):
    gh = ortam
    baslik, govde, etiket = gh.acilan[0]
    assert etiket == likely.ETIKET and "Mr. Likely" in baslik
    assert "## Hazır kuponlar" in govde and "| # | Maç |" in govde and "`pas`" in govde and ANSVAR in govde
    assert likely.sabah(AYAR, MACLAR, ORANLAR, SIMDI, gh) is None and len(gh.acilan) == 1


def test_secim_post_metnini_getirir_ve_kayda_girer(ortam):
    gh = ortam
    gh.yaz("A / 1 2")
    assert likely.kontrol(AYAR, gh, SIMDI) == 1
    gun = likely.yukle()["gunler"][0]
    assert gun["durum"] == "secildi" and len(gun["secilen"]) == 2
    assert all(k["metin"] in gh.yorum_kutusu[-1] and k["metin"].endswith(ANSVAR) for k in gun["secilen"])
    assert likely.kontrol(AYAR, gh, SIMDI) == 0 and len(gun["secilen"]) == 2  # aynı yorum iki kez işlenmez


def test_yabanci_ve_bot_yorumlari_sayilmaz(ortam):
    gh = ortam
    gh.yaz("A", kim="NONE")
    gh.yaz("A", tur="Bot")
    assert likely.kontrol(AYAR, gh, SIMDI) == 0 and not likely.yukle()["gunler"][0]["secilen"]


def test_E4_mac_basladiktan_sonra_kupon_secilemez(ortam):
    gh = ortam
    gh.yaz("A")
    likely.kontrol(AYAR, gh, SIMDI + timedelta(hours=11))
    assert not likely.yukle()["gunler"][0]["secilen"] and "başlamış" in gh.yorum_kutusu[-1]


def test_ayni_mactan_iki_oyun_ve_cok_uzun_kupon_reddedilir(ortam):
    gh = ortam
    adaylar = likely.yukle()["gunler"][0]["havuz"]
    ayni = [a["no"] for a in adaylar if a["fixture_id"] == adaylar[0]["fixture_id"]]
    assert len(ayni) == 2
    gh.yaz(f"{ayni[0]} {ayni[1]}")
    likely.kontrol(AYAR, gh, SIMDI)
    assert not likely.yukle()["gunler"][0]["secilen"] and "aynı maçtan" in gh.yorum_kutusu[-1]
    gh.yaz("99")
    likely.kontrol(AYAR, gh, SIMDI)
    assert "Aday numarası yok" in gh.yorum_kutusu[-1]


def test_pas_ve_iptal(ortam):
    gh = ortam
    gh.yaz("A")
    likely.kontrol(AYAR, gh, SIMDI)
    gh.yaz("iptal")
    likely.kontrol(AYAR, gh, SIMDI)
    gun = likely.yukle()["gunler"][0]
    assert not gun["secilen"] and gun["durum"] == "bekliyor"
    gh.yaz("pas")
    likely.kontrol(AYAR, gh, SIMDI)
    assert likely.yukle()["gunler"][0]["durum"] == "pas" and gh.kapali == [7]
    assert likely.karne(likely.yukle())["kupon"] == 0


# ---------- Sonuç ve karne ----------

def test_E5_karne_kaybedeni_de_sayar_ve_sonuc_taslagi_gelir(ortam):
    gh = ortam
    gh.yaz("1 / 2 3")
    likely.kontrol(AYAR, gh, SIMDI)
    gun = likely.yukle()["gunler"][0]
    tek, ikili = gun["secilen"]
    idler = {a["fixture_id"] for k in gun["secilen"] for a in k["ayaklar"]}
    # Tekli kupon tutar; ikilinin bir ayağı yatar (her maç 0-0: "üst" ve "kazanır" oyunları kaybeder)
    kazanan = {"MS1": (2, 0), "UST15": (2, 0), "UST25": (3, 0), "CS1X": (1, 0), "CS12": (1, 0)}
    skorlar = {fid: (0, 0) for fid in idler}
    skorlar[tek["ayaklar"][0]["fixture_id"]] = kazanan.get(tek["ayaklar"][0]["pazar"], (2, 0))
    assert likely.sonuclar(AYAR, bitir(skorlar), gh, SIMDI + timedelta(hours=3)) == 0  # maçlar bitmedi
    assert likely.sonuclar(AYAR, bitir(skorlar), gh, SIMDI + timedelta(hours=12)) == 2
    veri = likely.yukle()
    gun = veri["gunler"][0]
    durumlar = sorted(k["durum"] for k in gun["secilen"])
    assert durumlar == ["tuttu", "yatti"] and gun["durum"] == "bitti" and gh.kapali == [7]
    k = likely.karne(veri)
    kazanc = next(x["son_oran"] for x in gun["secilen"] if x["durum"] == "tuttu") - 1
    assert k["kupon"] == 2 and k["tutan"] == 1 and k["kar"] == round(kazanc - 1, 2)
    for kupon in gun["secilen"]:
        metin = kupon["sonuc_metni"]
        assert uzunluk(metin) <= LIMIT and metin.endswith(ANSVAR) and "Record: 1 of " in metin
        assert any(metin in y for y in gh.yorum_kutusu)
    yatan = next(x for x in gun["secilen"] if x["durum"] == "yatti")
    assert "❌" in yatan["sonuc_metni"] and "Coupon down" in yatan["sonuc_metni"]
    assert "Record: 1 of 2 landed" in gun["secilen"][-1]["sonuc_metni"]  # karne o ana kadarki bütün kuponlar


def test_E5_mac_basladiktan_sonra_kupon_geri_alinamaz(ortam):
    gh = ortam
    gh.yaz("A")
    likely.kontrol(AYAR, gh, SIMDI)
    gh.yaz("iptal")
    likely.kontrol(AYAR, gh, SIMDI + timedelta(hours=11))
    gun = likely.yukle()["gunler"][0]
    assert len(gun["secilen"]) == 1 and gun["durum"] == "secildi" and "geri alınamaz" in gh.yorum_kutusu[-1]


def test_iptal_edilen_mac_iade_sayilir(ortam):
    gh = ortam
    gh.yaz("1")
    likely.kontrol(AYAR, gh, SIMDI)
    al = lambda maclar, korner: {m["fixture_id"]: {"durum": "iptal", "skor": None} for m in maclar}
    likely.sonuclar(AYAR, al, gh, SIMDI + timedelta(hours=12))
    veri = likely.yukle()
    assert veri["gunler"][0]["secilen"][0]["durum"] == "iade" and likely.karne(veri) == {"kupon": 0, "tutan": 0, "kar": 0, "roi": 0.0}


def test_cevapsiz_paket_kapanir(ortam):
    gh = ortam
    likely.eskileri_kapat(gh, SIMDI + timedelta(hours=41))
    assert likely.yukle()["gunler"][0]["durum"] == "pas" and gh.kapali == [7]


# ---------- Sözleşme ----------

def test_E1_likely_x_e_paylasmaz():
    """Mr. Likely modülü X istemcisini kullanmaz: postu sahibi elle atar (hesap otomatik değildir)."""
    kaynak = (Path(likely.__file__)).read_text(encoding="utf-8")
    agac = ast.parse(kaynak)
    adlar = {n.id for n in ast.walk(agac) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(agac) if isinstance(n, ast.Attribute)}
    assert not adlar & {"XClient", "KonsolClient", "tweet_at", "paylas", "requests_oauthlib", "OAuth1Session"}
    ithal = {a.name for n in ast.walk(agac) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert "XClient" not in ithal and "X_API_KEY" not in kaynak


def test_kapaliyken_hicbir_sey_yapmaz(monkeypatch, tmp_path):
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: likely.LikelyAyar(aktif=False))
    gh = SahteGH()
    assert likely.sabah(AYAR, MACLAR, ORANLAR, SIMDI, gh) is None and not gh.acilan
    assert likely.kontrol(AYAR, gh, SIMDI) == 0 and likely.sonuclar(AYAR, None, gh, SIMDI) == 0
