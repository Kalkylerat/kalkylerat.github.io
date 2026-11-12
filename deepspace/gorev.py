"""Deep Space Log komut satırı. Bir görev = bir video. Kullanım:

    python -m deepspace.gorev istemler deepspace/gorevler/001-trappist   # sahibine Suno istem dosyası (SUNO.md)
    python -m deepspace.gorev gorseller deepspace/gorevler/001-trappist  # görsel istem listesi (GORSEL.md)
    python -m deepspace.gorev hepsi    deepspace/gorevler/001-trappist   # ses -> sahne -> video -> kapak -> metin -> shorts -> kontrol
    python -m deepspace.gorev kontrol  deepspace/gorevler/001-trappist   # yalnızca kapılar (rapor.json)
    python -m deepspace.gorev kaydet   deepspace/gorevler/001-trappist   # sahibin "ok"undan sonra: kayit.json'a işle
    python -m deepspace.gorev kanal                                      # banner ve profil resmi
    python -m deepspace.gorev denetle  <klasör>                          # görsel denetimi durumu (G13)
    python -m deepspace.gorev denetle  <klasör> --parca 2                # paftaları çıkar (denetçi bakar)
    python -m deepspace.gorev denetle  <klasör> --parca 2 --puan 8 [--sorun "tekrar:iki balıkçı"]  # karar

Google (deepspace/KURULUM.md):
    python -m deepspace.gorev al      <klasör> --drive DeepSpaceLog/001  # Drive'dan ses/ ve gorsel/ dosyaları
    python -m deepspace.gorev teslim  <klasör> --drive DeepSpaceLog/001  # bitmiş paketi Drive'a (cikti alt klasörü)
    python -m deepspace.gorev onay    <klasör> --yayin 2026-11-20T17:00:00Z  # denetçinin kararı (G8), en az 24 sa sonra
    python -m deepspace.gorev iptal   <klasör> [--neden ...]           # sahibinin acil freni (G8)
    python -m deepspace.gorev yukle   <klasör>                           # YouTube'a gizli/planlı yükleme

Tek tek istasyonlar: ses, sahneler, video, kapak, metin, shorts.

İş bölümü ve denetim kilidi (G15, G16; görev 002'den itibaren):
    python -m deepspace.gorev durum   <klasör>                           # istasyonlar, kararlar, sıradaki iş
    python -m deepspace.gorev kilit   <klasör> --istasyon video          # çıkış 0 açık, 3 kilitli
    python -m deepspace.gorev denetim <klasör> --istasyon X --karar GECTI|KALDI [--bulgu "kod:not"] [--kanit yol]
    python -m deepspace.gorev denetim --istasyon marka --karar GECTI     # kanal düzeyinde marka kiti
    python -m deepspace.gorev marka --onay --kim sahip                   # sahibinin bir kerelik kit onayı
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

from . import is_kaydi, kapak, kapilar, metin, ses, video
from .ortak import KAYIT_DOSYASI, ayar_yukle, cikti, gorev_yukle, kayit_yukle, sure_oku


def istemler(gorev: dict, ayar: dict) -> Path:
    """Sahibinin Suno'ya kopyalayacağı istemler. Her parça için Style, Exclude, Lyrics ayrı kod bloğunda."""
    kirmizi = [k for k in kapilar.gorev_dosyasi(gorev, ayar) if not k["gecti"]]
    if kirmizi:
        raise SystemExit("görev dosyası kapıdan geçmedi: " + "; ".join(f"{k['ad']} {k['ayrinti']}" for k in kirmizi))
    satir = [f"# Mission {gorev['no']:03d} · {gorev['hedef']}: Suno istemleri", "",
             "Her parça için: Suno'da **Custom** modu aç, aşağıdaki üç bloğu ilgili kutulara yapıştır, **Create**.",
             "Beğendiğin varyasyonu indir ve **dosya adını tam olarak** aşağıdaki gibi koy (uzantı .mp3 ya da .wav "
             "olabilir), `ses/` klasörüne at.",
             "Parça hedef süreden kısa çıkarsa son 30 saniyesinden **Extend** ile tamamla. Vokal gelirse "
             "**Instrumental**'ı açıp yeniden üret.", ""]
    if gorev.get("ses_paleti"):
        satir += ["Bölüm ses paleti (bütün parçalar bu enstrümanlardan seçer, mix'te tek ses gibi akar): "
                  + ", ".join(gorev["ses_paleti"]) + ".", ""]
    toplam = 0.0
    for i, p in enumerate(gorev["parca"], 1):
        toplam += sure_oku(p["hedef_sure"])
        satir += [f"## {i:02d}. {p['ad']} · {p['hedef_sure']} · {p['anahtar']} · {p['bpm']} BPM", "",
                  f"Dosya adı: `{p['dosya']}`", ""]
        if p.get("motif"):
            satir += [f"Motif: {p['motif']}", ""]
        for baslik, alan in (("Style", "style"), ("Exclude", "exclude"), ("Lyrics", "lyrics")):
            satir += [f"**{baslik}**", "```", p[alan].strip(), "```", ""]
    net = toplam - ayar["ses"]["capraz_gecis_sn"] * (len(gorev["parca"]) - 1)
    satir += [f"Toplam hedef: {len(gorev['parca'])} parça, ~{net / 60:.0f} dk (çapraz geçişler düşülmüş).", ""]
    yol = Path(gorev["klasor"]) / "SUNO.md"
    yol.write_text("\n".join(satir), encoding="utf-8")
    return yol


