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
    assert "How this mission is made" in yt["aciklama"]
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
    cube = renk.cube_yaz(tmp_path / "m.cube", renk.SECENEKLER["altin_saat"], boy=5)
    satir = cube.read_text(encoding="utf-8").splitlines()
    assert satir[0] == "LUT_3D_SIZE 5" and len(satir) == 1 + 5 ** 3


@pytest.mark.skipif(__import__("importlib").util.find_spec("cv2") is None, reason="opencv yok")
def test_G6_3d_fotograf_kusursuz_doner(tmp_path):
    from PIL import Image
    from deepspace.tablo import Tablo3D
    rng = np.random.default_rng(2)
    Image.fromarray((rng.random((90, 160, 3)) * 255).astype(np.uint8)).save(tmp_path / "g.png")
    derin = np.tile(np.linspace(0, 1, 90, dtype=np.float32)[:, None], (1, 160))  # alt yakın, üst uzak
    t = Tablo3D(tmp_path / "g.png", derin, W=160, H=90, L=24.0, tohum=1)
    assert np.abs(t.kare(0).astype(int) - t.kare(24.0 - 1e-6).astype(int)).mean() < 0.5
    assert np.abs(t.kare(0).astype(int) - t.kare(12.0).astype(int)).mean() > 0


@pytest.mark.skipif(__import__("importlib").util.find_spec("cv2") is None, reason="opencv yok")
def test_G6_sinemagraf_yalniz_secilen_yerler_hareket_eder_ve_doner(tmp_path):
    import json as _json
    from PIL import Image
    from deepspace.canli import Sinemagraf, tarif_oku
    rng = np.random.default_rng(4)
    (tmp_path / "gorsel").mkdir()
    g = tmp_path / "gorsel" / "02.png"
    Image.fromarray((rng.random((90, 160, 3)) * 255).astype(np.uint8)).save(g)
    tarif = {"bolgeler": [{"etki": "akis", "kutu": [0.5, 0.0, 1.0, 0.5], "hiz": 4, "tekrar": 2},
                          {"etki": "salinim", "kutu": [0.0, 0.5, 0.5, 1.0], "genlik": 3, "tekrar": 3},
                          {"etki": "dalga", "kutu": [0.5, 0.5, 1.0, 1.0], "tekrar": 4},
                          {"etki": "parilti", "kutu": [0.0, 0.0, 0.5, 0.5], "tekrar": 5},
                          {"etki": "kar", "adet": 20}, {"etki": "yildiz", "adet": 20},
                          {"etki": "donme", "merkez": [0.5, 0.5], "yaricap": 0.2, "doku": "02_doku.png"}]}
    Image.fromarray((rng.random((64, 128, 3)) * 255).astype(np.uint8)).save(tmp_path / "gorsel" / "02_doku.png")
    (tmp_path / "gorsel" / "02_hareket.json").write_text(_json.dumps(tarif))
    s = Sinemagraf(g, tarif_oku(g), W=160, H=90, L=24.0, tohum=1)
    k0 = s.kare(0).astype(int)
    bas = np.abs(s.kare(1 / 24).astype(int) - k0).mean()      # ilk kareden ikinciye fark
    son = np.abs(s.kare(24.0 - 1 / 24).astype(int) - k0).mean()  # son kareden başa dönüş farkı
    assert son <= bas * 1.5 + 0.5  # dikiş yok: sondan başa geçiş normal bir kare adımı kadar
    sabit = Sinemagraf(g, [{"etki": "salinim", "kutu": [0.0, 0.6, 0.3, 1.0], "yumusak": 0.01}], W=160, H=90, L=24.0)
    a, b = sabit.kare(0).astype(int), sabit.kare(6.0).astype(int)
    assert np.abs(a[:30, 80:] - b[:30, 80:]).max() == 0  # bölge dışı kıpırdamaz
    assert np.abs(a[60:, :40] - b[60:, :40]).mean() > 0  # bölge içi hareket eder
    korunan = Sinemagraf(g, [{"etki": "akis", "kutu": [0, 0, 1, 1], "haric": [[0.3, 0.3, 0.7, 0.7]], "hiz": 9}],
                         W=160, H=90, L=24.0)
    a, b = korunan.kare(0).astype(int), korunan.kare(5.0).astype(int)
    assert np.abs(a[38:52, 64:96] - b[38:52, 64:96]).max() == 0  # "haric" içindeki katı nesne kıpırdamaz
    assert np.abs(a[:10] - b[:10]).mean() > 0
    from deepspace.canli import Sinemagraf as _S
    assert isinstance(video.sahne_nesnesi(_gorev(tmp_path), 1, 160, 90, 24.0), _S)


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg yok")
def test_G6_hareketli_klip_dikissiz_doner(tmp_path):
    from deepspace import klip
    kaynak = tmp_path / "03.mp4"
    ortak.calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=320x180:rate=24:duration=6", "-pix_fmt", "yuv420p", str(kaynak)])
    hedef = klip.dongu(kaynak, tmp_path / "d.mp4", 192, 108, fps=24, capraz=1.0)
    assert abs(ortak.ffprobe_sure(hedef) - 5.0) < 0.1  # D - X

    def kare(t):
        ham = ortak.calistir(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", str(hedef), "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], text=False).stdout
        return np.frombuffer(ham, np.uint8).astype(int)

    ilk, son, orta = kare(0), kare(5.0 - 1 / 24), kare(2.5)
    assert np.abs(ilk - son).mean() < np.abs(ilk - orta).mean() / 3  # son kare başa kavuşuyor
    g = _gorev(tmp_path)
    (tmp_path / "gorsel").mkdir()
    (tmp_path / "gorsel" / "05.mp4").write_bytes(b"x")
    assert video.parca_klibi(g, 4) == tmp_path / "gorsel" / "05.mp4" and video.parca_klibi(g, 0) is None


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


def test_G8_denetci_karari_24_saat_ve_iptal(tmp_path):
    from datetime import datetime, timedelta, timezone
    from deepspace import google
    out = _hazir_cikti(tmp_path)
    simdi = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(google.GoogleHatasi, match="onay"):
        google.onay_kontrol(out)  # karar yok
    with pytest.raises(google.GoogleHatasi, match="24 saat"):
        google.onay_yaz(out, "denetci", "2026-11-11T06:00:00Z", simdi=simdi)  # 18 saat: sahibine süre kalmıyor
    google.onay_yaz(out, "denetci", "2026-11-11T13:00:00Z", simdi=simdi)
    karar = google.onay_kontrol(out)
    assert karar["karar_veren"] == "denetci" and karar["yayin_zamani"] == "2026-11-11T13:00:00Z"
    (out / "video.mp4").write_bytes(b"y" * 1001)  # karardan sonra değişen video yeniden karar ister
    with pytest.raises(google.GoogleHatasi, match="değişmiş"):
        google.onay_kontrol(out)
    google.onay_yaz(out, "denetci", "2026-11-11T13:00:00Z", simdi=simdi)
    google.iptal_yaz(out, "sahibi istemedi")  # iptal her zaman önceliklidir
    with pytest.raises(google.GoogleHatasi, match="iptal"):
        google.onay_kontrol(out)
    with pytest.raises(google.GoogleHatasi, match="iptal"):
        google.onay_yaz(out, "denetci", "2026-11-12T13:00:00Z", simdi=simdi)
    kirmizi = _hazir_cikti(tmp_path / "k", gecti=False)
    with pytest.raises(google.GoogleHatasi, match="kırmızı"):
        google.onay_yaz(kirmizi, "denetci", "2026-11-12T13:00:00Z", simdi=simdi)


def test_G8_yukleme_gizli_ve_planli():
    from deepspace import google
    g = google.youtube_govdesi({"baslik": "T", "aciklama": "A", "etiketler": []}, None)
    assert g["status"]["privacyStatus"] == "private" and "publishAt" not in g["status"]
    p = google.youtube_govdesi({"baslik": "T", "aciklama": "A", "etiketler": []}, "2026-11-20T17:00:00Z")
    assert p["status"]["privacyStatus"] == "private" and p["status"]["publishAt"] == "2026-11-20T17:00:00Z"
    skill = (KOK / ".claude" / "skills" / "deep-space-log" / "SKILL.md").read_text(encoding="utf-8")
    assert "rapor.json" in skill and "denetçi" in skill.lower() and "iptal" in skill


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
    assert yt["sentetik_icerik"] is True                       # Studio beyanı kalır
    assert not re.search(r"\bAI\b|artificial", yt["aciklama"])  # metin yapay zekâyı ayrıca anmaz (sahibinin kararı)
    assert "Visuals are artistic impressions based on real scientific data." in yt["aciklama"]


def test_G9_metinler_ai_anmaz_ama_yalan_da_soylemez():
    from deepspace import shorts
    yasak = re.compile(r"\bAI\b|artificial|hand-made|handmade|hand-played|human-composed|no AI", re.I)
    kanal = (KOK / "deepspace" / "kanal.md").read_text(encoding="utf-8").split("**Description:**")[1].split("**Links")[0]
    for t in (metin.SUREC_NOTU, shorts.SHORTS_NOTU, kanal):
        assert not yasak.search(t), t


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


