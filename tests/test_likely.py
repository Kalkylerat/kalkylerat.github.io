"""Mr. Likely (elle paylaşılan ikinci hesap) testleri. SOZLESME.md E bölümündeki her madde burada denetlenir."""

import ast
import re
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from dataclasses import replace

from bot import config, denetci, likely, model
from bot.tweets import ANSVAR, LIMIT, uzunluk

AYAR = config.yukle()
CFG = likely.LikelyAyar(aktif=True)


@pytest.fixture(autouse=True)
def _olcum_dizini(monkeypatch, tmp_path):
    monkeypatch.setattr(likely, "OLCUM", tmp_path / "olcum")
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

def test_E1_elle_modda_paylasmaz_ve_modul_x_anahtari_okumaz(ortam):
    """Elle modda paylaşım işlevleri hiçbir şey yapmaz; modül X anahtarı okumaz, başkalarına yanıt/takip/beğeni kodu yok."""
    x = SahteX()
    gh = ortam
    gh.yaz("A")
    likely.kontrol(AYAR, gh, SIMDI)
    assert likely.oto_paylas(AYAR, x, SIMDI + timedelta(hours=5)) == 0 and likely.oto_sonuc_paylas(AYAR, x, SIMDI) == 0
    assert likely.oto_bilgi(AYAR, x, SIMDI + timedelta(hours=6)) is False and not x.postlar
    assert likely.yeniden_paylas(AYAR, x, SIMDI) == 0 and not x.silinen
    kaynak = Path(likely.__file__).read_text(encoding="utf-8")
    assert "X_API_KEY" not in kaynak and "X_LIKELY" not in kaynak and "XClient" not in kaynak
    agac = ast.parse(kaynak)
    cagrilar = {n.func.attr for n in ast.walk(agac) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "x"}
    assert cagrilar == {"gonder", "medya_yukle", "sil"}  # yalnızca kendi postu, görseli ve kendi postunu silme; takip/beğeni/DM yok


# ---------- Otomatik mod ----------

OTO = likely.LikelyAyar(aktif=True, mod="otomatik")
ESKI_BILGI = replace(OTO, oto_mac_sayisi=0)  # maç postları kapalıyken büyük maç rakam postları (favori, gol, denk)


class SahteX:
    def __init__(self):
        self.postlar, self.medya, self.silinen = [], 0, []

    def sil(self, tweet_id):
        self.silinen.append(tweet_id)

    def medya_yukle(self, png):
        self.medya += 1
        return f"m{self.medya}"

    def gonder(self, metin, yanit=None, medya=None, alinti=None, **_):
        self.postlar.append({"metin": metin, "yanit": yanit, "medya": medya, "alinti": alinti})
        return f"t{len(self.postlar)}"


@pytest.fixture
def oto(monkeypatch, tmp_path):
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: OTO)
    gh = SahteGH()
    likely.sabah(AYAR, MACLAR, ORANLAR, SIMDI, gh)
    return gh


def test_E6_otomatik_kupon_kurallari():
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, OTO, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    secilen = likely.otomatik_sec(adaylar, OTO)
    assert 1 <= len(secilen) <= OTO.oto_max_kupon and secilen[0]["ad"] == "gunun-kuponu"
    for k in secilen:
        ayaklar = [harita[i] for i in k["ayaklar"]]
        assert OTO.oto_oran_min <= k["oran"] <= OTO.oto_oran_max                  # toplam oran 2.00–4.00
        assert k["olasilik"] >= OTO.oto_min_tutma and k["deger"] >= OTO.oto_min_kupon_deger
        assert len(ayaklar) <= OTO.oto_max_ayak and len({a["fixture_id"] for a in ayaklar}) == len(ayaklar)
        assert all(a["uyum"] and a["deger"] >= OTO.oto_min_deger and not a["kaynak"].startswith("average") for a in ayaklar)
        assert all(a["olasilik"] >= OTO.oto_min_ayak for a in ayaklar if a["tur"] == "guvenli")
        assert not [a for a in ayaklar if a["pazar"] == "CS12"]  # "Double chance 12" otomatik kupona girmez (14 Ekim)
    maclar = [harita[i]["fixture_id"] for k in secilen for i in k["ayaklar"]]
    assert len(maclar) == len(set(maclar))  # iki kupon aynı maçı paylaşmaz
    # Aralıktaki kuponlar içinde tutma ihtimali en yüksek olan: aynı ayaklardan daha olası bir kupon kurulamaz
    import itertools
    uygun = [a for a in adaylar if a["uyum"] and a["deger"] >= OTO.oto_min_deger and a["pazar"] not in OTO.oto_yasak_pazarlar]
    en_yuksek = max((likely.kupon_kur(list(c)) for n in range(1, OTO.oto_max_ayak + 1) for c in itertools.combinations(uygun, n)
                     if likely._farkli_mac(c)), key=lambda k: k["olasilik"] if OTO.oto_oran_min <= k["oran"] <= OTO.oto_oran_max
                    and k["deger"] >= OTO.oto_min_kupon_deger else -1)
    assert secilen[0]["olasilik"] >= en_yuksek["olasilik"] - OTO.oto_buyuk_tolerans
    # İstatistiğin ayrıştığı aday girmez
    ayrisan = likely.havuz([dict(m, istatistik_gol=[0.4, 0.4]) for m in MACLAR], ORANLAR, AYAR, OTO, SIMDI)
    uyum = {a["aday_id"]: a["uyum"] for a in ayrisan}
    assert not all(uyum.values())
    assert all(uyum[i] for k in likely.otomatik_sec(ayrisan, OTO) for i in k["ayaklar"])
    # Kural sağlanmazsa kupon yok: aday yok
    zayif = {m["fixture_id"]: oran_seti(0.42, 0.30, 0.45, 0.60) for m in MACLAR}
    assert likely.otomatik_sec(likely.havuz(MACLAR, zayif, AYAR, OTO, SIMDI), OTO) == []


