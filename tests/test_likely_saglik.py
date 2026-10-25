"""Mr. Likely canlı denetimi (SOZLESME G): sahibinin ilkelerinden sapma alarm olur."""

from datetime import datetime, timedelta, timezone

from bot import config, likely, likely_saglik as ls
from bot.tweets import ANSVAR

UTC = timezone.utc
AYAR = config.yukle()
CFG = likely.LikelyAyar(aktif=True, mod="otomatik", oto_kasa=True)
SIMDI = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
CLASICO = {"fixture_id": 9, "ev": "Barcelona", "dep": "Real Madrid", "lig_id": 140, "kaynak": "piyasa",
           "baslama": "2026-10-25T21:00:00+01:00"}
KUCUK = {"fixture_id": 8, "ev": "Sabadell", "dep": "Tenerife", "lig_id": 141, "kaynak": "piyasa",
         "baslama": "2026-10-25T14:00:00+01:00"}


def mesajlar(veri, analizler=(), simdi=SIMDI, cfg=CFG):
    return [m for _, m in ls.sorunlar(veri, list(analizler), simdi, AYAR, cfg)]


def test_G1_dev_mac_planda_yoksa_alarm():
    assert ls.dev_mac(CLASICO) and not ls.dev_mac(KUCUK)
    v = {"gunler": [{"tarih": "2026-10-25", "oto": True, "secilen": [], "maclar": []}]}
    assert any("Barcelona v Real Madrid günün maçı postlarında yok" in m for m in mesajlar(v, [CLASICO, KUCUK]))
    v["gunler"][0]["maclar"] = [{"fixture_id": 9, "ev": "Barcelona", "dep": "Real Madrid", "saat": "2026-10-25T19:30:00+01:00"}]
    assert not any("günün maçı postlarında yok" in m for m in mesajlar(v, [CLASICO]))
    satir = ls.plan_ozeti(v["gunler"][0], [CLASICO], AYAR)
    assert satir == ["🏟️ Barcelona v Real Madrid: maç postu 19:30 · kuponda yok"]


def test_G2_G4_paylasilan_metin_taranir():
    temiz = "🎩 Match of the day: Barcelona v Real Madrid.\n\n🛡️ Safest angle: Double chance 1X, 75%.\n\n" + ANSVAR
    assert ls.metin_ihlalleri(temiz) == []
    assert "bahis sitesi adı" in ls.metin_ihlalleri(temiz.replace("Safest", "Bet365"))
    assert "kısaltılmış oyun adı" in ls.metin_ihlalleri(temiz.replace("Double chance 1X", "1X"))
    assert "kısaltılmış oyun adı" in ls.metin_ihlalleri(temiz.replace("Double chance 1X", "BTTS"))
    assert "18+ satırı yok" in ls.metin_ihlalleri(temiz.replace(ANSVAR, "Play responsibly"))
    v = {"gunler": [{"tarih": "2026-10-25", "secilen": [{"ad": "k", "tweet_id": "1", "metin": temiz.replace("Double chance 1X", "X2"),
                                                         "ayaklar": [], "durum": "bekliyor"}]}]}
    assert any("kupon k: paylaşılan metin kural dışı: kısaltılmış oyun adı" in m for m in mesajlar(v))


def test_G6_geciken_kupon_mac_sonuc_kasa_alarm():
    bas = (SIMDI - timedelta(hours=8)).isoformat()
    v = {"kasa_duyuru": {"tarih": "2026-10-24"}, "gunler": [{
        "tarih": "2026-10-24", "oto": True, "duyuru": {"tweet_id": "5", "zaman": bas, "metin": "x\n18+"},
        "secilen": [{"ad": "a", "oto": True, "paylas": (SIMDI - timedelta(hours=1)).isoformat(), "durum": "bekliyor",
                     "ayaklar": []},
                    {"ad": "b", "oto": True, "tweet_id": "2", "durum": "yatti",
                     "ayaklar": [{"fixture_id": 1, "ev": "E", "dep": "D", "baslama": bas, "oran_kaynagi": "Bet365"}]}],
        "maclar": [{"fixture_id": 3, "ev": "X", "dep": "Y", "saat": (SIMDI - timedelta(hours=1)).isoformat()},
                   {"fixture_id": 4, "ev": "Z", "dep": "W", "saat": bas, "tweet_id": "denetci"}]}]}
    m = " | ".join(mesajlar(v))
    assert "a: planlanan saatten 30 dk geçti, kupon paylaşılmadı" in m
    assert "b: son maç başlayalı 6 saat oldu, sonuç postu hâlâ yok" in m
    assert "maç X v Y: planlanan saatten 30 dk geçti" in m and "maç Z v W: atılmadı (denetci)" in m
    assert "kasa grafiği ertesi sabah 09:30'a kadar çıkmadı" in m
    assert not mesajlar(v, cfg=likely.LikelyAyar(aktif=True, mod="elle"))  # elle modda denetim yok


def test_G6_ayak_fiyati_kupon_sitesi_disindan_alarm():
    v = {"gunler": [{"tarih": "2026-10-25", "secilen": [{"ad": "k", "tweet_id": "1", "durum": "bekliyor", "ayaklar": [
        {"fixture_id": 1, "ev": "E", "dep": "D", "baslama": SIMDI.isoformat(), "oran_kaynagi": "William Hill"}]}]}]}
    assert any("ayak fiyatı Bet365 dışından" in m for m in mesajlar(v))


def test_G6_canli_denetim_hata_verirse_sessiz_kalmaz(monkeypatch):
    monkeypatch.setattr(likely, "yukle", lambda: (_ for _ in ()).throw(ValueError("bozuk kayıt")))
    sonuc = ls.canli(AYAR, SIMDI)
    assert len(sonuc) == 1 and "canlı denetimi çalışmadı" in sonuc[0][1]