def _resim(yol, w=2736, h=1536, tohum=0):
    from PIL import Image
    r = np.random.default_rng(tohum)
    x = np.clip(r.normal(0.4, 0.15, (h // 8, w // 8, 3)), 0, 1)
    Image.fromarray((x * 255).astype(np.uint8)).resize((w, h)).save(yol)
    return yol


def test_G13_gorsel_denetimi(tmp_path):
    from deepspace import gorsel_denetim as gd
    (tmp_path / "gorsel").mkdir()
    g = _gorev(tmp_path, n=3)
    a = _resim(tmp_path / "gorsel" / "01.png", tohum=1)
    _resim(tmp_path / "gorsel" / "02.png", tohum=2)
    _resim(tmp_path / "gorsel" / "03.png", tohum=1)  # 01'in kopyası
    # Teknik katman: iyi görsel temiz; küçük, 4:3 ya da simsiyah görsel kalır.
    assert gd.teknik_sorunlar(gd.teknik_olcum(a)) == []
    assert gd.teknik_sorunlar(gd.teknik_olcum(_resim(tmp_path / "kucuk.png", 1280, 720)))
    assert any("16:9" in s for s in gd.teknik_sorunlar(gd.teknik_olcum(_resim(tmp_path / "kare.png", 2736, 2052))))
    from PIL import Image
    Image.new("RGB", (2736, 1536)).save(tmp_path / "siyah.png")
    assert gd.teknik_sorunlar(gd.teknik_olcum(tmp_path / "siyah.png"))
    # Göz denetimi yoksa kapı kapalı.
    assert all(not k["gecti"] for k in kapilar.gorseller(g))
    # Kritik kusur puandan bağımsız düşürür; puan <7 düşürür; bilinmeyen kod reddedilir.
    gd.goz_denetimi_yaz(a, 9, [{"kod": "anatomi", "not": "altı parmak"}])
    assert not gd.goz_denetimi_gecti(gd.goz_denetimi_oku(a), a)[0]
    gd.goz_denetimi_yaz(a, 6, [{"kod": "tekrar", "not": "iki balıkçı"}])
    assert not gd.goz_denetimi_gecti(gd.goz_denetimi_oku(a), a)[0]
    with pytest.raises(ValueError):
        gd.goz_denetimi_yaz(a, 8, [{"kod": "uydurma"}])
    for i in (1, 2, 3):
        gd.goz_denetimi_yaz(tmp_path / "gorsel" / f"{i:02d}.png", 8, [{"kod": "olcek", "not": "küçük"}])
    k = kapilar.gorseller(g)
    assert k[0]["gecti"] and k[1]["gecti"]
    assert not k[2]["gecti"] and "neredeyse aynı" in k[2]["ayrinti"]  # kopya görsel yakalanır
    # Görsel değişirse eski karar geçersiz.
    _resim(a, tohum=5)
    assert "değişmiş" in gd.goz_denetimi_gecti(gd.goz_denetimi_oku(a), a)[1]
    # Kontrol listesi: kritik maddeler ve eşikler sözleşmedeki gibi.
    kritik = {x["kod"] for x in gd.KONTROL_LISTESI if x["kritik"]}
    assert kritik == {"anatomi", "yazi", "fizik", "istem"}
    assert gd.GECME_PUANI == 7 and gd.YENIDEN_DENEME == 2
    # Paftalar tam çözünürlükte 6 parça.
    p = gd.paftalar(tmp_path / "gorsel" / "02.png", tmp_path / "pafta")
    assert len(p) == 6 and Image.open(p[0]).size == (912, 768)


# ---------- G14 ----------
def _defter(tmp_path, katmanlar, zarf=0.5):
    from PIL import Image
    from deepspace.defter import SeyirDefteri
    W, H, fps = 640, 360, 24
    g = tmp_path / "g.png"
    Image.fromarray((np.random.default_rng(1).random((H, W, 3)) * 255).astype(np.uint8)).save(g)
    n = fps * 30
    muzik = {"zarf": np.full(n, zarf, np.float32), "spektrum": np.full((n, 40), 0.3, np.float32)}
    bilgi = {"ad": "X", "kisa": "x", "bilgi": "x", "gorev_no": 2, "hedef": "X", "parca_no": 1,
             "parca_say": 20, "sonraki": "Y"}
    return SeyirDefteri(g, katmanlar, W, H, fps, 30.0, muzik, bilgi), W, H, fps


@pytest.mark.parametrize("katman", [
    {"etki": "pencereler", "kutu": [0.6, 0.6, 0.9, 0.9]},
    {"etki": "kutup_isigi", "kutu": [0.6, 0.6, 0.9, 0.9]},
    {"etki": "halka_piriltisi", "kutu": [0.6, 0.6, 0.9, 0.9]},
    {"etki": "bulutsu_tulu", "kutu": [0.6, 0.6, 0.9, 0.9]},
    {"etki": "uydu", "yol": [[0.6, 0.65], [0.9, 0.85]], "sure": 4, "aralik": 4},
    {"etki": "isaret_lambasi", "merkez": [0.75, 0.75]}])
def test_G14_uzay_katmanlari_kutu_disina_tasmaz(tmp_path, katman):
    s, W, H, fps = _defter(tmp_path, [katman])
    kareler = [s.kare(fps * t).astype(int) for t in (2, 9, 25)]
    orta = (slice(80, 150), slice(100, 260))          # kutunun ve HUD'un dışı
    assert all(np.abs(kareler[0][orta] - k[orta]).max() == 0 for k in kareler[1:])
    kutu = (slice(int(0.62 * H), int(0.88 * H)), slice(int(0.62 * W), int(0.88 * W)))
    assert max(np.abs(kareler[0][kutu] - k[kutu]).max() for k in kareler[1:]) > 0


def test_G14_hud_oynatici_alanina_girmez_kart_yalniz_basta(tmp_path):
    from PIL import Image
    from deepspace.defter import ALT_GUVENLI, SeyirDefteri
    W, H, fps, sure = 640, 360, 4, 400.0
    g = tmp_path / "g.png"
    Image.fromarray(np.zeros((H, W, 3), np.uint8)).save(g)
    n = int(fps * sure)
    muzik = {"zarf": np.full(n, 0.5, np.float32), "spektrum": np.full((n, 40), 0.3, np.float32)}
    bilgi = {"ad": "X", "kisa": "one of seven Earth-size worlds", "bilgi": "a long fact " * 8, "gorev_no": 1,
             "hedef": "X", "parca_no": 1, "parca_say": 20, "sonraki": "Y"}
    s = SeyirDefteri(g, [], W, H, fps, sure, muzik, bilgi)
    assert ALT_GUVENLI >= 0.16
    for t in (10.0, 200.0, sure - 10):
        for x, y, p in s._hud(t, int(t * fps)):
            assert y + p.shape[0] <= H * (1 - ALT_GUVENLI) + 1, f"t={t}: öğe oynatıcı alanında"
    kart_sayisi = lambda t: len(s._hud(t, int(t * fps)))
    assert kart_sayisi(10.0) == kart_sayisi(200.0) + 1   # baştaki kart görünür, ortada yok
    assert kart_sayisi(120.0) == kart_sayisi(200.0)       # 25 sn'lik satırlar parça başında biter


def test_G14_kart_tekrar_etmez_kaymaz_birlikte_kaybolur(tmp_path):
    import textwrap
    from PIL import Image
    from deepspace.defter import KART_SUTUN, SeyirDefteri
    W, H, fps, sure = 640, 360, 4, 400.0
    g = tmp_path / "g.png"
    Image.fromarray(np.zeros((H, W, 3), np.uint8)).save(g)
    n = int(fps * sure)
    muzik = {"zarf": np.full(n, 0.5, np.float32), "spektrum": np.full((n, 40), 0.3, np.float32)}
    kisa = "one of seven Earth-size worlds · 40 light-years"
    uzun = ("One of seven Earth-size planets around the cool red star TRAPPIST-1, about 40 light-years away, "
            "and among the most promising for liquid water.")
    bilgi = {"ad": "TRAPPIST-1e", "kisa": kisa, "bilgi": uzun, "gorev_no": 1, "hedef": "TRAPPIST-1",
             "parca_no": 16, "parca_say": 20, "sonraki": "Y"}
    s = SeyirDefteri(g, [], W, H, fps, sure, muzik, bilgi)
    sayfalar, onceki = [], None
    for k in range(0, 120 * 4):
        kart = s._kart(k / 4)
        if kart is None:
            continue
        etiket, satirlar, sol = kart
        assert len(satirlar) <= 3 and 0 < sol <= 1
        assert all("TRAPPIST-1e" not in x and kisa not in x for x in satirlar)
        if onceki and onceki[0] == etiket and len(onceki[1]) <= len(satirlar) and                 all(satirlar[i].startswith(onceki[1][i]) for i in range(len(onceki[1]) - 1)):
            sayfalar[-1] = satirlar           # aynı sayfa yazılmaya devam ediyor: satırlar yerinde kalır
        else:
            sayfalar.append(satirlar)
        onceki = (etiket, satirlar)
    assert sum(sayfalar, []) == textwrap.wrap(uzun, KART_SUTUN)   # bilgi bir kez, sırayla, kaymadan
    assert s._kart(119.0) is None


def test_G14_katman_muzik_bagi(tmp_path):
    k = [{"etki": "kutup_isigi", "kutu": [0.6, 0.6, 0.9, 0.9], "muzik": True}]
    sessiz, *_ = _defter(tmp_path, k, zarf=0.0)
    gur, *_ = _defter(tmp_path, k, zarf=1.0)
    taban = sessiz.taban
    kutu = (slice(220, 320), slice(390, 570))
    fark = lambda s: np.abs(s.kare(48).astype(float)[kutu] / 255 - taban[kutu]).sum()  # noqa: E731
    assert fark(gur) > fark(sessiz) * 1.5   # 0.7 + 0.6·zarf


def test_G14_hareket_kapisi_en_az_3_katman_biri_muzikle(tmp_path):
    g = _gorev(tmp_path, n=1, no=2)
    (tmp_path / "gorsel").mkdir()
    _resim(tmp_path / "gorsel" / "01.png", 64, 36)
    assert _kirmizi(kapilar.hareket(g))                        # tarif yok
    tarif = tmp_path / "gorsel" / "01_hareket.json"
    tarif.write_text(json.dumps({"katmanlar": [{"etki": "toz"}, {"etki": "yildiz"}]}), encoding="utf-8")
    assert _kirmizi(kapilar.hareket(g))
    tarif.write_text(json.dumps({"katmanlar": [{"etki": "toz"}, {"etki": "yildiz"}, {"etki": "uydu"}]}),
                     encoding="utf-8")
    assert _kirmizi(kapilar.hareket(g))                        # müzikle bağlı katman yok
    tarif.write_text(json.dumps({"katmanlar": [{"etki": "toz"}, {"etki": "yildiz"},
                                               {"etki": "isik", "nabiz": "muzik"}]}), encoding="utf-8")
    assert not _kirmizi(kapilar.hareket(g))
    tarif.write_text("{bozuk", encoding="utf-8")
    assert _kirmizi(kapilar.hareket(g))
    tarif.write_text(json.dumps({"katmanlar": [{"etki": "toz"}, {"etki": "yildiz"}, {"etki": "bukme", "muzik": True}]}),
                     encoding="utf-8")
    assert _kirmizi(kapilar.hareket(g))                        # bilinmeyen etki (G14: bükme yok)
    bos = _gorev(tmp_path / "bos", n=1, no=2)
    assert _kirmizi(kapilar.hareket(bos))                      # görsel yoksa hareket istasyonu geçemez


def test_G2_bolum_kesimleri_capraz_gecisin_ortasinda():
    b = _bolumler([300.0, 240.0, 360.0], capraz=8.0)
    k = video.bolum_kesimleri(b)
    assert k[0][0] == 0 and k[-1][1] == pytest.approx(b["toplam_sn"])
    assert k[0][1] == pytest.approx(b["parcalar"][1]["basla"] + 4.0)
    assert all(a[1] == pytest.approx(c[0]) for a, c in zip(k, k[1:]))


def test_G14_sessiz_ara_cikti_yalniz_ara_klasorunde(tmp_path):
    from deepspace import defter
    with pytest.raises(ValueError):
        defter.kodla(object(), None, tmp_path / "cikti" / "video.mp4", None)


def _defter_gorevi(tmp_path, sureler=(3.0, 3.0), capraz=1.0):
    import copy
    g = _gorev(tmp_path, n=len(sureler), no=2)
    (tmp_path / "gorsel").mkdir()
    for i in range(len(sureler)):
        _resim(tmp_path / "gorsel" / f"{i + 1:02d}.png", 320, 180, tohum=i)
    out = ortak.cikti(g)
    b = _bolumler(list(sureler), capraz=capraz)
    _yaz_bolumler(g, b)
    ortak.calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:duration={b['toplam_sn']}", "-c:a", "aac", str(out / "ses.m4a")])
    ayar = copy.deepcopy(AYAR)
    ayar["video"].update({"genislik": 320, "yukseklik": 180, "fps": 8, "crf": 32, "preset": "ultrafast",
                          "is_parcacigi": 2, "mod": "defter"})
    return g, ayar, b


def test_G14_uzun_video_defter_modunda(tmp_path):
    g, ayar, b = _defter_gorevi(tmp_path)
    yol = video.uzun_video(g, ayar)
    assert yol == ortak.cikti(g) / "video.mp4"
    assert ortak.ffprobe_sure(yol) == pytest.approx(b["toplam_sn"], abs=0.3)
    assert kapilar.ses_duyuluyor(yol)[0]
    assert not (ortak.cikti(g) / "ara").exists() or not any((ortak.cikti(g) / "ara").iterdir())
    assert not (ortak.cikti(g) / "bolum").exists()             # eski sinemagraf yolu çalışmadı


def test_G13_defter_modunda_gorselsiz_parca_kod_sahnesine_duser(tmp_path):
    g, ayar, b = _defter_gorevi(tmp_path)
    (tmp_path / "gorsel" / "02.png").unlink()      # iki denemede de kalan görsel çıkarıldı
    yol = video.uzun_video(g, ayar)
    assert ortak.ffprobe_sure(yol) == pytest.approx(b["toplam_sn"], abs=0.3)
    assert kapilar.ses_duyuluyor(yol)[0]
    assert not any((ortak.cikti(g) / "ara").iterdir())


def test_G12_en_iyi_aralik_kenarlari_ve_sessizligi_atlar():
    from deepspace import shorts
    e = np.full(300, -30.0)
    e[:12] = -10.0                 # giriş (çapraz geçiş) hariç tutulur
    e[100:145] = -14.0             # en canlı bölüm
    e[120] = -60.0                 # içinde sessiz saniye olan pencere seçilmez
    bas = shorts.en_iyi_aralik(e, 45)
    assert 12 <= bas and not (bas <= 120 < bas + 45)
    assert bas + 45 <= 300 - 12    # çıkış (fade) da hariç
    assert shorts.en_iyi_aralik(np.full(40, -30.0), 45) == -1
    tum_sessiz = np.full(300, -70.0)
    assert shorts.en_iyi_aralik(tum_sessiz, 45) == -1


def _analiz_gorevi(tmp_path):
    import copy
    g = _gorev(tmp_path, n=2, no=2)
    b = _bolumler([40.0, 40.0], capraz=4.0)
    _yaz_bolumler(g, b)
    # 0-36 sn ton, sonra 4 sn sessizlik (çapraz geçiş), 40-76 sn ton
    ortak.calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=330:duration={b['toplam_sn']}", "-af",
                    "volume=enable='between(t,26,30)':volume=0", "-c:a", "aac", str(ortak.cikti(g) / "ses.m4a")])
    ayar = copy.deepcopy(AYAR)
    ayar["shorts"]["sure_sn"] = 10
    return g, ayar, b


def test_G12_enerji_egrisi_ve_analiz(tmp_path):
    from deepspace import shorts
    g, ayar, b = _analiz_gorevi(tmp_path)
    e = shorts.enerji_egrisi(ortak.cikti(g) / "ses.m4a", 0.0, 40.0)
    assert len(e) == 40 and e[5] > -30 and e[27] < -45
    yol = shorts.analiz(g, ayar)
    assert yol == ortak.cikti(g) / "shorts_analiz.json"
    d = json.loads(yol.read_text(encoding="utf-8"))
    assert [x["parca"] for x in d] == [1, 2] and d[0]["ad"] == "World 1"
    p1 = d[0]
    assert p1["oneri_basla"] is not None
    goreli = p1["oneri_basla"] - p1["basla"]
    assert goreli >= 12 and not (goreli <= 27 < goreli + 10)  # sessiz saniyeleri içermez
    assert d[1]["oneri_basla"] >= b["parcalar"][1]["basla"] + 12


def test_G12_shorts_analiz_komutu(tmp_path, monkeypatch):
    from deepspace import gorev as cli
    g, ayar, _ = _analiz_gorevi(tmp_path)
    g["no"] = 1
    monkeypatch.setattr(cli, "gorev_yukle", lambda k: (g, ayar))
    assert cli.main(["shorts-analiz", str(tmp_path)]) == 0
    assert (ortak.cikti(g) / "shorts_analiz.json").exists()


def _plan(b, **ek):
    p = [{"parca": 2, "sure_sn": 45, "kirp_x": 0.5, "kanca": "Ice world"},
         {"parca": 5, "sure_sn": 45, "kirp_x": 0.3, "kanca": "Red sun"},
         {"parca": 9, "sure_sn": 45, "kirp_x": 0.7, "kanca": "Deep signal"}]
    for x in p:
        x["basla_sn"] = b["parcalar"][x["parca"] - 1]["basla"] + 60
        x.update(ek)
    return p


def _shorts_gorevi(tmp_path, no):
    g = _gorev(tmp_path, no=no)
    g["_ses_ozetleri"] = [f"oz{i}" for i in range(20)]
    return g, _bolumler([300.0] * 20)


def test_G12_plan_kurallari(tmp_path):
    from deepspace import shorts
    g, b = _shorts_gorevi(tmp_path, 2)
    kayit = {"gorevler": []}
    assert not _kirmizi(shorts.plan_kontrol(_plan(b), g, b, kayit, AYAR))
    p = _plan(b)
    p[1]["parca"], p[1]["basla_sn"] = 2, p[0]["basla_sn"]                  # aynı parça iki kez
    assert _kirmizi(shorts.plan_kontrol(p, g, b, kayit, AYAR))
    p = _plan(b)
    p[0]["basla_sn"] = b["parcalar"][1]["basla"] + 280                    # parça sonunu aşar
    assert _kirmizi(shorts.plan_kontrol(p, g, b, kayit, AYAR))
    p = _plan(b)
    p[0]["basla_sn"] = b["parcalar"][1]["basla"] + 2                      # çapraz geçişin içinde başlar
    assert _kirmizi(shorts.plan_kontrol(p, g, b, kayit, AYAR))
    assert _kirmizi(shorts.plan_kontrol(_plan(b, kanca="Four words are here"), g, b, kayit, AYAR))
    assert _kirmizi(shorts.plan_kontrol(_plan(b, kanca="Interstellar drift"), g, b, kayit, AYAR))  # G5
    assert _kirmizi(shorts.plan_kontrol(_plan(b, sure_sn=15), g, b, kayit, AYAR))
    assert _kirmizi(shorts.plan_kontrol(_plan(b, kirp_x=1.4), g, b, kayit, AYAR))
    assert _kirmizi(shorts.plan_kontrol(_plan(b)[:2], g, b, kayit, AYAR))   # adet
    bozuk = _plan(b)
    del bozuk[0]["basla_sn"]
    bozuk[1]["parca"] = 99
    assert _kirmizi(shorts.plan_kontrol(bozuk, g, b, kayit, AYAR))          # çökmez, kırmızı
    eksik = dict(g, _ses_ozetleri=["oz0"])                                   # ses özetleri hizasız
    assert _kirmizi(shorts.plan_kontrol(_plan(b), eksik, b, kayit, AYAR))
    p = _plan(b)
    p[1]["parca"], p[1]["basla_sn"] = "02", p[0]["basla_sn"]               # 2 ile "02" aynı parça
    assert any("ayrı parça" in k for k in _kirmizi(shorts.plan_kontrol(p, g, b, kayit, AYAR)))
    assert _kirmizi(shorts.plan_kontrol(_plan(b, kanca=None), g, b, kayit, AYAR))   # çökmez, kırmızı
    assert _kirmizi(shorts.plan_kontrol(_plan(b, kanca="   "), g, b, kayit, AYAR))
    uzun = shorts.plan_kontrol(_plan(b, kanca="Extraordinarily Unfathomable Hyperluminosity"), g, b, kayit, AYAR)
    assert any("telefonda" in k for k in _kirmizi(uzun))              # G16: en küçük boyda sığmaz


def test_G16_short_kancasi_en_kucuk_yazi_boyunun_altina_inmez():
    from deepspace import defter
    boy, sigar = defter.kanca_boyu("Extraordinarily Unfathomable Hyperluminosity", 1080, 1920, 64)
    assert boy >= 0.02 * 1920 and not sigar
    boy, sigar = defter.kanca_boyu("Ice world", 1080, 1920, 64)
    assert boy == 64 and sigar


def test_G12_dikey_karede_goruntu_bukulmez_ve_yazilar_okunur(tmp_path):
    from PIL import Image
    from deepspace import defter
    W, H, fps = 540, 960, 24
    g = tmp_path / "g.png"
    Image.fromarray((np.random.default_rng(2).random((1080, 1920, 3)) * 255).astype(np.uint8)).save(g)
    n = fps * 10
    muzik = {"zarf": np.full(n, 0.5, np.float32), "spektrum": np.full((n, 40), 0.3, np.float32)}
    bilgi = {"ad": "X", "kisa": "x", "bilgi": "x", "gorev_no": 2, "hedef": "X", "parca_no": 1,
             "parca_say": 20, "sonraki": "Y"}
    s = defter.SeyirDefteri(g, [], W, H, fps, 10.0, muzik, bilgi, kirp_x=0.2, kanca="Red sun")
    a, b = s.kare(10).astype(int), s.kare(200).astype(int)
    orta = (slice(int(0.55 * H), int(0.7 * H)), slice(0, W))
    assert np.abs(a[orta] - b[orta]).max() == 0
    assert a.shape == (H, W, 3)
    assert ortak.marka_yukle()["sablon"]["short_etiket"] >= defter.EN_KUCUK_YAZI_ORANI * 1920
    kanca_bandi = (slice(int(0.22 * H), int(0.34 * H)), slice(0, W))
    bos = defter.SeyirDefteri(g, [], W, H, fps, 10.0, muzik, bilgi, kirp_x=0.2, kanca="")
    assert np.abs(a[kanca_bandi] - bos.kare(10).astype(int)[kanca_bandi]).max() > 0   # kanca y≈0.28H'de
    sag = defter.SeyirDefteri(g, [], W, H, fps, 10.0, muzik, bilgi, kirp_x=0.8, kanca="Red sun")
    assert np.abs(a[orta] - sag.kare(10).astype(int)[orta]).max() > 0                 # kirp_x kadrajı kaydırır


def test_G12_dikey_karede_katmanlar_resimle_birlikte_kayar(tmp_path):
    from PIL import Image
    from deepspace import defter
    g = tmp_path / "g.png"
    Image.fromarray(np.zeros((180, 320, 3), np.uint8)).save(g)
    muzik = {"zarf": np.full(48, 0.5, np.float32), "spektrum": np.full((48, 40), 0.3, np.float32)}
    bilgi = {"ad": "X", "kisa": "", "bilgi": "", "gorev_no": 2, "hedef": "X", "parca_no": 1, "parca_say": 2,
             "sonraki": ""}
    lamba = [{"etki": "isik", "merkez": [0.6, 0.5], "yaricap": 0.01, "guc": 1.0, "nabiz": "yavas", "periyot": 4}]
    s = defter.SeyirDefteri(g, lamba, 540, 960, 24, 2.0, muzik, bilgi, kirp_x=0.5)
    k = s.kare(24).astype(int).sum(axis=2)[int(0.4 * 960):int(0.6 * 960)]
    x = int(np.argmax(k.max(axis=0)))
    # resim 960 yükseklikte 1707 genişliğe büyür, ortadan 540 kırpılır: 0.6·1707 − 583.5 ≈ 440
    assert abs(x - 440) <= 6


def test_G12_kullanilan_an_baska_gorevde_tekrar_etmez(tmp_path):
    from deepspace import shorts
    g, b = _shorts_gorevi(tmp_path, 3)
    kayit = {"gorevler": [{"no": 2, "shorts": [{"ses_ozeti": "oz1", "parca_ici_sn": 70.0, "sure_sn": 45}]}]}
    assert _kirmizi(shorts.plan_kontrol(_plan(b), g, b, kayit, AYAR))   # parça 2: göreli 60–105, örtüşür
    kayit["gorevler"][0]["shorts"][0]["parca_ici_sn"] = 120.0
    assert not _kirmizi(shorts.plan_kontrol(_plan(b), g, b, kayit, AYAR))


def _short_gorevi(tmp_path):
    import copy
    g = _gorev(tmp_path, n=2, no=2)
    (tmp_path / "gorsel").mkdir()
    for i in range(2):
        _resim(tmp_path / "gorsel" / f"{i + 1:02d}.png", 320, 180, tohum=i)
    b = _bolumler([30.0, 30.0], capraz=2.0)
    _yaz_bolumler(g, b)
    ortak.calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:duration={b['toplam_sn']}", "-c:a", "aac", str(ortak.cikti(g) / "ses.m4a")])
    ayar = copy.deepcopy(AYAR)
    ayar["video"].update({"fps": 8, "crf": 32, "preset": "ultrafast"})
    ayar["shorts"].update({"adet": 1, "min_sn": 5, "max_sn": 20})
    g["_ses_ozetleri"] = ["a", "b"]
    plan = [{"parca": 2, "basla_sn": b["parcalar"][1]["basla"] + 5, "sure_sn": 6, "kirp_x": 0.3, "kanca": "Red sun"}]
    return g, ayar, b, plan


def test_G12_short_uretimi_plan_ve_kapilar(tmp_path):
    from deepspace import shorts
    g, ayar, b, plan = _short_gorevi(tmp_path)
    with pytest.raises(SystemExit, match="shorts_plan.json"):
        shorts.uret(g, ayar)                                   # görev 2: plan olmadan Short yok
    (tmp_path / "shorts_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    yollar = shorts.uret(g, ayar)
    assert [y.name for y in yollar] == ["short_1.mp4"]
    k = kapilar.shorts(yollar, ayar)
    assert not _kirmizi(k) and any("ilk 2 sn" in x["ad"] for x in k)
    assert ortak.ffprobe_sure(yollar[0]) == pytest.approx(6.0, abs=0.3)
    m = json.loads((ortak.cikti(g) / "shorts.json").read_text(encoding="utf-8"))
    assert m[0]["baslik"].startswith("Red sun · World 2") and "#Shorts" in m[0]["baslik"]
    assert len(m[0]["baslik"]) <= 100 and "{UZUN_VIDEO}" in m[0]["aciklama"] and "artistic impressions" in m[0]["aciklama"]
    assert not _kirmizi(kapilar.metin_temel(m[0], ayar))
    assert not _kirmizi(shorts.istasyon_kapilari(g, ayar))
    plan[0]["sure_sn"] = 30                                     # kırmızı plan: üretim durur
    (tmp_path / "shorts_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(SystemExit, match="plan"):
        shorts.uret(g, ayar)


def test_G12_shorts_yukleme_takvimi(tmp_path, monkeypatch):
    from deepspace import google
    out = tmp_path
    (out / "yukleme.json").write_text(json.dumps({"video_id": "UZUN1"}), encoding="utf-8")
    (out / "shorts.json").write_text(json.dumps([
        {"baslik": f"S{k} | Deep Space Log #Shorts", "aciklama": "Full mission: {UZUN_VIDEO}", "etiketler": ["a"],
         "sentetik_icerik": True} for k in range(3)]), encoding="utf-8")
    for k in range(3):
        (out / f"short_{k + 1}.mp4").write_bytes(b"v" * 10)
    monkeypatch.setattr(google, "onay_kontrol", lambda c: {"yayin_zamani": "2026-11-20T17:00:00Z"})
    monkeypatch.setattr(google, "erisim_belirteci", lambda oturum=None: "tok")
    govdeler = []

    class Oturum:
        def post(self, url, params, json, timeout, headers):
            govdeler.append(json)
            return _Yanit(200, baslik={"Location": "u"})

        def put(self, url, data, headers, timeout):
            return _Yanit(200, {"id": f"S{len(govdeler)}"})

    sonuc = google.shorts_yukle(out, Oturum())
    assert [s["id"] for s in sonuc] == ["S1", "S2", "S3"]
    assert [g["status"]["publishAt"] for g in govdeler] == ["2026-11-21T17:00:00Z", "2026-11-23T17:00:00Z",
                                                            "2026-11-25T17:00:00Z"]
    assert all(g["status"]["privacyStatus"] == "private" and g["status"]["containsSyntheticMedia"] for g in govdeler)
    assert "https://youtu.be/UZUN1" in govdeler[0]["snippet"]["description"]
    (out / "yukleme.json").unlink()
    with pytest.raises(google.GoogleHatasi, match="uzun video"):
        google.shorts_yukle(out, Oturum())


def test_G12_shorts_yuklemesi_yarida_kalirsa_kaldigi_yerden_surer(tmp_path, monkeypatch):
    from deepspace import google
    out = tmp_path
    (out / "yukleme.json").write_text(json.dumps({"video_id": "UZUN1"}), encoding="utf-8")
    (out / "shorts.json").write_text(json.dumps([
        {"baslik": f"S{k}", "aciklama": "{UZUN_VIDEO}", "etiketler": ["a"], "sentetik_icerik": True}
        for k in range(3)]), encoding="utf-8")
    for k in range(3):
        (out / f"short_{k + 1}.mp4").write_bytes(b"v" * 10)
    (out / "shorts_yukleme.json").write_text(json.dumps(
        [{"id": "S1", "publishAt": "2026-11-21T17:00:00Z", "dosya": "short_1.mp4"}]), encoding="utf-8")
    monkeypatch.setattr(google, "onay_kontrol", lambda c: {"yayin_zamani": "2026-11-20T17:00:00Z"})
    monkeypatch.setattr(google, "erisim_belirteci", lambda oturum=None: "tok")
    basliklar = []

    class Oturum:
        def post(self, url, params, json, timeout, headers):
            basliklar.append(json["snippet"]["title"])
            return _Yanit(200, baslik={"Location": "u"})

        def put(self, url, data, headers, timeout):
            return _Yanit(200, {"id": f"N{len(basliklar)}"})

    sonuc = google.shorts_yukle(out, Oturum())
    assert basliklar == ["S1", "S2"]                       # Short 1 ikinci kez yüklenmedi
    assert [s["dosya"] for s in sonuc] == ["short_1.mp4", "short_2.mp4", "short_3.mp4"]
    assert google.shorts_yukle(out, Oturum()) == sonuc and len(basliklar) == 2   # hepsi yüklüyse dokunmaz


def test_G8_iptal_shortslarin_planli_yayinini_da_geri_alir(tmp_path, monkeypatch):
    from deepspace import google
    from deepspace import gorev as cli
    g = _gorev(tmp_path)
    out = ortak.cikti(g)
    (out / "yukleme.json").write_text(json.dumps({"video_id": "UZUN1"}), encoding="utf-8")
    (out / "shorts_yukleme.json").write_text(json.dumps(
        [{"id": f"S{k}", "publishAt": "x", "dosya": f"short_{k}.mp4"} for k in (1, 2, 3)]), encoding="utf-8")
    geri = []
    monkeypatch.setattr(google, "youtube_planli_yayini_geri_al", lambda vid, oturum=None: geri.append(vid))
    monkeypatch.setattr(google, "iptal_yaz", lambda c, n: "iptal")

    class A:
        komut, neden = "iptal", "sahibi istemedi"

    assert cli._google(A(), g) == 0
    assert geri == ["UZUN1", "S1", "S2", "S3"]


def test_G12_kaydet_shorts_anlarini_yazar(tmp_path, monkeypatch):
    from deepspace import gorev as cli
    monkeypatch.setattr(cli, "KAYIT_DOSYASI", tmp_path / "kayit.json")
    monkeypatch.setattr(ortak, "KAYIT_DOSYASI", tmp_path / "kayit.json")
    g, b = _shorts_gorevi(tmp_path, 2)
    (tmp_path / "ses").mkdir()
    for i, p in enumerate(g["parca"]):
        (tmp_path / "ses" / p["dosya"]).write_bytes(bytes([i]) * 10)
    _yaz_bolumler(g, b)
    (tmp_path / "shorts_plan.json").write_text(json.dumps(_plan(b)), encoding="utf-8")
    kayit = cli.kaydet(g, "VID")
    sh = kayit["gorevler"][0]["shorts"]
    assert [round(x["parca_ici_sn"]) for x in sh] == [60, 60, 60] and sh[0]["sure_sn"] == 45
    assert sh[0]["ses_ozeti"] == kayit["gorevler"][0]["ses_ozetleri"][1]


def test_G17_arastirma_basligi_pakete_girer_yasakliysa_sablon(tmp_path):
    g = _gorev(tmp_path, no=2)
    _yaz_bolumler(g, _bolumler([360.0] * 20))
    (tmp_path / "buyume").mkdir()
    o = {"kelimeler": ["sci fi ambient music"], "secilen": 0, "seri": "focus", "yayin_saati_utc": "14:00",
         "kaynaklar": [], "basliklar": ["World 3 | Sci-Fi Space Ambient for Deep Focus (2 Hours) · Mission 007",
                                        "Deep Focus Music · Mission 007"]}
    (tmp_path / "buyume" / "oneriler.json").write_text(json.dumps(o), encoding="utf-8")
    yt = metin.uret(g, AYAR)
    assert yt["baslik"].startswith("World 3 | Sci-Fi") and yt["baslik_kaynagi"] == "arastirma"
    o["basliklar"][0] = "Interstellar Ambient for Deep Focus"
    (tmp_path / "buyume" / "oneriler.json").write_text(json.dumps(o), encoding="utf-8")
    yt = metin.uret(g, AYAR)
    assert "interstellar" not in yt["baslik"].lower() and yt["baslik_kaynagi"] == "sablon"
    (tmp_path / "buyume" / "oneriler.json").write_text("{bozuk", encoding="utf-8")
    assert metin.uret(g, AYAR)["baslik_kaynagi"] == "sablon"          # bozuk öneri dosyası çökertmez
    o.update(secilen=5)
    (tmp_path / "buyume" / "oneriler.json").write_text(json.dumps(o), encoding="utf-8")
    assert metin.uret(g, AYAR)["baslik_kaynagi"] == "sablon"


def test_G9_surec_notu_gorsellerin_kaynagini_dogru_soyler():
    assert "artistic impressions" in metin.SUREC_NOTU and "generated with code" not in metin.SUREC_NOTU
    skill = (KOK / ".claude" / "skills" / "youtube" / "SKILL.md").read_text(encoding="utf-8")
    assert "## 8. YouTube uzmanı ajanı" in skill and "oneriler.json" in skill and "kararlar.json" in skill
    assert (KOK / "deepspace" / "buyume" / "README.md").exists()


def test_G14_seyir_defteri_goruntuyu_bukmez(tmp_path):
    from PIL import Image
    from deepspace.defter import SeyirDefteri
    W, H, fps = 640, 360, 24
    rng = np.random.default_rng(3)
    g = tmp_path / "g.png"
    Image.fromarray((rng.random((H, W, 3)) * 200).astype(np.uint8)).save(g)
    n = 24 * 20
    muzik = {"zarf": np.full(n, 0.5, np.float32), "spektrum": np.full((n, 40), 0.3, np.float32)}
    bilgi = {"ad": "TRAPPIST-1e", "kisa": "test", "bilgi": "A real fact.", "gorev_no": 1, "hedef": "TRAPPIST-1e",
             "parca_no": 1, "parca_say": 20, "sonraki": "Vega"}
    led = {"etki": "isik", "merkez": [0.5, 0.5], "yaricap": 0.004, "guc": 1.0, "nabiz": "yanip_son", "periyot": 4}
    s = SeyirDefteri(g, [led], W, H, fps, 20.0, muzik, bilgi)
    yan, son = s.kare(int(0.4 * fps)).astype(int), s.kare(int(2.0 * fps)).astype(int)  # LED yanık / sönük
    assert np.abs(yan[170:190, 310:330] - son[170:190, 310:330]).max() > 30  # ışık yanıp söner
    # Işığın ve yazıların dışında hiçbir piksel kıpırdamaz: görüntü bükülmez, yalnız üstüne katman eklenir.
    orta = (slice(80, 150), slice(100, 260))
    assert np.abs(yan[orta] - son[orta]).max() == 0
    assert np.abs(yan[orta] - (s.taban[orta] * 255 + 0.5).astype(int)).max() == 0
    assert s.kare(0).shape == (H, W, 3)
    # Telefonda okunurluk: en küçük yazı 1080p'de kare yüksekliğinin %2'si (22 px) altında olamaz.
    from deepspace import defter
    assert min(defter.YAZI.values()) >= defter.EN_KUCUK_YAZI_ORANI * 1080
@pytest.mark.skipif(__import__("importlib").util.find_spec("cv2") is None, reason="opencv yok")
def test_G14_gezegen_gercekten_doner_hayalet_yok(tmp_path):
    import cv2
    from PIL import Image
    from deepspace.canli import Sinemagraf
    W, H, L = 320, 180, 24.0
    rng = np.random.default_rng(7)
    doku = cv2.GaussianBlur(rng.random((H, W, 3)).astype(np.float32), (0, 0), 2.5)
    doku = (doku - doku.min()) / (doku.max() - doku.min())
    g = tmp_path / "g.png"
    Image.fromarray(np.full((H, W, 3), 90, np.uint8)).save(g)
    harita = cv2.GaussianBlur(rng.random((256, 512, 3)).astype(np.float32), (0, 0), 2.5)
    harita = (harita - harita.min()) / (harita.max() - harita.min())
    Image.fromarray((harita * 255).astype(np.uint8)).save(tmp_path / "g_doku.png")
    # Tam yüzey dokusu yoksa ya da disk kadraja sığmıyorsa dönme reddedilir: gezegen sabit kalır.
    with pytest.raises(ValueError, match="doku"):
        Sinemagraf(g, [{"etki": "donme", "merkez": [0.5, 0.5], "yaricap": 0.22}], W, H, L)
    with pytest.raises(ValueError, match="kadraja"):
        Sinemagraf(g, [{"etki": "donme", "merkez": [0.2, -1.9], "yaricap": 1.28, "doku": "g_doku.png"}], W, H, L)
    s = Sinemagraf(g, [{"etki": "donme", "merkez": [0.5, 0.5], "yaricap": 0.22, "doku": "g_doku.png"}], W, H, L)
    yy, xx = np.mgrid[0:H, 0:W]
    ic = ((xx - W / 2) ** 2 + (yy - H / 2) ** 2) < (0.12 * W) ** 2  # diskin iç kısmı
    k0 = s.kare(0).astype(np.float32)
    assert np.abs(s.kare(L).astype(int) - k0.astype(int)).max() == 0  # tam tur: dikişsiz
    for t in (L / 8, L / 4, L * 3 / 8):
        k = s.kare(t).astype(np.float32)
        assert np.abs(k[ic] - k0[ic]).mean() > 5  # yüzey gerçekten kayıyor
        # İki kopya karışsaydı doku kontrastı ~%30 düşerdi (hayalet); tek kopyada korunur.
        assert k[ic].std() > 0.85 * k0[ic].std()
    assert np.abs(s.kare(L / 4)[~ic & (yy < 20)].astype(int) - k0[~ic & (yy < 20)].astype(int)).max() == 0


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg yok")
def test_G14_teslim_edilen_videoda_ses_duyulur(tmp_path):
    def yap(ad, ses):
        y = tmp_path / ad
        ortak.calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=64x36:d=4",
                        "-f", "lavfi", "-i", ses, "-t", "4", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(y)])
        return y
    assert kapilar.ses_duyuluyor(yap("sesli.mp4", "sine=frequency=220:duration=4"))[0]
    assert not kapilar.ses_duyuluyor(yap("sessiz.mp4", "anullsrc=r=48000:cl=stereo"))[0]
    y = tmp_path / "sadece_goruntu.mp4"
    ortak.calistir(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=64x36:d=2",
                    "-c:v", "libx264", str(y)])
    assert kapilar.ses_duyuluyor(y) == (False, "ses akışı yok")
    # Örnek komutu sessiz döngüyü teslim klasörüne değil ara/ klasörüne yazar.
    kod = Path(__file__).resolve().parents[1].joinpath("deepspace", "ornek.py").read_text(encoding="utf-8")
    assert 'klasor / "ara"' in kod and "ses_duyuluyor" in kod


