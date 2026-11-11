"""Shorts departmanı (G12): müzik analizi, kurgucu planının kontrolü, dikey üretim ve metin.

Akış: `analiz` her parçanın saniyelik enerji eğrisini ve önerilen anı `cikti/shorts_analiz.json`'a yazar; kurgucu ajan
bu analize ve görsellere bakarak `shorts_plan.json`'u yazar; plan kod kapısından geçmeden Short üretilmez.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

from .kapilar import SES_ESIGI_DB, _k
from .ortak import cikti, kayit_yukle, seri

SR = 8000  # enerji eğrisi için yeterli (yalnız seviye ölçülür)


def enerji_egrisi(ses: Path, basla: float, sure: float) -> np.ndarray:
    """Sesin [basla, basla + sure) aralığında saniye başına RMS seviyesi (dBFS)."""
    ham = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{basla:.3f}", "-t", f"{sure:.3f}", "-i", str(ses),
                          "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(ham, np.float32)
    n = int(round(sure))
    x = np.pad(x, (0, max(0, n * SR - len(x))))[:n * SR].reshape(n, SR).astype(np.float64)
    return 20 * np.log10(np.sqrt((x * x).mean(axis=1)) + 1e-9)


def en_iyi_aralik(egri: np.ndarray, uzunluk: int, kenar: int = 12) -> int:
    """Ortalama enerjisi en yüksek, içinde sessiz (< G14 eşiği) saniye olmayan pencerenin başlangıç saniyesi.

    Parçanın ilk ve son `kenar` saniyesi (fade ve çapraz geçiş) dışarıda kalır. Uygun pencere yoksa -1."""
    e = np.asarray(egri, np.float64)
    son = len(e) - kenar - uzunluk  # son geçerli başlangıç
    if uzunluk <= 0 or son < kenar:
        return -1
    toplam = np.concatenate([[0.0], np.cumsum(e)])
    sessiz = np.concatenate([[0], np.cumsum(e < SES_ESIGI_DB)])
    bas = np.arange(kenar, son + 1)
    ort = (toplam[bas + uzunluk] - toplam[bas]) / uzunluk
    ort[(sessiz[bas + uzunluk] - sessiz[bas]) > 0] = -np.inf
    if not np.isfinite(ort).any():
        return -1
    return int(bas[np.argmax(ort)])


def analiz(gorev: dict, ayar: dict) -> Path:
    """Her parçanın enerji eğrisi ve önerilen Short anı (mutlak saniye, master zaman çizelgesinde)."""
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    ses = out / "ses.m4a"
    uzunluk = int(ayar["shorts"]["sure_sn"])
    sonuc = []
    for p in bolumler["parcalar"]:
        egri = enerji_egrisi(ses, p["basla"], p["sure"])
        bas = en_iyi_aralik(egri, uzunluk)
        sonuc.append({"parca": p["no"], "ad": p["ad"], "basla": p["basla"], "sure": p["sure"],
                      "egri": [round(float(v), 1) for v in egri],
                      "oneri_basla": round(p["basla"] + bas, 2) if bas >= 0 else None})
    yol = out / "shorts_analiz.json"
    yol.write_text(json.dumps(sonuc, ensure_ascii=False) + "\n", encoding="utf-8")
    return yol


# ---------- plan (kurgucu ajan yazar, kod denetler) ----------
PLAN_DOSYASI = "shorts_plan.json"
SHORTS_NOTU = ("Music generated with AI music tools (Suno), then hand-selected and mastered. "
               "Scenes are AI-generated images; the light motion and mission log are rendered with code.")


def plan_kontrol(plan: list, gorev: dict, bolumler: dict, kayit: dict, ayar: dict) -> list[dict]:
    """G12 plan kapısı: adet, ayrı parçalar, süre, aralık (çapraz geçiş hariç), kırpma, kanca (≤3 kelime, G5) ve
    başka görevde kullanılmış anla örtüşme (ses özeti + parça içi saniye)."""
    sh, mt = ayar["shorts"], ayar["metin"]
    if not isinstance(plan, list):
        return [_k("shorts planı bir liste", False)]
    satirlar = [x if isinstance(x, dict) else {} for x in plan]
    parcalar = [x.get("parca") for x in satirlar]
    sonuc = [_k(f"Short adedi {sh['adet']}", len(plan) == sh["adet"], f"{len(plan)} adet"),
             _k("her Short ayrı parçadan", len(set(map(str, parcalar))) == len(parcalar), str(parcalar))]
    n = len(bolumler["parcalar"])
    ozetler = gorev.get("_ses_ozetleri") or []
    hizali = len(ozetler) == n
    sonuc.append(_k("ses özetleri parçalarla hizalı", hizali, f"{len(ozetler)}/{n}"))
    capraz = bolumler["capraz_gecis_sn"]
    onceki = [(a.get("ses_ozeti"), float(a.get("parca_ici_sn", 0)), float(a.get("sure_sn", 0)))
              for g in kayit.get("gorevler", []) if g.get("no") != gorev.get("no") for a in g.get("shorts", [])]
    for k, x in enumerate(satirlar, 1):
        ad = f"Short {k}"
        try:
            parca, bas, sure = int(x["parca"]), float(x["basla_sn"]), float(x["sure_sn"])
            kirp, kanca = float(x["kirp_x"]), str(x["kanca"]).strip()
            if not 1 <= parca <= n:
                raise ValueError(f"parça {parca} yok (1–{n})")
        except (KeyError, TypeError, ValueError) as e:
            sonuc.append(_k(f"{ad}: plan satırı okunur", False, str(e)))
            continue
        bp = bolumler["parcalar"][parca - 1]
        alt, ust = bp["basla"] + capraz, bp["basla"] + bp["sure"] - capraz
        kelime = len(kanca.split())
        yasak = [w for w in mt["yasak_kelimeler"] if re.search(rf"\b{re.escape(w)}\b", kanca.lower())]
        sonuc += [
            _k(f"{ad}: süre {sh['min_sn']}–{sh['max_sn']} sn", sh["min_sn"] <= sure <= sh["max_sn"], f"{sure:g} sn"),
            _k(f"{ad}: aralık parçanın içinde (çapraz geçiş hariç)", alt <= bas and bas + sure <= ust,
               f"{bas:.1f}–{bas + sure:.1f}, izin {alt:.1f}–{ust:.1f}"),
            _k(f"{ad}: kirp_x 0–1", 0 <= kirp <= 1, f"{kirp:g}"),
            _k(f"{ad}: kanca 1–{sh['kanca_max_kelime']} kelime", 1 <= kelime <= sh["kanca_max_kelime"], kanca),
            _k(f"{ad}: kancada yasak kelime yok (G5)", not yasak, ", ".join(yasak)),
        ]
        if hizali:
            goreli = bas - bp["basla"]
            cakisan = [f"{g:.0f}–{g + d:.0f} sn" for oz, g, d in onceki
                       if oz == ozetler[parca - 1] and goreli < g + d and g < goreli + sure]
            sonuc.append(_k(f"{ad}: an başka görevde kullanılmamış", not cakisan, ", ".join(cakisan)))
    return sonuc


def plan_yukle(gorev: dict, ayar: dict, bolumler: dict) -> tuple[list[dict], bool]:
    """(plan, dosyadan_mi). Görev 002'den itibaren plan zorunlu; 001 için parçalara yayılan orta anlar kullanılır."""
    from .video import shorts_secimi
    yol = Path(gorev["klasor"]) / PLAN_DOSYASI
    if yol.exists():
        try:
            return json.loads(yol.read_text(encoding="utf-8")), True
        except ValueError as e:
            raise SystemExit(f"{PLAN_DOSYASI} bozuk: {e}")
    if gorev["no"] >= ayar["is_bolumu"]["kilit_baslangic"]:
        raise SystemExit(f"{PLAN_DOSYASI} yok: görev 002'den itibaren anları Shorts kurgucusu seçer (G12)")
    sure = float(ayar["shorts"]["sure_sn"])
    plan = []
    for i in shorts_secimi(len(gorev["parca"]), ayar["shorts"]["adet"]):
        bp = bolumler["parcalar"][i]
        plan.append({"parca": i + 1, "basla_sn": round(max(0.0, bp["basla"] + bp["sure"] / 2 - sure / 2), 2),
                     "sure_sn": sure, "kirp_x": 0.5, "kanca": ""})
    return plan, False


