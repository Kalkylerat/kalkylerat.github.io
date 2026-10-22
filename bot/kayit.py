"""Günlük kayıt: data/spel.json (her gün bir analiz kaydı; 1 Ekim 2026 öncesinin kupon günleri geçmiş olarak durur)."""

import json
from datetime import datetime, timezone
from pathlib import Path


def yukle(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def kaydet(path: Path, gunler: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(gunler, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bul(gunler: list[dict], gun_id: str) -> dict | None:
    return next((g for g in gunler if g["id"] == gun_id), None)


def simdi_utc() -> datetime:
    return datetime.now(timezone.utc)