# ---------- G15 / G16 / G17 (iş bölümü, marka, YouTube uzmanı) ----------
def test_G15_G16_G17_sozlesmede_ve_ayarda():
    s = (KOK / "SOZLESME.md").read_text(encoding="utf-8")
    for madde in ("| G15 |", "| G16 |", "| G17 |"):
        assert madde in s
    assert AYAR["is_bolumu"] == {"kilit_baslangic": 2, "en_cok_tur": 3}
    assert AYAR["vidiq"]["aylik_kredi"] == 100 and AYAR["vidiq"]["yenileme_gunu"] == 27
    assert AYAR["vidiq"]["cagri_kredi"] == 5
    assert AYAR["shorts"]["min_sn"] == 20 and AYAR["shorts"]["max_sn"] == 58
    assert AYAR["shorts"]["yayin_gunleri"] == [1, 3, 5] and AYAR["shorts"]["kanca_max_kelime"] == 3


def _istasyon_gorevi(tmp_path, no=2):
    g = _gorev(tmp_path, no=no)
    (tmp_path / "buyume").mkdir()
    for ad in ("oneriler.json", "arastirma.md"):
        (tmp_path / "buyume" / ad).write_text("{}", encoding="utf-8")
    return g


def test_G15_denetimsiz_istasyondan_sonra_kilit(tmp_path, monkeypatch):
    from deepspace import is_kaydi
    monkeypatch.setattr(is_kaydi, "gecerli_mi", lambda k, i: (i == "marka", "test"))
    ok, neden = is_kaydi.kilit(tmp_path, "konsept", 2)
    assert not ok and "arastirma" in neden
    assert is_kaydi.kilit(tmp_path, "konsept", 1) == (True, "kilit dışı")


