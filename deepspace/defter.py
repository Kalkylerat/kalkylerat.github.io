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
Marka kaydı (HUD, G14, 17 Kasım 2026 yerleşimi): sol üst halka-7, kanal, görev ve cismin veri satırı; sağ üst görev
saati; sağ kenarda Dock rotası (o anki durak büyük ve parlak, şarkı adıyla; uzaklar küçük ve soluk); sol altta buzlu
cam kayıt kartı (gerçek bilgi `gorev.toml`'dan) ve hemen altında müziğin spektrumundan "sinyal" çizgisi. Üst %10 ve
alt %16 boş kalır (oynatıcının başlığı ve oynatma çubuğu). Tarif: `gorsel/NN_hareket.json` içinde "katmanlar".
Dikey (Shorts, H > W): görsel `kirp_x` odağında kırpılır; üstte marka + görev, y ≈ 0.28·H'de kanca, altta (y > 0.8·H)
"Full N-hour mission" ve tam genişlikte sinyal; kayıt kartı yok. Katman koordinatları 16:9 karede yazılır ve dikey
kadraja resimle birlikte taşınır.
"""
from __future__ import annotations

import json
import math
import re
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
KART_SATIR = 3
# Oynatıcı güvenli alanı (G14-4): YouTube'un oynatma çubuğu karenin alt kısmını kaplar; yatay videoda hiçbir yazı
# ya da sinyal çizgisi alt ALT_GUVENLI oranına girmez. Kayıt kartı (G14-5): bilgi cümlesi bir kez, en çok 3 satırlık
# sayfalarla, kaymadan yazılır; her sayfa yazıldıktan sonra OKUMA_SN kalır; kart bütün olarak SOLMA_SN'de söner.
ALT_GUVENLI = 0.16
# Arayüz sönmesi (bağımsız inceleme önerisi, 11 Kasım 2026): parçanın ilk ACIK_SN'sinden sonra saat, başlık ve sinyal
# SONUK opaklığa iner (uyku dinleyicisi için); kart etkilenmez.
ACIK_SN = 60
SONUK = 0.6
YAZMA_HIZI = 22      # harf/sn
OKUMA_SN = 10
SOLMA_SN = 3
SONRAKI_SN = 25
# Yerleşim (G14, 17 Kasım 2026, sahibinin onayı): tam ekranda YouTube video başlığını üste yazar; yatay videoda hiçbir
# arayüz öğesi üst UST_GUVENLI oranına girmez. Rota sağ kenardadır, macOS Dock gibi: uzaklık -> (durak yazı boyu,
# şarkı adı boyu ya da 0, opaklık, nokta yarıçapı), 1080p piksel. Şarkı adları tek istisna fontla (G16, OFL).
UST_GUVENLI = 0.10
SARKI_FONT = "Lora-Italic.ttf"
ROTA_OLCEK = {0: (48, 34, 1.0, 9), 1: (30, 24, 0.70, 6), 2: (24, 0, 0.49, 4), 3: (22, 0, 0.33, 3), 4: (22, 0, 0.20, 2)}
ROTA_ARA = 34          # duraklar arası boşluk
ROTA_MERKEZ = 0.49     # o anki durağın dikey merkezi
# Perde (G14, 17 Kasım 2026, sahibinin isteği: "kesinlikle belli belirsiz"): sabit göstergelerin arkası en çok bu
# oranda koyulaşır; kenarsız, yazının şeklini izleyen yumuşak gölge.
PERDE_GUC = 0.55


@lru_cache(maxsize=64)
def kanca_boyu(metin: str, W: int, H: int, taban: int) -> tuple[int, bool]:
    """Short kancasının yazı boyu: tabandan küçülerek W·0.9'a sığana kadar, ama en az EN_KUCUK_YAZI_ORANI·H
    (G16 telefon kuralı). İkinci değer: o boyda sığıyor mu."""
    metin = metin.upper()
    en_kucuk = math.ceil(EN_KUCUK_YAZI_ORANI * H)

    def gen(b):
        f = _font(b)
        return sum(f.getlength(c) for c in metin) + b * 0.22 * (len(metin) - 1)

    boy = max(taban, en_kucuk)
    while gen(boy) > W * 0.9 and boy > en_kucuk:
        boy = max(en_kucuk, int(boy * 0.92))
    return boy, gen(boy) <= W * 0.9


def kanca_sigar_mi(metin: str, W: int, H: int) -> bool:
    return kanca_boyu(metin, W, H, math.ceil(EN_KUCUK_YAZI_ORANI * H))[1]


def _font(boy: int, kalin: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / ("SpaceMono-Bold.ttf" if kalin else "SpaceMono-Regular.ttf")), boy)


@lru_cache(maxsize=16)
def _sarki_font(boy: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT / SARKI_FONT), boy)


def sarki_adi(parca: dict) -> str:
    """Şarkının adı: `sarki` alanı ya da motifin ':'dan önceki kısmı ("Rings: G-B-D-F#, ..." -> "Rings")."""
    if parca.get("sarki"):
        return str(parca["sarki"]).strip()
    motif = str(parca.get("motif", ""))
    return motif.split(":", 1)[0].strip() if ":" in motif else ""


def _aralikli(d: ImageDraw.ImageDraw, xy, metin: str, f: ImageFont.FreeTypeFont, renk, opak: float = 1.0,
              aralik: float = 0.0, sag: bool = False) -> float:
    """Harf aralıklı yazı (kutusuz, konturusuz; okunurluğu _golgeli verir). sag=True ise x sağ kenardır."""
    ek = f.size * aralik
    gen = sum(f.getlength(c) for c in metin) + ek * max(0, len(metin) - 1)
    x, y = xy
    if sag:
        x -= gen
    for c in metin:
        d.text((x, y), c, font=f, fill=(*renk, int(255 * opak)))
        x += f.getlength(c) + ek
    return gen


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


def cumleler(metin: str) -> list[str]:
    return [c for c in re.split(r"(?<=[.!?])\s+", metin.strip()) if c]


def kart_sayfalari(metin: str) -> list[list[str]]:
    """Kart sayfaları (G14-5): her sayfa en çok KART_SATIR satır ve yalnız tam cümleler; cümle iki sayfaya bölünmez.
    Tek başına KART_SATIR'ı aşan cümle kendi sayfasında kalır (kapı bunu önceden reddeder)."""
    sayfalar, simdi = [], []
    for c in cumleler(metin):
        aday = simdi + [c]
        if simdi and len(textwrap.wrap(" ".join(aday), KART_SUTUN, break_on_hyphens=False)) > KART_SATIR:
            sayfalar.append(textwrap.wrap(" ".join(simdi), KART_SUTUN, break_on_hyphens=False))
            aday = [c]
        simdi = aday
    if simdi:
        sayfalar.append(textwrap.wrap(" ".join(simdi), KART_SUTUN, break_on_hyphens=False))
    return sayfalar


class SeyirDefteri:
    def __init__(self, gorsel: Path, katmanlar: list[dict], W: int, H: int, fps: int, sure: float, muzik: dict,
                 bilgi: dict, tohum: int = 1, ton: dict | None = None, t0: float = 0.0, kirp_x: float = 0.5,
                 kanca: str = "", onceki: Path | None = None, sonraki: Path | None = None, gecis_sn: float = 0.0):
        self.W, self.H, self.fps, self.sure, self.t0 = W, H, fps, sure, t0  # t0: görev saatinin başladığı an
        self.o = H / 1080
        self.dikey, self.kanca = H > W, kanca.strip()
        resim = Image.open(gorsel).convert("RGB")
        self._kadraj_kur(resim.width, resim.height, kirp_x)
        self.taban = self._taban_hazirla(resim, kirp_x, ton)
        self.lum = self._lum
        # Parça geçişi: kesim çapraz geçişin ortasındadır; bu bölümün ilk ve son gecis_sn/2'sinde komşu görsel
        # yarıya kadar karışır, böylece görüntü sesle birlikte yumuşakça döner (sert kesim yok).
        self.gecis = gecis_sn
        self.onceki = self._taban_hazirla(Image.open(onceki).convert("RGB"), kirp_x, ton) if onceki and gecis_sn else None
        self.sonraki = self._taban_hazirla(Image.open(sonraki).convert("RGB"), kirp_x, ton) if sonraki and gecis_sn else None
        self.muzik, self.bilgi = muzik, bilgi
        rng = np.random.default_rng(tohum)
        self.palet = marka_yukle()["palet"]
        self.katmanlar = [self._hazirla(k, rng) for k in (self._cerceveye(k) for k in katmanlar) if k]
        self._kayit = self._kayit_sayfalari()
        self._sabit = self._dikey_ust() if self.dikey else self._ust_sol()
        self._rota = None if self.dikey else self._rota_kur()
        self._saat = (-1, None)
        if not self.dikey:  # perde bir kez hesaplanır, görüntünün kendisine işlenir (komşu görseller dahil)
            perde = (1 - self._perde())[..., None]
            self.taban = (self.taban * perde).astype(np.float32)
            if self.onceki is not None:
                self.onceki = (self.onceki * perde).astype(np.float32)
            if self.sonraki is not None:
                self.sonraki = (self.sonraki * perde).astype(np.float32)
        self._cam = None if self.dikey else self._cam_kur()

    def _taban_hazirla(self, resim: Image.Image, kirp_x: float, ton: dict | None) -> np.ndarray:
        W, H = self.W, self.H
        taban = np.asarray(_kapla(resim, W, H, kirp_x), np.float32) / 255
        if ton:
            from .renk import uygula
            taban = uygula(taban, ton)
        self._lum = taban @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        # Sinema kararması: alt ve üst kenar hafifçe koyulur, kayıt yazısı parlak zeminde de okunur.
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        koyu = np.clip((yy - 0.78) / 0.22, 0, 1) ** 1.5 * 0.5 + np.clip((0.15 - yy) / 0.15, 0, 1) ** 1.5 * 0.3
        return (taban * (1 - koyu)[..., None]).astype(np.float32)

    def gecis_agirligi(self, t: float) -> tuple[float, float]:
        """(önceki görselin payı, sonraki görselin payı) t anında; kesimde ikisi de 0.5'tir."""
        if not self.gecis:
            return 0.0, 0.0
        y = self.gecis / 2
        once = max(0.0, 0.5 * (1 - t / y)) if self.onceki is not None else 0.0
        sonra = max(0.0, 0.5 * (1 - (self.sure - t) / y)) if self.sonraki is not None else 0.0
        return once, sonra

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
    def _kayit_sayfalari(self) -> list[tuple[float, float, str, list[str]]]:
        """(başlangıç, bitiş, etiket, satırlar). Bilgi cümlesi bir kez, 3 satırlık sayfalarla; ad ve kısa özet
        kartta tekrar edilmez (G14-5). Parça sonuna yakın tek satırlık NEXT kartı."""
        b = self.bilgi
        sayfalar, t = [], 3.0
        for sayfa in kart_sayfalari(b.get("bilgi") or b.get("kisa", "")):
            son = t + sum(map(len, sayfa)) / YAZMA_HIZI + OKUMA_SN
            sayfalar.append((t, son, "ARRIVAL", sayfa))
            t = son
        if b.get("sonraki"):
            bas = max(t + 30, self.sure - 45)
            sayfalar.append((bas, bas + SONRAKI_SN, "NEXT", [f"course set for {b['sonraki']}"]))
        return sayfalar

    def _kart(self, t: float) -> tuple[str, list[str], float] | None:
        """t anında kartta görünen (etiket, yazılmış satırlar, opaklık); kart yoksa None. Satırlar yerinde
        harf harf yazılır, yukarı kaymaz; sayfa bitince bir sonraki aynı yere gelir, son sayfadan sonra söner."""
        etkin = [s for s in self._kayit if s[0] <= t]
        if not etkin:
            return None
        bas, son, etiket, sayfa = etkin[-1]
        sol = 1.0 if t < son else 1 - (t - son) / SOLMA_SN
        if sol <= 0:
            return None
        n, yazili = int((t - bas) * YAZMA_HIZI), []
        for satir in sayfa:
            if n <= 0:
                break
            yazili.append(satir[:n])
            n -= len(satir)
        return (etiket, yazili, sol) if yazili else None

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

    def _golgeli(self, img: Image.Image) -> np.ndarray:
        """Kutusuz okunurluk: yazının arkasına yumuşak, bulanık koyu iz (17 Kasım 2026 tasarımı)."""
        a = img.split()[3].filter(ImageFilter.GaussianBlur(max(1.0, 4 * self.o))).point(lambda v: int(v * 0.8))
        golge = Image.new("RGBA", img.size, (0, 0, 0, 0))
        golge.putalpha(a)
        return np.asarray(Image.alpha_composite(golge, img), np.float32) / 255

    def _ust_sol(self) -> tuple[int, int, np.ndarray]:
        """Sol üst: halka-7 işareti (profil.png'nin dili), kanal adı, görev, cismin gerçek veri satırı, ARTIST'S
        IMPRESSION (G9: görsel bir çizimdir, dünya gerçektir). Üst UST_GUVENLI'nin altında başlar."""
        o, b = self.o, self.bilgi
        x0, y0 = int(40 * o), int(math.ceil(self.H * UST_GUVENLI))
        img, d = self._parca(1100 * o, 180 * o)

        def L(x, y):  # 1080p mutlak -> parça
            return x * o - x0, y * o - y0

        vurgu, yazi, ikincil = (rgb(self.palet[k]) for k in ("vurgu", "yazi", "yazi_ikincil"))
        cx, cy = L(98, 138)
        r = 26 * o
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*vurgu, 255), width=max(1, int(2.2 * o)))
        aci = math.radians(-40)
        px, py, n = cx + r * math.cos(aci), cy + r * math.sin(aci), max(1.0, 3.7 * o)
        d.ellipse([px - n, py - n, px + n, py + n], fill=(*vurgu, 255))
        f7 = _font(max(1, int(30 * o)), True)
        d.text((cx - f7.getlength("7") / 2, cy - r * 0.86), "7", font=f7, fill=(*vurgu, 255))
        _aralikli(d, L(142, 116), "DEEP SPACE LOG", _font(int(24 * o), True), yazi, 0.97, 0.16)
        gorev = f"MISSION {b['gorev_no']:03d}  ·  {str(b.get('gorev_ad') or b['hedef']).upper()}"
        _aralikli(d, L(142, 148), gorev, _font(int(YAZI["etiket"] * o)), vurgu, 0.95, 0.14)
        y = 206
        if b.get("kisa"):
            _aralikli(d, L(72, y), b["kisa"].upper(), _font(int(YAZI["etiket"] * o)), ikincil, 0.92, 0.06)
            y += 34
        _aralikli(d, L(72, y), "ARTIST'S IMPRESSION", _font(int(YAZI["etiket"] * o)), ikincil, 0.55, 0.08)
        return x0, y0, self._golgeli(img)

    def _rota_kur(self) -> tuple[int, int, np.ndarray]:
        """Sağ kenarda Dock rotası (G14, sahibinin isteği: "mouse gelince büyüyor ya öyle"): o anki durak `NOW ·
        NN/20`, büyük ve parlak, altında SONG TITLE ve şarkı adı; ±1 durak şarkı adıyla, sıradaki NEXT etiketiyle;
        ±4 durağa kadar küçülür ve solar. Parça boyunca değişmez, bir kez çizilir."""
        o, W, H, b = self.o, self.W, self.H, self.bilgi
        rota = [list(x) for x in (b.get("rota") or [])]
        simdi = b.get("parca_no", 1) - 1
        if not (0 <= simdi < len(rota)):
            rota, simdi = [[b["ad"], b.get("sarki", "")]], 0
        vurgu, yazi, ikincil = (rgb(self.palet[k]) for k in ("vurgu", "yazi", "yazi_ikincil"))
        f_et = _font(int(YAZI["etiket"] * o), True)
        f_ince = _font(int(YAZI["etiket"] * o))

        def yuk(f, ornek="AQ"):
            k = f.getbbox(ornek)
            return k[3] - k[1]

        bloklar = []  # (i, uzaklık, [(tür, font, yükseklik)])
        for i in range(max(0, simdi - 4), min(len(rota), simdi + 5)):
            k = abs(i - simdi)
            boy, sboy, _, _ = ROTA_OLCEK[k]
            sarki = rota[i][1] if sboy else ""
            satir = []
            if k == 0:
                satir += [("now", f_et, yuk(f_et)), ("bos", None, 8 * o)]
            fa = _font(int(boy * o), k <= 1)
            satir.append(("ad", fa, yuk(fa)))
            if sarki:
                fs = _sarki_font(max(1, int(sboy * o)))
                if k == 0:
                    satir += [("bos", None, 12 * o), ("etiket", f_ince, yuk(f_ince, "SONG")), ("bos", None, 9 * o)]
                else:
                    satir.append(("bos", None, 4 * o))
                satir.append(("sarki", fs, yuk(fs, "Rgy")))
            bloklar.append((i, k, satir))
        ara = ROTA_ARA * o
        boylar = [sum(h for _, _, h in st) for _, _, st in bloklar]
        ust_toplam = sum(h + ara for (i, _, _), h in zip(bloklar, boylar) if i < simdi)
        simdi_h = boylar[[i for i, _, _ in bloklar].index(simdi)]
        y_bas = ROTA_MERKEZ * H - simdi_h / 2 - ust_toplam
        toplam = sum(boylar) + ara * (len(bloklar) - 1)
        alt_sinir, ust_sinir = H * (1 - ALT_GUVENLI) - 40 * o, H * UST_GUVENLI + 80 * o  # saatin altı
        y_bas = min(max(y_bas, ust_sinir), alt_sinir - toplam)
        x0 = int(W - 760 * o)
        xc = W - 80 * o - x0
        xr = xc - 34 * o
        pad = int(40 * o)
        y0 = int(max(H * UST_GUVENLI, y_bas - pad))
        img, d = self._parca(W - x0, alt_sinir + pad - y0)
        noktalar, y = [], y_bas - y0
        for (i, k, satir), h in zip(bloklar, boylar):
            _, _, opak, nr = ROTA_OLCEK[k]
            ad, sarki = rota[i]
            yy = y
            for tur, f, sh in satir:
                if tur == "now":
                    _aralikli(d, (xr, yy - f.getbbox("NOW")[1]), f"NOW  ·  {i + 1:02d}/{len(rota):02d}", f, vurgu,
                              1.0, 0.16, sag=True)
                elif tur == "ad":
                    ust = yy - f.getbbox("A")[1]
                    g = _aralikli(d, (xr, ust), ad.upper(), f, yazi, opak, 0.08, sag=True)
                    if i == simdi + 1:
                        _aralikli(d, (xr - g - 18 * o, ust + (f.size - f_et.size) / 2 + 2 * o), "NEXT", f_et, vurgu,
                                  1.0, 0.16, sag=True)
                    noktalar.append((i, yy + sh / 2, nr * o, opak))
                elif tur == "etiket":
                    _aralikli(d, (xr, yy - f.getbbox("SONG")[1]), "SONG TITLE", f, ikincil, 0.65, 0.06, sag=True)
                elif tur == "sarki":
                    d.text((xr - f.getlength(sarki), yy - f.getbbox("R")[1]), sarki, font=f,
                           fill=(*yazi, int(255 * (1.0 if k == 0 else opak))))
                yy += sh
            y += h + ara
        if len(noktalar) > 1:
            ust, alt = noktalar[0][1] - 24 * o, noktalar[-1][1] + 24 * o
            simdi_y = [n[1] for n in noktalar if n[0] == simdi][0]
            d.line([(xc, ust), (xc, alt)], fill=(*ikincil, 60), width=max(1, int(o)))
            d.line([(xc, ust), (xc, simdi_y)], fill=(*vurgu, 150), width=max(1, int(2 * o)))
        for i, ny, nr, opak in noktalar:
            d.ellipse([xc - nr, ny - nr, xc + nr, ny + nr], fill=(*(vurgu if i <= simdi else ikincil), int(255 * opak)))
        return x0, y0, self._golgeli(img)

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
            boy = kanca_boyu(metin, W, H, int(sb["short_kanca"] * olc))[0]  # plan kapısı sığmayanı reddeder
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

    def _kart_kutusu(self) -> tuple[int, int, int, int]:
        """Sol alttaki cam kartın kutusu (x, y, w, h): bilgi satırları ve altında sinyal; alt kenar oynatıcı
        alanının üstünde (G14-4)."""
        o = self.o
        kw, kh = int(670 * o), int(242 * o)
        return int(48 * o), int(self.H * (1 - ALT_GUVENLI) - 12 * o) - kh, kw, kh

    def _perde(self) -> np.ndarray:
        """Göstergelerin arkasında kenarsız, belli belirsiz koyu perde (G14, 17 Kasım 2026): sabit yazıların (sol üst,
        rota, saat) ve sinyal şeridinin şeklini izleyen yumuşak bulut; parlak zeminde okunurluk verir, koyu zeminde
        fark edilmez. Çeyrek çözünürlükte hesaplanır, parça başına bir kez. Dönüş: 0..PERDE_GUC koyulaşma oranı."""
        W, H, o, q = self.W, self.H, self.o, 4
        A = np.zeros((H, W), np.float32)
        for px, py, p in (self._sabit, self._rota, self._saat_parca(0.0)):
            px, py = max(0, px), max(0, py)
            h, w = min(p.shape[0], H - py), min(p.shape[1], W - px)
            A[py:py + h, px:px + w] = np.maximum(A[py:py + h, px:px + w], p[:h, :w, 3])
        x, y, kw, kh = self._kart_kutusu()
        sy = y + kh - int(70 * o)  # sinyal şeridi (dalga şeridin üst ~%6'sı ile %72'si arasında gezinir)
        A[sy + int(4 * o):sy + int(52 * o), x + int(24 * o):x + kw - int(16 * o)] = 1
        m = Image.fromarray(((A > 0.05) * 255).astype(np.uint8)).resize((max(1, W // q), max(1, H // q)), Image.BOX)
        m = m.point(lambda v: 255 if v else 0)
        m = m.filter(ImageFilter.MaxFilter(max(3, int(round(21 * o / q)) | 1)))
        m = m.filter(ImageFilter.GaussianBlur(34 * o / q)).resize((W, H), Image.BILINEAR)
        return np.clip(np.asarray(m, np.float32) / 255 * 1.8, 0, 1) * PERDE_GUC

    def _cam_kur(self) -> Image.Image:
        """Buzlu cam: kartın arkasındaki görüntü bulanık ve koyu (parça boyunca aynı, bir kez hazırlanır)."""
        x, y, w, h = self._kart_kutusu()
        arka = Image.fromarray((np.clip(self.taban[y:y + h, x:x + w], 0, 1) * 255).astype(np.uint8))
        arka = np.asarray(arka.filter(ImageFilter.GaussianBlur(max(1.0, 20 * self.o))), np.float32)
        koyu = np.array(rgb(self.palet["arka"]), np.float32)
        return Image.fromarray((arka * 0.41 + koyu * 0.59).astype(np.uint8)).convert("RGBA")

    def _kayit_karti(self, etiket: str, satirlar: list[str], sol: float) -> tuple[int, int, np.ndarray]:
        """Sol altta buzlu cam kayıt kartı (sahibinin isteği, 11 Kasım 2026: "şık arka plan, köşede, videoya
        yayılmadan"; 17 Kasım 2026: sinyal kartın altında). İnce çerçeve, solda kehribar çubuk, üstte PROBE-7 ·
        ARRIVAL ya da NEXT etiketi; satırlar yerinde harf harf yazılır."""
        o = self.o
        x, y, kw, kh = self._kart_kutusu()
        img = self._cam.copy()
        img.putalpha(int(255 * sol))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, kw - 1, kh - 1], outline=(*rgb(self.palet["yazi_ikincil"]), int(50 * sol)),
                    width=max(1, int(o)))
        d.line([(24 * o, 24 * o), (24 * o, 174 * o)], fill=(*rgb(self.palet["vurgu"]), int(255 * sol)),
               width=max(1, int(3 * o)))
        _aralikli(d, (50 * o, 24 * o), f"PROBE-7  ·  {etiket}", _font(int(YAZI["etiket"] * o), True),
                  rgb(self.palet["vurgu"]), sol, 0.16)
        f = _font(int(YAZI["kayit"] * o))
        for j, metin in enumerate(satirlar):
            _aralikli(d, (50 * o, (64 + 36 * j) * o), metin, f, rgb(self.palet["yazi"]), 0.97 * sol, 0.02)
        return x, y, np.asarray(img, np.float32) / 255

    def _sinyal(self, i: int) -> tuple[int, int, np.ndarray]:
        """Kartın altında müziğin spektrumundan kehribar sinyal çizgisi (3x çizilip küçültülür: kenarlar yumuşak)."""
        o = self.o
        x, y, kw, kh = self._kart_kutusu()
        gh, k = int(70 * o), 3
        sp = self.muzik["spektrum"][min(i, len(self.muzik["spektrum"]) - 1)]
        img = Image.new("RGBA", (kw * k, gh * k), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        sol_x, sag_x = 24 * o * k, (kw - 16 * o) * k
        xs = np.linspace(sol_x, sag_x, 200)
        ince = np.convolve(np.interp(xs, np.linspace(sol_x, sag_x, len(sp)), sp), np.ones(5) / 5, mode="same")
        taban_y, tepe = gh * k * 0.72, 46 * o * k
        d.line([(float(a), float(taban_y - v * tepe)) for a, v in zip(xs, ince)],
               fill=(*rgb(self.palet["vurgu"]), 215), width=max(1, int(2.2 * k * o)), joint="curve")
        img = img.resize((kw, gh), Image.LANCZOS)
        return x, y + kh - gh, self._golgeli(img)

    def _saat_parca(self, t: float) -> tuple[int, int, np.ndarray]:
        """Sağ üstte görev saati (saniyede bir yeniden çizilir)."""
        s = int(self.t0 + t)
        if self._saat[0] != s:
            o = self.o
            gw, gh = int(420 * o), int(56 * o)
            img, d = self._parca(gw, gh)
            f = _font(int(26 * o), True)
            _aralikli(d, (gw - 8 * o, 8 * o), f"T+{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}", f,
                      rgb(self.palet["yazi"]), 0.97, 0.06, sag=True)
            self._saat = (s, (int(self.W - 72 * o - gw + 8 * o), int(110 * o), self._golgeli(img)))
        return self._saat[1]

    def _hud(self, t: float, i: int) -> list[tuple[int, int, np.ndarray]]:
        if self.dikey:
            return [self._sabit, self._dikey_alt(i)]
        sonuk = 1.0 if t < ACIK_SN else max(SONUK, 1 - (t - ACIK_SN) / 5 * (1 - SONUK))
        parcalar = [self._sabit, self._rota, self._saat_parca(t)]
        # sol alt: kayıt kartı yalnız parça başında (bilgi) ve sonuna yakın (NEXT), G14-4/5; sinyal hep, kartın altında
        kart = self._kart(t)
        kart_parca = None
        if kart:
            etiket, yazili, sol = kart
            satirlar = list(yazili)
            if i % 12 < 6:
                satirlar[-1] += "_"
            kart_parca = self._kayit_karti(etiket, satirlar, sol)
        sinyal = self._sinyal(i)
        if sonuk < 1:  # kart dışındaki arayüz söner (uyku dinleyicisi)
            soluk = []
            for x, y, a in parcalar + [sinyal]:
                a = a.copy()
                a[..., 3] *= sonuk
                soluk.append((x, y, a))
            parcalar, sinyal = soluk[:-1], soluk[-1]
        return parcalar + ([kart_parca] if kart_parca else []) + [sinyal]

    # ---------- kare ----------
    def kare(self, i: int) -> np.ndarray:
        t = i / self.fps
        kare = self.taban.copy()
        once, sonra = self.gecis_agirligi(t)
        if once > 0:
            kare += (self.onceki - kare) * once
        if sonra > 0:
            kare += (self.sonraki - kare) * sonra
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
