"""Sinemagraf: görüntü fotoğraf gibi durur, yalnızca seçilen bölgeler hareket eder (SOZLESME.md G6).

Kamera sabittir. Her parçanın görseline bir hareket tarifi eşlik eder (`gorsel/NN_hareket.json`): hangi bölgede
hangi etki. Bölge = normalize kutu [x0, y0, x1, y1] + yumuşak kenar, istenirse renk/parlaklık/derinlik koşulu ve
"haric" kutuları.

Hareket mantığı (sahibinin kuralı, 9 Kasım 2026): yalnızca gerçekte hareket eden şey hareket eder, ince ve zarif.
Katı nesneler (araç, insan, bina, kaya) asla akmaz ya da bükülmez: onların etrafı "haric" ile korunur; araçta yalnızca
ışık titrer. Toz ve kar az olur.

Etkiler (hepsi döngü süresi L'nin tam katı: kare(0) == kare(L)):
  akis     bulut, sis, su: dokular bir yöne akar (iki fazlı akış, dikiş görünmez)
  salinim  ağaç, bayrak, ot: üst kısım daha çok olmak üzere hafif sallanma
  dalga    buğday, çimen, su yüzeyi: rüzgâr dalgası bölge boyunca ilerler
  parilti  ışıklar, şehir ışıkları, halka: parlak noktalar titreşir ya da nefes alır
  kar      yavaşça düşen kar/toz taneleri
  yildiz   karanlık gökte yıldız pırıltısı
  donme    gezegen: yüzey küre gibi yavaşça döner (merkez, yarıçap verilir; iki fazlı, dikişsiz)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

TAU = 2 * math.pi


def _kapla(img: Image.Image, w: int, h: int) -> Image.Image:
    oran = max(w / img.width, h / img.height)
    yeni = img.resize((math.ceil(img.width * oran), math.ceil(img.height * oran)), Image.LANCZOS)
    x, y = (yeni.width - w) // 2, (yeni.height - h) // 2
    return yeni.crop((x, y, x + w, y + h))


def tarif_oku(gorsel: Path) -> list[dict] | None:
    yol = gorsel.with_name(gorsel.stem + "_hareket.json")
    return json.loads(yol.read_text(encoding="utf-8"))["bolgeler"] if yol.exists() else None


class Sinemagraf:
    def __init__(self, gorsel: Path, bolgeler: list[dict], W: int = 1920, H: int = 1080, L: float = 60.0,
                 tohum: int = 1, derinlik: np.ndarray | None = None):
        import cv2

        self.cv2 = cv2
        self.W, self.H, self.L = W, H, L
        rng = np.random.default_rng(tohum)
        self.img = np.asarray(_kapla(Image.open(gorsel).convert("RGB"), W, H), np.float32) / 255
        self.derin = None
        if derinlik is not None:
            d = Image.fromarray(np.asarray(derinlik, np.float32), mode="F")
            d = d.resize(Image.open(gorsel).size, Image.BICUBIC)
            self.derin = np.asarray(_kapla(d, W, H), np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        hsv = cv2.cvtColor((self.img * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        self.ton, self.doy = hsv[..., 0] * 2, hsv[..., 1] / 255  # ton 0..360
        self.lum = self.img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        self.bolgeler = [self._hazirla(b, rng) for b in bolgeler]

    # ---------- maske ----------
    def _maske(self, b: dict) -> np.ndarray:
        x0, y0, x1, y1 = b.get("kutu", [0, 0, 1, 1])
        yum = b.get("yumusak", 0.03)
        nx, ny = self.xx / self.W, self.yy / self.H
        mx = np.clip(np.minimum(nx - x0, x1 - nx) / max(yum, 1e-4), 0, 1)
        my = np.clip(np.minimum(ny - y0, y1 - ny) / max(yum * self.W / self.H, 1e-4), 0, 1)
        m = mx * my
        for hx0, hy0, hx1, hy1 in b.get("haric", []):  # katı nesneler (tren, insan, bina) asla bükülmez
            hm = ((nx > hx0) & (nx < hx1) & (ny > hy0) & (ny < hy1)).astype(np.float32)
            hm = self.cv2.GaussianBlur(hm, (0, 0), max(1.0, self.W * 0.004))
            m *= np.clip(1 - hm * 1.5, 0, 1)
        if "parlaklik_min" in b:
            m *= np.clip((self.lum - b["parlaklik_min"]) / 0.08, 0, 1)
        if "parlaklik_max" in b:
            m *= np.clip((b["parlaklik_max"] - self.lum) / 0.08, 0, 1)
        if "doygunluk_min" in b:
            m *= np.clip((self.doy - b["doygunluk_min"]) / 0.1, 0, 1)
        if "ton" in b:  # [merkez, genişlik] derece
            mer, gen = b["ton"]
            fark = np.minimum(np.abs(self.ton - mer), 360 - np.abs(self.ton - mer))
            m *= np.clip(1 - (fark - gen) / 15, 0, 1)
        if self.derin is not None and "derinlik" in b:
            lo, hi = b["derinlik"]
            m *= np.clip((self.derin - lo) / 0.05, 0, 1) * np.clip((hi - self.derin) / 0.05, 0, 1)
        return self.cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(1.0, self.W * 0.002))

    def _hazirla(self, b: dict, rng) -> dict:
        b = dict(b)
        b["m"] = self._maske(b)
        olcek = self.W / 1920
        e = b["etki"]
        if e == "akis":
            b["n"] = int(b.get("tekrar", 4))  # döngüde kaç akış periyodu
            b["vx"], b["vy"] = (np.array(b.get("yon", [1, 0]), np.float32) * b.get("hiz", 6) * olcek)
        elif e == "donme":
            cx, cy = b["merkez"]
            R = b["yaricap"] * self.W
            nx = (self.xx - cx * self.W) / R
            ny = (self.yy - cy * self.H) / R
            r2 = nx ** 2 + ny ** 2
            ic = np.clip((1 - r2) / 0.02, 0, 1)  # disk içi
            nz = np.sqrt(np.clip(1 - r2, 0, 1))
            b["lat_cos"] = np.sqrt(np.clip(1 - ny ** 2, 1e-6, 1)).astype(np.float32)
            b["lon"] = np.arctan2(nx, nz).astype(np.float32)
            b["cxp"], b["R"] = cx * self.W, R
            kenar = np.clip((1 - np.sqrt(np.clip(r2, 0, 1))) / 0.06, 0, 1)  # kenara yakın daha az kayar
            b["m"] = (b["m"] * ic * kenar).astype(np.float32)
            b["n"] = int(b.get("tekrar", 6))
            b["w"] = math.radians(b.get("hiz", 1.0))  # derece/sn
        elif e == "parilti":
            # yumuşak faz alanı: komşu ışıklar birlikte, uzaktakiler farklı zamanda titreşir (blok görünmez)
            g = rng.random((self.H // 24 + 2, self.W // 24 + 2)).astype(np.float32)
            g = self.cv2.resize(g, (self.W, self.H), interpolation=self.cv2.INTER_CUBIC)
            b["faz"] = (g * TAU * 3).astype(np.float32)
        elif e in ("kar", "yildiz"):
            adet = int(b.get("adet", 220 if e == "kar" else 160))
            x0, y0, x1, y1 = b.get("kutu", [0, 0, 1, 1])
            b["px"] = rng.uniform(x0 * self.W, x1 * self.W, adet).astype(np.float32)
            b["py"] = rng.uniform(y0 * self.H, y1 * self.H, adet).astype(np.float32)
            b["faz"] = rng.uniform(0, TAU, adet).astype(np.float32)
            b["k"] = rng.integers(1, 4, adet)
            b["boy"] = (rng.uniform(0.6, 1.8, adet) * olcek).astype(np.float32)
            if e == "yildiz":
                aday = b["m"][b["py"].astype(int).clip(0, self.H - 1), b["px"].astype(int).clip(0, self.W - 1)]
                b["boy"] = b["boy"] * (aday > 0.3)
        return b

    # ---------- etkiler ----------
    def kare(self, t: float) -> np.ndarray:
        cv2 = self.cv2
        t = t % self.L
        th = TAU * t / self.L
        dx = np.zeros((self.H, self.W), np.float32)
        dy = np.zeros((self.H, self.W), np.float32)
        for b in self.bolgeler:
            m = b["m"]
            if b["etki"] == "salinim":  # üst kısım daha çok: kutunun altından üstüne artan genlik
                x0, y0, x1, y1 = b.get("kutu", [0, 0, 1, 1])
                h = np.clip((y1 - self.yy / self.H) / max(y1 - y0, 1e-3), 0, 1) ** 1.5
                a = b.get("genlik", 2.0) * self.W / 1920
                f = int(b.get("tekrar", 6))
                dx += m * h * a * (np.sin(f * th + self.yy * 0.01) + 0.35 * np.sin(2 * f * th + self.xx * 0.02))
            elif b["etki"] == "dalga":
                a = b.get("genlik", 1.6) * self.W / 1920
                f = int(b.get("tekrar", 8))
                lam = b.get("dalga_boyu", 0.18) * self.W
                faz = TAU * (self.xx / lam + self.yy / (lam * 3)) - f * th
                dx += m * a * np.sin(faz)
                dy += m * a * 0.5 * np.cos(faz * 1.3)
        kare = cv2.remap(self.img, self.xx + dx, self.yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        for b in self.bolgeler:
            m = b["m"][..., None]
            if b["etki"] == "akis":  # iki fazlı akış: biri sıfırlanırken diğeri tam görünür
                T = self.L / b["n"]
                p1 = (t % T) / T
                p2 = ((t + T / 2) % T) / T
                yer = []
                for p in (p1, p2):
                    ox, oy = b["vx"] * T * (p - 0.5), b["vy"] * T * (p - 0.5)
                    yer.append(cv2.remap(self.img, self.xx - ox, self.yy - oy, cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_REFLECT))
                w1 = 1 - abs(2 * p1 - 1)
                akan = yer[0] * w1 + yer[1] * (1 - w1)
                kare = kare * (1 - m) + akan * m
            elif b["etki"] == "donme":  # boylam kayar: x' = cx + R*cos(enlem)*sin(boylam - delta)
                T = self.L / b["n"]
                p1 = (t % T) / T
                p2 = ((t + T / 2) % T) / T
                yer = []
                for p in (p1, p2):
                    delta = b["w"] * T * (p - 0.5)
                    lon = np.clip(b["lon"] - delta, -math.pi / 2, math.pi / 2)
                    sx = b["cxp"] + b["R"] * b["lat_cos"] * np.sin(lon)
                    yer.append(cv2.remap(self.img, sx.astype(np.float32), self.yy, cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_REFLECT))
                w1 = 1 - abs(2 * p1 - 1)
                donen = yer[0] * w1 + yer[1] * (1 - w1)
                kare = kare * (1 - m) + donen * m
            elif b["etki"] == "parilti":
                f = int(b.get("tekrar", 12))
                g = b.get("guc", 0.35)
                nabiz = 1 + g * np.sin(f * th + b["faz"])[..., None]
                kare = kare * (1 - m) + np.clip(kare * nabiz, 0, 1) * m
            elif b["etki"] in ("kar", "yildiz"):
                if b["etki"] == "kar":  # düşerken hafifçe sağa sola salınır; döngüde tam sayıda düşüş
                    n = int(b.get("tekrar", 2))
                    px = (b["px"] + 6 * np.sin(b["k"] * th + b["faz"])) % self.W
                    py = (b["py"] + self.H * n * t / self.L) % self.H
                    parlak = np.full_like(px, b.get("parlaklik", 0.55))
                else:
                    px, py = b["px"], b["py"]
                    parlak = np.clip(np.sin(b["k"] * th + b["faz"]), 0, 1) ** 3 * b.get("parlaklik", 0.6)
                for x, y, boy, p in zip(px, py, b["boy"], parlak):
                    if boy <= 0 or p <= 0.01:
                        continue
                    r = int(boy * 2.5) + 1
                    xa, xb = max(0, int(x) - r), min(self.W, int(x) + r + 1)
                    ya, yb = max(0, int(y) - r), min(self.H, int(y) + r + 1)
                    if xa >= xb or ya >= yb:
                        continue
                    yy, xx = np.mgrid[ya:yb, xa:xb]
                    gl = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * boy * boy)).astype(np.float32) * p
                    kare[ya:yb, xa:xb] += gl[..., None] * np.array([1.0, 0.97, 0.92], np.float32)
        return (np.clip(kare, 0, 1) * 255).astype(np.uint8)