def test_G15_kaldi_kilitler_ozet_degisince_gecersiz(tmp_path):
    from deepspace import is_kaydi
    _istasyon_gorevi(tmp_path)
    is_kaydi.kayit_yaz(tmp_path, "arastirma", "KALDI", "denetci", [{"kod": "x", "not": "y", "kanit": ""}], [])
    assert not is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]
    is_kaydi.kayit_yaz(tmp_path, "arastirma", "GECTI", "denetci", [], [])
    assert is_kaydi.kayit_oku(tmp_path, "arastirma")["tur"] == 2
    assert is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]
    (tmp_path / "buyume" / "oneriler.json").write_text('{"x": 1}', encoding="utf-8")
    assert not is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]


def test_G15_kirmizi_kapida_ya_da_ciktisiz_gecti_yazilamaz(tmp_path):
    from deepspace import is_kaydi
    _istasyon_gorevi(tmp_path)
    with pytest.raises(is_kaydi.KilitHatasi):
        is_kaydi.kayit_yaz(tmp_path, "arastirma", "GECTI", "denetci", [], ["ses kapısı"])
    with pytest.raises(is_kaydi.KilitHatasi):
        is_kaydi.kayit_yaz(tmp_path, "video", "GECTI", "denetci", [], [])  # video.mp4 yok


