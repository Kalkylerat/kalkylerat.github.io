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


class SahteX:
    def __init__(self):
        self.postlar, self.medya, self.silinen = [], 0, []

    def sil(self, tweet_id):
        self.silinen.append(tweet_id)

    def medya_yukle(self, png):
        self.medya += 1
        return f"m{self.medya}"

    def gonder(self, metin, yanit=None, medya=None, **_):
        self.postlar.append({"metin": metin, "yanit": yanit, "medya": medya})
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
    maclar = [harita[i]["fixture_id"] for k in secilen for i in k["ayaklar"]]
    assert len(maclar) == len(set(maclar))  # iki kupon aynı maçı paylaşmaz
    # Aralıktaki kuponlar içinde tutma ihtimali en yüksek olan: aynı ayaklardan daha olası bir kupon kurulamaz
    import itertools
    uygun = [a for a in adaylar if a["uyum"] and a["deger"] >= OTO.oto_min_deger]
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
    """Üçüncü kupon: yalnızca büyük maçlar, günün kuponunun sınırlarıyla, öncekilerle maç paylaşmaz; günde en fazla 3 kupon."""
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
    assert OTO.oto_max_kupon == 3 and len(secilen) <= 3 and adlar[0] == "gunun-kuponu" and "buyuk-maclar" in adlar
    b = secilen[adlar.index("buyuk-maclar")]
    assert all(harita[i]["buyuk"] for i in b["ayaklar"]) and len(b["ayaklar"]) <= OTO.oto_max_ayak
    assert OTO.oto_oran_min <= b["oran"] <= OTO.oto_oran_max and b["olasilik"] >= OTO.oto_min_tutma and b["deger"] >= OTO.oto_min_kupon_deger
    maclar = [harita[i]["fixture_id"] for k in secilen for i in k["ayaklar"]]
    assert len(maclar) == len(set(maclar))
    metin = likely.kupon_metni(b, [harita[i] for i in b["ayaklar"]], "t", gorselli=True)
    assert any(a in metin for a in likely.BUYUK_ACILIS) and f"{round(100 * b['olasilik'])}% to land" in metin
    # Büyük maç yoksa üçüncü kupon çıkmaz
    assert "buyuk-maclar" not in [k["ad"] for k in likely.otomatik_sec(likely.havuz(kucuk + orta, oranlar, AYAR, OTO, SIMDI), OTO)]


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


def test_otomatik_paylasim_bir_kez_gorselli_ve_sonuc_yaniti(oto):
    from bot import likely_gorsel
    x = SahteX()
    assert likely.oto_paylas(AYAR, x, SIMDI + timedelta(minutes=1), kart=likely_gorsel.kupon_karti) == 0  # zamanı gelmedi
    gun = likely.yukle()["gunler"][0]
    zaman = datetime.fromisoformat(gun["secilen"][0]["paylas"])
    assert likely.oto_paylas(AYAR, x, zaman, kart=likely_gorsel.kupon_karti) == 1
    likely.oto_paylas(AYAR, x, zaman, kart=likely_gorsel.kupon_karti)
    assert sum(p["yanit"] is None for p in x.postlar) == len({p["metin"] for p in x.postlar})  # aynı kupon iki kez gitmez
    k = likely.yukle()["gunler"][0]["secilen"][0]
    post = x.postlar[0]
    assert k["tweet_id"] == "t1" and post["medya"] == ["m1"] and post["yanit"] is None
    assert post["metin"].endswith(ANSVAR) and f"{round(100 * k['olasilik'])}% to land" in post["metin"] and uzunluk(post["metin"]) <= LIMIT
    # Sonuç: kupon postunun altına yanıt, bir kez
    idler = {a["fixture_id"] for a in k["ayaklar"]}
    adet = len(x.postlar)
    likely.sonuclar(AYAR, bitir({f: (2, 0) for f in {a["fixture_id"] for kk in likely.yukle()["gunler"][0]["secilen"] for a in kk["ayaklar"]}}),
                    oto, SIMDI + timedelta(hours=14))
    assert likely.oto_sonuc_paylas(AYAR, x, SIMDI + timedelta(hours=14)) >= 1
    yanit = x.postlar[adet]
    assert yanit["yanit"] == "t1" and "Record:" in yanit["metin"] and yanit["metin"].endswith(ANSVAR)
    assert likely.oto_sonuc_paylas(AYAR, x, SIMDI + timedelta(hours=15)) == 0 and idler


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
    bilgi = likely.bilgi_hazirla(analizler, "2026-10-10", SIMDI, OTO)
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
    denk = likely.bilgi_hazirla([dict(a, p=dict(a["p"], UST25=0.45)) for a in analizler], "2026-10-10", SIMDI, OTO)
    assert [b["tur"] for b in denk] == ["ders", "favori", "denk", "ders"] and "Wales v Norway" in denk[2]["metin"]
    assert [b["tur"] for b in likely.bilgi_hazirla([], "2026-10-10", SIMDI, OTO)] == ["ders", "ders"]
    # Başlamış ya da başlamak üzere olan maçtan rakam yazılmaz
    gec = likely.bilgi_hazirla([dict(a, baslama=(SIMDI + timedelta(minutes=30)).isoformat()) for a in analizler], "2026-10-10", SIMDI, OTO)
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
