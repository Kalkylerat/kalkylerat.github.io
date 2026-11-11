"""Seyir Defteri modu: PROBE-7'nin gözünden canlı görev kaydı (sahibinin seçtiği A yönü, 10 Kasım 2026).

Görüntü hiç bükülmez (SOZLESME G14). Hareket yalnızca resmin ÜSTÜNE eklenen katmanlardır, böylece fizikle çelişmez:
  isik     sahnedeki gerçek ışık kaynağı: lamba/LED yanıp söner (yanip_son), hale nefes alır (yavas) ya da müzikle
           hafifçe parlar (muzik). {merkez, yaricap, renk, guc, nabiz, periyot}
  toz      ışıkta süzülen ince toz: yavaş yatay sürüklenme, derinliğe göre boy/parlaklık. {kutu, adet, renk, hiz}
  goktasi  seyrek, soluk göktaşı çizgisi. {kutu, aralik: [min, max] sn, parlaklik}
  yildiz   karanlık gökte pırıltı (yalnız parlaklığı düşük piksellerde). {kutu, adet, esik}
  isaret_lambasi  istasyon/uydu işaret lambası: isik + yanip_son (varsayılan kırmızı, 2 sn). {merkez, renk, periyot}
  pencereler      istasyon pencereleri: her ışık ortalama 20 sn'de bir yanar/söner, 1 sn'de yumuşak geçer. {kutu, adet}
  kutup_isigi     kutup ışığı: görüntünün kendi parlaklığıyla çarpılan, yatay dalgalı ekleyici nabız. {kutu, periyot}
  halka_piriltisi halkadaki buz parçacıkları: yalnız parlak piksellerde (lum > 0.35) yanıp sönen noktalar. {kutu, adet}
  bulutsu_tulu    bulutsunun tülü: düşük frekanslı parlaklık dalgası, yavaşça kayar (piksel taşımaz). {kutu, guc, hiz}
  uydu            yolda süzülen soluk nokta, seyrek geçiş. {yol: [[x0, y0], [x1, y1]], sure, aralik, parlaklik}
Her katman `muzik: true` alabilir: gücü 0.7 + 0.6·zarf ile çarpılır. Kutulu katmanlar kutu dışındaki piksele dokunmaz.
Marka kaydı (HUD): sol üst kanal ve görev, sağ üst görev saati, sol alt satır satır yazılan kayıt (gerçek bilgi
`gorev.toml`'dan), sağ alt müziğin spektrumundan "sinyal" çizgisi. Tarif: `gorsel/NN_hareket.json` içinde "katmanlar".
Dikey (Shorts, H > W): görsel `kirp_x` odağında kırpılır; üstte marka + görev, y ≈ 0.28·H'de kanca, altta (y > 0.8·H)
"Full N-hour mission" ve tam genişlikte sinyal; kayıt kartı yok. Katman koordinatları 16:9 karede yazılır ve dikey
kadraja resimle birlikte taşınır.
"""
from __future__ import annotations

import json
import math
import subprocess
import textwrap
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .ortak import marka_yukle, rgb

FONT = Path(__file__).resolve().parent / "font"
TAU = 2 * math.pi
# Yazı boyları 1080p piksel cinsinden. Telefonda okunurluk (sahibinin 11 Kasım 2026 geri bildirimi: "telefonda çok
# küçük"): en küçük yazı kare yüksekliğinin %2'sinden küçük olamaz (1080p'de 22 px), test_G14 sınar.
YAZI = {"baslik": 34, "alt": 24, "kayit": 27, "etiket": 22}
EN_KUCUK_YAZI_ORANI = 0.02
KENAR = 64
KART_KENAR = 40          # kayıt kartı köşeye daha yakın
KART_GENISLIK = 660      # 1080p'de ~%34 genişlik: videoya yayılmaz
KART_SUTUN = 34          # kart içinde satır başına en çok karakter


@lru_cache(maxsize=64)
def _font(boy: int, kalin: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / ("SpaceMono-Bold.ttf" if kalin else "SpaceMono-Regular.ttf")), boy)


def _kapla(img: Image.Image, w: int, h: int, kirp_x: float = 0.5) -> Image.Image:
    oran = max(w / img.width, h / img.height)
    yeni = img.resize((math.ceil(img.width * oran), math.ceil(img.height * oran)), Image.LANCZOS)
    x, y = int((yeni.width - w) * kirp_x), (yeni.height - h) // 2
    return yeni.crop((x, y, x + w, y + h))


def _kadraj(iw: int, ih: int, w: float, h: float, kirp_x: float = 0.5) -> tuple[float, float, float, float]:
    """Resmi w x h kareye kaplayan ölçek: (büyütülmüş genişlik, yükseklik, x kırpma, y kırpma), piksel."""
    oran = max(w / iw, h / ih)
    nw, nh = iw * oran, ih * oran
    return nw, nh, (nw - w) * kirp_x, (nh - h) / 2