def test_G15_ucuncu_turdan_sonra_sefte_ve_bozuk_kayit(tmp_path):
    from deepspace import is_kaydi
    _istasyon_gorevi(tmp_path)
    for _ in range(3):
        is_kaydi.kayit_yaz(tmp_path, "arastirma", "KALDI", "denetci", [], [])
    satir = next(s for s in is_kaydi.durum(tmp_path)["istasyonlar"] if s["ad"] == "arastirma")
    assert satir["sefte"] and satir["tur"] == 3
    is_kaydi.kayit_yolu(tmp_path, "arastirma").write_text("{bozuk", encoding="utf-8")
    assert is_kaydi.kayit_oku(tmp_path, "arastirma") is None
    assert not is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]


def test_G15_ozet_satir_sonundan_bagimsiz_ve_cop_dosya_sayilmaz(tmp_path):
    from deepspace import is_kaydi
    _istasyon_gorevi(tmp_path)
    is_kaydi.kayit_yaz(tmp_path, "arastirma", "GECTI", "denetci", [], [])
    (tmp_path / "buyume" / "arastirma.md").write_bytes(b"satir\r\nikinci\r\n")
    is_kaydi.kayit_yaz(tmp_path, "arastirma", "GECTI", "denetci", [], [])
    (tmp_path / "buyume" / "arastirma.md").write_bytes(b"satir\nikinci\n")      # Linux klonu: LF
    assert is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]
    (tmp_path / "buyume" / "Thumbs.db").write_bytes(b"x")
    assert is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]