def test_E6_yakin_kuponlar_icinde_buyuk_maclar_tercih_edilir():
    """Aynı fiyatlı iki maç grubu: bilinmeyen lig (hafifçe daha olası) ve büyük lig. Fark toleransın içinde: büyük maçlar seçilir."""
    kucuk = [dict(mac(100 + i, f"Kasaba {i}", f"Mahalle {i}", 8, lig_id=41), lig="League One") for i in range(4)]
    buyuk = [mac(200 + i, f"Baskent {i}", f"Liman {i}", 8, lig_id=39) for i in range(4)]
    oranlar = {**{m["fixture_id"]: oran_seti(0.80, 0.13, 0.50, 0.70) for m in kucuk},
               **{m["fixture_id"]: oran_seti(0.795, 0.13, 0.50, 0.70) for m in buyuk}}
    adaylar = likely.havuz(kucuk + buyuk, oranlar, AYAR, OTO, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    assert any(a["buyuk"] for a in adaylar) and any(not a["buyuk"] for a in adaylar)
    ana = likely.otomatik_sec(adaylar, OTO)[0]
    assert all(harita[i]["buyuk"] for i in ana["ayaklar"])
    # Fark toleranstan büyükse ihtimal kazanır: büyük maçlar belirgin daha düşük ihtimalliyse seçilmez
    oranlar2 = {**{m["fixture_id"]: oran_seti(0.84, 0.10, 0.50, 0.70) for m in kucuk},
                **{m["fixture_id"]: oran_seti(0.70, 0.18, 0.50, 0.70) for m in buyuk}}
    adaylar2 = likely.havuz(kucuk + buyuk, oranlar2, AYAR, OTO, SIMDI)
    harita2 = {a["aday_id"]: a for a in adaylar2}
    ana2 = likely.otomatik_sec(adaylar2, OTO)[0]
    assert not all(harita2[i]["buyuk"] for i in ana2["ayaklar"])


def test_E6_long_shot_kurallari():
    """İkinci kupon: 3.00–4.00 oran, ayak oranı en az 1.30, günün kuponuyla maç paylaşmaz; sağlanmazsa çıkmaz."""
    saglam = [mac(300 + i, f"Guclu {i}", f"Zayif {i}", 8) for i in range(4)]
    orta = [mac(400 + i, f"Denk {i}", f"Rakip {i}", 8) for i in range(5)]
    oranlar = {**{m["fixture_id"]: oran_seti(0.80, 0.13, 0.50, 0.70) for m in saglam},
               **{m["fixture_id"]: oran_seti(0.66, 0.18, 0.50, 0.60) for m in orta}}
    adaylar = likely.havuz(saglam + orta, oranlar, AYAR, OTO, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    secilen = likely.otomatik_sec(adaylar, OTO)
    assert [k["ad"] for k in secilen][:2] == ["gunun-kuponu", "long-shot"]
    uzun = secilen[1]
    assert OTO.oto_uzun_oran_min <= uzun["oran"] <= OTO.oto_uzun_oran_max
    assert uzun["olasilik"] >= OTO.oto_uzun_min_tutma and uzun["deger"] >= OTO.oto_uzun_min_kupon_deger
    assert all(harita[i]["oran"] >= OTO.oto_uzun_min_ayak_oran for i in uzun["ayaklar"]) and len(uzun["ayaklar"]) <= OTO.oto_max_ayak
    assert not {harita[i]["fixture_id"] for i in uzun["ayaklar"]} & {harita[i]["fixture_id"] for i in secilen[0]["ayaklar"]}
    metin = likely.kupon_metni(dict(uzun, ad="long-shot"), [harita[i] for i in uzun["ayaklar"]], "t", gorselli=True)
    assert any(a in metin for a in likely.UZUN_ACILIS) and f"{round(100 * uzun['olasilik'])}% to land" in metin
    # Yalnızca çok düşük oranlı maçlar varsa long shot çıkmaz
    assert "long-shot" not in [k["ad"] for k in likely.otomatik_sec(likely.havuz(saglam, oranlar, AYAR, OTO, SIMDI), OTO)]


def test_E6_buyuk_maclar_kuponu_yalniz_buyuk_maclardan():
    """Üçüncü kupon: yalnızca büyük maçlar, günün kuponunun sınırlarıyla, öncekilerle maç paylaşmaz; günde en fazla 5 kupon."""
    kucuk = [dict(mac(600 + i, f"Kasaba {i}", f"Mahalle {i}", 8, lig_id=41), lig="League One") for i in range(4)]
    orta = [dict(mac(700 + i, f"Denk {i}", f"Rakip {i}", 8, lig_id=41), lig="League One") for i in range(5)]
    buyuk = [mac(800 + i, f"Baskent {i}", f"Liman {i}", 8, lig_id=39) for i in range(9)]
    oranlar = {**{m["fixture_id"]: oran_seti(0.84, 0.10, 0.50, 0.70) for m in kucuk},
               **{m["fixture_id"]: oran_seti(0.66, 0.18, 0.50, 0.60) for m in orta},
               **{m["fixture_id"]: oran_seti(0.74, 0.16, 0.50, 0.70) for m in buyuk}}
    adaylar = likely.havuz(kucuk + orta + buyuk, oranlar, AYAR, OTO, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    secilen = likely.otomatik_sec(adaylar, OTO)
    adlar = [k["ad"] for k in secilen]
    assert OTO.oto_max_kupon == 5 and len(secilen) <= 5 and adlar[0] == "gunun-kuponu" and "buyuk-maclar" in adlar
    b = secilen[adlar.index("buyuk-maclar")]
    assert all(harita[i]["buyuk"] for i in b["ayaklar"]) and len(b["ayaklar"]) <= OTO.oto_max_ayak
    assert OTO.oto_oran_min <= b["oran"] <= OTO.oto_oran_max and b["olasilik"] >= OTO.oto_min_tutma and b["deger"] >= OTO.oto_min_kupon_deger
    maclar = [harita[i]["fixture_id"] for k in secilen for i in k["ayaklar"]]
    assert len(maclar) == len(set(maclar))
    metin = likely.kupon_metni(b, [harita[i] for i in b["ayaklar"]], "t", gorselli=True)
    assert any(a in metin for a in likely.BUYUK_ACILIS) and f"{round(100 * b['olasilik'])}% to land" in metin
    # Büyük maç yoksa üçüncü kupon çıkmaz
    assert "buyuk-maclar" not in [k["ad"] for k in likely.otomatik_sec(likely.havuz(kucuk + orta, oranlar, AYAR, OTO, SIMDI), OTO)]


def test_E6_yogun_gunde_de_gunun_kuponu_bulunur():
    """9–10 Ekim 2026 hatası: çok maçlı günde en olası adayların hepsi ~1.08 idi; havuz ve arama yalnızca onlara
    bakınca 4 ayakla 2.00'a ulaşılamadı ve kupon çıkmadı. Oran bantlarına yer ayrıldığı için kural sağlanan kupon bulunur."""
    cok = [mac(900 + i, f"Dev {i}", f"Cuce {i}", 8, lig_id=41) for i in range(60)]
    orta = [mac(1000 + i, f"Orta {i}", f"Rakip {i}", 8, lig_id=41) for i in range(4)]
    oranlar = {**{m["fixture_id"]: oran_seti(0.92, 0.06, 0.62, 0.80) for m in cok},
               **{m["fixture_id"]: oran_seti(0.80, 0.13, 0.50, 0.70) for m in orta}}
    adaylar = likely.havuz(cok + orta, oranlar, AYAR, OTO, SIMDI)
    assert len(adaylar) <= OTO.havuz and any(a["oran"] >= 1.19 for a in adaylar)  # bant: orta oranlı adaylar havuzda
    secilen = likely.otomatik_sec(adaylar, OTO)
    assert secilen and secilen[0]["ad"] == "gunun-kuponu" and OTO.oto_oran_min <= secilen[0]["oran"] <= OTO.oto_oran_max


def test_E6_ek_kuponlar_gunun_kuponu_sinirlariyla_en_fazla_5():
    """18 Ekim 2026 (sahibinin isteği): üç türden sonra kalan yer, kalan maçlardan günün kuponuyla AYNI sınırlarla
    dolar; günde en fazla 5 kupon, kuponlar maç paylaşmaz. Sınır 3'e inerse ek kupon çıkmaz."""
    cok = [mac(1100 + i, f"Guclu {i}", f"Zayif {i}", 8, lig_id=41) for i in range(40)]
    oranlar = {m["fixture_id"]: oran_seti(0.80, 0.13, 0.50, 0.70) for m in cok}
    adaylar = likely.havuz(cok, oranlar, AYAR, OTO, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    secilen = likely.otomatik_sec(adaylar, OTO)
    adlar = [k["ad"] for k in secilen]
    assert 4 <= len(secilen) <= 5 and adlar[0] == "gunun-kuponu" and "gunun-kuponu-2" in adlar
    for k in secilen:
        if k["ad"].startswith("gunun-kuponu"):
            assert OTO.oto_oran_min <= k["oran"] <= OTO.oto_oran_max and k["olasilik"] >= OTO.oto_min_tutma
            assert k["deger"] >= OTO.oto_min_kupon_deger and len(k["ayaklar"]) <= OTO.oto_max_ayak
            assert all(likely.kupona_uygun(harita[i], OTO) for i in k["ayaklar"])
    maclar = [harita[i]["fixture_id"] for k in secilen for i in k["ayaklar"]]
    assert len(maclar) == len(set(maclar))
    assert len(likely.otomatik_sec(adaylar, replace(OTO, oto_max_kupon=3))) <= 3
    assert likely.KUPON_ADI["gunun-kuponu-2"] == "Günün kuponu 2"


def test_kupon_cikmazsa_bildirim_uyarir(monkeypatch, tmp_path):
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: OTO)
    gh = SahteGH()
    zayif = {m["fixture_id"]: oran_seti(0.42, 0.30, 0.45, 0.60) for m in MACLAR}
    likely.sabah(AYAR, MACLAR, zayif, SIMDI, gh)
    assert gh.acilan[0][0].startswith("⚠️") and "KUPON ÇIKMADI" in gh.acilan[0][0]


def test_gorselli_kupon_metni_emojili_ve_soruyla_biter():
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, OTO, SIMDI)
    harita = {a["aday_id"]: a for a in adaylar}
    k = likely.otomatik_sec(adaylar, OTO)[0]
    metin = likely.kupon_metni(k, [harita[i] for i in k["ayaklar"]], "2026-10-07", gorselli=True)
    satirlar = metin.split("\n")
    assert metin.startswith("🎩 ") and metin.endswith(ANSVAR) and uzunluk(metin) <= LIMIT
    assert sum(s.startswith("⚽ ") for s in satirlar) == len(k["ayaklar"])
    assert any(s.startswith("📊 ") and f"{round(100 * k['olasilik'])}% to land" in s for s in satirlar)
    assert any(s.startswith("💬 ") and s.endswith("?") for s in satirlar)
    assert likely.ses_uygun(metin, metin, []) == []
    assert "etkileşim tuzağı" in likely.ses_uygun(metin.replace("💬 ", "💬 RT if you agree. "), metin, [])


def test_otomatik_sabah_kuponu_secer_ve_zamanlar(oto):
    gun = likely.yukle()["gunler"][0]
    assert gun["oto"] and gun["durum"] == "secildi" and gun["secilen"] and all(k["oto"] for k in gun["secilen"])
    for k in gun["secilen"]:
        ilk = min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"])
        zaman = datetime.fromisoformat(k["paylas"])
        assert SIMDI < zaman <= ilk - timedelta(minutes=45)
    assert "otomatik" in oto.acilan[0][0] and "otomatik modda" in oto.acilan[0][1]


def test_E1_otomatik_paylasim_bir_kez_gorselli_ve_sonuc_alintisi(oto):
    from bot import likely_gorsel
    x = SahteX()
    assert likely.oto_paylas(AYAR, x, SIMDI + timedelta(minutes=1), kart=likely_gorsel.kupon_karti) == 0  # zamanı gelmedi
    gun = likely.yukle()["gunler"][0]
    zaman = datetime.fromisoformat(gun["secilen"][0]["paylas"])
    assert likely.oto_paylas(AYAR, x, zaman, kart=likely_gorsel.kupon_karti) == 1
    likely.oto_paylas(AYAR, x, zaman, kart=likely_gorsel.kupon_karti)
    assert len(x.postlar) == len({p["metin"] for p in x.postlar})  # aynı kupon iki kez gitmez
    k = likely.yukle()["gunler"][0]["secilen"][0]
    post = x.postlar[0]
    assert k["tweet_id"] == "t1" and post["medya"] == ["m1"] and post["yanit"] is None
    assert post["metin"].endswith(ANSVAR) and f"{round(100 * k['olasilik'])}% to land" in post["metin"] and uzunluk(post["metin"]) <= LIMIT
    # Sonuç: kupon postunu alıntılayan ayrı post (yanıt değil), sonuç kartıyla, bir kez
    idler = {a["fixture_id"] for a in k["ayaklar"]}
    adet = len(x.postlar)
    likely.sonuclar(AYAR, bitir({f: (2, 0) for f in {a["fixture_id"] for kk in likely.yukle()["gunler"][0]["secilen"] for a in kk["ayaklar"]}}),
                    oto, SIMDI + timedelta(hours=14))
    assert likely.oto_sonuc_paylas(AYAR, x, SIMDI + timedelta(hours=14), kart=likely_gorsel.sonuc_karti) >= 1
    sonuc = x.postlar[adet]
    assert sonuc["alinti"] == "t1" and sonuc["yanit"] is None and sonuc["medya"] and len(sonuc["medya"]) == 1
    assert "Record:" in sonuc["metin"] and sonuc["metin"].endswith(ANSVAR) and sonuc["metin"][0] in "✅❌↩" and uzunluk(sonuc["metin"]) <= LIMIT
    assert all(p["yanit"] is None for p in x.postlar)  # hiçbir post yanıt olarak gitmez
    assert likely.oto_sonuc_paylas(AYAR, x, SIMDI + timedelta(hours=15), kart=likely_gorsel.sonuc_karti) == 0 and idler


def test_E9_ucuz_mod_sonuclar_tek_postta_mac_postu_yalniz_buyuk(oto, monkeypatch):
    """28 Ekim 2026, sahibinin isteği (maliyet): kuponların sonuçları günde tek postta; maç postu yalnızca büyük maçlar."""
    from bot import likely_saglik
    gercek = likely.LikelyAyar(**{k: v for k, v in __import__("tomllib").loads(
        (likely.config.ROOT / "ayarlar.toml").read_text(encoding="utf-8"))["likely"].items()
        if k in likely.LikelyAyar.__dataclass_fields__})
    assert not gercek.oto_sonuc_tek and gercek.oto_mac_yalniz_buyuk  # sonuçlar kupon başına (28 Ekim akşamı) and gercek.oto_mac_sayisi == 3 and gercek.oto_hikaye_sayisi == 1
    tek = replace(OTO, oto_sonuc_tek=True)
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: tek)
    x = SahteX()
    for k in sorted(likely.yukle()["gunler"][0]["secilen"], key=lambda k: k["paylas"]):
        likely.oto_paylas(AYAR, x, datetime.fromisoformat(k["paylas"]))
    kuponlar = [k for k in likely.yukle()["gunler"][0]["secilen"] if k.get("tweet_id")]
    assert kuponlar
    fids = {a["fixture_id"] for k in kuponlar for a in k["ayaklar"]}
    adet, sonra = len(x.postlar), SIMDI + timedelta(hours=14)
    likely.sonuclar(AYAR, bitir({f: (2, 0) for f in fids}), oto, sonra,
                    yazici=lambda s, z: pytest.fail("tek sonuç modunda kupon başına Claude metni yazılmaz"))
    assert likely.oto_sonuc_paylas(AYAR, x, sonra) == 1 and likely.oto_sonuc_paylas(AYAR, x, sonra) == 0
    yeni = x.postlar[adet:]
    assert len(yeni) == 1 and yeni[0]["alinti"] is None and yeni[0]["yanit"] is None
    metin = yeni[0]["metin"]
    assert metin.endswith(ANSVAR) and uzunluk(metin) <= LIMIT and "Record:" in metin and metin.startswith("🎩 ")
    assert sum(bool(s) and s[0] in "✅❌↩" for s in metin.splitlines()) == len(kuponlar)
    assert not likely_saglik.metin_ihlalleri(metin, True)
    gun = likely.yukle()["gunler"][0]
    assert {k["sonuc_tweet_id"] for k in gun["secilen"] if k.get("tweet_id")} == {f"t{adet + 1}"}  # kasa sırası (E8)
    assert gun["toplu_sonuc"][0]["metin"] == metin
    # Günün paylaşılabilecek kuponu kaldıysa sonuç postu onu bekler
    veri = {"gunler": [{"tarih": "2026-10-07", "secilen": [
        {**next(k for k in gun["secilen"] if k.get("tweet_id")), "sonuc_tweet_id": None},
        {"ad": "gunun-kuponu-2", "durum": "bekliyor", "ayaklar": [{"baslama": (sonra + timedelta(hours=1)).isoformat()}]}]}]}
    assert likely._tek_sonuc_paylas(veri, x, sonra) == 0
    veri["gunler"][0]["secilen"][1]["ayaklar"][0]["baslama"] = (sonra - timedelta(hours=1)).isoformat()
    assert likely._tek_sonuc_paylas(veri, x, sonra) == 1  # paylaşılmadan maçı başlayan kupon beklenmez (E4)
    # Maç postu yalnızca büyük maçlar
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, OTO, SIMDI)
    plan = likely.mac_planla(MACLAR, adaylar, [], SIMDI, replace(OTO, oto_mac_yalniz_buyuk=True, oto_mac_sayisi=3,
                                                                oto_hikaye_sayisi=1), AYAR)
    assert len(plan) <= 3 and all(m["buyuk"] for m in plan) and sum(bool(m.get("hikaye")) for m in plan) <= 1
    assert {m["fixture_id"] for m in plan} <= {a["fixture_id"] for a in MACLAR if likely.analiz.onemli(a)}


