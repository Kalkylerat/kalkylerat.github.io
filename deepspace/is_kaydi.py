"""İş kaydı ve denetim kilidi (G15, G16).

Görevin işleri sıralı istasyonlardır. Her istasyonun denetçi kararı `<görev>/denetim/istasyon_<ad>.json` dosyasına,
çıktı dosyalarının sha256 özetleriyle yazılır. Bir istasyonun komutu, kendinden önceki her istasyon GEÇTİ olmadan
ve çıktıları karardan sonra değişmeden çalışmaz (gorev.py çıkış 3). Marka istasyonu kanal düzeyindedir: kaydı
`deepspace/marka/istasyon_marka.json`'dadır ve ayrıca sahibinin bir kerelik onayını ister (G16).

- Metin dosyalarının özeti satır sonundan bağımsızdır (Windows CRLF ile Linux LF aynı özeti verir).
- `gorev.toml`'daki görsel üretim alanları (`GORSEL_ALANLARI`) konsept özetine girmez, görsel istasyonuna aittir:
  görsel yeniden üretimi konsept kararını bozmaz.
- Her kayıt kendinden önceki istasyonların o anki özetlerini (`zincir`) taşır: önceki bir istasyonun çıktısı
  değişirse (yeniden onaylansa bile) sonraki kararlar geçersizdir.
- `tur` aynı denetim döngüsündeki sıradır: GEÇTİ'den sonraki ilk karar yeniden 1'den başlar.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .ortak import KOK, ayar_yukle, cikti

MARKA_KLASORU = KOK / "marka"
MARKA_DOSYASI = KOK / "marka.toml"
MARKA_KAYDI = "istasyon_marka.json"

ISTASYONLAR = ["marka", "arastirma", "konsept", "bilgi", "ses", "gorsel", "hareket", "video", "shorts", "paket",
               "karar"]
CIKTILAR: dict[str, list[str]] = {
    "arastirma": ["buyume/oneriler.json", "buyume/arastirma.md"],
    "konsept": ["gorev.toml", "SUNO.md"],
    "bilgi": ["bilgi_kaynak.json"],
    "ses": ["cikti/bolumler.json", "cikti/ses.m4a"],
    "gorsel": ["gorsel/[0-9][0-9].png", "denetim/[0-9][0-9].json"],
    "hareket": ["gorsel/*_hareket.json"],
    "video": ["cikti/video.mp4"],
    "shorts": ["shorts_plan.json", "cikti/short_?.mp4", "cikti/shorts.json"],
    "paket": ["cikti/kapak_?.jpg", "cikti/youtube.json", "cikti/aciklama.txt"],
    "karar": ["cikti/onay.json"],
}
KARARLAR = ("GECTI", "KALDI")
METIN_UZANTI = {".toml", ".json", ".jsonl", ".md", ".txt", ".cube"}
COP_DOSYALAR = {"thumbs.db", "desktop.ini", ".ds_store"}
GORSEL_ALANLARI = ("gorsel_akisi", "gorsel_istem", "gorsel_oturum", "gorsel_uretim")
_SHA_ONBELLEK: dict[tuple, str] = {}


class KilitHatasi(Exception):
    pass


def _sha(yol: Path) -> str:
    """Dosya özeti; metin dosyalarında CRLF -> LF. (yol, boyut, mtime) önbellekli: büyük video bir kez okunur."""
    st = yol.stat()
    anahtar = (str(Path(yol).resolve()), st.st_size, st.st_mtime_ns)
    if anahtar in _SHA_ONBELLEK:
        return _SHA_ONBELLEK[anahtar]
    h = hashlib.sha256()
    if yol.suffix.lower() in METIN_UZANTI:
        h.update(yol.read_bytes().replace(b"\r\n", b"\n"))
    else:
        with open(yol, "rb") as f:
            for blok in iter(lambda: f.read(1 << 20), b""):
                h.update(blok)
    _SHA_ONBELLEK[anahtar] = h.hexdigest()
    return _SHA_ONBELLEK[anahtar]


def _gorsel_satiri(satir: str) -> bool:
    return satir.split("=", 1)[0].strip() in GORSEL_ALANLARI if "=" in satir else False


def _gorev_toml_ozeti(yol: Path, gorsel: bool) -> str:
    """gorsel=False: görsel üretim alanları çıkarılmış konsept özeti; True: yalnız o alanların özeti."""
    satirlar = yol.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    secilen = [s for s in satirlar if _gorsel_satiri(s) == gorsel]
    return hashlib.sha256("\n".join(secilen).encode("utf-8")).hexdigest()


def _cop_mu(p: Path) -> bool:
    return p.name.lower() in COP_DOSYALAR


def _marka_dosyalari() -> list[Path]:
    dosyalar = [MARKA_DOSYASI] if MARKA_DOSYASI.exists() else []
    if MARKA_KLASORU.exists():
        dosyalar += sorted(p for p in MARKA_KLASORU.rglob("*")
                           if p.is_file() and p.name != MARKA_KAYDI and not _cop_mu(p)
                           and "taslak" not in p.relative_to(MARKA_KLASORU).parts)
    return dosyalar


def marka_ozeti() -> str:
    h = hashlib.sha256()
    for p in _marka_dosyalari():
        h.update(p.name.encode("utf-8"))
        h.update(_sha(p).encode("ascii"))
    return h.hexdigest()


def ozetler(klasor: Path | None, istasyon: str) -> dict[str, str]:
    if istasyon == "marka":
        taban = MARKA_KLASORU.parent
        return {(p.relative_to(taban).as_posix() if p.is_relative_to(taban) else p.name): _sha(p)
                for p in _marka_dosyalari()}
    klasor = Path(klasor)
    sonuc = {}
    for kalip in CIKTILAR.get(istasyon, []):
        for p in sorted(klasor.glob(kalip)):
            if not p.is_file() or _cop_mu(p):
                continue
            ad = p.relative_to(klasor).as_posix()
            sonuc[ad] = _gorev_toml_ozeti(p, gorsel=False) if ad == "gorev.toml" else _sha(p)
    if istasyon == "gorsel" and sonuc and (klasor / "gorev.toml").exists():
        sonuc["gorev.toml#gorsel"] = _gorev_toml_ozeti(klasor / "gorev.toml", gorsel=True)
    return sonuc


def zincir(klasor: Path | None, istasyon: str) -> dict[str, dict[str, str]]:
    """Kendinden önceki görev istasyonlarının şu anki çıktı özetleri (marka ayrıca marka_ozeti ile izlenir)."""
    if istasyon == "marka":
        return {}
    return {o: ozetler(klasor, o) for o in ISTASYONLAR[1:ISTASYONLAR.index(istasyon)]}


def kayit_yolu(klasor: Path | None, istasyon: str) -> Path:
    if istasyon == "marka":
        return MARKA_KLASORU / MARKA_KAYDI
    return Path(klasor) / "denetim" / f"istasyon_{istasyon}.json"


def kayit_oku(klasor: Path | None, istasyon: str) -> dict | None:
    yol = kayit_yolu(klasor, istasyon)
    try:
        d = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and d.get("karar") in KARARLAR else None


def _yaz(yol: Path, d: dict) -> Path:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return yol


def _simdi() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def kayit_yaz(klasor: Path | None, istasyon: str, karar: str, denetci: str, bulgular: list[dict],
              kirmizi: list[str]) -> Path:
    if istasyon not in ISTASYONLAR:
        raise KilitHatasi(f"bilinmeyen istasyon: {istasyon}")
    if karar not in KARARLAR:
        raise KilitHatasi(f"karar GECTI ya da KALDI olmalı: {karar}")
    oz = ozetler(klasor, istasyon)
    if karar == "GECTI" and kirmizi:
        raise KilitHatasi("kod kapısı kırmızıyken GEÇTİ yazılamaz: " + "; ".join(kirmizi))
    if karar == "GECTI" and not oz:
        raise KilitHatasi(f"{istasyon}: çıktı dosyası yok, GEÇTİ yazılamaz")
    onceki = kayit_oku(klasor, istasyon)
    tur = onceki["tur"] + 1 if onceki and onceki["karar"] == "KALDI" and isinstance(onceki.get("tur"), int) else 1
    d = {"istasyon": istasyon, "karar": karar, "tur": tur, "denetci": denetci,
         "ozetler": oz, "zincir": zincir(klasor, istasyon), "marka_ozeti": marka_ozeti(), "kirmizi": list(kirmizi),
         "bulgular": [{"kod": b.get("kod", ""), "not": b.get("not", ""), "kanit": b.get("kanit", "")}
                      for b in bulgular], "zaman": _simdi()}
    return _yaz(kayit_yolu(klasor, istasyon), d)


def sahip_onayi_yaz(kim: str) -> Path:
    d = kayit_oku(None, "marka")
    if not d or d["karar"] != "GECTI":
        raise KilitHatasi("marka kiti denetçiden geçmeden sahibin onayı yazılamaz")
    if d["ozetler"] != ozetler(None, "marka"):
        raise KilitHatasi("marka kiti denetimden sonra değişmiş; önce yeniden denetlenmeli")
    d["sahip_onayi"] = {"kim": kim, "zaman": _simdi(), "marka_ozeti": marka_ozeti()}
    return _yaz(kayit_yolu(None, "marka"), d)


def gecerli_mi(klasor: Path | None, istasyon: str) -> tuple[bool, str]:
    k = kayit_oku(klasor, istasyon)
    if not k:
        return False, "denetim kaydı yok"
    if k["karar"] != "GECTI":
        return False, f"karar {k['karar']} (tur {k.get('tur')})"
    if k.get("ozetler") != ozetler(klasor, istasyon):
        return False, "çıktılar karardan sonra değişti"
    if istasyon != "marka":
        eski, simdi = k.get("zincir"), zincir(klasor, istasyon)
        if not isinstance(eski, dict):
            return False, "kayıtta zincir yok; yeniden denetlenmeli"
        degisen = [o for o in simdi if eski.get(o) != simdi[o]]
        if degisen:
            return False, f"önceki istasyon karardan sonra değişti: {', '.join(degisen)}"
    if istasyon == "marka":
        so = k.get("sahip_onayi") or {}
        if so.get("marka_ozeti") != marka_ozeti():
            return False, "sahibin onayı yok (G16)"
    elif k.get("marka_ozeti") != marka_ozeti():
        return False, "marka kiti karardan sonra değişti (G16)"
    return True, "geçerli"


def _klasor(istasyon: str, klasor: Path | None) -> Path | None:
    return None if istasyon == "marka" else klasor


def kilit(klasor: Path, istasyon: str, gorev_no: int) -> tuple[bool, str]:
    if gorev_no < ayar_yukle()["is_bolumu"]["kilit_baslangic"]:
        return True, "kilit dışı"
    for onceki in ISTASYONLAR[:ISTASYONLAR.index(istasyon)]:
        ok, neden = gecerli_mi(_klasor(onceki, klasor), onceki)
        if not ok:
            return False, f"{onceki}: {neden}"
    return True, "açık"


def durum(klasor: Path) -> dict:
    en_cok = ayar_yukle()["is_bolumu"]["en_cok_tur"]
    satirlar, siradaki = [], None
    for ad in ISTASYONLAR:
        k = kayit_oku(_klasor(ad, klasor), ad) or {}
        ok, neden = gecerli_mi(_klasor(ad, klasor), ad)
        if not ok and siradaki is None:
            siradaki = ad
        satirlar.append({"ad": ad, "karar": k.get("karar"), "tur": k.get("tur", 0), "gecerli": ok, "neden": neden,
                         "sefte": k.get("karar") == "KALDI" and k.get("tur", 0) >= en_cok})
    return {"istasyonlar": satirlar, "siradaki": siradaki}


def kapi_kontrolleri(gorev: dict, ayar: dict, istasyon: str) -> list[dict]:
    """Denetçi kararından önce çalışan kod kapıları. Kırmızıysa GEÇTİ yazılamaz."""
    from . import kapilar
    from .ortak import seri
    out = cikti(gorev)
    bolumler = None
    if (out / "bolumler.json").exists():
        bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    eksik = [kapilar._k("bolumler.json var (ses istasyonu çalıştı)", False)]
    if istasyon == "konsept":
        return kapilar.gorev_dosyasi(gorev, ayar)
    if istasyon == "ses":
        return kapilar.ses(bolumler, ayar, seri(gorev, ayar)["hedef_dakika"]) if bolumler else eksik
    if istasyon == "gorsel":
        return kapilar.gorseller(gorev)
    if istasyon == "hareket":
        return kapilar.hareket(gorev)
    if istasyon == "video":
        return kapilar.video(out / "video.mp4", bolumler, ayar) if bolumler else eksik
    if istasyon == "shorts":
        from . import shorts
        return shorts.istasyon_kapilari(gorev, ayar)
    if istasyon == "paket":
        if not bolumler:
            return eksik
        from .kapak import kapak_yazilari
        saat = round(bolumler["toplam_sn"] / 3600)
        k = kapilar.kapak(sorted(out.glob("kapak_*.jpg")), kapak_yazilari(gorev, ayar, saat), ayar)
        yt = out / "youtube.json"
        k += kapilar.metin(json.loads(yt.read_text(encoding="utf-8")), ayar, bolumler) if yt.exists() \
            else [kapilar._k("youtube.json var", False)]
        return k
    return []