def test_G15_gorsel_yeniden_uretimi_konsept_kararini_bozmaz(tmp_path):
    from deepspace import is_kaydi
    g = _istasyon_gorevi(tmp_path)
    toml = tmp_path / "gorev.toml"
    toml.write_text('no = 2\nhedef = "X"\n\n[[parca]]\nad = "A"\ngorsel_istem = "eski"\ngorsel_uretim = "1"\n',
                    encoding="utf-8")
    (tmp_path / "SUNO.md").write_text("s", encoding="utf-8")
    is_kaydi.kayit_yaz(tmp_path, "konsept", "GECTI", "denetci", [], [])
    (tmp_path / "gorsel").mkdir()
    _resim(tmp_path / "gorsel" / "01.png", 64, 36)
    is_kaydi.kayit_yaz(tmp_path, "gorsel", "GECTI", "denetci", [], [])
    toml.write_text(toml.read_text(encoding="utf-8").replace('"eski"', '"yeni, no extra people"')
                    .replace('"1"', '"2"'), encoding="utf-8")
    assert is_kaydi.gecerli_mi(tmp_path, "konsept")[0]            # istem değişti, konsept geçerli
    assert not is_kaydi.gecerli_mi(tmp_path, "gorsel")[0]         # görsel istasyonu yeniden denetlenir
    toml.write_text(toml.read_text(encoding="utf-8").replace('ad = "A"', 'ad = "B"'), encoding="utf-8")
    assert not is_kaydi.gecerli_mi(tmp_path, "konsept")[0]