def test_E4_ilk_maca_az_kaldiysa_otomatik_paylasilmaz_ve_karneye_girmez(oto):
    x = SahteX()
    gun = likely.yukle()["gunler"][0]
    son = max(min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"]) for k in gun["secilen"])
    assert likely.oto_paylas(AYAR, x, son - timedelta(minutes=5)) == 0 and not x.postlar
    veri = likely.yukle()
    assert not veri["gunler"][0]["secilen"] and veri["gunler"][0]["kacan"]
    assert likely.karne(veri)["kupon"] == 0


def test_E5_paylasilmayan_otomatik_kupon_karneye_girmez(oto):
    gun = likely.yukle()["gunler"][0]
    idler = {a["fixture_id"] for k in gun["secilen"] for a in k["ayaklar"]}
    likely.sonuclar(AYAR, bitir({f: (0, 0) for f in idler}), oto, SIMDI + timedelta(hours=14))
    assert likely.karne(likely.yukle())["kupon"] == 0  # X'e hiç çıkmadı: sayılmaz


def test_otomatik_iptal_paylasilmamis_kuponu_durdurur(oto):
    oto.yaz("iptal")
    likely.kontrol(AYAR, oto, SIMDI)
    assert not likely.yukle()["gunler"][0]["secilen"] and "durduruldu" in oto.yorum_kutusu[-1]
    oto.yaz("A")
    likely.kontrol(AYAR, oto, SIMDI)
    assert not likely.yukle()["gunler"][0]["secilen"] and "Otomatik modda" in oto.yorum_kutusu[-1]


def buyuk_analiz(fid, ev, dep, saat, p1, px, ust):
    return dict(mac(fid, ev, dep, saat, lig_id=39), kaynak="piyasa", guven="yuksek",
                p={"MS1": p1, "MSX": px, "MS2": round(1 - p1 - px, 3), "UST25": ust, "ALT25": round(1 - ust, 3)})


def test_bilgi_postlari_rakamlari_kayittan_sinirda_ve_kurala_uygun():
    """Bilgi postları: iki ders + günün büyük maçlarından rakamlar. Rakam analiz kaydından; kesinlik dili, link, tavsiye yok."""
    analizler = [buyuk_analiz(1, "France", "Malta", 8, 0.86, 0.10, 0.55), buyuk_analiz(2, "Germany", "Spain", 9, 0.38, 0.28, 0.63),
                 buyuk_analiz(3, "Wales", "Norway", 9, 0.36, 0.30, 0.44)]
    bilgi = likely.bilgi_hazirla(analizler, "2026-10-10", SIMDI, ESKI_BILGI)
    assert [b["tur"] for b in bilgi] == ["ders", "favori", "gol", "ders"] and len(bilgi) <= OTO.oto_bilgi_sayisi
    assert [b["saat"] for b in bilgi] == sorted(b["saat"] for b in bilgi) and len({b["metin"] for b in bilgi}) == len(bilgi)
    favori, gol = bilgi[1]["metin"], bilgi[2]["metin"]
    assert "France" in favori and "86%" in favori and "Malta" in favori and "one time in 7" in favori
    assert "Germany v Spain" in gol and "63%" in gol
    for b in bilgi:
        m = b["metin"]
        assert uzunluk(m) <= LIMIT and m.endswith(ANSVAR) and m[0] in "💡📈⚽⚖"
        assert not denetci._KESINLIK.search(m) and not denetci._LINK.search(m) and "#" not in m and "@" not in m
        assert not likely._TUZAK.search(m) if hasattr(likely, "_TUZAK") else True
    # Gol beklentisi düşükse en dengeli maç; büyük maç yoksa yalnızca dersler
    denk = likely.bilgi_hazirla([dict(a, p=dict(a["p"], UST25=0.45)) for a in analizler], "2026-10-10", SIMDI, ESKI_BILGI)
    assert [b["tur"] for b in denk] == ["ders", "favori", "denk", "ders"] and "Wales v Norway" in denk[2]["metin"]
    assert [b["tur"] for b in likely.bilgi_hazirla([], "2026-10-10", SIMDI, ESKI_BILGI)] == ["ders", "ders"]
    # Başlamış ya da başlamak üzere olan maçtan rakam yazılmaz
    gec = likely.bilgi_hazirla([dict(a, baslama=(SIMDI + timedelta(minutes=30)).isoformat()) for a in analizler], "2026-10-10", SIMDI, ESKI_BILGI)
    assert [b["tur"] for b in gec] == ["ders", "ders"]


def test_bilgi_postu_saatinde_bir_kez_ve_diger_postlardan_uzakta(oto):
    x = SahteX()
    gun = likely.yukle()["gunler"][0]
    assert gun["bilgi"] and gun["bilgi"][0]["tur"] == "ders" and gun["bilgi"][0]["saat"] == 10.0
    assert likely.oto_bilgi(AYAR, x, SIMDI.replace(hour=7)) is False  # 09:00 İsveç: ilk bilgi postunun saatinden önce
    zamanlar = [datetime.fromisoformat(k["paylas"]) for k in gun["secilen"]]
    yakin = next(z for z in zamanlar if z.astimezone(UTC).hour >= 8)
    assert likely.oto_bilgi(AYAR, x, yakin - timedelta(minutes=20)) is False and not x.postlar  # kupon postuna 20 dk var
    uzak = next(t for t in (SIMDI.replace(hour=8) + timedelta(minutes=10 * i) for i in range(60))
                if all(abs((t - z).total_seconds()) >= 60 * OTO.oto_bilgi_aralik_dk for z in zamanlar))
    assert likely.oto_bilgi(AYAR, x, uzak) is True and x.postlar[-1]["metin"] == gun["bilgi"][0]["metin"]
    assert x.postlar[-1]["yanit"] is None and x.postlar[-1]["medya"] is None
    # Bir sonraki bilgi postu öncekinden en az oto_bilgi_aralik_dk sonra; gün sonunda her biri bir kez
    assert likely.oto_bilgi(AYAR, x, uzak + timedelta(minutes=10)) is False and len(x.postlar) == 1
    t = uzak
    for _ in range(120):
        t += timedelta(minutes=10)
        likely.oto_bilgi(AYAR, x, t)
    bilgi = likely.yukle()["gunler"][0]["bilgi"]
    metinler = [p["metin"] for p in x.postlar]
    assert len(metinler) == len(set(metinler)) <= OTO.oto_bilgi_sayisi and all(b.get("tweet_id") for b in bilgi if b["saat"] < 23)
    atilan = sorted(datetime.fromisoformat(b["zaman"]) for b in bilgi if b.get("zaman"))
    assert all((b - a).total_seconds() >= 60 * OTO.oto_bilgi_aralik_dk for a, b in zip(atilan, atilan[1:]))


def test_yeniden_paylas_mac_baslamadan_siler_ve_ayni_kuponu_yeniden_atar(oto):
    """Sahibinin isteğiyle: paylaşılmış kupon postu maç başlamadan silinip aynı kuponla yeniden atılır (E5: maç başladıysa dokunulmaz)."""
    x = SahteX()
    k0 = likely.yukle()["gunler"][0]["secilen"][0]
    zaman = datetime.fromisoformat(k0["paylas"])
    assert likely.oto_paylas(AYAR, x, zaman) == 1
    assert likely.yeniden_paylas(AYAR, x, zaman + timedelta(minutes=5)) == 1 and x.silinen == ["t1"]
    k = likely.yukle()["gunler"][0]["secilen"][0]
    assert "tweet_id" not in k and k["silinen"] == ["t1"] and k["ayaklar"] == k0["ayaklar"] and k["oran"] == k0["oran"]
    assert likely.oto_paylas(AYAR, x, zaman + timedelta(minutes=6)) == 1
    k = likely.yukle()["gunler"][0]["secilen"][0]
    assert k["tweet_id"] == "t2" and likely.yeniden_paylas(AYAR, SahteX(), zaman + timedelta(minutes=7)) == 1
    # Maçı başlamış bir maçın rakam postu atılmaz
    veri = likely.yukle()
    veri["gunler"][0]["bilgi"] = [{"tur": "favori", "metin": "📈 x\n\n" + ANSVAR, "saat": 0.0, "baslama": (zaman - timedelta(hours=1)).isoformat()}]
    likely.kaydet(veri)
    x3 = SahteX()
    assert likely.oto_bilgi(AYAR, x3, zaman + timedelta(hours=1, minutes=1)) is False and not x3.postlar
    # Maç başladıktan sonra: silinmez
    x2 = SahteX()
    ilk = min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"])
    veri = likely.yukle()
    veri["gunler"][0]["secilen"][0]["tweet_id"] = "t9"
    likely.kaydet(veri)
    silinecek = [kk for kk in veri["gunler"][0]["secilen"] if kk.get("tweet_id")]
    assert likely.yeniden_paylas(AYAR, x2, ilk + timedelta(minutes=1)) == 0 and not x2.silinen and silinecek


def test_kupon_karti_png():
    from bot import likely_gorsel
    k = {"oran": 1.52, "olasilik": 0.61, "ayaklar": [
        {"ev": "Borussia Monchengladbach", "dep": "Eintracht Frankfurt", "etiket": "Borussia Monchengladbach Over 0.5 goals", "oran": 1.15},
        {"ev": "Italy", "dep": "Türkiye", "etiket": "Double chance 1X", "oran": 1.12}]}
    png = likely_gorsel.kupon_karti(k, "2026-10-06")
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 20_000


def test_sonuc_karti_png_tutan_yatan_iade():
    from bot import likely_gorsel
    ayaklar = [{"ev": "Borussia Monchengladbach", "dep": "Eintracht Frankfurt", "etiket": "Borussia Monchengladbach Over 0.5 goals", "oran": 1.15, "skor": "2-1", "durum": "kazandi"},
               {"ev": "Italy", "dep": "Türkiye", "etiket": "Double chance 1X", "oran": 1.12, "skor": "0-1", "durum": "kaybetti"},
               {"ev": "Wales", "dep": "Norway", "etiket": "Over 1.5 goals", "oran": 1.30, "skor": None, "durum": "iade"}]
    kartlar = [likely_gorsel.sonuc_karti({"oran": 1.67, "son_oran": son, "olasilik": 0.55, "durum": durum, "ayaklar": ayaklar}, "2026-10-06")
               for durum, son in (("tuttu", 1.67), ("yatti", 1.67), ("iade", 1.0))]
    assert all(png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 20_000 for png in kartlar) and len(set(kartlar)) == 3


def test_sonuc_karti_yuklenemezse_sonuc_yine_paylasilir(oto):
    """E5: kaybeden de yazılır; görsel yükleme hatası sonuç postunu engellemez."""
    x = SahteX()
    gun = likely.yukle()["gunler"][0]
    likely.oto_paylas(AYAR, x, datetime.fromisoformat(gun["secilen"][0]["paylas"]))
    likely.sonuclar(AYAR, bitir({a["fixture_id"]: (0, 0) for k in gun["secilen"] for a in k["ayaklar"]}), oto, SIMDI + timedelta(hours=14))

    def bozuk(k, tarih):
        raise RuntimeError("medya")
    assert likely.oto_sonuc_paylas(AYAR, x, SIMDI + timedelta(hours=14), kart=bozuk) == 1
    assert x.postlar[-1]["alinti"] == "t1" and x.postlar[-1]["medya"] is None


def test_kapaliyken_hicbir_sey_yapmaz(monkeypatch, tmp_path):
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: likely.LikelyAyar(aktif=False))
    gh = SahteGH()
    assert likely.sabah(AYAR, MACLAR, ORANLAR, SIMDI, gh) is None and not gh.acilan
    assert likely.kontrol(AYAR, gh, SIMDI) == 0 and likely.sonuclar(AYAR, None, gh, SIMDI) == 0


