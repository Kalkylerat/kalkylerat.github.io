"""SOZLESME.md G bölümü (Deep Space Log) için testler. ffmpeg gerektirmez; hızlıdır."""

import json
import re
from pathlib import Path

import numpy as np
import pytest

from deepspace import kapak, kapilar, metin, ortak, ses, video
from deepspace.sahne import TURLER, Sahne

KOK = Path(__file__).resolve().parent.parent
AYAR = ortak.ayar_yukle()
GOREV_001 = KOK / "deepspace" / "gorevler" / "001-trappist"


def _gorev(tmp_path, n=20, **ek):
    parcalar = []
    for i in range(n):
        parcalar.append({"ad": f"World {i + 1}", "kisa": "a real place", "dosya": f"{i + 1:02d}.mp3",
                         "tur": TURLER[i % len(TURLER)], "palet": ["#000000", "#223344", "#556677", "#aabbcc"],
                         "bilgi": f"Fact {i + 1}.", "hedef_sure": "6:15", "anahtar": "D minor", "bpm": 58,
                         "style": "ambient, instrumental", "exclude": "drums, vocals", "lyrics": "[Intro]"})
    g = {"no": 7, "seri": "focus", "hedef": "World 3", "uzaklik": "10 light-years", "tohum": 7007,
         "ozet": "A test route.", "parca": parcalar, "klasor": tmp_path}
    g.update(ek)
    return g


def _bolumler(sureler, capraz=8.0, lufs=-16.0, tepe=-1.6, sessiz=None):
    basla = ses.zaman_cizelgesi(sureler, capraz)
    return {"capraz_gecis_sn": capraz, "toplam_sn": ses.toplam_sure(sureler, capraz),
            "parcalar": [{"no": i + 1, "ad": f"World {i + 1}", "basla": b, "sure": s,
                          "olcum": {"sure": s, "lufs": -10.0, "tepe_dbtp": -0.3,
                                    "sessiz": (sessiz or {}).get(i, [])}}
                         for i, (b, s) in enumerate(zip(basla, sureler))],
            "master": {"lufs": lufs, "tepe_dbtp": tepe}}


def _yaz_bolumler(g, b):
    (ortak.cikti(g) / "bolumler.json").write_text(json.dumps(b), encoding="utf-8")


def _kirmizi(kontroller):
    return [k["ad"] for k in kontroller if not k["gecti"]]


# ---------- G1 ----------
def test_G1_kimlik_ve_seriler():
    assert AYAR["kanal"]["ad"] == "Deep Space Log"
    assert AYAR["kanal"]["maskot"] == "PROBE-7"
    assert AYAR["kanal"]["youtube_kanal_id"] == "UCtJHvFs1UuIKwTUhcWVyWIg"
    assert AYAR["kanal"]["dil"] == "en"
    s = AYAR["seri"]
    assert (s["focus"]["hedef_dakika"], s["focus"]["parca_sayisi"]) == (120, 20)
    assert (s["sleep"]["hedef_dakika"], s["sleep"]["parca_sayisi"]) == (180, 20)
    assert (s["drift"]["hedef_dakika"], s["drift"]["parca_sayisi"]) == (120, 20)


# ---------- G2 ----------
def test_G2_sure_hedefte_ve_parca_sinirlari():
    assert AYAR["ses"]["parca_min_sn"] == 180 and AYAR["ses"]["parca_max_sn"] == 600
    assert AYAR["ses"]["sure_tolerans"] == pytest.approx(0.10)
    iyi = _bolumler([450] * 16)
    assert not _kirmizi(kapilar.ses(iyi, AYAR, 120))
    kisa = _bolumler([200] * 16)  # ~52 dk
    assert "toplam süre hedefte" in _kirmizi(kapilar.ses(kisa, AYAR, 120))
    uzun_parca = _bolumler([450] * 15 + [700])
    assert "parça 16 süresi" in _kirmizi(kapilar.ses(uzun_parca, AYAR, 120))


def test_G2_zaman_cizelgesi_capraz_gecisi_dusurur():
    assert ses.zaman_cizelgesi([100, 200, 300], 8) == [0, 92, 284]
    assert ses.toplam_sure([100, 200, 300], 8) == 584