def test_G15_onceki_istasyon_degisirse_sonraki_karar_gecersiz(tmp_path):
    from deepspace import is_kaydi
    _istasyon_gorevi(tmp_path)
    (tmp_path / "SUNO.md").write_text("s", encoding="utf-8")
    is_kaydi.kayit_yaz(tmp_path, "arastirma", "GECTI", "denetci", [], [])
    is_kaydi.kayit_yaz(tmp_path, "konsept", "GECTI", "denetci", [], [])
    assert is_kaydi.gecerli_mi(tmp_path, "konsept")[0]
    (tmp_path / "buyume" / "oneriler.json").write_text('{"secilen": 1}', encoding="utf-8")
    is_kaydi.kayit_yaz(tmp_path, "arastirma", "GECTI", "denetci", [], [])   # yeniden onaylandı
    ok, neden = is_kaydi.gecerli_mi(tmp_path, "konsept")
    assert not ok and "arastirma" in neden


def test_G15_tur_gecti_sonrasi_yeniden_baslar(tmp_path):
    from deepspace import is_kaydi
    _istasyon_gorevi(tmp_path)
    for karar in ("KALDI", "KALDI", "GECTI", "KALDI"):
        is_kaydi.kayit_yaz(tmp_path, "arastirma", karar, "denetci", [], [])
    assert is_kaydi.kayit_oku(tmp_path, "arastirma")["tur"] == 1


def test_G16_marka_degisince_eski_kararlar_gecersiz(tmp_path, monkeypatch):
    from deepspace import is_kaydi
    _istasyon_gorevi(tmp_path)
    monkeypatch.setattr(is_kaydi, "marka_ozeti", lambda: "a")
    is_kaydi.kayit_yaz(tmp_path, "arastirma", "GECTI", "denetci", [], [])
    assert is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]
    monkeypatch.setattr(is_kaydi, "marka_ozeti", lambda: "b")
    assert not is_kaydi.gecerli_mi(tmp_path, "arastirma")[0]


def test_G16_marka_sahip_onayi_olmadan_gecersiz(tmp_path, monkeypatch):
    from deepspace import is_kaydi
    monkeypatch.setattr(is_kaydi, "MARKA_KLASORU", tmp_path / "marka")
    monkeypatch.setattr(is_kaydi, "MARKA_DOSYASI", tmp_path / "marka.toml")
    (tmp_path / "marka").mkdir()
    (tmp_path / "marka.toml").write_text("durum = 'x'\n", encoding="utf-8")
    (tmp_path / "marka" / "banner.jpg").write_bytes(b"1")
    with pytest.raises(is_kaydi.KilitHatasi):
        is_kaydi.sahip_onayi_yaz("sahip")                      # denetçi kararı yok
    is_kaydi.kayit_yaz(None, "marka", "GECTI", "denetci", [], [])
    assert not is_kaydi.gecerli_mi(None, "marka")[0]
    is_kaydi.sahip_onayi_yaz("sahip")
    assert is_kaydi.gecerli_mi(None, "marka")[0]
    (tmp_path / "marka" / "banner.jpg").write_bytes(b"2")     # kit değişti
    assert not is_kaydi.gecerli_mi(None, "marka")[0]


def test_G16_sablon_yazilari_telefon_kuralini_saglar():
    m = ortak.marka_yukle()
    assert m["sablon"]["kapak_etiket"] >= 0.02 * 720
    assert m["sablon"]["short_etiket"] >= 0.02 * 1920
    assert "Earth-like" not in m["gorsel"]["stil_eki"]
    assert "Earth-like" in m["gorsel"]["stil_eki_001"]  # 001'in istemleri geriye dönük okunur
    assert m["yazi"]["baslik_font"].startswith("SpaceMono")


def _yazi_satirlari(katman):
    a = np.asarray(katman)[..., 3]
    return np.nonzero(a.max(axis=1) > 0)[0]


def test_G16_kapak_sablonu_uc_duzen():
    from deepspace import yazi
    m = ortak.marka_yukle()["sablon"]
    ust = _yazi_satirlari(yazi.kapak_katmani(1280, 720, "DEEP FOCUS", "2H", "ust"))
    alt = _yazi_satirlari(yazi.kapak_katmani(1280, 720, "DEEP FOCUS", "2H", "alt"))
    assert ust.max() < 720 * 0.35 and alt.min() > 720 * 0.6  # başlık üstte / altta
    k = np.asarray(yazi.kapak_katmani(1280, 720, "DEEP FOCUS", "2H", "etiket"))
    vurgu = np.array(ortak.rgb(ortak.marka_yukle()["palet"]["vurgu"]))
    renkli = np.nonzero((np.abs(k[..., :3].astype(int) - vurgu).sum(axis=2) < 30) & (k[..., 3] > 200))[0]
    beyaz = np.nonzero((k[..., :3].min(axis=2) > 225) & (k[..., 3] > 200))[0]
    assert renkli.min() < beyaz.min()  # seri etiketi (kehribar) başlığın önünde
    with pytest.raises(ValueError):
        yazi.kapak_katmani(1280, 720, "DEEP FOCUS", "2H", "yan")
    assert m["kapak_baslik"] > m["kapak_etiket"]


def test_G16_kanal_kiti_kaynak_gorselden(tmp_path):
    from PIL import Image
    from deepspace import marka_kiti
    kaynak = KOK / "deepspace" / "marka" / "kaynak" / "A2.png"
    yollar = marka_kiti.uret(kaynak, tmp_path)
    boyut = {p.name: Image.open(p).size for p in yollar}
    assert boyut == {"banner.jpg": (2560, 1440), "profil.png": (800, 800), "filigran.png": (150, 150),
                     "marka_kitabi.jpg": (1600, 1500)}
    assert Image.open(tmp_path / "filigran.png").mode == "RGBA"
    assert (tmp_path / "banner.jpg").stat().st_size < 6 * 1024 * 1024  # YouTube banner sınırı


def test_G16_filigran_probe_halkada_kenarlar_seffaf():
    from PIL import Image
    from deepspace import marka_kiti
    a = np.asarray(marka_kiti.filigran())[..., 3]
    assert max(a[0].max(), a[-1].max(), a[:, 0].max(), a[:, -1].max()) == 0  # kenarda kesilme yok
    p = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
    marka_kiti.probe_ekle(p, 75, 75, marka_kiti.FILIGRAN_PROBE)
    ys, xs = np.nonzero(np.asarray(p)[..., 3] > 0)
    ic_r = (marka_kiti.FILIGRAN_HALKA[1] - marka_kiti.FILIGRAN_HALKA[0]) / 2 - 3
    assert np.hypot(xs + 0.5 - 75, ys + 0.5 - 75).max() <= ic_r - 3  # panel uçları halkanın içinde


