"""Tiny Fixes (SOZLESME.md F bölümü) testleri. Her madde burada denetlenir; ağa ve gerçek Claude/X/Instagram'a çıkılmaz."""

import ast
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot import (config, flood, flood_denetci as den, flood_dogrula, flood_gorsel, flood_ig, flood_kaynak, flood_puan,
                 flood_yazar, flood_yetki)

UTC = timezone.utc
SIMDI = datetime(2026, 10, 15, 14, 5, tzinfo=UTC)
AYAR = flood.FloodAyar(mod="onay", alarm_kime="sahip")
ANA = config.yukle()
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _izole(monkeypatch, tmp_path):
    monkeypatch.setattr(flood, "DOSYA", tmp_path / "flood.json")
    monkeypatch.setattr(flood_yetki, "X_DOSYA", tmp_path / "x.enc")
    monkeypatch.setattr(flood_yetki, "IG_DOSYA", tmp_path / "ig.enc")
    from bot import saglik
    monkeypatch.setattr(saglik, "DOSYA", tmp_path / "saglik.json")


def kayit_fix() -> dict:
    return {"tur": "fix", "konu": "Phone battery draining after the update",
            "olgular": [{"metin": "Many users report faster battery drain after the 26.1 update",
                         "kaynaklar": ["https://www.alpha.com/a", "https://beta.org/b"]}],
            "kaynaklar": [], "arac": None,
            "denendi": {"model": "claude-sonnet-5-5", "ornek_girdi": "Screen 41%, Maps 22%, Mail 9%", "sure": "9 seconds",
                        "komut": "Here are my battery stats: <paste your battery stats here>. Rank the 5 most likely causes and give one check for each.",
                        "cikti": "1. Maps running in the background at 22% is the first suspect.",
                        "sinir": "It only reasons from the stats you paste and cannot read your phone."}}


def flood_fix() -> dict:
    return {"bicim": "flood",
            "x": {"postlar": ["Battery draining fast after the 26.1 update? Here is a prompt that ranks the likely causes from your own stats.",
                              "Many users report faster battery drain after the 26.1 update. The cause differs by phone, so guessing rarely works.",
                              "Paste this into an AI assistant: Here are my battery stats: <paste>. Rank the 5 most likely causes and give one check for each.",
                              "Tested with Claude Sonnet 5.5 on made-up stats. It put Maps at 22% first and said what to check.",
                              "The limit: it only reasons from the stats you paste and cannot read your phone.",
                              "Save this for the next update."],
                  "alternatif_hook": "A prompt that ranks why your battery drains after the 26.1 update, from your own stats.",
                  "link_yaniti": None},
            "ig": {"slaytlar": [{"baslik": "Battery draining after the update?", "metin": "Tested with Claude Sonnet 5.5", "tur": "icerik", "komut": ""},
                                {"baslik": "Why guessing fails", "metin": "The cause differs by phone.", "tur": "icerik", "komut": ""},
                                {"baslik": "The prompt", "metin": "", "tur": "komut", "komut": "Here are my battery stats: <paste>."},
                                {"baslik": "What it found", "metin": "Maps at 22% came first.", "tur": "icerik", "komut": ""},
                                {"baslik": "Save this", "metin": "Send it to a friend with the same problem.", "tur": "icerik", "komut": ""}],
                   "caption": "Phone battery draining after the update? A tested prompt that ranks the likely causes. Tested with Claude Sonnet 5.5.",
                   "etiketler": ["#AItools"]}}


# ---------- F1: kaynaklı olgu ----------

def test_F1_gecerli_kayit_ve_flood_temiz():
    assert den.kayit_kontrol(kayit_fix()) == []
    assert den.denetle(flood_fix(), kayit_fix()) == []


def test_F1_olgu_iki_bagimsiz_alan_adi_ister():
    k = kayit_fix()
    k["olgular"][0]["kaynaklar"] = ["https://a.example.com/1", "https://blog.example.com/2"]  # aynı alan adı
    assert any("2 bağımsız" in s for s in den.kayit_kontrol(k))
    assert den.alan_adi("https://www.blog.example.co.uk/x") == "example.co.uk"


def test_F1_haber_en_az_iki_olgu_ister():
    k = {"tur": "news", "konu": "New model released", "denendi": None, "arac": None,
         "olgular": [{"metin": "A lab released a model", "kaynaklar": ["https://a.com/1", "https://b.org/2"]}]}
    assert any("en az 2 doğrulanmış olgu" in s for s in den.kayit_kontrol(k))


def test_F1_yazar_kayitta_olmayan_rakam_uyduramaz():
    f = flood_fix()
    f["x"]["postlar"][1] = "Battery drain jumped 47% after the 26.1 update."
    assert any("kayıtta olmayan rakam" in s for s in den.denetle(f, kayit_fix()))
    f["x"]["postlar"][1] = "Here are 5 steps for the 26.1 update."  # liste boyutu bir olgu iddiası değildir
    assert not any("rakam" in s for s in den.denetle(f, kayit_fix()))


def test_F1_arama_uydurma_adresi_saymaz():
    metin = ("FACT: Lab X released model Y || SOURCES: https://real.com/a, https://other.org/b\n"
             "FACT: Invented claim || SOURCES: https://fake.com/a, https://fake2.org/b\n"
             "FACT: Single source only || SOURCES: https://real.com/a, https://sub.real.com/c\n")
    bilinen = {"https://real.com/a": "A", "https://other.org/b": "B", "https://sub.real.com/c": "C"}
    olgular = flood_dogrula.olgulari_ayikla(metin, bilinen)
    assert [o["metin"] for o in olgular] == ["Lab X released model Y"]  # uydurma adres ve tek alan adı elendi


