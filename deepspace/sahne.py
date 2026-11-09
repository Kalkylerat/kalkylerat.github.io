"""Sahne üreteci: her parça için kodla çizilen, kusursuz dönen uzay sahnesi (SOZLESME.md G6).

Her hareket döngü süresi L'nin tam katına bağlıdır, yani kare(0) == kare(L). 40 sn'lik döngü bir saat boyunca
tekrarlansa da dikiş görünmez. Ücretli hiçbir servis kullanılmaz: numpy ile çizilir, ffmpeg ile kodlanır.

Türler: kayalik, gaz, buz, lav, okyanus, yildiz (dev yıldız), pulsar, kuasar. Renkler görevin paletinden gelir.
"""
from __future__ import annotations

import math
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TAU = 2 * math.pi
TURLER = ("kayalik", "gaz", "buz", "lav", "okyanus", "yildiz", "pulsar", "kuasar")


def renk(hexs: str) -> np.ndarray:
    hexs = hexs.lstrip("#")
    return np.array([int(hexs[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255


def _fbm(h: int, w: int, rng: np.random.Generator, oktav: int = 6, taban: int = 4) -> np.ndarray:
    """Yumuşak bulut gürültüsü (döngüsel değil; nebula gibi kaydırılan katmanlar için)."""
    out = np.zeros((h, w), np.float32)
    genlik, toplam = 1.0, 0.0
    for o in range(oktav):
        gh, gw = max(2, taban * 2 ** o * h // w), taban * 2 ** o
        izgara = Image.fromarray((rng.random((gh, gw)) * 255).astype(np.uint8))
        out += genlik * np.asarray(izgara.resize((w, h), Image.BICUBIC), np.float32) / 255
        toplam += genlik
        genlik *= 0.5
    out /= toplam
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def _dongulu_doku(h: int, w: int, rng: np.random.Generator, terim: int = 48, cozgu: float = 0.0,
                  yatay: float = 1.0) -> np.ndarray:
    """x yönünde w genişliğinde tam periyodik doku: tam sayı frekanslı sinüslerin toplamı (+ alan bükme)."""
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, w, endpoint=False, dtype=np.float32)[None, :]
    bukme = np.zeros((h, w), np.float32)
    if cozgu:
        for _ in range(12):
            kx, ky = int(rng.integers(1, 5)), float(rng.uniform(0.5, 4))
            bukme += np.sin(TAU * (kx * x + ky * y) + rng.uniform(0, TAU)).astype(np.float32)
        bukme *= cozgu / 12
    out = np.zeros((h, w), np.float32)
    for _ in range(terim):
        f = float(rng.uniform(0, 1)) ** 2
        kx = int(round((1 + f * 23) * yatay)) * int(rng.choice([-1, 1]))
        ky = float(1 + f * 30)
        out += (1 / (1 + f * 12)) * np.sin(TAU * (kx * (x + bukme) + ky * y) + rng.uniform(0, TAU))
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def _dongulu_fbm(h: int, w: int, rng: np.random.Generator, oktav: int = 6, taban: int = 4,
                 kalicilik: float = 0.55) -> np.ndarray:
    """x yönünde tam periyodik bulut gürültüsü: yan yana üç kopya ızgara büyütülür, ortadaki kopya alınır."""
    out = np.zeros((h, w), np.float32)
    genlik, toplam = 1.0, 0.0
    for o in range(oktav):
        gw = taban * 2 ** o
        gh = max(2, gw * h // w * 2)
        izgara = rng.random((gh, gw)).astype(np.float32)
        uclu = np.tile(izgara, (1, 3))
        buyuk = np.asarray(Image.fromarray(uclu, mode="F").resize((3 * w, h), Image.BICUBIC), np.float32)
        out += genlik * buyuk[:, w:2 * w]
        toplam += genlik
        genlik *= kalicilik
    out /= toplam
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def _karisim(t: np.ndarray, renkler: list[np.ndarray]) -> np.ndarray:
    """0..1 değerini renk geçişine çevirir."""
    n = len(renkler) - 1
    i = np.clip((t * n).astype(int), 0, n - 1)
    f = (t * n - i)[..., None]
    r = np.stack(renkler)
    return r[i] * (1 - f) + r[i + 1] * f


@lru_cache(maxsize=4)
def probe_sprite(boy: int) -> tuple[np.ndarray, np.ndarray]:
    """PROBE-7: sakin, küçük bir sonda. (renk, alfa) olarak döner; ışık ayrıca yanıp söner."""
    s = 4
    W, H = boy * 2 * s, boy * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2 + H // 10
    gv = boy * s // 5
    # güneş panelleri
    for yon in (-1, 1):
        x0 = cx + yon * int(gv * 0.9)
        x1 = cx + yon * int(gv * 4.2)
        a, b = sorted((x0, x1))
        d.rectangle([a, cy - gv * 0.55, b, cy + gv * 0.55], fill=(38, 62, 104, 255), outline=(150, 170, 200, 255),
                    width=s * 2)
        for k in range(1, 4):
            xx = a + (b - a) * k / 4
            d.line([xx, cy - gv * 0.55, xx, cy + gv * 0.55], fill=(110, 135, 175, 255), width=s)
        d.line([cx + yon * gv * 0.6, cy, x0, cy], fill=(170, 170, 170, 255), width=s * 2)
    # gövde (altın folyo)
    d.rounded_rectangle([cx - gv * 0.7, cy - gv * 0.8, cx + gv * 0.7, cy + gv * 0.8], radius=s * 4,
                        fill=(196, 160, 82, 255), outline=(235, 210, 150, 255), width=s * 2)
    d.line([cx - gv * 0.7, cy, cx + gv * 0.7, cy], fill=(160, 125, 60, 255), width=s)
    # çanak anten
    d.line([cx, cy - gv * 0.8, cx, cy - gv * 1.35], fill=(200, 200, 200, 255), width=s * 2)
    d.ellipse([cx - gv * 0.75, cy - gv * 1.75, cx + gv * 0.75, cy - gv * 1.25], fill=(225, 228, 235, 255),
              outline=(150, 155, 165, 255), width=s * 2)
    img = img.resize((W // s, H // s), Image.LANCZOS)
    a = np.asarray(img, np.float32) / 255
    return a[..., :3].copy(), a[..., 3:].copy()


class Sahne:
    """Bir parçanın sahnesi. kare(t) -> HxWx3 uint8. Tüm hareketler L saniyede bir başa döner."""

    def __init__(self, parca: dict, tohum: int, W: int = 1920, H: int = 1080, L: float = 40.0,
                 yerlesim: str | None = None, olcek: float = 1.0, probe: bool = True):
        self.W, self.H, self.L = W, H, L
        self.tur = parca.get("tur", "kayalik")
        if self.tur not in TURLER:
            raise ValueError(f"bilinmeyen gezegen türü: {self.tur}")
        rng = np.random.default_rng(tohum)
        palet = [renk(c) for c in parca["palet"]]
        while len(palet) < 4:
            palet.append(palet[-1])
        self.palet = palet
        kisa = min(W, H)

        # arka plan: koyu radyal geçiş
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.hypot((xx - W / 2) / kisa, (yy - H / 2) / kisa)
        self.arka = (palet[0][None, None, :] * (1.0 - 0.55 * np.clip(r, 0, 1))[..., None]).astype(np.float32)
        self.vinyet = (1 - 0.45 * np.clip(r - 0.35, 0, 1) ** 1.5)[..., None].astype(np.float32)

        # nebula: daire çizerek kayan büyük bulut katmanı
        self.neb_r = int(kisa * 0.06)
        nh, nw = H + 2 * self.neb_r + 2, W + 2 * self.neb_r + 2
        n1, n2 = _fbm(nh, nw, rng), _fbm(nh, nw, rng, taban=3)
        yogun = np.clip((n1 - 0.45) * 2.2, 0, 1) ** 1.6 * 0.55
        self.nebula = (_karisim(n2, [palet[1], palet[1] * 0.6 + palet[2] * 0.4, palet[0] * 2]) *
                       yogun[..., None]).astype(np.float32)
        self.neb_faz = rng.uniform(0, TAU)

        # yıldızlar: üç katman, farklı yarıçapla dönerek paralaks
        self.yildiz = []
        for adet, yaricap, parlak in ((int(1100 * W * H / 2e6), 0.012, 0.5), (int(380 * W * H / 2e6), 0.024, 0.8),
                                      (int(90 * W * H / 2e6), 0.04, 1.0)):
            x = rng.uniform(0, W, adet).astype(np.float32)
            y = rng.uniform(0, H, adet).astype(np.float32)
            b = (rng.uniform(0.25, 1, adet) ** 2 * parlak).astype(np.float32)
            k = rng.integers(1, 4, adet)
            faz = rng.uniform(0, TAU, adet).astype(np.float32)
            ton = np.where(rng.random(adet)[:, None] < 0.15, np.array([1.0, 0.85, 0.7]),
                           np.where(rng.random(adet)[:, None] < 0.2, np.array([0.75, 0.85, 1.0]), 1.0))
            self.yildiz.append((x, y, b, k, faz, ton.astype(np.float32), yaricap * kisa))

        # yerleşim
        if yerlesim is None:
            yerlesim = "sol" if rng.random() < 0.5 else "sag"
        self.yerlesim = yerlesim
        konum = {"sol": (0.34, 0.5), "sag": (0.66, 0.5), "orta": (0.5, 0.5), "ust": (0.5, 0.38)}[yerlesim]
        self.cx, self.cy = W * konum[0], H * konum[1]
        self.R = kisa * (0.3 if self.tur not in ("pulsar", "kuasar") else 0.07) * olcek
        isik = np.array([-0.55 if yerlesim != "sol" else 0.55, -0.35, 0.76], np.float32)
        self.isik = isik / np.linalg.norm(isik)

        if self.tur in ("pulsar", "kuasar"):
            self._parlak_kur(rng, yy, xx)
        else:
            self._gezegen_kur(rng, parca)

        self.probe = probe
        self.probe_boy = int(kisa * 0.13)
        self.px, self.py = (W * 0.86, H * 0.8) if W >= H else (W * 0.78, H * 0.86)
        self.probe_k = int(rng.integers(1, 3))

    # ---------- gezegen ----------
    def _gezegen_kur(self, rng, parca):
        R, cx, cy, p = self.R, self.cx, self.cy, self.palet
        x0, x1 = int(max(0, cx - R * 1.25)), int(min(self.W, cx + R * 1.25))
        y0, y1 = int(max(0, cy - R * 1.25)), int(min(self.H, cy + R * 1.25))
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        nx, ny = (xx - cx) / R, (yy - cy) / R
        rr = nx ** 2 + ny ** 2
        disk = rr <= 1.0
        self.ys, self.xs = yy[disk].astype(np.int32), xx[disk].astype(np.int32)
        nz = np.sqrt(np.clip(1 - rr[disk], 0, 1))
        eg = 0.35  # eksen eğikliği
        X, Y, Z = nx[disk], ny[disk], nz
        Y2, Z2 = Y * math.cos(eg) - Z * math.sin(eg), Y * math.sin(eg) + Z * math.cos(eg)
        self.lat = np.arcsin(np.clip(-Y2, -1, 1))
        self.lon = np.arctan2(X, Z2)
        golge = np.clip(X * self.isik[0] + Y * self.isik[1] + nz * self.isik[2], 0, 1)
        self.aydin = (0.035 + 0.965 * golge ** 0.85).astype(np.float32)[:, None]
        self.kenar = (0.55 + 0.45 * nz).astype(np.float32)[:, None]  # kenar kararması

        th, tw = 512, 1024
        self.tw, self.th = tw, th
        self.tekrar = 3
        tur = self.tur
        if tur == "gaz":
            d = _dongulu_fbm(th, tw, rng, oktav=6, taban=3)
            bant = 0.5 + 0.5 * np.sin(np.linspace(0, 1, th, dtype=np.float32)[:, None] * TAU * rng.integers(5, 9)
                                      + d * 4)
            self.doku = _karisim(np.clip(bant * 0.7 + d * 0.3, 0, 1), [p[1], p[2], p[3], p[2]])
        elif tur == "kayalik":
            d = _dongulu_fbm(th, tw, rng, oktav=7)
            self.doku = _karisim(d, [p[1] * 0.5, p[1], p[2], p[3]])
        elif tur == "buz":
            d = _dongulu_fbm(th, tw, rng, oktav=7)
            catlak = np.clip(1 - np.abs(d - 0.5) * 30, 0, 1)
            self.doku = _karisim(d, [p[2] * 0.8, p[3], np.ones(3, np.float32) * 0.95]) * (1 - 0.45 * catlak[..., None])
        elif tur == "lav":
            d = _dongulu_fbm(th, tw, rng, oktav=7)
            catlak = np.clip(1 - np.abs(d - 0.5) * 14, 0, 1) ** 2
            self.doku = _karisim(d, [p[1] * 0.25, p[1] * 0.5, p[1] * 0.35])
            self.isima = (catlak[..., None] * p[3]).astype(np.float32)
        elif tur == "yildiz":  # kendi ışığını veren dev yıldız: gölge yok, kenar kararması güçlü
            d = _dongulu_fbm(th, tw, rng, oktav=7, taban=6)
            self.doku = _karisim(d, [p[1], p[2], p[3], p[3] * 0.5 + 0.5])
            self.aydin = np.ones_like(self.aydin)
            self.kenar = self.kenar ** 2.2
        elif tur == "okyanus":
            d = _dongulu_fbm(th, tw, rng, oktav=7)
            kara = np.clip((d - 0.56) * 6, 0, 1)[..., None]
            self.doku = p[1] * (0.7 + 0.3 * d[..., None]) * (1 - kara) + p[3] * kara
            bulut = _dongulu_fbm(th, tw, rng, oktav=6, taban=6)
            self.bulut = np.clip((bulut - 0.5) * 2.5, 0, 1).astype(np.float32)
        self.doku = self.doku.astype(np.float32)

        # atmosfer halesi (durağan)
        hy, hx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        d = np.hypot(hx - cx, hy - cy) / R
        yon = np.clip(((hx - cx) * self.isik[0] + (hy - cy) * self.isik[1]) / (R * 1.0) + 0.6, 0, 1.3)
        if self.tur == "yildiz":  # her yönde parlayan taç
            self.hale = (np.exp(-np.clip(d - 1, 0, None) * 4) * (d > 0.98) * 0.7)[..., None] * p[3][None, None, :]
        else:
            self.hale = (np.exp(-np.clip(d - 1, 0, None) * 18) * (d > 0.98) * yon * 0.55)[..., None] * \
                (p[2] * 0.6 + 0.4)[None, None, :]
        self.hale = self.hale.astype(np.float32)

        self.halka = parca.get("halka", False)
        if self.halka:
            k = 0.28
            rx = (hx - cx) / R
            ry = (hy - cy) / (R * k)
            rh = np.hypot(rx, ry)
            iz = _dongulu_doku(1, 512, rng, terim=30)[0]
            bant = np.interp(np.clip((rh - 1.25) / 1.1, 0, 1), np.linspace(0, 1, 512), iz)
            alfa = ((rh > 1.25) & (rh < 2.35)) * (0.25 + 0.6 * bant)
            self.halka_on = (alfa * (hy >= cy))[..., None].astype(np.float32)
            self.halka_arka = (alfa * (hy < cy))[..., None].astype(np.float32)
            self.halka_renk = (p[3] * 0.8 + 0.2).astype(np.float32)

    def _orneke(self, doku: np.ndarray, faz: float, tekrar: int) -> np.ndarray:
        u = (self.lon / TAU * tekrar * self.tw + faz) % self.tw
        v = ((self.lat / math.pi + 0.5) * (self.th - 1)).astype(np.int32)
        u0 = u.astype(np.int32) % self.tw
        f = (u - u0)[:, None].astype(np.float32)
        u1 = (u0 + 1) % self.tw
        if doku.ndim == 2:
            return doku[v, u0] * (1 - f[:, 0]) + doku[v, u1] * f[:, 0]
        return doku[v, u0] * (1 - f) + doku[v, u1] * f

    def _gezegen_ciz(self, kare: np.ndarray, t: float):
        faz = self.tw * t / self.L  # döngü başına bir doku genişliği: 1/tekrar tur
        renkler = self._orneke(self.doku, faz, self.tekrar)
        if self.tur == "okyanus":
            b = self._orneke(self.bulut, faz, 2)[:, None]  # bulutlar başka hızda döner, yine periyodik
            renkler = renkler * (1 - b) + 0.95 * b
        renkler = renkler * self.aydin * self.kenar
        if self.tur == "lav":
            nabiz = 0.8 + 0.2 * math.sin(TAU * t / self.L)
            renkler = renkler + self._orneke(self.isima, faz, self.tekrar) * nabiz * (0.6 + 0.4 * self.kenar)
        kare[self.ys, self.xs] = renkler

    # ---------- pulsar / kuasar ----------
    def _parlak_kur(self, rng, yy, xx):
        p = self.palet
        dx, dy = xx - self.cx, yy - self.cy
        r = np.hypot(dx, dy) / self.R
        self.cekirdek = (np.exp(-r * 1.6)[..., None] * (p[3] * 0.7 + 0.3) + np.exp(-r * 0.35)[..., None] *
                         p[2] * 0.25).astype(np.float32)
        self.aci = np.arctan2(dy, dx).astype(np.float32)
        self.r = r.astype(np.float32)
        if self.tur == "kuasar":
            k = 0.3
            ry = dy / k
            rd = np.hypot(dx, ry) / self.R
            self.disk_mask = (rd > 1.2) & (rd < 9)
            self.disk_r = rd[self.disk_mask].astype(np.float32)
            self.disk_a = np.arctan2(ry, dx)[self.disk_mask].astype(np.float32)
            self.disk_y, self.disk_x = np.nonzero(self.disk_mask)
            self.girdap = _dongulu_doku(64, 512, rng, terim=40, cozgu=0.1)
            self.jet = (np.exp(-np.abs(dx) / (self.R * 0.35)) * np.exp(-r * 0.12) * 0.35)[..., None] * \
                (p[2] * 0.5 + 0.5)
            self.jet = self.jet.astype(np.float32)

    def _parlak_ciz(self, kare: np.ndarray, t: float):
        p = self.palet
        kare += self.cekirdek
        if self.tur == "pulsar":
            th = TAU * t / self.L
            c = np.cos(self.aci - th)
            isin = np.exp((np.abs(c) - 1) * 60) * np.exp(-self.r * 0.06) * (self.r > 0.6)
            kare += (isin * 0.55)[..., None] * (p[2] * 0.6 + 0.4)
        else:
            u = ((self.disk_a / TAU + 0.5) * 512 + 12 / self.disk_r * 40 + 512 * t / self.L) % 512
            v = np.clip((self.disk_r - 1.2) / 7.8 * 63, 0, 63).astype(np.int32)
            g = self.girdap[v, u.astype(np.int32) % 512]
            parlak = np.exp(-(self.disk_r - 1.2) * 0.45) * (0.35 + 0.65 * g)
            kare[self.disk_y, self.disk_x] += parlak[:, None] * (p[3] * 0.6 + p[2] * 0.4)
            kare += self.jet

    # ---------- ortak ----------
    def _yildiz_ciz(self, kare: np.ndarray, t: float):
        th = TAU * t / self.L
        for x, y, b, k, faz, ton, yaricap in self.yildiz:
            px = (x + yaricap * math.cos(th)) % (self.W - 1)
            py = (y + yaricap * math.sin(th)) % (self.H - 1)
            parlak = b * (0.7 + 0.3 * np.sin(k * th + faz))
            x0, y0 = px.astype(np.int32), py.astype(np.int32)
            fx, fy = px - x0, py - y0
            for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy),
                              (1, 1, fx * fy)):
                np.add.at(kare, (y0 + dy, x0 + dx), (parlak * w)[:, None] * ton)

    def _probe_ciz(self, kare: np.ndarray, t: float):
        rgb, alfa = probe_sprite(self.probe_boy)
        sh, sw = alfa.shape[:2]
        y = int(self.py + 5 * math.sin(TAU * t / self.L) - sh / 2)
        x = int(self.px + 3 * math.cos(TAU * t / self.L) - sw / 2)
        if y < 0 or x < 0 or y + sh > self.H or x + sw > self.W:
            return
        alan = kare[y:y + sh, x:x + sw]
        alan[:] = alan * (1 - alfa) + rgb * 0.82 * alfa
        # yanıp sönen ışık (döngüde tam sayıda)
        if (t * 8 * self.probe_k / self.L) % 1 < 0.12:
            ly, lx = y + int(sh * 0.62), x + sw // 2 + int(sw * 0.08)
            kare[ly - 2:ly + 2, lx - 2:lx + 2] += np.array([1.0, 0.25, 0.2], np.float32)

    def kare(self, t: float) -> np.ndarray:
        t = t % self.L
        kare = self.arka.copy()
        th = TAU * t / self.L + self.neb_faz
        ox = int(round(self.neb_r + 1 + self.neb_r * math.cos(th)))
        oy = int(round(self.neb_r + 1 + self.neb_r * math.sin(th)))
        kare += self.nebula[oy:oy + self.H, ox:ox + self.W]
        self._yildiz_ciz(kare, t)
        if self.tur in ("pulsar", "kuasar"):
            self._parlak_ciz(kare, t)
        else:
            if self.halka:
                kare[:] = kare * (1 - self.halka_arka) + self.halka_renk * self.halka_arka
            kare += self.hale
            self._gezegen_ciz(kare, t)
            if self.halka:
                kare[:] = kare * (1 - self.halka_on) + self.halka_renk * self.halka_on
        if self.probe:
            self._probe_ciz(kare, t)
        kare *= self.vinyet
        return (np.clip(kare, 0, 1) ** (1 / 1.1) * 255).astype(np.uint8)


def dongu_kodla(sahne: Sahne, hedef: Path, fps: int = 24, crf: int = 16, sure: float | None = None,
                ust_katman: np.ndarray | None = None, lut: Path | None = None) -> Path:
    """Sahneyi ffmpeg'e ham kare olarak akıtır. sure verilmezse tam bir döngü (L sn) kodlanır.
    ust_katman: (H, W, 4) float 0..1, her karenin üstüne konur (Shorts yazıları için; filtreden sonra).
    lut: marka renk filtresinin .cube dosyası (renk.py); ffmpeg lut3d ile uygulanır."""
    if lut is not None and ust_katman is not None:
        from .renk import marka_filtresi, uygula
        f = marka_filtresi()
        lut, onceden = None, f  # yazı filtrelenmesin: filtre karede, yazı sonra
    else:
        onceden = None
    sure = sure or sahne.L
    n = int(round(sure * fps))
    komut = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{sahne.W}x{sahne.H}", "-r", str(fps), "-i", "-",
             *(["-vf", f"lut3d=file={lut}"] if lut else []), "-c:v", "libx264", "-preset", "medium",
             "-crf", str(crf), "-pix_fmt", "yuv420p", "-g", str(fps * 2), str(hedef)]
    surec = subprocess.Popen(komut, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            k = sahne.kare(i / fps)
            if onceden:
                k = uygula(k, onceden["duraklar"], onceden["guc"], onceden.get("kontrast", 1.0))
            if ust_katman is not None:
                a = ust_katman[..., 3:]
                k = (k * (1 - a) + ust_katman[..., :3] * 255 * a).astype(np.uint8)
            surec.stdin.write(k.tobytes())
        surec.stdin.close()
    except BrokenPipeError:
        pass
    if surec.wait() != 0:
        raise RuntimeError(f"ffmpeg sahne kodlaması başarısız: {surec.stderr.read().decode()[-1500:]}")
    return hedef