def test_G2_dongu_ile_sisirme_yok_video_sesten_uzun_olamaz(tmp_path):
    b = _bolumler([450] * 16)
    plan = video.bolum_plani(b, 24)
    toplam_kare = sum(p["kare"] for p in plan)
    assert toplam_kare == round(b["toplam_sn"] * 24)
    duz = [p for p in plan if p["tur"] == "duz"]
    assert len(duz) == 16 and len([p for p in plan if p["tur"] == "gecis"]) == 15


# ---------- G3 ----------
def test_G3_ses_seviyesi_tepe_ve_bosluk():
    a = AYAR["ses"]
    assert (a["hedef_lufs"], a["lufs_tolerans"], a["tepe_dbtp"], a["capraz_gecis_sn"], a["sessizlik_max_sn"]) == \
        (-16.0, 1.0, -1.5, 8, 4)
    assert "master ses yüksekliği" in _kirmizi(kapilar.ses(_bolumler([450] * 16, lufs=-12.5), AYAR, 120))
    assert "master tepe" in _kirmizi(kapilar.ses(_bolumler([450] * 16, tepe=-0.2), AYAR, 120))
    bosluklu = _bolumler([450] * 16, sessiz={4: [(200.0, 207.0)]})
    assert "parça 05 ortasında boşluk yok" in _kirmizi(kapilar.ses(bosluklu, AYAR, 120))
    # baştaki ve sondaki doğal sessizlik sorun değil
    kenar = _bolumler([450] * 16, sessiz={4: [(0.0, 6.0), (444.0, 450.0)]})
    assert not _kirmizi(kapilar.ses(kenar, AYAR, 120))


# ---------- G4 ----------
def test_G4_tohum_hedef_ve_ses_tekrari_yakalanir(tmp_path):
    g = _gorev(tmp_path)
    kayit = {"gorevler": [{"no": 1, "hedef": "World 3", "tohum": 1001, "ses_ozetleri": ["abc"]}]}
    assert "hedef gök cismi yeni" in _kirmizi(kapilar.ozgunluk(g, kayit))
    g2 = _gorev(tmp_path, hedef="Vega", tohum=1001)
    assert "tohum yeni" in _kirmizi(kapilar.ozgunluk(g2, kayit))
    g3 = _gorev(tmp_path, hedef="Vega", tohum=5)
    assert "ses daha önce yüklenmemiş" in _kirmizi(kapilar.ozgunluk(g3, kayit, ["abc", "def"]))
    assert not _kirmizi(kapilar.ozgunluk(g3, kayit, ["xyz", "def"]))


def test_G4_her_parcanin_kendi_sahnesi(tmp_path):
    g = _gorev(tmp_path)
    tohumlar = [video._tohum(g, i) for i in range(len(g["parca"]))]
    assert len(set(tohumlar)) == len(tohumlar)


def test_G4_kayit_dosyasi_gecerli():
    kayit = ortak.kayit_yukle()
    tohumlar = [g["tohum"] for g in kayit["gorevler"]]
    hedefler = [g["hedef"].lower() for g in kayit["gorevler"]]
    assert len(tohumlar) == len(set(tohumlar)) and len(hedefler) == len(set(hedefler))


# ---------- G5 ----------
def test_G5_metin_kurallari(tmp_path):
    g = _gorev(tmp_path)
    b = _bolumler([450] * 16)
    _yaz_bolumler(g, b)
    yt = metin.uret(g, AYAR)
    assert not _kirmizi(kapilar.metin(yt, AYAR, b))
    assert len(yt["baslik"]) <= 100 and "World 3" in yt["baslik"]
    assert yt["aciklama"].count("\n0:00 World 1") == 1
    for i in range(16):
        assert f"World {i + 1}: Fact {i + 1}." in yt["aciklama"]
    assert "How this music is made" in yt["aciklama"]
    bozuk = dict(yt, baslik=yt["baslik"] + " | Hans Zimmer style")
    assert "yasak kelime yok (sanatçı/film adı)" in _kirmizi(kapilar.metin(bozuk, AYAR, b))


def test_G5_bolum_bicimi():
    assert ortak.zaman(0) == "0:00"
    assert ortak.zaman(472) == "7:52"
    assert ortak.zaman(3790) == "1:03:10"


def test_G5_istemde_yasak_kelime_ve_vokal(tmp_path):
    g = _gorev(tmp_path)
    assert not _kirmizi(kapilar.gorev_dosyasi(g, AYAR))
    g["parca"][3]["style"] = "ambient like Interstellar, instrumental"
    g["parca"][5]["exclude"] = "drums"
    k = _kirmizi(kapilar.gorev_dosyasi(g, AYAR))
    assert "istemlerde ve bilgilerde yasak kelime yok" in k
    assert "her istem enstrümantal ve vokal yasaklı" in k


