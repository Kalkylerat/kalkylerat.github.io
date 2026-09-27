import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "spel.json"
PANEL_FILE = ROOT / "docs" / "index.html"


@dataclass(frozen=True)
class Ayarlar:
    saat_dilimi: str
    ligler: list[int]
    max_mac_tarama: int
    max_spel: int
    oran_min: float
    oran_max: float
    min_deger: float
    min_olasilik: float
    model_tolerans: float
    min_dakika_once: int
    keskin_bahisci: str
    isvec_bahisciler: list[str]
    claude_model: str
    claude_effort: str
    otomatik_paylas: bool


def yukle(path: Path = ROOT / "ayarlar.toml") -> Ayarlar:
    with open(path, "rb") as f:
        t = tomllib.load(f)
    s = t["spel"]
    return Ayarlar(
        saat_dilimi=t["genel"]["saat_dilimi"],
        ligler=list(t["ligler"]["izinli"]),
        max_mac_tarama=int(t["ligler"]["max_mac_tarama"]),
        max_spel=int(s["max_spel"]),
        oran_min=float(s["oran_min"]),
        oran_max=float(s["oran_max"]),
        min_deger=float(s["min_deger"]),
        min_olasilik=float(s["min_olasilik"]),
        model_tolerans=float(s["model_tolerans"]),
        min_dakika_once=int(s["min_dakika_once"]),
        keskin_bahisci=t["bahisciler"]["keskin"],
        isvec_bahisciler=list(t["bahisciler"]["isvec_lisansli"]),
        claude_model=t["claude"]["model"],
        claude_effort=t["claude"]["effort"],
        otomatik_paylas=bool(t["yayin"]["otomatik_paylas"]),
    )


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} tanımlı değil. GitHub > Settings > Secrets and variables > Actions altına ekleyin.")
    return value
