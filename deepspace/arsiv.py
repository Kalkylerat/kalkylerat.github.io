"""Bölüm arşivi (G19): videoya giren şarkılar, son görseller ve istemler görevin arsiv/ klasörüne kopyalanır."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class ArsivHatasi(Exception):
    pass


ISTEM_DOSYALARI = ("gorev.toml", "SUNO.md", "GORSEL.md", "ses/secim.json")


def _sha256(yol: Path) -> str:
    h = hashlib.sha256()
    with yol.open("rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def _puan(kl: Path, no: int) -> int | None:
    yol = kl / "denetim" / f"{no:02d}.json"
    if not yol.exists():
        return None
    return json.loads(yol.read_text(encoding="utf-8")).get("puan")


def arsivle(gorev: dict) -> Path:
    """Eksik dosya varsa hiçbir şey kopyalamadan ArsivHatasi verir; kaynaklara dokunmaz (yalnız kopyalar)."""
    kl = Path(gorev["klasor"])
    eksik = []
    for i, p in enumerate(gorev["parca"], 1):
        if not (kl / "ses" / p["dosya"]).exists():
            eksik.append(f"{i:02d} şarkı ({p['dosya']})")
        if not (kl / "gorsel" / f"{i:02d}.png").exists():
            eksik.append(f"{i:02d} görsel")
    if eksik:
        raise ArsivHatasi("arşiv kurulmadı, eksik: " + ", ".join(eksik))

    hedef = kl / "arsiv"
    for alt in ("sarkilar", "gorseller", "istemler"):
        (hedef / alt).mkdir(parents=True, exist_ok=True)
    satirlar = []
    for i, p in enumerate(gorev["parca"], 1):
        sarki = kl / "ses" / p["dosya"]
        gorsel = kl / "gorsel" / f"{i:02d}.png"
        shutil.copy2(sarki, hedef / "sarkilar" / sarki.name)
        shutil.copy2(gorsel, hedef / "gorseller" / gorsel.name)
        satirlar.append({"no": i, "ad": p["ad"], "sarki": sarki.name, "sarki_sha256": _sha256(sarki),
                         "gorsel": gorsel.name, "gorsel_sha256": _sha256(gorsel),
                         "gorsel_oturum": p.get("gorsel_oturum"), "gorsel_uretim": p.get("gorsel_uretim"),
                         "denetim_puani": _puan(kl, i)})
    for ad in ISTEM_DOSYALARI:
        kaynak = kl / ad
        if kaynak.exists():
            shutil.copy2(kaynak, hedef / "istemler" / kaynak.name)
    liste = {"gorev": gorev.get("no"), "olusturma": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "parcalar": satirlar}
    (hedef / "liste.json").write_text(json.dumps(liste, ensure_ascii=False, indent=2), encoding="utf-8")
    return hedef