def _hazirla(gorev: dict) -> dict:
    if gorev.get("_ses_ozetleri") is None:
        from . import ses
        gorev = dict(gorev, _ses_ozetleri=ses.ozetler(gorev))
    return gorev


# ---------- üretim ----------
def uret(gorev: dict, ayar: dict) -> list[Path]:
    """Plan kapısı yeşilse her Short: dikey Seyir Defteri (görsel kirp_x odağında, kanca), master sesin aynı
    aralığı (1.5 sn içe, 2.5 sn dışa geçiş, loudnorm). Ardından `shorts.json` metinleri yazılır."""
    from . import defter, video
    from .ornek import _loudnorm
    from .renk import marka_filtresi
    v = ayar["video"]
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    plan, dosyadan = plan_yukle(gorev, ayar, bolumler)
    if dosyadan:
        kirmizi = [f"{k['ad']} {k['ayrinti']}".strip()
                   for k in plan_kontrol(plan, _hazirla(gorev), bolumler, kayit_yukle(), ayar) if not k["gecti"]]
        if kirmizi:
            raise SystemExit("shorts planı kırmızı: " + "; ".join(kirmizi))
    ses_yol = out / "ses.m4a"
    fps, saat = v["fps"], round(bolumler["toplam_sn"] / 3600)
    eksik = [f"{int(x['parca']):02d}" for x in plan if not video.parca_gorseli(gorev, int(x["parca"]) - 1)[0]]
    if eksik:
        raise ValueError(f"Shorts görseli olmayan parça: {', '.join(eksik)}")
    yollar = []
    for k, x in enumerate(plan, 1):
        i = int(x["parca"]) - 1
        gorsel = video.parca_gorseli(gorev, i)[0]
        bas, sure = float(x["basla_sn"]), float(x["sure_sn"])
        sahne = defter.SeyirDefteri(gorsel, defter.katmanlari_oku(gorsel), 1080, 1920, fps, sure,
                                    defter.ses_ozeti(ses_yol, fps, basla=bas, sure=sure),
                                    {**video.parca_bilgisi(gorev, i), "saat": saat}, tohum=video._tohum(gorev, i) + 7,
                                    ton=marka_filtresi(), t0=bas, kirp_x=float(x["kirp_x"]), kanca=x.get("kanca", ""))
        hedef = out / f"short_{k}.mp4"
        defter.kodla(sahne, ses_yol, hedef, _loudnorm(ses_yol, sure, basla=bas, giris=1.5, cikis=2.5),
                     crf=v["crf"], preset=v["preset"], ses_basla=bas)
        yollar.append(hedef)
    metin(gorev, ayar, plan)
    return yollar