# ---------- Paylaşım izni (mevcut uygulamaya) ----------

def test_paylasim_izni_sifreli_saklanir_ve_yanlis_hesap_kaydedilmez(monkeypatch, tmp_path):
    from bot import likely_yetki
    monkeypatch.setattr(likely_yetki, "DOSYA", tmp_path / "likely_x.enc")
    assert likely_yetki.anahtarlar("gizli") is None
    likely_yetki.kaydet("gizli", "tok-123", "sec-456", "MrLikely")
    ham = (tmp_path / "likely_x.enc").read_bytes()
    assert b"tok-123" not in ham and b"sec-456" not in ham                      # depoda düz metin yok
    assert likely_yetki.anahtarlar("gizli") == {"token": "tok-123", "secret": "sec-456", "hesap": "MrLikely"}
    assert likely_yetki.anahtarlar("baska-gizli") is None                        # yanlış anahtarla açılmaz
    assert likely_yetki.coz("https://github.com/?oauth_token=AbC-1_x&oauth_verifier=Zz9_y") == ("AbC-1_x", "Zz9_y")
    assert likely_yetki.coz("guvenli_min_deger=-0.03") is None

    class Sahte:
        def __init__(self, *a, **k): pass
        def fetch_access_token(self, url):
            return {"oauth_token": "t", "oauth_token_secret": "s", "screen_name": "Kalkylerat"}
    monkeypatch.setattr(likely_yetki, "OAuth1Session", Sahte)
    with pytest.raises(RuntimeError):
        likely_yetki.tamamla("k", "gizli", "a", "b")
    assert likely_yetki.anahtarlar("gizli")["hesap"] == "MrLikely"               # önceki kayıt bozulmadı


def test_ek_kupon_eksik_turu_tamamlar_mevcuda_dokunmaz(oto):
    gun = likely.yukle()["gunler"][0]
    once = [k["ad"] for k in gun["secilen"]]
    dolu = {a["fixture_id"] for k in gun["secilen"] for a in k["ayaklar"]}
    orta = [mac(500 + i, f"Denk {i}", f"Rakip {i}", 8) for i in range(5)]
    oranlar = {**ORANLAR, **{m["fixture_id"]: oran_seti(0.66, 0.18, 0.50, 0.60) for m in orta}}
    eklenen = likely.ek_kupon(AYAR, MACLAR + orta, oranlar, SIMDI + timedelta(minutes=10), oto)
    gun = likely.yukle()["gunler"][0]
    assert [k["ad"] for k in gun["secilen"]][:len(once)] == once and len(gun["secilen"]) == len(once) + eklenen <= OTO.oto_max_kupon
    for k in gun["secilen"][len(once):]:
        assert k["oto"] and k["ad"] not in once and not {a["fixture_id"] for a in k["ayaklar"]} & dolu


def test_ek_kupon_ikinci_gunun_kuponunu_ek_adla_ekler(oto):
    """Öğlen tazelemede günün kuponu türü zaten varsa yeni kupon "gunun-kuponu-2" adıyla girer; toplam en fazla 5."""
    gun = likely.yukle()["gunler"][0]
    once = [k["ad"] for k in gun["secilen"]]
    dolu = {a["fixture_id"] for k in gun["secilen"] for a in k["ayaklar"]}
    cok = [mac(1300 + i, f"Guclu {i}", f"Zayif {i}", 8) for i in range(30)]
    oranlar = {**ORANLAR, **{m["fixture_id"]: oran_seti(0.80, 0.13, 0.50, 0.70) for m in cok}}
    likely.ek_kupon(AYAR, MACLAR + cok, oranlar, SIMDI + timedelta(minutes=10), oto)
    gun = likely.yukle()["gunler"][0]
    adlar = [k["ad"] for k in gun["secilen"]]
    assert "gunun-kuponu" in once and "gunun-kuponu-2" in adlar and len(adlar) == len(set(adlar)) <= OTO.oto_max_kupon
    for k in gun["secilen"][len(once):]:
        assert not {a["fixture_id"] for a in k["ayaklar"]} & dolu


def test_ogle_tazeleme_gunde_bir_kez_ve_saatinde(oto, monkeypatch):
    """Tazeleme yalnızca otomatik modda, oto_tazele_saati'nden sonra, kupon sayısı sınırın altındayken ve günde bir kez."""
    assert len(likely.yukle()["gunler"][0]["secilen"]) < OTO.oto_max_kupon
    tz = likely.ZoneInfo(AYAR.saat_dilimi)
    gun_ = SIMDI.astimezone(tz)
    erken = gun_.replace(hour=OTO.oto_tazele_saati - 1, minute=30)
    ogle = gun_.replace(hour=OTO.oto_tazele_saati, minute=30)
    assert not likely.tazeleme_zamani(AYAR, erken)
    assert likely.tazeleme_zamani(AYAR, ogle) and likely.yukle()["gunler"][0].get("tazeleme")
    assert not likely.tazeleme_zamani(AYAR, ogle + timedelta(minutes=15))  # ikinci kez yok
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: replace(OTO, mod="elle"))
    assert not likely.tazeleme_zamani(AYAR, ogle + timedelta(days=0))


# ---------- Anket, haftalık karne, ölçüm (gölge test) ----------

class AnketliX(SahteX):
    def gonder(self, metin, yanit=None, medya=None, alinti=None, anket=None, **_):
        self.postlar.append({"metin": metin, "yanit": yanit, "medya": medya, "alinti": alinti, "anket": anket})
        return f"t{len(self.postlar)}"


def test_E1_buyuk_mac_bilgi_postu_anketli_ve_anket_mac_baslayinca_kapanir():
    analizler = [buyuk_analiz(1, "France", "Malta", 8, 0.86, 0.10, 0.55), buyuk_analiz(2, "Germany", "Spain", 9, 0.38, 0.28, 0.63),
                 buyuk_analiz(3, "Wales", "Norway", 9, 0.36, 0.30, 0.44)]
    bilgi = likely.bilgi_hazirla(analizler, "2026-10-10", SIMDI, ESKI_BILGI)
    anketli = [b for b in bilgi if b.get("anket")]
    assert [b["tur"] for b in anketli] == ["favori", "gol"] and all("Vote below" in b["metin"] for b in anketli)
    assert all(len(o) <= 25 for b in anketli for o in b["anket"]["options"]) and anketli[1]["anket"]["bitis"] == analizler[1]["baslama"]
    assert not any(b.get("anket") for b in bilgi if b["tur"] == "ders")
    denk = likely.bilgi_hazirla([dict(a, p=dict(a["p"], UST25=0.45)) for a in analizler], "2026-10-10", SIMDI, ESKI_BILGI)
    assert denk[2]["anket"]["options"] == ["Wales", "Draw", "Norway"]
    uzun = likely.bilgi_hazirla([dict(a, p=dict(a["p"], UST25=0.45), dep="Borussia Mönchengladbach Reserves") for a in analizler],
                                "2026-10-10", SIMDI, ESKI_BILGI)
    assert "anket" not in uzun[2] and uzun[2]["tur"] == "denk"  # seçenek 25 karakteri aşarsa anket yok, post yine gider
    # Paylaşımda anket süresi maç başlangıcına kadar
    x = AnketliX()
    gun = {"tarih": "2026-10-10", "oto": True, "secilen": [], "bilgi": [dict(anketli[1], saat=0.0)]}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(likely, "yukle", lambda: {"gunler": [gun]})
        mp.setattr(likely, "kaydet", lambda veri: None)
        mp.setattr(likely, "ayar_yukle", lambda *a, **k: OTO)
        assert likely.oto_bilgi(AYAR, x, SIMDI) is True
    assert x.postlar[0]["anket"] == {"options": ["Over 2.5 goals", "Under 2.5 goals"], "duration_minutes": 9 * 60}