# ---------- F2: denendi ----------

def test_F2_fix_denenmeden_gecmez_ve_sinir_ister():
    k = kayit_fix()
    k["denendi"] = None
    assert any("F2" in s for s in den.kayit_kontrol(k))
    k = kayit_fix()
    k["denendi"]["sinir"] = ""
    assert any("sınırı yazılmamış" in s for s in den.kayit_kontrol(k))


def test_F2_post_hangi_modelle_denendigini_yazar():
    f = flood_fix()
    f["x"]["postlar"][3] = "It put Maps at 22% first and said what to check."
    assert any("Tested with" in s for s in den.denetle(f, kayit_fix()))
    g = flood_fix()  # "tested" yazıyor ama modeli söylemiyor: yetmez
    g["x"]["postlar"][3] = "Tested on made-up stats. It put Maps at 22% first and said what to check."
    assert any("Tested with" in s for s in den.denetle(g, kayit_fix()))
    h = flood_fix()  # Instagram: carousel hiç "Tested" demiyor
    h["ig"]["slaytlar"][0]["metin"] = "A prompt for your battery"
    h["ig"]["caption"] = "Phone battery draining after the update? A prompt that ranks the likely causes."
    assert any("'Tested' ibaresini" in s for s in den.denetle(h, kayit_fix()))


class _Ctx:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return SimpleNamespace(get_final_message=lambda: self.msg)

    def __exit__(self, *a):
        return False


class SahteClaude:
    """stream(): sıradaki yanıt (dict -> JSON metin, SimpleNamespace -> olduğu gibi); create(): sıradaki metin."""

    def __init__(self, yanitlar=(), create=()):
        self.yanitlar, self.create_yanitlari, self.cagrilar = list(yanitlar), list(create), []
        self.messages = self

    def stream(self, **kw):
        self.cagrilar.append(kw)
        y = self.yanitlar.pop(0)
        if isinstance(y, SimpleNamespace):
            return _Ctx(y)
        return _Ctx(SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(y))]))

    def create(self, **kw):
        self.cagrilar.append(kw)
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=self.create_yanitlari.pop(0))])


def test_F2_komut_gercekten_calistirilir_ve_zayif_cikti_paylasilmaz():
    ayar = flood.FloodAyar(mod="onay")
    k = {"komut": "Summarize this: {INPUT}", "ornek_girdi": "made-up sample text", "gosterim": "Summarize this: <paste text>"}
    c = SahteClaude(create=["A short, correct summary."])
    d = flood_dogrula.dene(c, ayar, k)
    assert c.cagrilar[0]["model"] == ayar.test_model
    assert "made-up sample text" in c.cagrilar[0]["messages"][0]["content"]  # örnek girdi komuta gerçekten girmiş
    assert d["komut"] == "Summarize this: <paste text>" and d["cikti"] == "A short, correct summary." and d["sure"].endswith("seconds")
    zayif = SahteClaude(yanitlar=[{"kalite": "zayif", "sinir": "x"}, {"kalite": "iyi", "sinir": "  "}])
    assert flood_dogrula.degerlendir(zayif, ayar, d)["kalite"] == "zayif"
    # kutuphane_kaydi: zayıf çıktı ya da boş sınır cümlesi kayıt üretmez
    c2 = SahteClaude(yanitlar=[{"komut": "Do X with {INPUT}", "ornek_girdi": "s", "gosterim": "Do X with <paste>"},
                               {"kalite": "iyi", "sinir": "  "}], create=["out"])
    assert flood_dogrula.kutuphane_kaydi(c2, ayar, "tema", yaz=lambda *_: None) is None


# ---------- F3: sahte kişisel deneyim yok ----------

@pytest.mark.parametrize("kotu", ["I've been using this for months and it works.", "My clients love this prompt.",
                                  "After testing 40 tools this one won.", "I tested dozens of prompts."])
def test_F3_sahte_deneyim_reddedilir(kotu):
    f = flood_fix()
    f["x"]["postlar"][1] = kotu
    assert any("F3" in s for s in den.denetle(f, kayit_fix()))


def test_F3_yazar_sistemi_deneyim_uydurmayi_yasaklar():
    assert "Never claim personal experience" in flood_yazar.YAZAR_SISTEMI and "we ran it" in flood_yazar.YAZAR_SISTEMI


# ---------- F4: link ve affiliate ----------

def test_F4_ana_postta_link_yok_instagram_caption_linksiz():
    f = flood_fix()
    f["x"]["postlar"][1] = "Details at example.com for the 26.1 update."
    assert any("link" in s for s in den.denetle(f, kayit_fix()))
    g = flood_fix()
    g["ig"]["caption"] += " https://example.com"
    assert any("caption'da link" in s for s in den.denetle(g, kayit_fix()))


def test_F4_affiliate_ibaresi_ve_denenmis_arac_sart():
    k = kayit_fix()
    k["arac"] = {"ad": "ToolX", "affiliate_url": "https://toolx.example/ref?id=1"}
    f = flood_fix()
    f["x"]["link_yaniti"] = "Try it here: https://toolx.example/ref?id=1"
    assert any("'affiliate' ibaresi yok" in s for s in den.denetle(f, k))
    f["x"]["link_yaniti"] = "Try it here (affiliate link): https://toolx.example/ref?id=1"
    assert den.denetle(f, k) == []
    k["denendi"]["cikti"] = ""
    assert any("denenmemiş araç" in s or "F2" in s for s in den.denetle(f, k))
    f["x"]["link_yaniti"] = "See https://random.example/page"
    assert any("kayıtta olmayan link" in s for s in den.denetle(f, kayit_fix()))