def metin(gorev: dict, ayar: dict, plan: list[dict]) -> list[dict]:
    """Short başına başlık ve açıklama (G5, G9). {UZUN_VIDEO} yüklemede uzun videonun bağlantısıyla değişir."""
    out = cikti(gorev)
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    saat = round(bolumler["toplam_sn"] / 3600)
    sr, kanal = seri(gorev, ayar), ayar["kanal"]["ad"]
    sonuc = []
    for x in plan:
        p = gorev["parca"][int(x["parca"]) - 1]
        kanca = (x.get("kanca") or "").strip()
        govde = f"{kanca} · {p['ad']}" if kanca else p["ad"]
        son = f" | {kanal} #Shorts"
        baslik = govde[:ayar["metin"]["baslik_max"] - len(son)].rstrip() + son
        aciklama = "\n".join([
            f"A moment from Mission {gorev['no']:03d} · {gorev['hedef']}: {p['ad']}.",
            *([p["bilgi"]] if p.get("bilgi") else []),
            "",
            f"Full {saat}-hour mission: {{UZUN_VIDEO}}",
            "",
            SHORTS_NOTU,
            "",
            " ".join(["#Shorts", *sr["hashtagler"]]),
        ])
        etiketler, toplam = [], 0
        for e in [*sr["etiketler"][:6], "shorts", kanal]:
            if toplam + len(e) + 1 > ayar["metin"]["etiket_max_karakter"]:
                break
            etiketler.append(e)
            toplam += len(e) + 1
        sonuc.append({"baslik": baslik, "aciklama": aciklama, "etiketler": etiketler, "kategori": "10",
                      "dil": ayar["kanal"]["dil"], "sentetik_icerik": True})
    (out / "shorts.json").write_text(json.dumps(sonuc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sonuc


def istasyon_kapilari(gorev: dict, ayar: dict) -> list[dict]:
    """Shorts istasyonunun kod kapıları (denetçi kararından önce): plan, dosyalar, metinler."""
    from . import kapilar
    out = cikti(gorev)
    if not (out / "bolumler.json").exists():
        return [_k("bolumler.json var (ses istasyonu çalıştı)", False)]
    bolumler = json.loads((out / "bolumler.json").read_text(encoding="utf-8"))
    try:
        plan = json.loads((Path(gorev["klasor"]) / PLAN_DOSYASI).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [_k(f"{PLAN_DOSYASI} var ve okunur", False)]
    sonuc = plan_kontrol(plan, _hazirla(gorev), bolumler, kayit_yukle(), ayar)
    sonuc += kapilar.shorts(sorted(out.glob("short_?.mp4")), ayar)
    try:
        metinler = json.loads((out / "shorts.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return sonuc + [_k("shorts.json var ve okunur", False)]
    for m in metinler:
        sonuc += kapilar.metin_temel(m, ayar)
    return sonuc