def kadraj(parca: dict) -> str:
    """Parçanın sahne kadrajı (G6): `kadraj` alanı, yoksa `tur`dan (yildiz → derin, gaz → yorunge, diğer → ufuk)."""
    if parca.get("kadraj"):
        return parca["kadraj"]
    return {"yildiz": "derin", "gaz": "yorunge"}.get(parca.get("tur", ""), "ufuk")


def gorsel_istemleri(gorev: dict) -> Path:
    """Görsel üretim listesi (GORSEL.md): her parça için sahne + kadraj eki + ortak stil tabanı; hazır olanlar işaretli."""
    from .ortak import marka_yukle
    g = marka_yukle()["gorsel"]
    # 12 Kasım 2026: tek uzun ek derin uzay karesine gezegen çağırıyordu; kısa taban + kadraja göre ek.
    satir = [f"# Mission {gorev['no']:03d} · {gorev['hedef']}: görsel istemleri", "",
             f"Model: `{g['model']}` (16:9). Her görsel `gorsel/NN.png` olarak kaydedilir (NN = parça no).",
             "Renk tonu marka filtresinden gelir (marka.toml [filtre]); istemdeki ışık tarifi yeterli.", ""]
    for i, p in enumerate(gorev["parca"], 1):
        durum = f"üretildi: `{p['gorsel_uretim']}`" if p.get("gorsel_uretim") else "üretilecek"
        k = kadraj(p)
        tam = f"{p['gorsel_istem']} {g['kadraj_eki'][k]} {g['stil_eki']}"
        satir += [f"## {i:02d}. {p['ad']} · {k} · {durum}", "", "```", tam, "```", ""]
    yol = Path(gorev["klasor"]) / "GORSEL.md"
    yol.write_text("\n".join(satir), encoding="utf-8")
    return yol


def ses_ozetleri(gorev: dict) -> list[str]:
    return ses.ozetler(gorev)


def _shorts_anlari(gorev: dict, ozetler: list[str]) -> list[dict]:
    """Kullanılan Shorts anları (G12: başka görevde tekrar etmez). Parça içi göreli saniye ve ses özetiyle."""
    from . import shorts
    yol = cikti(gorev) / "bolumler.json"
    if not yol.exists():
        return []
    bolumler = json.loads(yol.read_text(encoding="utf-8"))
    try:
        plan, _ = shorts.plan_yukle(gorev, ayar_yukle(), bolumler)
    except SystemExit:
        return []
    if len(ozetler) != len(gorev["parca"]):
        print("UYARI: ses dosyaları eksik; Shorts anları kayda yazılamadı")
        return []
    return [{"ses_ozeti": ozetler[int(x["parca"]) - 1],
             "parca_ici_sn": round(float(x["basla_sn"]) - bolumler["parcalar"][int(x["parca"]) - 1]["basla"], 2),
             "sure_sn": float(x["sure_sn"])} for x in plan]