def test_E1_haftalik_karne_yalniz_karneden():
    def kupon(durum, p, tweet=True):
        return {"oto": True, "durum": durum, "olasilik": p, **({"tweet_id": "t"} if tweet else {})}
    veri = {"gunler": [{"tarih": "2026-10-04", "secilen": [kupon("yatti", 0.5)]},  # önceki hafta: sayılmaz
                       {"tarih": "2026-10-06", "secilen": [kupon("tuttu", 0.5), kupon("yatti", 0.3)]},
                       {"tarih": "2026-10-08", "secilen": [kupon("yatti", 0.5), kupon("tuttu", 0.4, tweet=False)]},
                       {"tarih": "2026-10-11", "secilen": [kupon("tuttu", 0.45), kupon("bekliyor", 0.3)]}]}
    acik = replace(OTO, oto_haftalik_karne=True)
    assert likely.haftalik_karne(veri, "2026-10-12", OTO) is None  # ayar kapalıysa yok
    assert likely.haftalik_karne(veri, "2026-10-13", acik) is None  # Pazartesi değil
    h = likely.haftalik_karne(veri, "2026-10-12", acik)
    assert h["kupon"] == 4 and h["tutan"] == 2 and round(h["beklenen"], 2) == 1.75  # paylaşılmamış ve bekleyen sayılmaz
    m = likely.hafta_metni(h)
    assert "4 coupons, 2 landed" in m and "about 2 should" in m and m.endswith(ANSVAR) and uzunluk(m) <= LIMIT
    assert likely.ses_uygun(m, m, []) == []
    bilgi = likely.bilgi_hazirla([], "2026-10-12", SIMDI, acik, hafta=h)
    assert [b["tur"] for b in bilgi] == ["hafta", "ders"]


def _olcum_gunu(oto_tarih="2026-10-10"):
    havuz_ = likely.havuz(MACLAR, ORANLAR, AYAR, OTO, SIMDI)
    return {"tarih": oto_tarih, "havuz": havuz_, "secilen": [], "gunler": []}, havuz_


def test_E1_olcum_havuzun_butun_ayaklarini_toplu_sonuclandirir_paylasmaz(monkeypatch, tmp_path):
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    gun, havuz_ = _olcum_gunu()
    odds_mac, bitmeyen = havuz_[0]["fixture_id"], next(a["fixture_id"] for a in havuz_ if a["fixture_id"] != havuz_[0]["fixture_id"])
    for a in havuz_:
        if a["fixture_id"] == odds_mac:
            a["odds_id"] = "abc"  # The Odds API maçı: kredi harcamamak için ölçülmez
    likely.kaydet({"gunler": [gun]})
    istenen = []

    def sonuc_al(idler):
        istenen.append(list(idler))
        return {fid: {"durum": "bitti", "skor": (2, 1), "iy": (1, 0)} for fid in idler if fid != bitmeyen}

    sonra = SIMDI + timedelta(hours=14)
    adet = likely.olcum_guncelle(sonuc_al, sonra)
    assert len(istenen) == 1 and odds_mac not in istenen[0] and bitmeyen in istenen[0]  # tek toplu istek
    kayit = likely.yukle()["gunler"][0]
    assert adet == sum(1 for a in kayit["havuz"] if a.get("sonuc") in ("kazandi", "kaybetti", "iade")) > 0
    assert all(a["sonuc"] == "yok" for a in kayit["havuz"] if a.get("odds_id"))
    assert all("sonuc" not in a for a in kayit["havuz"] if a["fixture_id"] == bitmeyen) and not kayit.get("olcum_bitti")
    for a in kayit["havuz"]:  # 2-1: ev kazandı
        if a.get("sonuc") in ("kazandi", "kaybetti"):
            assert (a["sonuc"] == "kazandi") == model.kazandi_mi(a["pazar"], 2, 1, iy=(1, 0))
    # Saatte bir: hemen ardından yeni istek yok; bir saat sonra yalnızca kalan maç sorulur
    assert likely.olcum_guncelle(sonuc_al, sonra + timedelta(minutes=10)) == 0 and len(istenen) == 1
    likely.olcum_guncelle(lambda idler: istenen.append(list(idler)) or {f: {"durum": "iptal", "skor": None} for f in idler},
                          sonra + timedelta(hours=1))
    assert istenen[-1] == [bitmeyen]
    kayit = likely.yukle()["gunler"][0]
    assert kayit["olcum_bitti"] and all("sonuc" in a for a in kayit["havuz"])
    dosya = likely.olcum_oku()
    assert len(dosya) == 1 and dosya[0]["tam"] and all(a["sonuc"] in ("kazandi", "kaybetti", "iade") for a in dosya[0]["ayaklar"])
    assert likely.olcum_guncelle(sonuc_al, sonra + timedelta(hours=5)) == 0 and len(istenen) == 2  # bitmiş gün bir daha sorulmaz


def test_olcum_raporu_kalibrasyon_ve_kural_varyantlari():
    _, havuz_ = _olcum_gunu()
    gunler = [{"tarih": f"2026-10-{10 + i}", "tam": True,
               "ayaklar": [{**{k: a[k] for k in likely.OLCUM_ALANLARI if k in a}, "sonuc": "kazandi" if (a["fixture_id"] + i) % 3 else "kaybetti"}
                           for a in havuz_]} for i in range(3)]
    kal = likely.kalibrasyon(gunler, OTO)
    toplam = kal[-1]
    assert toplam["grup"] == "Toplam" and toplam["ayak"] == sum(r["ayak"] for r in kal[:-1])
    uygun = [a for g in gunler for a in g["ayaklar"] if likely.kupona_uygun(a, OTO)]
    assert toplam["tutan"] == sum(a["sonuc"] == "kazandi" for a in uygun)
    assert abs(toplam["beklenen"] - sum(a["olasilik"] for a in uygun)) < 0.1
    golge = likely.golge_kuponlar(gunler, OTO)
    assert [v["varyant"] for v in golge] == [v[0] for v in likely.VARYANTLAR]
    bugun = golge[0]["turler"]["gunun-kuponu"]
    assert bugun["kupon"] == 3 and 0 <= bugun["tutan"] <= 3 and 2.0 <= bugun["oran"] <= 4.0
    assert -3 <= bugun["kar"] <= 3 * (4.0 - 1) and (bugun["tutan"] > 0 or bugun["kar"] == -3)
    rapor = likely.olcum_raporu(OTO, gunler)
    assert "Toplam" in rapor and "Bugünkü kurallar" in rapor and "12 (ev ya da deplasman)" in rapor
    assert likely.olcum_raporu(OTO, []).startswith("Henüz ölçüm yok")
    eksik = [dict(g, tam=False) for g in gunler]  # sonucu eksik gün yeniden oynatılmaz
    assert all(not v["turler"] for v in likely.golge_kuponlar(eksik, OTO))


def test_toplu_sonuclar_20_mac_bir_istek_reddedilirse_tek_tek():
    from bot import football

    def kayit(fid, durum="FT"):
        return {"fixture": {"id": fid, "status": {"short": durum}}, "score": {"fulltime": {"home": 1, "away": 0},
                                                                            "halftime": {"home": 0, "away": 0}}}

    class Api:
        def __init__(self, toplu=True):
            self.istekler, self.toplu = [], toplu

        def get(self, path, **p):
            self.istekler.append(p)
            if "ids" in p:
                if not self.toplu:
                    raise football.ApiHatasi("ids desteklenmiyor")
                return [kayit(int(i), "NS" if i == "7" else "FT") for i in p["ids"].split("-")]
            return [kayit(p["id"])]

    api = Api()
    sonuc = football.toplu_sonuclar(api, list(range(1, 46)))
    assert len(api.istekler) == 3 and len(sonuc) == 45  # 45 maç: 20 + 20 + 5
    assert sonuc[1] == {"durum": "bitti", "skor": (1, 0), "goller": None, "iy": (0, 0), "korner": None} and sonuc[7]["durum"] == "bekliyor"
    api = Api(toplu=False)
    assert len(football.toplu_sonuclar(api, [1, 2, 3])) == 3 and len(api.istekler) == 4  # 1 reddedilen + 3 tek



# ---------- Sonuç postunda gerçek an (SOZLESME E2) ----------

def ayak(pazar, etiket, skor, goller, durum):
    return {"ev": "Arsenal", "dep": "Burnley", "pazar": pazar, "etiket": etiket, "skor": skor, "goller": goller,
            "durum": durum, "oran": 1.40, "olasilik": 0.7}


def test_E2_gec_gol_ani_gercek_dakika_ve_skorla_anlatilir():
    # Alt 2.5: 88'de 2-0, 90+3'te 3-0 (sahibinin örneği)
    alt = ayak("ALT25", "Under 2.5 goals", "3-0", [[30, 0, "ev"], [88, 0, "ev"], [90, 3, "ev"]], "kaybetti")
    x = likely.an(alt)
    assert x == {"tur": "yikim", "dk": "90+3", "once": "2-0", "sonra": "3-0", "odk": "88", "uzatma": True,
                 "M": "Arsenal v Burnley", "E": "Under 2.5 goals"}
    kupon = {"ayaklar": [alt, dict(ayak("CS1X", "Lens win or draw", "1-1", [[10, 0, "dep"], [50, 0, "ev"]], "kazandi"),
                                   ev="Lens", dep="Nice")],
             "durum": "yatti", "olasilik": 0.49, "son_oran": 1.4}
    for tohum in ("a", "b", "c", "d"):
        m = likely.sonuc_metni(kupon, {"kupon": 5, "tutan": 2}, tohum)
        assert m.startswith("❌ ") and "90+3" in m and "3-0" in m and "Arsenal v Burnley" in m
        assert uzunluk(m) <= LIMIT and m.endswith(ANSVAR) and likely.ses_uygun(m, m, []) == []
    # Geç kurtarış: Çifte şans 1X, 0-1'den 89'da 1-1
    kurtar = ayak("CS1X", "Arsenal win or draw", "1-1", [[20, 0, "dep"], [89, 0, "ev"]], "kazandi")
    assert likely.an(kurtar)["tur"] == "kurtaris" and likely.an(kurtar)["dk"] == "89"
    m = likely.sonuc_metni({"ayaklar": [kurtar], "durum": "tuttu", "olasilik": 0.7, "son_oran": 1.4}, {"kupon": 1, "tutan": 1}, "x")
    assert m.startswith("✅ ") and "89" in m and "1.40" in m
    # Anlatı yok: erken karar, el değiştirmeyen ayak, gol listesi yok, skorla tutmayan liste, ilk yarı pazarı
    assert likely.an(ayak("ALT25", "U", "3-0", [[10, 0, "ev"], [20, 0, "ev"], [30, 0, "ev"]], "kaybetti")) is None
    assert likely.an(ayak("ALT25", "U", "0-0", [], "kazandi")) is None
    assert likely.an(ayak("ALT25", "U", "3-0", None, "kaybetti")) is None
    assert likely.an(ayak("ALT25", "U", "4-0", [[30, 0, "ev"], [88, 0, "ev"], [90, 3, "ev"]], "kaybetti")) is None
    assert likely.an(ayak("IYU05", "U", "0-1", [[85, 0, "dep"]], "kaybetti")) is None
    # Gol listesi yoksa eski düz metin (uydurma an yok)
    duz = likely.sonuc_metni({"ayaklar": [dict(alt, goller=None)], "durum": "yatti", "olasilik": 0.7, "son_oran": 1.0},
                             {"kupon": 1, "tutan": 0}, "a")
    assert "90" not in duz and "Coupon down" in duz