def test_G5_gorev_001_kapidan_gecer():
    g, a = ortak.gorev_yukle(GOREV_001)
    assert not _kirmizi(kapilar.gorev_dosyasi(g, a))
    assert g["hedef"] in [p["ad"] for p in g["parca"]]


# ---------- G6 ----------
@pytest.mark.parametrize("tur", TURLER)
def test_G6_sahne_kusursuz_doner(tur):
    s = Sahne({"tur": tur, "palet": ["#050510", "#203040", "#4070a0", "#d0e0f0"], "halka": tur == "gaz"},
              tohum=3, W=192, H=108, L=40.0)
    k0, kL = s.kare(0.0).astype(int), s.kare(40.0 - 1e-6).astype(int)
    assert np.abs(k0 - kL).mean() < 0.5
    assert np.abs(k0 - s.kare(20.0).astype(int)).mean() > 0  # gerçekten hareket ediyor


def test_G6_video_boyutu_ve_ucretli_servis_yok():
    assert (AYAR["video"]["genislik"], AYAR["video"]["yukseklik"]) == (3840, 2160)
    for dosya in (KOK / "deepspace").glob("*.py"):
        metin_ = dosya.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(anthropic|openai|elevenlabs)", metin_, re.M), dosya.name
        if dosya.name != "google.py":  # ağa yalnızca ücretsiz Google API'leri için çıkılır
            assert not re.search(r"^\s*(import|from)\s+requests", metin_, re.M), dosya.name


def test_G6_canli_tablo_kusursuz_doner_ve_gorsel_secilir(tmp_path):
    from PIL import Image
    from deepspace.tablo import Tablo
    gorsel = tmp_path / "gorsel"
    gorsel.mkdir()
    rng = np.random.default_rng(0)
    Image.fromarray((rng.random((120, 200, 3)) * 255).astype(np.uint8)).save(gorsel / "03.png")
    t = Tablo(gorsel / "03.png", W=160, H=90, L=60.0, tohum=1)
    assert np.abs(t.kare(0).astype(int) - t.kare(60.0 - 1e-6).astype(int)).mean() < 0.5
    assert np.abs(t.kare(0).astype(int) - t.kare(30.0).astype(int)).mean() > 0
    g = _gorev(tmp_path)
    assert video.parca_gorseli(g, 2)[0] == gorsel / "03.png"
    assert video.parca_gorseli(g, 0) == (None, None)
    assert isinstance(video.sahne_nesnesi(g, 2, 160, 90, 60.0), Tablo)
    assert isinstance(video.sahne_nesnesi(g, 0, 160, 90, 60.0), Sahne)


def test_G6_marka_filtresi_tek_kaynaktan(tmp_path):
    from deepspace import renk
    img = (np.random.default_rng(1).random((20, 30, 3)) * 255).astype(np.uint8)
    for ad, ton in renk.SECENEKLER.items():
        assert np.array_equal(renk.uygula(img, dict(ton, guc=0.0)), img), ad  # güç 0: dokunmaz
        sicak = renk.uygula(img, ton).astype(int)
        once = img.astype(int)
        assert (sicak[..., 0] - sicak[..., 2]).mean() > (once[..., 0] - once[..., 2]).mean(), ad  # daha sıcak
        assert np.abs(sicak - once).mean() < 40, ad  # hafif: görselin kendi renkleri korunur (9 Kasım 2026)
    cube = renk.cube_yaz(tmp_path / "m.cube", renk.SECENEKLER["ember_film"], boy=5)
    satir = cube.read_text().splitlines()
    assert satir[0] == "LUT_3D_SIZE 5" and len(satir) == 1 + 5 ** 3


# ---------- G7 ----------
def test_G7_kapak_en_fazla_3_kelime_ve_3_varyant(tmp_path):
    for ad in AYAR["seri"]:
        yazilar = kapak.kapak_yazilari({"seri": ad}, AYAR, 2)
        assert sum(len(y.split()) for y in yazilar) <= AYAR["metin"]["kapak_max_kelime"]
    assert len(kapak.VARYANTLAR) == 3