# ---------- F5: güvenli alan ----------

@pytest.mark.parametrize("konu,kategori", [("New drug dosage advice from a chatbot", "sağlık"), ("Best stocks to invest in now", "finans"),
                                           ("Election results and AI", "siyaset"), ("Shooting suspect named by AI", "trajedi"),
                                           ("Company sued over AI model", "hukuk"), ("CEO accused of fraud", "kişi iddiası")])
def test_F5_guvensiz_alan(konu, kategori):
    assert kategori in den.guvensiz_alan(konu)
    aday = {"baslik": konu, "tur_ipucu": "news", "trafik": 0,
            "kaynaklar": [{"ad": "a", "url": f"https://a{i}.com/x", "baslik": konu + " AI model", "ozet": "", "tarih": SIMDI.isoformat(), "skor": 500, "yorum": 100} for i in range(4)]}
    assert flood_puan.sirala([aday], SIMDI) == []  # puanlamadan önce elenir: yazara hiç gitmez
    k = kayit_fix()
    k["konu"] = konu
    assert any("F5" in s for s in den.kayit_kontrol(k))


def test_F5_zararsiz_kelimeler_yanlis_alarm_vermez():
    assert den.guvensiz_alan("We investigate how Claude handles a long prompt") == []


# ---------- F6: onay ----------

class SahteGH:
    def __init__(self):
        self.acilan, self.yorumlar_, self.kapali, self.gelen = [], [], [], {}

    def issue_ac(self, baslik, govde, etiket):
        self.acilan.append((baslik, govde, etiket))
        return 40 + len(self.acilan)

    def yorumlar(self, no):
        return self.gelen.get(no, [])

    def yetkili(self, k):
        return False

    def yorum(self, no, m):
        self.yorumlar_.append((no, m))

    def kapat(self, no, m):
        self.kapali.append((no, m))

    def yaz(self, no, metin, kim="OWNER"):
        self.gelen.setdefault(no, []).append({"body": metin, "author_association": kim, "user": {"login": "sahip"}})


class SahteX:
    def __init__(self):
        self.gonderilen, self.medya = [], []

    def medya_yukle(self, png):
        self.medya.append(png)
        return f"m{len(self.medya)}"

    def gonder(self, metin, yanit=None, medya=None, **kw):
        self.gonderilen.append((metin, yanit, medya))
        return f"t{len(self.gonderilen)}"

    def metrikler_idle(self, idler):
        return [{"id": i, "public_metrics": {"impression_count": 120}} for i in idler]


class SahteIG:
    def __init__(self):
        self.yayinlar = []

    def kalan_hak(self):
        return 0, 100

    def carousel(self, urller, caption):
        self.yayinlar.append((urller, caption))
        return "ig1"

    def olcum(self, medya_id):
        return {"reach": 80, "saved": 5}


def bekleyen_birim(durum="onay_bekliyor", simdi=SIMDI):
    b = flood._birim(kayit_fix(), flood_fix(), simdi, AYAR, durum)
    b["issue"] = 41
    return b


@pytest.fixture
def hazirla(monkeypatch):
    monkeypatch.setattr(flood, "gorselleri_yayinla", lambda birim_id, jpegler, **kw: [f"https://img/{i}.jpg" for i in range(len(jpegler))])


def calistir(state, gh, simdi, x=None, ig=None, claude=None, ayar=AYAR):
    flood.DOSYA.write_text(json.dumps(state))
    flood.nabiz(ANA, simdi, yaz=lambda *_: None, gh=gh, ayar=ayar, get=lambda u: (_ for _ in ()).throw(RuntimeError("ağ yok")),
                istemci_fabrikasi=lambda s, y: (x, ig, claude))
    return flood.yukle()


def bos_state():
    return {"birimler": [], "konular": [], "gun": {}, "kutuphane": []}


def test_F6_onay_olmadan_trend_paylasilmaz_ok_ile_paylasilir(hazirla):
    gh, x, ig = SahteGH(), SahteX(), SahteIG()
    st = bos_state()
    st["birimler"].append(bekleyen_birim())
    s = calistir(st, gh, SIMDI + timedelta(minutes=10), x, ig)
    assert x.gonderilen == [] and ig.yayinlar == [] and s["birimler"][0]["durum"] == "onay_bekliyor"
    gh.yaz(41, "ok 2")
    s = calistir(s, gh, SIMDI + timedelta(minutes=20), x, ig)
    assert s["birimler"][0]["durum"] == "yayinlandi" and len(x.gonderilen) == 6 and len(ig.yayinlar) == 1
    assert x.gonderilen[0][0].startswith("A prompt that ranks")  # "ok 2" alternatif kancayı seçti
    assert x.gonderilen[1][1] == "t1" and x.gonderilen[0][2] == ["m1"]  # flood yanıt zinciri, ilk postta kart


def test_F6_iptal_onceliklidir_ve_sure_dolunca_taslak_duser(hazirla):
    gh, x = SahteGH(), SahteX()
    st = bos_state()
    st["birimler"] += [bekleyen_birim(), bekleyen_birim()]
    st["birimler"][1]["issue"], st["birimler"][1]["id"] = 42, "ikinci"
    gh.yaz(41, "ok")
    gh.yaz(41, "iptal")
    s = calistir(st, gh, SIMDI + timedelta(minutes=5), x, SahteIG())
    assert s["birimler"][0]["durum"] == "iptal" and x.gonderilen == []
    s = calistir(s, gh, SIMDI + timedelta(minutes=AYAR.onay_suresi_dk + 1), x, SahteIG())
    assert s["birimler"][1]["durum"] == "dustu" and x.gonderilen == []