def test_gol_dakikalari_mac_olaylarindan_ve_skorla_tutmali():
    from bot import football

    def olay(dk, takim, detay="Normal Goal", ek=None, tur="Goal"):
        return {"time": {"elapsed": dk, "extra": ek}, "team": {"id": takim}, "type": tur, "detail": detay}

    f = {"teams": {"home": {"id": 1}, "away": {"id": 2}},
         "events": [olay(88, 1), olay(30, 1), olay(90, 1, ek=3), olay(60, 2, "Missed Penalty"), olay(40, 1, tur="Card"),
                    olay(105, 2)]}  # uzatma devresi golü 90 dakikaya girmez
    assert football.goller(f, (3, 0)) == [[30, 0, "ev"], [88, 0, "ev"], [90, 3, "ev"]]
    # Kendi kalesine gol oyuncunun takımına yazılmışsa ters çevrilir
    kk = {"teams": {"home": {"id": 1}, "away": {"id": 2}}, "events": [olay(10, 1), olay(85, 1, "Own Goal")]}
    assert football.goller(kk, (1, 1)) == [[10, 0, "ev"], [85, 0, "dep"]]
    assert football.goller(kk, (2, 0)) == [[10, 0, "ev"], [85, 0, "ev"]]
    assert football.goller(kk, (3, 0)) is None and football.goller({"teams": f["teams"]}, (0, 0)) is None


def test_otomatik_zamanlama_kuponu_kendi_maci_sonrasina_itmez():
    """14 Ekim: 40 dk aralık seçim sırasıyla verildi; akşam kuponu önce gelince öğle ve akşamüstü kuponları kendi
    ilk maçlarının sonrasına itildi, long-shot kaçtı."""
    simdi = datetime(2026, 10, 14, 5, 39, tzinfo=UTC)
    kupon = lambda saat: {"ayaklar": [{"baslama": f"2026-10-14T{saat}:00+00:00"}]}
    kuponlar = [kupon("20:00"), kupon("11:05"), kupon("16:45")]  # seçim sırası: günün, long-shot, büyük maçlar
    zamanlar = likely.paylasim_zamanlari(kuponlar, simdi, OTO)
    for k, z in zip(kuponlar, zamanlar):
        ilk = datetime.fromisoformat(k["ayaklar"][0]["baslama"])
        assert simdi < z <= ilk - timedelta(minutes=45)
    sirali = sorted(zamanlar)
    assert all((b - a).total_seconds() >= 40 * 60 for a, b in zip(sirali, sirali[1:]))
    # Aynı saatte başlayan iki kupon: aralık son saati aşmıyorsa verilir, aşacaksa kupon kaçırılmaz
    ikiz = likely.paylasim_zamanlari([kupon("12:00"), kupon("12:00")], datetime(2026, 10, 14, 10, 50, tzinfo=UTC), OTO)
    assert all(z <= datetime(2026, 10, 14, 11, 15, tzinfo=UTC) for z in ikiz)


def test_E6_double_chance_12_otomatik_kupona_girmez():
    """14 Ekim, sahibinin kararı: "ya ev ya deplasman kazanır" (CS12) ayağı otomatik kupona hiç girmez."""
    assert "CS12" in OTO.oto_yasak_pazarlar
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, OTO, SIMDI)
    cs12 = [dict(a, pazar="CS12", aday_id=a["aday_id"] + "-12") for a in adaylar]
    assert not any(likely.kupona_uygun(a, OTO) for a in cs12)
    harita = {a["aday_id"]: a for a in adaylar + cs12}
    for k in likely.otomatik_sec(adaylar + cs12, OTO):
        assert all(harita[i]["pazar"] != "CS12" for i in k["ayaklar"])


def test_E6_gercek_disi_degerli_ayak_kupona_girmez():
    """14 Ekim: +%35 "değerli" görünen ayak hatalı fiyattı (Bet365'te 1.50, kayıtta 2.05)."""
    adaylar = likely.havuz(MACLAR, ORANLAR, AYAR, OTO, SIMDI)
    a = adaylar[0]
    assert not likely.kupona_uygun(dict(a, deger=0.35, tur="deger"), OTO)
    assert likely.kupona_uygun(dict(a, deger=min(a["deger"], OTO.oto_max_ayak_deger)), OTO) == likely.kupona_uygun(a, OTO)


def test_E5_veri_hatasi_iptal_mac_baslamadan_siler_karneye_girmez(oto):
    x = SahteX()
    gun = likely.yukle()["gunler"][0]
    k = gun["secilen"][0]
    zaman = datetime.fromisoformat(k["paylas"])
    assert likely.oto_paylas(AYAR, x, zaman) == 1
    tid = likely.yukle()["gunler"][0]["secilen"][0]["tweet_id"]
    ilk = min(datetime.fromisoformat(a["baslama"]) for a in k["ayaklar"])
    assert likely.veri_hatasi_iptal(AYAR, x, ilk + timedelta(minutes=1), k["ad"], "fiyat") is False  # maç başladı: olmaz
    assert likely.veri_hatasi_iptal(AYAR, x, zaman + timedelta(minutes=1), k["ad"], "aykırı fiyat") is True
    gun = likely.yukle()["gunler"][0]
    assert tid in x.silinen and all(s["ad"] != k["ad"] for s in gun["secilen"])
    assert gun["iptal_edilen"][0]["iptal"]["neden"] == "aykırı fiyat"
    idler = {a["fixture_id"] for s in gun["iptal_edilen"] for a in s["ayaklar"]}
    likely.sonuclar(AYAR, bitir({f: (2, 0) for f in idler}), oto, ilk + timedelta(hours=14))
    assert likely.karne(likely.yukle())["kupon"] == 0  # iptal edilen kupon sayılmaz


def test_bilgi_postu_x_kopya_reddinde_dongu_ve_alarm_yok(oto):
    """15 Ekim 19:05: X bilgi postunu atıp 503 döndü; sonraki her nabız 403 "duplicate content" aldı ve 2 saatte 18 alarm
    açıldı. X aynı metni reddederse post atlanır (tekrar denenmez, hata yükselmez)."""
    from bot.tweets import KopyaPost

    class KopyaX(SahteX):
        def gonder(self, metin, **k):
            self.denemeler = getattr(self, "denemeler", 0) + 1
            raise KopyaPost('X API hatası 403: {"detail":"You are not allowed to create a Tweet with duplicate content."}')
    x = KopyaX()
    gun = likely.yukle()["gunler"][0]
    zamanlar = [datetime.fromisoformat(k["paylas"]) for k in gun["secilen"]]
    uzak = next(t for t in (SIMDI.replace(hour=8) + timedelta(minutes=10 * i) for i in range(60))
                if all(abs((t - z).total_seconds()) >= 60 * OTO.oto_bilgi_aralik_dk for z in zamanlar))
    assert likely.oto_bilgi(AYAR, x, uzak) is False and x.denemeler == 1
    assert likely.yukle()["gunler"][0]["bilgi"][0]["tweet_id"] == "tekrar"
    likely.oto_bilgi(AYAR, x, uzak + timedelta(minutes=7))
    assert x.denemeler == 1  # aynı post bir daha denenmez


def test_E6_ayak_orani_yalniz_bet365ten():
    """24 Ekim 2026 (sahibinin kararı): kombinede ayakların en iyi fiyatı farklı sitelerden geliyordu, toplam oran tek
    sitede bulunamıyordu. Ayak oranı Bet365'in fiyatıdır; Bet365'te olmayan ya da aykırı fiyatlı pazar düşer."""
    b = oran_seti(0.80, 0.12, 0.60, 0.80)
    b["Unibet"] = {k: round(v * 1.05, 3) for k, v in b["Unibet"].items()}  # başka sitede daha iyi fiyat
    oranlar = {1: b}
    adaylar = likely.havuz(MACLAR[:1], oranlar, AYAR, CFG, SIMDI)
    assert adaylar and all(a["oran_kaynagi"] == "Bet365" for a in adaylar)
    for a in adaylar:
        assert a["oran"] == round(b["Bet365"][a["pazar"]], 2)
    kupon = likely._dondur(adaylar[:1], "gunun-kuponu", SIMDI)
    assert kupon["ayaklar"][0]["oran_kaynagi"] == "Bet365"
    # Bet365'te olmayan pazar kupona girmez
    b2 = {ad: dict(o) for ad, o in b.items()}
    del b2["Bet365"]["MS1"]
    assert not any(a["pazar"] == "MS1" for a in likely.havuz(MACLAR[:1], {1: b2}, AYAR, CFG, SIMDI))
    # Bet365 fiyatı aykırıysa (ortancadan %8'den yüksek) pazar düşer
    b3 = {ad: dict(o) for ad, o in b.items()}
    b3["Bet365"]["MS1"] = round(b3["Pinnacle"]["MS1"] * 1.3, 3)
    assert not any(a["pazar"] == "MS1" for a in likely.havuz(MACLAR[:1], {1: b3}, AYAR, CFG, SIMDI))
    # ayarlar.toml canlı ayarı da Bet365
    assert likely.ayar_yukle().oran_sitesi == "Bet365"


def test_E2_kupon_gorselinde_her_ayagin_ihtimali(monkeypatch):
    """24 Ekim 2026 (sahibinin isteği): kupon kartında her ayağın yanında kendi ihtimali (%)."""
    from PIL import ImageDraw
    from bot import likely_gorsel
    yazilar = []
    asil = ImageDraw.ImageDraw.text
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", lambda self, xy, metin, *a, **k: (yazilar.append(metin), asil(self, xy, metin, *a, **k))[1])
    k = {"oran": 2.04, "olasilik": 0.512, "ayaklar": [
        {"ev": "Arsenal", "dep": "Burnley", "etiket": "Arsenal win", "oran": 1.36, "olasilik": 0.712},
        {"ev": "Inter", "dep": "Lecce", "etiket": "Over 1.5 goals", "oran": 1.5, "olasilik": 0.719}]}
    assert likely_gorsel.kupon_karti(k, "2026-10-25")[:4] == b"\x89PNG"
    assert "Arsenal win · 71% likely" in yazilar and "Over 1.5 goals · 72% likely" in yazilar
