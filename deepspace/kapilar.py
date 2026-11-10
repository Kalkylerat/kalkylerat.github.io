"""Kapılar: her istasyonun çıkışındaki kod kontrolleri (SOZLESME.md G). Biri kalırsa video "hazır" sayılmaz.

Her kontrol {ad, gecti, ayrinti} döner. rapor() hepsini cikti/rapor.json'a yazar. Denetçi ajan bu raporu okur;
rapor kırmızıysa ajanın "bitti" demesi geçersizdir.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

from .ortak import calistir, cikti, ffprobe_sure, kayit_yukle, seri


def _k(ad: str, gecti: bool, ayrinti: str = "") -> dict:
    return {"ad": ad, "gecti": bool(gecti), "ayrinti": ayrinti}


# ---------- G4: özgünlük ----------
def ozgunluk(gorev: dict, kayit: dict, ses_ozetleri: list[str] | None = None) -> list[dict]:
    eski = [g for g in kayit.get("gorevler", []) if g.get("no") != gorev["no"]]
    sonuc = []
    tohumlar = {g.get("tohum") for g in eski}
    sonuc.append(_k("tohum yeni", gorev["tohum"] not in tohumlar, f"tohum {gorev['tohum']}"))
    hedefler = {g.get("hedef", "").lower() for g in eski}
    sonuc.append(_k("hedef gök cismi yeni", gorev["hedef"].lower() not in hedefler, gorev["hedef"]))
    adlar = [p["ad"] for p in gorev["parca"]]
    sonuc.append(_k("görev içinde parça adı tekrarı yok", len(adlar) == len(set(adlar)),
                    ", ".join(a for a in set(adlar) if adlar.count(a) > 1)))
    if ses_ozetleri is not None:
        eski_ses = {h for g in eski for h in g.get("ses_ozetleri", [])}
        tekrar = [h[:10] for h in ses_ozetleri if h in eski_ses]
        sonuc.append(_k("ses daha önce yüklenmemiş", not tekrar and len(set(ses_ozetleri)) == len(ses_ozetleri),
                        ", ".join(tekrar)))
    return sonuc


# ---------- G2/G5: görev dosyası ve Suno istemleri ----------
ZORUNLU_ALANLAR = ("ad", "kisa", "dosya", "tur", "palet", "bilgi", "hedef_sure", "anahtar", "bpm", "style", "exclude",
                   "lyrics")


def gorev_dosyasi(gorev: dict, ayar: dict) -> list[dict]:
    from .ortak import sure_oku
    from .sahne import TURLER
    sonuc = []
    eksik = [f"{i + 1}:{a}" for i, p in enumerate(gorev["parca"]) for a in ZORUNLU_ALANLAR if not p.get(a)]
    sonuc.append(_k("parçalarda zorunlu alanlar dolu", not eksik, ", ".join(eksik[:8])))
    turler = [p.get("tur") for p in gorev["parca"] if p.get("tur") not in TURLER]
    sonuc.append(_k("gezegen türleri tanınıyor", not turler, ", ".join(map(str, turler))))
    sr = seri(gorev, ayar)
    sonuc.append(_k("parça sayısı seriye uygun", len(gorev["parca"]) == sr["parca_sayisi"],
                    f"{len(gorev['parca'])} / {sr['parca_sayisi']}"))
    a = ayar["ses"]
    sureler = [sure_oku(p["hedef_sure"]) for p in gorev["parca"] if p.get("hedef_sure")]
    kotu = [p["ad"] for p, s in zip(gorev["parca"], sureler) if not a["parca_min_sn"] <= s <= a["parca_max_sn"]]
    sonuc.append(_k("hedef parça süreleri sınırda", not kotu, ", ".join(kotu)))
    toplam = sum(sureler) - a["capraz_gecis_sn"] * (len(sureler) - 1)
    hedef = sr["hedef_dakika"] * 60
    sonuc.append(_k("hedef toplam süre", abs(toplam - hedef) <= hedef * a["sure_tolerans"], f"{toplam / 60:.1f} dk"))
    dosyalar = [p.get("dosya") for p in gorev["parca"]]
    sonuc.append(_k("dosya adları benzersiz", len(dosyalar) == len(set(dosyalar))))
    istem = " ".join(" ".join(str(p.get(k, "")) for k in ("style", "exclude", "lyrics", "ad", "kisa", "bilgi"))
                     for p in gorev["parca"]).lower() + " " + gorev.get("ozet", "").lower()
    yasak = [k for k in ayar["metin"]["yasak_kelimeler"] if re.search(rf"\b{re.escape(k)}\b", istem)]
    sonuc.append(_k("istemlerde ve bilgilerde yasak kelime yok", not yasak, ", ".join(yasak)))
    vokal = [p["ad"] for p in gorev["parca"] if "instrumental" not in p.get("style", "").lower()
             or "vocals" not in p.get("exclude", "").lower()]
    sonuc.append(_k("her istem enstrümantal ve vokal yasaklı", not vokal, ", ".join(vokal)))
    return sonuc


# ---------- G2/G3: ses ----------
def ses(bolumler: dict, ayar: dict, hedef_dakika: float) -> list[dict]:
    a = ayar["ses"]
    sonuc = []
    for p in bolumler["parcalar"]:
        o = p["olcum"]
        sonuc.append(_k(f"parça {p['no']:02d} süresi", a["parca_min_sn"] <= o["sure"] <= a["parca_max_sn"],
                        f"{o['sure']:.0f} sn"))
        ic = [s for s in o["sessiz"] if s[0] > 15 and s[1] < o["sure"] - 15]
        sonuc.append(_k(f"parça {p['no']:02d} ortasında boşluk yok", not ic,
                        "; ".join(f"{s[0]:.0f}-{s[1]:.0f} sn" for s in ic)))
    hedef = hedef_dakika * 60
    toplam = bolumler["toplam_sn"]
    sonuc.append(_k("toplam süre hedefte", abs(toplam - hedef) <= hedef * a["sure_tolerans"],
                    f"{toplam / 60:.1f} dk (hedef {hedef_dakika} dk)"))
    m = bolumler["master"]
    sonuc.append(_k("master ses yüksekliği", m["lufs"] is not None and abs(m["lufs"] - a["hedef_lufs"]) <=
                    a["lufs_tolerans"], f"{m['lufs']} LUFS (hedef {a['hedef_lufs']})"))
    sonuc.append(_k("master tepe", m["tepe_dbtp"] is not None and m["tepe_dbtp"] <= a["tepe_dbtp"] + 0.5,
                    f"{m['tepe_dbtp']} dBTP (sınır {a['tepe_dbtp']})"))
    return sonuc


# ---------- G5: metin ----------
def metin(yt: dict, ayar: dict, bolumler: dict) -> list[dict]:
    mt = ayar["metin"]
    sonuc = [_k("başlık uzunluğu", 0 < len(yt["baslik"]) <= mt["baslik_max"], f"{len(yt['baslik'])} karakter"),
             _k("açıklama uzunluğu", len(yt["aciklama"]) <= mt["aciklama_max"], f"{len(yt['aciklama'])} karakter"),
             _k("etiket toplamı", sum(len(e) + 1 for e in yt["etiketler"]) <= mt["etiket_max_karakter"])]
    tum = " ".join([yt["baslik"], yt["aciklama"], " ".join(yt["etiketler"]), yt.get("sabit_yorum", "")]).lower()
    yasak = [k for k in mt["yasak_kelimeler"] if re.search(rf"\b{re.escape(k)}\b", tum)]
    sonuc.append(_k("yasak kelime yok (sanatçı/film adı)", not yasak, ", ".join(yasak)))
    sonuc.append(_k("sentetik içerik etiketi açık", yt.get("sentetik_icerik") is True))
    satirlar = [s for s in yt["aciklama"].splitlines() if re.match(r"^\d+:\d{2}(:\d{2})? ", s)]
    zamanlar = []
    for s in satirlar:
        parca = [int(x) for x in s.split(" ")[0].split(":")]
        zamanlar.append(parca[0] * 3600 + parca[1] * 60 + parca[2] if len(parca) == 3 else parca[0] * 60 + parca[1])
    bolum_ok = (len(zamanlar) >= 3 and zamanlar[0] == 0 and
                all(b - a >= 10 for a, b in zip(zamanlar, zamanlar[1:])) and
                len(zamanlar) == len(bolumler["parcalar"]))
    sonuc.append(_k("bölümler YouTube kuralına uygun", bolum_ok, f"{len(zamanlar)} bölüm"))
    return sonuc


# ---------- G7: kapak ----------
def kapak(yollar: list[Path], yazilar: list[str], ayar: dict) -> list[dict]:
    kelime = sum(len(y.split()) for y in yazilar)
    sonuc = [_k("kapak en fazla 3 kelime", kelime <= ayar["metin"]["kapak_max_kelime"], f"{kelime} kelime"),
             _k("3 kapak varyantı", len(yollar) == 3, f"{len(yollar)} adet")]
    for y in yollar:
        with Image.open(y) as im:
            ok = im.size == (1280, 720) and Path(y).stat().st_size < 2 * 1024 * 1024
        sonuc.append(_k(f"{Path(y).name} 1280x720 ve <2MB", ok))
    return sonuc


# ---------- G6: video ----------
def _akislar(dosya: Path) -> dict:
    s = calistir(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json",
                  str(dosya)])
    return json.loads(s.stdout)


def video(dosya: Path, bolumler: dict, ayar: dict, siyah_kontrol: bool = True) -> list[dict]:
    v = ayar["video"]
    sonuc = []
    if not dosya.exists():
        return [_k("video dosyası var", False, str(dosya))]
    sure = ffprobe_sure(dosya)
    sonuc.append(_k("video süresi = ses süresi", abs(sure - bolumler["toplam_sn"]) <= 1.0,
                    f"{sure:.1f} / {bolumler['toplam_sn']:.1f} sn"))
    ak = _akislar(dosya)["streams"]
    vid = [s for s in ak if s["codec_type"] == "video"]
    sonuc.append(_k("çözünürlük", bool(vid) and (vid[0]["width"], vid[0]["height"]) == (v["genislik"], v["yukseklik"]),
                    f"{vid[0]['width']}x{vid[0]['height']}" if vid else "video akışı yok"))
    sonuc.append(_k("ses akışı var", any(s["codec_type"] == "audio" for s in ak)))
    if siyah_kontrol:
        s = calistir(["ffmpeg", "-hide_banner", "-nostats", "-i", str(dosya), "-vf",
                      "fps=2,scale=320:-2,blackdetect=d=2:pix_th=0.02", "-an", "-f", "null", "-"])
        siyah = re.findall(r"black_start:([\d.]+)", s.stderr)
        sonuc.append(_k("siyah ekran yok", not siyah, ", ".join(siyah[:5])))
    return sonuc


def shorts(yollar: list[Path], ayar: dict) -> list[dict]:
    sonuc = [_k("Shorts adedi", len(yollar) == ayar["shorts"]["adet"], f"{len(yollar)}")]
    for y in yollar:
        ak = _akislar(y)["streams"]
        vid = [s for s in ak if s["codec_type"] == "video"]
        ok = bool(vid) and (vid[0]["width"], vid[0]["height"]) == (1080, 1920) and ffprobe_sure(y) <= 60
        sonuc.append(_k(f"{Path(y).name} dikey ve ≤60 sn", ok and any(s["codec_type"] == "audio" for s in ak)))
    return sonuc


# ---------- G13: görsel denetimi ----------
def gorseller(gorev: dict) -> list[dict]:
    """Görseli olan her parça teknik ölçümü ve göz denetimini geçmeli. Görseli olmayan parça kod sahnesine düşer (G6)."""
    from .gorsel_denetim import gorev_gorselleri
    return [_k(f"görsel {g['no']:02d} denetimi", not g["sorunlar"], "; ".join(g["sorunlar"]))
            for g in gorev_gorselleri(gorev) if g["yol"]]


def rapor(gorev: dict, ayar: dict, siyah_kontrol: bool = True) -> dict:
    from .kapak import kapak_yazilari
    out = cikti(gorev)
    kontroller = gorev_dosyasi(gorev, ayar) + ozgunluk(gorev, kayit_yukle(), gorev.get("_ses_ozetleri"))
    kontroller += gorseller(gorev)
    bolumler_yol = out / "bolumler.json"
    if bolumler_yol.exists():
        bolumler = json.loads(bolumler_yol.read_text(encoding="utf-8"))
        kontroller += ses(bolumler, ayar, seri(gorev, ayar)["hedef_dakika"])
        if (out / "youtube.json").exists():
            kontroller += metin(json.loads((out / "youtube.json").read_text(encoding="utf-8")), ayar, bolumler)
        else:
            kontroller.append(_k("youtube.json var", False))
        kapaklar = sorted(out.glob("kapak_*.jpg"))
        saat = round(bolumler["toplam_sn"] / 3600)
        kontroller += kapak(kapaklar, kapak_yazilari(gorev, ayar, saat), ayar)
        kontroller += video(out / "video.mp4", bolumler, ayar, siyah_kontrol)
        kontroller += shorts(sorted(out.glob("short_?.mp4")), ayar)
    else:
        kontroller.append(_k("bolumler.json var (ses istasyonu çalıştı)", False))
    sonuc = {"gorev": gorev["no"], "gecti": all(k["gecti"] for k in kontroller), "kontroller": kontroller}
    (out / "rapor.json").write_text(json.dumps(sonuc, indent=2, ensure_ascii=False), encoding="utf-8")
    return sonuc
