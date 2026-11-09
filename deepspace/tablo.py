"""Canlı tablo: tek bir durağan görseli kusursuz dönen, derinlikli bir sahneye çevirir (SOZLESME.md G6).

Görsel nereden gelirse gelsin (yapay zekâ, teleskop fotoğrafı, çizim) aynı hareket dili uygulanır:
- arka plan çok yavaş nefes alır (yakınlaşma) ve küçük bir daire çizer,
- ön plan katmanı varsa (NN_on.png, şeffaf) daha az hareket eder: iki katmanlı derinlik (parallax),
- karanlık bölgelerde yıldızlar pırıldar, önde yumuşak toz zerreleri süzülür.
Bütün hareketler döngü süresi L'nin tam katıdır: kare(0) == kare(L).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image

TAU = 2 * math.pi


def _kapla(img: Image.Image, w: int, h: int) -> Image.Image:
    """Görseli en-boy oranını bozmadan (w, h) alanını kaplayacak şekilde ölçekleyip ortadan kırpar."""
    oran = max(w / img.width, h / img.height)
    yeni = img.resize((math.ceil(img.width * oran), math.ceil(img.height * oran)), Image.LANCZOS)
    x, y = (yeni.width - w) // 2, (yeni.height - h) // 2
    return yeni.crop((x, y, x + w, y + h))


class Tablo:
    def __init__(self, gorsel: Path, W: int = 1920, H: int = 1080, L: float = 60.0, tohum: int = 1,
                 on_plan: Path | None = None, nefes: float = 0.03, yildiz: int = 140, toz: int = 60):
        self.W, self.H, self.L = W, H, L
        rng = np.random.default_rng(tohum)
        self.pay = 1.10  # kaynak, çıktıdan %10 büyük tutulur: hareket için boşluk
        self.SW, self.SH = int(W * self.pay), int(H * self.pay)
        self.arka = _kapla(Image.open(gorsel).convert("RGB"), self.SW, self.SH)
        self.on = None
        if on_plan and Path(on_plan).exists():
            self.on = _kapla(Image.open(on_plan).convert("RGBA"), self.SW, self.SH)
        self.nefes = nefes
        self.faz = rng.uniform(0, TAU)

        # pırıltı: kaynaktaki karanlık noktalara yerleşir, arka planla birlikte hareket eder
        kucuk = np.asarray(self.arka.resize((self.SW // 8, self.SH // 8)).convert("L"), np.float32) / 255
        aday = np.argwhere(kucuk < 0.22)
        if self.on is not None:
            alfa = np.asarray(self.on.split()[3].resize((self.SW // 8, self.SH // 8)), np.float32) / 255
            aday = np.array([a for a in aday if alfa[a[0], a[1]] < 0.1]) if len(aday) else aday
        secim = aday[rng.choice(len(aday), min(yildiz, len(aday)), replace=False)] if len(aday) else np.zeros((0, 2))
        self.y_src = (secim[:, 0] * 8 + rng.uniform(0, 8, len(secim))).astype(np.float32)
        self.x_src = (secim[:, 1] * 8 + rng.uniform(0, 8, len(secim))).astype(np.float32)
        self.y_k = rng.integers(1, 4, len(secim))
        self.y_faz = rng.uniform(0, TAU, len(secim)).astype(np.float32)
        self.y_parlak = (rng.uniform(0.3, 1.0, len(secim)) ** 2).astype(np.float32)

        # toz zerreleri: ekranda küçük dairelerde süzülür
        self.t_x = rng.uniform(0, W, toz).astype(np.float32)
        self.t_y = rng.uniform(0, H, toz).astype(np.float32)
        self.t_r = rng.uniform(0.01, 0.035, toz).astype(np.float32) * min(W, H)
        self.t_k = rng.choice([-1, 1], toz) * rng.integers(1, 3, toz)
        self.t_faz = rng.uniform(0, TAU, toz).astype(np.float32)
        self.t_boy = rng.uniform(1.0, 3.2, toz).astype(np.float32) * (min(W, H) / 1080)
        self.t_parlak = rng.uniform(0.04, 0.16, toz).astype(np.float32)
        self.isik = np.array([1.0, 0.95, 0.88], np.float32)

    def _donusum(self, t: float, carpan: float) -> tuple[float, float, float]:
        """(ölçek k, x0, y0): çıktı pikseli (x, y) -> kaynak (k*x + x0, k*y + y0)."""
        th = TAU * t / self.L + self.faz
        zoom = 1.0 + (self.pay - 1) * 0.5 + self.nefes * carpan * math.sin(th)
        zoom = min(max(zoom, 1.0 + 1e-3), self.pay - 1e-3)
        gor_w = self.SW / zoom
        k = gor_w / self.W
        bos_x = (self.SW - gor_w) / 2
        bos_y = (self.SH - self.H * k) / 2
        dx = bos_x * 0.45 * carpan * math.cos(th)
        dy = bos_y * 0.45 * carpan * math.sin(th)
        return k, bos_x + dx, bos_y + dy

    def _arka_plan(self, t: float, k: float, x0: float, y0: float) -> np.ndarray:
        bg = self.arka.transform((self.W, self.H), Image.AFFINE, (k, 0, x0, 0, k, y0), resample=Image.BILINEAR)
        if self.on is not None:
            k2, x2, y2 = self._donusum(t, 0.35)
            fg = self.on.transform((self.W, self.H), Image.AFFINE, (k2, 0, x2, 0, k2, y2), resample=Image.BILINEAR)
            bg = bg.convert("RGBA")
            bg.alpha_composite(fg)
            bg = bg.convert("RGB")
        return np.asarray(bg, np.float32) / 255

    def kare(self, t: float) -> np.ndarray:
        t = t % self.L
        k, x0, y0 = self._donusum(t, 1.0)
        kare = self._arka_plan(t, k, x0, y0)
        th = TAU * t / self.L

        # pırıltı (arka planla aynı dönüşüm)
        if len(self.x_src):
            px = (self.x_src - x0) / k
            py = (self.y_src - y0) / k
            p = self.y_parlak * np.clip(np.sin(self.y_k * th + self.y_faz), 0, 1) ** 3 * 0.55
            ic = (px > 2) & (px < self.W - 3) & (py > 2) & (py < self.H - 3) & (p > 0.01)
            xi, yi, pp = px[ic].astype(np.int32), py[ic].astype(np.int32), p[ic]
            kare[yi, xi] += pp[:, None]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                kare[yi + dy, xi + dx] += (pp * 0.35)[:, None]

        # toz (yumuşak, önde)
        tx = (self.t_x + self.t_r * np.cos(self.t_k * th + self.t_faz)) % self.W
        ty = (self.t_y + self.t_r * np.sin(self.t_k * th + self.t_faz)) % self.H
        for x, y, boy, parlak in zip(tx, ty, self.t_boy, self.t_parlak):
            r = int(boy * 2.5) + 1
            xa, xb = max(0, int(x) - r), min(self.W, int(x) + r + 1)
            ya, yb = max(0, int(y) - r), min(self.H, int(y) + r + 1)
            if xa >= xb or ya >= yb:
                continue
            yy, xx = np.mgrid[ya:yb, xa:xb]
            g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * boy * boy)).astype(np.float32) * parlak
            kare[ya:yb, xa:xb] += g[..., None] * self.isik
        return (np.clip(kare, 0, 1) * 255).astype(np.uint8)


class Tablo3D(Tablo):
    """3D fotoğraf efekti: derinlik haritasıyla yakın ve uzak katmanlar farklı hızda kayar (gerçek kamera hissi).

    Kamera çok yavaş bir elips çizer; derinliği odak düzleminden (`odak`) büyük olan yerler (ön plan) bir yöne,
    küçük olanlar (gökyüzü, gezegen) öbür yöne kayar. Uzak bölgelerde ince bir sis katmanı süzülür.
    Hepsi L'nin tam katı: kare(0) == kare(L).
    """

    def __init__(self, gorsel: Path, derinlik: np.ndarray, W: int = 1920, H: int = 1080, L: float = 60.0,
                 tohum: int = 1, genlik: float = 0.012, odak: float = 0.35, sis: float = 0.10, **kw):
        import cv2

        super().__init__(gorsel, W, H, L, tohum, nefes=0.012, **kw)
        src = Image.open(gorsel)
        d = Image.fromarray(np.asarray(derinlik, np.float32), mode="F").resize(src.size, Image.BICUBIC)
        oran = max(self.SW / d.width, self.SH / d.height)
        d = d.resize((math.ceil(d.width * oran), math.ceil(d.height * oran)), Image.BICUBIC)
        x, y = (d.width - self.SW) // 2, (d.height - self.SH) // 2
        d = np.asarray(d.crop((x, y, x + self.SW, y + self.SH)), np.float32)
        # kenar halesini azalt: yakın nesneleri biraz genişlet, sonra yumuşat
        cek = max(3, int(self.SW * 0.004)) | 1
        d = cv2.GaussianBlur(cv2.dilate(d, np.ones((cek, cek), np.uint8)), (0, 0), self.SW * 0.003)
        self.derin = d
        self.arka_np = np.asarray(self.arka, np.float32) / 255
        self.genlik, self.odak = genlik, odak
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        # sis: x'te periyodik bulut dokusu, döngü başına bir genişlik kayar
        from .sahne import _dongulu_fbm
        rng = np.random.default_rng(tohum + 7)
        self.sis_doku = _dongulu_fbm(max(64, H // 4), max(128, W // 4), rng, oktav=5, taban=3)
        self.sis = sis

    def _arka_plan(self, t: float, k: float, x0: float, y0: float) -> np.ndarray:
        import cv2

        th = TAU * t / self.L + self.faz
        ox = self.genlik * self.SW * math.cos(th)
        oy = self.genlik * 0.5 * self.SH * math.sin(th)
        mx = self.xx * k + x0
        my = self.yy * k + y0
        d = cv2.remap(self.derin, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        kayma = d - self.odak
        mx = mx - kayma * ox
        my = my - kayma * oy
        kare = cv2.remap(self.arka_np, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if self.sis:
            sh, sw = self.sis_doku.shape
            kay = int(round(sw * (t % self.L) / self.L))
            doku = np.roll(self.sis_doku, -kay, axis=1)
            doku = cv2.resize(doku, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
            uzak = np.clip(1.0 - d * 1.6, 0, 1)  # sis uzak ve orta mesafede
            a = (np.clip(doku - 0.45, 0, 1) * 1.8 * self.sis * uzak)[..., None]
            kare = kare * (1 - a) + np.array([1.0, 0.93, 0.82], np.float32) * a
        return kare