def test_E1_duyuru_postu(oto):
    """Sabah duyurusu: ilk kupondan önce bir kez, sayı paylaşılacak kupon sayısı; kupon yoksa ya da gün başladıysa yok."""
    x = SahteX()
    gun = likely.yukle()["gunler"][0]
    n = len(gun["secilen"])
    assert likely.oto_duyuru(AYAR, x, SIMDI) is True and len(x.postlar) == 1
    metin = x.postlar[0]["metin"]
    sayi = "one" if n == 1 else likely.SAYILAR[n]
    assert sayi in metin.lower() and "http" not in metin and uzunluk(metin) <= LIMIT
    assert not re.search(r"guarantee|lock|sure thing|can't lose|—", metin, re.I)
    assert likely.oto_duyuru(AYAR, x, SIMDI + timedelta(minutes=15)) is False and len(x.postlar) == 1  # günde bir kez
    assert likely.yukle()["gunler"][0]["duyuru"]["sayi"] == n
    # Bilgi postu duyurudan en az 40 dakika uzak durur
    assert SIMDI in likely._post_zamanlari(likely.yukle()["gunler"][0])


def test_E1_duyuru_kupon_yoksa_ya_da_gun_basladiysa_atilmaz(oto):
    x = SahteX()
    veri = likely.yukle()
    secilen = veri["gunler"][0]["secilen"]
    veri["gunler"][0]["secilen"] = []
    likely.kaydet(veri)
    assert likely.oto_duyuru(AYAR, x, SIMDI) is False and not x.postlar
    veri["gunler"][0]["secilen"] = secilen
    secilen[0]["tweet_id"] = "t0"  # bugün bir kupon zaten paylaşılmış: duyuru geç kalmıştır
    likely.kaydet(veri)
    assert likely.oto_duyuru(AYAR, x, SIMDI) is False and not x.postlar


def test_duyuru_metni_sesi():
    assert likely.duyuru_metni(4, "2026-10-21").startswith("🎩 ")
    assert "four" in likely.duyuru_metni(4, "2026-10-21").lower()
    assert "one coupon" in likely.duyuru_metni(1, "x").lower()
    tum = {likely.duyuru_metni(3, f"2026-10-{g:02d}") for g in range(1, 31)}
    assert len(tum) >= 4  # günden güne değişir
    assert any(e in likely.duyuru_metni(3, "t", ek_olabilir=True) for e in likely.DUYURU_EK)
    for t in likely.DUYURU + likely.DUYURU_TEK + likely.DUYURU_EK:
        assert "—" not in t and "http" not in t


def _analizli(maclar=MACLAR):
    """Testteki maçlara analiz kaydının alanları (piyasa ihtimalleri) eklenir."""
    p = {1: (0.78, 0.14), 2: (0.81, 0.12), 3: (0.80, 0.13), 4: (0.72, 0.18), 5: (0.42, 0.30), 6: (0.76, 0.15)}
    return [{**m, "kaynak": "piyasa", "guven": "yuksek",
             "p": {"MS1": p[m["fixture_id"]][0], "MSX": p[m["fixture_id"]][1], "MS2": 1 - sum(p[m["fixture_id"]]),
                   "UST25": 0.61, "KGVAR": 0.52}} for m in maclar]


def test_E1_mac_postlari(monkeypatch, tmp_path):
    """24 Ekim 2026 (sahibinin isteği): günde en fazla 10 günün maçı postu; önce büyük maçlar; rakamlar kayıttan;
    "safest angle" havuzun en yüksek ihtimalli oyunu; maçtan önce, birbirinden 15 dk uzak; maç başladıysa yok."""
    analizler = _analizli()
    adaylar = likely.havuz(analizler, ORANLAR, AYAR, OTO, SIMDI)
    plan = likely.mac_planla(analizler, adaylar, [], SIMDI, OTO, AYAR)
    assert 1 <= len(plan) <= OTO.oto_mac_sayisi == 10
    assert all(m["fixture_id"] != 6 for m in plan)  # 1 saat sonra başlayan maç (Lens) için vakit yok
    zamanlar = [datetime.fromisoformat(m["saat"]) for m in plan]
    assert all(b - a >= timedelta(minutes=likely.MAC_ARALIK_DK) for a, b in zip(zamanlar, zamanlar[1:]))
    for m, z in zip(plan, zamanlar):
        assert z <= datetime.fromisoformat(m["baslama"]) - timedelta(minutes=likely.MAC_SON_DK)
        enyi = max((c for c in adaylar if c["fixture_id"] == m["fixture_id"] and c["tur"] == "guvenli"
                    and c["pazar"] not in OTO.oto_yasak_pazarlar), key=lambda c: c["olasilik"])
        assert m["aci"]["aday_id"] == enyi["aday_id"]
    gunun = [m for m in plan if m.get("gunun_maci")]
    assert len(gunun) == 1 and gunun[0]["buyuk"]  # "Match of the day" büyük maç, en erken maç değil
    gun = {"tarih": "2026-10-10", "secilen": []}
    m = gunun[0]
    metin = likely.mac_metni(m, gun, AYAR)
    assert "Vote below" in metin and not any("Vote below" in likely.mac_metni(n, gun, AYAR) for n in plan if n is not m)
    assert metin.startswith(f"🎩 Match of the day: {m['ev']} v {m['dep']}") and metin.endswith(ANSVAR)
    assert uzunluk(metin) <= LIMIT and "Over 2.5 goals 61%" in metin and "Both teams score 52%" in metin
    assert f"{round(100 * m['aci']['olasilik'])}% at {m['aci']['oran']:.2f}" in metin
    assert "Not in today's coupons." in metin
    gun["secilen"] = [{"durum": "bekliyor", "ayaklar": [{"aday_id": m["aci"]["aday_id"]}]}]
    assert "coupon later today" in likely.mac_metni(m, gun, AYAR)
    gun["secilen"][0]["tweet_id"] = "t1"
    assert "leg in today's coupon" in likely.mac_metni(m, gun, AYAR)
    # Paylaşım: saati gelince bir kez, ilki anketli; maç başlamak üzereyse atlanır
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: OTO)
    likely.kaydet({"gunler": [{"tarih": "2026-10-10", "oto": True, "secilen": [], "maclar": plan}]})
    x = SahteX()
    an = datetime.fromisoformat(plan[0]["saat"])
    assert likely.oto_mac(AYAR, x, an) and len(x.postlar) == 1 and x.postlar[0]["metin"] == likely.mac_metni(plan[0], {"secilen": []}, AYAR)
    assert not likely.oto_mac(AYAR, x, an + timedelta(minutes=5))  # 10 dakikadan yakın: bekler
    gec = datetime.fromisoformat(plan[-1]["baslama"])
    likely.oto_mac(AYAR, x, gec)
    kayit = likely.yukle()["gunler"][0]["maclar"]
    assert all(n.get("tweet_id") for n in kayit)  # hepsi ya atıldı ya da "gecti"
    assert len(x.postlar) == sum(n["tweet_id"] not in ("gecti", "denetci", "tekrar") for n in kayit)
    assert kayit[-1]["tweet_id"] == "gecti"  # başlamak üzere olan maçın postu atılmaz


def test_E1_mac_postlari_acikken_buyuk_mac_rakam_postu_yok():
    bilgi = likely.bilgi_hazirla(_analizli(), "2026-10-10", SIMDI, OTO)
    assert not [b for b in bilgi if b["tur"] in ("favori", "gol", "denk")]


def test_E1_duyuru_sorusu_ve_18():
    tum = {likely.duyuru_metni(3, f"2026-10-{g:02d}") for g in range(1, 31)}
    for t in tum:
        assert "💬 " in t and t.endswith(ANSVAR) and uzunluk(t) <= LIMIT
    assert len({t.split("💬 ")[1].split("\n")[0] for t in tum}) >= 3  # soru günden güne değişir


def test_E1_yatan_kupon_sonucu_gelmeyen_ayagi_beklemez(monkeypatch, tmp_path):
    """25 Ekim 2026: 24 Ekim kuponu iki ayakla yatmıştı ama üçüncü ayağın (ilk yarı skoru yok) sonucu gelmediği için
    sonuç postu 30 saat bekleyecekti. Yatan kupon, bitişten 3 saat sonra "⏳ no result yet" ile sonuçlanır."""
    from bot import likely_gorsel
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: OTO)
    bas = SIMDI.isoformat()
    ayak = lambda fid, ev, dep, pazar, etiket: {"aday_id": f"{fid}-{pazar}", "fixture_id": fid, "pazar": pazar, "ev": ev,
                                                "dep": dep, "lig": "L", "baslama": bas, "etiket": etiket, "oran": 1.3,
                                                "olasilik": 0.8, "deger": 0.0, "durum": "bekliyor", "skor": None}
    kupon = {"ad": "gunun-kuponu", "oto": True, "oran": 2.2, "olasilik": 0.5, "deger": 0.0, "durum": "bekliyor",
             "tweet_id": "t1", "yayin": bas,
             "ayaklar": [ayak(1, "Esbjerg", "Fredericia", "CSX2", "Double chance X2"),
                         ayak(2, "Arda", "Levski", "IYA15", "1st half Under 1.5 goals")]}
    likely.kaydet({"gunler": [{"tarih": "2026-10-10", "durum": "secildi", "secilen": [kupon]}]})
    al = lambda maclar, korner: {1: {"durum": "bitti", "skor": (2, 1), "iy": (1, 0), "korner": None},
                                 2: {"durum": "bekliyor"}}
    gh = SahteGH()
    likely.sonuclar(AYAR, al, gh, SIMDI + timedelta(hours=3))
    k = likely.yukle()["gunler"][0]["secilen"][0]
    assert k["durum"] == "yatti" and not k.get("sonuc_metni")  # henüz 3 saat dolmadı
    likely.sonuclar(AYAR, al, gh, SIMDI + likely.MAC_SURESI + likely.YATAN_BEKLE)
    k = likely.yukle()["gunler"][0]["secilen"][0]
    assert k["durum"] == "yatti" and "⏳ Arda v Levski: 1st half Under 1.5 goals (no result yet)" in k["sonuc_metni"]
    assert "❌ Esbjerg 2-1 Fredericia" in k["sonuc_metni"] and uzunluk(k["sonuc_metni"]) <= LIMIT
    assert k["ayaklar"][1]["sonucsuz"] and k["ayaklar"][1]["durum"] == "bekliyor"
    assert likely_gorsel.sonuc_karti(k, "2026-10-10")[:4] == b"\x89PNG"
    # Tutan ya da henüz yatmamış kupon sonucu gelmeyen ayağı bekler (yalnızca yatan kupon beklemez)
    kupon2 = dict(kupon, ayaklar=[ayak(3, "A", "B", "CS1X", "Double chance 1X"), ayak(4, "C", "D", "IYA15", "x")])
    likely.kaydet({"gunler": [{"tarih": "2026-10-10", "durum": "secildi", "secilen": [kupon2]}]})
    al2 = lambda maclar, korner: {3: {"durum": "bitti", "skor": (1, 0), "iy": (0, 0), "korner": None}, 4: {"durum": "bekliyor"}}
    likely.sonuclar(AYAR, al2, gh, SIMDI + timedelta(hours=10))
    k2 = likely.yukle()["gunler"][0]["secilen"][0]
    assert k2["durum"] == "bekliyor" and not k2.get("sonuc_metni")


