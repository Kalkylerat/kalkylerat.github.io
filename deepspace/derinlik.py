"""Derinlik haritası: görselin hangi kısmı yakın, hangisi uzak (3D fotoğraf efekti için, SOZLESME.md G6).

Model: Depth Anything V2 Small (Apache-2.0), ONNX sürümü; bilgisayarda ücretsiz ve internetsiz çalışır.
İlk kullanımda GitHub'dan bir kez indirilir (~100 MB) ve `deepspace/.model/` altında saklanır (depoya girmez).
Çıktı: görselle aynı boyutta 0..1 dizi, 1 = en yakın. Sonuç `gorsel/NN_derinlik.png` olarak önbelleğe yazılır;
o dosya elle de düzeltilebilir (beyaz yakın, siyah uzak).
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

from .ortak import KOK

MODEL_URL = "https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v2.0.0/depth_anything_v2_vits.onnx"
MODEL_YOLU = KOK / ".model" / "depth_anything_v2_vits.onnx"
GIRDI = 518  # modelin beklediği kenar (14'ün katı)


def model_hazirla(yol: Path = MODEL_YOLU) -> Path:
    if not yol.exists():
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_suffix(".indiriliyor")
        urllib.request.urlretrieve(MODEL_URL, gecici)
        gecici.rename(yol)
    return yol


def tahmin(img: Image.Image, model: Path | None = None) -> np.ndarray:
    import onnxruntime as ort

    oturum = ort.InferenceSession(str(model or model_hazirla()), providers=["CPUExecutionProvider"])
    girdi = oturum.get_inputs()[0]
    x = np.asarray(img.convert("RGB").resize((GIRDI, GIRDI), Image.BICUBIC), np.float32) / 255
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    x = x.transpose(2, 0, 1)[None]
    d = np.squeeze(oturum.run(None, {girdi.name: x})[0]).astype(np.float32)  # büyük = yakın (göreli ters derinlik)
    d = np.asarray(Image.fromarray(d).resize(img.size, Image.BICUBIC), np.float32)
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)
    return np.clip((d - lo) / (hi - lo + 1e-6), 0, 1)


def derinlik_haritasi(gorsel: Path) -> np.ndarray:
    """gorsel/NN.png için önbellekli derinlik (gorsel/NN_derinlik.png)."""
    onbellek = gorsel.with_name(gorsel.stem + "_derinlik.png")
    img = Image.open(gorsel)
    if onbellek.exists():
        d = Image.open(onbellek).convert("L").resize(img.size, Image.BICUBIC)
        return np.asarray(d, np.float32) / 255
    d = tahmin(img)
    Image.fromarray((d * 255).astype(np.uint8)).save(onbellek)
    return d