def kaydet(gorev: dict, youtube_id: str | None) -> dict:
    kayit = kayit_yukle()
    kayit["gorevler"] = [g for g in kayit["gorevler"] if g.get("no") != gorev["no"]]
    ozetler = ses_ozetleri(gorev)
    giris = {
        "no": gorev["no"], "seri": gorev["seri"], "hedef": gorev["hedef"], "tohum": gorev["tohum"],
        "tarih": date.today().isoformat(), "youtube_id": youtube_id,
        "parcalar": [p["ad"] for p in gorev["parca"]], "ses_ozetleri": ozetler,
    }
    anlar = _shorts_anlari(gorev, ozetler)
    if anlar:
        giris["shorts"] = anlar
    kayit["gorevler"].append(giris)
    kayit["gorevler"].sort(key=lambda g: g["no"])
    KAYIT_DOSYASI.write_text(json.dumps(kayit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return kayit


# Komut -> çalışması için kendinden önceki her istasyonun GEÇTİ olması gereken istasyon (G15).
KOMUT_ISTASYONU = {"istemler": "konsept", "ses": "ses", "sahneler": "video", "video": "video", "shorts": "shorts",
                   "shorts-analiz": "shorts", "kapak": "paket", "metin": "paket", "onay": "karar", "yukle": "karar"}


def durum_yaz(klasor: Path) -> None:
    d = is_kaydi.durum(klasor)
    for s in d["istasyonlar"]:
        isaret = "+" if s["gecerli"] else "-"
        sef = "  << ŞEFTE (3 tur)" if s["sefte"] else ""
        print(f"{isaret} {s['ad']:<10} {s['karar'] or '-':<6} tur {s['tur']}  {s['neden']}{sef}")
    print(f"sıradaki: {d['siradaki'] or 'yok (hepsi geçerli)'}")


def denetim(gorev: dict | None, ayar: dict | None, a) -> int:
    """Denetçinin kararı. Önce kod kapıları çalışır; kırmızı varken GEÇTİ yazılamaz (G15)."""
    bulgular = [{"kod": k.strip(), "not": n.strip(), "kanit": a.kanit or ""}
                for k, _, n in (b.partition(":") for b in a.bulgu)]
    kirmizi = [] if gorev is None else [f"{k['ad']} {k['ayrinti']}".strip()
                                        for k in is_kaydi.kapi_kontrolleri(gorev, ayar, a.istasyon) if not k["gecti"]]
    klasor = None if gorev is None else Path(gorev["klasor"])
    try:
        yol = is_kaydi.kayit_yaz(klasor, a.istasyon, a.karar, a.kim or "denetci", bulgular, kirmizi)
    except is_kaydi.KilitHatasi as e:
        print(f"KİLİTLİ: {e}")
        return 3
    for k in kirmizi:
        print(f"  kırmızı kapı: {k}")
    print(yol)
    return 0


def _adim(ad: str, is_):
    bas = time.time()
    print(f"→ {ad} ...", flush=True)
    sonuc = is_()
    print(f"  {ad} bitti ({time.time() - bas:.0f} sn)", flush=True)
    return sonuc


def _kirmizi_mi(kontroller: list[dict]) -> list[dict]:
    return [k for k in kontroller if not k["gecti"]]


def _google(a, gorev: dict) -> int:
    from . import google
    out = cikti(gorev)
    if a.komut == "son-denetim":  # G18: yalnız son-denetci (Fable) yazar
        if not a.karar:
            raise SystemExit("--karar GECTI|KALDI gerekli")
        print(google.son_denetim_yaz(out, a.karar, a.puan, a.bulgu))
        if a.karar == "GECTI":  # G19: Fable onayından sonra bölüm arşivi
            from . import arsiv
            try:
                print(f"arşiv: {arsiv.arsivle(gorev)}")
            except arsiv.ArsivHatasi as e:
                print(f"UYARI: {e}")
        return 0
    if a.komut == "onay":
        if not a.yayin:
            raise SystemExit("--yayin gerekli (planlı yayın saati, en az 24 saat sonra)")
        print(google.onay_yaz(out, a.kim or "denetci", a.yayin))
        return 0
    if a.komut == "iptal":
        print(google.iptal_yaz(out, a.neden or ""))
        yuk = out / "yukleme.json"
        if yuk.exists():
            google.youtube_planli_yayini_geri_al(json.loads(yuk.read_text(encoding="utf-8"))["video_id"])
            print("YouTube'daki planlı yayın geri alındı (video gizli kaldı)")
        syuk = out / "shorts_yukleme.json"
        if syuk.exists():  # G8: iptal Shorts'un planlı yayınını da geri alır
            for s in json.loads(syuk.read_text(encoding="utf-8")):
                google.youtube_planli_yayini_geri_al(s["id"])
                print(f"Short planlı yayını geri alındı (gizli): {s['id']}")
        return 0
    if a.komut == "yukle":
        if (out / "yukleme.json").exists():  # yeniden çalıştırmada uzun video ikinci kez yüklenmez
            print("uzun video zaten yüklü (yukleme.json); yalnız Shorts denenir")
        else:
            sonuc = google.youtube_yukle(out)
            print(f"yüklendi (gizli): https://youtu.be/{sonuc['id']}  {sonuc.get('kapak_hatasi', '')}")
        if (out / "shorts.json").exists():  # yarıda kalan Shorts yüklemesi kaldığı yerden sürer
            for s in google.shorts_yukle(out):
                print(f"Short (gizli, {s['publishAt']}): https://youtu.be/{s['id']}")
        return 0
    if not a.drive:
        raise SystemExit("--drive klasör yolu gerekli")
    tok = google.erisim_belirteci()
    if a.komut == "al":
        kok = google.klasor_yolu(a.drive, tok)
        istenen = {p["dosya"] for p in gorev["parca"]}
        (Path(gorev["klasor"]) / "ses").mkdir(exist_ok=True)
        for d in google.drive_listele(kok, tok):
            if d["name"] in istenen:
                print("ses:", google.drive_indir(d["id"], Path(gorev["klasor"]) / "ses" / d["name"], tok))
        gorsel_id = google.klasor_bul("gorsel", tok, kok)
        if gorsel_id:
            (Path(gorev["klasor"]) / "gorsel").mkdir(exist_ok=True)
            for d in google.drive_listele(gorsel_id, tok):
                print("görsel:", google.drive_indir(d["id"], Path(gorev["klasor"]) / "gorsel" / d["name"], tok))
        eksik = sorted(istenen - {p.name for p in (Path(gorev["klasor"]) / "ses").glob("*")})
        print("eksik ses:", ", ".join(eksik) if eksik else "yok")
        return 0 if not eksik else 1
    hedef = google.klasor_yolu(a.drive.rstrip("/") + "/cikti", tok, olustur=True)
    for ad, mime in (("video.mp4", "video/mp4"), ("kapak_1.jpg", "image/jpeg"), ("kapak_2.jpg", "image/jpeg"),
                     ("kapak_3.jpg", "image/jpeg"), ("short_1.mp4", "video/mp4"), ("short_2.mp4", "video/mp4"),
                     ("short_3.mp4", "video/mp4"), ("aciklama.txt", "text/plain"), ("youtube.json", "application/json"),
                     ("rapor.json", "application/json")):
        if (out / ad).exists():
            print("teslim:", ad, google.drive_yukle(out / ad, hedef, tok, mime))
    return 0


def denetle(gorev: dict, a) -> int:
    """G13 görsel denetimi: durum, pafta çıkarma ya da denetçinin kararını yazma."""
    from . import gorsel_denetim as gd
    if a.parca is None:
        durum = gd.gorev_gorselleri(gorev)
        for g in durum:
            print(f"{g['no']:02d} {'GEÇTİ' if not g['sorunlar'] else 'KALDI'}  {'; '.join(g['sorunlar'])}")
        return 0 if all(not g["sorunlar"] for g in durum if g["yol"]) else 2
    ana, _ = video.parca_gorseli(gorev, a.parca - 1)
    if not ana:
        print(f"parça {a.parca:02d}: görsel yok")
        return 2
    if a.puan is None:
        print("Kontrol listesi:")
        for k in gd.KONTROL_LISTESI:
            print(f"  [{k['kod']}{' *kritik' if k['kritik'] else ''}] {k['soru']}")
        print("İstem:", gorev["parca"][a.parca - 1].get("gorsel_istem", ""))
        print("Teknik:", gd.teknik_sorunlar(gd.teknik_olcum(ana)) or "sorun yok")
        for p in gd.paftalar(ana, cikti(gorev) / "pafta"):
            print(p)
        return 0
    sorunlar = [{"kod": s.split(":", 1)[0].strip(), "not": s.split(":", 1)[1].strip() if ":" in s else ""}
                for s in a.sorun]
    hedef = gd.goz_denetimi_yaz(ana, a.puan, sorunlar, a.kim or "denetci")
    gecti, neden = gd.goz_denetimi_gecti(gd.goz_denetimi_oku(ana), ana)
    print(f"{hedef}: {'GEÇTİ' if gecti else 'KALDI'} ({neden})")
    return 0 if gecti else 2


def main(argv: list[str] | None = None) -> int:
    for akis in (sys.stdout, sys.stderr):  # Windows konsolu cp1252: Türkçe çıktı çökmesin
        if hasattr(akis, "reconfigure"):
            akis.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="deepspace.gorev")
    ap.add_argument("komut", choices=["istemler", "ses", "sahneler", "video", "kapak", "metin", "shorts", "kontrol",
                                      "hepsi", "kaydet", "kanal", "al", "teslim", "onay", "iptal", "yukle",
                                      "gorseller", "denetle", "ornek", "durum", "kilit", "denetim", "marka",
                                      "shorts-analiz", "son-denetim", "arsiv"])
    ap.add_argument("--drive", help="Drive klasör yolu, ör. DeepSpaceLog/001")
    ap.add_argument("--kim", help="karar veren (varsayılan: denetci)")
    ap.add_argument("--neden", help="iptal nedeni")
    ap.add_argument("--yayin", help="planlı yayın zamanı, RFC3339 UTC")
    ap.add_argument("klasor", nargs="?")
    ap.add_argument("--youtube-id")
    ap.add_argument("--parca", type=int, help="denetle: parça numarası (1'den)")
    ap.add_argument("--puan", type=int, help="denetle: göz denetimi puanı 0-10")
    ap.add_argument("--sorun", action="append", default=[], help="denetle: kod:not (tekrarlanabilir)")
    ap.add_argument("--ses", help="ornek: ses dosyası (wav/mp3)")
    ap.add_argument("--boyut", default="1920x1080", help="ornek: GENxYUK (varsayılan 1920x1080)")
    ap.add_argument("--mod", default="defter", choices=["defter", "sinemagraf"], help="ornek: sahne modu")
    ap.add_argument("--istasyon", choices=is_kaydi.ISTASYONLAR, help="kilit/denetim: istasyon adı")
    ap.add_argument("--karar", choices=["GECTI", "KALDI"], help="denetim: denetçinin kararı")
    ap.add_argument("--bulgu", action="append", default=[], help="denetim: kod:not (tekrarlanabilir)")
    ap.add_argument("--kanit", help="denetim: kanıt dosyası yolu")
    ap.add_argument("--onay", action="store_true", help="marka: sahibinin bir kerelik kit onayı (G16)")
    ap.add_argument("--siyah-kontrolu-yok", action="store_true", help="hızlı deneme için siyah ekran taramasını atla")
    a = ap.parse_args(argv)

    if a.komut == "kanal":
        for y in kapak.kanal_gorselleri(ayar_yukle()):
            print(y)
        return 0
    if a.komut == "marka":
        if not a.onay:
            ap.error("marka: --onay gerekli")
        try:
            print(is_kaydi.sahip_onayi_yaz(a.kim or "sahip"))
        except is_kaydi.KilitHatasi as e:
            print(f"KİLİTLİ: {e}")
            return 3
        return 0
    if a.komut in ("kilit", "denetim") and not a.istasyon:
        ap.error(f"{a.komut}: --istasyon gerekli")
    if a.komut == "denetim" and not a.karar:
        ap.error("denetim: --karar gerekli")
    if a.komut == "denetim" and a.istasyon == "marka":
        return denetim(None, None, a)
    if not a.klasor:
        ap.error("görev klasörü gerekli")
    gorev, ayar = gorev_yukle(Path(a.klasor))
    klasor = Path(gorev["klasor"])

    if a.komut == "durum":
        durum_yaz(klasor)
        return 0
    if a.komut == "kilit":
        ok, neden = is_kaydi.kilit(klasor, a.istasyon, gorev["no"])
        print(f"{a.istasyon}: {'AÇIK' if ok else 'KİLİTLİ'} ({neden})")
        return 0 if ok else 3
    if a.komut == "denetim":
        return denetim(gorev, ayar, a)
    if a.komut in KOMUT_ISTASYONU:
        ist = KOMUT_ISTASYONU[a.komut]
        ok, neden = is_kaydi.kilit(klasor, ist, gorev["no"])
        if ok and a.komut == "yukle" and gorev["no"] >= ayar["is_bolumu"]["kilit_baslangic"]:
            ok, neden = is_kaydi.gecerli_mi(klasor, "karar")
            neden = f"karar: {neden}"
        if not ok:
            print(f"KİLİTLİ ({ist}): {neden}")
            return 3
    if a.komut == "hepsi" and gorev["no"] >= ayar["is_bolumu"]["kilit_baslangic"]:
        print("KİLİTLİ: görev 002'den itibaren istasyonlar sırayla, denetimle çalıştırılır (G15). `gorev durum` bak.")
        return 3

    if a.komut == "istemler":
        print(istemler(gorev, ayar))
        return 0
    if a.komut == "gorseller":
        print(gorsel_istemleri(gorev))
        return 0
    if a.komut == "arsiv":  # G19
        from . import arsiv
        try:
            print(arsiv.arsivle(gorev))
        except arsiv.ArsivHatasi as e:
            print(f"HATA: {e}")
            return 2
        return 0
    if a.komut == "denetle":
        return denetle(gorev, a)
    if a.komut == "ornek":  # G14: tek parçalık referans video, sesi ölçülmüş
        from .ornek import ornek
        if a.parca is None or not a.ses:
            ap.error("ornek: --parca N ve --ses DOSYA gerekli")
        W, H = (int(x) for x in a.boyut.lower().split("x"))
        print(ornek(gorev, ayar, a.parca, Path(a.ses), W, H, mod=a.mod))
        return 0
    if a.komut in ("al", "teslim", "onay", "iptal", "yukle", "son-denetim"):
        return _google(a, gorev)
    if a.komut == "shorts-analiz":  # G12: kurgucu ajanın okuyacağı enerji eğrileri ve önerilen anlar
        from . import shorts
        print(shorts.analiz(gorev, ayar))
        return 0
    if a.komut == "kaydet":
        kaydet(gorev, a.youtube_id)
        print(f"kayit.json güncellendi: görev {gorev['no']}")
        return 0

    gorev["_ses_ozetleri"] = ses_ozetleri(gorev)
    on = kapilar.ozgunluk(gorev, kayit_yukle(), gorev["_ses_ozetleri"])
    if _kirmizi_mi(on) and a.komut in ("ses", "hepsi"):
        for k in _kirmizi_mi(on):
            print(f"KAPI KAPALI: {k['ad']} {k['ayrinti']}")
        return 2

    adimlar = {
        "ses": lambda: ses.birlestir(gorev, ayar),
        "sahneler": lambda: video.sahneler(gorev, ayar),
        "video": lambda: video.uzun_video(gorev, ayar),
        "kapak": lambda: kapak.kapaklar(gorev, ayar),
        "metin": lambda: metin.uret(gorev, ayar),
        "shorts": lambda: video.shorts(gorev, ayar),
    }
    if a.komut == "shorts" and not ayar["shorts"].get("acik", True):
        print("Shorts kapalı (G12: ilk 5 uzun videodan sonra açılır, ayar.toml [shorts] acik)")
        return 0
    if a.komut in adimlar:
        _adim(a.komut, adimlar[a.komut])
    elif a.komut == "hepsi":
        bolumler = _adim("ses", adimlar["ses"])
        ses_k = kapilar.ses(bolumler, ayar, ayar["seri"][gorev["seri"]]["hedef_dakika"])
        if _kirmizi_mi(ses_k):
            for k in _kirmizi_mi(ses_k):
                print(f"KAPI KAPALI (ses): {k['ad']} {k['ayrinti']}")
            return 2
        for ad in ("sahneler", "video", "kapak", "metin", "shorts"):
            if ad == "shorts" and not ayar["shorts"].get("acik", True):
                continue
            _adim(ad, adimlar[ad])

    r = kapilar.rapor(gorev, ayar, siyah_kontrol=not a.siyah_kontrolu_yok)
    kirmizi = _kirmizi_mi(r["kontroller"])
    print(f"\nRapor: {cikti(gorev) / 'rapor.json'}  ·  {len(r['kontroller'])} kontrol, {len(kirmizi)} kırmızı")
    for k in kirmizi:
        print(f"  ✗ {k['ad']}  {k['ayrinti']}")
    return 0 if r["gecti"] else 1


if __name__ == "__main__":
    sys.exit(main())