def test_E2_karakter_metni_oyun_adini_kisaltamaz():
    """25 Ekim 2026: sesli yazım "Double chance X2"yi "X2" diye kısaltmıştı; artık metin reddedilir, şablon gider."""
    sablon = ("❌ Coupon down.\n\n❌ Esbjerg 2-1 FC Fredericia: Double chance X2\n✅ A 2-0 B: Both teams score\n\n"
              "Record: 23 of 51 landed.\n18+ | Play responsibly")
    zorunlu = ["Esbjerg", "FC Fredericia", "Double chance X2", "A", "B", "Both teams score"]
    assert likely.ses_uygun(sablon, sablon, zorunlu) == []
    kisa = sablon.replace("Double chance X2", "X2")
    assert "kısaltılmış oyun adı" in likely.ses_uygun(kisa, sablon, zorunlu)
    assert "eksik maç/oyun/oran" in likely.ses_uygun(kisa, sablon, zorunlu)
    assert likely.ses_uygun(sablon.replace("Both teams score", "BTTS"), sablon, []) != []
    assert "Double chance X2" in likely._zorunlu([{"ev": "E", "dep": "D", "oran": 1.2, "etiket": "Double chance X2"}])


def test_E1_baska_gune_alinan_mac_iade_ve_postponed_yazar(monkeypatch, tmp_path):
    """25 Ekim 2026: Arda-Levski 24 Ekim'den 27 Ekim'e alındı; API "PST" değil yeni tarihli "NS" döndürdü ve ayak
    sonuçsuz kaldı. Kayıtlı saatten 24 saatten fazla ileri alınan maç iade sayılır, postta "postponed, void" yazar."""
    from bot import football
    yeni = {"fixture": {"id": 2, "date": "2026-10-27T17:00:00+02:00", "status": {"short": "NS"}}, "score": {}}
    assert football._sonuc(yeni) == {"durum": "bekliyor", "skor": None, "tarih": "2026-10-27T17:00:00+02:00"}
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: OTO)
    bas = SIMDI.isoformat()
    ayak = lambda fid, pazar, etiket: {"aday_id": f"{fid}-{pazar}", "fixture_id": fid, "pazar": pazar, "ev": f"E{fid}",
                                       "dep": f"D{fid}", "lig": "L", "baslama": bas, "etiket": etiket, "oran": 1.4,
                                       "olasilik": 0.8, "deger": 0.0, "durum": "bekliyor", "skor": None}
    kupon = {"ad": "gunun-kuponu", "oto": True, "oran": 2.0, "olasilik": 0.6, "deger": 0.0, "durum": "bekliyor",
             "tweet_id": "t1", "yayin": bas, "ayaklar": [ayak(1, "CS1X", "Double chance 1X"), ayak(2, "IYA15", "x")]}
    likely.kaydet({"gunler": [{"tarih": "2026-10-10", "durum": "secildi", "secilen": [kupon]}]})
    al = lambda maclar, korner: {1: {"durum": "bitti", "skor": (1, 0), "iy": (0, 0), "korner": None},
                                 2: {"durum": "bekliyor", "skor": None, "tarih": (SIMDI + timedelta(days=3)).isoformat()}}
    likely.sonuclar(AYAR, al, SahteGH(), SIMDI + timedelta(hours=3))
    k = likely.yukle()["gunler"][0]["secilen"][0]
    assert k["ayaklar"][1]["durum"] == "iade" and k["ayaklar"][1]["ertelendi"]
    assert k["durum"] == "tuttu" and k["son_oran"] == 1.4  # iade ayak 1.00 sayılır
    assert "↩️ E2 v D2: x (postponed, void)" in k["sonuc_metni"]
    # Aynı gün içinde birkaç saat kayan maç ertelenmiş sayılmaz
    kupon["ayaklar"][1].update(durum="bekliyor")
    likely.kaydet({"gunler": [{"tarih": "2026-10-10", "durum": "secildi", "secilen": [dict(kupon, durum="bekliyor")]}]})
    al2 = lambda maclar, korner: {2: {"durum": "bekliyor", "skor": None, "tarih": (SIMDI + timedelta(hours=4)).isoformat()}}
    likely.sonuclar(AYAR, al2, SahteGH(), SIMDI + timedelta(hours=3))
    assert likely.yukle()["gunler"][0]["secilen"][0]["ayaklar"][1]["durum"] == "bekliyor"


def test_E1_dev_mac_adayi_olmasa_da_gunun_maci_olur():
    """25 Ekim 2026: Barcelona v Real Madrid'in havuzdaki tek adayı kupona giremeyen "Double chance 12" olduğu için
    maç postu planlanmamıştı. Büyük maç, kupon adayı yoksa piyasanın en olası oyunuyla girer; dev maç (iki takım da
    taraftar etiketli) en önde ve "Match of the day"."""
    clasico = mac(9, "Barcelona", "Real Madrid", 11, 140)
    analizler = _analizli(MACLAR) + [{**clasico, "kaynak": "piyasa", "guven": "yuksek",
                                      "p": {"MS1": 0.57, "MSX": 0.18, "MS2": 0.25, "UST25": 0.81, "KGVAR": 0.77}}]
    oranlar = {**ORANLAR, 9: oran_seti(0.57, 0.18, 0.81, 0.93)}
    adaylar = [c for c in likely.havuz(analizler, oranlar, AYAR, OTO, SIMDI) if c["fixture_id"] != 9]  # adayı yok
    assert all(m["fixture_id"] != 9 for m in likely.mac_planla(analizler, adaylar, [], SIMDI, OTO, AYAR))  # eski hata
    plan = likely.mac_planla(analizler, adaylar, [], SIMDI, OTO, AYAR, oranlar)
    m = next(m for m in plan if m["fixture_id"] == 9)
    assert m.get("gunun_maci")
    assert OTO.oran_min <= m["aci"]["oran"] <= OTO.oran_max and m["aci"]["oran"] == round(oranlar[9]["Bet365"][m["aci"]["aday_id"].split("-")[1]], 2)
    metin = likely.mac_metni(m, {"secilen": []}, AYAR)
    assert metin.startswith("🎩 Match of the day: Barcelona v Real Madrid") and "Not in today's coupons." in metin


def test_E6_buyuk_mac_ayagi_yuzde_6_taban():
    """25 Ekim 2026 (sahibinin kararı): büyük maç ayağı adil fiyatın %6 altına kadar; diğerleri %4."""
    aday = {"pazar": "UST25", "deger": -0.05, "uyum": True, "kaynak": "Pinnacle", "tur": "guvenli", "olasilik": 0.8}
    assert likely.kupona_uygun({**aday, "buyuk": True}, OTO)
    assert not likely.kupona_uygun({**aday, "buyuk": False}, OTO)
    assert not likely.kupona_uygun({**aday, "buyuk": True, "deger": -0.065}, OTO)
    assert not likely.kupona_uygun({**aday, "buyuk": True, "pazar": "CS12"}, OTO)  # Double chance 12 yine yok
    # Havuz büyük maçta −%5'lik ayağı alır, küçük maçta almaz (aynı fiyatlar)
    b = oran_seti(0.80, 0.12, 0.60, 0.80)
    b["Bet365"] = {k: round(v * 0.975, 3) for k, v in b["Bet365"].items()}  # ~−%5 değer
    buyuk_mac, kucuk_mac = mac(1, "Arsenal", "Burnley", 6), mac(2, "Sabadell", "Tenerife", 6, lig_id=141)
    ha = likely.havuz([buyuk_mac, kucuk_mac], {1: b, 2: b}, AYAR, OTO, SIMDI)
    assert any(c["fixture_id"] == 1 and -0.06 <= c["deger"] < -0.04 and likely.kupona_uygun(c, OTO) for c in ha)
    assert not any(c["fixture_id"] == 2 and likely.kupona_uygun(c, OTO) for c in ha)


def test_E6_dev_mac_kuponu(monkeypatch, tmp_path):
    """Tek seferlik istisna (25 Ekim 2026): dev maç hiçbir kupona girmediyse sınır dolu olsa da onun ayağıyla kupon."""
    monkeypatch.setattr(likely, "DOSYA", tmp_path / "likely.json")
    monkeypatch.setattr(likely, "ayar_yukle", lambda *a, **k: OTO)
    clasico = mac(9, "Barcelona", "Real Madrid", 9, 140)
    analizler = _analizli(MACLAR) + [{**clasico, "kaynak": "piyasa", "guven": "yuksek",
                                      "p": {"MS1": 0.57, "MSX": 0.18, "MS2": 0.25, "UST25": 0.81, "KGVAR": 0.77}}]
    oranlar = {**ORANLAR, 9: oran_seti(0.57, 0.18, 0.81, 0.93)}
    dolu = [{"ad": f"k{i}", "oto": True, "durum": "bekliyor", "paylas": (SIMDI + timedelta(hours=1, minutes=40 * i)).isoformat(),
             "ayaklar": [{"fixture_id": 6}]} for i in range(5)]
    plan = [{"fixture_id": 9, "ev": "Barcelona", "dep": "Real Madrid", "saat": (SIMDI + timedelta(hours=7)).isoformat(),
             "aci": {"aday_id": "9-IYU05", "etiket": "x", "olasilik": 0.85, "oran": 1.11}}]
    likely.kaydet({"gunler": [{"tarih": "2026-10-10", "oto": True, "secilen": dolu, "maclar": plan}]})
    d = likely.dev_kupon(AYAR, analizler, oranlar, SIMDI, yaz=lambda *_: None)
    gun = likely.yukle()["gunler"][0]
    assert d and len(gun["secilen"]) == 6 and d["ad"] == "buyuk-maclar" and "istisna" in d
    assert any(a["fixture_id"] == 9 for a in d["ayaklar"]) and all(a["fixture_id"] != 6 for a in d["ayaklar"])
    assert OTO.oto_oran_min <= d["oran"] <= OTO.oto_oran_max and d["olasilik"] >= OTO.oto_min_tutma
    ayak = next(a for a in d["ayaklar"] if a["fixture_id"] == 9)
    assert gun["maclar"][0]["aci"]["aday_id"] == ayak["aday_id"]  # maç postu kupondaki ayağı gösterir
    assert likely.dev_kupon(AYAR, analizler, oranlar, SIMDI, yaz=lambda *_: None) is None  # ikinci kez eklenmez