def test_F6_yabancinin_ok_cevabi_sayilmaz(hazirla):
    gh, x = SahteGH(), SahteX()
    st = bos_state()
    st["birimler"].append(bekleyen_birim())
    gh.yaz(41, "ok", kim="NONE")
    s = calistir(st, gh, SIMDI + timedelta(minutes=5), x, SahteIG())
    assert s["birimler"][0]["durum"] == "onay_bekliyor" and x.gonderilen == []


def test_F6_yalnizca_evergreen_otomatiktir(hazirla):
    oto = flood.FloodAyar(mod="otomatik", alarm_kime="sahip")
    k = kayit_fix()
    k["tur"] = "library"
    assert flood._birim(k, flood_fix(), SIMDI, oto, "planli")["yayin_zamani"].startswith("2026-10-15T17:00")
    gh, x, ig = SahteGH(), SahteX(), SahteIG()
    st = bos_state()
    b = flood._birim(k, flood_fix(), SIMDI, oto, "planli")
    st["birimler"].append(b)
    s = calistir(st, gh, SIMDI, x, ig, ayar=oto)  # saatinden önce: çıkmaz
    assert x.gonderilen == []
    s = calistir(s, gh, SIMDI.replace(hour=17, minute=5), x, ig, ayar=oto)
    assert s["birimler"][0]["durum"] == "yayinlandi" and len(x.gonderilen) == 6


def test_F6_trend_taslagi_issue_acar_ve_slot_bir_kez_calisir(monkeypatch):
    gh = SahteGH()
    st = bos_state()
    kayit = kayit_fix()
    monkeypatch.setattr(flood, "_trend_adaylari", lambda *a: [(kayit, kayit["konu"])])
    monkeypatch.setattr(flood_yazar, "yaz", lambda *a, **k: (flood_fix(), []))
    sabah = SIMDI.replace(hour=7)  # yalnızca 06:00 trend slotu gelmiş
    flood.uret(AYAR, st, sabah, object(), gh, yaz=lambda *_: None)
    assert gh.acilan[0][2] == flood.ETIKET and st["birimler"][0]["durum"] == "onay_bekliyor"
    assert "ok 2" in gh.acilan[0][1] and "Kaynaklı olgular" in gh.acilan[0][1]
    flood.uret(AYAR, st, sabah, object(), gh, yaz=lambda *_: None)  # aynı slot yeniden denenmez (para harcar)
    assert len(gh.acilan) == 1 and st["gun"]["2026-10-15"]["slotlar"] == ["t6"]


# ---------- F7: başkalarına otomatik etkileşim yok ----------

def test_F7_istemcilerde_takip_begeni_dm_yontemi_yok():
    for kaynak in ("bot/flood_ig.py", "bot/flood.py"):
        agac = ast.parse((ROOT / kaynak).read_text(encoding="utf-8"))
        adlar = {n.name.lower() for n in ast.walk(agac) if isinstance(n, ast.FunctionDef)}
        assert not any(k in a for a in adlar for k in ("takip", "follow", "begen", "like", "dm", "etiketle", "yanitla")), (kaynak, adlar)
    assert not any(k in flood_yazar.YAZAR_SEMASI["properties"] for k in ("mention", "reply_to"))


def test_F7_postlarda_at_isareti_yok():
    f = flood_fix()
    f["x"]["postlar"][1] = "Thanks @someone for the 26.1 update tip."
    assert any("'@' var" in s for s in den.denetle(f, kayit_fix()))


def test_F7_yorum_kiti_yalnizca_taslak_ve_flood_sesi_var():
    from bot import yorum
    assert yorum.ETIKETLER["flood"] == "yorum-kiti-flood"
    assert "Tiny Fixes" in yorum._flood_sesi()


# ---------- F8: biçim ----------

def test_F8_flood_uzunlugu_ve_post_sinirlari():
    f = flood_fix()
    f["x"]["postlar"] = f["x"]["postlar"][:4]
    assert any("5-9 post" in s for s in den.denetle(f, kayit_fix()))
    g = flood_fix()
    g["x"]["postlar"][1] = "The 26.1 update " + "x" * 300
    assert any("sınır 280" in s for s in den.denetle(g, kayit_fix()))


@pytest.mark.parametrize("metin", ["This is a game-changer for the 26.1 update.", "Insane battery fix for the 26.1 update.",
                                   "RT if your battery dies after the 26.1 update.", "Here's what the 26.1 update broke.",
                                   "It's not the battery, it's the 26.1 update."])
def test_F8_abarti_tuzak_ve_yapay_zeka_izi_reddedilir(metin):
    f = flood_fix()
    f["x"]["postlar"][1] = metin
    assert den.denetle(f, kayit_fix())


def test_F8_etiket_kurallari():
    f = flood_fix()
    f["x"]["postlar"][1] += " #AI"
    f["x"]["postlar"][2] += " #ChatGPT"
    assert any("en fazla 1 etiket" in s for s in den.denetle(f, kayit_fix()))
    g = flood_fix()
    g["x"]["postlar"][5] += " #trending"
    assert any("genel/trend etiketi" in s for s in den.denetle(g, kayit_fix()))