def test_G16_banner_yazi_probe_ve_ufuk_gorunen_bantta():
    from PIL import Image
    from deepspace import marka_kiti
    gx, gy = marka_kiti.GUVENLI_ALAN
    x0, y0, x1, y1 = (2560 - gx) / 2, (1440 - gy) / 2, (2560 + gx) / 2, (1440 + gy) / 2
    for ciz in (lambda k: marka_kiti._baslik(k, "DEEP SPACE LOG", marka_kiti.ALT_YAZI, marka_kiti.BANNER_BASLIK_Y,
                                             120, 34, 560),
                lambda k: marka_kiti.probe_ekle(k, 1280, marka_kiti.BANNER_PROBE_Y, marka_kiti.BANNER_PROBE_BOY)):
        k = Image.new("RGBA", (2560, 1440), (0, 0, 0, 0))
        ciz(k)
        ys, xs = np.nonzero(np.asarray(k)[..., 3] > 0)
        assert xs.min() >= x0 and xs.max() <= x1 and ys.min() >= y0 and ys.max() <= y1
    ana = Image.open(KOK / "deepspace" / "marka" / "kaynak" / "A2.png").convert("RGB")
    L = np.asarray(marka_kiti._banner_kaynak(ana).resize((2560, 1440)).convert("L"), float)
    ufuk = 700 + int(L[700:1200, 1280].argmax())  # ufuk kemerinin parlak kenarı, ortada
    assert marka_kiti.BANNER_PROBE_Y < ufuk <= y1


def test_G15_komut_kilidi_cikis_3(tmp_path, monkeypatch, capsys):
    from deepspace import gorev as cli, is_kaydi
    monkeypatch.setattr(cli, "gorev_yukle", lambda k: (_gorev(tmp_path, no=2), AYAR))
    monkeypatch.setattr(is_kaydi, "gecerli_mi", lambda k, i: (False, "denetim yok"))
    assert cli.main(["video", str(tmp_path)]) == 3
    assert cli.main(["hepsi", str(tmp_path)]) == 3
    assert "marka" in capsys.readouterr().out


def test_G16_onaysiz_marka_kitiyle_kapak_ve_video_calismaz(tmp_path, monkeypatch):
    from deepspace import gorev as cli, is_kaydi
    monkeypatch.setattr(cli, "gorev_yukle", lambda k: (_gorev(tmp_path, no=2), AYAR))
    monkeypatch.setattr(is_kaydi, "gecerli_mi", lambda k, i: (i != "marka", "sahip onayı yok"))
    assert cli.main(["kapak", str(tmp_path)]) == 3
    assert cli.main(["video", str(tmp_path)]) == 3


def test_G15_001_kilit_disi_ve_denetim_komutu(tmp_path, monkeypatch):
    from deepspace import gorev as cli, is_kaydi
    monkeypatch.setattr(cli, "gorev_yukle", lambda k: (_gorev(tmp_path, no=1), AYAR))
    assert cli.main(["durum", str(tmp_path)]) == 0
    assert cli.main(["kilit", str(tmp_path), "--istasyon", "video"]) == 0
    _istasyon_gorevi(tmp_path, no=1)
    assert cli.main(["denetim", str(tmp_path), "--istasyon", "arastirma", "--karar", "KALDI",
                     "--bulgu", "kaynak:rakam kaynaksız"]) == 0
    k = is_kaydi.kayit_oku(tmp_path, "arastirma")
    assert k["karar"] == "KALDI" and k["bulgular"][0] == {"kod": "kaynak", "not": "rakam kaynaksız", "kanit": ""}
    assert cli.main(["denetim", str(tmp_path), "--istasyon", "video", "--karar", "GECTI"]) == 3


def _on_bolum(yol):
    satirlar = yol.read_text(encoding="utf-8").split("---")[1].strip().splitlines()
    return {a.strip(): b.strip() for a, _, b in (s.partition(":") for s in satirlar if ":" in s)}


def test_G15_ajan_dosyalari():
    klasor = KOK / ".claude" / "agents"
    beklenen = {"marka-tasarimcisi": "opus", "konsept-yazari": "sonnet", "bilgi-dogrulayici": "sonnet",
                "gorsel-yonetmeni": "sonnet", "gorsel-denetcisi": "opus", "hareket-tarifcisi": "sonnet",
                "operator": "haiku", "kod-ustasi": "sonnet", "denetci": "opus", "youtube-uzmani": "opus",
                "shorts-kurgucusu": "sonnet"}
    for ad, model in beklenen.items():
        on = _on_bolum(klasor / f"{ad}.md")
        assert on["name"] == ad and on["model"] == model and on["tools"] and on["effort"]
    denetci = _on_bolum(klasor / "denetci.md")
    assert not {"Write", "Edit", "NotebookEdit"} & {t.strip() for t in denetci["tools"].split(",")}
    uzman = _on_bolum(klasor / "youtube-uzmani.md")
    assert uzman["effort"] == "high"
    from deepspace import vidiq_butce
    araclar = {t.strip() for t in uzman["tools"].split(",")}
    assert {f"mcp__claude_ai_vidIQ__{a}" for a in vidiq_butce.IZINLI} <= araclar
    assert not any("generate" in t or "reply" in t or "upload" in t or "update" in t for t in araclar)


def test_G17_vidiq_izin_listesi_ve_tavan(tmp_path):
    from datetime import datetime, timezone
    from deepspace import vidiq_butce as vb
    d, ayar = tmp_path / "h.jsonl", {"vidiq": {"aylik_kredi": 10, "yenileme_gunu": 27, "cagri_kredi": 5}}
    t = datetime(2026, 11, 28, tzinfo=timezone.utc)
    assert not vb.karar("mcp__claude_ai_vidIQ__vidiq_generate_video", d, ayar, t)[0]
    assert not vb.karar("mcp__claude_ai_vidIQ__vidiq_reply_to_comment", d, ayar, t)[0]
    assert vb.karar("mcp__claude_ai_vidIQ__vidiq_balance", d, ayar, t)[0]
    assert vb.karar("mcp__vidIQ__vidiq_outliers", d, ayar, t)[0]
    assert vb.karar("mcp__claude_ai_vidIQ__vidiq_keyword_research", d, ayar, t)[0]
    assert not vb.karar("mcp__claude_ai_vidIQ__vidiq_outliers", d, ayar, t)[0]   # 10 kredi doldu
    assert vb.harcanan(d, vb.donem_basi(t, 27)) == 10                           # balance düşmedi
    assert len(d.read_text(encoding="utf-8").splitlines()) == 3
    yeni_donem = datetime(2026, 12, 27, 1, tzinfo=timezone.utc)
    assert vb.karar("mcp__claude_ai_vidIQ__vidiq_outliers", d, ayar, yeni_donem)[0]
    assert vb.donem_basi(datetime(2026, 1, 5, tzinfo=timezone.utc), 27).isoformat() == "2025-12-27"


def test_G17_kanca_bozuk_girdiyi_reddeder(monkeypatch):
    import io
    from deepspace import vidiq_butce as vb
    monkeypatch.setattr("sys.stdin", io.StringIO("{bozuk"))
    assert vb.main() == 2
    monkeypatch.setattr("sys.stdin", io.StringIO('{"tool_name": "mcp__claude_ai_vidIQ__vidiq_update_video"}'))
    assert vb.main() == 2


def test_G17_kanca_hata_verirse_cagriyi_reddeder(tmp_path, monkeypatch):
    import io
    from datetime import datetime, timezone
    from deepspace import vidiq_butce as vb
    d = tmp_path / "h.jsonl"
    d.write_bytes(b'{"zaman": "2026-11-28T00:00:00+00:00", "arac": "x", "kredi": 5}\n\xff\xfe\n')
    monkeypatch.setattr(vb, "DEFTER", d)
    monkeypatch.setattr("sys.stdin", io.StringIO('{"tool_name": "mcp__claude_ai_vidIQ__vidiq_outliers"}'))
    assert vb.main() == 2                                          # bozuk defter: kapalı başarısızlık
    ayar = {"vidiq": {"aylik_kredi": 10, "yenileme_gunu": 27, "cagri_kredi": 5}}
    d.write_text('{"zaman": "2026-11-28T00:00:00+00:00", "arac": "elle", "kredi": -500}\n'
                 '{"zaman": "2026-11-28T00:00:00+00:00", "arac": "x", "kredi": 10}\n', encoding="utf-8")
    t = datetime(2026, 11, 28, 5, tzinfo=timezone.utc)
    assert vb.harcanan(d, vb.donem_basi(t, 27)) == 10              # negatif satır bütçeyi açmaz
    assert not vb.karar("mcp__claude_ai_vidIQ__vidiq_outliers", d, ayar, t)[0]


def test_G9_beyan_secimi_sistemin_yaptigini_dogru_soyler():
    from deepspace import shorts
    assert "hand-selected" not in metin.SUREC_NOTU and "hand-selected" not in shorts.SHORTS_NOTU


def test_G17_kanca_proje_ayarinda():
    s = json.loads((KOK / ".claude" / "settings.json").read_text(encoding="utf-8"))
    kanca = s["hooks"]["PreToolUse"][0]
    assert re.fullmatch(kanca["matcher"], "mcp__claude_ai_vidIQ__vidiq_outliers")
    assert re.fullmatch(kanca["matcher"], "mcp__vidIQ__vidiq_outliers")
    assert "deepspace.vidiq_butce" in kanca["hooks"][0]["command"]


def test_G2_ses_dosyasi_wav_uzantisiyla_da_bulunur(tmp_path):
    g = _gorev(tmp_path, n=2)
    (tmp_path / "ses").mkdir()
    (tmp_path / "ses" / "01.wav").write_bytes(b"x")
    yollar = ses.ses_dosyalari(g)
    assert yollar[0].name == "01.wav" and yollar[1].name == "02.mp3" and not yollar[1].exists()
