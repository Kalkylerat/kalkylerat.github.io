"""Tek bildirim kanalı (sahibinin isteği, 25 Ekim 2026: "aynı bildirim e-posta ve GitHub'dan iki üç kez geliyor"):
yeni yorum fırsatı ve cevaplanmaya değer yorum geldiğinde telefona / Chrome'a TEK anlık bildirim (ntfy.sh), dokununca
gelen kutusu açılır. Konu adı GitHub secret'ında (NTFY_KONU): herkese açık depoda yazmaz, tahmin edilemez.
Konu yoksa bildirim gitmez (False) ve çağıran GitHub etiketlemesine döner (bir kez). Ücretsiz; hiçbir şey paylaşmaz."""

import os

import requests

SUNUCU = "https://ntfy.sh"


def acik() -> bool:
    return bool(os.environ.get("NTFY_KONU", "").strip())


def gonder(baslik: str, metin: str, url: str, etiket: str = "soccer") -> bool:
    """Bildirimi gönderir; gönderildiyse True. Hata paylaşımı durdurmaz."""
    konu = os.environ.get("NTFY_KONU", "").strip()
    if not konu:
        return False
    try:
        r = requests.post(SUNUCU, json={"topic": konu, "title": baslik[:120], "message": metin[:500], "click": url,
                                        "tags": [etiket]}, timeout=15)
        return r.ok
    except requests.RequestException:
        return False
