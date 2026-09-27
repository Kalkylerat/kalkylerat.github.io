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
    istek_araligi_sn: float
    max_oyun: int
    max_oyun_mac_basina: int
    guvenli_min_olasilik: float
    guvenli_min_deger: float
    deger_min_olasilik: float
    deger_min_deger: float
    oran_min: float
    oran_max: float
    model_tolerans: float
    min_dakika_once: int
    kombi_max_ayak: int
    kombi_max_oran: float
    kombi_min_olasilik: float
    kasa_baslangic: float
    oyun_yuzdesi: float
    para_birimi: str
    keskin_bahisci: str
    oran_bahiscileri: list[str]
    claude_model: str
    claude_effort: str
    otomatik_paylas: bool


def yukle(path: Path = ROOT / "ayarlar.toml") -> Ayarlar:
    with open(path, "rb") as f:
        t = tomllib.load(f)
    s, k, kasa = t["strateji"], t["kombine"], t["kasa"]
    return Ayarlar(
        saat_dilimi=t["genel"]["saat_dilimi"],
        ligler=list(t["ligler"]["izinli"]),
        max_mac_tarama=int(t["ligler"]["max_mac_tarama"]),
        istek_araligi_sn=float(t["ligler"]["istek_araligi_sn"]),
        max_oyun=int(s["max_oyun"]),
        max_oyun_mac_basina=int(s["max_oyun_mac_basina"]),
        guvenli_min_olasilik=float(s["guvenli_min_olasilik"]),
        guvenli_min_deger=float(s["guvenli_min_deger"]),
        deger_min_olasilik=float(s["deger_min_olasilik"]),
        deger_min_deger=float(s["deger_min_deger"]),
        oran_min=float(s["oran_min"]),
        oran_max=float(s["oran_max"]),
        model_tolerans=float(s["model_tolerans"]),
        min_dakika_once=int(s["min_dakika_once"]),
        kombi_max_ayak=int(k["max_ayak"]),
        kombi_max_oran=float(k["max_oran"]),
        kombi_min_olasilik=float(k["min_olasilik"]),
        kasa_baslangic=float(kasa["baslangic"]),
        oyun_yuzdesi=float(kasa["oyun_yuzdesi"]),
        para_birimi=kasa["para_birimi"],
        keskin_bahisci=t["bahisciler"]["keskin"],
        oran_bahiscileri=list(t["bahisciler"]["oran_bahiscileri"]),
        claude_model=t["claude"]["model"],
        claude_effort=t["claude"]["effort"],
        otomatik_paylas=bool(t["yayin"]["otomatik_paylas"]),
    )


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} tanımlı değil. GitHub > Settings > Secrets and variables > Actions altına ekleyin.")
    return value