def test_F8_instagram_biçimi():
    f = flood_fix()
    f["ig"]["slaytlar"] = f["ig"]["slaytlar"][:1]
    assert any("2-10 slayt" in s for s in den.denetle(f, kayit_fix()))
    g = flood_fix()
    g["ig"]["etiketler"] = [f"#t{i}" for i in range(6)]
    assert any("en fazla 5 etiket" in s for s in den.denetle(g, kayit_fix()))
    h = flood_fix()
    h["ig"]["caption"] = "Tested. " + "a" * 2300
    assert any("2200" in s for s in den.denetle(h, kayit_fix()))
    assert any("günde en fazla 3 Instagram" in s for s in den.ig_kontrol(flood_fix(), kayit_fix(), bugunku_ig=3))


def test_F8_instagram_gorselleri_jpegdir():
    jpegler = flood_gorsel.carousel(flood_fix()["ig"]["slaytlar"], "Here are my battery stats: <paste>.")
    assert len(jpegler) == 5 and all(j[:3] == b"\xff\xd8\xff" for j in jpegler)  # Instagram yalnızca JPEG kabul eder
    from PIL import Image
    import io
    assert Image.open(io.BytesIO(jpegler[0])).size == (1080, 1350)


def test_F8_ayni_metin_ayni_gun_iki_kez_paylasilmaz():
    f = flood_fix()
    assert any("D2" in s for s in den.denetle(f, kayit_fix(), bugunku_metinler=[f["x"]["postlar"][2]]))


def test_F8_gunluk_birim_siniri_ve_aralik(hazirla):
    gh, x, ig = SahteGH(), SahteX(), SahteIG()
    st = bos_state()
    for i in range(2):
        b = bekleyen_birim("onaylandi")
        b["id"] = f"b{i}"
        st["birimler"].append(b)
    s = calistir(st, gh, SIMDI, x, ig)
    assert [b["durum"] for b in s["birimler"]] == ["yayinlandi", "onaylandi"]  # nabız başına bir birim
    s = calistir(s, gh, SIMDI + timedelta(minutes=30), x, ig)
    assert s["birimler"][1]["durum"] == "onaylandi"  # birim aralığı (90 dk) dolmadı
    s = calistir(s, gh, SIMDI + timedelta(minutes=95), x, ig)
    assert s["birimler"][1]["durum"] == "yayinlandi"
    s["gun"]["2026-10-15"]["birim"] = den.GUNLUK_BIRIM
    b = bekleyen_birim("onaylandi")
    b["id"] = "fazla"
    s["birimler"].append(b)
    x2 = SahteX()
    s = calistir(s, gh, SIMDI + timedelta(minutes=200), x2, ig)
    assert x2.gonderilen == []  # günde en fazla 4 birim


def test_F8_son_kapi_yayin_aninda_yeniden_denetler(hazirla):
    gh, x = SahteGH(), SahteX()
    st = bos_state()
    b = bekleyen_birim("onaylandi")
    b["flood"]["x"]["postlar"][1] = "A game-changer for the 26.1 update."  # kayıttan sonra bozulmuş
    st["birimler"].append(b)
    s = calistir(st, gh, SIMDI, x, SahteIG())
    assert s["birimler"][0]["durum"] == "hata" and x.gonderilen == []


# ---------- F9: mod ----------

def test_F9_varsayilan_mod_kapali_ve_kapaliyken_hicbir_sey_okunmaz():
    assert flood.ayar_yukle().mod == "kapali" and flood.FloodAyar().mod == "kapali"

    def patla(*a):
        raise AssertionError("kapalı modda istemci/anahtar okunmamalı")
    flood.nabiz(ANA, SIMDI, gh=patla, ayar=flood.FloodAyar(mod="kapali"), istemci_fabrikasi=patla)
    assert not flood.DOSYA.exists()


def test_F9_anahtar_yoksa_yalnizca_taslak(hazirla):
    gh = SahteGH()
    st = bos_state()
    st["birimler"].append(bekleyen_birim("onaylandi"))
    s = calistir(st, gh, SIMDI, None, None)
    assert s["birimler"][0]["durum"] == "onaylandi"  # paylaşılmadı, kayıp da yok


def test_F9_yarim_kalan_flood_kaldigi_yerden_surer(hazirla):
    class Patlayan(SahteX):
        def gonder(self, metin, yanit=None, medya=None, **kw):
            if len(self.gonderilen) == 3:
                raise RuntimeError("X 503")
            return super().gonder(metin, yanit, medya)
    gh, x = SahteGH(), Patlayan()
    st = bos_state()
    st["birimler"].append(bekleyen_birim("onaylandi"))
    s = calistir(st, gh, SIMDI, x, None)
    assert s["birimler"][0]["durum"] == "onaylandi" and len(s["birimler"][0]["x"]["idler"]) == 3
    x2 = SahteX()
    x2.gonderilen = [("", None, None)] * 3
    s = calistir(s, gh, SIMDI + timedelta(minutes=8), x2, None)
    assert s["birimler"][0]["durum"] == "yayinlandi" and len(x2.gonderilen) == 6  # 3 yeni post, çift paylaşım yok


# ---------- Kaynaklar ve puan ----------

