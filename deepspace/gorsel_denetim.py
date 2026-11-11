"""Görsel denetimi (SOZLESME.md G13): yapay zekâ görsellerindeki saçmalıkları ve teknik kusurları yakalar.

İki katman:
1. Teknik ölçüm (bu dosya, ücretsiz): çözünürlük, 16:9 oran, pozlama (yanık/ezik), netlik, aynı görselin tekrarı.
2. Göz denetimi (denetçi ajan, `denetim/NN.json`): ajan görsele KONTROL_LISTESI ile bakar ve puan verir.
   Yapay zekâ görsellerinin tipik saçmalıkları burada yakalanır (fazla parmak, iki kafa, havada duran nesne...).
Kapı: ikisi de geçmeden görsel videoya girmez. Kalan görselin istemine bulunan kusurun tersi açıkça yazılır
("a single fisherman", "exactly six wheels") ve yeniden üretilir (en fazla YENIDEN_DENEME kez, tek varyasyon);
yine kalırsa istem sadeleştirilir ya da parça kod sahnesine düşer, olay kayda geçer.
Göz denetimi görselin dosya özetine bağlıdır: görsel değişirse eski denetim geçersizdir.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

SURUM = 1
GECME_PUANI = 7
YENIDEN_DENEME = 2

# Göz denetiminin sorduğu sorular. "kritik" olanlardan biri bile varsa puan ne olursa olsun görsel kalır.
KONTROL_LISTESI = [
    {"kod": "anatomi", "kritik": True,
     "soru": "İnsan/hayvan varsa: fazla ya da eksik kol, bacak, parmak, iki kafa, erimiş yüz, ters dönmüş eklem var mı?"},
    {"kod": "yazi", "kritik": True,
     "soru": "Görselde okunur ya da yarım yazı, logo, filigran, imza, arayüz öğesi var mı?"},
    {"kod": "fizik", "kritik": True,
     "soru": "Havada asılı duran ev/araç/insan, yere gömülmüş ya da ikiye bölünmüş nesne, imkânsız birleşme var mı? "
             "(Gökyüzündeki dev gök cismi konseptin parçasıdır, saçmalık sayılmaz.)"},
    {"kod": "tekrar", "kritik": False,
     "soru": "İstenmeyen kopya var mı: aynı figürden iki tane, istemde yokken iki güneş, kopyala-yapıştır gibi tekrar eden desen?"},
    {"kod": "olcek", "kritik": False,
     "soru": "Ölçek ve perspektif tutarlı mı: ufuk çizgisi düz, insan/araç boyutu çevreyle uyumlu, gölgeler makul yönde?"},
    {"kod": "bozulma", "kritik": False,
     "soru": "Erimiş doku, bulanık yama, dikiş izi, aşırı keskinleşme, plastik görünüm gibi bozulma var mı?"},
    {"kod": "istem", "kritik": True,
     "soru": "İstemin üç ana öğesi var mı: Dünya'ya benzeyen manzara, gökyüzünde dev gök cismi, küçük insan izi/hikâye unsuru?"},
    {"kod": "marka", "kritik": False,
     "soru": "Sakin ve sinematik mi? Neon pembe, mor gradyan, aşırı parlama, çizgi film görünümü yok mu?"},
]


# Simsiyah alan sınırı (G13, 11 Kasım 2026): konsept karanlık uzay manzarasıdır; derin siyah gökyüzü doğaldır.
# Yalnız neredeyse tamamen boş (siyah) kare kalır.
EZIK_SINIR = 0.75


def teknik_olcum(yol: Path) -> dict:
    with Image.open(yol) as im:
        w, h = im.size
        x = np.asarray(im.convert("L").resize((min(w, 1024), int(min(w, 1024) * h / w))), np.float32) / 255
    lap = np.abs(4 * x[1:-1, 1:-1] - x[:-2, 1:-1] - x[2:, 1:-1] - x[1:-1, :-2] - x[1:-1, 2:])
    return {"genislik": w, "yukseklik": h, "oran": round(w / h, 4), "ort_parlaklik": round(float(x.mean()), 3),
            "yanik": round(float((x > 0.98).mean()), 4), "ezik": round(float((x < 0.02).mean()), 4),
            "netlik": round(float(lap.var() * 1e4), 2)}


def parmak_izi(yol: Path) -> int:
    """Algısal özet (dHash 64 bit): neredeyse aynı görselleri yakalar."""
    with Image.open(yol) as im:
        x = np.asarray(im.convert("L").resize((9, 8), Image.BILINEAR), np.int16)
    bitler = (x[:, 1:] > x[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bitler), 2)


def benzerlik_farki(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def teknik_sorunlar(o: dict) -> list[str]:
    s = []
    if o["genislik"] < 2560:
        s.append(f"çözünürlük düşük ({o['genislik']} px; en az 2560)")
    if abs(o["oran"] - 16 / 9) > 0.04:
        s.append(f"oran 16:9 değil ({o['oran']})")
    if not 0.05 <= o["ort_parlaklik"] <= 0.8:
        s.append(f"pozlama aşırı ({o['ort_parlaklik']})")
    if o["yanik"] > 0.08:
        s.append(f"yanık alan fazla (%{o['yanik'] * 100:.0f})")
    if o["ezik"] > EZIK_SINIR:
        s.append(f"simsiyah alan fazla (%{o['ezik'] * 100:.0f})")
    if o["netlik"] < 1.0:
        s.append(f"görsel bulanık (netlik {o['netlik']})")
    return s


def dosya_ozeti(yol: Path) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def denetim_yolu(yol: Path) -> Path:
    """Karar depoda kalır (gorsel/ depoya girmez): <görev>/denetim/NN.json. Görselin özetine bağlıdır."""
    return Path(yol).parent.parent / "denetim" / f"{Path(yol).stem}.json"


def goz_denetimi_oku(yol: Path) -> dict | None:
    dj = denetim_yolu(yol)
    return json.loads(dj.read_text(encoding="utf-8")) if dj.exists() else None


def goz_denetimi_gecti(d: dict | None, yol: Path | None = None) -> tuple[bool, str]:
    if d is None:
        return False, "göz denetimi yapılmamış (denetim/NN.json yok)"
    if d.get("kontrol_listesi_surumu") != SURUM:
        return False, "eski kontrol listesiyle denetlenmiş"
    if yol is not None and d.get("ozet") != dosya_ozeti(yol):
        return False, "görsel denetimden sonra değişmiş (yeniden denetle)"
    kritik = {k["kod"] for k in KONTROL_LISTESI if k["kritik"]}
    bulunan = [s for s in d.get("sorunlar", []) if s.get("kod") in kritik]
    if bulunan:
        return False, "kritik: " + "; ".join(f"{s['kod']}: {s.get('not', '')}" for s in bulunan)
    if d.get("puan", 0) < GECME_PUANI:
        return False, f"puan {d.get('puan')} < {GECME_PUANI}"
    return True, f"puan {d.get('puan')}"


def goz_denetimi_yaz(yol: Path, puan: int, sorunlar: list[dict], denetleyen: str = "denetci") -> Path:
    """Denetçi ajanın kararı. sorunlar: [{"kod": KONTROL_LISTESI kodu, "not": "..."}]."""
    kodlar = {k["kod"] for k in KONTROL_LISTESI}
    for s in sorunlar:
        if s.get("kod") not in kodlar:
            raise ValueError(f"bilinmeyen kontrol kodu: {s.get('kod')}")
    if not 0 <= int(puan) <= 10:
        raise ValueError("puan 0-10 arası olmalı")
    d = {"kontrol_listesi_surumu": SURUM, "denetleyen": denetleyen, "ozet": dosya_ozeti(yol), "puan": int(puan),
         "sorunlar": sorunlar}
    d["gecti"] = goz_denetimi_gecti(d)[0]
    hedef = denetim_yolu(yol)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return hedef


def gorev_gorselleri(gorev: dict) -> list[dict]:
    """Her parçanın görseli için {no, yol, teknik, sorunlar, goz} (görsel olmayan parça 'yok' döner)."""
    from .video import parca_gorseli
    sonuc, izler = [], []
    for i, _ in enumerate(gorev["parca"]):
        ana, _on = parca_gorseli(gorev, i)
        if not ana:
            sonuc.append({"no": i + 1, "yol": None, "sorunlar": ["görsel yok"]})
            continue
        o = teknik_olcum(ana)
        sor = teknik_sorunlar(o)
        iz = parmak_izi(ana)
        for no, onceki in izler:
            if benzerlik_farki(iz, onceki) <= 4:
                sor.append(f"parça {no:02d} görseliyle neredeyse aynı")
        izler.append((i + 1, iz))
        gecti, neden = goz_denetimi_gecti(goz_denetimi_oku(ana), ana)
        if not gecti:
            sor.append(neden)
        sonuc.append({"no": i + 1, "yol": str(ana), "teknik": o, "sorunlar": sor})
    return sonuc


def paftalar(yol: Path, hedef: Path, sutun: int = 3, satir: int = 2) -> list[Path]:
    """Göz denetimi için görseli tam çözünürlükte parçalara böler (küçük önizlemede fazla parmak görünmez)."""
    hedef.mkdir(parents=True, exist_ok=True)
    out = []
    with Image.open(yol) as im:
        w, h = im.size
        for j in range(satir):
            for i in range(sutun):
                p = hedef / f"{Path(yol).stem}_pafta_{j * sutun + i + 1}.jpg"
                im.convert("RGB").crop((i * w // sutun, j * h // satir, (i + 1) * w // sutun,
                                        (j + 1) * h // satir)).save(p, quality=90)
                out.append(p)
    return out