ETKILER = ("isik", "toz", "goktasi", "yildiz", "isaret_lambasi", "pencereler", "kutup_isigi", "halka_piriltisi",
           "bulutsu_tulu", "uydu")


def muzikle_bagli(k: dict) -> bool:
    return k.get("nabiz") == "muzik" or bool(k.get("muzik"))


def _renk(h: str) -> np.ndarray:
    return np.array(rgb(h), np.float32) / 255


# ---------- müzik ----------
def ses_ozeti(ses: Path, fps: int, bant: int = 40, sr: int = 24000, basla: float = 0.0,
              sure: float | None = None) -> dict:
    """Kare başına müzik zarfı (0..1, yumuşak) ve spektrum bantları (kare x bant, 0..1).

    basla/sure: sesin yalnız bu aralığı okunur (uzun videoda her parça kendi aralığını okur)."""
    aralik = (["-ss", f"{basla:.3f}"] if basla else []) + (["-t", f"{sure:.3f}"] if sure else [])
    ham = subprocess.run(["ffmpeg", "-v", "error", *aralik, "-i", str(ses), "-ac", "1", "-ar", str(sr), "-f", "f32le",
                          "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(ham, np.float32)
    adim = sr / fps
    n = int(len(x) / adim) + 1
    pencere = 2048
    han = np.hanning(pencere).astype(np.float32)
    frek = np.fft.rfftfreq(pencere, 1 / sr)
    sinir = np.geomspace(60, 9000, bant + 1)
    idx = [np.where((frek >= a) & (frek < b))[0] for a, b in zip(sinir[:-1], sinir[1:])]
    rms = np.zeros(n, np.float32)
    spek = np.zeros((n, bant), np.float32)
    for i in range(n):
        a = int(i * adim)
        p = x[a:a + pencere]
        if len(p) < pencere:
            p = np.pad(p, (0, pencere - len(p)))
        rms[i] = np.sqrt(np.mean(p * p))
        m = np.abs(np.fft.rfft(p * han))
        spek[i] = [m[j].mean() if len(j) else 0 for j in idx]
    spek = np.log1p(spek / (np.percentile(spek, 99, axis=0) + 1e-6) * 6) / math.log1p(6)
    zarf = rms / (np.percentile(rms, 95) + 1e-6)

    def yumusat(v, tutma, birakma):  # tepeye hızlı çık, yavaş in
        o = np.zeros_like(v)
        s = v[0] if len(v) else 0
        for i, d in enumerate(v):
            s = s + (d - s) * np.where(d > s, tutma, birakma)
            o[i] = s
        return o
    return {"zarf": np.clip(yumusat(zarf, 0.05, 0.02), 0, 1.2), "spektrum": np.clip(yumusat(spek, 0.5, 0.12), 0, 1)}


# ---------- katmanlar ----------
def _hale(r: float, boy: int) -> np.ndarray:
    yy, xx = np.mgrid[-boy:boy + 1, -boy:boy + 1].astype(np.float32)
    d2 = (xx * xx + yy * yy) / max(r * r, 1e-3)
    return (np.exp(-d2 * 2.0) + 0.35 * np.exp(-d2 * 0.25)).astype(np.float32)  # çekirdek + yumuşak hale


def _ekle(kare: np.ndarray, sprite: np.ndarray, x: float, y: float, renk: np.ndarray, guc: float,
          sinir: tuple[int, int, int, int] | None = None):
    """sprite'ı (x, y) merkezine toplayarak ekler (ışık toplanır, görüntü bükülmez). sinir: piksel kutusu."""
    b = sprite.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    H, W = kare.shape[:2]
    X0, Y0, X1, Y1 = sinir or (0, 0, W, H)
    x0, y0, x1, y1 = max(X0, xi - b), max(Y0, yi - b), min(X1, xi + b + 1), min(Y1, yi + b + 1)
    if x0 >= x1 or y0 >= y1 or guc <= 0:
        return
    s = sprite[y0 - (yi - b):y1 - (yi - b), x0 - (xi - b):x1 - (xi - b)]
    kare[y0:y1, x0:x1] += s[..., None] * renk * guc


class SeyirDefteri:
    def __init__(self, gorsel: Path, katmanlar: list[dict], W: int, H: int, fps: int, sure: float, muzik: dict,
                 bilgi: dict, tohum: int = 1, ton: dict | None = None, t0: float = 0.0, kirp_x: float = 0.5,
                 kanca: str = ""):
        self.W, self.H, self.fps, self.sure, self.t0 = W, H, fps, sure, t0  # t0: görev saatinin başladığı an
        self.o = H / 1080
        self.dikey, self.kanca = H > W, kanca.strip()
        resim = Image.open(gorsel).convert("RGB")
        self._kadraj_kur(resim.width, resim.height, kirp_x)
        taban = np.asarray(_kapla(resim, W, H, kirp_x), np.float32) / 255
        if ton:
            from .renk import uygula
            taban = uygula(taban, ton)
        self.lum = taban @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        # Sinema kararması: alt ve üst kenar hafifçe koyulur, kayıt yazısı parlak zeminde de okunur.
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        koyu = np.clip((yy - 0.78) / 0.22, 0, 1) ** 1.5 * 0.5 + np.clip((0.15 - yy) / 0.15, 0, 1) ** 1.5 * 0.3
        self.taban = (taban * (1 - koyu)[..., None]).astype(np.float32)
        self.muzik, self.bilgi = muzik, bilgi
        rng = np.random.default_rng(tohum)
        self.palet = marka_yukle()["palet"]
        self.katmanlar = [self._hazirla(k, rng) for k in (self._cerceveye(k) for k in katmanlar) if k]
        self._kayit = self._kayit_satirlari()
        self._sabit = self._dikey_ust() if self.dikey else self._ust_sol()

    # ---------- kadraj: katmanlar 16:9 karede yazılır ----------
    def _kadraj_kur(self, iw: int, ih: int, kirp_x: float):
        self._yatay = _kadraj(iw, ih, 16, 9)                 # tarifin yazıldığı kare (oran yeter)
        self._bu = _kadraj(iw, ih, self.W, self.H, kirp_x)   # bu kare
        self.Wk = self._bu[0] * 16 / self._yatay[0]          # 16:9 karenin bu karedeki genişliği (boyut ölçeği)

    def _nokta(self, u: float, v: float) -> tuple[float, float]:
        nwl, nhl, oxl, oyl = self._yatay
        a, b = (u * 16 + oxl) / nwl, (v * 9 + oyl) / nhl    # resimde (0..1)
        nw, nh, ox, oy = self._bu
        return (a * nw - ox) / self.W, (b * nh - oy) / self.H

    def _cerceveye(self, k: dict) -> dict | None:
        k = dict(k)
        if "merkez" in k:
            k["merkez"] = list(self._nokta(*k["merkez"]))
        if "yol" in k:
            k["yol"] = [list(self._nokta(*q)) for q in k["yol"]]
        if "kutu" in k:
            (x0, y0), (x1, y1) = self._nokta(*k["kutu"][:2]), self._nokta(*k["kutu"][2:])
            x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(1.0, x1), min(1.0, y1)
            if x1 <= x0 or y1 <= y0:
                return None  # bu kadrajda görünmüyor
            k["kutu"] = [x0, y0, x1, y1]
        return k

    def _kutu_px(self, kutu) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = kutu
        X0, Y0 = min(self.W - 1, max(0, int(x0 * self.W))), min(self.H - 1, max(0, int(y0 * self.H)))
        return (X0, Y0, max(X0 + 1, min(self.W, math.ceil(x1 * self.W))),
                max(Y0 + 1, min(self.H, math.ceil(y1 * self.H))))

    def _hazirla(self, k: dict, rng) -> dict:
        e = k["etki"]
        if e == "isaret_lambasi":
            k = {"yaricap": 0.004, "renk": "#ff5a3c", "periyot": 2.0, "guc": 0.8, **k, "etki": "isik",
                 "nabiz": "yanip_son"}
            e = "isik"
        if e in ("pencereler", "kutup_isigi", "halka_piriltisi", "bulutsu_tulu"):
            k["sinir"] = self._kutu_px(k.get("kutu", [0, 0, 1, 1]))
            X0, Y0, X1, Y1 = k["sinir"]
            yy = np.linspace(0, 1, Y1 - Y0, dtype=np.float32)[:, None]
            xx = np.linspace(0, 1, X1 - X0, dtype=np.float32)[None, :]
            k["kenar"] = np.sqrt(np.clip(np.sin(np.pi * yy) * np.sin(np.pi * xx), 0, 1)).astype(np.float32)  # kutu kenarında 0
        if e == "pencereler":
            n = int(k.get("adet", 12))
            k["px"], k["py"] = rng.uniform(X0, X1, n), rng.uniform(Y0, Y1, n)
            ort = float(k.get("ortalama_sn", 20.0))
            k["acik0"] = rng.random(n) < 0.6
            k["degisim"] = [np.cumsum(rng.exponential(ort, int(self.sure / ort * 3) + 8)) for _ in range(n)]
            r = max(1.0, 0.0025 * self.Wk)
            k["sprite"] = _hale(r, int(r * 6) + 2)
            k["rgb"] = _renk(k.get("renk", "#ffd9a0"))
        elif e == "kutup_isigi":
            k["maske"] = (self.lum[Y0:Y1, X0:X1] * k["kenar"]).astype(np.float32)
            k["xf"] = np.linspace(0, 1, X1 - X0, dtype=np.float32)[None, :] * TAU * 1.5  # perde dalgası
            k["rgb"] = _renk(k.get("renk", "#5cffb0"))
        elif e == "halka_piriltisi":
            yy, xx = np.nonzero(self.lum[Y0:Y1, X0:X1] > k.get("esik", 0.35))
            n = min(int(k.get("adet", 40)), len(yy))
            sec = rng.choice(len(yy), n, replace=False) if n else np.array([], int)
            k["px"], k["py"] = xx[sec] + X0 + 0.0, yy[sec] + Y0 + 0.0
            k["faz"], k["w"] = rng.uniform(0, TAU, n), rng.uniform(0.15, 0.5, n)
            r = max(0.8, 0.0018 * self.Wk)
            k["sprite"] = _hale(r, int(r * 6) + 2)
            k["rgb"] = _renk(k.get("renk", "#fff6e8"))
        elif e == "bulutsu_tulu":
            # gürültü = ortalama sin(TAU·(fx·(x − kayma) + fy·y) + faz); sin(A+B) = sinA·cosB + cosA·sinB ayrışır,
            # böylece her karede tam boy sin yerine küçük bir matris çarpımı yeter (aynı görüntü, 4K'da hızlı).
            dalga = np.array([(rng.uniform(1, 3), rng.uniform(-1.5, 1.5), rng.uniform(0, TAU)) for _ in range(3)])
            yy = np.arange(Y0, Y1, dtype=np.float64) / self.H
            B = TAU * np.outer(yy, dalga[:, 1]) + dalga[:, 2]
            k["cosB"], k["sinB"] = np.cos(B).astype(np.float32) / 3, np.sin(B).astype(np.float32) / 3
            k["fx"] = dalga[:, 0]
            k["xx"] = np.arange(X0, X1, dtype=np.float64) / self.W
        elif e == "uydu":
            (ax, ay), (bx, by) = k.get("yol", [[0.1, 0.2], [0.9, 0.3]])
            k["a"], k["b"] = np.array([ax * self.W, ay * self.H]), np.array([bx * self.W, by * self.H])
            k["faz"] = rng.uniform(0, k.get("aralik", 240))
            r = max(0.9, 0.002 * self.Wk)
            k["sprite"] = _hale(r, int(r * 6) + 2)
            k["rgb"] = _renk(k.get("renk", "#f4f1ff"))
        elif e == "isik":
            r = k.get("yaricap", 0.004) * self.Wk
            k["sprite"] = _hale(r, int(r * 6) + 2)
            k["rgb"] = _renk(k.get("renk", "#ffd9a0"))
        elif e in ("toz", "yildiz"):
            x0, y0, x1, y1 = k.get("kutu", [0, 0, 1, 1])
            n = int(k.get("adet", 70 if e == "toz" else 120))
            k["px"] = rng.uniform(x0, x1, n) * self.W
            k["py"] = rng.uniform(y0, y1, n) * self.H
            if e == "yildiz":  # yalnız karanlık gökte
                koy = self.lum[k["py"].astype(int).clip(0, self.H - 1), k["px"].astype(int).clip(0, self.W - 1)]
                tut = koy < k.get("esik", 0.18)
                k["px"], k["py"] = k["px"][tut], k["py"][tut]
                n = len(k["px"])
            k["z"] = rng.uniform(0.3, 1.0, n)  # derinlik: yakın toz büyük, hızlı, parlak
            k["faz"] = rng.uniform(0, TAU, n)
            k["w"] = rng.uniform(0.15, 0.5, n)
            k["sprite"] = {b: _hale(b, int(b * 4) + 1) for b in (0.7, 1.0, 1.4, 1.9, 2.5)}
            k["rgb"] = _renk(k.get("renk", "#ffe2b0" if e == "toz" else "#f4f1ff"))
        elif e == "goktasi":
            a, b = k.get("aralik", [70, 140])
            t, olay = rng.uniform(a / 3, a), []
            while t < self.sure:
                olay.append((t, rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(-0.5, 0.5)))
                t += rng.uniform(a, b)
            k["olay"] = olay
            k["rgb"] = _renk(k.get("renk", "#fff4e0"))
            k["sprite"] = _hale(1.1 * self.o, 4)
        return k

    # ---------- kayıt (HUD) ----------
    def _kayit_satirlari(self) -> list[tuple[float, str]]:
        b = self.bilgi
        satir = [(3.0, f"ARRIVAL  {b['ad']}")]
        t = 6.0
        for parca in textwrap.wrap(b.get("kisa", ""), KART_SUTUN) + textwrap.wrap(b.get("bilgi", ""), KART_SUTUN):
            satir.append((t, parca))
            t += len(parca) / 20 + 1.2
        satir.append((self.sure * 0.5, "SIGNAL STEADY · COURSE HELD"))
        if b.get("sonraki"):
            satir.append((max(t + 30, self.sure - 45), f"NEXT  {b['sonraki']}"))
        return satir

    # Yazılar küçük şeffaf parçalara çizilir ve yalnız o bölgeye bindirilir (tam kare RGBA her karede pahalı).
    def _parca(self, w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    def _yazi(self, d, xy, metin, boy, kalin=False, opak=1.0, renk=None, hiza="sol", genislik=0):
        """Telefonda okunur: koyu kontur + gölge. boy 1080p piksel cinsinden (YAZI tablosundan)."""
        f = _font(int(boy * self.o), kalin)
        x, y = xy
        if hiza == "sag":
            x = genislik - d.textlength(metin, font=f) - x
        elif hiza == "orta":
            x = (genislik - d.textlength(metin, font=f)) / 2 + x
        r = rgb(renk or self.palet["yazi"])
        kontur = max(1, int(2 * self.o))
        d.text((x + 1, y + 3 * self.o), metin, font=f, fill=(0, 0, 0, int(120 * opak)))
        d.text((x, y), metin, font=f, fill=(*r, int(255 * opak)), stroke_width=kontur,
               stroke_fill=(8, 10, 18, int(150 * opak)))

    def _ust_sol(self) -> tuple[int, int, np.ndarray]:
        o, b, m = self.o, self.bilgi, int(KENAR * self.o)
        img, d = self._parca(1100 * o, 90 * o)
        self._yazi(d, (0, 0), "DEEP SPACE LOG", YAZI["baslik"], True, 0.95)
        self._yazi(d, (0, 48 * o), f"MISSION {b['gorev_no']:03d}  ·  {b['hedef']}", YAZI["alt"], False, 0.85,
                   self.palet["yazi_ikincil"])
        return m, m, np.asarray(img, np.float32) / 255

    # ---------- dikey (Shorts) ----------
    def _dikey_ust(self) -> tuple[int, int, np.ndarray]:
        """Üstte marka ve görev, y ≈ 0.28·H'de harf aralıklı kanca ve kehribar çizgi (marka.toml [sablon])."""
        b, W, H = self.bilgi, self.W, self.H
        sb = marka_yukle()["sablon"]
        olc = H / 1920
        img, d = self._parca(W, int(0.36 * H))
        etiket = sb["short_etiket"] / self.o * olc  # _yazi boyu 1080p birimindedir
        self._yazi(d, (0, 0.05 * H), "DEEP SPACE LOG", etiket * 1.2, True, 0.95, hiza="orta", genislik=W)
        self._yazi(d, (0, 0.05 * H + etiket * 1.75 * self.o), f"MISSION {b['gorev_no']:03d}  ·  {b['hedef']}",
                   etiket, False, 0.9, self.palet["yazi_ikincil"], hiza="orta", genislik=W)
        if self.kanca:
            metin = self.kanca.upper()
            boy = int(sb["short_kanca"] * olc)
            f = _font(boy)
            iz = boy * 0.22
            while sum(f.getlength(c) for c in metin) + iz * (len(metin) - 1) > W * 0.9 and boy > 12:
                boy = int(boy * 0.92)
                f, iz = _font(boy), boy * 0.22
            gen = sum(f.getlength(c) for c in metin) + iz * (len(metin) - 1)
            x, y = (W - gen) / 2, 0.28 * H - boy * 0.6
            kontur = max(1, int(2 * self.o))
            for c in metin:
                d.text((x + 1, y + 3 * self.o), c, font=f, fill=(0, 0, 0, 130))
                d.text((x, y), c, font=f, fill=(*rgb(self.palet["yazi"]), 255), stroke_width=kontur,
                       stroke_fill=(8, 10, 18, 150))
                x += f.getlength(c) + iz
            cy, cw = y + boy * 1.45, boy * 3.2
            d.line([(W / 2 - cw / 2, cy), (W / 2 + cw / 2, cy)], fill=(*rgb(self.palet["vurgu"]), 235),
                   width=max(2, boy // 24))
        return 0, 0, np.asarray(img, np.float32) / 255

    def _dikey_alt(self, i: int) -> tuple[int, int, np.ndarray]:
        """y > 0.8·H: "Full N-hour mission on the channel" ve tam genişlikte sinyal çizgisi."""
        W, H, o = self.W, self.H, self.o
        sb = marka_yukle()["sablon"]
        m = int(KENAR * o * 0.6)
        ph, k = int(0.16 * H), 2
        img = Image.new("RGBA", (W * k, ph * k), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        boy = sb["short_etiket"] * H / 1920
        f = _font(int(boy * k))
        metin = f"Full {self.bilgi.get('saat', 2)}-hour mission on the channel"
        d.text(((W * k - d.textlength(metin, font=f)) / 2, 0), metin, font=f,
               fill=(*rgb(self.palet["yazi"]), 235), stroke_width=max(1, int(2 * k * o)), stroke_fill=(8, 10, 18, 150))
        sp = self.muzik["spektrum"][min(i, len(self.muzik["spektrum"]) - 1)]
        xs = np.linspace(m * k, (W - m) * k, 200)
        ince = np.convolve(np.interp(xs, np.linspace(m * k, (W - m) * k, len(sp)), sp), np.ones(5) / 5, mode="same")
        taban_y, tepe = ph * k * 0.92, ph * k * 0.42
        d.line([(m * k, taban_y), ((W - m) * k, taban_y)], fill=(*rgb(self.palet["yazi_ikincil"]), 90), width=k)
        d.line([(float(x), float(taban_y - v * tepe)) for x, v in zip(xs, ince)],
               fill=(*rgb(self.palet["vurgu"]), 235), width=max(1, int(2.6 * k * o)), joint="curve")
        img = img.resize((W, ph), Image.LANCZOS)
        return 0, int(0.8 * H), np.asarray(img, np.float32) / 255

    def _kayit_karti(self, satirlar: list[tuple[str, float]]) -> tuple[int, int, np.ndarray]:
        """Sol alt köşede dar kayıt kartı (sahibinin isteği, 11 Kasım 2026: "şık arka plan, köşede, videoya
        yayılmadan"). Koyu cam zemin, ince çerçeve, solda vurgu çizgisi, üstte PROBE-7 · LOG etiketi."""
        o, H = self.o, self.H
        m = int(KART_KENAR * o)
        sat = YAZI["kayit"] * 1.42 * o
        ic = 22 * o
        bas_h = YAZI["etiket"] * 1.6 * o
        kw, kh = int(KART_GENISLIK * o), int(ic * 2 + bas_h + sat * 3)
        sol = max(s for _, s in satirlar)
        img = Image.new("RGBA", (kw, kh), (0, 0, 0, 0))
        zemin = Image.new("RGBA", (kw, kh), (0, 0, 0, 0))
        zd = ImageDraw.Draw(zemin)
        r = int(14 * o)
        zd.rounded_rectangle([0, 0, kw - 1, kh - 1], radius=r, fill=(*rgb(self.palet["arka"]), int(178 * sol)),
                             outline=(*rgb(self.palet["yazi_ikincil"]), int(55 * sol)), width=max(1, int(1.5 * o)))
        zd.rounded_rectangle([0, r, int(4 * o), kh - r], radius=int(2 * o), fill=(*rgb(self.palet["vurgu"]), int(230 * sol)))
        img.alpha_composite(zemin)
        d = ImageDraw.Draw(img)
        x = int(ic + 6 * o)
        self._yazi(d, (x, ic - 4 * o), "PROBE-7  ·  LOG", YAZI["etiket"], True, 0.9 * sol, self.palet["vurgu"])
        y = ic + bas_h
        for metin, s in satirlar:
            self._yazi(d, (x, y), metin, YAZI["kayit"], False, 0.96 * s)
            y += sat
        return m, H - m - kh, np.asarray(img, np.float32) / 255

    def _hud(self, t: float, i: int) -> list[tuple[int, int, np.ndarray]]:
        if self.dikey:
            return [self._sabit, self._dikey_alt(i)]
        o, W, H, b = self.o, self.W, self.H, self.bilgi
        m = int(KENAR * o)
        parcalar = [self._sabit]
        # sağ üst: görev saati ve alım ışığı
        gw = int(620 * o)
        img, d = self._parca(gw, 90 * o)
        s = int(self.t0 + t)
        self._yazi(d, (0, 0), f"T+{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}", YAZI["baslik"], True, 0.95,
                   hiza="sag", genislik=gw)
        alt = f"{b['parca_no']:02d}/{b['parca_say']:02d}  RECEIVING"
        self._yazi(d, (0, 48 * o), alt, YAZI["alt"], False, 0.85, self.palet["yazi_ikincil"], hiza="sag", genislik=gw)
        nabiz = 0.3 + 0.7 * (0.5 + 0.5 * math.cos(TAU * t / 2.4))
        gx = gw - d.textlength(alt, font=_font(int(YAZI["alt"] * o))) - 22 * o
        r, cy = 7 * o, 48 * o + YAZI["alt"] * 0.62 * o
        d.ellipse([gx - r, cy - r, gx + r, cy + r], fill=(*rgb(self.palet["vurgu"]), int(255 * nabiz)))
        parcalar.append((W - m - gw, m, np.asarray(img, np.float32) / 255))
        # sol alt: kayıt, son 3 satır, harf harf yazılır, 40 sn sonra solar
        gorunen = []
        for bas, metin in self._kayit:
            if t < bas:
                continue
            n = int((t - bas) * 22)
            sol = 1.0 if t - bas < 40 else max(0.0, 1 - (t - bas - 40) / 3)
            if sol > 0:
                gorunen.append(("> " + metin[:n] + ("_" if n < len(metin) and i % 12 < 6 else ""), sol))
        if gorunen:
            parcalar.append(self._kayit_karti(gorunen[-3:]))
        # sağ alt: sinyal, müziğin spektrumu (3x çizilip küçültülür: kenarlar yumuşak)
        sp = self.muzik["spektrum"][min(i, len(self.muzik["spektrum"]) - 1)]
        gw, gh, k = int(560 * o), int(120 * o), 3
        s_img = Image.new("RGBA", (gw * k, gh * k), (0, 0, 0, 0))
        sd = ImageDraw.Draw(s_img)
        xs = np.linspace(0, gw * k - 1, 180)
        ince = np.convolve(np.interp(xs, np.linspace(0, gw * k - 1, len(sp)), sp), np.ones(5) / 5, mode="same")
        taban_y = gh * k * 0.96
        tepe = gh * k * 0.62  # etiketin altından başlar
        golge = [(float(x), float(taban_y - v * tepe + 3 * k * o)) for x, v in zip(xs, ince)]
        sd.line(golge, fill=(8, 10, 18, 120), width=max(1, int(4 * k * o)), joint="curve")
        sd.line([(0, taban_y), (gw * k, taban_y)], fill=(*rgb(self.palet["yazi_ikincil"]), 90), width=k)
        sd.line([(float(x), float(taban_y - v * tepe)) for x, v in zip(xs, ince)],
                fill=(*rgb(self.palet["vurgu"]), 235), width=max(1, int(2.6 * k * o)), joint="curve")
        f = _font(int(YAZI["etiket"] * o * k))
        sd.text((0, 0), "SIGNAL", font=f, fill=(*rgb(self.palet["yazi_ikincil"]), 210),
                stroke_width=max(1, int(2 * k * o)), stroke_fill=(8, 10, 18, 140))
        s_img = s_img.resize((gw, gh), Image.LANCZOS)
        parcalar.append((W - m - gw, H - m - gh, np.asarray(s_img, np.float32) / 255))
        return parcalar

    # ---------- kare ----------
    def kare(self, i: int) -> np.ndarray:
        t = i / self.fps
        kare = self.taban.copy()
        zarf = float(self.muzik["zarf"][min(i, len(self.muzik["zarf"]) - 1)])
        for k in self.katmanlar:
            e = k["etki"]
            carp = 0.7 + 0.6 * min(zarf, 1.0) if k.get("muzik") else 1.0
            if e == "isik":
                x, y = k["merkez"][0] * self.W, k["merkez"][1] * self.H
                p = k.get("periyot", 4.0)
                if k.get("nabiz") == "yanip_son":  # LED: kısa, yumuşak kenarlı yanma
                    f = (t % p) / p
                    g = math.exp(-((f - 0.1) / 0.05) ** 2)
                elif k.get("nabiz") == "muzik":
                    g = 0.75 + 0.25 * min(zarf, 1.0) + 0.05 * math.sin(TAU * t / p)
                else:
                    g = 0.5 + 0.5 * math.sin(TAU * t / p)
                _ekle(kare, k["sprite"], x, y, k["rgb"], k.get("guc", 0.5) * g * carp)
            elif e in ("toz", "yildiz"):
                x0, y0, x1, y1 = (np.array(k.get("kutu", [0, 0, 1, 1])) * [self.W, self.H, self.W, self.H])
                if e == "toz":
                    hiz = k.get("hiz", 6) * self.o
                    px = x0 + (k["px"] - x0 + hiz * k["z"] * t) % max(x1 - x0, 1)
                    py = k["py"] + 3 * self.o * np.sin(k["w"] * t + k["faz"])
                    parlak = k.get("parlaklik", 0.35) * k["z"] * (0.55 + 0.45 * np.sin(k["w"] * 1.7 * t + k["faz"]) ** 2)
                    boy = 0.7 + 1.8 * k["z"]
                else:
                    px, py = k["px"], k["py"]
                    parlak = k.get("parlaklik", 0.6) * np.clip(np.sin(k["w"] * 3 * t + k["faz"]), 0, 1) ** 3
                    boy = 0.7 + 0.6 * k["z"]
                parlak = parlak * carp
                for x, y, p, b in zip(px, py, parlak, np.broadcast_to(boy, px.shape)):
                    if p > 0.01:
                        anah = min(k["sprite"], key=lambda q: abs(q - b * self.o))
                        _ekle(kare, k["sprite"][anah], x, y, k["rgb"], float(p))
            elif e == "goktasi":
                x0, y0, x1, y1 = k.get("kutu", [0, 0, 1, 0.4])
                sure = k.get("sure", 0.7)
                for bas, ax, ay, egim in k["olay"]:
                    if 0 <= t - bas <= sure:
                        f = (t - bas) / sure
                        sx, sy = (x0 + ax * (x1 - x0)) * self.W, (y0 + ay * (y1 - y0)) * self.H
                        dx, dy = 260 * self.o, (90 + 80 * egim) * self.o
                        bas_x, bas_y = sx + dx * f, sy + dy * f
                        isik = k.get("parlaklik", 0.5) * math.sin(math.pi * f) * carp
                        for j in range(28):  # kuyruk
                            q = j / 28
                            _ekle(kare, k["sprite"], bas_x - dx * 0.35 * q, bas_y - dy * 0.35 * q, k["rgb"],
                                  isik * (1 - q) ** 2)
            elif e == "pencereler":
                for x, y, a0, dg in zip(k["px"], k["py"], k["acik0"], k["degisim"]):
                    j = int(np.searchsorted(dg, t, side="right"))
                    acik = bool(a0) ^ (j % 2 == 1)
                    gecis = min(1.0, (t - dg[j - 1]) / 1.0) if j else 1.0  # 1 sn yumuşak geçiş
                    oran = gecis if acik else 1 - gecis
                    oran = oran * oran * (3 - 2 * oran)
                    if oran > 0.005:
                        _ekle(kare, k["sprite"], x, y, k["rgb"], k.get("guc", 0.6) * oran * carp, k["sinir"])
            elif e == "kutup_isigi":
                X0, Y0, X1, Y1 = k["sinir"]
                dalga = 0.5 + 0.5 * np.sin(TAU * t / k.get("periyot", 9.0) + k["xf"])
                kare[Y0:Y1, X0:X1] += (k["maske"] * dalga)[..., None] * (k["rgb"] * (k.get("guc", 0.25) * carp))
            elif e == "halka_piriltisi":
                parlak = k.get("guc", 0.5) * carp * np.clip(np.sin(k["w"] * 3 * t + k["faz"]), 0, 1) ** 3
                for x, y, p in zip(k["px"], k["py"], parlak):
                    if p > 0.01:
                        _ekle(kare, k["sprite"], x, y, k["rgb"], float(p), k["sinir"])
            elif e == "bulutsu_tulu":
                X0, Y0, X1, Y1 = k["sinir"]
                A = TAU * np.outer(k["fx"], k["xx"] - k.get("hiz", 0.01) * t)
                n = k["cosB"] @ np.sin(A).astype(np.float32) + k["sinB"] @ np.cos(A).astype(np.float32)
                n *= k["kenar"]
                n *= k.get("guc", 0.12) * carp
                n += 1
                kare[Y0:Y1, X0:X1] *= n[..., None]
            elif e == "uydu":
                ar, su = k.get("aralik", 240), k.get("sure", 90)
                if t >= k["faz"] and (t - k["faz"]) % ar < su:
                    f = ((t - k["faz"]) % ar) / su
                    x, y = k["a"] + (k["b"] - k["a"]) * f
                    _ekle(kare, k["sprite"], x, y, k["rgb"],
                          k.get("parlaklik", 0.8) * carp * math.sqrt(max(0.0, math.sin(math.pi * f))))
        np.clip(kare, 0, 1, out=kare)
        for x, y, p in self._hud(t, i):
            h, w = p.shape[:2]
            h, w = min(h, self.H - y), min(w, self.W - x)
            a = p[:h, :w, 3:4]
            bolge = kare[y:y + h, x:x + w]
            kare[y:y + h, x:x + w] = bolge * (1 - a) + p[:h, :w, :3] * a
        kare *= 255
        kare += 0.5
        return kare.astype(np.uint8)


def katmanlari_oku(gorsel: Path) -> list[dict]:
    yol = gorsel.with_name(gorsel.stem + "_hareket.json")
    return json.loads(yol.read_text(encoding="utf-8")).get("katmanlar", []) if yol.exists() else []


def kodla(sahne: SeyirDefteri, ses: Path | None, hedef: Path, ses_filtresi: str | None, crf: int = 18,
          preset: str = "medium", ses_basla: float = 0.0) -> Path:
    """Kareleri doğrudan ffmpeg'e akıtır; ses aynı geçişte eklenir.

    ses=None sessiz ara çıktıdır (uzun videonun parça bölümleri) ve yalnız bir `ara/` klasörüne yazılabilir;
    teslim edilen hiçbir dosya sessiz olamaz (G14)."""
    hedef = Path(hedef)
    if ses is None and hedef.parent.name != "ara":
        raise ValueError(f"sessiz video yalnız ara/ klasörüne yazılır (G14): {hedef}")
    W, H, fps = sahne.W, sahne.H, sahne.fps
    n = int(math.ceil(sahne.sure * fps - 1e-6))
    komut = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(fps), "-i", "-"]
    if ses is None:
        komut += ["-an"]
    else:
        if ses_basla:  # sesin bu andan başlayan dilimi (Shorts: master'dan aynı aralık)
            komut += ["-ss", f"{ses_basla:.3f}", "-t", f"{sahne.sure:.3f}"]
        komut += ["-i", str(ses), "-map", "0:v", "-map", "1:a", "-af", ses_filtresi, "-c:a", "aac", "-b:a", "320k"]
    komut += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-g", str(fps * 2),
              "-t", f"{sahne.sure:.3f}", "-movflags", "+faststart", str(hedef)]
    surec = subprocess.Popen(komut, stdin=subprocess.PIPE)
    try:
        for i in range(n):
            surec.stdin.write(sahne.kare(i).tobytes())
    finally:
        surec.stdin.close()
        surec.wait()
    if surec.returncode != 0:
        raise RuntimeError(f"ffmpeg başarısız ({surec.returncode})")
    return hedef