TRENDS = """<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
<item><title>iphone battery drain</title><ht:approx_traffic>200,000+</ht:approx_traffic><pubDate>Thu, 15 Oct 2026 12:00:00 +0000</pubDate>
<ht:news_item><ht:news_item_title>iOS update drains battery</ht:news_item_title><ht:news_item_snippet>Users report</ht:news_item_snippet>
<ht:news_item_url>https://www.example.com/a</ht:news_item_url><ht:news_item_source>Example</ht:news_item_source></ht:news_item></item></channel></rss>"""
RSS = """<rss version="2.0"><channel><item><title>OpenAI releases a new GPT model</title><link>https://openai.com/news/x</link>
<pubDate>Thu, 15 Oct 2026 13:00:00 GMT</pubDate><description>&lt;p&gt;Details&lt;/p&gt;</description></item></channel></rss>"""
ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Anthropic ships Claude update</title><link href="https://anthropic.com/news/y"/>
<updated>2026-10-15T12:30:00Z</updated></entry></feed>"""
HN = json.dumps({"hits": [{"title": "OpenAI releases a new GPT model", "url": "https://news.example.com/gpt", "points": 540,
                           "num_comments": 210, "created_at_i": int(SIMDI.timestamp()) - 3600}]})


def test_kaynak_ayristiricilar():
    t = flood_kaynak.trends_ayristir(TRENDS)[0]
    assert t["baslik"] == "iphone battery drain" and t["trafik"] == 200000 and t["kaynaklar"][0]["url"] == "https://www.example.com/a"
    assert flood_kaynak.rss_ayristir(RSS, "OpenAI")[0]["kaynaklar"][0]["tarih"] == "2026-10-15T13:00:00+00:00"
    assert flood_kaynak.rss_ayristir(ATOM, "Anthropic")[0]["kaynaklar"][0]["url"] == "https://anthropic.com/news/y"
    assert flood_kaynak.hn_ayristir(HN)[0]["kaynaklar"][0]["skor"] == 540


def test_kaynak_birlestirme_ve_bozuk_kaynak_digerlerini_engellemez():
    ayar = flood.FloodAyar(rss=(("OpenAI", "https://x/rss"), ("Bozuk", "https://bozuk/rss")))

    def get(url):
        if "bozuk" in url:
            raise RuntimeError("boom")
        return {"trends": TRENDS, "algolia": HN, "x/rss": RSS}[next(k for k in ("trends", "algolia", "x/rss") if k in url)]
    mesajlar = []
    adaylar = flood_kaynak.topla(ayar, get, mesajlar.append)
    gpt = next(a for a in adaylar if "GPT" in a["baslik"])
    assert len(gpt["kaynaklar"]) == 2 and any("Bozuk" in m for m in mesajlar)  # iki kaynakta görünen konu birleşti
    with pytest.raises(RuntimeError):
        flood_kaynak.topla(ayar, lambda u: (_ for _ in ()).throw(RuntimeError("x")), lambda *_: None)


def test_puan_cok_kaynak_taze_ve_hizli_konu_onde_nissiz_haber_elenir():
    adaylar = flood_kaynak.birlestir(flood_kaynak.rss_ayristir(RSS, "OpenAI") + flood_kaynak.hn_ayristir(HN)
                                     + flood_kaynak.rss_ayristir(ATOM, "Anthropic")
                                     + flood_kaynak.rss_ayristir(RSS.replace("OpenAI releases a new GPT model", "Local bakery wins award"), "Gazete"))
    sirali = flood_puan.sirala(adaylar, SIMDI)
    assert sirali[0]["baslik"].startswith("OpenAI releases") and all("bakery" not in a["baslik"] for a in sirali)  # alakasız haber girmez
    assert flood_puan.sirala(adaylar, SIMDI, gecmis=["OpenAI releases a new GPT model"])[0]["baslik"].startswith("Anthropic")  # işlenmiş konu elenir


# ---------- Yazar, görsel barındırma, Instagram, yetki ----------

def test_yazar_reddedilen_taslagi_sorunlarla_geri_gonderir():
    kotu = {"hook_a": "This is a game-changer for the 26.1 update.", "hook_b": "", "devam": ["a"] * 4,
            "ig_slaytlar": [], "ig_caption": "", "ig_etiketler": []}
    f = flood_fix()
    iyi = {"hook_a": f["x"]["postlar"][0], "hook_b": f["x"]["alternatif_hook"], "devam": f["x"]["postlar"][1:],
           "ig_slaytlar": f["ig"]["slaytlar"], "ig_caption": f["ig"]["caption"], "ig_etiketler": f["ig"]["etiketler"]}
    c = SahteClaude(yanitlar=[kotu, iyi])
    flood_, sorunlar = flood_yazar.yaz(c, flood.FloodAyar(), kayit_fix(), yaz_=lambda *_: None)
    assert sorunlar == [] and flood_["x"]["alternatif_hook"]
    assert "your_previous_draft_was_rejected_for" in c.cagrilar[1]["messages"][0]["content"]
    c2 = SahteClaude(yanitlar=[kotu] * flood_yazar.DENEME)
    assert flood_yazar.yaz(c2, flood.FloodAyar(), kayit_fix(), yaz_=lambda *_: None)[0] is None


def test_yazar_triage_guvensiz_ve_atla_konulari_almaz():
    adaylar = [{"baslik": f"t{i}", "kaynaklar": [{"ad": "a", "ozet": ""}]} for i in range(3)]
    c = SahteClaude(yanitlar=[{"secimler": [{"indeks": 0, "tur": "atla", "problem": "", "fikir": ""},
                                            {"indeks": 1, "tur": "fix", "problem": "why is x", "fikir": "ask AI"},
                                            {"indeks": 9, "tur": "news", "problem": "", "fikir": ""}]}])
    s = flood_yazar.triage(c, flood.FloodAyar(), adaylar)
    assert [x["aday"]["baslik"] for x in s] == ["t1"] and s[0]["tur"] == "fix"


def test_gorsel_dali_hata_mesaji_anahtari_sizdirmaz_ve_adres_beklenir(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GH_TOKEN", "gizli-token-123")
    import subprocess

    def run_hata(komut, **kw):
        raise subprocess.CalledProcessError(1, komut)
    with pytest.raises(RuntimeError) as e:
        flood.gorselleri_yayinla("b1", [b"x"], run=run_hata, head=None, bekle=lambda s: None)
    assert "gizli-token-123" not in str(e.value) and "gizli-token-123" not in repr(e.value.__cause__)
    komutlar = []
    urller = flood.gorselleri_yayinla("b1", [b"x", b"y"], run=lambda k, **kw: komutlar.append(k),
                                      head=lambda u, **kw: SimpleNamespace(status_code=200), bekle=lambda s: None)
    assert urller[0] == "https://raw.githubusercontent.com/owner/repo/flood-medya/b1/slayt1.jpg" and len(komutlar) == 4
    with pytest.raises(RuntimeError, match="erişilebilir değil"):
        flood.gorselleri_yayinla("b1", [b"x"], run=lambda k, **kw: None, head=lambda u, **kw: SimpleNamespace(status_code=404),
                                 bekle=lambda s: None)


class SahteOturum:
    def __init__(self, yanitlar):
        self.yanitlar, self.istekler = list(yanitlar), []

    def request(self, yontem, url, params=None, data=None, headers=None, timeout=None):
        self.istekler.append((yontem, url.split("graph.instagram.com/")[1], data or params))
        y = self.yanitlar.pop(0)
        return SimpleNamespace(status_code=y.get("_kod", 200), json=lambda: y, text=json.dumps(y), content=b"x")


def test_instagram_carousel_sirasi_ve_hata_durumunda_yayin_yok():
    o = SahteOturum([{"id": "c1"}, {"id": "c2"}, {"status_code": "FINISHED"}, {"status_code": "FINISHED"}, {"id": "k1"},
                     {"status_code": "FINISHED"}, {"id": "m1"}])
    ig = flood_ig.InstagramClient("tok", "123", surum="v23.0", oturum=o, bekle=lambda s: None)
    assert ig.carousel(["https://a/1.jpg", "https://a/2.jpg"], "Tested.") == "m1"
    yollar = [(y, p) for y, p, _ in o.istekler]
    assert yollar[0] == ("POST", "v23.0/123/media") and yollar[-1] == ("POST", "v23.0/123/media_publish")
    assert o.istekler[4][2]["media_type"] == "CAROUSEL" and o.istekler[4][2]["children"] == "c1,c2"
    with pytest.raises(flood_ig.IgHata):
        ig.carousel(["https://a/1.jpg"], "x")  # tek görsel carousel olmaz
    o2 = SahteOturum([{"id": "c1"}, {"id": "c2"}, {"status_code": "ERROR"}])
    with pytest.raises(flood_ig.IgHata):
        flood_ig.InstagramClient("tok", "123", oturum=o2, bekle=lambda s: None).carousel(["u1", "u2"], "x")
    assert not any(p.endswith("media_publish") for _, p, _ in o2.istekler)


def test_yetki_sifreli_saklar_ve_yanlis_hesabi_reddeder():
    flood_yetki.kaydet_ig("x-secret", "ig-token", "123", SIMDI)
    assert flood_yetki.ig_anahtar("x-secret")["token"] == "ig-token" and flood_yetki.ig_anahtar("baska-secret") is None
    assert b"ig-token" not in flood_yetki.IG_DOSYA.read_bytes()
    assert not flood_yetki.yenileme_gerekli(flood_yetki.ig_anahtar("x-secret"), SIMDI + timedelta(days=29))
    assert flood_yetki.yenileme_gerekli(flood_yetki.ig_anahtar("x-secret"), SIMDI + timedelta(days=31))
    assert "kalkylerat" in flood_yetki._yasak("x")


def test_olcum_24_saat_sonra_yalniz_ilk_post_idleri_sorulur(hazirla):
    x, ig = SahteX(), SahteIG()
    b = bekleyen_birim("yayinlandi")
    b["yayin"], b["x"]["idler"], b["ig"]["medya_id"] = SIMDI.isoformat(), ["t1", "t2"], "ig1"
    st = bos_state()
    st["birimler"].append(b)
    flood.olcum_guncelle(st, x, ig, SIMDI + timedelta(hours=23), yaz=lambda *_: None)
    assert "olcum" not in b
    flood.olcum_guncelle(st, x, ig, SIMDI + timedelta(days=1, hours=1), yaz=lambda *_: None)
    assert b["olcum"] == {"x": {"impression_count": 120}, "ig": {"reach": 80, "saved": 5}}


def test_alarm_hata_ve_sessizlik():
    st = bos_state()
    b = bekleyen_birim("hata")
    b["hata"] = ["x"]
    st["birimler"].append(b)
    assert any(k.startswith("flood-hata") for k, _ in flood.sorunlar(AYAR, st, SIMDI))
    st = bos_state()
    st["baslangic"] = (SIMDI - timedelta(hours=40)).isoformat()
    assert any(k.startswith("flood-sessiz") for k, _ in flood.sorunlar(AYAR, st, SIMDI))
    assert flood.sorunlar(flood.FloodAyar(mod="kapali"), st, SIMDI) == []


def test_sozlesme_f_bolumu_her_madde_icin_test_var():
    sozlesme = (ROOT / "SOZLESME.md").read_text(encoding="utf-8")
    bu_dosya = Path(__file__).read_text(encoding="utf-8")
    for no in range(1, 10):
        assert f"| F{no} |" in sozlesme and f"def test_F{no}_" in bu_dosya, f"F{no}"


# ---------- Uçtan uca (sahte Claude): araştırma, deneme, yazma, taslak ----------

def _arama_yaniti(metin, urller, durum="end_turn"):
    return SimpleNamespace(stop_reason=durum, content=[
        SimpleNamespace(type="text", text=metin),
        SimpleNamespace(type="web_search_tool_result", content=[SimpleNamespace(url=u, title="t") for u in urller])])


def _yazar_yaniti():
    f = flood_fix()
    return {"hook_a": f["x"]["postlar"][0], "hook_b": f["x"]["alternatif_hook"], "devam": f["x"]["postlar"][1:],
            "ig_slaytlar": f["ig"]["slaytlar"], "ig_caption": f["ig"]["caption"], "ig_etiketler": f["ig"]["etiketler"]}


def test_uctan_uca_trend_fix_taslagi(monkeypatch):
    k = kayit_fix()["denendi"]
    fakt = ("FACT: Many users report faster battery drain after the 26.1 update || SOURCES: https://www.alpha.com/a, https://beta.org/b\n")
    aday = {"baslik": "iphone battery drain", "tur_ipucu": "trend", "trafik": 200000,
            "kaynaklar": [{"ad": "Example", "url": "https://www.alpha.com/a", "baslik": "x", "ozet": "iOS update drains battery",
                           "tarih": SIMDI.isoformat(), "skor": 0, "yorum": 0}]}
    c = SahteClaude(yanitlar=[
        {"secimler": [{"indeks": 0, "tur": "fix", "problem": "Phone battery draining after the update", "fikir": "rank causes"}]},  # triage
        _arama_yaniti("thinking...", ["x"], "pause_turn"),                                                                          # araştırma, devam
        _arama_yaniti(fakt, ["https://www.alpha.com/a", "https://beta.org/b"]),
        {"komut": k["komut"].replace("<paste your battery stats here>", "{INPUT}"), "ornek_girdi": k["ornek_girdi"], "gosterim": k["komut"]},
        {"kalite": "iyi", "sinir": k["sinir"]},                                                                                    # değerlendirme
        _yazar_yaniti()], create=[k["cikti"]])
    monkeypatch.setattr(flood_kaynak, "topla", lambda *a, **kw: [aday])
    gh, st = SahteGH(), bos_state()
    flood.uret(AYAR, st, SIMDI.replace(hour=7), c, gh, yaz=lambda *_: None)
    b = st["birimler"][0]
    assert b["durum"] == "onay_bekliyor" and b["tur"] == "fix" and gh.acilan[0][2] == flood.ETIKET
    assert b["kayit"]["denendi"]["model"] == AYAR.test_model and b["kayit"]["olgular"][0]["kaynaklar"][0] == "https://www.alpha.com/a"
    assert den.denetle(b["flood"], b["kayit"]) == []
    arama = [x for x in c.cagrilar if x.get("tools")]
    assert arama and arama[0]["tools"][0]["type"] == "web_search_20260209"
    assert any(x.get("messages", [{}])[-1].get("role") == "assistant" for x in arama[1:])  # pause_turn kaldığı yerden sürdü


def test_uctan_uca_evergreen_otomatik_modda_planlanir_ve_tema_tekrarlanmaz(monkeypatch):
    oto = flood.FloodAyar(mod="otomatik", alarm_kime="sahip")
    k = kayit_fix()["denendi"]
    kayit_lib = {"tur": "library", "konu": flood_yazar.KUTUPHANE[0], "olgular": [], "kaynaklar": [], "arac": None,
                 "denendi": {**k, "komut": "Summarize: <paste>", "cikti": "A short summary.", "sinir": "It cannot check facts."}}
    gorulen = []
    monkeypatch.setattr(flood_dogrula, "kutuphane_kaydi", lambda c, a, tema, yaz=print: gorulen.append(tema) or {**kayit_lib, "konu": tema})
    monkeypatch.setattr(flood_yazar, "yaz", lambda *a, **kw: (flood_fix(), []))
    gh, st = SahteGH(), bos_state()
    st["gun"]["2026-10-15"] = {"slotlar": ["t6"], "birim": 0, "ig": 0, "metinler": []}  # trend slotu zaten işlenmiş
    flood.uret(oto, st, SIMDI.replace(hour=11), object(), gh, yaz=lambda *_: None)
    b = st["birimler"][0]
    assert b["durum"] == "planli" and b["tur"] == "library" and b["yayin_zamani"].startswith("2026-10-15T17:00")
    assert gh.acilan == []  # evergreen otomatik: onay issue'su yok
    st["gun"]["2026-10-16"] = {"slotlar": ["t6"], "birim": 0, "ig": 0, "metinler": []}
    flood.uret(oto, st, SIMDI.replace(day=16, hour=11), object(), gh, yaz=lambda *_: None)
    assert gorulen[0] != gorulen[1] and gorulen[0] == flood_yazar.KUTUPHANE[0]  # ertesi gün başka tema


def test_uctan_uca_onay_modunda_evergreen_de_onay_ister(monkeypatch):
    k = kayit_fix()["denendi"]
    kayit_lib = {"tur": "library", "konu": "tema", "olgular": [], "kaynaklar": [], "arac": None, "denendi": dict(k)}
    monkeypatch.setattr(flood_dogrula, "kutuphane_kaydi", lambda *a, **kw: kayit_lib)
    monkeypatch.setattr(flood_yazar, "yaz", lambda *a, **kw: (flood_fix(), []))
    gh, st = SahteGH(), bos_state()
    st["gun"]["2026-10-15"] = {"slotlar": ["t6"], "birim": 0, "ig": 0, "metinler": []}
    flood.uret(AYAR, st, SIMDI.replace(hour=11), object(), gh, yaz=lambda *_: None)  # AYAR.mod == "onay"
    assert st["birimler"][0]["durum"] == "onay_bekliyor" and len(gh.acilan) == 1