# ---------- G8 ----------
def _hazir_cikti(tmp_path, gecti=True):
    out = tmp_path / "cikti"
    out.mkdir(parents=True)
    (out / "rapor.json").write_text(json.dumps({"gecti": gecti}), encoding="utf-8")
    (out / "video.mp4").write_bytes(b"x" * 1000)
    (out / "youtube.json").write_text(json.dumps({"baslik": "T", "aciklama": "A", "etiketler": ["e"],
                                                  "sentetik_icerik": True}), encoding="utf-8")
    return out


def test_G8_onaysiz_ya_da_kirmizi_raporla_yukleme_yok(tmp_path):
    from deepspace import google
    out = _hazir_cikti(tmp_path)
    with pytest.raises(google.GoogleHatasi, match="onay"):
        google.onay_kontrol(out)
    google.onay_yaz(out, "sahip")
    assert google.onay_kontrol(out)["onaylayan"] == "sahip"
    (out / "video.mp4").write_bytes(b"y" * 1001)  # onaydan sonra değişen video yeniden onay ister
    with pytest.raises(google.GoogleHatasi, match="değişmiş"):
        google.onay_kontrol(out)
    kirmizi = _hazir_cikti(tmp_path / "k", gecti=False)
    with pytest.raises(google.GoogleHatasi, match="kırmızı"):
        google.onay_yaz(kirmizi, "sahip")


def test_G8_yukleme_gizli_ve_planli():
    from deepspace import google
    g = google.youtube_govdesi({"baslik": "T", "aciklama": "A", "etiketler": []}, None)
    assert g["status"]["privacyStatus"] == "private" and "publishAt" not in g["status"]
    p = google.youtube_govdesi({"baslik": "T", "aciklama": "A", "etiketler": []}, "2026-11-20T17:00:00Z")
    assert p["status"]["privacyStatus"] == "private" and p["status"]["publishAt"] == "2026-11-20T17:00:00Z"
    skill = (KOK / ".claude" / "skills" / "deep-space-log" / "SKILL.md").read_text(encoding="utf-8")
    assert "rapor.json" in skill and "denetçi" in skill.lower() and "ok" in skill


class _Yanit:
    def __init__(self, kod, govde=None, baslik=None):
        self.status_code, self._g, self.headers, self.text = kod, govde or {}, baslik or {}, ""

    def json(self):
        return self._g


def test_G8_devam_ettirilebilir_yukleme_parcalari(tmp_path, monkeypatch):
    from deepspace import google
    monkeypatch.setattr(google, "PARCA", 256 * 1024)
    dosya = tmp_path / "v.mp4"
    dosya.write_bytes(b"z" * (256 * 1024 * 2 + 100))
    araliklar = []

    class Oturum:
        def put(self, url, data, headers, timeout):
            araliklar.append(headers["Content-Range"])
            return _Yanit(200, {"id": "VID"}) if len(araliklar) == 3 else _Yanit(308)

    assert google._devam_ettir("u", dosya, "video/mp4", Oturum())["id"] == "VID"
    assert araliklar == ["bytes 0-262143/524388", "bytes 262144-524287/524388", "bytes 524288-524387/524388"]


# ---------- G9 ----------
def test_G9_sentetik_icerik_etiketi_ve_aciklama(tmp_path):
    g = _gorev(tmp_path)
    _yaz_bolumler(g, _bolumler([450] * 16))
    yt = metin.uret(g, AYAR)
    assert yt["sentetik_icerik"] is True
    assert "AI music tools" in yt["aciklama"]


# ---------- G10 ----------
def test_G10_reklam_yalnizca_parca_gecislerinde(tmp_path):
    g = _gorev(tmp_path)
    b = _bolumler([450] * 16)
    _yaz_bolumler(g, b)
    yt = metin.uret(g, AYAR)
    assert yt["reklam_noktalari"] == [ortak.zaman(p["basla"]) for p in b["parcalar"][1:]]


# ---------- G11 ----------
def test_G11_metin_sablonla_yapay_zeka_cagrisi_yok():
    t = (KOK / "deepspace" / "metin.py").read_text(encoding="utf-8")
    assert "anthropic" not in t and "requests" not in t


# ---------- G12 ----------
def test_G12_shorts():
    assert AYAR["shorts"]["adet"] == 3 and AYAR["shorts"]["sure_sn"] <= 60
    assert video.shorts_secimi(16, 3) == [3, 7, 11]
    assert len(video.shorts_secimi(4, 3)) == 3
